"""
RubricCarver 2.0 정적 대시보드 생성기
GitHub Pages 배포용 docs/index.html 생성

실행:
  python3 docs/export_static.py
"""
import sys, os, json, shutil, re
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR / "analysis"))

import data_extractor

EXP_NAME = "exp2_rough"
DOCS_DIR = PROJECT_DIR / "docs"
TEMPLATE_PATH = PROJECT_DIR / "analysis" / "templates" / "dashboard.html"
OUTPUT_PATH = DOCS_DIR / "index.html"
STATIC_SRC = PROJECT_DIR / "analysis" / "static"
STATIC_DST = DOCS_DIR / "static"

def main():
    print(f"[1/4] 실험 데이터 추출 중: {EXP_NAME}")
    data = data_extractor.build_data(EXP_NAME)
    data_json = json.dumps(data, ensure_ascii=False, indent=None)
    print(f"      데이터 크기: {len(data_json):,} bytes")

    print("[2/4] 대시보드 템플릿 변환 중")
    html = TEMPLATE_PATH.read_text(encoding="utf-8")

    # Jinja2 태그 제거: {{ exp_name|default('exp1_analytic') }} → exp2_rough
    html = html.replace(
        '"{{ exp_name|default(\'exp1_analytic\') }}"',
        f'"{EXP_NAME}"'
    )

    # fetchData() 함수를 인라인 데이터 주입으로 교체
    # 기존: async function fetchData(){ ... fetch('/api/data?exp=...') ... } fetchData();
    old_fetch = re.search(
        r'async function fetchData\(\)\{.*?fetchData\(\);',
        html, re.DOTALL
    )
    if old_fetch:
        new_fetch = (
            f'const __STATIC_DATA__ = {data_json};\n'
            f'    function fetchData(){{\n'
            f'      DATA = __STATIC_DATA__;\n'
            f'      document.getElementById(\'gen-time\').textContent = \'생성: \' + DATA.generated_at;\n'
            f'      buildLive();\n'
            f'      buildOverview();\n'
            f'      buildDetail();\n'
            f'      buildBoundary();\n'
            f'      buildRubric();\n'
            f'    }}\n'
            f'    fetchData();'
        )
        html = html[:old_fetch.start()] + new_fetch + html[old_fetch.end():]
        print("      fetchData() → 인라인 데이터 교체 완료")
    else:
        print("      경고: fetchData() 패턴을 찾지 못했습니다. 수동 확인 필요")

    # 정적 자산 경로: /static/ → static/ (GitHub Pages 상대 경로)
    html = html.replace('src="/static/', 'src="static/')
    html = html.replace("src='/static/", "src='static/")

    # 실시간 갱신 dot 비활성화 (정적 페이지에서 의미 없음)
    html = html.replace(
        '<div class="live-dot"></div>',
        '<div class="live-dot" style="background:var(--muted);animation:none;" title="정적 스냅샷"></div>'
    )

    print("[3/4] 파일 저장 중")
    DOCS_DIR.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"      저장됨: {OUTPUT_PATH}")

    # 정적 자산 복사
    STATIC_DST.mkdir(exist_ok=True)
    for f in STATIC_SRC.iterdir():
        if f.is_file():
            shutil.copy2(f, STATIC_DST / f.name)
            print(f"      복사됨: static/{f.name}")

    print(f"[4/4] 완료")
    print(f"      → docs/index.html ({OUTPUT_PATH.stat().st_size // 1024} KB)")
    print(f"      → docs/static/ ({len(list(STATIC_DST.iterdir()))}개 파일)")

if __name__ == "__main__":
    main()
