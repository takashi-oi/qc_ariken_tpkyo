from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import markdown
import re
import os


def register_fonts():
    """日本語フォントを登録する"""
    # フォントファイルのパスを設定
    font_path = os.path.join(os.path.dirname(__file__), '..', '..', 'fonts')
    
    # フォントファイルが存在しない場合は作成
    if not os.path.exists(font_path):
        os.makedirs(font_path)
    
    # IPAフォントをダウンロード（存在しない場合）
    ipa_font_path = os.path.join(font_path, 'ipaexg.ttf')
    if not os.path.exists(ipa_font_path):
        import urllib.request
        url = 'https://moji.or.jp/wp-content/ipafont/IPAexfont/IPAexfont00401/ipaexg00401.zip'
        zip_path = os.path.join(font_path, 'ipaexg.zip')
        urllib.request.urlretrieve(url, zip_path)
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(font_path)
        os.remove(zip_path)
    
    # フォントを登録
    pdfmetrics.registerFont(TTFont('IPAexGothic', ipa_font_path))


def convert_markdown_to_pdf(markdown_file, pdf_file):
    """MarkdownファイルをPDFに変換する"""
    # フォントを登録
    register_fonts()
    
    # Markdownファイルを読み込む
    with open(markdown_file, 'r', encoding='utf-8') as f:
        markdown_text = f.read()

    # PDFドキュメントを作成
    doc = SimpleDocTemplate(
        pdf_file,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    # スタイルを設定
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Heading1'],
        fontName='IPAexGothic',
        fontSize=24,
        spaceAfter=30
    ))
    styles.add(ParagraphStyle(
        name='CustomHeading',
        parent=styles['Heading2'],
        fontName='IPAexGothic',
        fontSize=18,
        spaceAfter=20
    ))
    styles.add(ParagraphStyle(
        name='CustomSubHeading',
        parent=styles['Heading3'],
        fontName='IPAexGothic',
        fontSize=14,
        spaceAfter=15
    ))
    styles.add(ParagraphStyle(
        name='Normal',
        parent=styles['Normal'],
        fontName='IPAexGothic',
        fontSize=12,
        leading=14
    ))

    # コンテンツを格納するリスト
    content = []

    # テキストを行ごとに処理
    lines = markdown_text.split('\n')
    current_table = []
    in_table = False

    for line in lines:
        # 見出しの処理
        if line.startswith('#'):
            level = len(re.match('^#+', line).group())
            text = line.lstrip('#').strip()
            if level == 1:
                content.append(Paragraph(text, styles['CustomTitle']))
            elif level == 2:
                content.append(Paragraph(text, styles['CustomHeading']))
            else:
                content.append(Paragraph(text, styles['CustomSubHeading']))
            content.append(Spacer(1, 12))

        # テーブルの処理
        elif line.startswith('|'):
            if not in_table:
                in_table = True
            current_table.append([cell.strip() for cell in line.split('|')[1:-1]])
        elif in_table and not line.strip():
            if current_table:
                table = Table(current_table)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'IPAexGothic'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'IPAexGothic'),
                    ('FONTSIZE', (0, 1), (-1, -1), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                content.append(table)
                content.append(Spacer(1, 12))
                current_table = []
                in_table = False

        # 通常のテキストの処理
        elif line.strip():
            content.append(Paragraph(line.strip(), styles['Normal']))
            content.append(Spacer(1, 12))

    # PDFを生成
    doc.build(content)


if __name__ == '__main__':
    convert_markdown_to_pdf('docs/specification.md', 'docs/specification.pdf') 