# 亲健 · 青年亲密关系健康管理平台

## 部署到服务器（快速上线）

### 前置条件
- 一台 Linux 服务器（2C/4GB 起步）
- 一个 OpenAI 兼容模型接口 Key（可用 SiliconFlow / OpenAI / 其他兼容网关）
- 可选：域名（后续再补 HTTPS）

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

# 一键部署（自动安装 Docker、配置环境变量、启动服务）
sudo bash deploy.sh
```

脚本会提示你输入：
- `AI_API_KEY`
- `AI_BASE_URL`（默认 `https://api.siliconflow.cn/v1`）

如果你暂时没有域名，也可以先直接用服务器 IP 跑通。

### 步骤三：可选配置域名与 HTTPS

推荐正式上线后再配置：
1. 域名解析到你的服务器 IP
2. Nginx 反向代理
3. Let's Encrypt 证书
4. `FRONTEND_ORIGIN` 改成正式域名

### 完成！🎉

- 临时访问：`http://你的服务器IP:8080`
- 健康检查：`http://你的服务器IP:8080/api/health`
- 正式域名上线后再切 HTTPS

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
|---|---|------|
| 前端 | HTML / CSS / JS（移动端优先 Web 工作台） |
| 后端 | Python FastAPI + PostgreSQL |
| AI | OpenAI 兼容模型网关（默认兼容 SiliconFlow） |
| 部署 | Docker Compose + Nginx |

## 界面截图

### 核心功能

| 首页 | 打卡页 | 报告页 |
|:---:|:---:|:---:|
| ![首页](screenshots/home.png) | ![打卡](screenshots/checkin.png) | ![报告](screenshots/report.png) |

| 发现页 | 个人中心 |
|:---:|:---:|
| ![发现](screenshots/discover.png) | ![个人中心](screenshots/profile.png) |

### 认证与测试

| 登录页 | 注册页 | 依恋测试 |
|:---:|:---:|:---:|
| ![登录](screenshots/auth-login.png) | ![注册](screenshots/auth-register.png) | ![依恋测试](screenshots/attachment-test.png) |

| 关系健康测试 |
|:---:|
| ![健康测试](screenshots/health-test.png) |

### 发现页功能

| 异地恋 | 社区 | 挑战赛 |
|:---:|:---:|:---:|
| ![异地恋](screenshots/longdistance.png) | ![社区](screenshots/community.png) | ![挑战赛](screenshots/challenges.png) |

| 课程 | 专家咨询 | 会员中心 |
|:---:|:---:|:---:|
| ![课程](screenshots/courses.png) | ![专家](screenshots/experts.png) | ![会员](screenshots/membership.png) |

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
