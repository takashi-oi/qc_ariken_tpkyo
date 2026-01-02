#!/bin/bash
# 仮想環境のStreamlitを直接実行するスクリプト

# ディレクトリを移動
cd "$(dirname "$0")"

# 実行
if [ -f "venv/bin/python" ]; then
    echo "Starting Arch System..."
    venv/bin/python -m streamlit run Arch.py
else
    echo "Error: venv not found. Please run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi
