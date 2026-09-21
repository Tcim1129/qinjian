# 部署指南

## 服务器信息

### 当前线上服务器（qinjian.tech）
- 服务器 IP：`52.140.193.23`
- 访问地址：`https://qinjian.tech/`
- 项目目录：`/home/azureuser/qinjian`
- 登录用户：`azureuser`

### 旧服务器记录
- 服务器 IP：`129.212.216.187`
- 项目目录：`/root/qinjian`
- 登录用户：`root`

> `qinjian.tech` 当前解析并提供页面的是 `52.140.193.23`。`129.212.216.187` 保留作旧记录，不作为当前网站的发布目标。部署前先以域名页面和 `/api/health` 的实际响应为准。

## 快速部署

### 方式一：部署到当前线上服务器 (52.140.193.23)

```bash
python deploy_current_workspace.py --host 52.140.193.23 --username azureuser --remote-root /home/azureuser/qinjian
```

> 密码不要写进仓库或文档，优先使用 `QJ_REMOTE_PASSWORD` 环境变量，或改用 `--key-file` 指定 SSH 私钥。

脚本会自动：

1. 在本地构建 `web-vue3/dist`
2. 打包 `backend`、`web-vue3`、`docker-compose.yml`、`nginx.conf`
3. 上传到服务器 `/home/azureuser/qinjian`
4. 校正 `FRONTEND_ORIGIN`
5. 执行 `docker compose up -d --build`

### 方式二：手动部署

```bash
cd web-vue3
npm install
npm run build

ssh azureuser@52.140.193.23
cd /home/azureuser/qinjian
git pull
docker compose up -d --build
docker compose ps
```

## 服务器环境变量

在 `/home/azureuser/qinjian/.env` 中至少配置：

```bash
DB_PASSWORD=<数据库密码>
SECRET_KEY=<32位以上随机字符串>
FRONTEND_ORIGIN=https://qinjian.tech

AI_API_KEY=
AI_BASE_URL=
SILICONFLOW_API_KEY=<可选，兼容旧配置>
QWEN_ASR_API_KEY=<DashScope API Key>

ASR_PROVIDER=qwen3
REALTIME_ASR_PROVIDER=qwen3
REALTIME_ASR_MAX_SESSION_SECONDS=60
QWEN_ASR_FILE_MODEL=qwen3-asr-flash
QWEN_ASR_REALTIME_MODEL=qwen3-asr-flash-realtime
AI_TEXT_MODEL=Pro/deepseek-ai/DeepSeek-V3.2
AI_MULTIMODAL_MODEL=moonshot/kimi-k2.6
PHONE_CODE_STORE=redis
REDIS_URL=redis://redis:6379/0
```

推荐直接从根目录 [.env.example](.env.example) 复制生成。

## 服务管理

```bash
cd /home/azureuser/qinjian

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f
docker compose logs -f backend

# 重启
docker compose restart
docker compose restart backend

# 停止
docker compose down
```

## 健康检查

```bash
curl https://qinjian.tech/api/health
```

浏览器检查：

- Web：`https://qinjian.tech`
- 健康检查：`https://qinjian.tech/api/health`

## 说明

- Web 服务挂载的是 `web-vue3/dist`，不再使用旧 `web/` 静态前端目录。
- 上传文件默认不通过 Nginx 直接公开，需走后端签名访问接口。
- 生产环境默认通过 Compose 内置 Redis 承接验证码和登录风控，不再允许回退到内存。
- 如需本地调试 API 文档，可通过后端环境变量开启 `ENABLE_API_DOCS=true`。
- 软件功能和主要接口见 [设计说明书](docs/copyright/设计说明书.md)。
