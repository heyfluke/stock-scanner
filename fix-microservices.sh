#!/bin/bash

# 微服务部署问题修复脚本
# 解决PostgreSQL驱动和Nginx配置问题

set -e

echo "🔧 修复微服务部署问题..."

# 停止现有服务
echo "🛑 停止现有服务..."
docker-compose -f docker-compose.microservices.yml down 2>/dev/null || true

# 清理容器和镜像
echo "🧹 清理容器和镜像..."
docker container prune -f
docker image prune -f

# 重新构建镜像（包含PostgreSQL驱动）
echo "🔨 重新构建镜像..."
make build-all

# 创建必要的目录
echo "📁 创建必要目录..."
mkdir -p nginx/logs
mkdir -p data logs

# 创建环境变量文件（如果不存在）
if [ ! -f .env ]; then
    echo "📝 创建环境变量文件..."
    cat > .env << EOL
API_KEY=your_api_key_here
API_URL=https://api.openai.com/v1/chat/completions
API_MODEL=gpt-3.5-turbo
API_TIMEOUT=60
ENABLE_USER_SYSTEM=true
JWT_SECRET_KEY=your_secret_key_here
ANNOUNCEMENT_TEXT=Stock Scanner 微服务版本

# 数据库配置
POSTGRES_DB=stock_scanner
POSTGRES_USER=stock_user
POSTGRES_PASSWORD=stock_password
EOL
    echo "⚠️  请编辑 .env 文件设置正确的API密钥"
fi

# 启动微服务
echo "🚀 启动微服务..."
make deploy-microservices

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "📊 检查服务状态..."
docker-compose -f docker-compose.microservices.yml ps

# 检查健康状态
echo "🏥 检查健康状态..."
for i in {1..5}; do
    if curl -s http://localhost:80/health > /dev/null; then
        echo "✅ 服务健康检查通过"
        break
    else
        echo "⏳ 等待服务启动... ($i/5)"
        sleep 5
    fi
done

echo ""
echo "🎉 修复完成！"
echo "📱 访问地址: http://localhost:80"
echo "📋 查看日志: make logs-microservices"
echo "�� 停止服务: make stop" 