#!/bin/bash

# FastWhisper 启动脚本

set -e

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "Please edit .env file with your configuration."
fi

# 创建存储目录
mkdir -p storage/uploads storage/results

# 运行数据库迁移
echo "Running database migrations..."
alembic upgrade head

# 启动服务
echo "Starting FastWhisper service..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload