"""PayPal REST 客户端。

未配置 PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET 时自动进入 Mock 模式，
使用 app/mock_data.py 演示，保证评审在没有外部凭据的情况下也能跑通。

配置沙盒凭据后走真实 PayPal Sandbox API：
- OAuth2 客户端凭据流
- /v1/billing/subscriptions        订阅查询
- /v1/billing/subscriptions/{id}/cancel  取消订阅
- /v1/reporting/transactions       交易流水
"""

import asyncio
import os
import time

import httpx

from . import mock_data

CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")
API_BASE = os.getenv("PAYPAL_API_BASE", "https://api-m.sandbox.paypal.com")

# Mock 模式的可变内存状态（演示中取消订阅后立刻可见）
_state: list[dict] = [dict(s) for s in mock_data.MOCK_SUBSCRIPTIONS]


def mode() -> str:
    return "sandbox" if (CLIENT_ID and CLIENT_SECRET) else "mock"


_token_cache: tuple[float, str] | None = None


async def _token() -> str:
    global _token_cache
    if _token_cache and _token_cache[0] > time.time():
        return _token_cache[1]
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(CLIENT_ID, CLIENT_SECRET),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    _token_cache = (time.time() + int(data.get("expires_in", 300)) - 30, data["access_token"])
    return _token_cache[1]


async def _api(method: str, path: str, **kwargs) -> dict:
    token = await _token()
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method, f"{API_BASE}{path}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=20, **kwargs,
        )
        resp.raise_for_status()
        return resp.json() if resp.text else {}


# 沙盒目录缓存：新订阅还没有扣款记录，名字和价格要从计划/商品目录取
_catalog_cache: tuple[float, dict, dict] | None = None
# 订阅列表缓存：一次仪表盘加载要打 9 个 PayPal 接口，短缓存让页面秒开、网络抖动也不白屏
_subs_cache: tuple[float, list[dict]] | None = None
_refresh_task: asyncio.Task | None = None
_REFRESH_INTERVAL = 25


async def _refresh_subs() -> list[dict]:
    """从 PayPal 拉取订阅全集并重建视图，成功后写缓存。"""
    global _subs_cache
    data = await _api("GET", "/v1/billing/subscriptions", params={"page_size": 20})
    plans, products = await _catalog()
    # 列表接口只返回 id/status/create_time，plan_id 和账单信息要并行拉详情
    details = await asyncio.gather(
        *[_safe_api("GET", f"/v1/billing/subscriptions/{item['id']}") for item in data.get("subscriptions", [])])
    subs = []
    for item, d in zip(data.get("subscriptions", []), details):
        subs.append(_build_sub(d if isinstance(d, dict) else item, plans, products))
    _subs_cache = (time.time(), subs)
    return [dict(s) for s in subs]


async def _refresh_loop():
    """常驻后台刷新：仪表盘永远读缓存秒开，数据最多滞后 25 秒。"""
    while True:
        try:
            await _refresh_subs()
        except Exception:
            pass  # PayPal 网络抖动时保持旧数据，下一轮再试
        await asyncio.sleep(_REFRESH_INTERVAL)


def start_refresh_loop():
    global _refresh_task
    if _refresh_task is None or _refresh_task.done():
        _refresh_task = asyncio.create_task(_refresh_loop())


async def list_subscriptions() -> list[dict]:
    if mode() == "mock":
        return [dict(s) for s in _state]
    if _subs_cache:
        return [dict(s) for s in _subs_cache[1]]
    return await _refresh_subs()  # 首次且后台刷新尚未成功时现拉一次


async def _catalog() -> tuple[dict, dict]:
    """返回 ({plan_id: plan}, {product_id: product})，带 5 分钟缓存。"""
    global _catalog_cache
    now = time.time()
    if _catalog_cache and _catalog_cache[0] > now:
        return _catalog_cache[1], _catalog_cache[2]
    try:
        plans_list = (await _api("GET", "/v1/billing/plans", params={"page_size": 20})).get("plans", [])
    except Exception:
        plans_list = []
    # 列表接口的计划不含 billing_cycles（拿不到价格），并行补拉详情
    details = await asyncio.gather(
        *[_safe_api("GET", f"/v1/billing/plans/{p['id']}") for p in plans_list],
        return_exceptions=True)
    plans = {p["id"]: p for p in plans_list}
    for p, d in zip(plans_list, details):
        if isinstance(d, dict):
            plans[p["id"]] = d
    try:
        products = {p["id"]: p for p in
                    (await _api("GET", "/v1/catalogs/products", params={"page_size": 20})).get("products", [])}
    except Exception:
        products = {}
    if plans or products or not _catalog_cache:
        _catalog_cache = (now + 300, plans, products)
    return _catalog_cache[1], _catalog_cache[2]


async def _safe_api(method: str, path: str, **kwargs) -> dict | Exception:
    try:
        return await _api(method, path, **kwargs)
    except Exception as e:
        return e


# PayPal 商品目录没有 category 字段，分类标签按名称归类（与 mock 数据的分类口径一致）
_CATEGORY_HINTS = {
    "streamflix": "视频娱乐", "netflix": "视频娱乐", "iqiyi": "视频娱乐", "爱奇艺": "视频娱乐",
    "youtube": "视频娱乐", "disney": "视频娱乐", "hbo": "视频娱乐",
    "musicbox": "音乐", "spotify": "音乐", "音乐": "音乐", "apple music": "音乐",
    "clouddrive": "云存储", "icloud": "云存储", "dropbox": "云存储", "onedrive": "云存储",
    "chatgpt": "AI 工具", "claude": "AI 工具", "gemini": "AI 工具", "copilot": "AI 工具",
    "microsoft": "软件办公", "adobe": "软件办公", "office": "软件办公",
    "keep": "健身", "健身": "健身",
}


def _guess_category(name: str) -> str:
    n = name.lower()
    for key, cat in _CATEGORY_HINTS.items():
        if key in n:
            return cat
    return "订阅服务"


def _build_sub(item: dict, plans: dict, products: dict) -> dict:
    plan = plans.get(item.get("plan_id"), {})
    product = products.get(plan.get("product_id", ""), {})
    price = {}
    for cycle in plan.get("billing_cycles") or []:
        fp = (cycle.get("pricing_scheme") or {}).get("fixed_price") or {}
        if fp:
            price = fp
            break
    last_pay = item.get("billing_info", {}).get("last_payment", {}).get("amount", {})
    nbt = item.get("billing_info", {}).get("next_billing_time", "")
    return {
        "id": item["id"],
        "name": product.get("name") or plan.get("name") or item["id"],
        "category": _guess_category(product.get("name") or plan.get("name") or item["id"]),
        "monthly_amount": float(price.get("value") or last_pay.get("value") or 0),
        "currency": price.get("currency_code") or last_pay.get("currency_code") or "USD",
        "status": item.get("status", "UNKNOWN"),
        "next_billing_date": nbt[:10] if nbt else None,
        "subscribed_since": (item.get("create_time") or "")[:10],
        "billing_interval": ((plan.get("billing_cycles") or [{}])[0].get("frequency") or {}).get("interval_unit", "MONTH"),
    }


async def cancel_subscription(subscription_id: str) -> dict:
    if mode() == "mock":
        for s in _state:
            if s["id"] == subscription_id:
                if s["status"] != "ACTIVE":
                    return {"ok": False, "error": f"{s['name']} 已经不是生效状态"}
                s["status"] = "CANCELLED"
                s["next_billing_date"] = None
                return {"ok": True, "subscription": dict(s)}
        return {"ok": False, "error": f"找不到 ID 为 {subscription_id} 的订阅"}
    await _api("POST", f"/v1/billing/subscriptions/{subscription_id}/cancel",
               json={"reason": "Cancelled by SubScribe Butler"})
    global _subs_cache
    if _subs_cache:
        _subs_cache = (0.0, _subs_cache[1])  # 标记为过期，保留数据供页面即时渲染
    asyncio.create_task(_safe_refresh())
    return {"ok": True, "subscription_id": subscription_id}


async def _safe_refresh():
    try:
        await _refresh_subs()
    except Exception:
        pass


async def get_transactions(days: int = 30) -> list[dict]:
    """扣款流水。PayPal 交易接口单次查询窗口最长 31 天，长跨度按窗口拼接并按流水号去重。"""
    if mode() == "mock":
        return [dict(t) for t in mock_data.MOCK_TRANSACTIONS]
    from datetime import datetime, timedelta

    now = datetime.now().astimezone()
    tz = now.strftime("%z")  # 本机时区偏移，如 +0800
    win_start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    by_id: dict[str, dict] = {}
    while win_start < now:
        win_end = min(win_start + timedelta(days=31), now)
        page, total_pages = 1, 1
        while page <= total_pages:
            data = await _api("GET", "/v1/reporting/transactions", params={
                "start_date": win_start.strftime("%Y-%m-%dT%H:%M:%S") + tz,
                "end_date": win_end.strftime("%Y-%m-%dT%H:%M:%S") + tz,
                "fields": "all", "page_size": 100, "page": page,
            })
            total_pages = int(data.get("total_pages") or 1)
            for t in data.get("transaction_details", []):
                ti = t.get("transaction_info", {})
                if ti.get("transaction_event_code") == "T1900" or ti.get("transaction_subject") == "Initial balance":
                    continue  # 账户余额台账，不是扣款
                key = ti.get("transaction_id") or f"{ti.get('transaction_initiation_date')}{ti.get('transaction_amount')}"
                by_id[key] = t
            page += 1
        win_start = win_end
    _STATUS = {"S": "Success", "P": "Pending", "V": "Voided", "F": "Failed", "R": "Reversed"}
    return [
        {
            "transaction_id": ti.get("transaction_id", ""),
            "name": ti.get("transaction_subject", "") or ti.get("transaction_note", ""),
            "amount": float(ti.get("transaction_amount", {}).get("value", "0") or 0),
            "currency": ti.get("transaction_amount", {}).get("currency_code", "USD"),
            "date": (ti.get("transaction_initiation_date") or "")[:10],
            "status": _STATUS.get(ti.get("transaction_status", ""), ti.get("transaction_status", "")),
        }
        for ti in by_id.values()
    ]
