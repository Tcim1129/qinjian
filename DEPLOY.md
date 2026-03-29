# 部署指南

## 服务器信息

- 服务器IP: 129.212.216.187
- 域名: https://qinjian.tech
- 项目路径: /root/qinjian
- 用户: root

## 快速部署

### 方式一: 使用部署脚本

```bash
python deploy_current_workspace.py --host 129.212.216.187 --username root --password <密码>
```

脚本执行流程:
1. 检查服务器 /root/qinjian 目录
2. 打包 backend、web、配置文件
3. 上传到服务器
4. 执行 docker compose up -d --build

### 方式二: 手动部署

```bash
# SSH登录
ssh root@129.212.216.187

# 进入项目目录
cd /root/qinjian

# 拉取最新代码
git pull

# 重建并启动
docker compose up -d --build

# 查看状态
docker compose ps
```

## 环境配置

### 后端环境变量

在 /root/qinjian/backend/.env 中配置:

```bash
# 安全配置(必需)
SECRET_KEY=<32位以上随机字符串>

# 数据库连接
DATABASE_URL=postgresql+psycopg://qinjian:<密码>@db:5432/qinjian

# 前端域名
FRONTEND_ORIGIN=https://qinjian.tech

# AI服务(硅基流动)
AI_API_KEY=<硅基流动API Key>
AI_BASE_URL=https://api.siliconflow.cn/v1

# 语音识别(阿里云DashScope)
QWEN_ASR_API_KEY=<DashScope API Key>
ASR_PROVIDER=qwen3
REALTIME_ASR_PROVIDER=qwen3
```

### 模型配置

```bash
# 语音识别模型
QWEN_ASR_FILE_MODEL=qwen3-asr-flash
QWEN_ASR_REALTIME_MODEL=qwen3-asr-flash-realtime-2026-02-10

# 文本分析模型
AI_TEXT_MODEL=Pro/deepseek-ai/DeepSeek-V3.2

# 多模态模型
AI_MULTIMODAL_MODEL=moonshot/kimi-k2.5
```

## 服务管理

### 查看服务状态
```bash
cd /root/qinjian
docker compose ps
```

### 查看日志
```bash
# 所有服务日志
docker compose logs -f

# 仅后端日志
docker compose logs -f backend

# 最近100行日志
docker compose logs --tail=100 backend

# 实时追踪
docker compose logs -f --tail=50 backend
```

### 重启服务
```bash
# 重启所有服务
docker compose restart

# 仅重启后端
docker compose restart backend

# 仅重启数据库
docker compose restart db
```

### 停止服务
```bash
# 停止所有服务
docker compose down

# 停止并删除数据卷(危险操作)
docker compose down -v
```

## 健康检查

### 命令行检查
```bash
# 本地检查
curl http://localhost:8000/api/health

# 远程检查
curl https://qinjian.tech/api/health
```

### 浏览器检查
- Web界面: https://qinjian.tech
- 健康检查: https://qinjian.tech/api/health
- API文档: https://qinjian.tech/docs (需开启)

## 依赖管理

### 添加新依赖
```bash
# 本地添加
cd backend
pip install <package>
pip freeze > requirements.txt

# 服务器更新
cd /root/qinjian
docker compose exec backend pip install <package>

# 或重建容器
docker compose up -d --build backend
```

### 更新DashScope SDK
```bash
# 进入容器
docker compose exec backend bash

# 安装/更新
pip install dashscope --upgrade

# 或在服务器上直接执行
docker compose exec backend pip install dashscope --upgrade
```

## 数据库管理

### 数据库迁移
```bash
# 进入后端容器
docker compose exec backend bash

# 查看迁移状态
alembic current

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

### 数据库备份
```bash
# 导出数据
docker compose exec db pg_dump -U qinjian qinjian > backup.sql

# 导入数据
docker compose exec -T db psql -U qinjian qinjian < backup.sql
```

## 常见问题

### 1. 服务启动失败
```bash
# 检查日志
docker compose logs backend

# 常见原因:
# - .env 文件不存在或配置错误
# - 端口被占用
# - 数据库连接失败
# - 依赖未安装
```

### 2. API返回错误
```bash
# 检查后端日志
docker compose logs -f backend

# 检查环境变量
docker compose exec backend env | grep -E "AI_|QWEN_|SECRET_"

# 检查模型配置
docker compose exec backend env | grep MODEL
```

### 3. 语音识别失败
```bash
# 检查DashScope配置
docker compose exec backend env | grep QWEN

# 检查dashscope安装
docker compose exec backend pip show dashscope

# 查看错误日志
docker compose logs backend | grep -i asr
```

### 4. 前端缓存问题
```
# 浏览器强制刷新: Ctrl+Shift+R
# 或清除浏览器缓存后重新访问
```

### 5. 数据库连接失败
```bash
# 检查数据库状态
docker compose ps db

# 检查数据库日志
docker compose logs db

# 检查网络连接
docker compose exec backend ping db
```

## 安全配置

### 更新SECRET_KEY
```bash
# 生成新密钥
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 更新.env
SECRET_KEY=<新生成的密钥>

# 重启服务
docker compose restart backend
```

### 更新数据库密码
```bash
# 修改.env中的DATABASE_URL
# 同时修改db容器的POSTGRES_PASSWORD
docker compose down -v  # 注意: 会清空数据
docker compose up -d
```

## 监控与日志

### 日志轮转
日志自动轮转配置在 docker-compose.yml 中:
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 资源监控
```bash
# 查看容器资源使用
docker stats

# 查看磁盘使用
df -h

# 查看内存使用
free -h
```

## 版本更新

### 更新代码
```bash
cd /root/qinjian
git pull
docker compose up -d --build
```

### 回滚版本
```bash
# 查看提交历史
git log --oneline

# 回滚到指定版本
git checkout <commit-hash>
docker compose up -d --build

# 或使用标签
git checkout v1.0.0
docker compose up -d --build
```

## 联系方式

- 项目路径: /root/qinjian
- 服务器: root@129.212.216.187
- 域名: https://qinjian.tech
