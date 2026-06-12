import os
import markdown

files = [
    "00_Abstract.md",
    "01_Introduction.md",
    "02_Question_and_Achievement_Design.md",
    "03_Experimental_Setup_and_Agent_Roles.md",
    "04_Student_Answers_and_Reference_Standard.md",
    "05_Experimental_Results_and_Analysis.md",
    "06_Conclusion.md",
    "99_References.md"
]

title = "다중 에이전트 기반 수학 서술형 평가 루브릭 자율 최적화 프레임워크 연구"
author = "김진철 (경상국립대학교 AI융합대학원 석사과정)"

full_text = f"# {title}\n\n**{author}**\n\n---\n\n"

for f in files:
    path = os.path.join("/Users/home/vaults/projects/Rubric/paper/sections", f)
    with open(path, "r", encoding="utf-8") as file:
        full_text += file.read() + "\n\n"

html_content = markdown.markdown(full_text, extensions=['tables', 'fenced_code'])

html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{ font-family: "Malgun Gothic", "Apple SD Gothic Neo", sans-serif; line-height: 1.6; padding: 2em; }}
        h1 {{ text-align: center; }}
        p {{ text-align: justify; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid black; padding: 8px; text-align: left; }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>
"""

with open("/Users/home/vaults/projects/Rubric/paper/full_paper.html", "w", encoding="utf-8") as f:
    f.write(html_template)

print("HTML generated successfully.")
