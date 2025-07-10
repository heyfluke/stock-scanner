# Docker开发环境指南

本指南介绍如何使用Docker容器进行快速开发和调试，无需重新构建镜像。

## 概述

我们提供了三种Docker开发模式：

1. **简单模式** - 使用现有生产镜像 + 代码挂载
2. **完整模式** - 专门的开发镜像 + Docker Compose
3. **工具模式** - 统一的开发工具脚本

## 🚀 快速开始

### 方法1：简单模式（推荐）

使用现有的生产镜像，挂载代码目录：

```bash
# 启动开发环境
./run_docker_dev_simple.sh

# 查看日志
docker logs -f stock-scanner-dev

# 进入容器调试
docker exec -it stock-scanner-dev bash
```

### 方法2：完整模式

使用专门的开发镜像和Docker Compose：

```bash
# 启动开发环境
./run_docker_dev.sh

# 查看日志
docker-compose -f docker-compose.dev.yml logs -f app-dev

# 进入容器
docker-compose -f docker-compose.dev.yml exec app-dev bash
```

### 方法3：工具模式

使用统一的开发工具脚本：

```bash
# 启动
./dev_tools.sh start

# 查看状态
./dev_tools.sh status

# 查看日志
./dev_tools.sh logs -f

# 进入shell
./dev_tools.sh shell
```

## 📋 详细说明

### 环境配置

1. **创建配置文件**：
   ```bash
   # 创建 .env 文件（与生产环境保持一致）
   cp .env.example .env  # 如果有示例文件
   # 或手动创建 .env 文件
   ```

2. **编辑配置**：
   ```bash
   vim .env
   ```
   
   设置必要的环境变量：
   ```env
   API_KEY=your_actual_api_key
   API_URL=https://api.openai.com/v1/chat/completions
   API_MODEL=gpt-3.5-turbo
   ENABLE_USER_SYSTEM=true
   JWT_SECRET_KEY=your_dev_secret_key
   ```

### 核心特性

#### 🔄 热重载
- 代码修改后自动重启服务器
- 监控 `services/` 和 `utils/` 目录
- 支持 Python 文件的实时更新

#### 📁 代码挂载
关键目录和文件会被挂载到容器中：
- `./services/` → `/app/services/`
- `./utils/` → `/app/utils/`
- `./web_server.py` → `/app/web_server.py`
- `./data/` → `/app/data/`
- `./logs/` → `/app/logs/`

#### 🔍 调试功能
- 详细的调试日志
- 开发数据库（独立于生产环境）
- 内置开发工具（black, flake8, pytest等）

## 🛠️ 开发工具

### 使用 dev_tools.sh

```bash
# 查看帮助
./dev_tools.sh help

# 启动/停止
./dev_tools.sh start
./dev_tools.sh stop
./dev_tools.sh restart

# 查看日志
./dev_tools.sh logs
./dev_tools.sh logs -f    # 跟踪日志

# 进入容器
./dev_tools.sh shell

# 运行测试
./dev_tools.sh test

# 代码格式化
./dev_tools.sh format

# 代码检查
./dev_tools.sh lint

# 安装包
./dev_tools.sh install requests

# 查看已安装包
./dev_tools.sh pip-freeze
```

### 直接使用Docker命令

```bash
# 查看运行状态
docker ps | grep stock-scanner-dev

# 查看日志
docker logs -f stock-scanner-dev

# 进入容器
docker exec -it stock-scanner-dev bash

# 重启容器
docker restart stock-scanner-dev

# 停止容器
docker stop stock-scanner-dev
```

## 🎯 开发工作流

### 典型的开发流程

1. **启动开发环境**：
   ```bash
   ./run_docker_dev_simple.sh
   ```

2. **验证环境**：
   ```bash
   curl http://localhost:8888/api/config
   ```

3. **开始开发**：
   - 编辑 `services/` 或 `utils/` 中的代码
   - 服务器会自动重启
   - 在浏览器中测试：http://localhost:8888

4. **调试问题**：
   ```bash
   # 查看日志
   ./dev_tools.sh logs -f
   
   # 进入容器调试
   ./dev_tools.sh shell
   ```

5. **运行测试**：
   ```bash
   ./dev_tools.sh test
   ```

6. **代码格式化**：
   ```bash
   ./dev_tools.sh format
   ./dev_tools.sh lint
   ```

### 前端开发

如果同时需要开发前端：

```bash
# 在另一个终端启动前端
cd frontend
npm install
npm run dev

# 前端会连接到容器中的后端API
```

## 🔧 高级配置

### 使用PostgreSQL替代SQLite

```bash
# 启动包含PostgreSQL的开发环境
docker-compose -f docker-compose.dev.yml --profile postgres up -d

# 更新环境变量
echo "DATABASE_URL=postgresql://dev_user:dev_password@postgres-dev:5432/stock_scanner_dev" >> .env
```

### 使用Redis缓存

```bash
# 启动包含Redis的开发环境
docker-compose -f docker-compose.dev.yml --profile redis up -d
```

### 自定义端口

```bash
# 修改端口
export HOST_PORT=9999
./run_docker_dev_simple.sh
```

## 🐛 故障排除

### 常见问题

1. **容器启动失败**
   ```bash
   # 查看详细日志
   docker logs stock-scanner-dev
   
   # 检查端口占用
   lsof -i :8888
   ```

2. **代码修改不生效**
   ```bash
   # 检查文件挂载
   docker exec stock-scanner-dev ls -la /app/services/
   
   # 重启容器
   docker restart stock-scanner-dev
   ```

3. **依赖包缺失**
   ```bash
   # 进入容器安装
   docker exec -it stock-scanner-dev pip install package_name
   
   # 或更新requirements.txt后重启
   docker restart stock-scanner-dev
   ```

4. **数据库问题**
   ```bash
   # 检查数据库文件
   ls -la data/
   
   # 重新创建数据库
   rm data/stock_scanner.db
   docker restart stock-scanner-dev
   ```

### 性能优化

1. **使用本地镜像缓存**：
   ```bash
   # 构建本地开发镜像
   docker build -f Dockerfile.dev -t stock-scanner-dev .
   ```

2. **优化文件监控**：
   ```bash
   # 减少监控的文件类型
   # 在docker-compose.dev.yml中调整--reload-include参数
   ```

## 📊 监控和日志

### 日志管理

```bash
# 实时查看日志
./dev_tools.sh logs -f

# 查看特定时间的日志
docker logs --since="2024-01-01T00:00:00" stock-scanner-dev

# 查看最后N行日志
docker logs --tail=100 stock-scanner-dev
```

### 性能监控

```bash
# 查看容器资源使用
docker stats stock-scanner-dev

# 查看容器详细信息
docker inspect stock-scanner-dev
```

## 🔄 与生产环境对比

| 特性 | 开发环境 | 生产环境 |
|------|----------|----------|
| 代码挂载 | ✅ | ❌ |
| 热重载 | ✅ | ❌ |
| 调试日志 | ✅ | ❌ |
| 开发工具 | ✅ | ❌ |
| 数据库 | SQLite | SQLite/PostgreSQL |
| 性能优化 | ❌ | ✅ |
| 安全配置 | 基础 | 完整 |

## 🎉 总结

Docker开发环境提供了：
- **快速启动**：无需重新构建镜像
- **实时开发**：代码修改即时生效
- **环境一致性**：与生产环境保持一致
- **便捷调试**：丰富的调试工具和日志
- **灵活配置**：支持多种开发模式

选择最适合你的开发模式，开始高效的容器化开发吧！ 