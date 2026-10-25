"""给 PayPal 沙盒账号种演示数据：3 个服务 → 月度计划 → 订阅。

- 幂等可重跑：商品/计划按名字复用，订阅按 plan_id 去重，不重复堆积。
- 沙盒订阅创建后为 APPROVAL_PENDING，脚本会打印批准链接；
  用沙盒【个人】测试账号登录并逐个点开批准后即变 ACTIVE（且产生首笔扣款流水）。
- 激活接口（POST /activate）对 APPROVAL_PENDING 的订阅会被 422 拒绝，别绕这条路。

运行：python seed_sandbox.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, sys.path.path0 if hasattr(sys, "path0") else ".")

import httpx  # noqa: E402

from app import paypal_client as pc  # noqa: E402  导入即加载 .env

DEMO_SERVICES = [
    ("StreamFlix", "StreamFlix 月度会员", "12.99"),
    ("MusicBox", "MusicBox 月度会员", "9.99"),
    ("CloudDrive", "CloudDrive 2TB 空间月费", "4.99"),
]


async def api(method: str, path: str, **kwargs) -> httpx.Response:
    token = await pc._token()
    async with httpx.AsyncClient() as client:
        return await client.request(
            method, f"{pc.API_BASE}{path}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=30, **kwargs,
        )


async def find_or_create_product(name: str) -> str:
    data = (await api("GET", "/v1/catalogs/products", params={"page_size": 20})).json()
    for p in data.get("products", []):
        if p["name"] == name:
            print(f"复用商品 {name} ({p['id']})")
            return p["id"]
    r = await api("POST", "/v1/catalogs/products", json={
        "name": name, "description": f"{name} 演示订阅（SubScribe Butler 种子数据）", "type": "SERVICE",
    })
    r.raise_for_status()
    pid = r.json()["id"]
    print(f"新建商品 {name} ({pid})")
    return pid


async def find_or_create_plan(name: str, product_id: str, price: str) -> str:
    data = (await api("GET", "/v1/billing/plans", params={"page_size": 20})).json()
    for p in data.get("plans", []):
        if p["name"] == name:
            print(f"复用计划 {name} ({p['id']})")
            return p["id"]
    r = await api("POST", "/v1/billing/plans", json={
        "product_id": product_id,
        "name": name,
        "status": "ACTIVE",
        "billing_cycles": [{
            "frequency": {"interval_unit": "MONTH", "interval_count": 1},
            "tenure_type": "REGULAR", "sequence": 1, "total_cycles": 0,
            "pricing_scheme": {"fixed_price": {"value": price, "currency_code": "USD"}},
        }],
        "payment_preferences": {"auto_bill_outstanding": True,
                                "setup_fee_failure_action": "CONTINUE",
                                "payment_failure_threshold": 3},
    })
    r.raise_for_status()
    pid = r.json()["id"]
    print(f"新建计划 {name} ({pid})")
    return pid


async def main():
    # 去重用本地状态文件：列表接口看不到 APPROVAL_PENDING 的订阅，
    # 待批准订阅的 cancel 接口也是 404（不可取消），所以靠它避免重复创建。
    state_path = Path(__file__).parent / ".seed_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    sub_ids: dict[str, str] = {}

    for svc, plan_name, price in DEMO_SERVICES:
        product_id = await find_or_create_product(svc)
        plan_id = await find_or_create_plan(plan_name, product_id, price)
        sid = state.get(svc)
        if sid:
            d = (await api("GET", f"/v1/billing/subscriptions/{sid}")).json()
            if d.get("status") and d["status"] != "CANCELLED":
                sub_ids[svc] = sid
                print(f"复用订阅 {svc} ({sid}) [{d['status']}]")
                continue
        r = await api("POST", "/v1/billing/subscriptions", json={
            "plan_id": plan_id,
            "subscriber": {"name": {"given_name": svc},
                            "email_address": "demo-buyer@subscribetest.com"},
            "application_context": {
                "brand_name": "SubScribe Butler", "locale": "en-US",
                "user_action": "CONTINUE", "shipping_preference": "NO_SHIPPING",
                "payment_method": {"payer_selected": "PAYPAL",
                                    "payee_preferred": "IMMEDIATE_PAYMENT_REQUIRED"},
            },
        })
        if r.status_code >= 300:
            print(f"[FAIL] 建订阅 {svc}: {r.status_code} {r.text[:300]}")
            continue
        sub = r.json()
        sub_ids[svc] = sub["id"]
        state[svc] = sub["id"]
        print(f"新建订阅 {svc} ({sub['id']}) [{sub['status']}]")

    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    # 汇总当前状态 + 打印待批准链接
    # 注意：GET /v1/billing/subscriptions 列表接口不返回 APPROVAL_PENDING 的订阅，
    # 所以逐个按 ID 查详情，才能看到待批准状态和链接。
    print("\n当前演示订阅状态：")
    for svc, _, _ in DEMO_SERVICES:
        sid = sub_ids.get(svc)
        if not sid:
            continue
        d = (await api("GET", f"/v1/billing/subscriptions/{sid}")).json()
        status = d.get("status")
        print(f"  - {svc}  [{status}]  {sid}")
        if status == "APPROVAL_PENDING":
            for link in d.get("links", []):
                if link.get("rel") == "approve":
                    print(f"    待批准，买家批准链接：{link['href']}")

    print("\n提示：用沙盒【个人】测试账号（Testing Tools > Sandbox Accounts 里 @personal.example.com 那个）"
          "登录 www.sandbox.paypal.com 后逐个打开上面的链接点同意，订阅即变 ACTIVE 并产生首笔扣款。")


if __name__ == "__main__":
    asyncio.run(main())
