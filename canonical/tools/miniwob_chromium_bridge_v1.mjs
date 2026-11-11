// MiniWoB++ task pages in a real Chromium, one JSON command per line on stdin, one JSON reply per line on stdout.
//
// What this is: the public MiniWoB++ task pages (Farama-Foundation/miniwob-plusplus, MIT, pages nobody in this
// repository wrote) loaded in headless Chromium, with the browser's own layout, hit-testing and input pipeline.
// A click is a real mouse press at a point of the element where the element is on top; typing is real key events
// into whatever the click focused. The page's own reward is read back. Same commands and same observation as the jsdom bridge
// next to this file, plus the box of every element in window pixels.
//
// What this is not: a person's desktop. It is headless, the window is small and fixed, there is one page, and
// the browser binary is the one the npm package @sparticuz/chromium carries (built for servers; its text is
// drawn with the one font family that package ships, so boxes can differ by pixels from a desktop Chrome).
//
// Six properties the measurement depends on, enforced here rather than hoped for:
//   * one episode, one verdict. What is read back after an action is the page's verdict on the episode the action
//     began in. Nothing the hand does begins another episode: the page's own START cover, which a press would
//     otherwise turn into a new episode in the middle of an action made of several presses, takes no press;
//   * an episode is a freshly opened page. Every reset loads the page again and then seeds it, so nothing a
//     previous episode did (scroll positions, widgets a library set up once, script variables) can reach the next
//     one, and a seed means one page by construction;
//   * time is virtual. setTimeout / setInterval / requestAnimationFrame / Date / performance.now belong to a
//     clock that only moves when a command moves it, and CSS transitions and animations are switched off, so the
//     same (task, seed, actions) gives the same episode on any machine;
//   * the agent has one channel: a hand. It can press an element (once, or three times fast), type into one,
//     move the pointer onto one, take hold of one and let go of it over another, carry one a short way up, down,
//     left or right, and let time pass. It cannot read page globals, run script, or see anything except the shown
//     elements and the instruction. The instruction is what the benchmark's own environment hands to an agent
//     (`core.getUtterance()`; one page words a colour sample there, all others return the instruction's text);
//   * the page is looked at after it has been drawn. Every look waits for one real frame, and for every file
//     that frame made the page ask for (a stylesheet asks for a picture only when the element showing it is first
//     drawn), so the boxes reported are the ones a person would see, the first time as much as the hundredth;
//   * an action lands where a hand would land: on a part of the element that can be seen. Its middle when the
//     element is on top there; else the point nearest the middle where it is (two buttons that overlap are both
//     still pressable, each on what shows of it); when nothing of it shows, its middle, and whatever covers it
//     gets the press. An element outside its scrolling container is first scrolled into view, as a hand would do.
//
// usage: node miniwob_chromium_bridge_v1.mjs <path to miniwob/html> [<directory containing node_modules>]
//        (node_modules must hold puppeteer-core and @sparticuz/chromium)
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import readline from 'node:readline';
import { pathToFileURL } from 'node:url';

const htmlDir = process.argv[2];
const modulesDir = process.argv[3] || process.env.MINIWOB_CHROMIUM_NODE_MODULES || process.cwd();

