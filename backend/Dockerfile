FROM python:3.12-slim

WORKDIR /app

# 系统依赖（使用官方源，兼容海外服务器）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev postgresql-client && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY . .

# 启动脚本可执行
RUN chmod +x start.sh wait-for-db.sh

EXPOSE 8000

CMD ["./start.sh"]
