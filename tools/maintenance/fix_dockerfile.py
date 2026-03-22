with open("backend/Dockerfile", "r", encoding="utf-8") as f:
    content = f.read()

# Replace python image with mirror
content = content.replace("FROM python:3.12-slim", "FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/library/python:3.12-slim")

with open("backend/Dockerfile", "w", encoding="utf-8") as f:
    f.write(content)
