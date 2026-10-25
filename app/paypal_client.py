"""PayPal REST 客户端。

未配置 PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET 时自动进入 Mock 模式，
使用 app/mock_data.py 演示，保证评审在没有外部凭据的情况下也能跑通。

配置沙盒凭据后走真实 PayPal Sandbox API：
- OAuth2 客户端凭据流
- /v1/billing/subscriptions        订阅查询
- /v1/billing/subscriptions/{id}/cancel  取消订阅
- /v1/reporting/transactions       交易流水
"""

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


async def _catalog() -> tuple[dict, dict]:
    """返回 ({plan_id: plan}, {product_id: product})，带 5 分钟缓存。"""
    global _catalog_cache
    now = time.time()
    if _catalog_cache and _catalog_cache[0] > now:
        return _catalog_cache[1], _catalog_cache[2]
    try:
        plans = {p["id"]: p for p in
                 (await _api("GET", "/v1/billing/plans", params={"page_size": 20})).get("plans", [])}
    except Exception:
        plans = {}
    # 列表接口的计划不含 billing_cycles（拿不到价格），逐个补拉详情
    for pid, plan in list(plans.items()):
        if not plan.get("billing_cycles"):
            try:
                plans[pid] = await _api("GET", f"/v1/billing/plans/{pid}")
            except Exception:
                pass
    try:
        products = {p["id"]: p for p in
                    (await _api("GET", "/v1/catalogs/products", params={"page_size": 20})).get("products", [])}
    except Exception:
        products = {}
    _catalog_cache = (now + 300, plans, products)
    return plans, products


async def list_subscriptions() -> list[dict]:
    if mode() == "mock":
        return [dict(s) for s in _state]
    data = await _api("GET", "/v1/billing/subscriptions", params={"page_size": 20})
    plans, products = await _catalog()
    subs = []
    for item in data.get("subscriptions", []):
        # 列表接口只返回 id/status/create_time，plan_id 和账单信息要逐条拉详情
        try:
            item = await _api("GET", f"/v1/billing/subscriptions/{item['id']}")
        except Exception:
            pass
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
        subs.append({
            "id": item["id"],
            "name": product.get("name") or plan.get("name") or item["id"],
            "category": "订阅服务",
            "monthly_amount": float(price.get("value") or last_pay.get("value") or 0),
            "currency": price.get("currency_code") or last_pay.get("currency_code") or "USD",
            "status": item.get("status", "UNKNOWN"),
            "next_billing_date": nbt[:10] if nbt else None,
            "subscribed_since": (item.get("create_time") or "")[:10],
        })
    return subs


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
    return {"ok": True, "subscription_id": subscription_id}


async def get_transactions(days: int = 30) -> list[dict]:
    if mode() == "mock":
        return [dict(t) for t in mock_data.MOCK_TRANSACTIONS]
    from datetime import date, timedelta
    end = date.today().isoformat()
    start = (date.today() - timedelta(days=days)).isoformat()
    data = await _api("GET", "/v1/reporting/transactions", params={
        "start_date": f"{start}T00:00:00-0700",
        "end_date": f"{end}T23:59:59-0700",
        "fields": "all",
    })
    return [
        {
            "transaction_id": t.get("transaction_info", {}).get("transaction_id", ""),
            "name": t.get("transaction_info", {}).get("transaction_subject", ""),
            "amount": float(t.get("transaction_info", {}).get("transaction_amount", {}).get("value", "0") or 0),
            "currency": t.get("transaction_info", {}).get("transaction_amount", {}).get("currency_code", "USD"),
            "date": (t.get("transaction_info", {}).get("transaction_initiation_date") or "")[:10],
            "status": t.get("transaction_info", {}).get("transaction_status", ""),
        }
        for t in data.get("transaction_details", [])
    ]