const STEP_MS = 500;               // virtual time that passes after a reset and after every action
const EPOCH_MS = 1767225600000;    // 2026-01-01T00:00:00Z: every episode starts its clock here
const VIEWPORT = { width: 480, height: 360, deviceScaleFactor: 1 };
const REST_POINT = { x: VIEWPORT.width - 2, y: VIEWPORT.height - 2 };   // where the pointer waits between episodes
const KEY_EVENTS_UP_TO = 32;       // longer text is inserted in one piece, except its last character
const COMMAND_TIMEOUT_MS = 15000;
const DRAG_STEPS = 12;             // pointer positions the page is told of between the two ends of a drag
const NUDGE_PX = 30;               // how far a nudge carries what it took hold of
const DROP_PAST_SHARE = 1 / 8;     // a dropped thing is let go this share of the target's smaller side past its middle,
const DROP_PAST_MIN_PX = 2;        // and never less than this
const NUDGES = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
const MAX_WAIT_S = 60;
const AIMED = new Set(['click', 'type', 'hover', 'grab', 'drop', 'nudge', 'triple']);   // actions done AT an element
const PAGE_CONFIG = {
  epoch: EPOCH_MS,
  skipIds: ['query', 'reward-display', 'sync-task-cover', 'click-canvas'],
  skipTags: ['SCRIPT', 'STYLE', 'LINK', 'META', 'HEAD', 'TITLE', 'BR', 'NOSCRIPT', 'TEMPLATE'],
  nativeClick: ['BUTTON', 'INPUT', 'A', 'OPTION', 'LABEL', 'TEXTAREA', 'SUMMARY', 'AREA'],
  textInputTypes: ['text', 'password', 'email', 'number', 'search', 'tel', 'url', 'date', 'time', 'datetime-local', 'month', 'week', ''],
  attrs: ['type', 'name', 'for', 'placeholder', 'title', 'alt', 'href', 'role', 'aria-label', 'data-value', 'data-index'],
  aimGrid: 7,                      // a covered middle: this many points each way across the element are tried
};

function packageAt(name) {
  const base = path.join(modulesDir, 'node_modules', name);
  const meta = JSON.parse(fs.readFileSync(path.join(base, 'package.json'), 'utf8'));
  const root = meta.exports && meta.exports['.'];
  const entry = (root && (root.import || root.default)) || meta.main || 'index.js';
  return { base, version: meta.version, url: pathToFileURL(path.join(base, entry)).href };
}

