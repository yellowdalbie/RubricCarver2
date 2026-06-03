with open('analysis/templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('&lt;title>', '<title>')
with open('analysis/templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
