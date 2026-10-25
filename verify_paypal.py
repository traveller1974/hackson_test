"""PayPal 沙盒连接验证：读取 .env 里的凭据，测试 OAuth2 + 订阅 + 交易三个接口。

只输出成功/失败与打码后的凭据指纹，绝不打印 Client Secret。
运行：python verify_paypal.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import paypal_client  # noqa: E402  导入 app 会先触发 __init__.py 加载 .env

results = []


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  -> {detail}" if detail else ""))
    results.append(ok)


def mask(s: str) -> str:
    return f"{s[:6]}…{s[-4:]}" if len(s) > 12 else "(长度不足，疑似填错)"


async def main():
    cid, sec = paypal_client.CLIENT_ID, paypal_client.CLIENT_SECRET
    mode = paypal_client.mode()
    check("凭据已加载（mode=sandbox）", mode == "sandbox",
          f"mode={mode}，ClientID={mask(cid) if cid else '(空)'}")
    if mode != "sandbox":
        print("\n结论：❌ 未检测到有效凭据，请检查 .env 是否保存。")
        return

    try:
        token = await paypal_client._token()
        check("OAuth2 换取 access_token", bool(token), f"token长度={len(token)}")
    except Exception as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        hint = "凭据被拒（401）：检查是否复制完整、用的是 Sandbox 的应用" if status == 401 else "网络或服务异常"
        check("OAuth2 换取 access_token", False, f"{type(e).__name__} status={status}（{hint}）")

    try:
        subs = await paypal_client.list_subscriptions()
        check("Subscriptions API 列表查询", isinstance(subs, list), f"共 {len(subs)} 条订阅（新沙盒账号为 0 属正常）")
    except Exception as e:
        check("Subscriptions API 列表查询", False, f"{type(e).__name__}")

    try:
        txs = await paypal_client.get_transactions(30)
        check("Transactions API 流水查询", isinstance(txs, list), f"近30天 {len(txs)} 笔（新沙盒账号为 0 属正常）")
    except Exception as e:
        check("Transactions API 流水查询", False, f"{type(e).__name__}")

    print("\n结论：" + ("✅ 沙盒凭据有效，可以开始接真实 API 了" if all(results) else "❌ 有失败项，见上方提示"))


if __name__ == "__main__":
    asyncio.run(main())
