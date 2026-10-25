# 订阅管家 SubScribe Butler

> **PayPal AI Hackathon 参赛作品**（截止 2026-11-12）
> 用自然语言管理 PayPal 订阅：查订阅、算开销、取消退订、省钱建议。

一个 AI Agent 网页应用：左侧对话，右侧订阅仪表盘。用户说"这个月花了多少""取消 Spotify""怎么省钱"，Agent 调用 PayPal API 完成操作并给出汇总。

## 核心特性
- 💬 **自然语言 Agent**：基于 LLM function-calling（OpenAI 兼容接口），无 Key 时自动降级为内置规则引擎，离线也能完整演示
- 🔐 **PayPal 官方 API 集成**：OAuth2 客户端凭据流 + Subscriptions API + Transactions API（沙盒环境）
- 🧪 **零配置演示**：未配置任何凭据时使用 mock 数据运行，评审可直接体验
- 📊 **实时仪表盘**：月开销、分类占比、订阅卡片一键取消

## 快速开始
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload   # 打开 http://127.0.0.1:8000
python smoke_test.py            # 冒烟测试（mock 模式，无需任何凭据）
```

## 配置
复制 `.env.example` 为 `.env` 填入凭据（也可直接设置环境变量）：
- `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET`：PayPal 开发者平台 Sandbox 应用凭据（[创建入口](https://developer.paypal.com/dashboard/applications/sandbox)）
- `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`：任意 OpenAI 兼容大模型接口（可选）

## 使用的 PayPal 能力
| API | 用途 |
|---|---|
| OAuth2 `/v1/oauth2/token` | 客户端凭据授权 |
| Subscriptions `/v1/billing/subscriptions` | 订阅查询、取消 |
| Transactions `/v1/reporting/transactions` | 扣款流水与开销统计 |

## 架构
```
static/index.html      网页前端（聊天 + 仪表盘）
app/main.py            FastAPI 服务
app/agent.py           Agent：LLM 工具调用循环 + 规则引擎兜底
app/paypal_client.py   PayPal REST 客户端（沙盒/mock 双模式）
app/mock_data.py       演示数据
```

## Roadmap
- [ ] 省钱建议升级：按实际使用频率（交易数据）识别闲置订阅
- [ ] 邮件/消息推送：扣款前 3 天提醒
- [ ] 多币种支持
- [ ] 部署公开 Demo（Vercel/Railway）+ 演示视频
