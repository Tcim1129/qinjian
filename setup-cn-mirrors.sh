#!/bin/bash
# 配置国内镜像源（中国大陆服务器专用）

echo "=== 配置 Docker 国内镜像源 ==="

# 创建 Docker 配置文件
sudo mkdir -p /etc/docker

sudo tee /etc/docker/daemon.json > /dev/null << 'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.sjtug.sjtu.edu.cn",
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
EOF

# 重启 Docker
if command -v systemctl &> /dev/null; then
    sudo systemctl restart docker
    echo "✓ Docker 服务已重启"
else
    sudo service docker restart
    echo "✓ Docker 服务已重启"
fi

echo ""
echo "=== 验证配置 ==="
sudo docker info | grep -A 5 "Registry Mirrors"

echo ""
echo "✅ 国内镜像源配置完成！"
echo ""
echo "接下来可以执行:"
echo "  cd /root/qinjian"
echo "  docker compose up -d"
