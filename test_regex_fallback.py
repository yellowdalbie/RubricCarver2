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
    pre_match = re.search(r'(?:PG-1|Pre-check|사전 검사).*?(YES|NO)', text, re.IGNORECASE)
    if pre_match:
        result["pre_check"]["answer"] = pre_match.group(1).upper()

    # C1-1 ~ C3-5 추출
    criteria = ["C1-1", "C1-2", "C2-1", "C2-2", "C2-3", "C3-1", "C3-2", "C3-3", "C3-4", "C3-5"]
    for c in criteria:
        line_match = re.search(rf'^.*{c}.*$', text, re.MULTILINE)
        if line_match:
            line = line_match.group(0)
            ans_match = re.search(r'\b(YES|NO)\b', line, re.IGNORECASE)
            ans = ans_match.group(1).upper() if ans_match else "NO"
            # Cleanup basis
            basis = re.sub(r'\b(YES|NO)\b', '', line, flags=re.IGNORECASE)
            basis = basis.replace(c, '').replace('*', '').replace('#', '').strip(' -:→>|\\n')
            result["checklist"][c] = {"answer": ans, "basis": basis.strip()}
        else:
            result["checklist"][c] = {"answer": "NO", "basis": "기준 언급 없음"}

    # Level 추출 (A-E)
    level_match = re.search(r'(?:level|성취수준|최종 판정).*?\b([A-E])\b', text, re.IGNORECASE)
    if level_match:
        result["level"] = level_match.group(1).upper()
    else:
        # If all NO -> E, else ?
        all_no = all(v["answer"] == "NO" for v in result["checklist"].values())
        result["level"] = "E" if all_no else "?"

    return result

markdown_text = """### 채점 결과
#### **(1) 위치 계산 (요소 1)**
- **C1-1**: 정적분 식 $\int_0^2 (t^2 - 5t + 4)\,dt$을 명시하지 않음 → **NO**  
- **C1-2**: 위치가 속도의 정적분(변위)임을 설명하지 않음 → **NO**  

### **최종 채점**
- **결론**: 정답 값만 기재한 **권위 호소**(F1)로, **모든 기준 자동 0점** 처리
"""

print(json.dumps(fallback_regex_parse(markdown_text), ensure_ascii=False, indent=2))
