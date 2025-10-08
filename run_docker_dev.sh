#!/bin/bash

# Docker开发环境启动脚本
# 使用容器进行快速调试，支持代码目录挂载和热重载

set -e

echo "=== Stock Scanner Docker Development Environment ==="
echo "Starting development environment with code mounting..."

# 检查Docker和Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    echo "❌ Docker Compose is not installed"
    exit 1
fi

# 设置环境变量文件
ENV_FILE=".env"
if [[ ! -f "$ENV_FILE" ]]; then
    echo "❌ $ENV_FILE not found."
    echo ""
    echo "Please create a $ENV_FILE file with your configuration."
    echo "You can use the following template:"
    echo ""
    echo "# API配置"
    echo "API_KEY=your_api_key_here"
    echo "API_URL=https://api.openai.com/v1/chat/completions"
    echo "API_MODEL=gpt-3.5-turbo"
    echo "API_TIMEOUT=30"
    echo ""
    echo "# 用户系统配置"
    echo "ENABLE_USER_SYSTEM=true"
    echo "JWT_SECRET_KEY=your_secret_key_here"
    echo ""
    echo "# 公告配置（可选）"
    echo "ANNOUNCEMENT_TEXT=Docker开发环境 - Stock Scanner"
    echo ""
    echo "After creating the file, run this script again."
    exit 1
fi

# 加载环境变量
echo "📋 Loading environment variables from $ENV_FILE..."
export $(grep -v '^#' "$ENV_FILE" | xargs)

# 创建必要的目录
echo "📁 Creating necessary directories..."
mkdir -p data logs

# 显示当前配置
echo ""
echo "=== Current Configuration ==="
echo "API_URL: ${API_URL:-not set}"
echo "API_MODEL: ${API_MODEL:-not set}"
echo "ENABLE_USER_SYSTEM: ${ENABLE_USER_SYSTEM:-true}"
echo "=========================="
echo ""

# 检查是否有正在运行的容器
if docker ps -q --filter "name=stock-scanner-app-dev" | grep -q .; then
    echo "🔄 Stopping existing development container..."
    docker-compose -f docker-compose.dev.yml down
fi

# 构建开发镜像（如果需要）
echo "🔨 Building development image..."
docker-compose -f docker-compose.dev.yml build app-dev

# 检查是否传入 -d 参数（后台运行）
DETACHED_MODE=false
if [[ "$1" == "-d" ]]; then
    DETACHED_MODE=true
fi

# 启动开发环境
echo "🚀 Starting development environment..."
echo ""
echo "📊 Services starting:"
echo "  - Main App: http://localhost:8888"
echo "  - API Docs: http://localhost:8888/docs"
echo "  - Health Check: http://localhost:8888/api/config"
echo ""
echo "🔧 Development features enabled:"
echo "  - Hot reload on code changes"
echo "  - Debug logging"
echo "  - Code directory mounted"
echo "  - Development database (SQLite)"
echo ""

if [ "$DETACHED_MODE" = true ]; then
    # 后台启动模式
    echo "🔙 Starting in detached mode (background)..."
    echo ""
    docker-compose -f docker-compose.dev.yml up -d
    
    # 等待服务启动
    echo "⏳ Waiting for services to start..."
    sleep 5
    
    # 检查服务状态
    if docker-compose -f docker-compose.dev.yml ps | grep -q "Up"; then
        echo "✅ Development environment started successfully!"
        echo ""
        echo "🎯 Quick commands:"
        echo "  - View logs: docker-compose -f docker-compose.dev.yml logs -f app-dev"
        echo "  - Restart app: docker-compose -f docker-compose.dev.yml restart app-dev"
        echo "  - Shell access: docker-compose -f docker-compose.dev.yml exec app-dev bash"
        echo "  - Stop all: docker-compose -f docker-compose.dev.yml down"
        echo ""
        echo "🔍 Testing API..."
        if curl -s http://localhost:8888/api/config > /dev/null; then
            echo "✅ API is responding!"
        else
            echo "⚠️  API not responding yet, may need more time to start"
        fi
    else
        echo "❌ Failed to start development environment"
        echo "Check logs with: docker-compose -f docker-compose.dev.yml logs"
        exit 1
    fi
else
    # 交互启动模式（默认）
    echo "🖥️  Starting in interactive mode..."
    echo "📝 Press Ctrl+C to stop"
    echo "🛑 To run in background, use: $0 -d"
    echo ""
    docker-compose -f docker-compose.dev.yml up
fi