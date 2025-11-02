@echo off
REM UV環境での起動スクリプト
echo === 有研東京検査所 精度管理システム ===
echo UV環境での起動を開始します...

REM プロジェクトディレクトリに移動
cd /d %~dp0\..

REM UV環境が存在するかチェック
if not exist ".venv" (
    echo エラー: UV環境が見つかりません。
    echo 以下のコマンドでUV環境を初期化してください：
    echo   init_uv_env.bat
    pause
    exit /b 1
)

REM 仮想環境を有効化
echo 仮想環境を有効化中...
call .venv\Scripts\activate.bat

REM Pythonバージョンの確認
echo Pythonバージョン:
python --version

REM 依存関係の確認
echo 依存関係を確認中...
python -c "import streamlit" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 依存関係がインストールされていません。インストール中...
    uv pip install -r requirements.txt
)

REM Streamlitアプリケーションを起動
echo Streamlitアプリケーションを起動中...
echo ブラウザで http://localhost:8501 にアクセスしてください
echo.
echo アプリケーションを停止するには Ctrl+C を押してください
echo.

streamlit run qc_ariken_tokyo.py

pause