// ---- everything below this line, up to the matching marker, runs INSIDE the page, before any page script ------
function inPage(cfg) {
  const EPOCH = cfg.epoch;
  const RealDate = Date;
  const realFrame = window.requestAnimationFrame.bind(window);   // the browser's own, kept for drawn(): the page gets the virtual ones
  const realTask = window.setTimeout.bind(window);
  const SKIP_IDS = new Set(cfg.skipIds), SKIP_TAGS = new Set(cfg.skipTags);
  const NATIVE_CLICK = new Set(cfg.nativeClick), TEXT_INPUT_TYPES = new Set(cfg.textInputTypes);
  const timers = new Map();
  const errors = [];
  let now = EPOCH, order = 0, nextId = 1, current = [], pageTimeLimit = null;
  let lastInputAt = EPOCH;         // when the hand last did something (or the episode began)
  let grabbed = null;              // the element the hand has hold of, if any
  let waited = null;               // seconds the hand has just let pass doing nothing, if that was its last action

  // -- the clock ---------------------------------------------------------------------------------------------
  function add(fn, delay, args, repeat) {
    let wait = Number(delay);
    if (!(wait >= 0)) wait = 0;
    const id = nextId++;
    timers.set(id, { id, at: now + wait, fn, args, every: repeat ? Math.max(1, wait) : null, order: order++ });
    return id;
  }
  function tick(ms) {
    const end = now + ms;
    for (let fired = 0; ; fired++) {
      let next = null;
      for (const t of timers.values()) {
        if (t.at <= end && (next === null || t.at < next.at || (t.at === next.at && t.order < next.order))) next = t;
      }
      if (next === null) break;
      if (fired > 20000) { errors.push('VIRTUAL_CLOCK_RUNAWAY'); break; }
      now = Math.max(now, next.at);
      if (next.every !== null) { next.at = now + next.every; next.order = order++; } else timers.delete(next.id);
      try {
        if (typeof next.fn === 'function') next.fn.apply(window, next.args); else (0, eval)(String(next.fn));
      } catch (e) { errors.push(String((e && e.message) || e).slice(0, 200)); }
    }
    now = end;
  }
  window.setTimeout = (fn, delay, ...args) => add(fn, delay, args, false);
  window.setInterval = (fn, delay, ...args) => add(fn, delay, args, true);
  window.clearTimeout = window.clearInterval = (id) => { timers.delete(id); };
  window.requestAnimationFrame = (fn) => add(() => fn(now - EPOCH), 16, [], false);
  window.cancelAnimationFrame = (id) => { timers.delete(id); };
  function VirtualDate(...a) {
    if (!new.target) return new RealDate(now).toString();
    return a.length === 0 ? new RealDate(now) : new RealDate(...a);
  }
  VirtualDate.prototype = RealDate.prototype;          // a date made here IS a Date; `instanceof Date` holds both ways
  VirtualDate.now = () => now;
  VirtualDate.parse = RealDate.parse;
  VirtualDate.UTC = RealDate.UTC;
  window.Date = VirtualDate;
  try { Object.defineProperty(window.performance, 'now', { configurable: true, value: () => now - EPOCH }); } catch (e) {}

  window.addEventListener('error', (e) => { errors.push(String((e && e.message) || e).slice(0, 200)); });
  window.addEventListener('unhandledrejection', (e) => { errors.push('REJECTION: ' + String((e && e.reason && e.reason.message) || (e && e.reason)).slice(0, 180)); });
  document.addEventListener('DOMContentLoaded', () => {
    const style = document.createElement('style');
    style.textContent = '*, *::before, *::after { transition: none !important; animation: none !important; scroll-behavior: auto !important; }';
    document.head.appendChild(style);
  });

  // -- what the agent sees -------------------------------------------------------------------------------------
  function squash(s) { return String(s || '').replace(/\s+/g, ' ').trim(); }
  function global(name) { try { return (0, eval)(name); } catch (e) { return null; } }
  function isOption(el) { return el.tagName === 'OPTION' || el.tagName === 'OPTGROUP'; }
  // An option of a drop-down has no box of its own (the browser draws the list); it is on offer whenever its
  // select is. Everything else is asked of the layout engine: display, content-visibility and visibility.
  function shown(el) { return isOption(el) ? true : el.checkVisibility({ visibilityProperty: true }); }

  // The instruction, as the benchmark's own environment reads it for an agent: `core.getUtterance()`. Two kinds
  // of page replace that function: one turns a colour sample in the instruction into the colour's name, three
  // return the text together with the answer taken apart into fields -- of that, only the text is passed on.
  function instruction() {
    const shownText = squash((document.getElementById('query') || { textContent: '' }).textContent);
    try {
      const core = global('core');
      const said = core && typeof core.getUtterance === 'function' ? core.getUtterance() : null;
      const text = said && typeof said === 'object' ? said.utterance : said;
      if (typeof text === 'string' && squash(text)) return squash(text);
    } catch (e) {}
    return shownText;
  }

  function observe() {
    const out = [];
    current = [];
    function walk(el, parent) {
      if (SKIP_TAGS.has(el.tagName) || SKIP_IDS.has(el.id)) return '';
      if (!shown(el)) return '';
      const index = out.length;
      const rec = { index, parent, tag: el.tagName.toLowerCase(), text: '' };
      if (el.id) rec.id = el.id;
      const cls = squash(typeof el.className === 'string' ? el.className : (el.getAttribute('class') || ''));
      if (cls) rec.classes = cls;
      for (const a of cfg.attrs) { const v = el.getAttribute(a); if (v !== null && v !== '') rec[a] = String(v).slice(0, 200); }
      const typed = (el.tagName === 'TEXTAREA') || (el.tagName === 'INPUT' && TEXT_INPUT_TYPES.has((el.getAttribute('type') || '').toLowerCase()));
      if (['INPUT', 'TEXTAREA', 'SELECT', 'OPTION'].includes(el.tagName) && typeof el.value === 'string') rec.value = el.value.slice(0, 200);
      if (el.tagName === 'INPUT' && (el.type === 'checkbox' || el.type === 'radio')) rec.checked = !!el.checked;
      if (el.tagName === 'OPTION') rec.selected = !!el.selected;
      if (document.activeElement === el) rec.focused = true;
      if (el.disabled === true) rec.disabled = true;
      // its colour, as far as the page states one on the element itself, in the page's own words: what a drawn
      // shape is filled with, else the background the element is given inline (nothing is read from stylesheets)
      const fill = el.getAttribute('fill');
      const colour = (fill && fill !== 'none') ? fill : ((el.style && el.style.backgroundColor) || '');
      if (colour) rec.colour = String(colour).slice(0, 60);
      const r = el.getBoundingClientRect();
      rec.box = [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)];
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
      const hasBox = isOption(el) || (r.width > 0 && r.height > 0);
      // what the mouse can land on: an element none of whose children takes up any room is, to a mouse, a leaf
      let roomy = 0;
      for (let k = index + 1; k < out.length; k++) {
        if (out[k].parent === index && (out[k].tag === 'option' || (out[k].box[2] > 0 && out[k].box[3] > 0))) roomy++;
      }
      rec.can_click = hasBox && ((roomy === 0) || NATIVE_CLICK.has(el.tagName) || own !== '');
      rec.can_type = hasBox && typed && el.disabled !== true && el.readOnly !== true;
      return full;
    }
    if (document.body) walk(document.body, -1);
    const seen = {
      utterance: instruction(),
      done: !!global('WOB_DONE_GLOBAL'),
      raw_reward: Number(global('WOB_RAW_REWARD_GLOBAL')) || 0,
      reason: global('WOB_REWARD_REASON') || null,
      virtual_ms: now - EPOCH,
      elements: out,
      js_errors: errors.splice(0).slice(0, 5),
    };
    // a picture still on its way has no size yet, so the boxes around it are not the ones a person would see
    let arriving = 0;
    for (const img of document.images) if (!img.complete) arriving++;
    if (arriving) seen.pictures_still_arriving = arriving;
    // text that shows as selected (a person sees it highlighted); nothing is said when nothing is
    const picked = squash(String(window.getSelection() || ''));
    if (picked) seen.selection = picked.slice(0, 200);
    // what the hand itself is in the middle of: no page shows it, and what can be done next depends on it
    if (grabbed !== null) seen.holding = current.indexOf(grabbed);
    if (waited !== null) seen.waited_s = waited;
    return seen;
  }

  function fire(el, type) { el.dispatchEvent(new Event(type, { bubbles: true, cancelable: true })); }

  // Resolves once the browser has drawn the page as it now is. A frame is asked for by changing something that
  // has to be repainted and shows nowhere (the colour of the text cursor on the root); the browser draws at once
  // when there is something to draw. The task queued from inside the frame runs after that frame's style, layout
  // and paint, which is when a picture named by a stylesheet gets asked for.
  let flip = 0;
  function drawn() {
    return new Promise((resolve) => {
      flip = 1 - flip;
      document.documentElement.style.caretColor = flip ? 'rgb(0, 0, 1)' : 'rgb(0, 0, 2)';
      realFrame(() => { realTask(resolve, 0); });
    });
  }

  window.__bridge = {
    ready() {
      tick(50);
      const core = global('core');
      return { ok: !!(core && typeof global('genProblem') === 'function' && typeof Math.seedrandom === 'function'), js_errors: errors.splice(0).slice(0, 5) };
    },
    reset(seed, timeLimitMs, stepMs) {
      const core = global('core');
      timers.clear();                    // timers left by the previous episode must not fire in this one
      now = EPOCH;
      lastInputAt = EPOCH; grabbed = null; waited = null;
      // focus, selection and scrolling left by the previous episode are history too
      try { const a = document.activeElement; if (a && a !== document.body && typeof a.blur === 'function') a.blur(); } catch (e) {}
      try { window.getSelection().removeAllRanges(); } catch (e) {}
      window.scrollTo(0, 0);
      if (pageTimeLimit === null) pageTimeLimit = core.EPISODE_MAX_TIME;
      // the caller may lift the page's episode timer to explore (it says so in its record); the default is the page's own
      core.EPISODE_MAX_TIME = (typeof timeLimitMs === 'number' && timeLimitMs > 0) ? timeLimitMs : pageTimeLimit;
      Math.seedrandom(String(seed));
      if (core.cover_div == null) core.startEpisode();
      // When an episode ends the page puts a START cover over itself, and a press on the cover begins another
      // episode. An action made of several presses would run on into that one, and what was read back would be
      // the verdict on a page nobody asked about. Here only `reset` begins an episode: the cover takes no press.
      core.cover_div.onclick = null;
      core.startEpisodeReal();
      tick(stepMs);
      return drawn().then(() => {
        const obs = observe();
        obs.time_limit_ms = core.EPISODE_MAX_TIME;
        obs.page_time_limit_ms = pageTimeLimit;
        return obs;
      });
    },
    // Where a hand would go to do `how` to element `index`, or what stops it. A press goes to a point where the
    // element itself (or something inside it) is on top: its middle if that is one -- the left end for something
    // that takes text, so a field made of parts starts at its first part -- else the nearest such point to the
    // middle; if nothing of it is on top, the middle. Letting go of something goes to the middle whatever is
    // there, the thing in the hand included.
    aim(index, how) {
      const el = current[index];
      if (!el || !el.isConnected) return { error: 'NO_SUCH_ELEMENT' };
      if (global('WOB_DONE_GLOBAL')) return { error: 'EPISODE_ALREADY_OVER' };
      if (el.tagName === 'OPTION') {
        if (how !== 'click') return { error: 'ONLY_A_PRESS_PICKS_AN_OPTION' };
        // a person picks an option from the open list; the page then sees `input` and `change` on the select
        const select = el.closest('select');
        if (select && !select.disabled) {
          if (select.multiple) el.selected = !el.selected; else select.value = el.value;
          fire(select, 'input'); fire(select, 'change');
        }
        lastInputAt = now; waited = null;
        return { handled: true };
      }
      el.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'instant' });
      const rects = Array.from(el.getClientRects()).filter((r) => r.width > 0 && r.height > 0);
      if (!rects.length) return { error: 'ELEMENT_HAS_NO_BOX' };
      const r = rects[0];
      let point = { x: how === 'type' ? r.left + Math.min(6, r.width / 2) : r.left + r.width / 2, y: r.top + r.height / 2 };
      const onTop = (x, y) => { const hit = document.elementFromPoint(x, y); return !!hit && (hit === el || el.contains(hit)); };
      if (how !== 'drop' && !onTop(point.x, point.y)) {
        let best = null;
        const n = cfg.aimGrid;
        for (const q of rects) {
          for (let i = 0; i < n; i++) {
            for (let j = 0; j < n; j++) {
              const x = q.left + (i + 0.5) * q.width / n, y = q.top + (j + 0.5) * q.height / n;
              if (!onTop(x, y)) continue;
              const d = (x - point.x) * (x - point.x) + (y - point.y) * (y - point.y);
              if (best === null || d < best.d) best = { x, y, d };
            }
          }
        }
        if (best !== null) point = { x: best.x, y: best.y };
      }
      lastInputAt = now; waited = null;
      if (how === 'drop') { point.w = r.width; point.h = r.height; }
      return point;
    },
    hold(index) { grabbed = current[index] || null; },
    letGo() { grabbed = null; },
    // Nothing is done until `seconds` have gone by since the hand last did something. That IS the action: no
    // further time is added after it.
    wait(seconds) {
      let problem = null;
      const until = lastInputAt + seconds * 1000;
      try { if (until > now) tick(until - now); } catch (e) { problem = 'PAGE_EXCEPTION: ' + String(e.message).slice(0, 160); }
      waited = seconds;
      return drawn().then(() => {
        const obs = observe();
        if (problem) obs.action_error = problem;
        return obs;
      });
    },
    focusedIs(index) { return document.activeElement === current[index]; },
    look() { return drawn().then(() => observe()); },
    // the page itself confirms that these pictures have reached it
    arrived(urls) {
      return Promise.all(urls.map((url) => { const img = new Image(); img.src = url; return img.decode().catch(() => {}); })).then(() => urls.length);
    },
    step(stepMs, problem) {
      try { tick(stepMs); } catch (e) { problem = problem || ('PAGE_EXCEPTION: ' + String(e.message).slice(0, 160)); }
      return drawn().then(() => {
        const obs = observe();
        if (problem) obs.action_error = problem;
        return obs;
      });
    },
  };
}
// ---- end of the in-page part -----------------------------------------------------------------------------------

