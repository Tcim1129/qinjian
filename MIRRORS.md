# 国内镜像说明

如果服务器位于中国大陆，拉取基础镜像和 Python 依赖时建议使用镜像源。

## Docker

`/etc/docker/daemon.json` 参考：

```json
{
  "registry-mirrors": [
    "https://docker.mirrors.sjtug.sjtu.edu.cn",
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}
```

重启 Docker：

```bash
sudo systemctl restart docker
```

## 项目当前策略

- `backend/Dockerfile` 已优先使用国内 apt / pip 源
- `docker-compose.yml` 默认还是官方镜像名
- 如果某个镜像源异常，部署脚本会回退到官方 `postgres:16-alpine` 和 `nginx:alpine`

## 远端操作

```bash
cd /root/qinjian
docker compose up -d --build
```

## 版权

版权所有：心晴合伙人项目组 黄菁蓝、吴秀秀、叶笙尧、钟昊桐、郑梓滢
