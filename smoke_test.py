"""冒烟测试：无外部凭据（mock 模式）下验证核心链路。运行：python smoke_test.py"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 本测试断言的是 mock 数据，导入后强制客户端进入 mock 模式（.env 里有沙盒凭据也不影响）
from fastapi.testclient import TestClient

from app import paypal_client
from app.main import app

paypal_client.CLIENT_ID = ""
paypal_client.CLIENT_SECRET = ""

client = TestClient(app)
failures = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f"  -> {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


# 1. 首页可访问
r = client.get("/")
check("GET / 返回页面", r.status_code == 200 and "SubScribe Butler" in r.text)

# 2. 订阅列表
r = client.get("/api/subscriptions")
subs = r.json()
check("GET /api/subscriptions", r.status_code == 200 and subs["active_count"] >= 5,
      f"active={subs.get('active_count')}")
ACTIVE_BEFORE = subs["active_count"]

# 3. 对话：查开销
r = client.post("/api/chat", json={"message": "这个月订阅花了多少？"})
reply = r.json()["reply"]
check("对话-查开销", r.status_code == 200 and "开销" in reply and "分类" in reply, reply)

# 4. 对话：列订阅
r = client.post("/api/chat", json={"message": "我有哪些订阅？"})
reply = r.json()["reply"]
check("对话-列订阅", "Netflix" in reply and "Spotify" in reply, reply)

# 5. 对话：省钱建议
r = client.post("/api/chat", json={"message": "怎么帮我省钱？"})
reply = r.json()["reply"]
check("对话-省钱建议", "省" in reply and ("视频娱乐" in reply or "AI" in reply), reply)

# 6. 对话：取消订阅
r = client.post("/api/chat", json={"message": "帮我取消 iQIYI 黄金会员"})
data = r.json()
reply = data["reply"]
check("对话-取消订阅", "已取消" in reply and "省下" in reply, reply)

# 7. 取消后列表联动
r = client.get("/api/subscriptions")
check("取消后状态联动", r.json()["active_count"] == ACTIVE_BEFORE - 1)

# 8. 取消不存在的订阅有兜底话术
r = client.post("/api/chat", json={"message": "帮我取消不存在的东西99"})
check("对话-兜底", "取消失败" in r.json()["reply"] or "哪个" in r.json()["reply"], r.json()["reply"])

# 9. 取消接口幂等保护
r = client.post("/api/cancel/I-5QX41LMK2P")
check("重复取消有提示", r.json()["ok"] is False)

print("\n" + ("全部通过 ✅" if not failures else f"失败 {len(failures)} 项：{failures}"))
sys.exit(1 if failures else 0)
