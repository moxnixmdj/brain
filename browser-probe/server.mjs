import http from 'node:http';
import crypto from 'node:crypto';
import chromium from '@sparticuz/chromium';
import puppeteer from 'puppeteer-core';

const port = Number(process.env.PORT || 3000);

async function runProbe() {
  const executablePath = await chromium.executablePath();
  const browser = await puppeteer.launch({
    args: chromium.args,
    executablePath,
    headless: true,
    defaultViewport: { width: 900, height: 600 },
  });
  try {
    const page = await browser.newPage();
    await page.setContent(`<!doctype html><html><body><h1 id="state">before</h1><button id="go">Change state</button><script>document.querySelector('#go').addEventListener('click',()=>{document.querySelector('#state').textContent='after';document.body.dataset.clicked='yes';});</script></body></html>`, { waitUntil: 'domcontentloaded' });
    const before = await page.$eval('#state', el => el.textContent);
    await page.click('#go');
    await page.waitForFunction(() => document.querySelector('#state')?.textContent === 'after');
    const after = await page.$eval('#state', el => el.textContent);
    const clicked = await page.$eval('body', el => el.dataset.clicked);
    const js = await page.evaluate(() => ({ ua: navigator.userAgent, webdriver: navigator.webdriver, href: location.href }));
    const screenshot = await page.screenshot({ type: 'png' });
    const screenshotSha256 = crypto.createHash('sha256').update(screenshot).digest('hex');
    return { ok: before === 'before' && after === 'after' && clicked === 'yes', before, after, clicked, js, screenshot_sha256: screenshotSha256, screenshot_bytes: screenshot.length };
  } finally {
    await browser.close();
  }
}

const server = http.createServer(async (req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ ok: true }));
    return;
  }
  if (req.url === '/probe') {
    const started = Date.now();
    try {
      const result = await runProbe();
      res.writeHead(result.ok ? 200 : 500, { 'content-type': 'application/json', 'cache-control': 'no-store' });
      res.end(JSON.stringify({ ...result, wall_ms: Date.now() - started }));
    } catch (error) {
      res.writeHead(500, { 'content-type': 'application/json', 'cache-control': 'no-store' });
      res.end(JSON.stringify({ ok: false, error: String(error?.stack || error), wall_ms: Date.now() - started }));
    }
    return;
  }
  res.writeHead(404, { 'content-type': 'application/json' });
  res.end(JSON.stringify({ ok: false, error: 'not_found' }));
});

server.listen(port, '0.0.0.0', () => console.log(`browser probe listening on ${port}`));
