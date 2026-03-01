#!/bin/bash
# 亲健自动部署脚本 - 在服务器上执行

set -e

echo "🚀 亲健项目自动部署"
echo "===================="
echo ""

cd /opt/qinjian

echo "[1/5] 拉取最新代码..."
git pull origin main

echo ""
echo "[2/5] 停止现有服务..."
docker-compose down 2>/dev/null || true

echo ""
echo "[3/5] 构建并启动服务..."
docker-compose up -d --build

echo ""
echo "[4/5] 等待服务启动 (15秒)..."
sleep 15

echo ""
echo "[5/5] 检查服务状态..."
docker-compose ps

echo ""
echo "后端日志 (最近30行):"
docker-compose logs --tail=30 backend 2>/dev/null || echo "暂无日志"

echo ""
echo "===================="
echo "✅ 部署完成！"
echo "===================="
echo ""
echo "访问地址:"
echo "  Web: http://143.198.110.145:8080"
echo "  API: http://143.198.110.145:8080/api/health"
echo ""
echo "查看日志: cd /opt/qinjian && docker-compose logs -f"
