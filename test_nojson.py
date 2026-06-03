import json
import requests
import sys

from engine.agents import GraderAgent, TEACHER_PERSONAS

with open("question.md", "r", encoding="utf-8") as f:
    question = f.read()

with open("rubrics/v00_rubric.md", "r", encoding="utf-8") as f:
    rubric = f.read()

with open("students/student_F1.md", "r", encoding="utf-8") as f:
    answer = f.read()

t_info = TEACHER_PERSONAS["T2"]
grader = GraderAgent(t_info)

checklist_template = ",\n    ".join(f'"{code}": {{"answer": "YES 또는 NO", "basis": "답안 인용 또는 이유"}}' for code in ["C1-1", "C1-2", "C2-1", "C2-2", "C2-3", "C3-1", "C3-2", "C3-3", "C3-4", "C3-5"])
cascade_section = f"\n★ 연계 판단 규칙\n{grader.cascade_rule}\n"
system_prompt = f"""당신은 수학 교사 '{grader.name}'입니다.
평가 철학: {grader.philosophy}

[채점 절차]
(생략: 동일한 프롬프트)
"""
prompt = f"""### 문항
{question}
### 루브릭 (이진 채점 기준)
{rubric}
### 채점 대상 답안
<student_answer>
{answer}
</student_answer>"""

payload = {
    "model": "qwen3:8b",
    "prompt": prompt,
    "system": system_prompt,
    "stream": True,
    "options": {"temperature": 0.2}
}

print("Streaming response (NO JSON FORMAT):")
response = requests.post("http://localhost:11434/api/generate", json=payload, stream=True)
count = 0
for line in response.iter_lines():
    if line:
        data = json.loads(line)
        sys.stdout.write(data.get("response", ""))
        sys.stdout.flush()
print("\nDone.")
