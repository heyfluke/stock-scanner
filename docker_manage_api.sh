#!/bin/bash

# Docker环境的API配置管理脚本
# 自动使用Docker开发环境的数据库

set -e

# 数据库路径（Docker开发环境）
DB_PATH="data/stock_scanner.db"

echo "🐳 Docker Development Environment - API Config Manager"
echo "📁 Database: $DB_PATH"
echo ""

# 确保data目录存在
mkdir -p data

# 检查Docker容器是否在运行
if ! docker-compose -f docker-compose.dev.yml ps app-dev | grep -q "Up"; then
    echo "⚠️  Docker容器未运行，尝试在本地运行..."
    python3 manage_api_configs.py "$@" --db "$DB_PATH"
else
    echo "✓ Docker容器正在运行，在容器内执行..."
    docker-compose -f docker-compose.dev.yml exec -T app-dev python manage_api_configs.py "$@" --db "$DB_PATH"
fi

