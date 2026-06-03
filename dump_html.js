const fs = require('fs');
const html = fs.readFileSync('analysis/templates/dashboard.html', 'utf8');

const scriptMatch = html.match(/const GS_DATA = \{[\s\S]*?function selectGsStudent\(id\) \{/);
let code = scriptMatch[0] + "\n}";
code = `
  const document = {
    getElementById: (id) => ({ innerHTML: '' })
  };
  let panelsHTML = '';
  const panels = {
    set innerHTML(val) { panelsHTML = val; }
  };
  const nav = { innerHTML: '' };
  
  // mock document.getElementById to return nav and panels
  document.getElementById = (id) => {
    if (id === 'gs-nav') return nav;
    if (id === 'gs-panels') return panels;
    return {};
  };

  ${code}
  buildGoldStandard();
  fs.writeFileSync('panels.html', panelsHTML);
`;
eval(code);
