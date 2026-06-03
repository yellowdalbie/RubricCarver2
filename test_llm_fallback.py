import re
import json

def _parse_json(text):
    # Attempt normal regex extraction first
    clean = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    
    for candidate in (clean, text):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', candidate, re.DOTALL)
        if json_match:
            try: return json.loads(json_match.group(1))
            except: pass

        brace_match = re.search(r'(\{.*\})', candidate, re.DOTALL)
        if brace_match:
            try: return json.loads(brace_match.group(1))
            except: pass

    # LLM-based fallback
    print("Normal parsing failed. Attempting LLM extraction...")
    # This simulates passing the text to an LLM
    return None

raw_markdown = """### 채점 결과
#### **(1) 위치 계산 (요소 1)**
- **C1-1**: 정적분 식 $\int_0^2 (t^2 - 5t + 4)\,dt$을 명시하지 않음 → **NO**  
- **C1-2**: 위치가 속도의 정적분(변위)임을 설명하지 않음 → **NO**  

### **최종 채점**
- **결론**: 정답 값만 기재한 **권위 호소**(F1)로, **모든 기준 자동 0점** 처리
"""
print(_parse_json(raw_markdown))
