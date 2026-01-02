#!/usr/bin/env bash
set -euo pipefail

echo "== Arch Docker 起動 =="

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker が見つかりません。インストールしてください。" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker デーモンが起動していません。Docker Desktop などを起動してください。" >&2
  exit 1
fi

echo "-- 既存コンテナ停止・削除"
docker-compose down || true

echo "-- ビルド＆起動"
docker-compose up --build -d

echo "-- 状態確認"
docker ps | grep arch || true

cat <<'EOF'

起動完了:
- ブラウザで http://localhost:8501 を開いてください
- ログ確認: docker-compose logs -f
- 停止: docker-compose down

EOF




