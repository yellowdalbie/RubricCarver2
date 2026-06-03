import os
import sys
import json
import re
import time
import logging
import argparse
from collections import defaultdict
from datetime import datetime
from database import ExperimentDB
from agents import (GraderAgent, AnalystAgent, AuditorAgent,
                    compute_scores_from_checklist, TEACHER_PERSONAS)

# .env 로드
_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../Rubric/.env")
if os.path.exists(_ENV_FILE):
    with open(_ENV_FILE) as _f:
        for _line in _f:
            _line = _line.strip()
            if '=' in _line and not _line.startswith('#'):
                _k, _v = _line.split('=', 1)
                os.environ.setdefault(_k, _v)

# ──────────────────────────────────────────────────────────────────────────────
# 전역 설정 (argparse 이후 갱신됨)
# ──────────────────────────────────────────────────────────────────────────────
ENGINE_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR  = os.path.dirname(ENGINE_DIR)
STUDENTS_DIR = os.path.join(PROJECT_DIR, "students")

EXP_DIR = None
DATA_DIR = None
RUBRICS_DIR = None
CYCLES_DIR = None
EXP_CONFIG = {}
CRITERION_CODES = []

# ── 교사 목록 (TEACHER_PERSONAS 딕셔너리 → 정렬된 리스트)
TEACHERS = [TEACHER_PERSONAS[tid] for tid in sorted(TEACHER_PERSONAS.keys())]

# ── 경계 케이스 목록 (exp_config.json 에 정의되지 않으면 빈 리스트)
BOUNDARY_CASES = []

def extract_criteria_from_rubric(rubric_md):
    """
    루브릭 마크다운에서 표(|)를 찾아 첫 번째 열의 채점 코드(예: C1-1, C2)를 추출합니다.
    """
    codes = []
    lines = rubric_md.split('\n')
    in_table = False
    for line in lines:
        line = line.strip()
        if line.startswith('|') and '코드' in line and '이진 채점 기준' in line:
            in_table = True
            continue
        if in_table and line.startswith('|'):
            if '---' in line:
                continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) > 1:
                # 첫 번째 열에서 마크다운 볼드(**) 등 제거
                code_raw = parts[1].replace('*', '').strip()
                if code_raw.startswith('C'):
                    codes.append(code_raw)
        elif in_table and not line.startswith('|') and line != '':
            in_table = False
    return codes

logger = logging.getLogger("RubricCarver")


