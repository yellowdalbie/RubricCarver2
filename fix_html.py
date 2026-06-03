import re
import html

with open('analysis/templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

def unescape_match(m):
    return '<script>' + html.unescape(m.group(1)) + '</script>'

new_content = re.sub(r'<script>(.*?)</script>', unescape_match, content, flags=re.DOTALL)

with open('analysis/templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(new_content)
print("Fixed!")
