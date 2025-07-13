# Stock Scanner 部署指南

## 部署方案概览

本项目提供多种部署方案，适应不同的使用场景：

### 1. 单容器部署 (个人用户/Synology NAS)
- **文件**: `docker-compose.yml`
- **特点**: 单容器 + SQLite，简单易用
- **适用**: 个人用户、家庭NAS、轻量级部署

### 2. 开发环境部署
- **文件**: `docker-compose.dev.yml`
- **特点**: 开发模式，支持热重载
- **适用**: 开发调试

### 3. 微服务架构 (企业用户)
- **文件**: `docker-compose.microservices.yml`
- **特点**: 前后端分离 + PostgreSQL + Nginx
- **适用**: 企业级部署，需要完整功能

## 快速开始

### 单容器部署 (推荐新手)
```bash
docker-compose up -d
```

### 微服务部署
```bash
docker-compose -f docker-compose.microservices.yml up -d
```

## 文件结构 (已优化)

### 核心配置文件
- `docker-compose.yml` - 单容器部署
- `docker-compose.microservices.yml` - 微服务架构
- `docker-compose.dev.yml` - 开发环境

### Dockerfile
- `Dockerfile` - 单容器镜像
- `Dockerfile.backend` - 后端专用镜像
- `Dockerfile.dev` - 开发环境镜像
- `frontend/Dockerfile` - 前端专用镜像

### 实用脚本
- `run_docker_dev.sh` - 开发环境启动脚本
- `run_docker_dev_simple.sh` - 简化开发环境启动
- `fix-microservices.sh` - 微服务问题修复脚本
- `build-frontend.sh` - 前端本地构建脚本
- `add_demo_user.sh` - 添加演示用户脚本
- `dev_tools.sh` - 开发工具脚本

### Nginx配置
- `nginx/nginx.conf` - 单容器配置
- `nginx/nginx.microservices.conf` - 微服务配置

### 数据库脚本
- `init-scripts/` - PostgreSQL初始化脚本
- `manage_migrations.py` - 数据库迁移管理
- `migrate_database.py` - 数据库迁移脚本

## 选择建议

1. **个人用户**: 使用 `docker-compose.yml`
2. **企业用户**: 使用 `docker-compose.microservices.yml`
3. **开发调试**: 使用 `docker-compose.dev.yml`

## 端口说明

- **80**: Nginx反向代理 (微服务架构)
- **3000**: 前端服务 (微服务架构)
- **8888**: 后端API服务
- **5432**: PostgreSQL数据库 (微服务架构)
