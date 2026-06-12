"""
full_paper.md → paper_draft.hwpx
한글(Hancom) 논문 작성 양식 준수 버전
"""
import re, zipfile, shutil, html
from pathlib import Path
from xml.sax.saxutils import escape as xe

TEMPLATE   = Path("paper/논문 작성 양식.hwpx")
INPUT_MD   = Path("paper/full_paper.md")
OUTPUT     = Path("paper/paper_draft.hwpx")

TEXT_W = 42520   # 텍스트 영역 폭(HWP 단위 ≈ 150mm)
MM_TO_HWP = 283.465  # 1mm = 283.465 HWP단위

# ─── 스타일 ID (template 분석 결과) ───────────────────────────
PAR_BODY    = 38   # 본문: JUSTIFY, 들여쓰기 1100, 줄간격 160%
PAR_H1      = 15   # 1단계 제목: CENTER
PAR_H2      = 28   # 2단계 이하 제목: JUSTIFY
PAR_CENTER  = 13   # 가운데 정렬 본문
PAR_RIGHT   = 31   # 우측 정렬

CHAR_BODY   = 9    # 11pt 휴먼명조
CHAR_H1     = 36   # 15pt
CHAR_H2     = 31   # 13pt 진하게
CHAR_H3     = 32   # 13pt (다른 서체)
CHAR_SMALL  = 16   # 11pt (표 셀용)

BF_TABLE    = 4    # 표 외곽: SOLID 전체
BF_CELL     = 9    # 셀: SOLID 전체

# ─── 한글 수식 편집기 문법 변환 ──────────────────────────────
# 한글 수식 편집기 규칙:
#   - 분수:   {분자} over {분모}
#   - 거듭제곱: base ^{exp}
#   - 아래첨자: base _{sub}
#   - 그리스 문자: backslash 없이 이름만  (kappa, alpha, ...)
#   - 적분: int _{하한}^{상한}
#   - 합: sum _{하한}^{상한}
#   - 기타 연산자: leq, geq, neq, approx, times, cdot, pm, ...
# 수식은 본문에 〔수식: ...〕 형태로 표시 → 한글에서 복사 후 수식 편집기에 붙여넣기

