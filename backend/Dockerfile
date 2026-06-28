FROM python:3.13-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY app/ ./app/
COPY uploads/ ./uploads/

# 创建数据目录
RUN mkdir -p /app/data

EXPOSE 8000

# 使用环境变量指定数据库路径到持久化目录
ENV DATABASE_URL=sqlite+aiosqlite:////app/data/xinan_dawang.db

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
