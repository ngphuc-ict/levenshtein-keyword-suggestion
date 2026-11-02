"""Bộ phân tích Markdown tối giản dùng chung cho các bộ sinh báo cáo.

Chỉ hỗ trợ tập con cú pháp mà báo cáo đang dùng: tiêu đề, đoạn văn, danh sách,
bảng, khối mã, đường kẻ ngang và trang bìa.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

HEADING = re.compile(r"^(#{1,4})\s+(.*)$")
NUMBERED = re.compile(r"^\d+\.\s")


@dataclass
class Block:
    kind: str
    text: str = ""
    level: int = 0
    subtitle: str = ""
    meta: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)


def is_special(line: str) -> bool:
    return (
        line.startswith(("#", "- ", "|", "```"))
        or line == "---"
        or bool(NUMBERED.match(line))
    )


def parse(source: Path) -> list[Block]:
    lines = source.read_text(encoding="utf-8").splitlines()
    blocks: list[Block] = []
    index = 0

    # --- Trang bìa ---------------------------------------------------------
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        index = 1
        while index < len(lines) and not lines[index].strip():
            index += 1
        subtitle = ""
        if index < len(lines) and lines[index].startswith("## "):
            subtitle = lines[index][3:].strip()
            index += 1
        meta: list[str] = []
        while index < len(lines) and lines[index].strip() != "---":
            if lines[index].strip():
                meta.append(lines[index].strip())
            index += 1
        blocks.append(Block("cover", text=title, subtitle=subtitle, meta=meta))
        index += 1  # bỏ qua đường kẻ dưới bìa

    # --- Thân bài ----------------------------------------------------------
    while index < len(lines):
        stripped = lines[index].strip()

        if not stripped:
            index += 1
            continue

        if stripped == "---":
            blocks.append(Block("rule"))
            index += 1
            continue

        if stripped.startswith("```"):
            index += 1
            code: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code.append(lines[index])
                index += 1
            index += 1
            blocks.append(Block("code", text="\n".join(code)))
            continue

        if stripped.startswith("|"):
            rows: list[list[str]] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                index += 1
                if all(cell == "" or re.fullmatch(r":?-{2,}:?", cell) for cell in cells):
                    continue
                rows.append(cells)
            blocks.append(Block("table", rows=rows))
            continue

        heading = HEADING.match(stripped)
        if heading:
            blocks.append(Block("heading", text=heading.group(2), level=len(heading.group(1))))
            index += 1
            continue

        if stripped.startswith("- "):
            while index < len(lines) and lines[index].strip().startswith("- "):
                blocks.append(Block("bullet", text=lines[index].strip()[2:]))
                index += 1
            continue

        if NUMBERED.match(stripped):
            blocks.append(Block("numbered", text=stripped))
            index += 1
            continue

        buffer = [stripped]
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if not candidate or is_special(candidate):
                break
            buffer.append(candidate)
            index += 1
        blocks.append(Block("paragraph", text=" ".join(buffer)))

    return blocks
