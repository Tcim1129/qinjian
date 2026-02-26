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

- 访问 `https://你的域名` 即可看到亲健登录页
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

| 层 | 技术 |
|---|------|
| 前端 | HTML / CSS / JS（Web 原型） |
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
