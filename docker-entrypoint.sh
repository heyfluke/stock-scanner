#!/bin/bash

# 等待函数
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    
    echo "⏳ 等待 $service_name 服务启动..."
    while ! nc -z "$host" "$port" 2>/dev/null; do
        echo "   $service_name 还未就绪，等待中..."
        sleep 2
    done
    echo "✅ $service_name 服务已就绪"
}

# 数据库迁移函数
run_database_migration() {
    echo "🔄 开始数据库迁移..."
    
    # 检查数据库连接
    python3 -c "
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

database_url = os.getenv('DATABASE_URL', 'sqlite:///./data/stock_scanner.db')
print(f'数据库连接: {database_url}')

if database_url.startswith('postgresql://'):
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute(text('SELECT version()'))
            version = result.fetchone()[0]
            print(f'PostgreSQL 版本: {version}')
        print('✅ 数据库连接成功')
    except Exception as e:
        print(f'❌ 数据库连接失败: {e}')
        sys.exit(1)
else:
    print('使用 SQLite 数据库')
"
    
    if [ $? -ne 0 ]; then
        echo "❌ 数据库连接检查失败"
        exit 1
    fi
    
    # 运行迁移
    python3 -c "
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, '/app')

try:
    from services.user_service import UserService
    print('正在初始化数据库...')
    
    # 创建用户服务实例，这会自动创建数据库表
    database_url = os.getenv('DATABASE_URL', 'sqlite:///./data/stock_scanner.db')
    user_service = UserService(database_url)
    print('✅ 数据库初始化完成')
except Exception as e:
    print(f'❌ 数据库初始化失败: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        echo "✅ 数据库迁移完成"
    else
        echo "❌ 数据库迁移失败"
        exit 1
    fi
}

echo "🚀 启动 Stock Scanner 应用..."

# 设置环境变量
export PYTHONPATH="/app:$PYTHONPATH"

# 检查是否启用用户系统
if [ "${ENABLE_USER_SYSTEM:-true}" = "true" ]; then
    echo "👤 用户系统已启用"
    
    # 如果使用PostgreSQL，等待数据库服务
    if [[ "${DATABASE_URL:-}" =~ ^postgresql:// ]]; then
        # 从DATABASE_URL提取主机和端口
        DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
        DB_PORT=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
        
        if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
            wait_for_service "$DB_HOST" "$DB_PORT" "PostgreSQL"
        fi
    fi
    
    # 运行数据库迁移
    run_database_migration
else
    echo "👤 用户系统已禁用"
fi

# 启动应用
echo "🌟 启动 FastAPI 服务器..."
exec uvicorn web_server:app --host 0.0.0.0 --port 8888 --workers 1 