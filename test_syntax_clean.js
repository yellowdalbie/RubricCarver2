const fs = require('fs');
const html = fs.readFileSync('analysis/templates/dashboard.html', 'utf8');

// Extract everything from 'const GS_DATA = {' up to '</script>'
const scriptMatch = html.match(/const GS_DATA = \{[\s\S]*?<\/script>/);
let code = scriptMatch[0].replace('</script>', '');

// Mock DOM
code = `
  const classListMock = {
    add: function(c) {},
    remove: function(c) {}
  };
  const mockNode = {
    classList: classListMock,
    dataset: { id: 'A2' }
  };
  const document = {
    getElementById: (id) => ({ innerHTML: '', classList: classListMock }),
    querySelectorAll: (sel) => [mockNode],
    addEventListener: () => {}
  };
  ${code}
  buildGoldStandard();
  selectGsStudent('A2');
  console.log("Success calling selectGsStudent!");
`;

try {
  eval(code);
} catch (e) {
  console.log("Error:", e);
}
