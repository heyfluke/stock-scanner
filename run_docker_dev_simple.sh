#!/bin/bash

# 简化的Docker开发环境启动脚本
# 使用现有的生产镜像，挂载代码目录进行开发

set -e

echo "=== Stock Scanner Simple Docker Development ==="
echo "Using existing image with code mounting..."

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi

# 配置
CONTAINER_NAME="stock-scanner-dev"
IMAGE_NAME="heyfluke/stock-scanner:latest"
HOST_PORT="8888"
CONTAINER_PORT="8888"

# 环境变量文件
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

# 创建必要目录
mkdir -p data logs

# 停止现有容器
if docker ps -a --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo "🔄 Stopping existing container..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
fi

# 拉取最新镜像
echo "📥 Pulling latest image..."
docker pull "$IMAGE_NAME"

# 启动开发容器
echo "🚀 Starting development container..."

docker run -d \
    --name "$CONTAINER_NAME" \
    -p "$HOST_PORT:$CONTAINER_PORT" \
    --env-file "$ENV_FILE" \
    -e DATABASE_URL=sqlite:///data/stock_scanner.db \
    -e PYTHONUNBUFFERED=1 \
    -e DEBUG=true \
    -e LOG_LEVEL=DEBUG \
    -v "$(pwd)/services:/app/services" \
    -v "$(pwd)/utils:/app/utils" \
    -v "$(pwd)/web_server.py:/app/web_server.py" \
    -v "$(pwd)/data:/app/data" \
    -v "$(pwd)/logs:/app/logs" \
    --restart unless-stopped \
    "$IMAGE_NAME" \
    sh -c "
        echo 'Starting development server with hot reload...' &&
        pip install --quiet watchdog &&
        uvicorn web_server:app \
            --host 0.0.0.0 \
            --port $CONTAINER_PORT \
            --reload \
            --reload-dir /app/services \
            --reload-dir /app/utils \
            --reload-include='*.py' \
            --log-level debug \
            --access-log
    "

# 等待启动
echo "⏳ Waiting for container to start..."
sleep 3

# 检查状态
if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$CONTAINER_NAME.*Up"; then
    echo "✅ Development container started successfully!"
    echo ""
    echo "🌐 Access points:"
    echo "  - Application: http://localhost:$HOST_PORT"
    echo "  - API Documentation: http://localhost:$HOST_PORT/docs"
    echo "  - Health Check: http://localhost:$HOST_PORT/api/config"
    echo ""
    echo "🔧 Development features:"
    echo "  - Code changes auto-reload"
    echo "  - Debug logging enabled"
    echo "  - Development database"
    echo ""
    echo "📝 Useful commands:"
    echo "  - View logs: docker logs -f $CONTAINER_NAME"
    echo "  - Shell access: docker exec -it $CONTAINER_NAME bash"
    echo "  - Restart: docker restart $CONTAINER_NAME"
    echo "  - Stop: docker stop $CONTAINER_NAME"
    echo ""
    
    # 测试API
    echo "🔍 Testing API..."
    if curl -s "http://localhost:$HOST_PORT/api/config" > /dev/null; then
        echo "✅ API is responding!"
    else
        echo "⚠️  API not responding yet, container may still be starting"
    fi
else
    echo "❌ Failed to start container"
    echo "Check logs: docker logs $CONTAINER_NAME"
    exit 1
fi 