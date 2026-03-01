#!/bin/bash

echo "=========================================="
echo "  亲健 - 本地测试启动脚本"
echo "=========================================="
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "[错误] Docker 未安装，请先安装 Docker"
    echo "Linux 安装指南: https://docs.docker.com/engine/install/"
    echo "macOS 下载地址: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# 检查 .env 文件是否存在
if [ ! -f "backend/.env" ]; then
    echo "[提示] 未找到 backend/.env 文件，正在创建..."
    cp "backend/.env.example" "backend/.env"
    echo ""
    echo "⚠️  重要: 请编辑 backend/.env 文件，填入你的 SILICONFLOW_API_KEY"
    echo "   获取地址: https://siliconflow.cn"
    echo ""
    
    # 尝试用默认编辑器打开
    if command -v nano &> /dev/null; then
        nano "backend/.env"
    elif command -v vim &> /dev/null; then
        vim "backend/.env"
    else
        echo "请手动编辑 backend/.env 文件"
    fi
    
    echo ""
    echo "请保存文件后按 Enter 键继续..."
    read
fi

echo "[1/4] 停止旧容器..."
docker-compose down > /dev/null 2>&1

echo "[2/4] 拉取最新镜像..."
docker-compose pull > /dev/null 2>&1

echo "[3/4] 构建并启动服务..."
docker-compose up -d --build

if [ $? -ne 0 ]; then
    echo ""
    echo "[错误] 启动失败，请检查 Docker 是否正常运行"
    exit 1
fi

echo "[4/4] 等待服务就绪..."
sleep 5

echo ""
echo "=========================================="
echo "  ✅ 启动成功！"
echo "=========================================="
echo ""
echo "  访问地址: http://localhost:8080"
echo ""
echo "  常用命令:"
echo "    - 查看日志: docker-compose logs -f"
echo "    - 停止服务: docker-compose down"
echo "    - 重启服务: docker-compose restart"
echo ""

# 尝试自动打开浏览器
if command -v open &> /dev/null; then
    open "http://localhost:8080"
elif command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:8080"
else
    echo "  请手动打开浏览器访问上述地址"
fi
