import re
import json

text = """{
  "pre_check": {"answer": "YES", "basis": "ok"},
  "checklist": {
    "C1-1": {"answer": "YES", "basis": "good"}
  },
  "level": "A",
  "comment": "Nice"
}"""

c = "C1-1"
line_match = re.search(rf'^.*{c}.*$', text, re.MULTILINE)
if line_match:
    line = line_match.group(0)
    ans_match = re.search(r'\b(YES|NO)\b', line, re.IGNORECASE)
    ans = ans_match.group(1).upper() if ans_match else "NO"
    basis = re.sub(r'\b(YES|NO)\b', '', line, flags=re.IGNORECASE)
    basis = basis.replace(c, '').replace('*', '').replace('#', '').strip(' -:→>|\\n')
    print("basis:", basis)
