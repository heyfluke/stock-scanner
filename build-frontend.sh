#!/bin/bash

# 前端本地构建脚本
set -e

echo "🚀 开始构建前端应用..."

# 进入前端目录
cd frontend

# 设置npm镜像
echo "📦 设置npm镜像源..."
npm config set registry https://registry.npmmirror.com/
npm config set timeout 600000
npm config set fetch-timeout 600000

# 清理并安装依赖
echo "📥 安装依赖..."
rm -rf node_modules package-lock.json
npm install

# 构建应用
echo "🔨 构建应用..."
npm run build

# 检查构建结果
if [ ! -d "dist" ]; then
    echo "❌ 构建失败：dist目录不存在"
    exit 1
fi

echo "✅ 前端构建完成！"
echo "📁 构建产物位置: frontend/dist/"

# 返回根目录
cd ..

echo "🎉 前端构建脚本执行完成！" 