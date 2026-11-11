// MiniWoB++ task pages in a headless DOM, one JSON command per line on stdin, one JSON reply per line on stdout.
//
// What this is: the public MiniWoB++ task pages (Farama-Foundation/miniwob-plusplus, MIT, pages nobody in this
// repository wrote) loaded with jsdom, acted on at ELEMENT level, with the page's own reward read back.
//
// What this is not: a browser. jsdom has no layout engine and no renderer, so there are no coordinates, sizes,
// colours or pixels (a displayed element reports a nominal 1x1 box so that visibility queries answer as they would
// in a browser; nothing else about geometry is real). A task that needs geometry (drag, draw, slide, scroll, shapes by position) cannot be done
// faithfully here and is expected to fail; the caller counts those, it does not hide them.
//
// Two properties the measurement depends on, both enforced here rather than hoped for:
//   * time is virtual. setTimeout / setInterval / requestAnimationFrame / Date belong to a fake clock that only
//     moves when a command moves it, so the same (task, seed, actions) gives the same episode on any machine;
//   * the agent has one channel. It can click an element or type into one. It cannot read page globals, run
//     script, or see anything except the visible elements and the instruction text.
//
// usage: node miniwob_jsdom_bridge_v1.js <path to miniwob/html> [<directory containing node_modules>]
'use strict';
const path = require('path');
const fs = require('fs');
const readline = require('readline');

const htmlDir = process.argv[2];
const modulesDir = process.argv[3] || process.env.MINIWOB_BRIDGE_NODE_MODULES || '';
function need(name) {
  if (modulesDir) return require(require.resolve(name, { paths: [modulesDir] }));
  return require(name);
}
function versionOf(name) {
  try {
    const entry = modulesDir ? require.resolve(name + '/package.json', { paths: [modulesDir] }) : require.resolve(name + '/package.json');
    return JSON.parse(fs.readFileSync(entry, 'utf8')).version;
  } catch (e) { return null; }
}
const { JSDOM, VirtualConsole } = need('jsdom');
const FakeTimers = need('@sinonjs/fake-timers');

const STEP_MS = 500;               // virtual time that passes after a reset and after every action
const EPOCH_MS = 1767225600000;    // 2026-01-01T00:00:00Z: every page load starts its clock here
const SKIP_IDS = new Set(['query', 'reward-display', 'sync-task-cover', 'click-canvas']);
const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'LINK', 'META', 'HEAD', 'TITLE', 'BR', 'NOSCRIPT', 'TEMPLATE']);
const NATIVE_CLICK = new Set(['BUTTON', 'INPUT', 'A', 'OPTION', 'LABEL', 'TEXTAREA', 'SUMMARY', 'AREA']);
const TEXT_INPUT_TYPES = new Set(['text', 'password', 'email', 'number', 'search', 'tel', 'url', 'date', 'time', 'datetime-local', 'month', 'week', '']);
const ATTRS = ['type', 'name', 'for', 'placeholder', 'title', 'alt', 'href', 'role', 'aria-label', 'data-value', 'data-index'];

let dom = null, clock = null, errors = [], current = [], pageTimeLimit = null;

function squash(s) { return String(s || '').replace(/\s+/g, ' ').trim(); }

// ---- display / visibility of one element, without paying for a full computed style ----------------------------
// jsdom's getComputedStyle matches the element against EVERY rule of every stylesheet; with jQuery UI's sheet
// loaded that is about a millisecond per element, and it is what an observation costs. Only two properties
// matter here. So the rules that mention `display` or `visibility` are collected once per page, and an element
// that none of them selects, that has no `hidden` attribute and is not one of the few tags the default sheet
// hides, cannot be hidden by a stylesheet: its own inline style decides, and that is read directly. Every other
// element still goes through getComputedStyle. The shortcut never decides a case the full lookup would decide
// differently; it only skips the lookups whose answer is already known.
const DEFAULT_SHEET_MAY_HIDE = new Set(['AREA', 'BASE', 'BASEFONT', 'DATALIST', 'DIALOG', 'NOEMBED', 'NOFRAMES',
  'PARAM', 'RP', 'TEMPLATE', 'HEAD', 'LINK', 'META', 'SCRIPT', 'STYLE', 'TITLE']);
const NEVER_AN_ELEMENT = /::|:before|:after|:first-line|:first-letter|:-moz-|:-webkit-|:-ms-/i;
const selectorCache = new WeakMap();

