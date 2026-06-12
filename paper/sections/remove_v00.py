import glob
import os

files = glob.glob("/Users/home/vaults/projects/Rubric/paper/sections/*.md")
for filepath in files:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "(v00)" in content:
        new_content = content.replace("(v00)", "")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Removed from {os.path.basename(filepath)}")

print("Done")
