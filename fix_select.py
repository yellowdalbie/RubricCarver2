with open('analysis/templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('function selectGsStudent(id) {', 'window.selectGsStudent = function(id) {')

with open('analysis/templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
