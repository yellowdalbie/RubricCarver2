import os

section_files = [
    "00_Abstract.md",
    "01_Introduction.md",
    "02_Question_and_Achievement_Design.md",
    "03_Experimental_Setup_and_Agent_Roles.md",
    "04_Student_Answers_and_Reference_Standard.md",
    "05_Experimental_Results_and_Analysis.md",
    "06_Conclusion.md",
    "07_Data_Availability.md",
    "99_References.md"
]

appendix_files = [
    "Appendix_A_Grader_Prompt.md",
    "Appendix_B_Analyst_Prompt.md",
    "Appendix_C_Auditor_Prompt.md",
    "Appendix_C2_Auditor_Evaluation_Guide.md",
    "Appendix_D_Synthetic_Student_Answers.md",
    "Appendix_E_Experiment_Metrics_Summary.md",
]

title = "채점 기계에서 벗어나기: 수학적 사고의 이분법적 모호성을 수용하는 다중 에이전트 평가 프레임워크"
author = "김진철 (경상국립대학교 AI융합대학원 석사과정)"

sections_dir = "/Users/home/vaults/projects/Rubric/paper/sections"
appendix_dir = "/Users/home/vaults/projects/Rubric/paper/appendix"

full_text = f"---\ntitle: \"{title}\"\nauthor: {author}\n---\n\n"

for f in section_files:
    path = os.path.join(sections_dir, f)
    with open(path, "r", encoding="utf-8") as file:
        full_text += file.read() + "\n\n"

full_text += "---\n\n# 부록 (Appendix)\n\n"

for f in appendix_files:
    path = os.path.join(appendix_dir, f)
    with open(path, "r", encoding="utf-8") as file:
        full_text += file.read() + "\n\n---\n\n"

with open("/Users/home/vaults/projects/Rubric/paper/full_paper.md", "w", encoding="utf-8") as f:
    f.write(full_text)

print("Unified markdown generated successfully (with appendices).")
