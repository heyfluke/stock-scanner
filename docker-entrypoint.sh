#!/bin/bash

# 数据库迁移函数
run_database_migration() {
    echo "🔄 开始数据库迁移..."
    
    # Python 内部循环重试数据库连接
    python3 - <<'EOF'
import os
import sys
import time
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

database_url = os.getenv('DATABASE_URL', 'sqlite:///./data/stock_scanner.db')
print(f'数据库连接: {database_url}')

max_retries = 10
for attempt in range(1, max_retries + 1):
    try:
        if database_url.startswith('postgresql://'):
            engine = create_engine(database_url)
            with engine.connect() as conn:
                result = conn.execute(text('SELECT version()'))
                version = result.fetchone()[0]
                print(f'PostgreSQL 版本: {version}')
            print('✅ 数据库连接成功')
        else:
            print('使用 SQLite 数据库')
        break
    except Exception as e:
        print(f'❌ 数据库连接失败（第{attempt}次）：{e}')
        if attempt == max_retries:
            print('❌ 已达到最大重试次数，退出')
            sys.exit(1)
        time.sleep(3)
EOF
    
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
    # 运行数据库迁移
    run_database_migration
else
    echo "👤 用户系统已禁用"
fi

# 启动应用
echo "🌟 启动 FastAPI 服务器..."
exec uvicorn web_server:app --host 0.0.0.0 --port 8888 --workers 1 