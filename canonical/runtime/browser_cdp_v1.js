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
  if (a === '--act') {
    // --act <url> <query> <comma,separated,words>
    const [url, q, toks] = [b, process.argv[4], (process.argv[5] || '').split(',').filter(Boolean)];
    console.log(JSON.stringify(await act(url, q, toks), null, 1)); return;
  }
  const br = await connect();
  if (a) await br.goto(a);
  console.log(JSON.stringify(await br.eval(b), null, 1));
  br.ws.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });

// ---------------------------------------------------------------------------
// Acting, not just reading.
//
// The point of this mode is that nobody names a selector. Given a page and
// some words, it decides which control those words refer to, uses it with
// real events, and reports what the page became. Handing it a CSS selector
// would be a human doing the part that matters.
// ---------------------------------------------------------------------------
async function act(url, query, tokens) {
  const b = await connect();
  await b.goto(url);
  const before = { url: await b.eval('location.href'), chars: await b.eval('document.body.innerText.length') };

  // Score every editable control against the words, using the text a person
  // would read: its label, placeholder, name, aria-label, and the form it
  // sits in. The control the words describe is the one to use.
  const pick = await b.eval(`(()=>{
    const toks=${JSON.stringify(tokens)}.map(t=>t.toLowerCase()).filter(t=>t.length>2);
    const vis=e=>{const r=e.getBoundingClientRect();
      return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden';};
    const cands=[...document.querySelectorAll('input,textarea,select')]
      .filter(e=>vis(e)&&!e.disabled&&!['hidden','submit','button','checkbox','radio','file'].includes((e.type||'').toLowerCase()));
    const scored=cands.map(e=>{
      const hay=[e.name,e.id,e.placeholder,e.getAttribute('aria-label'),
        e.getAttribute('title'),e.type,
        (e.labels&&e.labels[0]&&e.labels[0].innerText)||'',
        (e.closest('form')||{}).getAttribute&&e.closest('form')?.getAttribute('aria-label')||'',
        (e.closest('form')||{}).className||'', e.className||'']
        .join(' ').toLowerCase();
      return {sel:e.id?'#'+CSS.escape(e.id):null, idx:[...document.querySelectorAll('input,textarea,select')].indexOf(e),
        score:toks.filter(t=>hay.includes(t)).length, hay:hay.slice(0,80), tag:e.tagName, type:e.type};
    }).sort((x,y)=>y.score-x.score);
    return scored.slice(0,5);
  })()`);

  const best = pick[0];
  if (!best) return { error: 'no editable control on the page', before };
  if (!best.sel) return { error: 'best control has no id', best, before };

  // REFUSE WHEN THERE IS NO EVIDENCE.
  // On github.com's logged-out homepage the only editable fields are email
  // signup boxes. Every candidate scored 0, and the first version typed the
  // query into one of them anyway. Score 0 does not mean "the first one is
  // as good as any" -- it means the words describe nothing on this page, so
  // the honest answer is that there is nothing to act on. Typing into the
  // nearest field is guessing with a keyboard, and it is worse than doing
  // nothing because it looks like success.
  if (!best.score) {
    return { refused: true,
      reason: 'no control on this page matches the words; refusing to type into the nearest field',
      considered: pick, before };
  }

  await b.focus(best.sel);
  await b.send('Input.insertText', { text: query });       // real key events
  const typed = await b.eval(`document.querySelector(${JSON.stringify(best.sel)}).value`);

  // Submit the way a person would: press Enter in the field.
  for (const type of ['keyDown', 'keyUp'])
    await b.send('Input.dispatchKeyEvent',
      { type, key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13, text: type === 'keyDown' ? '\r' : undefined });

  // Wait for the page to actually change rather than assuming it did.
  let changed = false;
  try {
    await b.waitFor(`()=>location.href!==${JSON.stringify(before.url)} || document.body.innerText.length!==${before.chars}`, 15000, 'page to respond');
    changed = true;
  } catch (e) { /* report below; a page that did not change is a real answer */ }
  await b.waitFor(`()=>document.readyState==='complete'`, 15000, 'load');

  const after = {
    url: await b.eval('location.href'),
    title: await b.eval('document.title'),
    chars: await b.eval('document.body.innerText.length'),
    text: (await b.eval('document.body.innerText')).replace(/\s+/g, ' ').trim().slice(0, 3000),
  };
  b.ws.close();
  return { chose: best, considered: pick, typed, changed, before, after };
}
