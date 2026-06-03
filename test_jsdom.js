const fs = require('fs');
const jsdom = require("jsdom");
const { JSDOM } = jsdom;

const html = fs.readFileSync('analysis/templates/dashboard.html', 'utf8');
const dom = new JSDOM(html, { runScripts: "dangerously" });

setTimeout(() => {
    try {
        const A1_btn = dom.window.document.getElementById('gs-btn-A1');
        const A2_btn = dom.window.document.getElementById('gs-btn-A2');
        console.log("A1 btn:", A1_btn ? A1_btn.className : 'null');
        console.log("A2 btn:", A2_btn ? A2_btn.className : 'null');
        
        dom.window.selectGsStudent('A2');
        
        const A2_panel = dom.window.document.getElementById('gs-panel-A2');
        console.log("A2 panel classes:", A2_panel ? A2_panel.className : 'null');
    } catch(e) {
        console.error("Error in JSDOM:", e);
    }
}, 500);
