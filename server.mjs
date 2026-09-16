import http from 'node:http';
import crypto from 'node:crypto';
import chromium from '@sparticuz/chromium';
import puppeteer from 'puppeteer-core';

const PORT = Number(process.env.PORT || 10000);
const TOKEN = process.env.BROWSER_SENSOR_TOKEN || '';
const VIEWPORT = { width: 1280, height: 720, deviceScaleFactor: 1 };
const MAX_BODY = 1024 * 1024;
let browser = null;
const sessions = new Map();

function send(res, status, data) {
  const body = JSON.stringify(data);
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'content-length': Buffer.byteLength(body), 'cache-control': 'no-store' });
  res.end(body);
}
function authorized(req) {
  if (!TOKEN) return false;
  const value = req.headers.authorization || '';
  if (!value.startsWith('Bearer ')) return false;
  const supplied = Buffer.from(value.slice(7));
  const expected = Buffer.from(TOKEN);
  return supplied.length === expected.length && crypto.timingSafeEqual(supplied, expected);
}
async function bodyJson(req) {
  const chunks = [];
  let n = 0;
  for await (const chunk of req) {
    n += chunk.length;
    if (n > MAX_BODY) throw new Error('BODY_TOO_LARGE');
    chunks.push(chunk);
  }
  if (!chunks.length) return {};
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}
async function ensureBrowser() {
  if (browser?.connected) return browser;
  const executablePath = await chromium.executablePath();
  browser = await puppeteer.launch({
    args: [...chromium.args, '--disable-dev-shm-usage', '--no-zygote'],
    executablePath,
    headless: true,
    defaultViewport: VIEWPORT,
  });
  browser.on('disconnected', () => {
    browser = null;
    sessions.clear();
  });
  return browser;
}
function getSession(id) {
  const s = sessions.get(id);
  if (!s) throw new Error('SESSION_NOT_FOUND');
  return s;
}
async function closeSession(id) {
  const s = sessions.get(id);
  if (!s) return false;
  sessions.delete(id);
  try { await s.context.close(); } catch {}
  return true;
}

const server = http.createServer(async (req, res) => {
  const started = Date.now();
  try {
    const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
    if (req.method === 'GET' && url.pathname === '/health') {
      return send(res, 200, {
        ok: true,
        schema: 'PROJECT_BRAIN_RENDER_BROWSER_SENSOR_V1',
        browser_connected: Boolean(browser?.connected),
        active_sessions: sessions.size,
        max_sessions: 1,
        memory_rss_bytes: process.memoryUsage().rss,
      });
    }
    if (!authorized(req)) return send(res, 401, { ok: false, error: 'UNAUTHORIZED' });

    if (req.method === 'POST' && url.pathname === '/session/start') {
      if (sessions.size >= 1) return send(res, 409, { ok: false, error: 'SESSION_LIMIT' });
      const b = await ensureBrowser();
      const context = await b.createBrowserContext();
      const page = await context.newPage();
      await page.setViewport(VIEWPORT);
      const id = crypto.randomUUID();
      sessions.set(id, { context, page, createdAt: Date.now() });
      return send(res, 200, { ok: true, session_id: id, viewport: VIEWPORT, elapsed_ms: Date.now() - started });
    }

    const m = url.pathname.match(/^\/session\/([^/]+)(?:\/(navigate|screenshot|click|type|key))?$/);
    if (!m) return send(res, 404, { ok: false, error: 'NOT_FOUND' });
    const id = decodeURIComponent(m[1]);
    const op = m[2] || '';

    if (req.method === 'DELETE' && !op) {
      const closed = await closeSession(id);
      return send(res, closed ? 200 : 404, { ok: closed, closed });
    }

    const { page } = getSession(id);
    if (req.method === 'POST' && op === 'navigate') {
      const b = await bodyJson(req);
      const target = String(b.url || '');
      if (!/^https?:\/\//i.test(target)) return send(res, 400, { ok: false, error: 'HTTP_URL_REQUIRED' });
      await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 30000 });
      return send(res, 200, { ok: true, url: page.url(), title: await page.title(), elapsed_ms: Date.now() - started });
    }
    if (req.method === 'GET' && op === 'screenshot') {
      const png = Buffer.from(await page.screenshot({ type: 'png', fullPage: false }));
      return send(res, 200, {
        ok: true,
        screenshot_sha256: crypto.createHash('sha256').update(png).digest('hex'),
        mime: 'image/png',
        width: VIEWPORT.width,
        height: VIEWPORT.height,
        png_base64: png.toString('base64'),
        url: page.url(),
        elapsed_ms: Date.now() - started,
      });
    }
    if (req.method === 'POST' && op === 'click') {
      const b = await bodyJson(req);
      const x = Number(b.x_norm), y = Number(b.y_norm);
      if (!Number.isFinite(x) || !Number.isFinite(y) || x < 0 || x > 1 || y < 0 || y > 1) return send(res, 400, { ok: false, error: 'NORMALIZED_COORDS_REQUIRED' });
      await page.mouse.click(Math.round(x * VIEWPORT.width), Math.round(y * VIEWPORT.height));
      await new Promise(r => setTimeout(r, 120));
      return send(res, 200, { ok: true, clicked: { x_norm: x, y_norm: y }, url: page.url(), elapsed_ms: Date.now() - started });
    }
    if (req.method === 'POST' && op === 'type') {
      const b = await bodyJson(req);
      const text = String(b.text ?? '');
      if (text.length > 10000) return send(res, 400, { ok: false, error: 'TEXT_TOO_LARGE' });
      await page.keyboard.type(text, { delay: 0 });
      return send(res, 200, { ok: true, typed_chars: text.length, elapsed_ms: Date.now() - started });
    }
    if (req.method === 'POST' && op === 'key') {
      const b = await bodyJson(req);
      const key = String(b.key || '');
      if (!key || key.length > 32) return send(res, 400, { ok: false, error: 'KEY_REQUIRED' });
      await page.keyboard.press(key);
      return send(res, 200, { ok: true, key, elapsed_ms: Date.now() - started });
    }
    return send(res, 405, { ok: false, error: 'METHOD_NOT_ALLOWED' });
  } catch (e) {
    const error = String(e?.message || e);
    const status = error === 'SESSION_NOT_FOUND' ? 404 : error === 'BODY_TOO_LARGE' ? 413 : error.includes('JSON') ? 400 : 500;
    return send(res, status, { ok: false, error, elapsed_ms: Date.now() - started });
  }
});

async function shutdown() {
  for (const id of [...sessions.keys()]) await closeSession(id);
  try { await browser?.close(); } catch {}
  process.exit(0);
}
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
server.listen(PORT, '0.0.0.0', () => console.log(JSON.stringify({ schema: 'PROJECT_BRAIN_RENDER_BROWSER_SENSOR_V1', listening: PORT })));
