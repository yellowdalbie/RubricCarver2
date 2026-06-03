import re
import json

def fallback_regex_parse(text):
    result = {
        "pre_check": {"answer": "NO", "basis": "Pre-check or PG-1 not explicitly matched"},
        "checklist": {},
        "level": "E",
        "comment": "정규식(Regex) Fallback에 의해 텍스트에서 추출됨"
    }

    # Pre-check 추출
    pre_match = re.search(r'(?:PG-1|Pre-check).*?(YES|NO)', text, re.IGNORECASE)
    if pre_match:
        result["pre_check"]["answer"] = pre_match.group(1).upper()

    # C1-1 ~ C3-5 추출
    criteria = ["C1-1", "C1-2", "C2-1", "C2-2", "C2-3", "C3-1", "C3-2", "C3-3", "C3-4", "C3-5"]
    for c in criteria:
        chunk_match = re.search(rf'{c}(.*?)(?=C[1-3]-[1-5]|\"level\"|$)', text, re.IGNORECASE | re.DOTALL)
        if chunk_match:
            chunk = chunk_match.group(1)
            ans_match = re.search(r'\b(YES|NO)\b', chunk, re.IGNORECASE)
            ans = ans_match.group(1).upper() if ans_match else "NO"
            
            # basis 추출
            basis_match = re.search(r'\"basis\"\s*:\s*\"(.*?)\"', chunk, re.IGNORECASE | re.DOTALL)
            if basis_match:
                basis = basis_match.group(1)
            else:
                basis = re.sub(r'\b(YES|NO)\b', '', chunk, flags=re.IGNORECASE)
                basis = basis.replace('*', '').replace('#', '').strip(' -:→>|\\n{}"\',')
            result["checklist"][c] = {"answer": ans, "basis": basis.strip()}
        else:
            result["checklist"][c] = {"answer": "NO", "basis": "기준 언급 없음"}

    # Level 추출 (A-E)
    level_match = re.search(r'(?:level|성취수준|최종 판정).*?\b([A-E])\b', text, re.IGNORECASE)
    if level_match:
        result["level"] = level_match.group(1).upper()
    else:
        all_no = all(v["answer"] == "NO" for v in result["checklist"].values())
        result["level"] = "E" if all_no else "?"

    return result

json_broken = """{
  "pre_check": {"answer": "YES", "basis": "ok"},
  "checklist": {
    "C1-1": {"answer": "YES", "basis": "답안에 "수식"이 포함됨"},
    "C1-2": {"answer": "NO", "basis": "설명 부족"}
  },
  "level": "A"
}"""

md_text = """### 채점 결과
- **C1-1**: 명시하지 않음 → **NO**  
- **C1-2**: 설명함 → **YES**  
"""

print("--- JSON BROKEN ---")
print(json.dumps(fallback_regex_parse(json_broken), ensure_ascii=False, indent=2))
print("--- MD TEXT ---")
print(json.dumps(fallback_regex_parse(md_text), ensure_ascii=False, indent=2))

