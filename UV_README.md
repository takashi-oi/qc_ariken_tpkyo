# UV環境での実行手順

## 概要
有研東京検査所 精度管理システムをUV環境で実行するための手順です。
UVは、pipとvenvの高速な代替となるRustで書かれたPythonパッケージマネージャーです。

## UVとは
- **高速**: pipより10-100倍高速なパッケージインストール
- **依存関係解決**: 高速で正確な依存関係の解決
- **互換性**: pip/venvと同じコマンド形式で使用可能
- **プロジェクト管理**: pyproject.tomlベースの依存関係管理に対応

## 前提条件
- Python 3.13がインストールされていること
- UVがインストールされていること
- macOS/Linux環境（Windowsの場合は適宜コマンドを変更してください）

### UVのインストール

#### macOS/Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### macOS (Homebrew)
```bash
brew install uv
```

#### Windows
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

インストール後、シェルを再起動するか、以下のコマンドでパスを通してください：
```bash
source $HOME/.cargo/env
```

## 初期セットアップ

### 方法1: 自動セットアップスクリプトを使用（推奨）

```bash
# 実行権限を付与
chmod +x init_uv_env.sh

# UV環境の初期化
./init_uv_env.sh
```

このスクリプトは以下を実行します：
- UV環境（.venv）の作成
- 依存関係のインストール
- Pythonバージョンの確認

### 方法2: 手動セットアップ

#### 1. UV環境の作成
```bash
uv venv --python 3.13
```

#### 2. 仮想環境のアクティベート
```bash
source .venv/bin/activate
```

#### 3. 依存関係のインストール
```bash
uv pip install --upgrade pip
uv pip install -r requirements.txt
```

## 実行方法

### 方法1: 自動起動スクリプトを使用（推奨）

```bash
# 実行権限を付与
chmod +x run_uv.sh

# アプリケーションの起動
./run_uv.sh
```

### 方法2: 手動で実行

```bash
# 仮想環境をアクティベート
source .venv/bin/activate

# Pythonバージョンの確認
python --version

# Streamlitアプリケーションを起動
streamlit run qc_ariken_tokyo.py
```

### 方法3: UV runを使用（アクティベート不要）

```bash
uv run streamlit run qc_ariken_tokyo.py
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

## パッケージの管理

### 新しいパッケージの追加
```bash
# 仮想環境をアクティベート
source .venv/bin/activate

# パッケージのインストール
uv pip install <package-name>

# requirements.txtの更新
uv pip freeze > requirements.txt
```

### パッケージの更新
```bash
source .venv/bin/activate
uv pip install --upgrade -r requirements.txt
```

## トラブルシューティング

### UV環境が見つからない場合
```bash
./init_uv_env.sh
```

### 依存関係のエラーが発生した場合
```bash
source .venv/bin/activate
uv pip install --upgrade pip
uv pip install -r requirements.txt --force-reinstall
```

### ポートが使用中の場合
```bash
streamlit run qc_ariken_tokyo.py --server.port 8502
```

### Python 3.13が見つからない場合
```bash
# pyenvを使用している場合
pyenv install 3.13.2
pyenv local 3.13.2

# UV環境を再作成
uv venv --python 3.13
```

### UVコマンドが見つからない場合
```bash
# パスの確認
echo $PATH

# UVの再インストール
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

## 従来のvenvからの移行

### 既存のvenvフォルダがある場合
```bash
# 既存のvenvフォルダを削除またはリネーム
mv venv venv_old

# UV環境の初期化
./init_uv_env.sh
```

## 注意事項
- このプロジェクトはPython 3.13で動作確認済みです
- UV環境（.venv）を使用することで、システムのPython環境に影響を与えることなくアプリケーションを実行できます
- プロジェクトを終了する際は、必ず `deactivate` コマンドで仮想環境を終了してください
- 新しい依存関係を追加した場合は、`requirements.txt` を更新してください
- UV環境は`.venv`フォルダに作成されます（従来の`venv`フォルダとは異なります）

## UV環境の利点

### 1. 高速なインストール
従来のpipと比較して、パッケージのインストールが大幅に高速です。

### 2. 正確な依存関係解決
UVは依存関係の競合を正確に検出し、解決します。

### 3. プロジェクト管理
`pyproject.toml`を使用した依存関係管理に対応しており、将来的な拡張が容易です。

### 4. 互換性
既存の`requirements.txt`ファイルと互換性があり、既存プロジェクトを簡単に移行できます。

