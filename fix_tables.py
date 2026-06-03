import re

with open('analysis/templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# targeted replacements for table tags
tags = ['table', 'thead', 'tbody', 'tr', 'td', 'th', '/table', '/thead', '/tbody', '/tr', '/td', '/th']

for tag in tags:
    content = content.replace(f'&lt;{tag}', f'<{tag}')

with open('analysis/templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed tables!")
