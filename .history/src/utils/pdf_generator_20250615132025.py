from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import markdown
import re

def convert_markdown_to_pdf(markdown_file, pdf_file):
    """MarkdownファイルをPDFに変換する"""
    # Markdownファイルを読み込む
    with open(markdown_file, 'r', encoding='utf-8') as f:
        markdown_text = f.read()

    # MarkdownをHTMLに変換
    html = markdown.markdown(markdown_text)

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
        fontSize=24,
        spaceAfter=30
    ))
    styles.add(ParagraphStyle(
        name='CustomHeading',
        parent=styles['Heading2'],
        fontSize=18,
        spaceAfter=20
    ))
    styles.add(ParagraphStyle(
        name='CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=14,
        spaceAfter=15
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
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
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