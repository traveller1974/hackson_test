# Devpost 投稿文案（PayPal AI Hackathon）

> 对应 Devpost 草稿剩余 4 步。英文为可直接粘贴的正式文案，中文只是给你看的说明。
> 草稿随时可改，**最终 Submit 按计划 11-11 再点**（留 1 天缓冲）。当前进度：1/5（Manage team ✅）。

## 第 2 步：Project overview 项目概述（现在就能填完）

### Project title 项目名
```
SubScribe Butler
```
> 草稿现在叫"Untitled"，第一件事就是改成这个。

### Elevator pitch 一句话简介（限 140 字符）
```
Manage your PayPal subscriptions by chatting: check spending, cancel anytime, get smart money-saving tips.
```

### Cover image / 关键词（如表单要求）
- 关键词标签：AI Agent, PayPal API, Subscriptions, LLM, Chatbot, Personal Finance
- 封面图：等 11-03~11-08 做完仪表盘美化后截图，暂可跳过

## 第 3 步：Project details 项目详情（文字部分现在就能填）

### Inspiration 灵感来源
```
Subscription fatigue is real. People juggle a dozen recurring charges and consistently underestimate what they cost — cancelling is buried in merchant sites or deep menus. We wanted one chat window where anyone can ask "what am I paying for?", "cancel Spotify", or "how do I save money?" — and have it actually done through PayPal's official APIs.
```

### What it does 做了什么
```
SubScribe Butler is an AI-agent web app: a chat panel on the left, a live subscription dashboard on the right. You talk to it in plain language — "how much did I spend this month?", "cancel my video subscription", "where can I cut costs?" The agent understands the intent, calls PayPal APIs (Subscriptions + Transactions) via function calling, executes the action, and updates the dashboard in real time: monthly spend, category breakdown, and one-click cancel on every subscription card.
```

### How we built it 怎么做的
```
- Backend: Python + FastAPI, with an agent loop built on LLM function calling (any OpenAI-compatible endpoint). When no LLM key is configured, a built-in rule engine takes over, so the demo never breaks.
- PayPal integration: a REST client covering OAuth2 client-credentials, the Subscriptions API (list / cancel) and the Transactions API (spend aggregation). It runs against the PayPal sandbox, and falls back to realistic mock data when no credentials are set — judges can try it with zero setup.
- Frontend: single-page chat + dashboard, no framework, instant load.
```

### Challenges we ran into 遇到的挑战
```
Mapping fuzzy human requests ("I don't watch that show anymore") onto precise API calls; keeping the agent useful when the LLM or PayPal credentials are unavailable (solved with layered fallbacks); presenting subscription lifecycle states in a UI that stays honest about what was really cancelled.
```

### Accomplishments 我们引以为傲的
```
The full loop works end-to-end: natural language → agent decision → real PayPal sandbox API call → visible dashboard update. And it passes our smoke tests with zero configuration, which means anyone can run it in under a minute.
```

### What we learned 学到了什么
```
The PayPal API family (OAuth2 flows, Subscriptions lifecycle, transaction reporting), and how to design an agent that degrades gracefully instead of failing hard when dependencies are missing.
```

### What's next 下一步
```
Idle-subscription detection from actual transaction history ("you haven't used it in 3 months"), pre-debit reminders 3 days before renewal, multi-currency support, and a hosted public demo.
```

## 第 4 步：Additional info 附加信息（部分要等仓库/部署/视频）

### Built with 技术栈标签
```
python, fastapi, paypal-api, oauth2, llm, function-calling, javascript, html, css
```

### 链接类（占位，齐了再填）
- [ ] GitHub repository → **等你建仓库**
- [ ] Demo site → 计划 11-09~11-10 部署 Vercel/Railway
- [ ] Demo video → 计划 11-09~11-10 录制（≤3 分钟，英文或双语字幕）
- [ ] "Did you use PayPal API?" 之类勾选题 → 答 Yes，列 OAuth2 / Subscriptions / Transactions

## 第 5 步：Submit（11-11 再点）

提交前最后核对：
- [ ] Project name 不是 Untitled，pitch 已填
- [ ] GitHub 仓库公开、README 完整
- [ ] Demo 链接或视频至少一个能用
- [ ] Preview 预览版检查一遍排版
- [ ] 点 Submit 后截图存档
