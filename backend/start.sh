#!/bin/sh
set -e

# 等待数据库就绪（带重试）
./wait-for-db.sh

echo "=== Running Alembic migrations ==="
alembic upgrade head 2>&1 || echo "WARNING: Alembic migration failed, falling back to create_all"

echo "=== Starting uvicorn ==="
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
