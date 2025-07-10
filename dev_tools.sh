#!/bin/bash

# 开发工具脚本
# 提供常用的Docker开发环境管理命令

set -e

CONTAINER_NAME="stock-scanner-dev"
COMPOSE_FILE="docker-compose.dev.yml"

# 显示帮助信息
show_help() {
    echo "Stock Scanner Development Tools"
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  start          - Start development environment"
    echo "  stop           - Stop development environment"
    echo "  restart        - Restart development environment"
    echo "  logs           - View application logs"
    echo "  shell          - Access container shell"
    echo "  status         - Show container status"
    echo "  clean          - Clean up containers and volumes"
    echo "  build          - Rebuild development image"
    echo "  test           - Run tests inside container"
    echo "  format         - Format code with black"
    echo "  lint           - Run linting checks"
    echo "  db-shell       - Access database shell"
    echo "  install <pkg>  - Install Python package"
    echo "  pip-freeze     - Show installed packages"
    echo ""
    echo "Examples:"
    echo "  $0 start       # Start development environment"
    echo "  $0 logs -f     # Follow logs"
    echo "  $0 shell       # Access container shell"
    echo "  $0 install requests  # Install package"
}

# 检查容器是否运行
check_container() {
    if ! docker ps --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        echo "❌ Container $CONTAINER_NAME is not running"
        echo "   Start it with: $0 start"
        return 1
    fi
    return 0
}

# 启动开发环境
start_dev() {
    echo "🚀 Starting development environment..."
    
    if [[ -f "$COMPOSE_FILE" ]]; then
        # 使用docker-compose
        docker-compose -f "$COMPOSE_FILE" up -d
    else
        # 使用简单脚本
        ./run_docker_dev_simple.sh
    fi
}

# 停止开发环境
stop_dev() {
    echo "🛑 Stopping development environment..."
    
    if [[ -f "$COMPOSE_FILE" ]]; then
        docker-compose -f "$COMPOSE_FILE" down
    else
        docker stop "$CONTAINER_NAME" 2>/dev/null || true
        docker rm "$CONTAINER_NAME" 2>/dev/null || true
    fi
}

# 重启开发环境
restart_dev() {
    echo "🔄 Restarting development environment..."
    
    if [[ -f "$COMPOSE_FILE" ]]; then
        docker-compose -f "$COMPOSE_FILE" restart app-dev
    else
        docker restart "$CONTAINER_NAME"
    fi
}

# 查看日志
view_logs() {
    check_container || return 1
    
    if [[ -f "$COMPOSE_FILE" ]]; then
        docker-compose -f "$COMPOSE_FILE" logs "$@" app-dev
    else
        docker logs "$@" "$CONTAINER_NAME"
    fi
}

# 进入容器shell
enter_shell() {
    check_container || return 1
    
    echo "🐚 Entering container shell..."
    docker exec -it "$CONTAINER_NAME" bash
}

# 显示状态
show_status() {
    echo "📊 Development Environment Status:"
    echo ""
    
    if docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -q "$CONTAINER_NAME"; then
        echo "✅ Container is running:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "$CONTAINER_NAME"
    else
        echo "❌ Container is not running"
    fi
    
    echo ""
    echo "🔗 Quick links:"
    echo "  - Application: http://localhost:8888"
    echo "  - API Docs: http://localhost:8888/docs"
    echo "  - Health Check: http://localhost:8888/api/config"
}

# 清理环境
clean_env() {
    echo "🧹 Cleaning up development environment..."
    
    # 停止容器
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    
    # 清理compose资源
    if [[ -f "$COMPOSE_FILE" ]]; then
        docker-compose -f "$COMPOSE_FILE" down -v --remove-orphans
    fi
    
    # 清理未使用的镜像
    docker image prune -f
    
    echo "✅ Cleanup completed"
}

# 构建镜像
build_image() {
    echo "🔨 Building development image..."
    
    if [[ -f "$COMPOSE_FILE" ]]; then
        docker-compose -f "$COMPOSE_FILE" build app-dev
    else
        docker build -f Dockerfile.dev -t stock-scanner-dev .
    fi
}

# 运行测试
run_tests() {
    check_container || return 1
    
    echo "🧪 Running tests..."
    docker exec "$CONTAINER_NAME" python -m pytest tests/ -v
}

# 格式化代码
format_code() {
    check_container || return 1
    
    echo "🎨 Formatting code with black..."
    docker exec "$CONTAINER_NAME" black services/ utils/ web_server.py
}

# 代码检查
lint_code() {
    check_container || return 1
    
    echo "🔍 Running linting checks..."
    docker exec "$CONTAINER_NAME" flake8 services/ utils/ web_server.py
}

# 数据库shell
db_shell() {
    check_container || return 1
    
    echo "🗄️  Accessing database shell..."
    docker exec -it "$CONTAINER_NAME" python -c "
import sqlite3
conn = sqlite3.connect('/app/data/stock_scanner_dev.db')
conn.execute('.help')
"
}

# 安装包
install_package() {
    check_container || return 1
    
    if [[ -z "$1" ]]; then
        echo "❌ Please specify package name"
        return 1
    fi
    
    echo "📦 Installing package: $1"
    docker exec "$CONTAINER_NAME" pip install "$1"
}

# 显示已安装的包
pip_freeze() {
    check_container || return 1
    
    echo "📋 Installed packages:"
    docker exec "$CONTAINER_NAME" pip freeze
}

# 主逻辑
case "${1:-help}" in
    "start")
        start_dev
        ;;
    "stop")
        stop_dev
        ;;
    "restart")
        restart_dev
        ;;
    "logs")
        shift
        view_logs "$@"
        ;;
    "shell")
        enter_shell
        ;;
    "status")
        show_status
        ;;
    "clean")
        clean_env
        ;;
    "build")
        build_image
        ;;
    "test")
        run_tests
        ;;
    "format")
        format_code
        ;;
    "lint")
        lint_code
        ;;
    "db-shell")
        db_shell
        ;;
    "install")
        install_package "$2"
        ;;
    "pip-freeze")
        pip_freeze
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac 