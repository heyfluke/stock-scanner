# Stock Scanner Makefile
# 支持单体容器和微服务架构的构建和部署

.PHONY: help build build-all test test-all clean deploy deploy-monolithic deploy-microservices

# 默认目标
help:
	@echo "Stock Scanner 构建和部署工具"
	@echo ""
	@echo "可用命令:"
	@echo "  build              - 构建单体容器镜像"
	@echo "  build-frontend     - 构建前端容器镜像"
	@echo "  build-backend      - 构建后端容器镜像"
	@echo "  build-all          - 构建所有镜像"
	@echo "  test               - 测试Docker Compose配置"
	@echo "  test-monolithic    - 测试单体容器配置"
	@echo "  test-microservices - 测试微服务配置"
	@echo "  clean              - 清理构建产物"
	@echo "  deploy-monolithic  - 部署单体容器版本"
	@echo "  deploy-microservices - 部署微服务版本"
	@echo "  logs               - 查看服务日志"
	@echo "  stop               - 停止所有服务"

# 构建单体容器镜像
build:
	@echo "🔨 构建单体容器镜像..."
	docker build -t heyfluke/stock-scanner:latest .
	@echo "✅ 单体容器镜像构建完成"

# 构建前端容器镜像
build-frontend:
	@echo "🔨 构建前端容器镜像..."
	docker build -t heyfluke/stock-scanner-frontend:latest ./frontend
	@echo "✅ 前端容器镜像构建完成"

# 构建后端容器镜像
build-backend:
	@echo "🔨 构建后端容器镜像..."
	docker build -f Dockerfile.backend -t heyfluke/stock-scanner-backend:latest .
	@echo "✅ 后端容器镜像构建完成"

# 构建所有镜像
build-all: build build-frontend build-backend
	@echo "🎉 所有镜像构建完成"

# 测试Docker Compose配置
test:
	@echo "🧪 测试Docker Compose配置..."
	python tests/test-docker-compose.py

# 测试单体容器配置
test-monolithic:
	@echo "🧪 测试单体容器配置..."
	docker-compose -f docker-compose.yml config

# 测试微服务配置
test-microservices:
	@echo "🧪 测试微服务配置..."
	docker-compose -f docker-compose.microservices.yml config

# 清理构建产物
clean:
	@echo "🧹 清理构建产物..."
	docker system prune -f
	docker volume prune -f
	@echo "✅ 清理完成"

# 部署单体容器版本
deploy-monolithic:
	@echo "🚀 部署单体容器版本..."
	docker-compose -f docker-compose.yml up -d
	@echo "✅ 单体容器版本部署完成"

# 部署微服务版本
deploy-microservices:
	@echo "🚀 部署微服务版本..."
	docker-compose -f docker-compose.microservices.yml up -d
	@echo "✅ 微服务版本部署完成"

# 查看服务日志
logs:
	@echo "📋 查看服务日志..."
	docker-compose logs -f

# 查看单体容器日志
logs-monolithic:
	@echo "📋 查看单体容器日志..."
	docker-compose -f docker-compose.yml logs -f

# 查看微服务日志
logs-microservices:
	@echo "📋 查看微服务日志..."
	docker-compose -f docker-compose.microservices.yml logs -f

# 停止所有服务
stop:
	@echo "🛑 停止所有服务..."
	docker-compose -f docker-compose.yml down
	docker-compose -f docker-compose.microservices.yml down
	@echo "✅ 所有服务已停止"

# 重启服务
restart:
	@echo "🔄 重启服务..."
	$(MAKE) stop
	$(MAKE) deploy-monolithic

# 重启微服务
restart-microservices:
	@echo "🔄 重启微服务..."
	docker-compose -f docker-compose.microservices.yml down
	docker-compose -f docker-compose.microservices.yml up -d

# 检查服务状态
status:
	@echo "📊 检查服务状态..."
	docker-compose -f docker-compose.yml ps
	@echo ""
	docker-compose -f docker-compose.microservices.yml ps

# 备份数据
backup:
	@echo "💾 备份数据..."
	mkdir -p backups
	tar -czf backups/stock-scanner-$(shell date +%Y%m%d-%H%M%S).tar.gz data/ logs/
	@echo "✅ 数据备份完成"

# 恢复数据
restore:
	@echo "📥 恢复数据..."
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "❌ 请指定备份文件: make restore BACKUP_FILE=backups/xxx.tar.gz"; \
		exit 1; \
	fi
	tar -xzf $(BACKUP_FILE) -C ./
	@echo "✅ 数据恢复完成"

# 开发环境
dev:
	@echo "🔧 启动开发环境..."
	./run_docker_dev.sh

# 开发环境（简化版）
dev-simple:
	@echo "🔧 启动简化开发环境..."
	./run_docker_dev_simple.sh

# 推送镜像到Docker Hub
push:
	@echo "📤 推送镜像到Docker Hub..."
	docker push heyfluke/stock-scanner:latest
	docker push heyfluke/stock-scanner-frontend:latest
	docker push heyfluke/stock-scanner-backend:latest
	@echo "✅ 镜像推送完成"

# 拉取最新镜像
pull:
	@echo "📥 拉取最新镜像..."
	docker pull heyfluke/stock-scanner:latest
	docker pull heyfluke/stock-scanner-frontend:latest
	docker pull heyfluke/stock-scanner-backend:latest
	@echo "✅ 镜像拉取完成"

# 健康检查
health:
	@echo "🏥 执行健康检查..."
	@curl -f http://localhost:8888/api/config || echo "❌ 单体容器服务不可用"
	@curl -f http://localhost:80/health || echo "❌ 微服务不可用"
	@echo "✅ 健康检查完成"

# 性能测试
benchmark:
	@echo "⚡ 执行性能测试..."
	@echo "测试单体容器性能..."
	@ab -n 100 -c 10 http://localhost:8888/api/config || echo "❌ 单体容器性能测试失败"
	@echo "测试微服务性能..."
	@ab -n 100 -c 10 http://localhost:80/health || echo "❌ 微服务性能测试失败"
	@echo "✅ 性能测试完成" 