def latex_to_heq(expr: str) -> str:
    """LaTeX 표현 → 한글 수식 편집기 입력 문법"""
    s = expr.strip()

    # \text{...} → 괄호 없이 텍스트
    s = re.sub(r'\\text\s*\{([^}]*)\}', r'"\1"', s)

    # \frac{a}{b} → {a} over {b}
    def frac_repl(m):
        return f'{{{m.group(1)}}} over {{{m.group(2)}}}'
    s = re.sub(r'\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}', frac_repl, s)

    # \sqrt{x} → sqrt {x}
    s = re.sub(r'\\sqrt\s*\{([^}]*)\}', r'sqrt {\1}', s)
    s = re.sub(r'\\sqrt\s*(\S)',        r'sqrt \1', s)

    # 그리스 문자 (backslash 제거)
    for g in ['alpha','beta','gamma','delta','epsilon','zeta','eta','theta',
              'iota','kappa','lambda','mu','nu','xi','pi','rho','sigma',
              'tau','upsilon','phi','chi','psi','omega',
              'Alpha','Beta','Gamma','Delta','Epsilon','Zeta','Eta','Theta',
              'Iota','Kappa','Lambda','Mu','Nu','Xi','Pi','Rho','Sigma',
              'Tau','Upsilon','Phi','Chi','Psi','Omega']:
        s = s.replace(f'\\{g}', g)

    # 연산자·기호
    replacements = [
        (r'\\int',      'int'),
        (r'\\sum',      'sum'),
        (r'\\prod',     'prod'),
        (r'\\infty',    'inf'),
        (r'\\partial',  'partial'),
        (r'\\nabla',    'nabla'),
        (r'\\leq',      'leq'),
        (r'\\geq',      'geq'),
        (r'\\neq',      'neq'),
        (r'\\approx',   'approx'),
        (r'\\sim',      'sim'),
        (r'\\times',    'times'),
        (r'\\cdot',     'cdot'),
        (r'\\pm',       'pm'),
        (r'\\mp',       'mp'),
        (r'\\to',       'to'),
        (r'\\rightarrow', 'to'),
        (r'\\leftarrow',  'leftarrow'),
        (r'\\Rightarrow', 'Rightarrow'),
        (r'\\in',       'in'),
        (r'\\notin',    'notin'),
        (r'\\subset',   'subset'),
        (r'\\cup',      'cup'),
        (r'\\cap',      'cap'),
        (r'\\ldots',    '...'),
        (r'\\cdots',    '...'),
        (r'\\prime',    "'"),
        (r"\'",         "'"),
        # 공백/포맷 제거
        (r'\\,',  ' '),
        (r'\\!',  ''),
        (r'\\;',  ' '),
        (r'\\:',  ' '),
        (r'\\quad',  ' '),
        (r'\\qquad', ' '),
        (r'\\\\',    ' '),
        (r'\\left',  ''),
        (r'\\right', ''),
        (r'\\ ',     ' '),
    ]
    for pat, rep in replacements:
        s = re.sub(pat, rep, s)

    # 남은 백슬래시 명령 제거
    s = re.sub(r'\\[a-zA-Z]+', '', s)

    # ── 이항 연산자 앞 공백 추가 ──────────────────────────────
    # 지수·첨자·숫자·닫는 괄호 뒤의 + - 앞에 공백을 넣어
    # 수식 편집기가 지수 범위를 잘못 인식하지 않도록 함
    # 예: t^2-5t+4  →  t^2 -5t +4
    s = re.sub(
        r'(?<=[a-zA-Z0-9)\]}])([+\-])(?=[a-zA-Z0-9(\\{])',
        r' \1 ', s
    )
    # 연속 공백 정리
    s = re.sub(r'  +', ' ', s)

    return s.strip()

def inline_math(text):
    """$$...$$ 블록 수식 → 수식 편집기 문법 텍스트"""
    return re.sub(
        r'\$\$(.+?)\$\$',
        lambda m: latex_to_heq(m.group(1)),
        text, flags=re.DOTALL
    )

def inline_math_simple(text):
    """$...$ 인라인 수식 → 수식 편집기 문법 텍스트"""
    return re.sub(
        r'\$([^$\n]+?)\$',
        lambda m: latex_to_heq(m.group(1)),
        text
    )

def clean_text(text):
    """마크다운 마커 제거 + 수식 편집기 문법으로 변환 + XML 이스케이프"""
    text = inline_math(text)
    text = inline_math_simple(text)
    # 링크 [text](url) → text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # 볼드/이탤릭 제거
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', text)
    text = re.sub(r'\*\*(.+?)\*\*',     r'\1', text)
    text = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'\1', text)
    # 인라인 코드
    text = re.sub(r'`([^`]+)`', r'\1', text)
    return xe(text)

# ─── XML 생성 헬퍼 ─────────────────────────────────────────────
_pid = 0
def para(par_id, char_id, text_xml, style=0, line_sz=1100):
    """단락 XML 생성"""
    global _pid
    _pid += 1
    return (
        f'<hp:p id="{_pid}" paraPrIDRef="{par_id}" styleIDRef="{style}" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{char_id}">{text_xml}</hp:run>'
        f'<hp:linesegarray>'
        f'<hp:lineseg textpos="0" vertpos="0" vertsize="{line_sz}" '
        f'textheight="{line_sz}" baseline="{int(line_sz*0.85)}" '
        f'spacing="{int(line_sz*0.6)}" horzpos="0" horzsize="{TEXT_W}" flags="393216"/>'
        f'</hp:linesegarray></hp:p>'
    )