let browser = null, page = null, versions = null, loadedUrl = null;
const inFlight = new Set();        // files the page has asked for and not yet received
let asked = 0;                     // how many files the page has asked for, ever
let pictures = [];                 // addresses of the pictures among them, since the last look
let held = false;                  // the mouse button is down on something the hand took hold of
let heldAt = null;                 // where the pointer was when it took hold

async function start() {
  const pptr = packageAt('puppeteer-core');
  const pack = packageAt('@sparticuz/chromium');
  const puppeteer = (await import(pptr.url)).default;
  const chromium = await import(pack.url);
  // the package carries the browser and the few shared libraries a bare server lacks, compressed; unpack once
  const bin = path.join(pack.base, 'bin');
  const executablePath = await chromium.inflate(path.join(bin, 'chromium.br'));
  await chromium.inflate(path.join(bin, 'fonts.tar.br'));
  await chromium.inflate(path.join(bin, 'swiftshader.tar.br'));
  const libs = path.join(await chromium.inflate(path.join(bin, 'al2023.tar.br')), 'lib');
  const env = Object.assign({}, process.env, {
    LD_LIBRARY_PATH: [libs, os.tmpdir(), process.env.LD_LIBRARY_PATH || ''].filter(Boolean).join(':'),
    FONTCONFIG_PATH: path.join(os.tmpdir(), 'fonts'),
  });
  browser = await puppeteer.launch({
    executablePath, env, headless: 'shell', defaultViewport: VIEWPORT, protocolTimeout: COMMAND_TIMEOUT_MS,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--no-first-run',
      '--no-default-browser-check', '--mute-audio', '--font-render-hinting=none', '--force-device-scale-factor=1',
      '--allow-file-access-from-files', '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
      '--disable-backgrounding-occluded-windows', '--disable-features=Translate,BackForwardCache',
      '--disable-frame-rate-limit', '--disable-gpu-vsync'],   // input waits for a frame; do not wait for a display that is not there
  });
  page = await browser.newPage();
  page.setDefaultTimeout(COMMAND_TIMEOUT_MS);
  page.on('dialog', (dialog) => { dialog.dismiss().catch(() => {}); });
  await page.evaluateOnNewDocument(`(${inPage.toString()})(${JSON.stringify(PAGE_CONFIG)});`);
  const session = await page.createCDPSession();
  await session.send('Emulation.setFocusEmulationEnabled', { enabled: true });
  session.on('Network.requestWillBeSent', (e) => {
    asked++; inFlight.add(e.requestId);
    if (e.type === 'Image' && e.request && e.request.url) pictures.push(e.request.url);
  });
  session.on('Network.loadingFinished', (e) => { inFlight.delete(e.requestId); });
  session.on('Network.loadingFailed', (e) => { inFlight.delete(e.requestId); });
  await session.send('Network.enable');
  versions = {
    node: process.version, browser: await browser.version(), puppeteer_core: pptr.version,
    chromium_package: pack.version, step_ms: STEP_MS, epoch_ms: EPOCH_MS, viewport: [VIEWPORT.width, VIEWPORT.height],
    drag_steps: DRAG_STEPS, nudge_px: NUDGE_PX,
    browser_pid: browser.process() ? browser.process().pid : null,
  };
}

