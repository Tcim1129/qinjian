# 部署指南

## 默认运行位置

服务器统一使用：

```bash
/root/qinjian
```

## 推荐方式

在本地项目根目录执行：

```bash
python deploy_current_workspace.py --host <server> --username root --password <password>
```

这个脚本会做四件事：

1. 检查 `/root/qinjian` 和 `.env`
2. 将 `backend`、`web`、`docker-compose.yml`、`nginx.conf` 打成压缩包
3. 上传并同步到远端目录
4. 执行 `docker compose up -d --build`

## 远端检查

```bash
cd /root/qinjian
docker compose ps
docker compose logs --tail=100 backend
```

线上检查地址：

- Web: `http://143.198.110.145:8080`
- API: `http://143.198.110.145:8080/api/health`

## 环境变量

至少保证 `.env` 中这些值可用：

- `DB_PASSWORD`
- `SECRET_KEY`
- `FRONTEND_ORIGIN`
- `AI_API_KEY`
- `AI_BASE_URL`

如果你是从旧目录迁回 `/root/qinjian`，优先保留原线上可用的 `.env`，不要随意重新生成数据库密码。

## 缓存说明

- `index.html` 现在设置为 `no-store`
- 静态资源继续走版本号

如果手机端看到旧标题、旧布局或底部按钮没悬浮，通常是拿到了旧缓存；重新打开页面后应会切到新版本。

## 版权

版权所有：心晴合伙人项目组 黄菁蓝、吴秀秀、叶笙尧、钟昊桐、郑梓滢
