FROM python:3.12-slim

WORKDIR /app

# uv をインストール
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 依存関係ファイルをコピー（キャッシュ活用）
COPY pyproject.toml uv.lock ./

# 本番用依存関係をインストール
RUN uv sync --frozen --no-cache --no-dev

# アプリケーションコードをコピー
COPY src/ ./src/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