async function load(task) {
  if (!/^[a-z0-9-]+$/.test(String(task))) return { ok: false, error: 'TASK_NAME_INVALID' };
  const file = path.join(htmlDir, 'miniwob', task + '.html');
  if (!fs.existsSync(file)) return { ok: false, error: 'TASK_FILE_MISSING' };
  loadedUrl = null;
  const url = pathToFileURL(file).href;
  inFlight.clear();
  await page.goto(url, { waitUntil: 'load' });
  const reply = await page.evaluate(() => window.__bridge.ready());
  if (reply.ok) loadedUrl = url;
  return reply;
}

// Files load in real time, which the virtual clock does not own. If drawing the page made it ask for anything,
// the look that came back is already out of date: what was asked for is waited for (real time, bounded), the page
// confirms the pictures have reached it, and it is drawn and looked at again -- until a look asks for nothing new.
// If something never arrives the observation says so instead of hiding it.
async function settled(look) {
  let before = asked;
  pictures = [];
  let seen = await look();
  if (!seen || !Array.isArray(seen.elements)) return seen;
  const keep = {};
  for (const k of ['time_limit_ms', 'page_time_limit_ms', 'action_error']) if (k in seen) keep[k] = seen[k];
  const errors = seen.js_errors || [];
  for (let round = 0; round < 8 && (asked !== before || inFlight.size || seen.pictures_still_arriving); round++) {
    const until = Date.now() + 400;
    while (inFlight.size && Date.now() < until) await new Promise((resolve) => setTimeout(resolve, 1));
    before = asked;
    const urls = pictures.splice(0);
    if (urls.length) await page.evaluate((list) => window.__bridge.arrived(list), urls);
    else if (seen.pictures_still_arriving) await new Promise((resolve) => setTimeout(resolve, 2));
    seen = await page.evaluate(() => window.__bridge.look());
    errors.push(...(seen.js_errors || []));
  }
  if (inFlight.size) seen.files_still_arriving = inFlight.size;
  return Object.assign(seen, keep, { js_errors: errors.slice(0, 5) });
}

