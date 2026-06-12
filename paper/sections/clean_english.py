import re
import glob
import os

replacements = {
    r"노이즈\(Noise\)": "노이즈",
    r"경계 케이스\(Edge Cases\)": "경계 케이스",
    r"표상\(Representation\)": "표상",
    r"스트레스 테스트\s*\(Stress Test\)": "스트레스 테스트",
    r"단위 테스트\(Unit Test\)": "단위 테스트",
    r"레드티밍\(Red-teaming\)": "레드티밍",
    r"참조 표준\(Ground Truth\)": "참조 표준",
    r"결정론적\(Deterministic\)": "결정론적",
    r"참조 표준\s*\(Reference Standard\)": "참조 표준",
    r"사전 등록\(Pre-registration\)": "사전 등록",
    r"미도달\(I, Incomplete\)": "미도달(I)",
    r"프롬프트 인젝션\(Prompt Injection\)": "프롬프트 인젝션",
    r"자가 발전\(Self-correction\)": "자가 발전",
    r"정답\(Ground Truth\)": "정답",
    r"오차율\(Error Rate\)": "오차율",
    r"이견\(Healthy Disagreement\)": "이견",
    r"천장 효과\(Ceiling Effect\)": "천장 효과",
    r"거짓 합의\(False Consensus\)": "거짓 합의",
    r"존재 증명\(Existence Proof\)": "존재 증명",
    r"취약성\(Vulnerability\)": "취약성",
    r"강건성\(Robustness\)": "강건성",
    r"공격 벡터\(Attack Vectors\)": "공격 벡터",
    r"경계 케이스\(Boundary Cases\)": "경계 케이스",
    r"보조 교사\(AI Tutor\)": "보조 교사",
    r"채점 기계\(Scoring Machine\)": "채점 기계",
    r"운전대\(Steering wheel\)": "운전대",
    r"추론 전문 모델\(Reasoning-focused Models\)": "추론 전문 모델",
    r"수 감각\(Number Sense\)": "수 감각",
    r"복원할 수 있는지\(Resilience\)": "복원할 수 있는지"
}

files = glob.glob("/Users/home/vaults/projects/Rubric/paper/sections/*.md")
for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    for pattern, repl in replacements.items():
        content = re.sub(pattern, repl, content)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {os.path.basename(filepath)}")

