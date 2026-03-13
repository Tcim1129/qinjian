# 亲健 - 国内镜像源配置
# 解决中国大陆访问慢的问题

## 1. Docker 镜像源配置

创建或编辑 `/etc/docker/daemon.json`：

```json
{
  "registry-mirrors": [
    "https://docker.mirrors.sjtug.sjtu.edu.cn",
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
```

然后重启 Docker：
```bash
sudo systemctl restart docker
```

## 2. 项目中直接使用的国内镜像

已在以下文件中替换：

### docker-compose.yml
- `postgres:16-alpine` → 通过 Docker 镜像源加速
- `nginx:alpine` → 通过 Docker 镜像源加速

### backend/Dockerfile
- `python:3.12-slim` → 使用阿里云镜像
- `apt-get` → 使用阿里云 Debian 源
- `pip` → 使用清华 PyPI 镜像

## 3. 手动部署时配置

如果在服务器上手动部署，先执行：

```bash
# 配置 Docker 镜像源
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.sjtug.sjtu.edu.cn",
    "https://docker.mirrors.ustc.edu.cn"
  ]
}
EOF

sudo systemctl restart docker

# 然后正常部署
cd /root/qinjian
docker compose up -d
```
