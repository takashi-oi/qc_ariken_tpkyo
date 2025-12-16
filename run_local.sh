#!/usr/bin/env bash
set -euo pipefail

echo "== Arch ローカル環境セットアップ & 起動 =="

# 1) Python確認
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python3 が見つかりません。インストールしてください。" >&2
  exit 1
fi

# 2) 仮想環境作成・有効化
if [ ! -d ".venv" ]; then
  echo "-- venv 作成中 (.venv)"
  python3 -m venv .venv
fi
echo "-- venv 有効化"
source .venv/bin/activate

# 3) 依存インストール
pip install --upgrade pip
pip install -r requirements.txt

# 4) 必要ディレクトリ作成
mkdir -p db_folder data/master logs

cat <<'EOF'

[必要ならデータを復元]
- バックアップ: backup/<timestamp>/db_folder, data
- 例: cp -r backup/20251216_112356/db_folder/* db_folder/

EOF

# 5) Streamlit 起動
echo "-- Streamlit を起動します (Ctrl+C で停止)"
exec streamlit run Arch.py --server.address=0.0.0.0 --server.port=8501 --server.headless=true

