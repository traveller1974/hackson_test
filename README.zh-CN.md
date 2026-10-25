# 订阅管家 SubScribe Butler（中文说明）

> 用自然语言管理 PayPal 订阅的 AI Agent：查订阅、算开销、随时取消、智能省钱建议。
> 英文版说明见 [README.md](README.md)。

![Demo](docs/screenshots/demo.png)

## 核心特性
- 💬 **自然语言 Agent**：基于 LLM function-calling（OpenAI 兼容接口），无 Key 时自动降级为内置规则引擎，离线也能完整演示
- 🔐 **PayPal 官方 API 集成**：OAuth2 客户端凭据流 + Subscriptions API + Transactions API（沙盒环境）
- 🧪 **零配置演示**：未配置任何凭据时使用 mock 数据运行，评审可直接体验
- 📊 **实时仪表盘**：月开销环形图、订阅卡片一键取消，与对话实时联动
- 🛡 **演示级容错**：后台常驻刷新循环 + 缓存读取，PayPal 再慢界面也不白屏

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

想复现演示数据？`python seed_sandbox.py` 会在你自己的沙盒里创建三个示例订阅。

## 使用的 PayPal 能力
| API | 用途 |
|---|---|
| OAuth2 `/v1/oauth2/token` | 客户端凭据授权 |
| Subscriptions `/v1/billing/subscriptions` | 订阅查询、取消 |
| Catalog `/v1/catalogs/products`、`/v1/billing/plans` | 名称与价格解析 |
| Transactions `/v1/reporting/transactions` | 扣款流水与开销统计 |

## Roadmap
- [ ] 省钱建议升级：按实际使用频率（交易数据）识别闲置订阅
- [ ] 邮件/消息推送：扣款前 3 天提醒
- [ ] 多币种支持
- [x] 沙盒真实链路 + 演示数据一键补种