def text_run(char_id, text):
    return f'<hp:run charPrIDRef="{char_id}"><hp:t>{text}</hp:t></hp:run>'

def fn_run(fn_id, content_xml):
    """각주 인라인 컨트롤"""
    return (
        f'<hp:run charPrIDRef="{CHAR_BODY}">'
        f'<hp:ctrl><hp:fn id="{fn_id}" autoNum="1">'
        f'<hp:subList textDirection="HORIZONTAL" lineWrap="BREAK" '
        f'vertAlign="TOP" linkListIDRef="0" linkListNextIDRef="0" '
        f'textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
        f'{content_xml}'
        f'</hp:subList></hp:fn></hp:ctrl>'
        f'</hp:run>'
    )

# ─── 표 생성 ──────────────────────────────────────────────────
def display_len(s):
    return sum(2 if ord(c) > 127 else 1 for c in s)

def table_xml(rows, tbl_id):
    """
    rows: list of list of str (헤더 포함)
    열 너비: 내용 길이 기반 비례 배분, 최소 너비 보장
    """
    if not rows: return ''
    ncols = max(len(r) for r in rows)
    nrows = len(rows)

    # 열별 최대 내용 길이
    maxlen = [0] * ncols
    for row in rows:
        for j, cell in enumerate(row):
            if j < ncols:
                text = re.sub(r'\$[^$]+\$', 'X', cell)  # 수식은 짧게 취급
                maxlen[j] = max(maxlen[j], display_len(text.strip()))

    # 최소 단위: 숫자/코드 열은 8, 긴 설명 열은 그대로
    MIN_UNITS = 8
    clamped = [max(v, MIN_UNITS) for v in maxlen]
    total = sum(clamped)

    # HWP 단위 배분 (TEXT_W - 여유 284)
    avail = TEXT_W - 284
    widths_hwp = [int(avail * v / total) for v in clamped]
    widths_hwp[-1] = avail - sum(widths_hwp[:-1])
    # 최소 폭 보장: 3mm = 850 HWP 단위
    for i in range(ncols):
        widths_hwp[i] = max(widths_hwp[i], 850)

    # 표 높이 추정 (행수 × 셀 높이)
    row_h   = 1900
    tbl_h   = nrows * row_h
    tbl_w   = sum(widths_hwp)

    out  = (
        f'<hp:tbl id="{tbl_id}" zOrder="1" numberingType="TABLE" '
        f'textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" '
        f'dropcapstyle="None" pageBreak="CELL" repeatHeader="1" '
        f'rowCnt="{nrows}" colCnt="{ncols}" cellSpacing="0" '
        f'borderFillIDRef="{BF_TABLE}" noAdjust="0">'
        f'<hp:sz width="{tbl_w}" widthRelTo="ABSOLUTE" height="{tbl_h}" heightRelTo="ABSOLUTE" protect="0"/>'
        f'<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" '
        f'holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="PARA" '
        f'vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
        f'<hp:outMargin left="0" right="0" top="141" bottom="141"/>'
        f'<hp:inMargin left="0" right="0" top="141" bottom="141"/>'
    )

    for ri, row in enumerate(rows):
        is_header = (ri == 0)
        out += f'<hp:tr>'
        for ci in range(ncols):
            cell_text = row[ci] if ci < len(row) else ''
            cell_clean = clean_text(cell_text)
            w = widths_hwp[ci]
            # 헤더 행은 CHAR_H3(13pt), 내용은 CHAR_BODY(11pt)
            c_id = CHAR_H3 if is_header else CHAR_BODY
            p_id = PAR_CENTER if is_header else PAR_BODY
            out += (
                f'<hp:tc name="" header="{1 if is_header else 0}" '
                f'hasMargin="0" protect="0" editable="0" dirty="0" '
                f'borderFillIDRef="{BF_CELL}">'
                f'<hp:sz width="{w}" height="{row_h}"/>'
                f'<hp:subList textDirection="HORIZONTAL" lineWrap="BREAK" '
                f'vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" '
                f'textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
                + para(p_id, c_id, f'<hp:t>{cell_clean}</hp:t>')
                + f'</hp:subList></hp:tc>'
            )
        out += '</hp:tr>'
    out += '</hp:tbl>'
    return out

