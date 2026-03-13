#!/bin/bash
# 亲健自动部署脚本
# 在服务器上运行: sudo bash deploy.sh

set -e

PUBLIC_HOST="${PUBLIC_HOST:-$(hostname -I 2>/dev/null | awk '{print $1}') }"

echo "=========================================="
echo "  亲健 - 自动部署脚本"
echo "=========================================="

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then 
    echo "请使用 sudo 运行"
    exit 1
fi

# 安装 Docker
echo "[1/6] 安装 Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# 安装 Docker Compose
echo "[2/6] 安装 Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# 克隆代码
echo "[3/6] 下载代码..."
cd /opt
if [ -d "qinjian" ]; then
    cd qinjian
    git pull origin main
else
    git clone https://github.com/Tcim1129/qinjian.git
    cd qinjian
fi

# 配置环境
echo "[4/6] 配置环境..."
if [ ! -f "backend/.env" ]; then
    SECRET_KEY=$(openssl rand -hex 32)
    DB_PASSWORD=$(openssl rand -hex 16)
    read -r -p "请输入 OpenAI 兼容网关 API Key（留空则稍后手动填写）: " AI_API_KEY
    read -r -p "请输入 OpenAI 兼容网关 Base URL（默认 https://api.siliconflow.cn/v1）: " AI_BASE_URL
    AI_BASE_URL=${AI_BASE_URL:-https://api.siliconflow.cn/v1}
    cat > backend/.env << 'EOF'
SECRET_KEY=__SECRET_KEY__
DATABASE_URL=postgresql+psycopg://qinjian:__DB_PASSWORD__@db:5432/qinjian
AI_API_KEY=__AI_API_KEY__
AI_BASE_URL=__AI_BASE_URL__
SILICONFLOW_API_KEY=
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
AI_MULTIMODAL_MODEL=moonshot/kimi-k2.5
AI_TEXT_MODEL=deepseek-ai/DeepSeek-V3
EOF
    sed -i "s|__SECRET_KEY__|${SECRET_KEY}|g" backend/.env
    sed -i "s|__DB_PASSWORD__|${DB_PASSWORD}|g" backend/.env
    sed -i "s|__AI_API_KEY__|${AI_API_KEY}|g" backend/.env
    sed -i "s|__AI_BASE_URL__|${AI_BASE_URL}|g" backend/.env
fi

# 修改端口为 80
echo "[5/6] 配置端口..."
sed -i 's/"8080:80"/"80:80"/' docker-compose.yml

# 启动服务
echo "[6/6] 启动服务..."
docker-compose down 2>/dev/null || true
docker-compose up -d --build

# 等待就绪
echo "等待服务启动..."
sleep 10

# 检查状态
echo ""
echo "=========================================="
echo "  ✅ 部署完成！"
echo "=========================================="
echo ""
echo "  访问地址: http://${PUBLIC_HOST}"
echo ""
echo "  服务状态:"
docker-compose ps
echo ""
echo "  查看日志:"
echo "    cd /opt/qinjian && docker-compose logs -f"
echo ""
