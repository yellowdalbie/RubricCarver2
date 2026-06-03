import os
import json
from engine.agents import GraderAgent, TEACHER_PERSONAS

with open("question.md", "r", encoding="utf-8") as f:
    question = f.read()

with open("rubrics/v00_rubric.md", "r", encoding="utf-8") as f:
    rubric = f.read()

with open("students/student_F1.md", "r", encoding="utf-8") as f:
    answer = f.read()

t_info = TEACHER_PERSONAS["T2"]
grader = GraderAgent(t_info)

# Override generate to print raw text
original_generate = grader.client.generate

def verbose_generate(prompt, system_prompt=None, json_mode=False):
    payload = {
        "model": grader.client.model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_ctx": grader.client.num_ctx},
    }
    if grader.client.think is not None:
        payload["think"] = grader.client.think
    if system_prompt:
        payload["system"] = system_prompt
    if json_mode:
        payload["format"] = "json"
        
    print("Sending request to Ollama...")
    import requests
    response = requests.post(grader.client.base_url, json=payload, timeout=grader.client.timeout)
    response.raise_for_status()
    text = response.json().get('response', '')
    print("=== RAW OLLAMA RESPONSE ===")
    print(text)
    print("===========================")
    return grader.client._parse_json(text, 0)

grader.client.generate = verbose_generate

print(f"Testing T2 grading F1...")
result = grader.grade(question, rubric, answer)
print("Parsed Result:")
print(json.dumps(result, ensure_ascii=False, indent=2))
