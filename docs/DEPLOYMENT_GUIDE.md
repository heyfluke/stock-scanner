# Stock Scanner 部署指南

本指南详细介绍了Stock Scanner的多种部署方案，从简单的单体容器到企业级微服务架构。

## 📋 目录

- [部署方案对比](#部署方案对比)
- [单体容器部署](#单体容器部署)
- [微服务部署](#微服务部署)
- [云平台部署](#云平台部署)
- [生产环境配置](#生产环境配置)
- [监控和维护](#监控和维护)
- [故障排除](#故障排除)

## 🏗️ 部署方案对比

| 特性 | 单体容器 | 微服务架构 |
|------|----------|------------|
| **适用场景** | 个人用户、小团队、NAS | 企业、高并发、高可用 |
| **部署复杂度** | ⭐ 简单 | ⭐⭐⭐ 中等 |
| **资源占用** | ⭐ 低 (512MB-1GB) | ⭐⭐ 中等 (2-4GB) |
| **扩展性** | ⭐⭐ 有限 | ⭐⭐⭐⭐⭐ 高 |
| **高可用性** | ⭐⭐ 一般 | ⭐⭐⭐⭐⭐ 高 |
| **维护成本** | ⭐ 低 | ⭐⭐⭐ 中等 |
| **数据库** | SQLite | PostgreSQL |
| **缓存** | 无 | Redis |

## 🏠 单体容器部署

### 适用场景
- 个人用户
- 小型团队
- Synology NAS
- 开发和测试环境

### 快速部署

```bash
# 1. 克隆项目
git clone https://github.com/heyfluke/stock-scanner.git
cd stock-scanner

# 2. 创建配置文件
cat > .env << EOL
API_KEY=你的API密钥
API_URL=https://api.openai.com/v1/chat/completions
API_MODEL=gpt-3.5-turbo
API_TIMEOUT=60
ENABLE_USER_SYSTEM=true
JWT_SECRET_KEY=your_secret_key
ANNOUNCEMENT_TEXT=欢迎使用Stock Scanner
EOL

# 3. 启动服务
make deploy-monolithic
```

### 手动部署

```bash
# 使用Docker Compose
docker-compose -f docker-compose.yml up -d

# 或使用Docker命令
docker run -d \
  --name stock-scanner \
  -p 8888:8888 \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/logs:/app/logs" \
  --env-file .env \
  heyfluke/stock-scanner:latest
```

### 配置说明

**必需环境变量：**
- `API_KEY`: AI API密钥
- `API_URL`: AI API地址
- `API_MODEL`: AI模型名称

**可选环境变量：**
- `API_TIMEOUT`: API超时时间（默认60秒）
- `ENABLE_USER_SYSTEM`: 启用用户系统（默认true）
- `JWT_SECRET_KEY`: JWT密钥（自动生成）
- `ANNOUNCEMENT_TEXT`: 系统公告

### 数据持久化

单体容器使用SQLite数据库，数据存储在：
- 数据库文件：`./data/stock_scanner.db`
- 日志文件：`./logs/`

## 🏢 微服务部署

### 适用场景
- 企业级部署
- 高并发需求
- 高可用性要求
- 需要独立扩展

### 完整微服务部署

```bash
# 1. 克隆项目
git clone https://github.com/heyfluke/stock-scanner.git
cd stock-scanner

# 2. 创建配置文件
cat > .env << EOL
API_KEY=你的API密钥
API_URL=https://api.openai.com/v1/chat/completions
API_MODEL=gpt-3.5-turbo
API_TIMEOUT=60
ENABLE_USER_SYSTEM=true
JWT_SECRET_KEY=your_secret_key
ANNOUNCEMENT_TEXT=欢迎使用Stock Scanner

# 数据库配置
POSTGRES_DB=stock_scanner
POSTGRES_USER=stock_user
POSTGRES_PASSWORD=stock_password
EOL

# 3. 构建镜像
make build-all

# 4. 启动微服务
make deploy-microservices
```

### 微服务部署

```bash
# 使用完整微服务配置
make deploy-microservices
```

### 微服务架构说明

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端容器       │    │   后端容器       │    │   数据库容器     │
│  (Vue + Nginx)  │◄──►│  (Python API)   │◄──►│  (PostgreSQL)   │
│  端口: 3000     │    │  端口: 8888     │    │  端口: 5432     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   反向代理       │
                    │    (Nginx)      │
                    │  端口: 80/443   │
                    └─────────────────┘
```

### 服务配置

**前端服务 (frontend):**
- 端口：3000
- 功能：Vue应用 + Nginx静态服务
- 环境变量：`VITE_API_BASE_URL`

**后端服务 (backend):**
- 端口：8888
- 功能：Python FastAPI
- 环境变量：API配置、数据库连接

**数据库服务 (postgres):**
- 端口：5432
- 功能：PostgreSQL数据库
- 数据持久化：`postgres_data`卷

**缓存服务 (redis):**
- 端口：6379
- 功能：Redis缓存
- 数据持久化：`redis_data`卷

**反向代理 (nginx):**
- 端口：80/443
- 功能：统一入口、SSL终止、负载均衡

## ☁️ 云平台部署

### Zeabur部署

1. **连接GitHub仓库**
2. **选择部署方式：**
   - 单体容器：使用 `docker-compose.yml`
   - 微服务：使用 `docker-compose.microservices.yml`

3. **配置环境变量**
4. **自动部署**

### Railway部署

```bash
# 1. 安装Railway CLI
npm install -g @railway/cli

# 2. 登录Railway
railway login

# 3. 初始化项目
railway init

# 4. 部署
railway up
```

### Render部署

1. **创建Web Service**
2. **连接GitHub仓库**
3. **配置构建命令：**
   ```bash
   make build-all && make deploy-microservices
   ```
4. **设置环境变量**

### Fly.io部署

```bash
# 1. 安装Fly CLI
curl -L https://fly.io/install.sh | sh

# 2. 登录
fly auth login

# 3. 创建应用
fly apps create stock-scanner

# 4. 部署
fly deploy
```

## 🔧 生产环境配置

### 安全配置

```bash
# 1. 生成强密码
openssl rand -base64 32

# 2. 配置环境变量
JWT_SECRET_KEY=生成的强密钥
POSTGRES_PASSWORD=强密码

# 3. 配置SSL证书
# 将证书文件放在 nginx/ssl/ 目录
```

### 性能优化

```yaml
# docker-compose.microservices.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
  
  postgres:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
```

### 监控配置

```bash
# 启用健康检查
docker-compose up -d

# 查看服务状态
make status

# 查看日志
make logs
```

## 📊 监控和维护

### 健康检查

```bash
# 检查服务状态
make health

# 查看详细状态
docker-compose ps

# 查看资源使用
docker stats
```

### 日志管理

```bash
# 查看所有日志
make logs

# 查看特定服务日志
docker-compose logs -f backend

# 查看错误日志
docker-compose logs --tail=100 | grep ERROR
```

### 数据备份

```bash
# 备份数据
make backup

# 恢复数据
make restore BACKUP_FILE=backups/xxx.tar.gz

# 数据库备份（微服务）
docker exec stock-scanner-postgres pg_dump -U stock_user stock_scanner > backup.sql
```

### 更新部署

```bash
# 拉取最新镜像
make pull

# 重启服务
make restart

# 或重启微服务
make restart-microservices
```

## 🐛 故障排除

### 常见问题

**1. 服务无法启动**
```bash
# 检查端口占用
netstat -tulpn | grep :8888

# 检查日志
docker-compose logs app

# 检查配置
docker-compose config
```

**2. 数据库连接失败**
```bash
# 检查数据库状态
docker-compose logs postgres

# 检查网络连接
docker network ls
docker network inspect stock-scanner_stock-scanner-network
```

**3. API调用失败**
```bash
# 检查API配置
echo $API_KEY
echo $API_URL

# 测试API连接
curl -X POST $API_URL \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-3.5-turbo","messages":[{"role":"user","content":"test"}]}'
```

**4. 前端无法访问后端**
```bash
# 检查网络配置
docker-compose exec frontend ping backend

# 检查API代理配置
docker-compose exec frontend curl http://backend:8888/api/config
```

### 调试命令

```bash
# 进入容器调试
docker-compose exec backend bash
docker-compose exec frontend sh

# 查看网络配置
docker network inspect stock-scanner_stock-scanner-network

# 查看卷挂载
docker volume ls
docker volume inspect stock-scanner_postgres_data
```

### 性能调优

```bash
# 查看资源使用
docker stats

# 性能测试
make benchmark

# 优化数据库
docker-compose exec postgres psql -U stock_user -d stock_scanner -c "VACUUM ANALYZE;"
```

## 📞 支持

- 🐛 Issues: [GitHub Issues](https://github.com/heyfluke/stock-scanner/issues)
- 📖 文档: [项目Wiki](https://github.com/heyfluke/stock-scanner/wiki)

## 📄 许可证

待定