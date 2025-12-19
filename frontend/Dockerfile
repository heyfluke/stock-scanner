# 使用官方Node.js镜像作为基础镜像
FROM node:18-alpine

# 设置工作目录
WORKDIR /app

# 设置官方npm registry
RUN npm config set registry https://registry.npmjs.org/

# 安装构建依赖（用于编译原生模块）
RUN apk add --no-cache python3 make g++

# 复制package.json和package-lock.json（使用lock文件确保依赖版本一致）
COPY package.json package-lock.json* ./

# 安装依赖（使用package-lock.json确保版本一致）
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund

# 复制源代码
COPY . .

# 构建应用
RUN npm run build

# 使用nginx来服务静态文件
FROM nginx:alpine

# 复制构建产物到nginx目录
COPY --from=0 /app/dist /usr/share/nginx/html

# 复制nginx配置
COPY nginx.conf /etc/nginx/nginx.conf

# 暴露端口
EXPOSE 80

# 启动nginx
CMD ["nginx", "-g", "daemon off;"] 