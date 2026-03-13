# 亲健 - 部署指南

## 📋 前置要求

- Docker & Docker Compose
- 服务器：2核4GB内存（最低配置）
- 域名（可选，用于HTTPS）
- 一个 OpenAI 兼容接口的 API Key（可用 SiliconFlow / OpenAI / 其他兼容网关）

## 🔧 环境准备

### 1. 克隆代码

```bash
git clone https://github.com/Tcim1129/qinjian.git
cd qinjian
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp backend/.env.example backend/.env

# 编辑 .env 文件，填入你的配置
nano backend/.env
```

**必需配置**:
- `AI_API_KEY`: 你的模型网关 API Key
- `AI_BASE_URL`: 模型网关地址；默认可用 `https://api.siliconflow.cn/v1`
- `SECRET_KEY`: 随机密钥（生产环境必须修改）
- `FRONTEND_ORIGIN`: 你的正式前端域名，例如 `https://app.example.com`

### 3. 修改端口（可选）

编辑 `docker compose.yml`，将 `8080` 改为你想要的端口：
```yaml
ports:
  - "80:80"  # 或 "8080:80"
```

## 🚀 部署步骤

### 方式一：快速部署（本地测试）

```bash
# 启动所有服务
docker compose up -d

# 查看日志
docker compose logs -f

# 停止服务
docker compose down
```

访问 http://localhost:8080

### 方式二：生产部署（Linux服务器）

```bash
# 1. 进入项目目录
cd qinjian

# 2. 后台启动
docker compose up -d

# 3. 检查状态
docker compose ps

# 4. 查看日志
docker compose logs -f backend
```

### 方式三：使用 Nginx 反向代理（推荐生产环境）

1. 安装 Nginx:
```bash
sudo apt update
sudo apt install nginx
```

2. 创建 Nginx 配置文件:
```bash
sudo nano /etc/nginx/sites-available/qinjian
```

3. 添加配置:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

4. 启用配置:
```bash
sudo ln -s /etc/nginx/sites-available/qinjian /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 🔐 HTTPS 配置（Let's Encrypt）

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期测试
sudo certbot renew --dry-run
```

## 📊 数据库迁移

如果需要迁移数据库（添加新字段后）：

```bash
# 进入后端容器
docker compose exec backend bash

# 进入项目目录
cd /app

# 创建迁移
alembic revision --autogenerate -m "add new fields"

# 执行迁移
alembic upgrade head
```

## 🔍 常见问题

### 1. 端口被占用

```bash
# 查看端口占用
sudo lsof -i :8080

# 修改 docker compose.yml 中的端口映射
```

### 2. 内存不足

```bash
# 查看容器内存使用
docker stats

# 调整 docker compose.yml 中的 memory 限制
```

### 3. 数据库连接失败

```bash
# 检查数据库容器
docker compose logs db

# 重启服务
docker compose restart
```

### 4. AI 接口报错

- 检查 `AI_API_KEY` / `AI_BASE_URL` 是否正确
- 检查对应模型服务是否可用、账户是否有额度
- 查看后端日志: `docker compose logs backend`

## 📝 更新代码

```bash
# 拉取最新代码
git pull origin main

# 重启服务
docker compose down
docker compose up -d --build
```

## 🗄️ 备份数据

```bash
# 备份数据库
docker compose exec db pg_dump -U qinjian qinjian > backup.sql

# 备份上传文件
tar -czvf uploads_backup.tar.gz uploads/
```

## 📈 监控

```bash
# 查看实时日志
docker compose logs -f

# 查看资源使用
docker stats

# 查看容器状态
docker compose ps
```

## 🆘 故障排查

```bash
# 重启所有服务
docker compose restart

# 完全重置（会丢失数据！）
docker compose down -v
docker compose up -d

# 查看后端详细日志
docker compose logs --tail=100 backend
```

## 🎯 验证部署

1. 访问首页应该能看到登录界面
2. 注册新账号
3. 创建配对，测试邀请码（或以单人模式进入）
4. 测试打卡功能
5. 查看 AI 生成的报告
6. 测试发现页子模块（异地模式、关系体检、会员方案等）

## 📞 联系支持

如有问题，请查看 GitHub Issues 或联系开发者。
