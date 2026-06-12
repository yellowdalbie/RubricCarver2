"""
full_paper.md → paper_draft.docx 변환 스크립트
- 불필요한 **bold** / *italic* 제거 (수식·헤딩·표·목록 제외)
- 표 열 너비 자동 조정 (내용 길이 기반)
- A4, 여백 3/3/2.5/2.5 cm
"""
import re
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.shared import Cm, Pt
from docx.oxml.ns import qn

INPUT  = Path("/Users/home/vaults/projects/RubricCarver2/paper/full_paper.md")
OUTPUT = Path("/Users/home/vaults/projects/RubricCarver2/paper/paper_draft.docx")
TEMP   = Path("/tmp/_paper_clean.md")

# ── 1. 마크다운 전처리 ──────────────────────────────────────────

def strip_emphasis(line: str) -> str:
    """본문 줄에서 **bold** / *italic* 마커 제거."""
    line = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', line)
    line = re.sub(r'\*\*(.+?)\*\*',     r'\1', line)
    # 단독 * (이탤릭) — 리스트 마커(줄 시작 '* ')는 건드리지 않음
    line = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'\1', line)
    return line

def preprocess(content: str) -> str:
    lines  = content.split('\n')
    result = []
    in_code = False
    for line in lines:
        # 코드 블록 토글
        if line.startswith('```'):
            in_code = not in_code
            result.append(line)
            continue
        if in_code:
            result.append(line)
            continue
        # 헤딩 / 표 행 / 목록 → 그대로
        if (line.startswith('#')
                or line.startswith('|')
                or re.match(r'^[-*+] ', line)
                or re.match(r'^\d+\. ', line)):
            result.append(line)
            continue
        result.append(strip_emphasis(line))
    return '\n'.join(result)

content = INPUT.read_text(encoding='utf-8')
TEMP.write_text(preprocess(content), encoding='utf-8')

# ── 2. pandoc 변환 ──────────────────────────────────────────────

proc = subprocess.run(
    ['pandoc', str(TEMP), '-o', str(OUTPUT), '--wrap=none', '--standalone'],
    capture_output=True, text=True
)
if proc.returncode != 0:
    print("pandoc 오류:", proc.stderr, file=sys.stderr)
    sys.exit(1)
print("pandoc 완료")

# ── 3. python-docx 후처리 ───────────────────────────────────────

doc = Document(str(OUTPUT))

# 페이지 설정 (A4)
sec = doc.sections[0]
sec.page_width   = Cm(21)
sec.page_height  = Cm(29.7)
sec.left_margin  = Cm(3)
sec.right_margin = Cm(3)
sec.top_margin   = Cm(2.5)
sec.bottom_margin = Cm(2.5)

AVAIL = Cm(15)   # 21 - 3 - 3

def display_len(text: str) -> int:
    """한글/CJK = 2, ASCII = 1 로 표시 폭 추정."""
    return sum(2 if ord(c) > 127 else 1 for c in text)

def set_col_widths(table):
    ncols = len(table.columns)
    if ncols == 0:
        return

    # 열별 최대 내용 길이 (헤더 포함)
    maxlen = [0] * ncols
    for row in table.rows:
        cells = row.cells
        for j in range(min(ncols, len(cells))):
            maxlen[j] = max(maxlen[j], display_len(cells[j].text.strip()))

    # 최소 단위 보장 (숫자/코드 열이 너무 좁아지지 않도록)
    clamped = [max(v, 6) for v in maxlen]
    total   = sum(clamped)

    widths = [int(AVAIL * v / total) for v in clamped]
    # 반올림 오차 보정 (마지막 열)
    widths[-1] = AVAIL - sum(widths[:-1])
    if widths[-1] < Cm(0.5):
        widths[-1] = Cm(0.5)

    # 전체 테이블 너비 설정
    tbl    = table._tbl
    tblPr  = tbl.find(qn('w:tblPr'))
    if tblPr is None:
        tblPr = OxmlElement('w:tblPr')
        tbl.insert(0, tblPr)

    # w:tblW — 전체 폭
    tblW = tblPr.find(qn('w:tblW'))
    if tblW is None:
        from docx.oxml import OxmlElement
        tblW = OxmlElement('w:tblW')
        tblPr.append(tblW)
    tblW.set(qn('w:w'),    str(int(AVAIL)))
    tblW.set(qn('w:type'), 'dxa')

    # 각 셀 너비 적용
    for j, col in enumerate(table.columns):
        w = widths[j]
        for cell in col.cells:
            tc   = cell._tc
            tcPr = tc.find(qn('w:tcPr'))
            if tcPr is None:
                from docx.oxml import OxmlElement
                tcPr = OxmlElement('w:tcPr')
                tc.insert(0, tcPr)
            tcW = tcPr.find(qn('w:tcW'))
            if tcW is None:
                from docx.oxml import OxmlElement
                tcW = OxmlElement('w:tcW')
                tcPr.append(tcW)
            # python-docx Cm()은 EMU 단위, Word tcW는 twips(1/20pt) 단위
            # 1 cm = 567 twips
            twips = int(w / 914400 * 1440)   # EMU → twips
            tcW.set(qn('w:w'),    str(twips))
            tcW.set(qn('w:type'), 'dxa')

for table in doc.tables:
    set_col_widths(table)

doc.save(str(OUTPUT))
print(f"저장 완료 → {OUTPUT}")
