# Stock Scanner Development Makefile
# 提供统一的开发命令接口

.PHONY: help dev-start dev-stop dev-restart dev-logs dev-shell dev-status dev-clean
.PHONY: docker-dev docker-dev-simple docker-dev-stop docker-dev-logs docker-dev-shell
.PHONY: build test format lint install
.DEFAULT_GOAL := help

# 颜色定义
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

## 显示帮助信息
help:
	@echo "$(GREEN)Stock Scanner Development Commands$(RESET)"
	@echo ""
	@echo "$(YELLOW)本地开发:$(RESET)"
	@echo "  make dev-start      - 启动本地开发服务器"
	@echo "  make dev-stop       - 停止本地开发服务器"
	@echo "  make dev-test       - 运行测试"
	@echo ""
	@echo "$(YELLOW)Docker开发:$(RESET)"
	@echo "  make docker-dev     - 启动Docker开发环境（简单模式）"
	@echo "  make docker-dev-compose - 启动Docker开发环境（完整模式）"
	@echo "  make docker-dev-stop - 停止Docker开发环境"
	@echo "  make docker-dev-logs - 查看Docker开发环境日志"
	@echo "  make docker-dev-shell - 进入Docker开发环境Shell"
	@echo "  make docker-dev-status - 查看Docker开发环境状态"
	@echo ""
	@echo "$(YELLOW)代码质量:$(RESET)"
	@echo "  make format         - 格式化代码"
	@echo "  make lint           - 代码检查"
	@echo "  make test           - 运行测试"
	@echo ""
	@echo "$(YELLOW)环境管理:$(RESET)"
	@echo "  make install        - 安装依赖"
	@echo "  make clean          - 清理环境"
	@echo "  make build          - 构建Docker镜像"
	@echo ""
	@echo "$(YELLOW)快速命令:$(RESET)"
	@echo "  make setup          - 初始化开发环境"
	@echo "  make dev            - 启动开发环境（自动选择模式）"

## 本地开发命令
dev-start:
	@echo "$(GREEN)启动本地开发服务器...$(RESET)"
	@if [ -f "run_backend_dev.sh" ]; then \
		./run_backend_dev.sh; \
	else \
		echo "$(RED)run_backend_dev.sh not found$(RESET)"; \
	fi

dev-stop:
	@echo "$(GREEN)停止本地开发服务器...$(RESET)"
	@pkill -f "uvicorn web_server:app" || echo "No local server running"

dev-test:
	@echo "$(GREEN)运行开发环境测试...$(RESET)"
	@if [ -f "test_dev_setup.py" ]; then \
		python3 test_dev_setup.py; \
	else \
		echo "$(RED)test_dev_setup.py not found$(RESET)"; \
	fi

## Docker开发命令
docker-dev:
	@echo "$(GREEN)启动Docker开发环境（简单模式）...$(RESET)"
	@./run_docker_dev_simple.sh

docker-dev-compose:
	@echo "$(GREEN)启动Docker开发环境（完整模式）...$(RESET)"
	@./run_docker_dev.sh

docker-dev-stop:
	@echo "$(GREEN)停止Docker开发环境...$(RESET)"
	@./dev_tools.sh stop

docker-dev-logs:
	@echo "$(GREEN)查看Docker开发环境日志...$(RESET)"
	@./dev_tools.sh logs -f

docker-dev-shell:
	@echo "$(GREEN)进入Docker开发环境Shell...$(RESET)"
	@./dev_tools.sh shell

docker-dev-status:
	@echo "$(GREEN)查看Docker开发环境状态...$(RESET)"
	@./dev_tools.sh status

## 代码质量命令
format:
	@echo "$(GREEN)格式化代码...$(RESET)"
	@if docker ps --format "table {{.Names}}" | grep -q "stock-scanner-dev"; then \
		./dev_tools.sh format; \
	else \
		echo "$(YELLOW)Docker环境未运行，使用本地格式化...$(RESET)"; \
		black services/ utils/ web_server.py; \
	fi

lint:
	@echo "$(GREEN)代码检查...$(RESET)"
	@if docker ps --format "table {{.Names}}" | grep -q "stock-scanner-dev"; then \
		./dev_tools.sh lint; \
	else \
		echo "$(YELLOW)Docker环境未运行，使用本地检查...$(RESET)"; \
		flake8 services/ utils/ web_server.py; \
	fi

test:
	@echo "$(GREEN)运行测试...$(RESET)"
	@if docker ps --format "table {{.Names}}" | grep -q "stock-scanner-dev"; then \
		./dev_tools.sh test; \
	else \
		echo "$(YELLOW)Docker环境未运行，使用本地测试...$(RESET)"; \
		python -m pytest tests/ -v; \
	fi

## 环境管理命令
install:
	@echo "$(GREEN)安装依赖...$(RESET)"
	@pip install -r requirements.txt

clean:
	@echo "$(GREEN)清理环境...$(RESET)"
	@./dev_tools.sh clean
	@echo "$(GREEN)清理Python缓存...$(RESET)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true

build:
	@echo "$(GREEN)构建Docker镜像...$(RESET)"
	@docker build -f Dockerfile.dev -t stock-scanner-dev .

## 快速命令
setup:
	@echo "$(GREEN)初始化开发环境...$(RESET)"
	@mkdir -p data logs
	@if [ ! -f ".env" ]; then \
		echo "$(YELLOW)请手动创建 .env 文件...$(RESET)"; \
		echo "参考 docker-compose.yml 或项目文档创建配置文件"; \
	fi
	@echo "$(GREEN)环境初始化完成！$(RESET)"
	@echo "$(YELLOW)请编辑 .env 文件设置API密钥$(RESET)"

dev:
	@echo "$(GREEN)启动开发环境...$(RESET)"
	@if command -v docker >/dev/null 2>&1; then \
		echo "$(YELLOW)检测到Docker，使用Docker开发环境$(RESET)"; \
		make docker-dev; \
	else \
		echo "$(YELLOW)未检测到Docker，使用本地开发环境$(RESET)"; \
		make dev-start; \
	fi

## 生产环境命令
prod-start:
	@echo "$(GREEN)启动生产环境...$(RESET)"
	@docker-compose up -d

prod-stop:
	@echo "$(GREEN)停止生产环境...$(RESET)"
	@docker-compose down

prod-logs:
	@echo "$(GREEN)查看生产环境日志...$(RESET)"
	@docker-compose logs -f 