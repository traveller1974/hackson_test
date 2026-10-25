"""SubScribe Butler —— 订阅管家 API 服务。"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import agent, paypal_client

app = FastAPI(title="SubScribe Butler", version="0.1.0")


class ChatIn(BaseModel):
    message: str
    history: list[dict] = []


@app.post("/api/chat")
async def chat(inp: ChatIn):
    result = await agent.chat(inp.message.strip(), inp.history)
    result["mode"] = paypal_client.mode()
    return result


@app.get("/api/subscriptions")
async def subscriptions():
    subs = await paypal_client.list_subscriptions()
    active = [s for s in subs if s["status"] == "ACTIVE"]
    currency = next((s["currency"] for s in active if s.get("currency")), "USD")
    return {
        "mode": paypal_client.mode(),
        "active_count": len(active),
        "monthly_total": round(sum(s["monthly_amount"] for s in active), 2),
        "currency": currency,
        "subscriptions": subs,
    }


@app.post("/api/cancel/{subscription_id}")
async def cancel(subscription_id: str):
    return await paypal_client.cancel_subscription(subscription_id)


@app.get("/")
async def index():
    return FileResponse(Path(__file__).parent.parent / "static" / "index.html")
