# 使用官方Node.js镜像作为基础镜像
FROM node:18-alpine

# 设置工作目录
WORKDIR /app

# 设置官方npm registry
RUN npm config set registry https://registry.npmjs.org/

# 复制package.json
COPY package.json ./

# 清理缓存并安装依赖（不使用package-lock.json）
RUN npm cache clean --force && \
    npm install --no-audit --no-fund

# 复制源代码
COPY . .

# 彻底解决esbuild版本问题
RUN rm -rf node_modules && \
    npm cache clean --force && \
    npm install --no-audit --no-fund

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