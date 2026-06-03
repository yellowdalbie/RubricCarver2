const fs = require('fs');
const jsdom = require('jsdom');
const { JSDOM } = jsdom;

const html = fs.readFileSync('analysis/templates/dashboard.html', 'utf8');
const dom = new JSDOM(html, { runScripts: "dangerously" });

setTimeout(() => {
  console.log("Nav buttons count:", dom.window.document.querySelectorAll('.gs-btn').length);
  console.log("Panels count:", dom.window.document.querySelectorAll('.gs-panel').length);
  
  const a2Btn = dom.window.document.querySelector('.gs-btn[data-id="A2"]');
  if (a2Btn) {
    console.log("Clicking A2...");
    a2Btn.click();
    
    const a2Panel = dom.window.document.getElementById('gs-panel-A2');
    console.log("A2 panel classes after click:", a2Panel.className);
  } else {
    console.log("A2 button not found!");
  }
}, 1000);