function styleRules(win) {
  const doc = win.document;
  let count = 0;
  for (const sheet of doc.styleSheets) { try { count += sheet.cssRules.length; } catch (e) { count += 1; } }
  const stamp = doc.styleSheets.length + ':' + count;
  const cached = selectorCache.get(win);
  if (cached && cached.stamp === stamp) return cached;
  const fresh = { stamp, selectors: [], unknown: false };
  const visit = (rules) => {
    for (const rule of rules) {
      if (rule.cssRules) { visit(rule.cssRules); continue; }      // @media and the like: taken as applying
      if (!rule.style || !rule.selectorText) continue;
      if (!rule.style.getPropertyValue('display') && !rule.style.getPropertyValue('visibility')) continue;
      for (const part of rule.selectorText.split(',')) {
        const selector = part.trim();
        if (!selector || NEVER_AN_ELEMENT.test(selector)) continue;
        try { doc.documentElement.matches(selector); fresh.selectors.push(selector); }
        catch (e) { fresh.unknown = true; }                          // a selector this DOM cannot evaluate: no shortcut
      }
    }
  };
  for (const sheet of doc.styleSheets) { try { visit(sheet.cssRules); } catch (e) { fresh.unknown = true; } }
  selectorCache.set(win, fresh);
  return fresh;
}

// 0 = shown, 1 = display:none, 2 = visibility hidden or collapsed
function ownStyle(win, el) {
  let exact = el.hasAttribute('hidden') || DEFAULT_SHEET_MAY_HIDE.has(el.tagName)
    || (el.tagName === 'INPUT' && (el.getAttribute('type') || '').toLowerCase() === 'hidden')
    || (el.parentElement !== null && el.parentElement.tagName === 'DETAILS');
  if (!exact) {
    const rules = styleRules(win);
    exact = rules.unknown;
    for (let i = 0; !exact && i < rules.selectors.length; i++) {
      try { exact = el.matches(rules.selectors[i]); } catch (e) { exact = true; }
    }
  }
  if (!exact) {
    // No stylesheet rule about display or visibility selects this element, so only its own inline style can
    // switch it off (this is how jQuery hides things), and that can be read directly.
    const inline = el.getAttribute('style');
    if (inline === null || !/display|visibility/i.test(inline)) return 0;
    const style = el.style;
    if (style) {
      if (style.display === 'none') return 1;
      return (style.visibility === 'hidden' || style.visibility === 'collapse') ? 2 : 0;
    }
  }
  const cs = win.getComputedStyle(el);
  if (cs.display === 'none') return 1;
  return (cs.visibility === 'hidden' || cs.visibility === 'collapse') ? 2 : 0;
}

// Is this element itself switched off? The page is walked from the top and a switched-off element is not
// entered, so by the time an element is asked, its ancestors are known to be shown.
function shownItself(win, el) {
  return ownStyle(win, el) === 0;
}

