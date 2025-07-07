#!/bin/bash
set -e

# 确保数据目录存在且权限正确
mkdir -p /app/data
chmod 755 /app/data

# 确保日志目录存在
mkdir -p /app/logs
chmod 755 /app/logs

# 如果没有设置JWT密钥，生成一个随机密钥
if [ -z "$JWT_SECRET_KEY" ]; then
    export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
    echo "Generated JWT_SECRET_KEY: $JWT_SECRET_KEY"
fi

# 启动应用
echo "Starting Stock Scanner Application..."
echo "Database URL: $DATABASE_URL"
echo "User System Enabled: $ENABLE_USER_SYSTEM"

exec python web_server.py 