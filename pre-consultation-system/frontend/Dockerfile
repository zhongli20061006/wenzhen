# ============ Build Stage ============
FROM node:22-alpine AS builder

WORKDIR /app

# 先拷贝依赖文件，利用 Docker 层缓存
COPY package.json package-lock.json ./
RUN npm ci

# 拷贝源码并构建
COPY vite.config.js ./
COPY index.html ./
COPY public/ ./public/
COPY src/ ./src/

RUN npm run build


# ============ Serve Stage ============
FROM nginx:1.27-alpine

# 删除默认配置
RUN rm -f /etc/nginx/conf.d/default.conf

# 拷贝自定义 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 拷贝构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
