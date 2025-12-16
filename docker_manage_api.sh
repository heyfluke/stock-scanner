#!/bin/bash

# Docker环境的API配置管理脚本
# 自动使用Docker开发环境的数据库

set -e

# 数据库路径（Docker开发环境）
DB_PATH="data/stock_scanner.db"

echo "🐳 Docker Development Environment - API Config Manager"
echo "📁 Database: $DB_PATH"
echo ""

# 传递所有参数给manage_api_configs.py，并自动添加--db参数
python manage_api_configs.py "$@" --db "$DB_PATH"