async function reset(seed, timeLimitMs) {
  if (held) { await page.mouse.up(); held = false; heldAt = null; }       // nothing is carried from one episode into the next
  await page.mouse.move(REST_POINT.x, REST_POINT.y);
  inFlight.clear();
  await page.goto(loadedUrl, { waitUntil: 'load' });
  const fresh = await page.evaluate(() => window.__bridge.ready());
  if (!fresh.ok) return { error: 'PAGE_DID_NOT_COME_BACK' };
  return settled(() => page.evaluate((s, limit, step) => window.__bridge.reset(s, limit, step), seed, typeof timeLimitMs === 'number' ? timeLimitMs : null, STEP_MS));
}

async function act(action) {
  let problem = null;
  const kind = action.type;
  const typing = kind === 'type';
  if (kind === 'wait') {
    const seconds = Number(action.seconds);
    if (!(seconds > 0 && seconds <= MAX_WAIT_S)) problem = 'WAIT_NOT_UNDERSTOOD';
    else return settled(() => page.evaluate((s) => window.__bridge.wait(s), seconds));
  } else if (!AIMED.has(kind)) problem = 'UNKNOWN_ACTION';
  else if (kind === 'nudge' && !Object.prototype.hasOwnProperty.call(NUDGES, String(action.text))) problem = 'NUDGE_NOT_UNDERSTOOD';
  else if (held && kind !== 'drop') problem = 'THE_HAND_IS_HOLDING_SOMETHING';       // all it can do is let go
  else if (!held && kind === 'drop') problem = 'THE_HAND_HOLDS_NOTHING';
  if (!problem) {
    const aim = await page.evaluate((i, how) => window.__bridge.aim(i, how), action.index, kind);
    if (aim.error) problem = aim.error;
    else if (aim.handled) { /* an option of a drop-down: the page has been told */ }
    else if (kind === 'click' || typing) await page.mouse.click(aim.x, aim.y);
    else if (kind === 'triple') await page.mouse.click(aim.x, aim.y, { count: 3 });
    else if (kind === 'hover') await page.mouse.move(aim.x, aim.y, { steps: 2 });
    else if (kind === 'grab') {
      await page.mouse.move(aim.x, aim.y);
      await page.mouse.down();
      held = true; heldAt = { x: aim.x, y: aim.y };
      await page.evaluate((i) => window.__bridge.hold(i), action.index);
    } else if (kind === 'drop') {
      // The hand lets go just PAST the middle of where it is going, on the line it came along: a list that
      // reorders itself, like much else that takes a dropped thing, counts the thing as arrived once the pointer
      // has crossed the middle, and a pointer resting exactly on the middle has not crossed it.
      const dx = aim.x - heldAt.x, dy = aim.y - heldAt.y, far = Math.hypot(dx, dy);
      if (far > 0) {
        const past = Math.max(DROP_PAST_MIN_PX, Math.min(aim.w, aim.h) * DROP_PAST_SHARE);
        aim.x += dx / far * past; aim.y += dy / far * past;
      }
      await page.mouse.move(aim.x, aim.y, { steps: DRAG_STEPS });
      await page.mouse.up();
      held = false; heldAt = null;
      await page.evaluate(() => window.__bridge.letGo());
    } else if (kind === 'nudge') {
      const [dx, dy] = NUDGES[String(action.text)];
      await page.mouse.move(aim.x, aim.y);
      await page.mouse.down();
      await page.mouse.move(aim.x + dx * NUDGE_PX, aim.y + dy * NUDGE_PX, { steps: DRAG_STEPS });
      await page.mouse.up();
    }
    if (!problem && typing) {
      if (!(await page.evaluate((i) => window.__bridge.focusedIs(i), action.index))) problem = 'TEXT_TARGET_DID_NOT_TAKE_FOCUS';
      else {
        const text = String(action.text);
        await page.keyboard.down('Control'); await page.keyboard.press('KeyA'); await page.keyboard.up('Control');
        if (text === '') await page.keyboard.press('Backspace');
        else if (text.length <= KEY_EVENTS_UP_TO) await page.keyboard.type(text);
        else { await page.keyboard.sendCharacter(text.slice(0, -1)); await page.keyboard.type(text.slice(-1)); }
      }
    }
  }
  return settled(() => page.evaluate((step, why) => window.__bridge.step(step, why), STEP_MS, problem));
}