# ──────────────────────────────────────────────────────────────────────────────
# 파일 저장 헬퍼
# ──────────────────────────────────────────────────────────────────────────────
def save_file(path: str, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        if isinstance(content, (dict, list)):
            f.write(json.dumps(content, ensure_ascii=False, indent=2))
        else:
            f.write(str(content))


# ──────────────────────────────────────────────────────────────────────────────
# 루브릭 검증
# ──────────────────────────────────────────────────────────────────────────────
def validate_rubric_structure(rubric_text: str, cycle_name: str) -> bool:
    for code in CRITERION_CODES:
        if code not in rubric_text:
            logger.warning(f"[{cycle_name}] ⚠️ 구조 오류: 필수 코드 {code} 누락")
            return False
    return True


def validate_analyst_response(proposal: str, known_students: list) -> tuple:
    if '```markdown' not in proposal:
        return False, "루브릭 개정안(```markdown 블록) 누락"
    mentioned = re.findall(r'Student\s+([A-Z][0-9])', proposal)
    hallucinated = [s for s in set(mentioned) if s not in known_students]
    if hallucinated:
        return False, f"존재하지 않는 학생 ID 언급: {hallucinated}"
    match = re.search(r'```markdown\s*(.*?)\s*```', proposal, re.DOTALL)
    if not match:
        return False, "마크다운 블록 추출 실패"
    if not validate_rubric_structure(match.group(1), "Analyst Proposal"):
        return False, "루브릭 기계적 구조 검증 실패"
    return True, "OK"


# ──────────────────────────────────────────────────────────────────────────────
# 불일치 표 생성 (분석관 입력용 텍스트)
# ──────────────────────────────────────────────────────────────────────────────
def build_disagreement_table(rows, students: list, teachers: list) -> str:
    teacher_ids = [t['id'] for t in teachers]
    data = {}
    for row in rows:
        sid, tid = row['student_id'], row['teacher_id']
        try:
            checklist = json.loads(row['checklist_data']) if row['checklist_data'] else {}
        except Exception:
            checklist = {}
        if sid not in data:
            data[sid] = {}
        data[sid][tid] = {
            code: {
                'answer': checklist.get(code, {}).get('answer', '?'),
                'basis': checklist.get(code, {}).get('basis', ''),
            }
            for code in CRITERION_CODES
        }

    lines = []
    for sid in students:
        if sid not in data:
            continue
        s_data = data[sid]
        totals = {tid: sum(1 for c in CRITERION_CODES
                           if s_data.get(tid, {}).get(c, {}).get('answer', 'NO').upper() == 'YES')
                  for tid in teacher_ids if tid in s_data}
        scores_str = " / ".join(f"{tid}:{totals.get(tid,'?')}점" for tid in teacher_ids)
        lines.append(f"\n## Student {sid} [{scores_str}]")
        for code in CRITERION_CODES:
            answers = {tid: s_data.get(tid, {}).get(code, {}).get('answer', '?')
                       for tid in teacher_ids if tid in s_data}
            unique = set(v.upper() for v in answers.values() if v != '?')
            flag = "  ← ⚠️ 불일치" if len(unique) > 1 else ""
            ans_str = " | ".join(f"{tid}={answers.get(tid,'?')}" for tid in teacher_ids)
            lines.append(f"  {code}: {ans_str}{flag}")
            # 불일치가 있는 기준에 한해 교사별 채점 근거 추가
            if len(unique) > 1:
                for tid in teacher_ids:
                    if tid in s_data:
                        basis = s_data[tid].get(code, {}).get('basis', '')
                        if basis:
                            lines.append(f"    [{tid} 근거] {basis}")
    return "\n".join(lines)


def extract_disagreed_student_ids(rows, students: list, teachers: list) -> list[str]:
    """불일치가 하나라도 있는 학생 ID 목록 반환"""
    teacher_ids = [t['id'] for t in teachers]
    matrix = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        sid, tid = row['student_id'], row['teacher_id']
        try:
            checklist = json.loads(row['checklist_data']) if row['checklist_data'] else {}
        except Exception:
            checklist = {}
        for code in CRITERION_CODES:
            matrix[sid][code][tid] = checklist.get(code, {}).get('answer', 'NO').upper()

    disagreed = []
    for sid in students:
        for code in CRITERION_CODES:
            votes = set(matrix[sid][code].get(tid, 'NO') for tid in teacher_ids)
            if len(votes) > 1:
                disagreed.append(sid)
                break
    return disagreed


# ──────────────────────────────────────────────────────────────────────────────
# Fleiss Kappa 계산
# ──────────────────────────────────────────────────────────────────────────────
def compute_fleiss_kappa(rows, students: list, teachers: list) -> tuple:
    n = len(teachers)
    teacher_ids = [t['id'] for t in teachers]

    matrix = defaultdict(dict)
    for row in rows:
        sid, tid = row['student_id'], row['teacher_id']
        try:
            checklist = json.loads(row['checklist_data']) if row['checklist_data'] else {}
        except Exception:
            checklist = {}
        for code in CRITERION_CODES:
            matrix[(sid, code)][tid] = checklist.get(code, {}).get('answer', 'NO').upper()

    def _kappa(yes_counts: list) -> float | None:
        N = len(yes_counts)
        if N == 0 or n <= 1:
            return None
        P_bar = (1 / (N * n * (n - 1))) * sum(ny * (ny - 1) + (n - ny) * (n - ny - 1) for ny in yes_counts)
        p_yes = sum(yes_counts) / (N * n)
        p_no  = 1.0 - p_yes
        P_e   = p_yes ** 2 + p_no ** 2
        if P_e >= 1.0:
            return 1.0
        return round((P_bar - P_e) / (1.0 - P_e), 4)

    all_yes = [
        sum(1 for tid in teacher_ids if matrix.get((sid, code), {}).get(tid, 'NO') == 'YES')
        for sid in students for code in CRITERION_CODES
    ]
    overall = _kappa(all_yes)

    kappa_by = {}
    for code in CRITERION_CODES:
        yes_list = [
            sum(1 for tid in teacher_ids if matrix.get((sid, code), {}).get(tid, 'NO') == 'YES')
            for sid in students
        ]
        kappa_by[code] = _kappa(yes_list)

    disagree = sum(1 for ny in all_yes if 0 < ny < n)
    return overall, kappa_by, disagree


# ──────────────────────────────────────────────────────────────────────────────
# 루브릭 diff 계산
# ──────────────────────────────────────────────────────────────────────────────
def extract_rubric_criteria(rubric_text: str) -> dict:
    criteria = {}
    for code in CRITERION_CODES:
        pattern = rf'\|\s*\*\*{re.escape(code)}\*\*\s*\|\s*(.+?)\s*\|'
        match = re.search(pattern, rubric_text, re.DOTALL)
        if match:
            criteria[code] = re.sub(r'\s+', ' ', match.group(1).strip())
    return criteria


def compute_rubric_diff(old_rubric: str, new_rubric: str) -> tuple:
    old_c = extract_rubric_criteria(old_rubric)
    new_c = extract_rubric_criteria(new_rubric)
    changed, unchanged = [], []
    for code in CRITERION_CODES:
        if old_c.get(code, "") != new_c.get(code, ""):
            changed.append({"code": code, "old": old_c.get(code, ""), "new": new_c.get(code, "")})
        else:
            unchanged.append(code)
    return changed, unchanged


def generate_diff_md(changed: list, unchanged: list) -> str:
    lines = ["# 루브릭 기준 변경사항\n"]
    if changed:
        lines.append(f"## 변경된 기준 ({len(changed)}개)\n")
        for item in changed:
            lines += [f"### {item['code']}",
                      f"**이전:** {item['old']}",
                      f"**이후:** {item['new']}\n"]
    else:
        lines.append("## 변경된 기준 없음\n")
    if unchanged:
        lines.append(f"## 변경 없는 기준 ({len(unchanged)}개)")
        lines.append(", ".join(unchanged))
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# 사이클 아티팩트 저장 헬퍼
# ──────────────────────────────────────────────────────────────────────────────
def save_grade_files(cycle_dir: str, rows, teachers: list, students: list):
    grades_dir = os.path.join(cycle_dir, "grades")
    os.makedirs(grades_dir, exist_ok=True)
    teacher_data = {t['id']: {"teacher_id": t['id'], "teacher_name": t['name'], "grades": {}} for t in teachers}
    for row in rows:
        sid, tid = row['student_id'], row['teacher_id']
        if tid not in teacher_data:
            continue
        try:
            checklist = json.loads(row['checklist_data']) if row['checklist_data'] else {}
        except Exception:
            checklist = {}
        teacher_data[tid]["grades"][sid] = {
            "checklist": checklist,
            "total": row['total'],
            "level": row['level'],
            "comment": row['comment'],
        }
    for tid, payload in teacher_data.items():
        save_file(os.path.join(grades_dir, f"teacher_{tid}.json"), payload)


def save_disagreement_matrix(cycle_dir: str, rows, teachers: list, students: list):
    teacher_ids = [t['id'] for t in teachers]
    raw = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        sid, tid = row['student_id'], row['teacher_id']
        try:
            checklist = json.loads(row['checklist_data']) if row['checklist_data'] else {}
        except Exception:
            checklist = {}
        for code in CRITERION_CODES:
            raw[sid][code][tid] = checklist.get(code, {}).get('answer', 'NO').upper()

    result = {}
    for sid in students:
        result[sid] = {}
        for code in CRITERION_CODES:
            votes = raw[sid][code]
            vals = set(votes.get(tid, 'NO') for tid in teacher_ids)
            result[sid][code] = {**{tid: votes.get(tid, '?') for tid in teacher_ids},
                                 "agreed": len(vals) <= 1}

    students_with_disagreement = [
        sid for sid in students
        if any(not result[sid][c]["agreed"] for c in CRITERION_CODES)
    ]
    save_file(os.path.join(cycle_dir, "disagreement_matrix.json"), {
        "students_with_disagreement": students_with_disagreement,
        "matrix": result,
    })
    return result


def build_cycle_metrics(cycle_idx: int, rows, students: list, teachers: list,
                        kappa: float, kappa_by: dict, disagree_count: int,
                        audit_decision: str, criteria_changed: list, criteria_unchanged: list,
                        gold_std_accuracy: dict | None = None) -> dict:
    teacher_ids = [t['id'] for t in teachers]
    raw = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        sid, tid = row['student_id'], row['teacher_id']
        try:
            checklist = json.loads(row['checklist_data']) if row['checklist_data'] else {}
        except Exception:
            checklist = {}
        for code in CRITERION_CODES:
            raw[sid][code][tid] = checklist.get(code, {}).get('answer', 'NO').upper()

    boundary_results = {}
    for sid, code in BOUNDARY_CASES:
        boundary_results[f"{sid}_{code}"] = {
            tid: raw[sid][code].get(tid, '?') for tid in teacher_ids
        }

    return {
        "cycle": cycle_idx,
        "timestamp": datetime.now().isoformat(),
        "fleiss_kappa_overall": kappa,
        "fleiss_kappa_by_criterion": kappa_by,
        "disagreement_pairs_count": disagree_count,
        "boundary_case_grading": boundary_results,
        "auditor_decision": audit_decision,
        "criteria_changed": criteria_changed,
        "criteria_unchanged": criteria_unchanged,
        "gold_standard_accuracy": gold_std_accuracy or {},
    }


# ──────────────────────────────────────────────────────────────────────────────
# 실험 이력 관리
# ──────────────────────────────────────────────────────────────────────────────
def extract_disagreed_pairs(rows, students: list, teachers: list) -> list[tuple[str, str]]:
    """불일치가 있는 (학생ID, 기준코드) 쌍 전체 반환"""
    teacher_ids = [t['id'] for t in teachers]
    matrix = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        sid, tid = row['student_id'], row['teacher_id']
        try:
            checklist = json.loads(row['checklist_data']) if row['checklist_data'] else {}
        except Exception:
            checklist = {}
        for code in CRITERION_CODES:
            matrix[sid][code][tid] = checklist.get(code, {}).get('answer', 'NO').upper()
    pairs = []
    for sid in students:
        for code in CRITERION_CODES:
            votes = set(matrix[sid][code].get(tid, 'NO') for tid in teacher_ids)
            if len(votes) > 1:
                pairs.append((sid, code))
    return pairs


def build_history_entry(cycle_idx: int, kappa, disagree_count: int,
                        disagreed_pairs: list, audit_decision: str,
                        rubric_changes: list) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"\n## Cycle {cycle_idx:03d} ({timestamp})"]
    lines.append(f"- Fleiss κ: {kappa} | 불일치 쌍: {disagree_count}건")

    if disagreed_pairs:
        by_student: dict[str, list] = defaultdict(list)
        for sid, code in disagreed_pairs:
            by_student[sid].append(code)
        pairs_str = ", ".join(
            f"{sid}({', '.join(codes)})" for sid, codes in sorted(by_student.items())
        )
        lines.append(f"- 불일치 학생/기준: {pairs_str}")
    else:
        lines.append("- 불일치 학생/기준: 없음")

    if rubric_changes:
        for ch in rubric_changes:
            old_s = (ch['old'][:50] + '…') if len(ch['old']) > 50 else ch['old']
            new_s = (ch['new'][:50] + '…') if len(ch['new']) > 50 else ch['new']
            lines.append(f"- 변경 {ch['code']}: \"{old_s}\" → \"{new_s}\"")
    else:
        lines.append("- 루브릭 변경: 없음")

    lines.append(f"- Auditor 결과: {audit_decision}")
    return "\n".join(lines)


