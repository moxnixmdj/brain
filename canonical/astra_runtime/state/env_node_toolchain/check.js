const fs = require('fs');
const p = 'out/report.txt';
if (!fs.existsSync(p)) { console.log('FAIL: no report'); process.exit(1); }
const t = fs.readFileSync(p, 'utf8');
if (!/# (pass|fail) \d+/.test(t)) { console.log('FAIL: report shows no tests ran'); process.exit(1); }
if (!/# pass 3/.test(t)) { console.log('FAIL: not all tests passed'); process.exit(1); }
console.log('OK: report shows a real node test run');
