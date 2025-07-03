from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
import os

# 日本語フォントの設定
FONT_PATH = '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'
pdfmetrics.registerFont(TTFont('Hiragino', FONT_PATH))

def create_spec_pdf():
    # PDFファイルの作成
    c = canvas.Canvas("有研東京検査所_精度管理システム_仕様書.pdf", pagesize=A4)
    width, height = A4

    # タイトル
    c.setFont('Hiragino', 24)
    c.drawString(50*mm, 270*mm, "有研東京検査所 精度管理システム 仕様書")

    # 1. システム概要
    c.setFont('Hiragino', 16)
    c.drawString(20*mm, 250*mm, "1. システム概要")
    c.setFont('Hiragino', 12)
    text = """本システムは、株式会社有研東京検査所の感染症（病原性腸内細菌）検査における精度管理を目的とした
Webアプリケーションです。Streamlitを使用して構築されており、内部精度管理手法として
WESTGARD multi-Ruleを採用しています。"""
    y = 240*mm
    for line in text.split('\n'):
        c.drawString(20*mm, y, line)
        y -= 7*mm

    # 2. システム構成
    c.setFont('Hiragino', 16)
    c.drawString(20*mm, 220*mm, "2. システム構成")
    
    # 2.1 メインファイル
    c.setFont('Hiragino', 14)
    c.drawString(25*mm, 205*mm, "2.1 メインファイル")
    c.setFont('Hiragino', 12)
    text = """- qc_ariken_tokyo.py
  - システムのメインページ
  - ページ設定とナビゲーションメニューの提供
  - SQLiteデータベース接続の初期化"""
    y = 195*mm
    for line in text.split('\n'):
        c.drawString(25*mm, y, line)
        y -= 7*mm

    # 2.2 機能モジュール
    c.setFont('Hiragino', 14)
    c.drawString(25*mm, 170*mm, "2.2 機能モジュール（pages/）")
    c.setFont('Hiragino', 12)
    text = """1. pg01_qc_check.py
   - 管理試料測定結果の登録と確認機能
   - ファイルサイズ: 18KB
   - 行数: 419行

2. pg02_test_status.py
   - 測定状況の登録機能
   - ファイルサイズ: 12KB
   - 行数: 295行

3. pg03_qc_act_log.py
   - 精度管理試料測定結果の対応機能
   - ファイルサイズ: 18KB
   - 行数: 479行

4. pg04_confirmation_of_accuracy_control.py
   - 管理者向け精度管理実施状況確認機能
   - ファイルサイズ: 16KB
   - 行数: 425行

5. pg05_statical.py
   - 精度管理図の出力機能
   - ファイルサイズ: 7.6KB
   - 行数: 191行

6. pg99_master_table.py
   - マスターテーブル管理機能
   - ファイルサイズ: 1.5KB
   - 行数: 38行"""
    y = 160*mm
    for line in text.split('\n'):
        c.drawString(25*mm, y, line)
        y -= 7*mm

    # 3. データベース構成
    c.setFont('Hiragino', 16)
    c.drawString(20*mm, 100*mm, "3. データベース構成")
    c.setFont('Hiragino', 12)
    text = """- データベースファイル: your_database.db
- 接続方式: SQLite3
- スレッドセーフ対応: 有効（check_same_thread=True）"""
    y = 90*mm
    for line in text.split('\n'):
        c.drawString(25*mm, y, line)
        y -= 7*mm

    # 4. 依存関係
    c.setFont('Hiragino', 16)
    c.drawString(20*mm, 70*mm, "4. 依存関係")
    c.setFont('Hiragino', 12)
    text = """- 主要なライブラリ:
  - streamlit: Webアプリケーションフレームワーク
  - sqlite3: データベース管理
  - その他の依存関係は requirements.txt に記載"""
    y = 60*mm
    for line in text.split('\n'):
        c.drawString(25*mm, y, line)
        y -= 7*mm

    # 5. ログ管理
    c.setFont('Hiragino', 16)
    c.drawString(20*mm, 40*mm, "5. ログ管理")
    c.setFont('Hiragino', 12)
    text = """- アプリケーションログ: app.log
- QCチェックログ: qc_check.log"""
    y = 30*mm
    for line in text.split('\n'):
        c.drawString(25*mm, y, line)
        y -= 7*mm

    # 6. ディレクトリ構造
    c.setFont('Hiragino', 16)
    c.drawString(20*mm, 20*mm, "6. ディレクトリ構造")
    c.setFont('Hiragino', 12)
    text = """- pages/: 機能モジュール
- docs/: ドキュメント
- db_folder/: データベース関連ファイル
- master_folder/: マスターデータ
- src/: ソースコード
- .vscode/: VSCode設定
- .venv/: 仮想環境"""
    y = 10*mm
    for line in text.split('\n'):
        c.drawString(25*mm, y, line)
        y -= 7*mm

    c.save()

if __name__ == "__main__":
    create_spec_pdf() 