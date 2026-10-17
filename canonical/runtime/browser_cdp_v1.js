const WebSocket = require('ws');
// Minimal CDP driver: connect, navigate, evaluate. This is what Puppeteer
// does underneath -- the CLI hangs on compositing, the protocol does not.
async function main() {
  const url = process.argv[2], expr = process.argv[3];
  const list = await (await fetch('http://127.0.0.1:9222/json/list')).json();
  const page = list.find(t => t.type === 'page');
  const ws = new WebSocket(page.webSocketDebuggerUrl, { perMessageDeflate: false });
  let id = 0; const pending = new Map();
  const send = (method, params = {}) => new Promise(res => {
    const i = ++id; pending.set(i, res);
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  ws.on('message', m => {
    const msg = JSON.parse(m);
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
  });
  await new Promise(r => ws.on('open', r));
  await send('Page.enable'); await send('Runtime.enable');
  await send('Page.navigate', { url });
  await new Promise(r => setTimeout(r, 1500));
  const r = await send('Runtime.evaluate', {
    expression: expr, returnByValue: true, awaitPromise: true });
  console.log(JSON.stringify(r.result && r.result.result
    ? r.result.result.value : r.result, null, 1));
  ws.close();
}
main().catch(e => { console.error('ERR', e.message); process.exit(1); });
