#!/usr/bin/env python3
"""Chuyển ``bao-cao-backend.md`` sang PDF (A4) bằng ReportLab.

Cách chạy::

    pip install reportlab
    python report/build_pdf.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

from markdown_blocks import Block, parse

REPORT_DIR = Path(__file__).resolve().parent
SOURCE = REPORT_DIR / "bao-cao-backend.md"
TARGET = REPORT_DIR / "bao-cao-backend.pdf"

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
MONO_FONT = Path("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf")
INK = colors.HexColor("#16202E")
MUTED = colors.HexColor("#556073")
ACCENT = colors.HexColor("#1D4ED8")
RULE = colors.HexColor("#C9D3E0")
CODE_BG = colors.HexColor("#F3F5F9")
CODE_BORDER = colors.HexColor("#DDE3EC")
HEADER_BG = colors.HexColor("#E8EEF9")

INLINE_PATTERN = re.compile(r"(\*\*.+?\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))")

PAGE_MARGIN_LEFT = 2.2 * cm
PAGE_MARGIN_RIGHT = 1.8 * cm
CONTENT_WIDTH = A4[0] - PAGE_MARGIN_LEFT - PAGE_MARGIN_RIGHT


def register_fonts() -> None:
    fonts = {
        "DejaVu": FONT_DIR / "DejaVuSans.ttf",
        "DejaVuBold": FONT_DIR / "DejaVuSans-Bold.ttf",
        "Mono": MONO_FONT,
    }
    for name, path in fonts.items():
        if not path.is_file():
            raise FileNotFoundError(f"Thiếu phông {path}")
        pdfmetrics.registerFont(TTFont(name, str(path)))
    pdfmetrics.registerFontFamily(
        "DejaVu", normal="DejaVu", bold="DejaVuBold", italic="DejaVu", boldItalic="DejaVuBold"
    )


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(text: str) -> str:
    """Chuyển **đậm**, `mã`, [liên kết](url) sang thẻ ReportLab."""
    pieces: list[str] = []
    position = 0
    for match in INLINE_PATTERN.finditer(text):
        if match.start() > position:
            pieces.append(escape(text[position : match.start()]))
        token = match.group(0)
        if token.startswith("**"):
            pieces.append(f"<b>{escape(token[2:-2])}</b>")
        elif token.startswith("`"):
            pieces.append(
                f'<font name="Mono" color="#9A3412" size="9">{escape(token[1:-1])}</font>'
            )
        else:
            label = token[1 : token.index("]")]
            url = token[token.index("(") + 1 : -1]
            pieces.append(f'<link href="{escape(url)}" color="#1D4ED8">{escape(label)}</link>')
            if url and url != label:
                pieces.append(f' <font color="#556073" size="8.5">({escape(url)})</font>')
        position = match.end()
    if position < len(text):
        pieces.append(escape(text[position:]))
    return "".join(pieces)


def build_styles() -> dict[str, ParagraphStyle]:
    body = ParagraphStyle(
        "body",
        fontName="DejaVu",
        fontSize=10.5,
        leading=16,
        alignment=TA_JUSTIFY,
        spaceAfter=7,
        textColor=INK,
    )
    return {
        "body": body,
        "h1": ParagraphStyle(
            "h1", fontName="DejaVuBold", fontSize=15, leading=20, spaceBefore=16,
            spaceAfter=7, textColor=INK,
        ),
        "h2": ParagraphStyle(
            "h2", fontName="DejaVuBold", fontSize=12.5, leading=17, spaceBefore=12,
            spaceAfter=5, textColor=INK,
        ),
        "h3": ParagraphStyle(
            "h3", fontName="DejaVuBold", fontSize=11, leading=15, spaceBefore=9,
            spaceAfter=4, textColor=INK,
        ),
        "bullet": ParagraphStyle(
            "bullet", parent=body, leftIndent=14, bulletIndent=4, bulletFontName="DejaVu",
            bulletFontSize=10.5, spaceAfter=4,
        ),
        "numbered": ParagraphStyle("numbered", parent=body, leftIndent=16, spaceAfter=4),
        "code": ParagraphStyle(
            "code", fontName="Mono", fontSize=8.2, leading=10.6, textColor=INK
        ),
        "cell": ParagraphStyle(
            "cell", fontName="DejaVu", fontSize=8.6, leading=11.2, textColor=INK
        ),
        "cell_header": ParagraphStyle(
            "cell_header", fontName="DejaVuBold", fontSize=8.6, leading=11.2, textColor=INK
        ),
        "cover_title": ParagraphStyle(
            "cover_title", fontName="DejaVuBold", fontSize=22, leading=29,
            alignment=TA_CENTER, textColor=INK,
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub", fontName="DejaVuBold", fontSize=13, leading=19,
            alignment=TA_CENTER, textColor=ACCENT, spaceBefore=10,
        ),
        "cover_label": ParagraphStyle(
            "cover_label", fontName="DejaVuBold", fontSize=10, leading=15, textColor=MUTED
        ),
        "cover_value": ParagraphStyle(
            "cover_value", fontName="DejaVu", fontSize=10, leading=15, textColor=INK
        ),
    }


def column_widths(rows: list[list[str]], columns: int) -> list[float]:
    weights = []
    for index in range(columns):
        longest = max(
            (len(row[index]) for row in rows if index < len(row)),
            default=4,
        )
        weights.append(max(6, min(longest, 32)))
    total = sum(weights)
    widths = [CONTENT_WIDTH * weight / total for weight in weights]
    minimum = min(2.1 * cm, CONTENT_WIDTH / columns)
    widths = [max(minimum, width) for width in widths]
    scale = CONTENT_WIDTH / sum(widths)
    return [width * scale for width in widths]


def make_table(rows: list[list[str]], styles: dict[str, ParagraphStyle]) -> Table:
    columns = max(len(row) for row in rows)
    data = []
    for row_index, row in enumerate(rows):
        cells = []
        style = styles["cell_header"] if row_index == 0 else styles["cell"]
        for column_index in range(columns):
            text = row[column_index] if column_index < len(row) else ""
            cells.append(Paragraph(inline(text), style))
        data.append(cells)

    table = Table(
        data,
        colWidths=column_widths(rows, columns),
        repeatRows=1,
        hAlign="CENTER",
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, RULE),
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def make_code_block(code: str, styles: dict[str, ParagraphStyle]) -> Table:
    preformatted = Preformatted(code, styles["code"])
    block = Table([[preformatted]], colWidths=[CONTENT_WIDTH])
    block.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
                ("BOX", (0, 0), (-1, -1), 0.5, CODE_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return block


def make_cover(block: Block, styles: dict[str, ParagraphStyle]) -> list:
    story: list = [Spacer(1, 3.2 * cm)]
    story.append(Paragraph(escape(block.text.upper()), styles["cover_title"]))
    story.append(Paragraph(escape(block.subtitle), styles["cover_sub"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.9, color=ACCENT, spaceAfter=14))

    rows = []
    for line in block.meta:
        match = re.match(r"^\*\*(.+?):\*\*\s*(.+)$", line)
        if match:
            rows.append(
                [
                    Paragraph(escape(match.group(1)), styles["cover_label"]),
                    Paragraph(inline(match.group(2)), styles["cover_value"]),
                ]
            )
    table = Table(rows, colWidths=[4.3 * cm, 9.7 * cm], hAlign="CENTER")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)
    story.append(PageBreak())
    return story


def decorate(canvas, doc) -> None:
    if doc.page == 1:  # bìa không cần header/footer
        return
    canvas.saveState()
    canvas.setFont("DejaVu", 8)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(
        A4[0] - PAGE_MARGIN_RIGHT,
        A4[1] - 1.15 * cm,
        "Báo cáo backend — Gợi ý từ khóa bằng Levenshtein",
    )
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(PAGE_MARGIN_LEFT, A4[1] - 1.35 * cm, A4[0] - PAGE_MARGIN_RIGHT, A4[1] - 1.35 * cm)
    canvas.drawCentredString(A4[0] / 2, 0.95 * cm, f"Trang {doc.page}")
    canvas.restoreState()


def build(source: Path, target: Path) -> None:
    register_fonts()
    styles = build_styles()
    blocks = parse(source)

    document = BaseDocTemplate(
        str(target),
        pagesize=A4,
        leftMargin=PAGE_MARGIN_LEFT,
        rightMargin=PAGE_MARGIN_RIGHT,
        topMargin=2.0 * cm,
        bottomMargin=1.7 * cm,
        title="Báo cáo backend — Gợi ý từ khóa bằng Levenshtein",
        author="Nhóm thực hiện",
        subject="Bài tập giữa kỳ môn Phân tích và Thiết kế Giải thuật",
    )
    frame = Frame(
        document.leftMargin,
        document.bottomMargin,
        document.width,
        document.height,
        id="normal",
    )
    document.addPageTemplates([PageTemplate(id="content", frames=[frame], onPage=decorate)])

    story: list = []
    for block in blocks:
        if block.kind == "cover":
            story.extend(make_cover(block, styles))
            story.append(Spacer(1, 0.2 * cm))
        elif block.kind == "heading":
            style = {2: styles["h1"], 3: styles["h2"], 4: styles["h3"]}.get(
                block.level, styles["h3"]
            )
            story.append(Paragraph(inline(block.text), style))
        elif block.kind == "paragraph":
            story.append(Paragraph(inline(block.text), styles["body"]))
        elif block.kind == "bullet":
            story.append(Paragraph(inline(block.text), styles["bullet"], bulletText="•"))
        elif block.kind == "numbered":
            story.append(Paragraph(inline(block.text), styles["numbered"]))
        elif block.kind == "code":
            story.append(Spacer(1, 3))
            story.append(make_code_block(block.text, styles))
            story.append(Spacer(1, 7))
        elif block.kind == "table":
            if block.rows:
                story.append(Spacer(1, 3))
                story.append(make_table(block.rows, styles))
                story.append(Spacer(1, 9))
        elif block.kind == "rule":
            story.append(HRFlowable(width="100%", thickness=0.5, color=RULE, spaceAfter=8))

    document.build(story)


def main() -> int:
    if not SOURCE.is_file():
        print(f"Không tìm thấy {SOURCE}", file=sys.stderr)
        return 1
    build(SOURCE, TARGET)
    print(f"Đã tạo {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
