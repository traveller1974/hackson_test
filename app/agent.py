"""AI Agent 核心：自然语言 → 工具调用 → 回答。

支持两种驱动方式：
1. 配置 LLM_API_KEY（OpenAI 兼容接口）后，走标准的 function-calling 循环；
2. 无 Key 时自动降级为规则引擎（中文关键词意图识别），保证离线可演示。
"""

import json
import os
from collections import defaultdict

import httpx

from . import paypal_client

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = (
    "你是「订阅管家 SubScribe Butler」，帮用户管理 PayPal 订阅：查询订阅、统计开销、取消订阅、给出省钱建议。"
    "回答简洁友好，涉及金额时给出具体数字。用户取消订阅时先复述要取消的服务，执行后确认结果。"
    "省钱建议要基于用户的真实订阅数据（同类别多份订阅时建议保留一份）。"
)

TOOLS_SPEC = [
    {"type": "function", "function": {
        "name": "list_subscriptions",
        "description": "列出用户所有 PayPal 订阅及其状态、月费、下次扣款日",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "cancel_subscription",
        "description": "取消一个订阅。需要订阅 ID",
        "parameters": {"type": "object", "properties": {
            "subscription_id": {"type": "string", "description": "订阅 ID，形如 I-XXXX"}},
            "required": ["subscription_id"]}}},
    {"type": "function", "function": {
        "name": "get_monthly_spend",
        "description": "统计本月订阅开销总额及分类占比",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "get_transactions",
        "description": "查询最近 N 天的扣款流水",
        "parameters": {"type": "object", "properties": {
            "days": {"type": "integer", "description": "回溯天数，默认 30"}},
            "required": []}}},
    {"type": "function", "function": {
        "name": "get_savings_suggestions",
        "description": "基于当前订阅给出省钱建议",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
]

# ---------------- 工具实现 ----------------

def _currency_of(items: list[dict], default: str = "USD") -> str:
    """从订阅/交易数据里推断币种（mock 数据是 CNY，真实沙盒多为 USD）。"""
    for it in items:
        if it.get("currency"):
            return it["currency"]
    return default


async def _list_subscriptions() -> dict:
    subs = await paypal_client.list_subscriptions()
    active = [s for s in subs if s["status"] == "ACTIVE"]
    return {"total": len(subs), "active": len(active), "subscriptions": subs}

async def _cancel_subscription(subscription_id: str) -> dict:
    return await paypal_client.cancel_subscription(subscription_id)

async def _get_monthly_spend() -> dict:
    subs = await paypal_client.list_subscriptions()
    active = [s for s in subs if s["status"] == "ACTIVE"]
    by_cat = defaultdict(float)
    total = 0.0
    for s in active:
        by_cat[s["category"]] += s["monthly_amount"]
        total += s["monthly_amount"]
    return {
        "currency": _currency_of(active),
        "monthly_total": round(total, 2),
        "active_count": len(active),
        "by_category": {k: round(v, 2) for k, v in sorted(by_cat.items(), key=lambda x: -x[1])},
    }

async def _get_transactions(days: int = 30) -> dict:
    txns = await paypal_client.get_transactions(days)
    total = round(sum(t["amount"] for t in txns), 2)
    return {"days": days, "total": total, "currency": _currency_of(txns), "count": len(txns), "transactions": txns}

async def _get_savings_suggestions() -> dict:
    subs = [s for s in await paypal_client.list_subscriptions() if s["status"] == "ACTIVE"]
    currency = _currency_of(subs)
    by_cat = defaultdict(list)
    for s in subs:
        by_cat[s["category"]].append(s)
    suggestions = []
    saving = 0.0
    for cat, items in by_cat.items():
        if cat == "订阅服务":
            continue  # 兜底分类无法判断是否同类竞品，不做重复付费推断，避免假建议
        if len(items) > 1:
            items.sort(key=lambda x: x["monthly_amount"])
            keep, dup = items[0], items[1:]
            for d in dup:
                saving += d["monthly_amount"]
                suggestions.append(
                    f"「{d['name']}」与「{keep['name']}」同属{cat}类，可考虑退掉「{d['name']}」，每月省 {_fmt_money(d['monthly_amount'], currency)}")

    # 闲置识别：对比近 90 天扣款流水，长期无扣款的月付订阅可能是闲置
    try:
        txns = await paypal_client.get_transactions(90)
    except Exception:
        txns = []
    if txns:
        from datetime import date, timedelta
        today = date.today()
        last_debit: dict[str, str] = {}
        for t in txns:
            tname = (t.get("name") or "").lower()
            if not tname:
                continue
            for s in subs:
                sname = s["name"].lower()
                if sname in tname or tname in sname:
                    if s["name"] not in last_debit or t["date"] > last_debit[s["name"]]:
                        last_debit[s["name"]] = t["date"]
        for s in subs:
            if s.get("billing_interval", "MONTH") != "MONTH":
                continue  # 非月付订阅没有月度扣款预期，不做闲置判断
            since = s.get("subscribed_since") or ""
            if since and since > (today - timedelta(days=60)).isoformat():
                continue  # 新订阅观察期
            last = last_debit.get(s["name"])
            idle_days = (today - date.fromisoformat(last)).days if last else 90
            if last is None or idle_days >= 45:
                saving += s["monthly_amount"]
                suggestions.append(
                    f"「{s['name']}」已 {idle_days} 天没有扣款记录，可能在闲置，退掉每月可省 {_fmt_money(s['monthly_amount'], currency)}")

    return {"potential_monthly_saving": round(saving, 2), "currency": currency,
            "suggestions": suggestions or ["当前订阅结构健康，没有明显的重复付费或闲置订阅。"]}

_TOOLS = {
    "list_subscriptions": _list_subscriptions,
    "cancel_subscription": _cancel_subscription,
    "get_monthly_spend": _get_monthly_spend,
    "get_transactions": _get_transactions,
    "get_savings_suggestions": _get_savings_suggestions,
}

# ---------------- LLM 驱动 ----------------

def _llm_ready() -> bool:
    return bool(LLM_API_KEY)

async def _llm_call(messages: list[dict]) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={"model": LLM_MODEL, "messages": messages, "tools": TOOLS_SPEC, "temperature": 0.3},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()

async def _run_llm(message: str, history: list[dict]) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history[-10:] + [{"role": "user", "content": message}]
    for _ in range(6):
        data = await _llm_call(messages)
        msg = data["choices"][0]["message"]
        if not msg.get("tool_calls"):
            return msg.get("content") or ""
        messages.append(msg)
        for tc in msg["tool_calls"]:
            fn = tc["function"]["name"]
            args = json.loads(tc["function"].get("arguments") or "{}")
            try:
                result = await _TOOLS[fn](**args)
            except Exception as e:  # 工具失败也回灌给模型，让它组织兜底话术
                result = {"error": str(e)}
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(result, ensure_ascii=False)})
    return "这个请求有点复杂，我处理超时了，请换个说法试试。"

