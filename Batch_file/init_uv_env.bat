@echo off
REM UV環境の初期化スクリプト
echo === 有研東京検査所 精度管理システム ===
echo UV環境の初期化を開始します...

REM UVがインストールされているかチェック
where uv >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo エラー: UVがインストールされていません。
    echo 以下のコマンドでUVをインストールしてください：
    echo   winget install --id=astral-sh.uv  -e
    echo または: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    pause
    exit /b 1
)

echo UVバージョン:
uv --version

REM プロジェクトディレクトリに移動
cd /d %~dp0\..

REM 既存のUV環境がある場合は削除
if exist ".venv" (
    echo 既存のUV環境が見つかりました。削除して再作成します...
    rmdir /s /q .venv
)

REM UV環境の作成
echo UV環境を作成中...
uv venv --python 3.13

if %ERRORLEVEL% NEQ 0 (
    echo エラー: UV環境の作成に失敗しました。
    pause
    exit /b 1
)

REM 仮想環境を有効化
echo 仮想環境を有効化中...
call .venv\Scripts\activate.bat

REM Pythonバージョンの確認
echo Pythonバージョン:
python --version

REM 依存関係のインストール
echo 依存関係をインストール中...
uv pip install --upgrade pip
uv pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo エラー: 依存関係のインストールに失敗しました。
    pause
    exit /b 1
)

echo.
echo ✅ 初期設定が完了しました！
echo.
echo 次のステップ:
echo   run_uv.bat を実行してアプリケーションを起動してください
echo.
pause

