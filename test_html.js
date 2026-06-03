const fs = require('fs');
const html = fs.readFileSync('analysis/templates/dashboard.html', 'utf8');

// Extract the script
const scriptMatch = html.match(/const GS_DATA = \{[\s\S]*?<\/script>/);
let code = scriptMatch[0].replace('</script>', '');

// Create a real JSDOM to test if innerHTML drops anything
const jsdom = require('jsdom');
const { JSDOM } = jsdom;
const dom = new JSDOM(`<html><body>
  <div id="gs-nav"></div>
  <div id="gs-panels"></div>
</body></html>`, { runScripts: "dangerously" });

// execute code
dom.window.eval(code);
dom.window.eval('buildGoldStandard();');

console.log("Number of nav buttons:", dom.window.document.querySelectorAll('.gs-btn').length);
console.log("Number of panels:", dom.window.document.querySelectorAll('.gs-panel').length);