def load_cycle_history(history_path: str) -> str | None:
    if os.path.exists(history_path):
        with open(history_path, 'r', encoding='utf-8') as f:
            return f.read().strip() or None
    return None


def append_history_entry(history_path: str, entry: str):
    with open(history_path, 'a', encoding='utf-8') as f:
        f.write(entry + '\n')


# ──────────────────────────────────────────────────────────────────────────────
# 골드스탠더드 정확도 계산
# ──────────────────────────────────────────────────────────────────────────────
def extract_criterion_tags(rubric_text: str) -> dict[str, str]:
    """루브릭 텍스트에서 각 기준의 [절차]/[개념] 태그 추출 (루브릭 진화에 따라 동적으로 변할 수 있음)"""
    tags = {}
    for code in CRITERION_CODES:
        for line in rubric_text.split('\n'):
            if f'**{code}**' in line and '|' in line:
                if '[절차]' in line:
                    tags[code] = '절차'
                    break
                elif '[개념]' in line:
                    tags[code] = '개념'
                    break
        if code not in tags:
            tags[code] = '미분류'
    return tags


def compute_gold_standard_accuracy(
    rows, students: list, teachers: list,
    gold_standard: dict, criterion_tags: dict,
) -> dict:
    """교사 채점 다수결을 골드스탠더드와 비교하여 정확도 계산.
    다수결: 4인 중 ≥3 YES → YES, ≤1 YES → NO, 2-2 → SPLIT(불일치로 처리).
    """
    teacher_ids = [t['id'] for t in teachers]
    n = len(teacher_ids)

    matrix: dict = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        sid, tid = row['student_id'], row['teacher_id']
        try:
            checklist = json.loads(row['checklist_data']) if row['checklist_data'] else {}
        except Exception:
            checklist = {}
        for code in CRITERION_CODES:
            matrix[sid][code][tid] = checklist.get(code, {}).get('answer', 'NO').upper()

    def majority_vote(sid, code):
        yes_n = sum(1 for tid in teacher_ids if matrix[sid][code].get(tid, 'NO') == 'YES')
        if yes_n > n / 2:   return 'YES'
        if yes_n < n / 2:   return 'NO'
        return 'SPLIT'

    boundary_set = set(BOUNDARY_CASES)
    totals   = {"correct": 0, "total": 0, "split": 0}
    boundary = {"correct": 0, "total": 0}
    by_tag: dict = defaultdict(lambda: {"correct": 0, "total": 0})
    per_teacher = {tid: {"correct": 0, "total": 0} for tid in teacher_ids}
    key_students: dict = {}

    for sid in students:
        if sid not in gold_standard:
            continue
        gs = gold_standard[sid]
        s_correct, s_wrong = [], []

        for code in CRITERION_CODES:
            gs_val = str(gs.get(code, '')).upper()
            if gs_val not in ('YES', 'NO'):
                continue

            mv = majority_vote(sid, code)
            correct = (mv == gs_val)

            totals["total"] += 1
            if mv == 'SPLIT':
                totals["split"] += 1
            else:
                totals["correct"] += int(correct)
                (s_correct if correct else s_wrong).append(code)

            if (sid, code) in boundary_set:
                boundary["total"] += 1
                if mv != 'SPLIT':
                    boundary["correct"] += int(correct)

            tag = criterion_tags.get(code, '미분류')
            by_tag[tag]["total"] += 1
            if mv != 'SPLIT':
                by_tag[tag]["correct"] += int(correct)

            for tid in teacher_ids:
                t_val = matrix[sid][code].get(tid, 'NO')
                per_teacher[tid]["total"] += 1
                per_teacher[tid]["correct"] += int(t_val == gs_val)

        if sid in ('B2', 'C3'):
            denom = len(s_correct) + len(s_wrong)
            key_students[sid] = {
                "correct_criteria": s_correct,
                "wrong_criteria":   s_wrong,
                "accuracy": round(len(s_correct) / denom, 3) if denom else 0,
            }

    def acc(d): return round(d["correct"] / d["total"], 3) if d["total"] else 0

    return {
        "overall_accuracy":  acc(totals),
        "overall_correct":   totals["correct"],
        "overall_total":     totals["total"],
        "split_count":       totals["split"],
        "boundary_accuracy": acc(boundary),
        "boundary_correct":  boundary["correct"],
        "boundary_total":    boundary["total"],
        "tag_accuracy": {
            tag: {"accuracy": acc(v), "correct": v["correct"], "total": v["total"]}
            for tag, v in by_tag.items()
        },
        "per_teacher_accuracy": {
            tid: round(per_teacher[tid]["correct"] / per_teacher[tid]["total"], 3)
            if per_teacher[tid]["total"] else 0
            for tid in teacher_ids
        },
        "key_students": key_students,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 불일치 학생 원문 로드
# ──────────────────────────────────────────────────────────────────────────────
def load_student_answers(student_ids: list[str]) -> dict[str, str]:
    """지정된 학생들의 답안 원문을 파일에서 로드"""
    answers = {}
    for sid in student_ids:
        path = os.path.join(STUDENTS_DIR, f"student_{sid}.md")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                answers[sid] = f.read()
        else:
            logger.warning(f"  [!] 학생 답안 파일 없음: {path}")
    return answers


# ──────────────────────────────────────────────────────────────────────────────
# RubricCarver 2.0 엔진 메인
# ──────────────────────────────────────────────────────────────────────────────
def check_setup():
    """필수 파일 존재 여부 및 루브릭 구조 검증 (--check 모드)"""
    ok = True

    achievement_levels_path = os.path.join(EXP_DIR, "achievement_levels.md")
    if not os.path.exists(achievement_levels_path):
        achievement_levels_path = os.path.join(PROJECT_DIR, "2026수능_11_성취수준.md")

    gs_path = os.path.join(EXP_DIR, "expected_scores_matrix.json")
    if not os.path.exists(gs_path):
        gs_path = os.path.join(PROJECT_DIR, "experiment_design", "expected_scores_matrix.json")

    rubric_path = os.path.join(RUBRICS_DIR, "master_rubric.md")
    if not os.path.exists(rubric_path):
        rubric_path = os.path.join(RUBRICS_DIR, "v00_rubric.md")

    required = [
        os.path.join(PROJECT_DIR, "question.md"),
        rubric_path,
        achievement_levels_path,
        gs_path,
    ]
    for path in required:
        if not os.path.exists(path):
            print(f"  [MISSING] {path}")
            ok = False
        else:
            print(f"  [OK]      {path}")

    student_files = sorted(f for f in os.listdir(STUDENTS_DIR)
                           if f.startswith("student_") and f.endswith(".md"))
    print(f"  [INFO] 학생 파일 {len(student_files)}개 발견: "
          f"{[f[8:-3] for f in student_files]}")
    if len(student_files) == 0:
        print("  [ERROR] 학생 파일 없음")
        ok = False

    if os.path.exists(rubric_path):
        with open(rubric_path, 'r', encoding='utf-8') as f:
            rubric = f.read()
        if validate_rubric_structure(rubric, "pre-check"):
            print("  [OK]      루브릭 구조 검증 통과")
        else:
            print("  [ERROR]   루브릭 구조 검증 실패")
            ok = False

    levels_path = os.path.join(EXP_DIR, "achievement_levels.md")
    if os.path.exists(levels_path):
        with open(levels_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if "플레이스홀더" in content:
            print("  [WARN]    achievement_levels.md가 플레이스홀더 상태")
        else:
            print("  [OK]      achievement_levels.md 작성됨")

    print("\n" + ("✅ 설정 검증 통과" if ok else "❌ 설정 검증 실패 — 위 항목을 수정하세요"))
    return ok


def run_carver():
    global EXP_DIR, DATA_DIR, RUBRICS_DIR, CYCLES_DIR, EXP_CONFIG, CRITERION_CODES, BOUNDARY_CASES

    parser = argparse.ArgumentParser()
    parser.add_argument('--exp-dir', required=True,
                        help='경로 지정 (예: experiments/exp1_analytic)')
    parser.add_argument('--check', action='store_true',
                        help='설정 파일 유효성 검사만 수행하고 종료')
    parser.add_argument('--test-cycle', action='store_true',
                        help='cycle_001만 실행 후 종료 (단일 사이클 테스트)')
    args = parser.parse_args()

    EXP_DIR = os.path.abspath(args.exp_dir)
    if not os.path.exists(EXP_DIR):
        print(f"Error: Experiment directory not found: {EXP_DIR}")
        return

    # 설정 파일 로드
    config_path = os.path.join(EXP_DIR, "config.json")
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            EXP_CONFIG = json.load(f)
    else:
        print(f"Error: config.json not found in {EXP_DIR}")
        return

    CRITERION_CODES = EXP_CONFIG.get("criterion_codes", [])
    BOUNDARY_CASES = EXP_CONFIG.get("boundary_cases", [])

    DATA_DIR = os.path.join(EXP_DIR, "data")
    RUBRICS_DIR = os.path.join(EXP_DIR, "rubrics")
    CYCLES_DIR = os.path.join(EXP_DIR, "cycles")
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(CYCLES_DIR, exist_ok=True)
    os.makedirs(RUBRICS_DIR, exist_ok=True)

    if args.check:
        check_setup()
        return

    test_mode  = args.test_cycle
    max_cycles = 1 if test_mode else EXP_CONFIG.get("max_cycles", 10)
    mode_label = "TEST(1-cycle)" if test_mode else "EXPERIMENT"

    db_path      = os.path.join(DATA_DIR, "rubric_carver.sqlite")
    log_file     = os.path.join(EXP_DIR, "carver_execution.log")
    history_path = os.path.join(EXP_DIR, "experiment_history.md")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    pass

    try:
        logger.info(f"=== RubricCarver 2.0 Engine Starting [{mode_label}] ===")

        with open(os.path.join(PROJECT_DIR, "question.md"), 'r', encoding='utf-8') as f:
            question = f.read()

        # 성취수준별 진술문 로드 (분석관·심의관에 전달)
        achievement_levels_path = os.path.join(EXP_DIR, "achievement_levels.md")
        if not os.path.exists(achievement_levels_path):
            achievement_levels_path = os.path.join(PROJECT_DIR, "2026수능_11_성취수준.md")
        
        achievement_levels = None
        if os.path.exists(achievement_levels_path):
            with open(achievement_levels_path, 'r', encoding='utf-8') as f:
                achievement_levels = f.read()
            logger.info("  [+] 성취수준별 진술문 로드 완료")
        else:
            logger.warning("  [!] 성취수준.md 없음 — 분석관/심의관 규범적 판단 제한됨")

        # 수학교육학적 관점 문서 로드 (심의관에 전달)
        auditor_doc_path = os.path.join(EXP_DIR, "2026수능_11_판정관.md")
        if not os.path.exists(auditor_doc_path):
            auditor_doc_path = os.path.join(PROJECT_DIR, "2026수능_11_판정관.md")
            
        auditor_doc = None
        if os.path.exists(auditor_doc_path):
            with open(auditor_doc_path, 'r', encoding='utf-8') as f:
                auditor_doc = f.read()
            logger.info("  [+] 판정관(Auditor) 지침 로드 완료")
        else:
            logger.warning("  [!] 판정관.md 없음 — 심의관 수학교육학적 판단 제한됨")

        # 문항 출제 의도 추출
        intent_match = re.search(r'##\s*출제\s*의도\s*\n(.*?)(?:\n##|\Z)', question, re.DOTALL)
        question_intent = intent_match.group(1).strip() if intent_match else question[:300]

        # 골드스탠더드 로드 (사후 검증용 — 분석관/심의관에는 전달하지 않음)
        gs_path = os.path.join(EXP_DIR, "expected_scores_matrix.json")
        if not os.path.exists(gs_path):
            gs_path = os.path.join(PROJECT_DIR, "experiment_design", "expected_scores_matrix.json")
        
        gold_standard = {}
        if os.path.exists(gs_path):
            with open(gs_path, 'r', encoding='utf-8') as f:
                gold_standard = json.load(f).get("gold_standard", {})
            logger.info(f"  [+] 골드스탠더드 로드 완료 ({len(gold_standard)}명)")

        current_idx = 1
        previous_rubric = None
        current_rubric_path = os.path.join(RUBRICS_DIR, "v00_rubric.md")

        # Resume 로직: cycle_{N:03d}/next_rubric.md 탐색
        while os.path.exists(os.path.join(CYCLES_DIR, f"cycle_{current_idx:03d}", "next_rubric.md")):
            if current_idx > 1:
                with open(current_rubric_path, 'r', encoding='utf-8') as _f:
                    previous_rubric = _f.read()
            current_rubric_path = os.path.join(CYCLES_DIR, f"cycle_{current_idx:03d}", "next_rubric.md")
            current_idx += 1

        with open(current_rubric_path, 'r', encoding='utf-8') as f:
            current_rubric = f.read()

        if test_mode:
            max_cycles = current_idx

        db = ExperimentDB(db_path)

        # 학생 목록: students/student_{ID}.md 에서 ID 추출
        student_files = sorted(f for f in os.listdir(STUDENTS_DIR) if f.startswith("student_") and f.endswith(".md"))
        students = [f[len("student_"):-len(".md")] for f in student_files]
        logger.info(f"Loaded {len(students)} students: {students}")

        # ── 메인 사이클 루프 ──────────────────────────────────────────────────
        while current_idx <= max_cycles:
            cycle_name = f"cycle_{current_idx:03d}"
            cycle_dir = os.path.join(CYCLES_DIR, cycle_name)
            os.makedirs(cycle_dir, exist_ok=True)
            db_cycle_id = db.add_cycle(cycle_name, current_rubric)

            if EXP_CONFIG.get("dynamic_criteria"):
                extracted_codes = extract_criteria_from_rubric(current_rubric)
                if extracted_codes:
                    CRITERION_CODES = extracted_codes
                    logger.info(f"  [>] 동적 평가 기준 파싱: {CRITERION_CODES}")

            logger.info(f"=== {cycle_name} 시작 ===")

            if not validate_rubric_structure(current_rubric, cycle_name):
                logger.error("Rubric structure invalid. Terminating.")
                break

            # ① 사용 루브릭 스냅샷 저장
            save_file(os.path.join(cycle_dir, "rubric_used.md"), current_rubric)

            # ② 채점 단계 ─────────────────────────────────────────────────────
            for t_info in TEACHERS:
                try:
                    grader = GraderAgent(t_info)
                    logger.info(f"  [+] {t_info['name']} grading...")
                    for sid in students:
                        if os.path.exists(os.path.join(ENGINE_DIR, "PAUSE_SIGNAL")):
                            logger.info("PAUSE_SIGNAL detected. Stopping.")
                            return
                        if db.check_grade_exists(db_cycle_id, sid, t_info['id']):
                            continue

                        with open(os.path.join(STUDENTS_DIR, f"student_{sid}.md"), 'r', encoding='utf-8') as f:
                            s_answer = f.read()

                        result = grader.grade(question, current_rubric, s_answer, CRITERION_CODES)
                        raw_checklist = result.get("checklist", {})
                        checklist = {
                            k: (v if isinstance(v, dict) else {"answer": str(v), "basis": ""})
                            for k, v in raw_checklist.items()
                        }
                        element_scores, total = compute_scores_from_checklist(checklist, CRITERION_CODES)

                        db.add_teacher_grade(db_cycle_id, sid, t_info['id'],
                                             json.dumps(checklist, ensure_ascii=False),
                                             json.dumps(element_scores, ensure_ascii=False),
                                             total, "", result.get("comment", ""))
                        time.sleep(0.5)
                except Exception as e:
                    logger.error(f"Error grading [{t_info['name']}]: {e}")

            # ③ 채점 결과 파일 저장 ────────────────────────────────────────────
            rows = db.get_cycle_checklist_data(db_cycle_id)
            save_grade_files(cycle_dir, rows, TEACHERS, students)
            save_disagreement_matrix(cycle_dir, rows, TEACHERS, students)

            # ④ Fleiss Kappa 계산
            kappa, kappa_by_criterion, disagree_count = compute_fleiss_kappa(rows, students, TEACHERS)
            logger.info(f"  [κ] Fleiss Kappa = {kappa}  |  불일치 쌍 = {disagree_count}")

            # ④-b 골드스탠더드 일치율 계산 (분석관/심의관에는 전달하지 않음 — 사후 검증 전용)
            criterion_tags = extract_criterion_tags(current_rubric)
            gold_std_accuracy = compute_gold_standard_accuracy(
                rows, students, TEACHERS, gold_standard, criterion_tags
            )
            logger.info(
                f"  [GS] 전체 일치율={gold_std_accuracy['overall_accuracy']} "
                f"| 경계케이스={gold_std_accuracy['boundary_accuracy']} "
                f"| split={gold_std_accuracy['split_count']}건"
            )

            # ⑤ 분석 및 심의 단계 ─────────────────────────────────────────────
            criteria_changed, criteria_unchanged = [], list(CRITERION_CODES)

            # 사이클 시작 시 누적 이력 로드 (분석관·심의관 전달용)
            cycle_history = load_cycle_history(history_path)
            rubric_change_details: list = []

            # 전체 학생 원문 로드 (분석관 열람권)
            disagreed_sids = extract_disagreed_student_ids(rows, students, TEACHERS)
            student_answers = load_student_answers(students)
            logger.info(f"  [!] 불일치 학생 {len(disagreed_sids)}명: {disagreed_sids} | 전체 {len(students)}명 원문 분석관 전달")

            disagreement_table = build_disagreement_table(rows, students, TEACHERS)
            analyst = AnalystAgent()
            auditor = AuditorAgent()
            audit_decision = "FAILED_ALL"

            for revision in range(1, 4):
                try:
                    logger.info(f"  [*] Revision {revision} — Analyst analyzing...")
                    proposal = analyst.analyze(
                        disagreement_table, current_rubric, students,
                        question=question,
                        student_answers=student_answers,
                        achievement_levels=achievement_levels,
                        previous_rubric=previous_rubric,
                        cycle_history=cycle_history,
                    )
                    proposal_str = (json.dumps(proposal, ensure_ascii=False, indent=2)
                                    if isinstance(proposal, dict) else str(proposal))

                    save_file(os.path.join(cycle_dir, f"analyst_raw_r{revision}.md"), proposal_str)

                    valid, reason = validate_analyst_response(proposal_str, students)
                    if not valid:
                        logger.warning(f"  [!] Analyst invalid (r{revision}): {reason}")
                        db.add_cycle_result(db_cycle_id, revision, proposal_str, reason, "ANALYST_INVALID")
                        save_file(os.path.join(cycle_dir, f"auditor_decision_r{revision}.json"),
                                  {"revision": revision, "status": "ANALYST_INVALID", "reason": reason})
                        time.sleep(2)
                        continue

                    match = re.search(r'```markdown\s*(.*?)\s*```', proposal_str, re.DOTALL)
                    candidate_rubric = match.group(1) if match else proposal_str
                    save_file(os.path.join(cycle_dir, f"rubric_proposal_r{revision}.md"), candidate_rubric)

                    logger.info(f"  [*] Revision {revision} — Auditor reviewing...")
                    decision_text = auditor.audit(
                        proposal_str, question_intent,
                        previous_rubric=previous_rubric,
                        achievement_levels=achievement_levels,
                        auditor_doc=auditor_doc,
                        cycle_history=cycle_history,
                    )
                    decision_str = (json.dumps(decision_text, ensure_ascii=False, indent=2)
                                    if isinstance(decision_text, dict) else str(decision_text))
                    status = "APPROVED" if "APPROVED" in decision_str.upper() else "REJECTED"

                    save_file(os.path.join(cycle_dir, f"auditor_raw_r{revision}.md"), decision_str)
                    save_file(os.path.join(cycle_dir, f"auditor_decision_r{revision}.json"), {
                        "revision": revision,
                        "status": status,
                        "excerpt": decision_str[:500],
                    })
                    db.add_cycle_result(db_cycle_id, revision, proposal_str, decision_str, status)
                    logger.info(f"  [!] Auditor: {status}")

                    if status == "APPROVED":
                        base_for_diff = previous_rubric if previous_rubric else current_rubric
                        changed, unchanged = compute_rubric_diff(base_for_diff, candidate_rubric)
                        criteria_changed   = [c["code"] for c in changed]
                        criteria_unchanged = unchanged
                        rubric_change_details = changed
                        save_file(os.path.join(cycle_dir, "rubric_diff.md"),
                                  generate_diff_md(changed, unchanged))
                        logger.info(f"  [Δ] 변경된 기준: {criteria_changed or '없음'}")

                        previous_rubric = current_rubric
                        current_rubric  = candidate_rubric
                        save_file(os.path.join(cycle_dir, "next_rubric.md"), current_rubric)
                        audit_decision = "APPROVED"
                        break

                    time.sleep(2)

                except Exception as e:
                    logger.error(f"Error in revision {revision}: {e}")

            if audit_decision != "APPROVED":
                save_file(os.path.join(cycle_dir, "next_rubric.md"), current_rubric)

            # ⑥ 사이클 지표 저장 ─────────────────────────────────────────────
            metrics = build_cycle_metrics(
                current_idx, rows, students, TEACHERS,
                kappa, kappa_by_criterion, disagree_count,
                audit_decision, criteria_changed, criteria_unchanged,
                gold_std_accuracy=gold_std_accuracy,
            )
            save_file(os.path.join(cycle_dir, "cycle_metrics.json"), metrics)

            # ⑦ 실험 이력 누적 기록 ──────────────────────────────────────────
            disagreed_pairs = extract_disagreed_pairs(rows, students, TEACHERS)
            history_entry = build_history_entry(
                current_idx, kappa, disagree_count,
                disagreed_pairs, audit_decision, rubric_change_details,
            )
            append_history_entry(history_path, history_entry)
            logger.info(f">>> {cycle_name} 완료. Decision={audit_decision}, κ={kappa}")

            current_idx += 1

    except Exception as e:
        logger.critical(f"FATAL: {e}", exc_info=True)
    finally:
        logger.info("RubricCarver 2.0 Engine shut down.")


if __name__ == "__main__":
    run_carver()
