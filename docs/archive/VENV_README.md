# 仮想環境での実行手順 (Python 3.12.7)

## 概要
株式会社 ARCHArch 精度管理システムをPython 3.12.7の仮想環境で実行するための手順です。

## 前提条件
- Python 3.12.7がインストールされていること
- macOS/Linux環境（Windowsの場合は適宜コマンドを変更してください）

## セットアップ手順

### 1. 仮想環境の作成
```bash
python3.12 -m venv venv
```

### 2. 仮想環境のアクティベート
```bash
source venv/bin/activate
```

### 3. 依存関係のインストール
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 実行方法

### 方法1: 自動起動スクリプトを使用
```bash
./run_venv.sh
```

### 方法2: 手動で実行
```bash
# 仮想環境をアクティベート
source venv/bin/activate

# Pythonバージョンの確認
python --version

# Streamlitアプリケーションを起動
streamlit run Arch.py
```

## アクセス方法
アプリケーションが起動したら、ブラウザで以下のURLにアクセスしてください：
```
http://localhost:8501
```

## 仮想環境の終了
```bash
deactivate
```

## トラブルシューティング

### 仮想環境が見つからない場合
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 依存関係のエラーが発生した場合
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### ポートが使用中の場合
```bash
streamlit run Arch.py --server.port 8502
```

### Python 3.12.7が見つからない場合
```bash
# pyenvを使用している場合
pyenv install 3.12.7
pyenv local 3.12.7

# または、システムのPythonを使用
python3 -m venv venv
```

## 注意事項
- このプロジェクトはPython 3.12.7で動作確認済みです
- 仮想環境を使用することで、システムのPython環境に影響を与えることなくアプリケーションを実行できます
- プロジェクトを終了する際は、必ず `deactivate` コマンドで仮想環境を終了してください
- 新しい依存関係を追加した場合は、`requirements.txt` を更新してください 