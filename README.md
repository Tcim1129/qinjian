# 亲健

基于生成式 AI 的泛亲密关系智能感知与维系平台。

## 核心能力

- 多身份入口：支持账号密码、手机号验证码、资料更新与演示模式入口。
- 关系空间协作：支持创建邀请、加入预览、待确认加入请求、关系类型切换、备注名、关系树能量收集与解绑挽留留痕。
- 多模态记录与简报：围绕文字、图片、语音记录生成日报/周报/月报，并沉淀趋势回看。
- 智能陪伴与干预：提供助手会话、消息预演、双视角叙事对齐、修复协议、实时语音转写与会话记忆。
- 任务与回看：支持系统任务、手动任务、任务优先级、刷新冷却、反馈回收和时间轴归档。
- 多场景扩展：覆盖单人整理、朋友关系、异地关系、里程碑、关系体检、依恋类型、社群提示等延伸功能。
- 隐私与安全：内置隐私中心、删除申请、审计留痕、签名访问、上传归属校验、隐私运行时与基础安全响应头。
- 答辩演示友好：前端内置独立样例数据和 `demo` 入口，适合现场快速演示关系空间、简报、预演、修复、回看与隐私链路。

## 技术栈

- 前端：Vue 3 + Vite + Vue Router + Pinia
- 后端：FastAPI + SQLAlchemy + Pydantic v2
- 数据层：PostgreSQL / SQLite
- 部署：Docker Compose + Nginx

## 默认模型配置

| 功能 | 默认模型 | 服务商 |
| --- | --- | --- |
| 语音识别 | `qwen3-asr-flash` | 阿里云 DashScope |
| 实时语音 | `qwen3-asr-flash-realtime` | 阿里云 DashScope |
| 文本 / Agent | `deepseek-v4.1-flash` | 阿里云 MaaS 兼容网关 |
| 多模态 | `qwen3.7-plus-2026-05-26`，备用 `qwen3.7-plus` | 阿里云 MaaS 兼容网关 |

以上默认值与 [docker-compose.yml](docker-compose.yml)、[backend/app/core/config.py](backend/app/core/config.py)、[.env.example](.env.example) 保持一致，并允许通过环境变量覆盖。

## 目录结构

```text
qinjian/
├── backend/                    # FastAPI 后端与测试
│   ├── app/                    # 应用代码（API、模型、服务）
│   ├── alembic/                # 数据库迁移
│   └── tests/                  # 自动化测试
├── web-vue3/                   # Vue 3 前端源码
│   ├── src/                    # 页面、组件、状态管理
│   ├── public/                 # 静态资源（含演示入口）
│   └── dist/                   # Vite 构建产物（本地构建生成，不入库）
├── docker-compose.yml          # 容器编排
├── nginx.conf                  # Nginx 反向代理与安全响应头
└── .env.example                # Docker / 服务器环境变量模板
```

## 本地开发

### 1. 启动后端

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

### 2. 启动前端

```bash
cd web-vue3
npm install
npm run dev
```

默认前端开发地址为 `http://localhost:3001`。如需临时改用其他端口，可执行 `npm run dev -- --port 5173`。后端放行来源可在 `backend/.env` 中设置：

```bash
FRONTEND_ORIGIN=http://localhost:3001
ADDITIONAL_FRONTEND_ORIGINS=http://localhost:3000
```

### 3. 本地全栈容器运行

```bash
copy .env.example .env
cd web-vue3
npm install
npm run build
cd ..
docker compose up -d --build
```

启动后：

- Web：`http://localhost`
- API 健康检查：`http://localhost/api/health`

## 演示模式

项目内置了独立样例数据，适合答辩或汇报时避开真实账号与实时生成波动。

- 页面入口：`http://localhost:3001/preview-demo.html?route=/`
- 关系管理入口：`http://localhost:3001/preview-demo.html?route=/pair`
- 关系空间详情：`http://localhost:3001/preview-demo.html?route=/relationship-space/22222222-2222-4222-8222-222222222222`
- 指定页面直达：`http://localhost:3001/preview-demo.html?route=/report`
- 消息预演入口：`http://localhost:3001/preview-demo.html?route=/message-simulation`

演示模式会自动注入 `demo-mode` token 和样例关系数据，可直接展示关系空间、今日安排、简报、双视角、修复协议、时间轴归档与隐私安全页面。

## 工程验证

- 后端当前复核 `pytest -q` 为 `227/227` 条自动化测试通过。
- 前端工具层当前复核 `npm test` 为 `109/109` 自动化测试通过。
- 前端生产构建当前复核 `npm run build` 通过，可生成正式部署产物。

## 环境变量

### 根目录 `.env`

用于 Docker Compose 和服务器部署，模板见 [.env.example](.env.example)。

关键项：

```bash
DB_PASSWORD=your_secure_password_here
SECRET_KEY=your_random_secret_key_min_32_chars
FRONTEND_ORIGIN=https://your-domain.com
AI_API_KEY=
AI_BASE_URL=https://llm-ipplpz10dpd82u07.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
SILICONFLOW_API_KEY=
QWEN_ASR_API_KEY=
AI_TEXT_MODEL=deepseek-v4.1-flash
AI_TEXT_FALLBACK_MODEL=deepseek-v4.1-flash
AI_MULTIMODAL_MODEL=qwen3.7-plus-2026-05-26
AI_MULTIMODAL_FALLBACK_MODEL=qwen3.7-plus
QWEN_ASR_FILE_MODEL=qwen3-asr-flash
QWEN_ASR_REALTIME_MODEL=qwen3-asr-flash-realtime
```

### `backend/.env`

用于本地直接运行 FastAPI，模板见 [backend/.env.example](backend/.env.example)。

## 安全与隐私

- 上传目录默认不对公网直接暴露，Nginx 会拦截 `/uploads/` 直链访问。
- 本地上传文件通过签名访问接口发放短期访问地址，而不是裸露静态资源路径。
- Web 层默认附带基础安全响应头，包括 `X-Content-Type-Options`、`X-Frame-Options` 和 `Content-Security-Policy`。
- 隐私审计、删除申请与留存治理能力已经进入后端接口与测试链路。

## 系统边界

- 系统用于关系记录、风险提示和沟通辅助，不替代真实沟通。
- 模型输出属于辅助建议，不作为医疗、法律或心理诊断依据。
- 遇到高风险冲突、持续升级或安全顾虑时，应优先暂停冲突、联系可信支持网络，并转向专业帮助。

## 部署

使用 Docker Compose 一键运行全栈：

```bash
copy .env.example .env    # 填入 DB_PASSWORD、SECRET_KEY 与 AI API Key
cd web-vue3
npm install
npm run build
cd ..
docker compose up -d --build
```

启动后：

- Web：`http://localhost`
- API 健康检查：`http://localhost/api/health`

服务说明：PostgreSQL 提供数据存储，Redis 支撑验证码与登录风控，Nginx 挂载 `web-vue3/dist` 静态产物并代理 `/api` 到后端，配置见 [docker-compose.yml](docker-compose.yml) 与 [nginx.conf](nginx.conf)。