function observe() {
  const win = dom.window, doc = win.document;
  const out = [];
  current = [];
  // returns the text a reader would see inside `el` (skipped and hidden parts contribute nothing)
  function walk(el, parent) {
    if (SKIP_TAGS.has(el.tagName) || SKIP_IDS.has(el.id)) return '';
    if (!shownItself(win, el)) return '';
    const index = out.length;
    const tag = el.tagName.toLowerCase();
    const rec = { index, parent, tag, text: '' };
    if (el.id) rec.id = el.id;
    const cls = squash(typeof el.className === 'string' ? el.className : (el.getAttribute('class') || ''));
    if (cls) rec.classes = cls;
    for (const a of ATTRS) { const v = el.getAttribute(a); if (v !== null && v !== '') rec[a] = String(v).slice(0, 200); }
    const typed = (el.tagName === 'TEXTAREA') || (el.tagName === 'INPUT' && TEXT_INPUT_TYPES.has((el.getAttribute('type') || '').toLowerCase()));
    if (['INPUT', 'TEXTAREA', 'SELECT', 'OPTION'].includes(el.tagName) && typeof el.value === 'string') rec.value = el.value.slice(0, 200);
    if (el.tagName === 'INPUT' && (el.type === 'checkbox' || el.type === 'radio')) rec.checked = !!el.checked;
    if (el.tagName === 'OPTION') rec.selected = !!el.selected;
    if (doc.activeElement === el) rec.focused = true;
    if (el.disabled === true) rec.disabled = true;
    out.push(rec);
    current.push(el);
    let own = '', kids = 0;
    const parts = [];
    for (const n of el.childNodes) {
      if (n.nodeType === 3) { own += n.nodeValue; parts.push(n.nodeValue); }
      else if (n.nodeType === 1) { const before = out.length; parts.push(walk(n, index)); if (out.length > before) kids++; }
    }
    own = squash(own);
    const full = squash(parts.join(' '));
    rec.text = own;
    if (full && full !== own) rec.full_text = full.slice(0, 200);
    rec.can_click = (kids === 0) || NATIVE_CLICK.has(el.tagName) || own !== '';
    rec.can_type = typed && el.disabled !== true && el.readOnly !== true;
    return full;
  }
  if (doc.body) walk(doc.body, -1);
  const g = (name) => { try { return win.eval(name); } catch (e) { return null; } };
  // the instruction as the benchmark's own environment reads it for an agent (see the Chromium bridge)
  let said = squash((doc.getElementById('query') || { textContent: '' }).textContent);
  try {
    const core = g('core');
    const own = core && typeof core.getUtterance === 'function' ? core.getUtterance() : null;
    const text = own && typeof own === 'object' ? own.utterance : own;
    if (typeof text === 'string' && squash(text)) said = squash(text);
  } catch (e) {}
  return {
    utterance: said,
    done: !!g('WOB_DONE_GLOBAL'),
    raw_reward: Number(g('WOB_RAW_REWARD_GLOBAL')) || 0,
    reason: g('WOB_REWARD_REASON') || null,
    virtual_ms: clock.now - EPOCH_MS,
    elements: out,
    js_errors: errors.splice(0).slice(0, 5),
  };
}

function fire(win, el, type, init) {
  const Ctor = /^(mouse|click|dblclick)/.test(type) ? win.MouseEvent : (/^key/.test(type) ? win.KeyboardEvent : win.Event);
  el.dispatchEvent(new Ctor(type, Object.assign({ bubbles: true, cancelable: true, view: win }, init || {})));
}

function doClick(win, el) {
  if (el.tagName === 'OPTION') {
    // a real user picks an option from the open list; the page then sees `change` on the select
    const select = el.closest('select');
    if (select && !select.disabled) {
      if (select.multiple) el.selected = !el.selected; else select.value = el.value;
      fire(win, select, 'input'); fire(win, select, 'change');
    }
    return;
  }
  fire(win, el, 'mousedown');
  if (typeof el.focus === 'function') el.focus();
  fire(win, el, 'mouseup');
  if (typeof el.click === 'function') el.click(); else fire(win, el, 'click');
}

function doType(win, el, text) {
  if (typeof el.focus === 'function') el.focus();
  el.value = String(text);
  const last = String(text).slice(-1) || ' ';
  fire(win, el, 'keydown', { key: last }); fire(win, el, 'keypress', { key: last });
  fire(win, el, 'input'); fire(win, el, 'keyup', { key: last }); fire(win, el, 'change');
}

async function load(task) {
  if (!/^[a-z0-9-]+$/.test(String(task))) return { ok: false, error: 'TASK_NAME_INVALID' };
  const file = path.join(htmlDir, 'miniwob', task + '.html');
  if (!fs.existsSync(file)) return { ok: false, error: 'TASK_FILE_MISSING' };
  if (dom) { try { clock.uninstall(); } catch (e) {} try { dom.window.close(); } catch (e) {} }
  errors = []; current = []; pageTimeLimit = null;
  const vc = new VirtualConsole();
  vc.on('jsdomError', (e) => { const m = String((e && e.message) || e); if (!/Not implemented/.test(m)) errors.push(m.slice(0, 200)); });
  dom = await JSDOM.fromFile(file, {
    runScripts: 'dangerously', resources: 'usable', pretendToBeVisual: true, virtualConsole: vc,
    beforeParse(window) {
      clock = FakeTimers.withGlobal(window).install({
        now: EPOCH_MS,
        toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval', 'Date', 'requestAnimationFrame', 'cancelAnimationFrame'],
      });
      // jsdom has no 2D canvas: the click-tracking overlay gets a context that accepts every call and draws nothing
      const nothing = new Proxy(function () {}, { get: (t, k) => (k === 'canvas' ? null : nothing), set: () => true, apply: () => nothing });
      window.HTMLCanvasElement.prototype.getContext = function () { return nothing; };
      window.scrollTo = function () {};
      // jsdom reports a 0x0 box for everything, which reads as "nothing is rendered" to any visibility query
      // (jQuery's :visible, used by the pages and by jQuery UI). An element that is displayed gets a nominal
      // 1x1 box instead: "rendered, size unknown". Sizes and positions stay meaningless here.
      const rendered = (el) => {
        if (!el.isConnected) return false;
        for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
          if (ownStyle(window, e) === 1) return false;
        }
        return true;
      };
      const nominal = { x: 0, y: 0, left: 0, top: 0, right: 1, bottom: 1, width: 1, height: 1 };
      window.Element.prototype.getClientRects = function () { return rendered(this) ? [nominal] : []; };
      for (const name of ['offsetWidth', 'offsetHeight']) {
        Object.defineProperty(window.HTMLElement.prototype, name, { configurable: true, get() { return rendered(this) ? 1 : 0; } });
      }
    },
  });
  await new Promise((resolve) => {
    if (dom.window.document.readyState === 'complete') resolve();
    else dom.window.addEventListener('load', () => resolve());
  });
  try { clock.tick(50); } catch (e) { errors.push('TICK_AFTER_LOAD: ' + String(e.message).slice(0, 160)); }
  const win = dom.window;
  const ok = !!(win.core && typeof win.genProblem === 'function' && typeof win.Math.seedrandom === 'function');
  return { ok, js_errors: errors.splice(0).slice(0, 5) };
}

