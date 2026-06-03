import json
import requests
import sys

from engine.agents import GraderAgent, TEACHER_PERSONAS

with open("question.md", "r", encoding="utf-8") as f:
    question = f.read()

with open("rubrics/v00_rubric.md", "r", encoding="utf-8") as f:
    rubric = f.read()

with open("students/student_B2.md", "r", encoding="utf-8") as f:
    answer = f.read()

t_info = TEACHER_PERSONAS["T1"]
grader = GraderAgent(t_info)

res = grader.grade(question, rubric, answer)
print(json.dumps(res, ensure_ascii=False, indent=2))
