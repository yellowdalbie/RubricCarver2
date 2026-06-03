"""
RubricCarver 2.0 실험 대시보드 생성기

실행:
  python3 analysis/generate_dashboard.py               # 1회 생성
  python3 analysis/generate_dashboard.py --watch       # 30초마다 재생성 (실시간 모니터링)
  python3 analysis/generate_dashboard.py --watch --interval 15

출력: analysis/dashboard.html
"""
import os, sys, json, re, time, sqlite3, argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict

PROJECT_DIR = Path(__file__).parent.parent
STUDENTS = ["A1","A2","B1","B2","C1","C2","C3","D1","D2","D3","E1","E2","F1","F2","I1","I2"]

TEACHERS = ["T1", "T2", "T3", "T4"]
TEACHER_LABELS = {
    "T1": "절차 중심(독립) (절차·독립)",
    "T2": "절차 중심(연계) (절차·연계)",
    "T3": "개념 중심(요소) (개념·독립)",
    "T4": "개념 중심(통합) (개념·연계)",
}

def get_conn(db_path):
    if not db_path.exists():
        return None
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

# ── 실시간 진행 ───────────────────────────────────────────────────────────────
def load_live(db_path, criterion_codes):
    conn = get_conn(db_path)
    if not conn:
        return {"current_cycle": None, "progress": {}, "student_grid": {}}

    cur = conn.cursor()

    cur.execute("SELECT MAX(cycle_id) as m FROM teacher_grades")
    row = cur.fetchone()
    current_cycle = row["m"] if row and row["m"] else None

    # 교사별 완료 학생 수 (현재 사이클)
    progress = {t: 0 for t in TEACHERS}
    # 학생 × 교사 그리드 (총점 + checklist_data)
    student_grid = {}
    if current_cycle:
        cur.execute("SELECT student_id, teacher_id, checklist_data FROM teacher_grades WHERE cycle_id=?", (current_cycle,))
        rows = cur.fetchall()
        for r in rows:
            progress[r["teacher_id"]] += 1
            s = r["student_id"]
            if s not in student_grid:
                student_grid[s] = {t: {} for t in TEACHERS}
            try:
                ch = json.loads(r["checklist_data"]) if r["checklist_data"] else {}
                for code in criterion_codes:
                    student_grid[s][r["teacher_id"]][code] = ch.get(code, {}).get("answer", "NO").upper()
            except:
                pass

    conn.close()
    
    # Load Prompts from Paper Appendix
    prompts = {}
    appendix_dir = PROJECT_DIR / "analysis" / "prompts"
    prompt_files = {
        "A": ("Appendix_A_Grader_Prompt.md", "교사 에이전트 시스템 프롬프트 (T1~T4)"),
        "B": ("Appendix_B_Analyst_Prompt.md", "분석관 에이전트 시스템 프롬프트"),
        "C": ("Appendix_C_Auditor_Prompt.md", "심의관 에이전트 시스템 프롬프트"),
        "C2": ("Appendix_C2_Auditor_Evaluation_Guide.md", "심의관 평가 가이드 (수학교육학적 렌즈)")
    }
    
    for key, (filename, title) in prompt_files.items():
        file_path = appendix_dir / filename
        if file_path.exists():
            prompts[key] = {
                "title": title,
                "content": file_path.read_text(encoding="utf-8")
            }
        else:
            prompts[key] = {
                "title": title,
                "content": f"{filename} 파일을 찾을 수 없습니다."
            }

    return {
        "current_cycle": current_cycle,
        "progress": progress,
        "student_grid": student_grid,
    }

def load_all_grades(db_path):
    conn = get_conn(db_path)
    if not conn:
        return []
    cur = conn.cursor()
    cur.execute("""
        SELECT cycle_id, teacher_id, student_id, total, checklist_data
        FROM teacher_grades
        ORDER BY cycle_id, student_id, teacher_id
    """)
    results = []
    for r in cur.fetchall():
        checklist = {}
        try:
            checklist = json.loads(r["checklist_data"] or "{}")
        except Exception:
            pass
        results.append({
            "cycle": r["cycle_id"],
            "teacher": r["teacher_id"],
            "student": r["student_id"],
            "total": r["total"],
            "checklist": {k: v.get("answer","?") for k, v in checklist.items()},
            "basis":     {k: v.get("basis","")  for k, v in checklist.items()},
        })
    conn.close()
    return results

# ── 루브릭 태그 집계 ──────────────────────────────────────────────────────────
def count_rubric_tags(text: str):
    return (
        len(re.findall(r'\[절차\]', text)),
        len(re.findall(r'\[개념\]', text)),
    )

def rubric_tags_at_cycle(cycle_dir: Path):
    rp = cycle_dir / "rubric_used.md"
    if not rp.exists():
        exp_dir = cycle_dir.parent.parent
        rp = exp_dir / "rubrics" / "master_rubric.md"
        if not rp.exists():
            rp = exp_dir / "rubrics" / "v00_rubric.md"
    if not rp.exists():
        return 0, 0
    return count_rubric_tags(rp.read_text(encoding="utf-8"))

