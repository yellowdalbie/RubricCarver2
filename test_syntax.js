const fs = require('fs');
const html = fs.readFileSync('analysis/templates/dashboard.html', 'utf8');

// Extract everything from 'const GS_DATA = {' up to 'function buildGoldStandard() {'
const scriptMatch = html.match(/const GS_DATA = \{[\s\S]*?function selectGsStudent\(id\) \{/);
if (!scriptMatch) {
  console.log("Could not find script block");
  process.exit(1);
}

let code = scriptMatch[0] + "\n}";
// Add dummy DOM elements
code = `
  const document = {
    getElementById: (id) => ({ innerHTML: '' })
  };
  ${code}
  buildGoldStandard();
  console.log("Success!");
`;

try {
  eval(code);
} catch (e) {
  console.log("Error:", e);
}
