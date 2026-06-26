#!/bin/bash
set -e

echo "================================================"
echo "  智能预问诊系统 — Docker 启动"
echo "================================================"

# 等待 MySQL 就绪
echo "[1/4] 等待数据库就绪..."
MAX_RETRIES=30
RETRY_COUNT=0
until python -c "
import pymysql
import os
host = os.environ.get('DB_HOST', 'db')
port = int(os.environ.get('DB_PORT', 3306))
user = os.environ.get('DB_USER', 'root')
password = os.environ.get('DB_PASSWORD', '')
db_name = os.environ.get('DB_NAME', 'pre_consultation')
conn = pymysql.connect(host=host, port=port, user=user, password=password)
conn.close()
" 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -gt $MAX_RETRIES ]; then
        echo "[FAIL] 数据库连接超时，已重试 ${MAX_RETRIES} 次"
        exit 1
    fi
    echo "  等待中... (${RETRY_COUNT}/${MAX_RETRIES})"
    sleep 2
done
echo "[OK] 数据库已就绪"

# 初始化种子数据（幂等：已有数据则跳过）
echo "[2/4] 初始化种子数据..."
python -m seed.seed_data
echo "[OK] 种子数据检查完成"

# 生产就绪检查
echo "[3/4] 运行启动检查..."
python startup_check.py
echo "[OK] 启动检查通过"

# 启动 FastAPI
echo "[4/4] 启动 FastAPI 服务 → http://0.0.0.0:8000"
echo "       API 文档 → http://0.0.0.0:8000/docs"
echo "================================================"

exec python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \
    --proxy-headers \
    --forwarded-allow-ips '*'
