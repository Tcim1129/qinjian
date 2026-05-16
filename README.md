# 亲健 - 青年亲密关系健康管理平台

## 技术架构

### 后端框架
- FastAPI 0.135.1 + Uvicorn 0.30.0
- SQLAlchemy 2.0 (异步ORM)
- PostgreSQL / SQLite
- Pydantic v2 数据验证
- JWT认证

### AI服务配置
| 功能 | 模型 | 服务商 |
|------|------|--------|
| 语音识别 | qwen3-asr-flash | 阿里云DashScope |
| 实时语音 | qwen3-asr-flash-realtime-2026-02-10 | 阿里云DashScope |
| 文本分析 | Pro/deepseek-ai/DeepSeek-V3.2 | 硅基流动 |
| 多模态 | moonshot/kimi-k2.5 | 硅基流动 |

### 前端
- HTML5 / CSS3 / JavaScript
- 移动端优先响应式设计
- 无框架原生实现

### 部署架构
- Docker Compose容器化
- Nginx反向代理
- Cloudflare CDN加速

## 目录结构

```
qinjian/
├── backend/
│   ├── app/
│   │   ├── api/v1/           # API路由模块
│   │   │   ├── auth.py       # 认证接口
│   │   │   ├── pairs.py      # 配对接口
│   │   │   ├── checkins.py   # 打卡接口
│   │   │   ├── reports.py    # 报告接口
│   │   │   ├── upload.py     # 文件上传
│   │   │   ├── agent.py      # AI对话
│   │   │   └── ws.py         # WebSocket
│   │   ├── core/
│   │   │   ├── config.py     # 配置管理
│   │   │   ├── security.py   # 安全模块
│   │   │   └── database.py   # 数据库连接
│   │   ├── models/           # SQLAlchemy模型
│   │   ├── schemas/          # Pydantic模型
│   │   ├── services/         # 业务逻辑层
│   │   └── ai/
│   │       ├── asr.py        # 语音识别
│   │       ├── reporter.py   # 报告生成
│   │       └── __init__.py   # AI服务入口
│   ├── alembic/              # 数据库迁移
│   ├── tests/                # 测试用例
│   └── requirements.txt      # Python依赖
├── web/
│   ├── index.html            # 主页面
│   ├── js/
│   │   ├── app.js            # 主逻辑
│   │   └── api.js            # API调用
│   └── css/
│       └── style.css         # 样式
├── docker-compose.yml        # 容器编排
├── nginx.conf                # Nginx配置
└── deploy.sh                 # 部署脚本
```

## 核心模块说明

### 1. 认证模块 (app/api/v1/auth.py)
- 邮箱注册/登录
- 手机号验证码登录
- JWT Token生成与验证
- 密码加密存储

### 2. 配对模块 (app/api/v1/pairs.py)
- 创建关系配对
- 生成邀请码
- 配对绑定/解绑
- 配对状态管理

### 3. 打卡模块 (app/api/v1/checkins.py)
- 每日打卡提交
- 情绪标签记录
- 互动频率统计
- 后台情感分析

### 4. 报告模块 (app/api/v1/reports.py)
- 日报/周报生成
- AI情感分析
- 关系健康评分
- 趋势分析

### 5. 语音模块 (app/ai/asr.py)
- 语音文件上传转写
- 实时语音流识别
- 支持DashScope和讯飞两种Provider

### 6. AI服务 (app/ai/__init__.py)
- chat_completion(): 文本对话
- analyze_sentiment(): 情感分析
- transcribe_audio(): 语音转文字

### 7. 智能对话 (app/api/v1/agent.py)
- AI伴侣对话
- 情绪引导
- 打卡信息提取

## 本地开发

### 环境要求
- Python 3.11+
- PostgreSQL 15+ (可选,默认SQLite)

### 后端启动
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### 前端启动
```bash
cd web
python -m http.server 3000
# 或直接用浏览器打开 index.html
```

## 配置说明

### 必需环境变量
```bash
# 安全配置
SECRET_KEY=your-secret-key-min-32-chars

# 数据库
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/qinjian

# 前端域名
FRONTEND_ORIGIN=https://your-domain.com

# AI服务
AI_API_KEY=your-api-key
AI_BASE_URL=https://api.siliconflow.cn/v1

# 语音识别
QWEN_ASR_API_KEY=your-dashscope-key
ASR_PROVIDER=qwen3
```

### 模型配置
```bash
# 语音模型
QWEN_ASR_FILE_MODEL=qwen3-asr-flash
QWEN_ASR_REALTIME_MODEL=qwen3-asr-flash-realtime-2026-02-10

# 文本模型
AI_TEXT_MODEL=Pro/deepseek-ai/DeepSeek-V3.2
AI_MULTIMODAL_MODEL=moonshot/kimi-k2.5
```

## 部署说明

### 服务器路径
项目统一部署到: /root/qinjian

### 部署方式
```bash
# 方式一: 使用部署脚本
python deploy_current_workspace.py --host <ip> --username root --password <pwd>

# 方式二: 手动部署
ssh root@<server>
cd /root/qinjian
git pull
docker compose up -d --build
```

### 服务管理
```bash
cd /root/qinjian

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f backend

# 重启服务
docker compose restart

# 停止服务
docker compose down
```

## API文档

启动后访问:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/api/health

## 测试

```bash
cd backend

# 运行所有测试
pytest tests/ -v

# 运行情感分析测试
pytest tests/test_sentiment.py -v

# 运行安全测试
pytest tests/test_auth_security.py -v
```

## 运维命令

```bash
# 查看服务状态
docker compose ps

# 实时日志
docker compose logs -f backend

# 重启后端
docker compose restart backend

# 更新部署
git pull && docker compose up -d --build

# 进入容器
docker compose exec backend bash

# 数据库迁移
docker compose exec backend alembic upgrade head
```

## 版本信息

- 版本: 2026.03
- Python: 3.11+
- FastAPI: 0.135.1
- 最后更新: 2026-03-29
