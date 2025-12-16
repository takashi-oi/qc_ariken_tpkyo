# Python 3.13の公式イメージを使用
FROM python:3.13-slim

# メタデータの設定
LABEL maintainer="QC ARIKEN TOKYO"
LABEL description="有研東京検査所 精度管理システム - Docker環境"

# 作業ディレクトリを設定
WORKDIR /app

# システムパッケージの更新と必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をコピー
COPY requirements.txt pyproject.toml ./

# pipのアップグレードと依存関係のインストール
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# アプリケーションのソースコードをコピー
COPY . .

# 必要なディレクトリを作成
RUN mkdir -p db_folder logs data/master

# ポート8501を公開（Streamlitのデフォルトポート）
EXPOSE 8501

# Streamlitアプリケーションを起動
# ホストを0.0.0.0に設定して外部からアクセス可能にする
CMD ["streamlit", "run", "Arch.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]

