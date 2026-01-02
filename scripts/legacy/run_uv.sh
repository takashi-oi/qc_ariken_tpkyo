#!/bin/bash

# 株式会社 ARCHArch 精度管理システム - UV環境起動スクリプト

echo "=== 株式会社 ARCHArch 精度管理システム ==="
echo "UV環境での起動を開始します..."

# プロジェクトディレクトリに移動
cd "$(dirname "$0")"

# UV環境が存在するかチェック
if [ ! -d "venv" ]; then
    echo "エラー: UV環境が見つかりません。"
    echo "以下のコマンドでUV環境を初期化してください："
    echo "  ./init_uv_env.sh"
    exit 1
fi

# 仮想環境をアクティベート
echo "仮想環境をアクティベート中..."
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "エラー: 仮想環境が見つかりません。"
    echo "以下のコマンドで仮想環境を作成してください："
    echo "  python3.14 -m venv .venv"
    echo "  .venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Pythonバージョンの確認
echo "Pythonバージョン: $(python --version)"

# 依存関係の確認
echo "依存関係を確認中..."
if command -v python &> /dev/null; then
    if ! python -c "import streamlit" 2>/dev/null; then
        echo "依存関係がインストールされていません。インストール中..."
        uv pip install -r requirements.txt
    fi
    
    # duckdbの確認
    if ! python -c "import duckdb" 2>/dev/null; then
        echo "duckdbがインストールされていません。インストール中..."
        uv pip install duckdb duckdb-engine
    fi
    
    # Streamlitアプリケーションを起動
    echo "Streamlitアプリケーションを起動中..."
    echo "ブラウザで http://localhost:8501 にアクセスしてください"
    echo ""
    echo "アプリケーションを停止するには Ctrl+C を押してください"
    echo ""
    
    python -m streamlit run Arch.py
else
    echo "Pythonが見つかりません。UV環境を使用して起動します..."
    uv run streamlit run Arch.py
fi


