FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 必要なパッケージ（PostgreSQLなど使ってるならlibpq-devが必要）
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Python 依存関係インストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのコード
COPY . .

# 環境変数と実行コマンド
ENV PORT=8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]