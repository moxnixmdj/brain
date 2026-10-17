// Perception and action. Nothing else.
//
// Deciding WHICH element serves a goal is not this file's job -- that
// belongs to the loop, which already has machinery for choosing between
// candidates. Scoring fields by token overlap inside the driver was the
// same mistake as hand-rolling the protocol: solving in the wrong layer.
// So this exposes what is on the page and offers the means to act on it.
//
// The one thing we genuinely own is getting a Chromium at all: Playwright's
// downloader cannot reach its CDN, so browser_launch_v1.sh fetches the
// binary from npm. Everything after that is Playwright's job.
//
//   node browser_bridge_v1.js state <url>            what is on the page
//   node browser_bridge_v1.js click <sel>
//   node browser_bridge_v1.js type  <sel> <text> [--enter]
//   node browser_bridge_v1.js shot  <url> <outfile>
const { chromium } = require('playwright-core');
const PORT = process.env.BROWSER_PORT || '9222';

async function open(url) {
  const browser = await chromium.connectOverCDP(`http://127.0.0.1:${PORT}`);
  const ctx = browser.contexts()[0] || await browser.newContext();
  const page = ctx.pages()[0] || await ctx.newPage();
  if (url) await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  return { browser, page };
}

// What a person would call each control: its accessible name. This is what
// the loop matches a goal against, so it has to be the text a human reads.
async function state(url) {
  const { browser, page } = await open(url);
  const elements = await page.evaluate(`(() => {
    const vis = e => { const r = e.getBoundingClientRect();
      return r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== 'hidden'; };
    const name = e => ([e.getAttribute('aria-label'),
      (e.labels && e.labels[0] && e.labels[0].innerText),
      e.placeholder, e.title, e.name, e.id, e.innerText]
      .map(s => (s || '').trim()).filter(Boolean)[0] || '');
    const sel = (e, i) => e.id ? '#' + CSS.escape(e.id)
      : e.getAttribute('data-testid') ? '[data-testid="' + e.getAttribute('data-testid') + '"]'
      : e.tagName.toLowerCase() + ':nth-of-type(' + i + ')';
    return [...document.querySelectorAll(
      'a[href],button,input,textarea,select,[role=button],[onclick]')]
      .map((e, i) => ({ role: e.tagName.toLowerCase(), type: e.type || null,
        name: name(e).slice(0, 120), value: (e.value || '').slice(0, 120),
        text: (e.innerText || '').trim().slice(0, 120), selector: sel(e, i + 1),
        visible: vis(e), disabled: !!e.disabled }))
      .filter(e => e.visible && !e.disabled).slice(0, 120);
  })()`);
  const text = (await page.locator('body').innerText()).replace(/\s+/g, ' ').trim();
  const out = { url: page.url(), title: await page.title(), chars: text.length,
    text: text.slice(0, 8000), elements };
  await browser.close();
  return out;
}

(async () => {
  const [cmd, a, b, c] = process.argv.slice(2);
  if (cmd === 'state') return console.log(JSON.stringify(await state(a), null, 1));
  if (cmd === 'shot') {
    const { browser, page } = await open(a);
    await page.setViewportSize({ width: 900, height: 700 });
    await page.screenshot({ path: b });
    const { size } = require('fs').statSync(b);
    const out = { path: b, bytes: size, title: await page.title(), url: page.url() };
    await browser.close(); return console.log(JSON.stringify(out, null, 1));
  }
  if (cmd === 'click') {
    const { browser, page } = await open();
    await page.click(a, { timeout: 20000 });
    await page.waitForLoadState('domcontentloaded').catch(() => {});
    const out = { clicked: a, url: page.url(), title: await page.title() };
    await browser.close(); return console.log(JSON.stringify(out, null, 1));
  }
  if (cmd === 'type') {
    const { browser, page } = await open();
    await page.fill(a, b);
    if (c === '--enter') await page.press(a, 'Enter');
    await page.waitForLoadState('domcontentloaded').catch(() => {});
    const out = { typed: b, into: a, url: page.url(), title: await page.title() };
    await browser.close(); return console.log(JSON.stringify(out, null, 1));
  }
  console.error('unknown command', cmd); process.exit(2);
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
