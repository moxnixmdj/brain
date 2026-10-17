#!/usr/bin/env node
// Real browser interaction over the Chrome DevTools Protocol.
//
// The --dump-dom / --screenshot command-line paths hang in containers
// without working graphics: the GPU process never initialises, so
// compositing never completes. The DevTools endpoint starts regardless,
// and CDP is what Puppeteer and Playwright drive underneath. So this
// drives the protocol directly.
//
// Usage:
//   node browser_cdp_v1.js <url> <expr>              evaluate JavaScript
//   node browser_cdp_v1.js --demo <url>              run the interaction probe
const WebSocket = require('ws');
const PORT = process.env.BROWSER_PORT || '9222';

class Browser {
  constructor(ws) {
    this.ws = ws; this.id = 0; this.pending = new Map();
    ws.on('message', m => {
      const msg = JSON.parse(m);
      if (msg.id && this.pending.has(msg.id)) {
        this.pending.get(msg.id)(msg); this.pending.delete(msg.id);
      }
    });
  }
  send(method, params = {}) {
    return new Promise(res => {
      const i = ++this.id;
      this.pending.set(i, res);
      this.ws.send(JSON.stringify({ id: i, method, params }));
    });
  }
  async eval(expr) {
    const r = await this.send('Runtime.evaluate', {
      expression: expr, returnByValue: true, awaitPromise: true });
    if (r.result && r.result.exceptionDetails)
      throw new Error('page error: ' +
        (r.result.exceptionDetails.exception?.description || 'unknown'));
    return r.result?.result?.value;
  }
  async goto(url) {
    await this.send('Page.navigate', { url });
    await this.waitFor(() => document.readyState === 'complete', 15000);
  }
  // Poll rather than sleep: returns as soon as the condition is true.
  async waitFor(fnBody, timeout = 10000, label = 'condition') {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) {
      if (await this.eval(`(()=>{return (${fnBody})()})()`)) return true;
      await new Promise(r => setTimeout(r, 100));
    }
    throw new Error(`timed out waiting for ${label}`);
  }
  box(sel) {
    return this.eval(`(()=>{const e=document.querySelector(${JSON.stringify(sel)});
      if(!e)return null;const r=e.getBoundingClientRect();
      return {x:r.x+r.width/2,y:r.y+r.height/2};})()`);
  }
  async click(sel) {
    const b = await this.box(sel);
    if (!b) throw new Error(`no element for ${sel}`);
    await this.send('Input.dispatchMouseEvent',
      { type: 'mouseMoved', x: b.x, y: b.y, button: 'none' });
    for (const type of ['mousePressed', 'mouseReleased'])
      await this.send('Input.dispatchMouseEvent',
        { type, x: b.x, y: b.y, button: 'left', clickCount: 1 });
  }
  async focus(sel) { await this.eval(`document.querySelector(${JSON.stringify(sel)}).focus()`); }
  // Real key events: fires the same handlers a human typing would.
  async type(sel, text) {
    await this.focus(sel);
    await this.send('Input.insertText', { text });
  }
  text(sel) {
    return this.eval(`document.querySelector(${JSON.stringify(sel)})?.textContent`);
  }
  // Screenshots work over CDP even though the --screenshot CLI hangs:
  // same compositing problem, different route past it. fromSurface:false
  // captures from the renderer rather than waiting on a compositor frame.
  async viewport(w, h) {
    await this.send('Emulation.setDeviceMetricsOverride',
      { width: w, height: h, deviceScaleFactor: 1, mobile: false });
  }
  async screenshot(path) {
    const r = await this.send('Page.captureScreenshot',
      { format: 'png', fromSurface: false });
    if (!r.result?.data) throw new Error('screenshot returned no data');
    const buf = Buffer.from(r.result.data, 'base64');
    if (path) require('fs').writeFileSync(path, buf);
    return { bytes: buf.length, path };
  }
}

async function connect() {
  const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
  const page = list.find(t => t.type === 'page');
  if (!page) throw new Error('no page target');
  const ws = new WebSocket(page.webSocketDebuggerUrl, { perMessageDeflate: false });
  await new Promise((res, rej) => { ws.on('open', res); ws.on('error', rej); });
  const b = new Browser(ws);
  await b.send('Page.enable'); await b.send('Runtime.enable');
  return b;
}

async function demo(url) {
  const b = await connect();
  const out = {};
  await b.goto(url);
  out.loaded = await b.text('#h');

  // 1. a click that only a real mouse event can produce
  out.counter_before = await b.text('#n');
  await b.click('#btn'); await b.click('#btn'); await b.click('#btn');
  out.counter_after_3_clicks = await b.text('#n');

  // 2. typing that fires oninput live, key by key
  await b.type('#txt', 'brain');
  out.reversed_live = await b.text('#rev');

  // 3. a real form submit, default prevented by the page's own handler
  await b.click('#f button[type=submit]');
  out.after_submit = await b.text('#done');

  // 4. a screenshot, so the system can see the page and not just read it
  await b.viewport(800, 600);
  out.screenshot = await b.screenshot('/tmp/brain_screenshot.png');

  // 5. content that only exists after an async timer -- the SPA case
  out.late_immediately = await b.text('#late');
  await b.waitFor(`()=>document.querySelector('#late')?.textContent!=='NOT_YET'`,
    5000, 'async content');
  out.late_after_wait = await b.text('#late');

  console.log(JSON.stringify(out, null, 1));
  b.ws.close();
}

(async () => {
  const [a, b] = process.argv.slice(2);
  if (a === '--demo') return demo(b);
  const br = await connect();
  if (a) await br.goto(a);
  console.log(JSON.stringify(await br.eval(b), null, 1));
  br.ws.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