function reset(seed, timeLimitMs) {
  const win = dom.window;
  clock.reset();                       // timers left by the previous episode must not fire in this one
  // focus left by the previous episode is history too: a new episode starts with nothing focused
  try { const a = win.document.activeElement; if (a && a !== win.document.body && typeof a.blur === 'function') a.blur(); } catch (e) {}
  if (pageTimeLimit === null) pageTimeLimit = win.core.EPISODE_MAX_TIME;
  // the caller may lift the page's episode timer to explore (it says so in its record); the default is the page's own
  win.core.EPISODE_MAX_TIME = (typeof timeLimitMs === 'number' && timeLimitMs > 0) ? timeLimitMs : pageTimeLimit;
  win.Math.seedrandom(String(seed));
  if (win.core.cover_div == null) win.core.startEpisode();
  win.core.startEpisodeReal();
  clock.tick(STEP_MS);
  const obs = observe();
  obs.time_limit_ms = win.core.EPISODE_MAX_TIME;
  obs.page_time_limit_ms = pageTimeLimit;
  return obs;
}

function act(action) {
  const win = dom.window;
  const el = current[action.index];
  if (!el || !el.isConnected) return Object.assign(observe(), { action_error: 'NO_SUCH_ELEMENT' });
  if (win.eval('WOB_DONE_GLOBAL')) return Object.assign(observe(), { action_error: 'EPISODE_ALREADY_OVER' });
  let problem = null;
  try {
    if (action.type === 'click') doClick(win, el);
    else if (action.type === 'type') doType(win, el, action.text);
    else problem = 'UNKNOWN_ACTION';
    clock.tick(STEP_MS);
  } catch (e) { problem = 'PAGE_EXCEPTION: ' + String(e.message).slice(0, 160); }
  const obs = observe();
  if (problem) obs.action_error = problem;
  return obs;
}

async function handle(msg) {
  if (msg.cmd === 'versions') {
    return { node: process.version, jsdom: versionOf('jsdom'), fake_timers: versionOf('@sinonjs/fake-timers'), step_ms: STEP_MS, epoch_ms: EPOCH_MS };
  }
  if (msg.cmd === 'load') return load(msg.task);
  if (!dom) return { error: 'NOTHING_LOADED' };
  if (msg.cmd === 'reset') return reset(msg.seed, msg.time_limit_ms);
  if (msg.cmd === 'act') return act(msg.action || {});
  return { error: 'UNKNOWN_COMMAND' };
}

const rl = readline.createInterface({ input: process.stdin });
let chain = Promise.resolve();
rl.on('line', (line) => {
  chain = chain.then(async () => {
    let reply;
    try {
      const msg = JSON.parse(line);
      if (msg.cmd === 'close') { process.stdout.write('{"closed":true}\n'); process.exit(0); }
      reply = await handle(msg);
    } catch (e) { reply = { error: 'BRIDGE_EXCEPTION: ' + String((e && e.message) || e).slice(0, 300) }; }
    process.stdout.write(JSON.stringify(reply) + '\n');
  });
});
rl.on('close', () => { chain.then(() => process.exit(0)); });