async function handle(msg) {
  if (msg.cmd === 'versions') return versions;
  if (msg.cmd === 'load') return load(msg.task);
  if (!loadedUrl) return { error: 'NOTHING_LOADED' };
  if (msg.cmd === 'reset') return reset(msg.seed, msg.time_limit_ms);
  if (msg.cmd === 'act') return act(msg.action || {});
  return { error: 'UNKNOWN_COMMAND' };
}

function shutdown(code) {
  try { const child = browser && browser.process(); if (child && child.pid) process.kill(-child.pid, 'SIGKILL'); } catch (e) {}
  try { const child = browser && browser.process(); if (child) child.kill('SIGKILL'); } catch (e) {}
  process.exit(code);
}
process.on('SIGTERM', () => shutdown(0));
process.on('SIGINT', () => shutdown(0));

const rl = readline.createInterface({ input: process.stdin });
let chain = start().catch((e) => { process.stdout.write(JSON.stringify({ error: 'BROWSER_DID_NOT_START: ' + String((e && e.message) || e).slice(0, 300) }) + '\n'); shutdown(1); });
rl.on('line', (line) => {
  chain = chain.then(async () => {
    let reply;
    try {
      const msg = JSON.parse(line);
      if (msg.cmd === 'close') { process.stdout.write('{"closed":true}\n'); shutdown(0); }
      reply = await handle(msg);
    } catch (e) { reply = { error: 'BRIDGE_EXCEPTION: ' + String((e && e.message) || e).slice(0, 300) }; }
    process.stdout.write(JSON.stringify(reply) + '\n');
  });
});
rl.on('close', () => { chain.then(() => shutdown(0)); });