# ─── 마크다운 파서 ─────────────────────────────────────────────
def parse_md(text):
    """마크다운을 블록 목록으로 파싱. 각 블록: (type, content)"""
    blocks = []
    lines  = text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]

        # 코드 블록
        if line.startswith('```'):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1
            blocks.append(('code', '\n'.join(code_lines)))
            continue

        # 표 수집
        if '|' in line and line.strip().startswith('|'):
            table_lines = []
            while i < len(lines) and '|' in lines[i] and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1
            # 구분선 제거
            rows = []
            for tl in table_lines:
                if re.match(r'^\s*\|[\s\-:]+\|', tl):
                    continue
                cells = [c.strip() for c in tl.strip().strip('|').split('|')]
                rows.append(cells)
            if rows:
                blocks.append(('table', rows))
            continue

        # 빈 줄
        if not line.strip():
            blocks.append(('blank', ''))
            i += 1
            continue

        # 헤딩
        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m:
            level = len(m.group(1))
            blocks.append((f'h{level}', m.group(2).strip()))
            i += 1
            continue

        # 목록
        if re.match(r'^[-*+]\s', line) or re.match(r'^\d+\.\s', line):
            blocks.append(('list', line))
            i += 1
            continue

        # 일반 단락 (여러 줄 이어붙임)
        para_lines = []
        while i < len(lines) and lines[i].strip() and not lines[i].startswith('#') \
              and not lines[i].startswith('|') and not lines[i].startswith('```') \
              and not re.match(r'^[-*+]\s', lines[i]) and not re.match(r'^\d+\.\s', lines[i]):
            para_lines.append(lines[i])
            i += 1
        if para_lines:
            blocks.append(('p', ' '.join(para_lines)))
        continue

    return blocks

# ─── 각주 추출 ────────────────────────────────────────────────
def extract_footnotes(text):
    """각주 ^[...] 추출 → (정제된 텍스트, [(fn_pos, fn_text), ...])"""
    fns   = []
    fn_id = [0]

    def repl(m):
        fn_id[0] += 1
        fns.append((fn_id[0], m.group(1)))
        return f'__FN{fn_id[0]}__'

    clean = re.sub(r'\^\[(.+?)\]', repl, text, flags=re.DOTALL)
    return clean, fns

# ─── 섹션 XML 생성 ────────────────────────────────────────────
_tbl_id = 100

