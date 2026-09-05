"""数据处理模块:PDF -> 文本,并粗定位章节标题。"""

import re
from pathlib import Path

import pdfplumber

HEADING_PATTERN = re.compile(
    r"^\s*((第[一二三四五六七八九十百]+[章节部分篇])|"
    r"(\d+(\.\d+)*[\s、．.]{0,2}[^\d]))",
    re.MULTILINE,
)


def extract_pdf_text(pdf_path: Path) -> str:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            pages.append(f"\n===== 第 {i} 页 =====\n{text}")
    return "\n".join(pages)


def detect_headings(text: str, limit: int = 30) -> list[str]:
    heads = []
    for m in HEADING_PATTERN.finditer(text):
        line = m.group(0).strip()
        if line not in heads:
            heads.append(line)
        if len(heads) >= limit:
            break
    return heads
