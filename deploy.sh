#!/bin/bash
# ═══════════════════════════════════════════
# 亲健 · DigitalOcean 一键部署脚本
# 适用于：Ubuntu 22.04+ / Debian 12+
# 服务器：2C/4GB DigitalOcean Droplet
# ═══════════════════════════════════════════

set -e

echo "🚀 亲健平台部署脚本"
echo "════════════════════"

# ── 1. 检查运行环境 ──
if [ "$(id -u)" -ne 0 ]; then
    echo "⚠️  请使用 root 用户运行: sudo bash deploy.sh"
    exit 1
fi

# ── 2. 安装 Docker ──
if ! command -v docker &>/dev/null; then
    echo "📦 安装 Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "✅ Docker 安装完成"
else
    echo "✅ Docker 已安装"
fi

# ── 3. 安装 Docker Compose ──
if ! docker compose version &>/dev/null; then
    echo "📦 安装 Docker Compose 插件..."
    apt-get update && apt-get install -y docker-compose-plugin
    echo "✅ Docker Compose 安装完成"
else
    echo "✅ Docker Compose 已安装"
fi

# ── 4. 设置环境变量 ──
ENV_FILE=".env"

if [ ! -f "$ENV_FILE" ]; then
    echo ""
    echo "⚙️  首次部署，需要配置环境变量"
    echo ""

    # 生成随机密钥
    SECRET_KEY=$(openssl rand -hex 32)
    DB_PASSWORD=$(openssl rand -hex 16)

    # 询问硅基流动 API Key
    read -p "🔑 请输入硅基流动 API Key (sk-...): " SILICONFLOW_API_KEY
    if [ -z "$SILICONFLOW_API_KEY" ]; then
        echo "⚠️  未输入 API Key，AI 功能将不可用"
        SILICONFLOW_API_KEY="sk-placeholder"
    fi

    # 写入 .env 文件
    cat > "$ENV_FILE" << EOF
# 亲健 生产环境配置
# 生成于: $(date)

SECRET_KEY=${SECRET_KEY}
DB_PASSWORD=${DB_PASSWORD}
SILICONFLOW_API_KEY=${SILICONFLOW_API_KEY}

# AI 模型（可按需修改）
AI_MULTIMODAL_MODEL=moonshot/kimi-k2.5
AI_TEXT_MODEL=deepseek-ai/DeepSeek-V3
EOF

    echo "✅ 环境变量已保存到 .env"
    echo "   SECRET_KEY: ${SECRET_KEY:0:8}..."
    echo "   DB_PASSWORD: ${DB_PASSWORD:0:8}..."
else
    echo "✅ .env 文件已存在"
    source "$ENV_FILE"
fi

# ── 5. 构建并启动 ──
echo ""
echo "🔨 构建镜像并启动服务..."
docker compose up -d --build

echo ""
echo "⏳ 等待服务启动..."
sleep 5

# ── 6. 健康检查 ──
echo ""
echo "🏥 健康检查..."

for i in {1..10}; do
    if curl -s http://localhost/api/health | grep -q "ok"; then
        echo "✅ API 服务正常"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "⚠️  API 暂未就绪，请手动检查: docker compose logs backend"
    fi
    sleep 2
done

if curl -s -o /dev/null -w "%{http_code}" http://localhost/ | grep -q "200"; then
    echo "✅ Web 前端正常"
else
    echo "⚠️  Web 暂未就绪，请等待或检查: docker compose logs web"
fi

# ── 7. 完成 ──
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")

echo ""
echo "════════════════════════════════════════"
echo "🎉 亲健平台部署完成！"
echo "════════════════════════════════════════"
echo ""
echo "📱 访问地址："
echo "   Web 前端: http://${SERVER_IP}"
echo "   API 文档: http://${SERVER_IP}/api/health"
echo ""
echo "📝 Cloudflare 配置步骤："
echo "   1. 添加 A 记录: 你的域名 → ${SERVER_IP}"
echo "   2. 打开代理（橙色云朵 ☁️）"
echo "   3. SSL/TLS → 选择 Flexible"
echo "   4. 等待 DNS 生效（通常几分钟）"
echo ""
echo "🔧 常用命令："
echo "   查看日志:  docker compose logs -f"
echo "   重启服务:  docker compose restart"
echo "   停止服务:  docker compose down"
echo "   更新代码:  git pull && docker compose up -d --build"
echo ""
