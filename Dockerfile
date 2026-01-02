# ベースイメージ
FROM python:3.13-slim

# メタデータ
LABEL maintainer="Lab.Arch"
LABEL description="Arch 管理システム Docker 環境"

# 作業ディレクトリ
WORKDIR /app

# 必要パッケージ
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 依存関係をコピーしてインストール
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# 必要ディレクトリ
RUN mkdir -p db_folder logs data/master

# ポート
EXPOSE 8501

# Streamlit 起動
CMD ["streamlit", "run", "Arch.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]

