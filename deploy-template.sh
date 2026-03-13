#!/bin/bash
# 亲健部署脚本模板
# ⚠️ 重要：使用前请将 API Key 等敏感信息填入 .env 文件，不要硬编码在此脚本中

set -e

echo "=== 亲健部署脚本 ==="

# 检查 .env 文件是否存在
if [ ! -f .env ]; then
    echo "❌ 错误：.env 文件不存在"
    echo "请创建 .env 文件并填入以下配置："
    echo ""
    echo "DB_PASSWORD=你的数据库密码"
    echo "SECRET_KEY=你的密钥（随机字符串）"
    echo "SILICONFLOW_API_KEY=sk-你的硅基流动API密钥"
    echo "WECHAT_APPID=你的微信小程序AppID（可选）"
    echo "WECHAT_SECRET=你的微信小程序Secret（可选）"
    exit 1
fi

# 加载环境变量
export $(grep -v '^#' .env | xargs)

# 检查必需的环境变量
if [ -z "$SILICONFLOW_API_KEY" ]; then
    echo "❌ 错误：SILICONFLOW_API_KEY 未设置"
    exit 1
fi

echo "✓ 环境变量加载成功"

# 配置 Docker 镜像源（中国大陆服务器）
if [ ! -f /etc/docker/daemon.json ]; then
    echo "=== 配置 Docker 国内镜像源 ==="
    sudo mkdir -p /etc/docker
    sudo tee /etc/docker/daemon.json > /dev/null <<'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.sjtug.sjtu.edu.cn",
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}
EOF
    sudo systemctl restart docker
    echo "✓ Docker 镜像源配置完成"
fi

# 拉取最新代码
echo "=== 拉取最新代码 ==="
git pull origin main

# 部署
echo "=== 启动服务 ==="
docker compose down
docker compose up -d --build

# 数据库迁移
echo "=== 执行数据库迁移 ==="
sleep 5
docker compose exec backend alembic upgrade head

echo ""
echo "✅ 部署完成！"
echo ""
echo "访问地址："
echo "  - 前端：http://你的服务器IP:8080"
echo "  - API：http://你的服务器IP:8080/api/health"
echo ""
echo "查看日志：docker compose logs -f"