def block_to_xml(block_type, content, fn_map):
    global _tbl_id, _pid

    if block_type == 'blank':
        return para(PAR_BODY, CHAR_BODY, '')

    if block_type == 'code':
        lines = content.split('\n')[:6]   # 너무 긴 코드는 앞부분만
        parts = []
        for ln in lines:
            if ln.strip():
                parts.append(para(PAR_BODY, CHAR_SMALL, f'<hp:t>{xe(ln)}</hp:t>'))
        return ''.join(parts) if parts else ''

    if block_type == 'table':
        _tbl_id += 1
        txml = table_xml(content, _tbl_id)
        _pid += 1
        wrapper = (
            f'<hp:p id="{_pid}" paraPrIDRef="{PAR_BODY}" styleIDRef="0" '
            f'pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{CHAR_BODY}">'
            f'<hp:ctrl>{txml}</hp:ctrl>'
            f'</hp:run>'
            f'<hp:linesegarray>'
            f'<hp:lineseg textpos="0" vertpos="0" vertsize="1100" textheight="1100" '
            f'baseline="935" spacing="660" horzpos="0" horzsize="{TEXT_W}" flags="393216"/>'
            f'</hp:linesegarray></hp:p>'
        )
        return wrapper

    if block_type in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
        level = int(block_type[1])
        raw   = content
        # 헤딩에서 각주 처리
        raw, local_fns = extract_footnotes(raw)
        for fid, _ in local_fns:
            raw = raw.replace(f'__FN{fid}__', '')
        txt = clean_text(raw)

        if level == 1:
            # # Chapter N → Ⅰ 스타일 (로마숫자 변환)
            m = re.match(r'Chapter\s+(\d+)\.\s*(.*)', txt)
            if m:
                roman = ['Ⅰ','Ⅱ','Ⅲ','Ⅳ','Ⅴ','Ⅵ','Ⅶ','Ⅷ','Ⅸ','Ⅹ']
                n = int(m.group(1))
                r_num = roman[n-1] if 1 <= n <= len(roman) else str(n)
                txt = f'{r_num}. {m.group(2)}'
            return para(PAR_H1, CHAR_H1, f'<hp:t>{txt}</hp:t>', line_sz=1500)

        elif level == 2:
            # ## N.N. → "N." 형식
            m = re.match(r'(\d+\.\d+)\.\s*(.*)', txt)
            if m:
                num_parts = m.group(1).split('.')
                txt = f'{num_parts[-1]}. {m.group(2)}'
            return para(PAR_H2, CHAR_H2, f'<hp:t>{txt}</hp:t>', line_sz=1300)

        elif level == 3:
            m = re.match(r'(#{0,3})\s*(.*)', txt)
            return para(PAR_H2, CHAR_H3, f'<hp:t>{txt}</hp:t>', line_sz=1200)

        else:
            return para(PAR_BODY, CHAR_BODY, f'<hp:t>{txt}</hp:t>')

    if block_type == 'list':
        # 목록 항목: 들여쓰기 본문으로 처리
        m = re.match(r'^[-*+]\s+(.*)', content) or re.match(r'^\d+\.\s+(.*)', content)
        item = m.group(1) if m else content
        item, local_fns = extract_footnotes(item)
        runs = build_runs_with_fn(item, local_fns, fn_map)
        _pid += 1
        return (
            f'<hp:p id="{_pid}" paraPrIDRef="{PAR_BODY}" styleIDRef="0" '
            f'pageBreak="0" columnBreak="0" merged="0">'
            + runs +
            f'<hp:linesegarray>'
            f'<hp:lineseg textpos="0" vertpos="0" vertsize="1100" textheight="1100" '
            f'baseline="935" spacing="660" horzpos="0" horzsize="{TEXT_W}" flags="393216"/>'
            f'</hp:linesegarray></hp:p>'
        )

    # 일반 단락 ('p')
    raw = content
    raw, local_fns = extract_footnotes(raw)
    runs = build_runs_with_fn(raw, local_fns, fn_map)
    _pid += 1
    return (
        f'<hp:p id="{_pid}" paraPrIDRef="{PAR_BODY}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        + runs +
        f'<hp:linesegarray>'
        f'<hp:lineseg textpos="0" vertpos="0" vertsize="1100" textheight="1100" '
        f'baseline="935" spacing="660" horzpos="0" horzsize="{TEXT_W}" flags="393216"/>'
        f'</hp:linesegarray></hp:p>'
    )

def build_runs_with_fn(text, local_fns, fn_map):
    """각주 마커 __FNn__ 이 포함된 텍스트를 run + footnote ctrl로 변환"""
    result = ''
    parts  = re.split(r'(__FN\d+__)', text)
    for part in parts:
        m = re.match(r'__FN(\d+)__', part)
        if m:
            fid   = int(m.group(1))
            fn_txt = fn_map.get(fid, '')
            fn_clean = clean_text(fn_txt)
            fn_body  = para(PAR_BODY, CHAR_SMALL, f'<hp:t>{fn_clean}</hp:t>')
            result  += fn_run(fid, fn_body)
        else:
            if part.strip():
                clean = clean_text(part)
                result += f'<hp:run charPrIDRef="{CHAR_BODY}"><hp:t>{clean}</hp:t></hp:run>'
    return result or f'<hp:run charPrIDRef="{CHAR_BODY}"/>'

