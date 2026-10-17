"""The browser as a capability the loop can choose, not a tool a human names.

The loop already reads projects and consults validators. This adds the one
sense it never had: what a page looks like after the scripts run.

Everything here is deterministic. It launches a real Chromium, drives it
over the DevTools protocol, and returns what was actually there. No model
call decides anything -- that is what makes it a capability rather than a
summariser wearing the same name.
"""
from __future__ import annotations
import json, os, re, shutil, subprocess, urllib.request

SCHEMA = "PROJECT_BRAIN_BROWSER_V1"
BUILD = os.environ.get("BRAIN_BROWSER_BUILD", os.path.expanduser("~/browser_build"))
NODE = os.path.join(BUILD, "node_modules")
DRIVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_cdp_v1.js")
LAUNCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_launch_v1.sh")
PORT = os.environ.get("BRAIN_BROWSER_PORT", "9222")
_URL = re.compile(r"https?://[^\s\"'<>)\]]+")


def urls_in(text: str) -> list[str]:
    """Every URL a goal or file mentions. The loop uses this to notice that
    a task is about a page at all."""
    if not text:
        return []
    seen, out = set(), []
    for u in _URL.findall(text):
        u = u.rstrip(".,;:")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def available() -> tuple[bool, str]:
    """Can a browser run here at all? Answer from the filesystem, not hope."""
    if not shutil.which("node"):
        return False, "node is not installed"
    if not os.path.exists(os.path.join(BUILD, "chromium")):
        return False, f"no browser built yet (run {LAUNCH})"
    return True, "browser present"


def running(port: str = PORT) -> bool:
    """Is a browser already listening? Starting one is slow; reusing is not."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2):
            return True
    except Exception:
        return False


def spki_pins(host: str, port: int = 443, timeout: int = 25) -> list[str]:
    """Base64 SHA-256 hashes of a host's public keys (SPKI pins).

    This build has no root certificate store -- it ships without
    libnssckbi.so, and the only copies reachable from here are Git LFS
    pointers rather than binaries -- so the CA system cannot decide whether
    a certificate is genuine. Pinning the key decides it cryptographically
    instead of not at all.

    The key is read once, over a connection openssl checks against the
    system trust store, and the browser is then held to it. A different key
    means a different server, and the page fails to load instead of loading
    quietly from whoever answered.

    Stronger than the CA system for a pinned host -- no trusted third party
    can vouch for a key we did not pin. Weaker in one way: it is trust on
    first use, so the first read must happen somewhere trustworthy.
    """
    import base64, hashlib, re as _re, subprocess
    try:
        raw = subprocess.run(
            ["openssl", "s_client", "-showcerts", "-servername", host,
             "-connect", f"{host}:{port}"],
            input=b"", capture_output=True, timeout=timeout).stdout
    except Exception:
        return []
    certs = _re.findall(rb"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
                        raw, _re.S)
    pins = []
    for cert in certs:
        try:
            pub = subprocess.run(["openssl", "x509", "-pubkey", "-noout"],
                                 input=cert, capture_output=True, timeout=timeout)
            if pub.returncode:
                continue
            der = subprocess.run(["openssl", "pkey", "-pubin", "-outform", "der"],
                                 input=pub.stdout, capture_output=True, timeout=timeout)
            if der.returncode:
                continue
            dg = subprocess.run(["openssl", "dgst", "-sha256", "-binary"],
                                input=der.stdout, capture_output=True, timeout=timeout)
            if dg.returncode:
                continue
            pins.append(base64.b64encode(dg.stdout).decode())
        except Exception:
            continue
    return list(dict.fromkeys(pins))


def start(port: str = PORT, timeout: int = 120) -> tuple[bool, str]:
    """Launch the browser and wait for its endpoint. Idempotent."""
    ok, why = available()
    if not ok:
        return False, why
    if running(port):
        return True, "already running"
    r = subprocess.run(["sh", LAUNCH, port], capture_output=True, text=True, timeout=timeout)
    return (True, "started") if r.returncode == 0 and running(port) else (False, r.stdout + r.stderr)


def _driver(args: list[str], timeout: int = 180):
    env = dict(os.environ, NODE_PATH=NODE, BROWSER_PORT=PORT)
    r = subprocess.run(["node", DRIVER] + args, capture_output=True, text=True,
                       timeout=timeout, env=env)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "browser driver failed").strip()[:500])
    return json.loads(r.stdout)


READ_JS = """(()=>{
  const t=(document.body&&document.body.innerText||'').replace(/\\s+/g,' ').trim();
  const links=[...document.querySelectorAll('a[href]')].slice(0,60)
      .map(a=>({text:(a.innerText||'').trim().slice(0,80),href:a.href}))
      .filter(l=>l.text||l.href);
  return {title:document.title, url:location.href,
          chars:t.length, text:t.slice(0,6000),
          links:links, scripts:document.querySelectorAll('script').length};
})()"""


def read(url: str, wait_for: str | None = None, timeout: int = 180) -> dict:
    """Load a page in a real browser and report what is actually there.

    wait_for is a JavaScript predicate; the driver polls it rather than
    sleeping, so this returns as soon as the content exists.
    """
    ok, why = start()
    if not ok:
        return {"schema": SCHEMA, "ok": False, "reason": why, "url": url}
    args = [url, READ_JS]
    data = _driver(args, timeout)
    if wait_for:
        data["waited"] = _driver([url, f"(()=>{{return ({wait_for})()}})()"], timeout)
    return {"schema": SCHEMA, "ok": True, "url": url, "data": data}
