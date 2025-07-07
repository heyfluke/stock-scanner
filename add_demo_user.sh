#!/bin/bash

# 添加demo用户到数据库的脚本
# 使用方法: ./add_demo_user.sh [数据库路径]
# 如果不提供路径，默认使用 ./data/stock_scanner.db

set -e

# 默认数据库路径
DEFAULT_DB_PATH="./data/stock_scanner.db"
DB_PATH="${1:-$DEFAULT_DB_PATH}"

# 检查数据库文件是否存在
if [ ! -f "$DB_PATH" ]; then
    echo "错误: 数据库文件不存在: $DB_PATH"
    echo "请先启动应用以创建数据库，或提供正确的数据库路径"
    exit 1
fi

# Demo用户信息
USERNAME="demo"
PASSWORD="demo"
DISPLAY_NAME="Demo User"
EMAIL="demo@example.com"

# 计算密码哈希 (使用与Python相同的SHA256方法)
PASSWORD_HASH=$(echo -n "$PASSWORD" | sha256sum | cut -d' ' -f1)

echo "正在检查数据库: $DB_PATH"
echo "Demo用户信息:"
echo "  用户名: $USERNAME"
echo "  密码: $PASSWORD"
echo "  显示名称: $DISPLAY_NAME"

# 检查demo用户是否已存在
USER_EXISTS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM users WHERE username = '$USERNAME';" 2>/dev/null || echo "0")

if [ "$USER_EXISTS" -gt 0 ]; then
    echo "✓ Demo用户已存在，无需添加"
    echo ""
    echo "可以使用以下信息登录:"
    echo "  用户名: $USERNAME"
    echo "  密码: $PASSWORD"
    exit 0
fi

echo "→ Demo用户不存在，正在添加..."

# 获取当前时间戳
TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M:%S')

# 插入demo用户
sqlite3 "$DB_PATH" <<EOF
INSERT INTO users (username, email, password_hash, display_name, created_at, updated_at, is_active)
VALUES ('$USERNAME', '$EMAIL', '$PASSWORD_HASH', '$DISPLAY_NAME', '$TIMESTAMP', '$TIMESTAMP', 1);
EOF

if [ $? -eq 0 ]; then
    echo "✓ Demo用户添加成功!"
    echo ""
    echo "现在可以使用以下信息登录:"
    echo "  用户名: $USERNAME"
    echo "  密码: $PASSWORD"
    echo ""
    echo "也可以创建默认设置..."
    
    # 获取用户ID
    USER_ID=$(sqlite3 "$DB_PATH" "SELECT id FROM users WHERE username = '$USERNAME';")
    
    # 为demo用户创建默认设置
    sqlite3 "$DB_PATH" <<EOF
INSERT INTO user_settings (user_id, default_market_type, default_analysis_days, created_at, updated_at)
VALUES ($USER_ID, 'A', 30, '$TIMESTAMP', '$TIMESTAMP');
EOF
    
    echo "✓ 默认设置创建成功!"
else
    echo "✗ Demo用户添加失败"
    exit 1
fi 