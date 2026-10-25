# 部署指南（公开 Demo）

目标：11-09~11-10 前把应用部署成一个公网可访问的演示链接，填进 Devpost 的 Demo site。
**最省事的选择是 Railway**——从 GitHub 仓库直接部署，不需要 Docker 知识，环境变量可全部留空。

## 方案 A：Railway（推荐，约 10 分钟）

1. 打开 https://railway.com → 用 GitHub 账号登录（traveller1974）
2. **New Project → Deploy from GitHub repo** → 选 `traveller1974/hackson_test`
3. Railway 会自动识别 Python 项目；若没有自动识别，Settings 里手动设：
   - Start Command：`uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. **Settings → Networking → Generate Domain**，得到形如 `https://hackson-test.up.railway.app` 的公网地址
5. （可选）Variables 页添加 `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET`，接真实沙盒；
   **什么都不加也能跑**——应用自动进入 mock 演示模式，评委打开即可玩
6. 打开公网地址，冒烟验证：右上角徽章显示「演示数据模式」或「PayPal Sandbox 已连接」，仪表盘有数据

## 方案 B：Docker（任意平台）

```bash
docker build -t subscribe-butler .
docker run -p 8000:8000 subscribe-butler
# 可选：-e PAYPAL_CLIENT_ID=... -e PAYPAL_CLIENT_SECRET=...
```

## 注意事项

- **密钥安全**：凭据只放在部署平台的环境变量里，永远不要写进仓库（.gitignore 已拦截 .env）
- **沙盒 vs 生产**：演示必须用 Sandbox（`PAYPAL_API_BASE` 默认值即是），生产环境需要另行申请
- **免费额度**：Railway 免费额度足够跑完整个赛期；比赛结束后可删除服务
- 提交 Devpost 时把公网链接填到 Additional info 的 Demo site 一栏
