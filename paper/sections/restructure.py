import re

# 1. Read Chapter 4 and extract the section
with open("/Users/home/vaults/projects/Rubric/paper/sections/04_Student_Answers_and_Reference_Standard.md", "r", encoding="utf-8") as f:
    c4_lines = f.readlines()

# Extract lines 34 to 55 (0-indexed)
extracted_section = c4_lines[34:56]
# Delete them from Chapter 4
del c4_lines[34:56]

# In Chapter 4, change `## 4. 참조 표준...` to `## 3. 참조 표준...`
for i, line in enumerate(c4_lines):
    if line.startswith("## 4. 참조 표준 확립의 정당성"):
        c4_lines[i] = line.replace("## 4. ", "## 3. ")
        break

# Write Chapter 4
with open("/Users/home/vaults/projects/Rubric/paper/sections/04_Student_Answers_and_Reference_Standard.md", "w", encoding="utf-8") as f:
    f.writelines(c4_lines)


# 2. Append to Chapter 2
with open("/Users/home/vaults/projects/Rubric/paper/sections/02_Question_and_Achievement_Design.md", "r", encoding="utf-8") as f:
    c2_content = f.read()

# Fix numbering in the extracted section
extracted_text = "".join(extracted_section)
extracted_text = extracted_text.replace("## 3. 초기 루브릭", "## 4. 초기 루브릭")
extracted_text = extracted_text.replace("<표 3>", "<표 2>")
# Add a transition
extracted_text = extracted_text.replace("학생들의 가상 답안을 평가하고 참조 표준을 확립하기 위한 첫 단계로서, 연구진은 문항 설계 의도를 반영한", "학생들의 가상 답안을 평가하고 참조 표준을 확립하기 위한 첫 단계로서, 연구진은 앞서 도출된 성취수준 진술문과 문항 설계 의도를 결합하여")

c2_content += "\n" + extracted_text

with open("/Users/home/vaults/projects/Rubric/paper/sections/02_Question_and_Achievement_Design.md", "w", encoding="utf-8") as f:
    f.write(c2_content)


# 3. Update Chapter 3
with open("/Users/home/vaults/projects/Rubric/paper/sections/03_Experimental_Setup_and_Agent_Roles.md", "r", encoding="utf-8") as f:
    c3_content = f.read()

# Fix the introduction sentence
c3_content = c3_content.replace(
    "초기 루브릭(성취수준 진술문)이 확정된 후, 본 연구는 이를 인간의 개입 없이 자동으로 정교화하기 위한", 
    "앞서 2장에서 완성된 초기 루브릭(v00)을 인간의 개입 없이 자동으로 정교화하기 위해, 본 연구는 "
)

# Fix Table number
c3_content = c3_content.replace("<표 2>", "<표 3>")

with open("/Users/home/vaults/projects/Rubric/paper/sections/03_Experimental_Setup_and_Agent_Roles.md", "w", encoding="utf-8") as f:
    f.write(c3_content)

print("Restructuring Complete")
