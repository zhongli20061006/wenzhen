FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖（mysqlclient 编译依赖 + wget 用于健康检查）
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        default-libmysqlclient-dev \
        pkg-config \
        wget \
    && rm -rf /var/lib/apt/lists/*

# 先拷贝依赖文件，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝应用代码
COPY . .

# entrypoint 脚本需要可执行权限
RUN chmod +x docker-entrypoint.sh

# 创建非 root 用户运行服务
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/docs')" || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
