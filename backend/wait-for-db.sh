#!/bin/sh
# 等待 PostgreSQL 数据库就绪

set -e

host="${DB_HOST:-db}"
port="${DB_PORT:-5432}"
user="${DB_USER:-qinjian}"
database="${DB_NAME:-qinjian}"
max_attempts=30
wait_seconds=2

echo "=== 等待数据库就绪 (${host}:${port}) ==="

attempt=1
while [ $attempt -le $max_attempts ]; do
    if pg_isready -h "$host" -p "$port" -U "$user" -d "$database" >/dev/null 2>&1; then
        echo "数据库已就绪 (尝试 ${attempt}/${max_attempts})"
        exit 0
    fi
    
    echo "数据库未就绪，${wait_seconds}秒后重试... (尝试 ${attempt}/${max_attempts})"
    sleep $wait_seconds
    attempt=$((attempt + 1))
done

echo "错误：数据库在 ${max_attempts} 次尝试后仍未就绪"
exit 1
