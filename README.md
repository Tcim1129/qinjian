# 亲健 · 青年亲密关系健康管理平台

## 部署到 DigitalOcean（3分钟）

### 前置条件
- DigitalOcean Droplet（2C/4GB，学生有$200额度）
- 域名已在 Cloudflare 托管
- 硅基流动 API Key（[siliconflow.cn](https://siliconflow.cn) 注册获取）

### 步骤一：推送代码到 GitHub

在你的电脑上：
```bash
cd ~/Desktop/亲健
git init
git add .
git commit -m "亲健 MVP v1"

# 在 GitHub 创建私有仓库后：
git remote add origin git@github.com:你的用户名/qinjian.git
git push -u origin main
```

### 步骤二：在服务器上部署

SSH 登录你的 DO 服务器，然后执行：
```bash
# 克隆代码
git clone https://github.com/你的用户名/qinjian.git
cd qinjian

# 一键部署（自动安装Docker、配置环境变量、启动服务）
sudo bash deploy.sh
```

脚本会提示你输入 **硅基流动 API Key**，粘贴后回车即可。

### 步骤三：配置 Cloudflare

1. 进入 Cloudflare Dashboard → 你的域名
2. **DNS** → 添加记录：
   - 类型：`A`
   - 名称：`@`（或子域名如 `qinjian`）
   - IPv4：你的 DO 服务器 IP
   - 代理：**开启**（橙色云朵 ☁️）
3. **SSL/TLS** → 加密模式选 **Flexible**
4. 等待几分钟 DNS 生效

### 完成！🎉

- 访问 `https://你的域名` 即可进入亲健 Web 关系健康工作台
- API 文档在 `https://你的域名/api/health`

---

## 本地开发

### 后端
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 编辑填入你的 API Key
uvicorn app.main:app --reload --port 8000
```

### 前端
```bash
cd web
# 用浏览器直接打开 index.html
# 或 python -m http.server 3000
```

---

## 技术栈

当前 Web 登录页已支持两种认证方式：

- 邮箱注册 / 登录
- 手机号验证码登录（未注册手机号首次登录时自动创建账号）

| 层 | 技术 |
|---|------|
| 前端 | HTML / CSS / JS（移动端优先 Web 工作台） |
| 后端 | Python FastAPI + PostgreSQL |
| AI | 硅基流动 API（DeepSeek-V3 + Kimi K2.5 多模态） |
| 部署 | Docker Compose + Nginx + Cloudflare |

## 常用运维命令

```bash
# 查看所有服务状态
docker compose ps

# 查看实时日志
docker compose logs -f

# 只看后端日志
docker compose logs -f backend

# 重启
docker compose restart

# 更新代码后重新部署
git pull && docker compose up -d --build

# 停止所有服务
docker compose down

# 完全清理（包括数据库！慎用）
docker compose down -v
```

## 2026-03 Upgrade Notes

The project has moved beyond a simple "frontend + backend + API" stack and now includes a relationship intelligence layer with:

- Relationship event stream and timeline replay
- Relationship profile snapshots and intervention scorecards
- Adaptive task strategy, policy registry, and policy scheduling
- Seven-day playbook runtime with branch transitions
- Message simulation, narrative alignment, and repair protocols
- A dedicated timeline workspace with filters, branch overlay, and evidence drawer

Recent UX upgrades:

- The report page now acts like a relationship cockpit
- A dedicated timeline page can replay recent relationship events in order
- Clicking a timeline node opens an evidence drawer that explains why the system recorded it and what it affects next

Recommended next steps:

1. Add browser-level visual verification for the timeline page
2. Build a richer evidence detail panel backed by dedicated per-event API data
3. Build a stronger UI system layer for the report cockpit, timeline, and admin workbench

Latest timeline upgrade in this workspace:

- `GET /api/v1/insights/timeline/events/{event_id}` now returns per-event metrics, evidence cards, and current-context hints
- The timeline evidence drawer now loads detail asynchronously after node selection instead of relying only on local payload fallback
- The right-side drawer has been restyled into a richer evidence panel with loading state, context block, and source cards

Latest strategy upgrade in this workspace:

- `GET /api/v1/insights/plans/policy-audit` now exposes an event-backed decision audit snapshot
- The audit ties together current policy, recommended next policy, selection rule, schedule rule, recent decision trail, and supporting events
- The report page and timeline sidebar now surface the audit so policy changes are easier to explain during demos and reviews
- `web/index.html` script/style version params were refreshed so browsers pick up the new JS/CSS instead of stale cached assets

Latest admin rollout upgrade in this workspace:

- `GET /api/v1/admin/policies/{policy_id}/audit` now returns an event-backed release history for each strategy version
- `POST /api/v1/admin/policies/{policy_id}/rollback` can restore a selected historical snapshot while appending a new rollback event
- The policy workbench now has an audit view with field-level change cards, operator traceability, and one-click rollback

Latest competition-oriented upgrade in this workspace:

- `?demo=1` now opens a read-only Demo Mode that can walk judges through the fixed story path: report cockpit -> timeline -> message simulation -> narrative alignment -> repair protocol -> policy audit
- `GET /api/v1/insights/safety/status` now exposes a unified trust and safety summary with `risk_level`, evidence bullets, limitation notes, and handoff guidance
- `POST /api/v1/insights/assessments/weekly`, `GET /api/v1/insights/assessments/latest`, and `GET /api/v1/insights/assessments/trend` now turn the old frontend-only health test into an event-backed weekly assessment loop
- Report, timeline, and profile now share a more consistent “Hero / Evidence / Action” cockpit structure, making the project easier to demo as a coherent product instead of a collection of AI features
- Message simulation, repair protocol, and report surfaces now all expose the same trust-boundary explanation fields: evidence summary, limitation note, and safety handoff
