# 使用 Python 3.10 作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目所有文件到容器
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000"]