# ── 완료된 사이클 ─────────────────────────────────────────────────────────────
def load_cycles(cycles_dir, max_cycles, criterion_codes):
    cycles = []
    for i in range(1, max_cycles + 1):
        cd = cycles_dir / f"cycle_{i:03d}"
        if not cd.exists():
            break
        mp = cd / "cycle_metrics.json"
        if not mp.exists():
            cycles.append({"cycle": i, "status": "in_progress"})
            break

        m = json.loads(mp.read_text(encoding="utf-8"))

        # Analyst / Auditor 이력
        audit_history = []
        for r in range(1, 4):
            ap = cd / f"auditor_decision_r{r}.json"
            if not ap.exists():
                break
            ad = json.loads(ap.read_text(encoding="utf-8"))
            status = ad.get("status", "?")
            analyst_path = cd / f"analyst_raw_r{r}.md"
            auditor_path = cd / f"auditor_raw_r{r}.md"
            analyst_text = analyst_path.read_text(encoding="utf-8") if analyst_path.exists() else ""
            if status == "ANALYST_INVALID":
                auditor_text = f"[무효 사유] {ad.get('reason', '')}"
            else:
                auditor_text = auditor_path.read_text(encoding="utf-8") if auditor_path.exists() else ad.get("reason", "")
            audit_history.append({
                "revision": r,
                "status": status,
                "analyst_text": analyst_text,
                "auditor_text": auditor_text,
            })

        # 루브릭 diff
        diff_items = []
        dp = cd / "rubric_diff.md"
        if dp.exists():
            diff_text = dp.read_text(encoding="utf-8")
            for code in criterion_codes:
                pat = rf'### {re.escape(code)}\n\*\*이전:\*\* (.+?)\n\*\*이후:\*\* (.+?)(?:\n|$)'
                hit = re.search(pat, diff_text, re.DOTALL)
                if hit:
                    diff_items.append({
                        "code": code,
                        "old": hit.group(1).strip()[:300],
                        "new": hit.group(2).strip()[:300],
                    })

        proc, conc = rubric_tags_at_cycle(cd)
        gsa = m.get("gold_standard_accuracy", {})

        cycles.append({
            "cycle": i,
            "status": "done",
            "kappa": m.get("fleiss_kappa_overall"),
            "kappa_by": m.get("fleiss_kappa_by_criterion", {}),
            "disagreements": m.get("disagreement_pairs_count", 0),
            "auditor_decision": m.get("auditor_decision", "?"),
            "criteria_changed": m.get("criteria_changed", []),
            "boundary": m.get("boundary_case_grading", {}),
            "gold_std": gsa,
            "audit_history": audit_history,
            "diff_items": diff_items,
            "proc_count": proc,
            "conc_count": conc,
        })

    return cycles

# ── 골드스탠더드 & 경계케이스 메타 ───────────────────────────────────────────
def load_gold_standard(exp_dir):
    gs_path = exp_dir / "expected_scores_matrix.json"
    if not gs_path.exists():
        gs_path = PROJECT_DIR / "experiment_design" / "expected_scores_matrix.json"
        if not gs_path.exists():
            return {}, {}
    d = json.loads(gs_path.read_text(encoding="utf-8"))
    gold = d.get("gold_standard", {})
    bm = {}
    for bc in d.get("boundary_cases", []):
        key = f"{bc['student_id']}_{bc['criterion_code']}"
        bm[key] = bc
    return gold, bm

# ── 메인 ─────────────────────────────────────────────────────────────────────
def build_data(exp_name="exp1_analytic", refresh_secs=None):
    exp_dir = PROJECT_DIR / "experiments" / exp_name
    config_path = exp_dir / "config.json"
    cfg = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    
    criterion_codes = cfg.get("criterion_codes", [])
    max_cycles = cfg.get("max_cycles", 10)
    boundary_cases = cfg.get("boundary_cases", [])
    db_path = exp_dir / "data" / "rubric_carver.sqlite"
    cycles_dir = exp_dir / "cycles"

    gold, boundary_meta = load_gold_standard(exp_dir)
    proc0, conc0 = rubric_tags_at_cycle(cycles_dir / "cycle_001")
    # 초기 루브릭 (master or v00_rubric.md)
    if proc0 == 0 and conc0 == 0:
        rp = exp_dir / "rubrics" / "v00_rubric.md"
        if rp.exists():
            proc0, conc0 = count_rubric_tags(rp.read_text(encoding="utf-8"))

    student_texts = {}
    for s in STUDENTS:
        student_file = PROJECT_DIR / "students" / f"student_{s}.md"
        if student_file.exists():
            student_texts[s] = student_file.read_text(encoding="utf-8")

    
    # Load Prompts from Paper Appendix
    prompts = {}
    appendix_dir = PROJECT_DIR / "analysis" / "prompts"
    prompt_files = {
        "A": ("Appendix_A_Grader_Prompt.md", "교사 에이전트 시스템 프롬프트 (T1~T4)"),
        "B": ("Appendix_B_Analyst_Prompt.md", "분석관 에이전트 시스템 프롬프트"),
        "C": ("Appendix_C_Auditor_Prompt.md", "심의관 에이전트 시스템 프롬프트"),
        "C2": ("Appendix_C2_Auditor_Evaluation_Guide.md", "심의관 평가 가이드 (수학교육학적 렌즈)")
    }
    
    for key, (filename, title) in prompt_files.items():
        file_path = appendix_dir / filename
        if file_path.exists():
            prompts[key] = {
                "title": title,
                "content": file_path.read_text(encoding="utf-8")
            }
        else:
            prompts[key] = {
                "title": title,
                "content": f"{filename} 파일을 찾을 수 없습니다."
            }

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "refresh_secs": refresh_secs,
        "students": STUDENTS,
        "student_texts": student_texts,
        "teachers": TEACHERS,
        "teacher_labels": TEACHER_LABELS,
        "criterion_codes": criterion_codes,
        "max_cycles": max_cycles,
        "boundary_cases": list(boundary_meta.keys()),
        "boundary_meta": boundary_meta,
        "gold_standard": gold,
        "live": load_live(db_path, criterion_codes),
        "all_grades": load_all_grades(db_path),
        "cycles": load_cycles(cycles_dir, max_cycles, criterion_codes),
        "init_proc": proc0,
        "init_conc": conc0,
        "prompts": prompts,
    }
