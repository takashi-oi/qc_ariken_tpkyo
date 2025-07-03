from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
import os

# 日本語フォントの設定（Arial Unicode MSを使用）
FONT_PATH = '/System/Library/Fonts/Arial Unicode.ttf'
pdfmetrics.registerFont(TTFont('ArialUnicode', FONT_PATH))

def create_spec_pdf():
    # PDFファイルの作成
    c = canvas.Canvas("有研東京検査所_精度管理システム_仕様書.pdf", pagesize=A4)
    width, height = A4

    # タイトル
    c.setFont('ArialUnicode', 24)
    c.drawString(50*mm, 270*mm, "有研東京検査所 精度管理システム 仕様書")

    # 1. システム概要
    c.setFont('ArialUnicode', 16)
    c.drawString(20*mm, 250*mm, "1. システム概要")
    c.setFont('ArialUnicode', 12)
    text = """本システムは、株式会社有研東京検査所の感染症（病原性腸内細菌）検査における精度管理を目的とした\nWebアプリケーションです。Streamlitを使用して構築されており、内部精度管理手法として\nWESTGARD multi-Ruleを採用しています。"""
    y = 240*mm
    for line in text.split('\n'):
        c.drawString(20*mm, y, line)
        y -= 7*mm

    # 2. システム構成
    c.setFont('ArialUnicode', 16)
    c.drawString(20*mm, 220*mm, "2. システム構成")
    
    # 2.1 メインファイル
    c.setFont('ArialUnicode', 14)
    c.drawString(25*mm, 205*mm, "2.1 メインファイル")
    c.setFont('ArialUnicode', 12)
    text = """- qc_ariken_tokyo.py\n  - システムのメインページ\n  - ページ設定とナビゲーションメニューの提供\n  - SQLiteデータベース接続の初期化"""
    y = 195*mm
    for line in text.split('\n'):
        c.drawString(25*mm, y, line)
        y -= 7*mm

    # 2.2 機能モジュール
    c.setFont('ArialUnicode', 14)
    c.drawString(25*mm, 170*mm, "2.2 機能モジュール（pages/）")
    c.setFont('ArialUnicode', 12)
    text = """1. pg01_qc_check.py\n   - 管理試料測定結果の登録と確認機能\n   - ファイルサイズ: 18KB\n   - 行数: 419行\n\n2. pg02_test_status.py\n   - 測定状況の登録機能\n   - ファイルサイズ: 12KB\n   - 行数: 295行\n\n3. pg03_qc_act_log.py\n   - 精度管理試料測定結果の対応機能\n   - ファイルサイズ: 18KB\n   - 行数: 479行\n\n4. pg04_confirmation_of_accuracy_control.py\n   - 管理者向け精度管理実施状況確認機能\n   - ファイルサイズ: 16KB\n   - 行数: 425行\n\n5. pg05_statical.py\n   - 精度管理図の出力機能\n   - ファイルサイズ: 7.6KB\n   - 行数: 191行\n\n6. pg99_master_table.py\n   - マスターテーブル管理機能\n   - ファイルサイズ: 1.5KB\n   - 行数: 38行"""
    y = 160*mm
    for line in text.split('\n'):
        c.drawString(25*mm, y, line)
        y -= 7*mm

    # 3. データベース構成
    c.setFont('ArialUnicode', 16)
    c.drawString(20*mm, 100*mm, "3. データベース構成")
    c.setFont('ArialUnicode', 12)
    text = """- データベースファイル: your_database.db\n- 接続方式: SQLite3\n- スレッドセーフ対応: 有効（check_same_thread=True）"""
    y = 90*mm
    for line in text.split('\n'):
        c.drawString(25*mm, y, line)
        y -= 7*mm

    # 4. 依存関係
    c.setFont('ArialUnicode', 16)
    c.drawString(20*mm, 70*mm, "4. 依存関係")
    c.setFont('ArialUnicode', 12)
    text = """- 主要なライブラリ:\n  - streamlit: Webアプリケーションフレームワーク\n  - sqlite3: データベース管理\n  - その他の依存関係は requirements.txt に記載"""
    y = 60*mm
    for line in text.split('\n'):
        c.drawString(25*mm, y, line)
        y -= 7*mm

    # 5. ログ管理
    c.setFont('ArialUnicode', 16)
    c.drawString(20*mm, 40*mm, "5. ログ管理")
    c.setFont('ArialUnicode', 12)
    text = """- アプリケーションログ: app.log\n- QCチェックログ: qc_check.log"""
    y = 30*mm
    for line in text.split('\n'):
        c.drawString(25*mm, y, line)
        y -= 7*mm

    # 6. ディレクトリ構造
    c.setFont('ArialUnicode', 16)
    c.drawString(20*mm, 20*mm, "6. ディレクトリ構造")
    c.setFont('ArialUnicode', 12)
    text = """- pages/: 機能モジュール\n- docs/: ドキュメント\n- db_folder/: データベース関連ファイル\n- master_folder/: マスターデータ\n- src/: ソースコード\n- .vscode/: VSCode設定\n- .venv/: 仮想環境"""
    y = 10*mm
    for line in text.split('\n'):
        c.drawString(25*mm, y, line)
        y -= 7*mm

    c.save()

if __name__ == "__main__":
    create_spec_pdf() 