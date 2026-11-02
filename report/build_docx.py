#!/usr/bin/env python3
"""Chuyển ``bao-cao-backend.md`` sang DOCX có định dạng.

Cách chạy::

    pip install python-docx
    python report/build_docx.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from markdown_blocks import Block, parse

REPORT_DIR = Path(__file__).resolve().parent
SOURCE = REPORT_DIR / "bao-cao-backend.md"
TARGET = REPORT_DIR / "bao-cao-backend.docx"

BODY_FONT = "Times New Roman"
CODE_FONT = "Consolas"
ACCENT = RGBColor(0x1D, 0x4E, 0xD8)
INK = RGBColor(0x16, 0x20, 0x2E)
MUTED = RGBColor(0x55, 0x60, 0x73)

INLINE_PATTERN = re.compile(r"(\*\*.+?\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))")


# --------------------------------------------------------------------------
# Tiện ích định dạng
# --------------------------------------------------------------------------
def _set_run_font(run, name: str, size: float | None = None) -> None:
    run.font.name = name
    if size is not None:
        run.font.size = Pt(size)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attribute in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attribute), name)


def add_inline(paragraph, text: str, *, size: float | None = None) -> None:
    """Thêm văn bản có định dạng **đậm**, `mã`, [liên kết](url)."""
    position = 0
    for match in INLINE_PATTERN.finditer(text):
        if match.start() > position:
            run = paragraph.add_run(text[position : match.start()])
            _set_run_font(run, BODY_FONT, size)
        token = match.group(0)

        if token.startswith("**"):
            run = paragraph.add_run(token[2:-2])
            run.bold = True
            _set_run_font(run, BODY_FONT, size)
        elif token.startswith("`"):
            run = paragraph.add_run(token[1:-1])
            _set_run_font(run, CODE_FONT, (size or 13) - 1.5)
            run.font.color.rgb = RGBColor(0x9A, 0x34, 0x12)
        else:
            label = token[1 : token.index("]")]
            url = token[token.index("(") + 1 : -1]
            run = paragraph.add_run(label)
            run.font.color.rgb = ACCENT
            run.underline = True
            _set_run_font(run, BODY_FONT, size)
            if url and url != label:
                suffix = paragraph.add_run(f" ({url})")
                _set_run_font(suffix, BODY_FONT, (size or 13) - 1.5)
                suffix.font.color.rgb = MUTED
        position = match.end()

    if position < len(text):
        run = paragraph.add_run(text[position:])
        _set_run_font(run, BODY_FONT, size)


def shade_cell(cell, color: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    properties.append(shd)


def add_horizontal_rule(document: Document) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(2)
    paragraph.paragraph_format.space_after = Pt(6)
    properties = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "C9D3E0")
    borders.append(bottom)
    properties.append(borders)


def add_page_number_footer(section) -> None:
    paragraph = section.footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("Trang ")
    _set_run_font(run, BODY_FONT, 9)
    run.font.color.rgb = MUTED

    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instruction)
    run._r.append(end)


def add_header(section, text: str) -> None:
    paragraph = section.header.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run(text)
    _set_run_font(run, BODY_FONT, 9)
    run.font.color.rgb = MUTED


# --------------------------------------------------------------------------
# Các khối nội dung
# --------------------------------------------------------------------------
def configure_styles(document: Document) -> None:
    normal = document.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(13)
    normal.font.color.rgb = INK
    rpr = normal.element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    for attribute in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attribute), BODY_FONT)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.28

    sizes = {"Heading 1": 18, "Heading 2": 15, "Heading 3": 13.5, "Heading 4": 13}
    for name, size in sizes.items():
        style = document.styles[name]
        style.font.name = BODY_FONT
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = INK
        style.paragraph_format.space_before = Pt(14 if name != "Heading 1" else 6)
        style.paragraph_format.space_after = Pt(6)
        style.paragraph_format.keep_with_next = True


def add_heading(document: Document, level: int, text: str) -> None:
    # Cấp 1 trên Markdown là tiêu đề bìa, nên các mục "##" phải thành Heading 1
    # để cây điều hướng của Word bắt đầu đúng từ cấp mục lớn.
    mapped = {2: 1, 3: 2, 4: 3}.get(level, 3)
    paragraph = document.add_heading(level=mapped)
    add_inline(paragraph, text)


def add_paragraph(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    add_inline(paragraph, text)


def add_bullet(document: Document, text: str) -> None:
    paragraph = document.add_paragraph(style="List Bullet")
    add_inline(paragraph, text)


def add_numbered(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.left_indent = Cm(0.6)
    paragraph.paragraph_format.first_line_indent = Cm(-0.6)
    add_inline(paragraph, text)


def add_code_block(document: Document, code: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.left_indent = Cm(0.4)
    paragraph.paragraph_format.space_before = Pt(4)
    paragraph.paragraph_format.space_after = Pt(8)
    paragraph.paragraph_format.line_spacing = 1.0

    properties = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), "F3F5F9")
    properties.append(shd)

    borders = OxmlElement("w:pBdr")
    for side in ("top", "left", "bottom", "right"):
        border = OxmlElement(f"w:{side}")
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), "4")
        border.set(qn("w:space"), "4")
        border.set(qn("w:color"), "DDE3EC")
        borders.append(border)
    properties.append(borders)

    run = paragraph.add_run(code)
    _set_run_font(run, CODE_FONT, 9.5)


def add_table(document: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    columns = max(len(row) for row in rows)
    table = document.add_table(rows=len(rows), cols=columns)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    for row_index, row in enumerate(rows):
        for column_index in range(columns):
            cell = table.cell(row_index, column_index)
            text = row[column_index] if column_index < len(row) else ""
            cell.text = ""
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(2)
            paragraph.paragraph_format.line_spacing = 1.0
            add_inline(paragraph, text, size=10.5 if columns > 6 else 11)
            if row_index == 0:
                for run in paragraph.runs:
                    run.bold = True
                shade_cell(cell, "E8EEF9")

    spacer = document.add_paragraph()
    spacer.paragraph_format.space_after = Pt(2)


def add_cover(document: Document, block: Block) -> None:
    for _ in range(3):
        document.add_paragraph()

    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(block.text.upper())
    run.bold = True
    _set_run_font(run, BODY_FONT, 24)
    run.font.color.rgb = INK

    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(block.subtitle)
    run.bold = True
    _set_run_font(run, BODY_FONT, 15)
    run.font.color.rgb = ACCENT
    paragraph.paragraph_format.space_after = Pt(30)

    add_horizontal_rule(document)

    table = document.add_table(rows=0, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for line in block.meta:
        match = re.match(r"^\*\*(.+?):\*\*\s*(.+)$", line)
        if not match:
            continue
        row = table.add_row().cells
        label, value = match.group(1), match.group(2)
        for index, text in enumerate((label, value)):
            cell = row[index]
            cell.text = ""
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(4)
            run = paragraph.add_run(text)
            run.bold = index == 0
            _set_run_font(run, BODY_FONT, 12)
            if index == 0:
                run.font.color.rgb = MUTED

    document.add_page_break()


# --------------------------------------------------------------------------
# Dựng tài liệu
# --------------------------------------------------------------------------
def build(source: Path, target: Path) -> None:
    blocks = parse(source)

    document = Document()
    configure_styles(document)

    section = document.sections[0]
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.2)
    add_page_number_footer(section)
    add_header(section, "Báo cáo backend — Gợi ý từ khóa bằng Levenshtein")

    for block in blocks:
        if block.kind == "cover":
            add_cover(document, block)
        elif block.kind == "heading":
            add_heading(document, block.level, block.text)
        elif block.kind == "paragraph":
            add_paragraph(document, block.text)
        elif block.kind == "bullet":
            add_bullet(document, block.text)
        elif block.kind == "numbered":
            add_numbered(document, block.text)
        elif block.kind == "code":
            add_code_block(document, block.text)
        elif block.kind == "table":
            add_table(document, block.rows)
        elif block.kind == "rule":
            add_horizontal_rule(document)

    document.core_properties.title = "Báo cáo backend — Gợi ý từ khóa bằng Levenshtein"
    document.core_properties.language = "vi-VN"
    document.save(target)


def main() -> int:
    if not SOURCE.is_file():
        print(f"Không tìm thấy {SOURCE}", file=sys.stderr)
        return 1
    build(SOURCE, TARGET)
    print(f"Đã tạo {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
