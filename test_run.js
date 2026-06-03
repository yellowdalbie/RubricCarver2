const fs = require('fs');
const html = fs.readFileSync('analysis/templates/dashboard.html', 'utf8');
const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);
const scriptContent = scriptMatch[1];

const domMock = `
const window = { addEventListener: () => {} };
const classListMock = { add: () => {}, remove: () => {}, contains: () => false };
const elementMock = { innerHTML: '', textContent: '', appendChild: () => {}, classList: classListMock, style: {}, getContext: () => ({}) };
const document = {
  addEventListener: () => {},
  getElementById: (id) => elementMock,
  querySelectorAll: (sel) => [elementMock, elementMock],
  createElement: (tag) => elementMock
};
const Chart = class { constructor() {} destroy() {} };
`;

const fetchAndRun = `
const http = require('http');
http.get('http://127.0.0.1:5555/api/data', (res) => {
    let body = '';
    res.on('data', chunk => body += chunk);
    res.on('end', () => {
        global.DATA = JSON.parse(body);
        const fetch = async () => ({ json: async () => global.DATA });
        eval(\`\${scriptContent}; fetchData().then(() => console.log("SUCCESS!")).catch(e => console.error("CAUGHT:", e));\`);
    });
});
`;
fs.writeFileSync('test_exec.js', domMock + fetchAndRun);
