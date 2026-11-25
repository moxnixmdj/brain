#!/usr/bin/env node
/* Minimal CDP bridge for the GUI mechanism loop: JSON lines on stdio, Chrome DevTools Protocol.
 *
 * Built-ins only (node >= 22): fetch for HTTP discovery, WebSocket for the
 * debugging socket. No npm dependencies, no payloads from the network at run
 * time. The bridge is dumb plumbing: it opens a tab, navigates, evaluates,
 * and delivers input events. Every decision lives in Python; nothing here
 * sees the goal, the memory store, or the lesson gate.
 *
 * In:  {"id":1,"op":"open","url":"http://..."}      -> {"id":1,"ok":true,...}
 *      {"id":n,"op":"evaluate","expression":"..."}  -> {"id":n,"ok":true,"value":...}
 *      {"id":n,"op":"click","x":100,"y":200}        -> Input.dispatchMouseEvent
 *      {"id":n,"op":"insert_text","text":"abc"}      -> Input.insertText
 *      {"id":n,"op":"press","key":"Enter"}           -> Input.dispatchKeyEvent (Enter only)
 *      {"id":n,"op":"console","clear":true}          -> drains console/exception buffer
 *      {"id":n,"op":"close"}                        -> closes the tab, exits
 *
 * A reply always carries exactly one line. Errors are {"id":n,"ok":false,"error":"..."}.
 */
'use strict';

const DEBUG_URL = process.env.CDP_DEBUG_URL || 'http://127.0.0.1:9222';
const rl = require('node:readline').createInterface({ input: process.stdin });

let ws = null;
let seq = 0;
let consoleLog = [];
const pending = new Map();

function reply(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

function fail(id, error) {
  reply({ id, ok: false, error: String(error).slice(0, 2000) });
}

function cdp(method, params) {
  return new Promise((resolve, reject) => {
    if (!ws) return reject(new Error('NO_SOCKET'));
    const id = ++seq;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params: params || {} }));
  });
}

async function ensurePage(url) {
  const version = await fetch(DEBUG_URL + '/json/version').then(r => r.json());
  let wsBrowser = new WebSocket(version.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    wsBrowser.addEventListener('open', resolve, { once: true });
    wsBrowser.addEventListener('error', () => reject(new Error('BROWSER_WS_OPEN_FAILED')), { once: true });
  });
  const browserCdp = (method, params) => new Promise((resolve, reject) => {
    const id = ++seq;
    const onMessage = event => {
      const msg = JSON.parse(event.data);
      if (msg.id === id) {
        wsBrowser.removeEventListener('message', onMessage);
        if (msg.error) reject(new Error(msg.error.message));
        else resolve(msg.result || {});
      }
    };
    wsBrowser.addEventListener('message', onMessage);
    wsBrowser.send(JSON.stringify({ id, method, params: params || {} }));
  });
  let list = await fetch(DEBUG_URL + '/json/list').then(r => r.json());
  let page = list.find(t => t.type === 'page');
  if (!page) {
    await browserCdp('Target.createTarget', { url: 'about:blank' });
    list = await fetch(DEBUG_URL + '/json/list').then(r => r.json());
    page = list.find(t => t.type === 'page');
  }
  wsBrowser.close();
  if (!page) throw new Error('NO_PAGE_TARGET');
  ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener('open', resolve, { once: true });
    ws.addEventListener('error', () => reject(new Error('WS_OPEN_FAILED')), { once: true });
  });
  ws.addEventListener('message', event => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(msg.error.message || JSON.stringify(msg.error)));
      else resolve(msg.result || {});
      return;
    }
    if (msg.method === 'Runtime.exceptionThrown') {
      const d = (msg.params && msg.params.exceptionDetails) || {};
      consoleLog.push('EXCEPTION: ' + String((d.exception && d.exception.description) || d.text || 'unknown').slice(0, 500));
    } else if (msg.method === 'Runtime.consoleAPICalled') {
      const args = (msg.params && msg.params.args) || [];
      consoleLog.push('CONSOLE.' + (msg.params.type || 'log').toUpperCase() + ': ' +
        args.map(a => String(a.value !== undefined ? a.value : (a.description || ''))).join(' ').slice(0, 500));
    } else if (msg.method === 'Log.entryAdded') {
      const e = (msg.params && msg.params.entry) || {};
      if (e.level === 'error') consoleLog.push('LOG.ERROR: ' + String(e.text || '').slice(0, 500));
    }
  });
  await cdp('Runtime.enable');
  await cdp('Log.enable');
  await cdp('Page.enable');
  if (url) {
    await cdp('Page.navigate', { url });
    await new Promise(r => setTimeout(r, 1200)); // the page boots itself; no event wait needed here
  }
}

async function evaluate(expression) {
  const result = await cdp('Runtime.evaluate', {
    expression,
    returnByValue: true,
    awaitPromise: true,
    userGesture: true,
  });
  if (result.exceptionDetails) {
    const d = result.exceptionDetails;
    const desc = (d.exception && d.exception.description) || d.text || 'EXCEPTION';
    throw new Error('EVAL_EXCEPTION: ' + String(desc).slice(0, 1000));
  }
  return (result.result || {}).value;
}

async function click(x, y) {
  for (const type of ['mousePressed', 'mouseReleased']) {
    await cdp('Input.dispatchMouseEvent', {
      type, x: Math.round(x), y: Math.round(y), button: 'left',
      clickCount: 1, pointerType: 'mouse',
    });
  }
}

async function pressEnter() {
  // "rawKeyDown" never generates a keypress; this app binds 'keypress #new-todo'.
  // "keyDown" with text '\r' makes Chrome emit keypress with which=13, like a real Enter.
  await cdp('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', text: '\r', windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13 });
  await cdp('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13, nativeVirtualKeyCode: 13 });
}

let chain = Promise.resolve();

rl.on('line', line => {
  chain = chain.then(async () => {
  let msg;
  try { msg = JSON.parse(line); } catch { return; }
  const id = msg.id;
  try {
    switch (msg.op) {
      case 'open':
        await ensurePage(msg.url);
        reply({ id, ok: true });
        break;
      case 'evaluate':
        reply({ id, ok: true, value: await evaluate(msg.expression) });
        break;
      case 'click':
        await click(msg.x, msg.y);
        reply({ id, ok: true });
        break;
      case 'insert_text':
        await cdp('Input.insertText', { text: String(msg.text) });
        reply({ id, ok: true });
        break;
      case 'press':
        if (msg.key !== 'Enter') throw new Error('PRESS_ONLY_ENTER_SUPPORTED');
        await pressEnter();
        reply({ id, ok: true });
        break;
      case 'console':
        reply({ id, ok: true, log: consoleLog.slice(), });
        if (msg.clear) consoleLog = [];
        break;
      case 'close':
        try { await cdp('Page.close'); } catch { /* target may vanish first */ }
        reply({ id, ok: true });
        ws = null;
        process.exit(0);
      default:
        fail(id, 'UNKNOWN_OP: ' + String(msg.op));
    }
  } catch (error) {
    fail(id, (error && error.message) || error);
  }
  });
});

rl.on('close', () => {
  // not yet: async ops issued so far must finish first (this is why replies were lost)
  chain.then(() => process.exit(0));
});
