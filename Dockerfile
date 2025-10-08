# 阶段一: 构建Vue前端
FROM node:18 as frontend-builder

# 设置工作目录
WORKDIR /app/frontend

# 设置npm源（可通过构建参数配置）
ARG NPM_REGISTRY=http://mirrors.cloud.tencent.com/npm/
ENV NPM_REGISTRY=${NPM_REGISTRY}

# 复制前端项目文件
COPY frontend/package.json ./

# 设置npm配置
RUN npm config set registry ${NPM_REGISTRY} && \
    npm config set fetch-timeout 600000 && \
    npm config set fetch-retry-mintimeout 10000 && \
    npm config set fetch-retry-maxtimeout 60000 && \
    npm config set fetch-retries 10

# 复制前端源代码
COPY frontend/ ./ 

# 清理可能存在的package-lock.json并重新安装依赖以避免版本冲突
RUN rm -rf package-lock.json node_modules && \
    npm install --no-audit --no-fund

# 构建前端应用
RUN npm run build

# 阶段二: 构建Python后端
FROM python:3.10-slim as backend-builder

# 设置工作目录
WORKDIR /app
ENV DEBIAN_FRONTEND=noninteractive
# 安装系统依赖和构建依赖
RUN apt-get update && apt-get install -y \
    libgl1 \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY requirements.txt /app/

# 安装 Python 依赖
RUN pip install --no-cache-dir --user -r requirements.txt

# 阶段三: 运行阶段
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    libgl1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制Python依赖
COPY --from=backend-builder /root/.local /root/.local

# 确保脚本路径在PATH中
ENV PATH=/root/.local/bin:$PATH

# 设置环境变量
ENV PYTHONPATH=/app

# 复制应用代码
COPY . /app/

# 从前端构建阶段复制生成的静态文件到后端的前端目录
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# 创建数据目录用于SQLite数据库持久化
RUN mkdir -p /app/data

# 设置数据库环境变量
ENV DATABASE_URL=sqlite:///data/stock_scanner.db

# 复制并设置启动脚本权限
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# 暴露端口
EXPOSE 8888

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8888/api/config || exit 1

# 启动命令
CMD ["/app/docker-entrypoint.sh"]