# ─── 섹션 헤더 XML (template에서 복사) ─────────────────────────
def get_sec_pr(template_zip):
    s = template_zip.read('Contents/section0.xml').decode('utf-8', errors='replace')
    m = re.search(r'(<hp:secPr.*?</hp:secPr>)', s, re.DOTALL)
    return m.group(1) if m else ''

# ─── 메인 빌드 ────────────────────────────────────────────────
def build():
    global _pid
    _pid = 0

    md_text = INPUT_MD.read_text(encoding='utf-8')

    # 전체 각주 사전 수집 (fn_id → fn_text)
    _, all_fns = extract_footnotes(md_text)
    fn_map = {fid: ftxt for fid, ftxt in all_fns}

    # 각주 마커 삽입된 텍스트로 재파싱
    md_with_markers, _ = extract_footnotes(md_text)
    blocks = parse_md(md_with_markers)

    # XML 생성
    body_xml = ''
    for btype, bcontent in blocks:
        try:
            body_xml += block_to_xml(btype, bcontent, fn_map)
        except Exception as e:
            # 변환 실패 시 빈 단락으로 대체
            body_xml += para(PAR_BODY, CHAR_BODY, '')

    # section0.xml 조립
    NS = (
        'xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app" '
        'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
        'xmlns:hp10="http://www.hancom.co.kr/hwpml/2016/paragraph" '
        'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
        'xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" '
        'xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" '
        'xmlns:hhs="http://www.hancom.co.kr/hwpml/2011/history" '
        'xmlns:hm="http://www.hancom.co.kr/hwpml/2011/master-page" '
        'xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:opf="http://www.idpf.org/2007/opf/" '
        'xmlns:ooxmlchart="http://www.hancom.co.kr/hwpml/2016/ooxmlchart" '
        'xmlns:hwpunitchar="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar" '
        'xmlns:epub="http://www.idpf.org/2007/ops" '
        'xmlns:config="urn:oasis:names:tc:opendocument:xmlns:config:1.0"'
    )

    with zipfile.ZipFile(TEMPLATE) as tz:
        sec_pr = get_sec_pr(tz)

    # secPr를 첫 단락에 삽입
    first_para = (
        f'<hp:p id="1" paraPrIDRef="{PAR_BODY}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{CHAR_BODY}">{sec_pr}</hp:run>'
        f'<hp:linesegarray>'
        f'<hp:lineseg textpos="0" vertpos="0" vertsize="1100" textheight="1100" '
        f'baseline="935" spacing="660" horzpos="0" horzsize="{TEXT_W}" flags="393216"/>'
        f'</hp:linesegarray></hp:p>'
    )

    section0 = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
        f'<hs:sec {NS}>'
        f'{first_para}'
        f'{body_xml}'
        f'</hs:sec>'
    )

    # hwpx 패키징 (template 파일 복사 + section0.xml 교체)
    if OUTPUT.exists():
        OUTPUT.unlink()

    with zipfile.ZipFile(TEMPLATE) as tz, \
         zipfile.ZipFile(OUTPUT, 'w', zipfile.ZIP_DEFLATED) as oz:
        for item in tz.namelist():
            if item == 'Contents/section0.xml':
                oz.writestr(item, section0.encode('utf-8'))
            elif item == 'Preview/PrvText.txt':
                oz.writestr(item, '채점 기계에서 벗어나기 — RubricCarver 2.0'.encode('utf-8'))
            elif item == 'Preview/PrvImage.png':
                pass   # 미리보기 이미지 생략
            else:
                oz.writestr(item, tz.read(item))

    print(f"생성 완료 → {OUTPUT}")
    print(f"단락 수: {_pid}, 각주: {len(fn_map)}")

if __name__ == '__main__':
    build()
