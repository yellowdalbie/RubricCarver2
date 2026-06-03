
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

const http = require('http');
http.get('http://127.0.0.1:5555/api/data', (res) => {
    let body = '';
    res.on('data', chunk => body += chunk);
    res.on('end', () => {
        global.DATA = JSON.parse(body);
        const fetch = async () => ({ json: async () => global.DATA });
        eval(`${scriptContent}; fetchData().then(() => console.log("SUCCESS!")).catch(e => console.error("CAUGHT:", e));`);
    });
});
