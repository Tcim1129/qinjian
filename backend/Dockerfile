FROM python:3.12-slim

WORKDIR /app

# 使用国内 apt 镜像源
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# 使用国内 pip 镜像源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码
COPY . .

# 启动脚本可执行
RUN chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]