# ---------------- 规则引擎兜底 ----------------

def _fmt_money(v: float, currency: str = "CNY") -> str:
    s = f"{v:,.2f}".rstrip("0").rstrip(".")
    return f"${s}" if currency == "USD" else f"{s} 元"

async def _run_fallback(message: str) -> str:
    subs = await paypal_client.list_subscriptions()
    active = [s for s in subs if s["status"] == "ACTIVE"]
    text = message.lower()

    if any(k in text for k in ("取消", "退订", "cancel")):
        target = None
        for s in active:
            for word in s["name"].lower().split() + [s["name"].lower()]:
                if word and word in text:
                    target = s
                    break
            if target:
                break
        if not target and len(active) == 1:
            target = active[0]
        if not target:
            names = "、".join(s["name"] for s in active)
            return f"想取消哪个订阅呢？当前生效的有：{names}。（也可以在右侧仪表盘直接点「取消」）"
        result = await paypal_client.cancel_subscription(target["id"])
        if result.get("ok"):
            return f"✅ 已取消「{target['name']}」（{target['id']}），之后不会再扣款了。每月为你省下 {_fmt_money(target['monthly_amount'], target.get('currency', 'USD'))}。"
        return f"取消失败：{result.get('error', '未知错误')}"

    if any(k in text for k in ("省", "建议", "优化", "重复")):
        sug = await _get_savings_suggestions()
        lines = [f"💰 预计每月可省 {_fmt_money(sug['potential_monthly_saving'], sug['currency'])}："] + \
                [f"· {s}" for s in sug["suggestions"]]
        return "\n".join(lines)

    if any(k in text for k in ("流水", "交易", "扣款记录", "最近")):
        tx = await _get_transactions(30)
        lines = [f"最近 30 天共 {tx['count']} 笔扣款，合计 {_fmt_money(tx['total'], tx['currency'])}："]
        lines += [f"· {t['date']}  {t['name']}  {_fmt_money(t['amount'], t['currency'])}" for t in tx["transactions"]]
        return "\n".join(lines)

    if any(k in text for k in ("多少", "花", "开销", "账单", "统计", "汇总", "spend")):
        spend = await _get_monthly_spend()
        lines = [f"本月订阅开销共 {_fmt_money(spend['monthly_total'], spend['currency'])}，生效订阅 {spend['active_count']} 个。分类如下："]
        lines += [f"· {k}：{_fmt_money(v, spend['currency'])}" for k, v in spend["by_category"].items()]
        return "\n".join(lines)

    if any(k in text for k in ("查", "列表", "都有什么", "有哪些", "订阅", "list")):
        lines = [f"你目前有 {len(active)} 个生效订阅："]
        lines += [f"· {s['name']}（{s['category']}）：{_fmt_money(s['monthly_amount'], s.get('currency', 'USD'))}/月，下次扣款 {s['next_billing_date'] or '-'}"
                  for s in active]
        return "\n".join(lines)

    return ("我是订阅管家，可以帮你：\n"
            "· 查订阅 ——「我有哪些订阅？」\n"
            "· 看开销 ——「这个月订阅花了多少？」\n"
            "· 管扣款 ——「最近扣款记录」\n"
            "· 取消订阅 ——「取消 Spotify」\n"
            "· 省钱建议 ——「怎么省钱？」")

# ---------------- 入口 ----------------

async def chat(message: str, history: list[dict] | None = None) -> dict:
    history = history or []
    if _llm_ready():
        try:
            reply = await _run_llm(message, history)
            return {"reply": reply, "engine": "llm"}
        except Exception:
            pass  # LLM 网络异常时静默降级到规则引擎，演示不中断
    return {"reply": await _run_fallback(message), "engine": "rules"}
