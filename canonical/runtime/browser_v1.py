"""The browser: one more sense the loop can consult.

This is deliberately thin. Three things exist and each has one job:

    browser_launch_v1.sh   obtain a Chromium and pin TLS.
                           Ours, because Playwright's downloader cannot
                           reach its CDN and this build has no root store.
    osworld_v21_browser_cdp_v1
                           drive it -- typed, validated, policy-bound, and
                           already in this repo. Registered long ago and
                           unable to run until a browser existed.
    the loop               decide which element serves the goal.

Earlier versions of this module wrote their own CDP client and their own
scoring of which field a goal meant. Both were mistakes of the same kind:
building something that already existed, and deciding something the loop
should decide. What is left here is only the seam between them.

Nothing here asks a model to describe a page. A page is loaded and reported.
"""
from __future__ import annotations

import base64
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from collections.abc import Mapping

SCHEMA = "PROJECT_BRAIN_BROWSER_V1"
BUILD = os.environ.get("BRAIN_BROWSER_BUILD", os.path.expanduser("~/browser_build"))
HERE = Path(__file__).resolve().parent
LAUNCH = str(HERE / "browser_launch_v1.sh")
PORT = os.environ.get("BRAIN_BROWSER_PORT", "9222")
_URL = re.compile(r"https?://[^\s\"'<>)\]]+")

_ACTIVE_PINS: set = set()


def urls_in(text: str) -> list[str]:
    """Every URL a goal or file mentions -- how the loop notices that a task
    is about a page at all."""
    seen, out = set(), []
    for u in _URL.findall(text or ""):
        u = u.rstrip(".,;:")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def host_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def available() -> tuple[bool, str]:
    """Answered from the filesystem, not from hope."""
    if not shutil.which("node"):
        return False, "node is not installed"
    if not os.path.exists(os.path.join(BUILD, "chromium")):
        return False, f"no browser built yet (run {LAUNCH})"
    try:
        import playwright  # noqa: F401
    except Exception:
        return False, "playwright not importable in this interpreter"
    return True, "browser present"


def running(port: str = PORT) -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2):
            return True
    except Exception:
        return False


def spki_pins(host: str, port: int = 443, timeout: int = 25) -> list[str]:
    """Base64 SHA-256 SPKI hashes of a host's public keys.

    This build has no root certificate store -- it ships without
    libnssckbi.so, and every copy reachable from here is a Git LFS pointer
    rather than a binary -- so the CA system cannot decide whether a
    certificate is genuine. Pinning the key decides it cryptographically
    instead of not at all.

    Trust on first use: the key is read once through openssl, which does
    validate against the system trust store, and the browser is held to it
    afterwards. A different key means a different server, and the page fails
    to load rather than loading quietly from whoever answered.
    """
    try:
        raw = subprocess.run(
            ["openssl", "s_client", "-showcerts", "-servername", host,
             "-connect", f"{host}:{port}"],
            input=b"", capture_output=True, timeout=timeout).stdout
    except Exception:
        return []
    pins = []
    for cert in re.findall(rb"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
                           raw, re.S):
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


def stop() -> None:
    subprocess.run(["pkill", "-x", "chromium"], capture_output=True)
    _ACTIVE_PINS.clear()


def ensure(hosts: list[str], port: str = PORT, timeout: int = 180) -> tuple[bool, str]:
    """A browser running that is pinned to every host named.

    Pins can only be set at launch, so a new host costs one restart. Without
    the right pins a page cannot load at all, so this is what makes HTTPS
    work, not a security extra bolted on.
    """
    hosts = [h for h in hosts if h]
    if not hosts:
        return start(port=port)
    pins = set(_ACTIVE_PINS)
    for h in hosts:
        pins |= set(spki_pins(h))
    if not pins:
        return False, f"could not read a public key for {', '.join(hosts)}"
    if running(port) and pins <= _ACTIVE_PINS:
        return True, "already running with these pins"
    stop()
    env = dict(os.environ, CHROMIUM_SPKI_PINS=",".join(sorted(pins)))
    env.pop("CHROMIUM_INSECURE", None)
    r = subprocess.run(["sh", LAUNCH, port], capture_output=True, text=True,
                       timeout=timeout, env=env)
    if r.returncode != 0 or not running(port):
        return False, (r.stdout + r.stderr).strip()[:300]
    _ACTIVE_PINS.clear()
    _ACTIVE_PINS.update(pins)
    named = ", ".join(sorted(set(hosts)))
    return True, f"pinned to {len(pins)} key(s) for {named}"


def start(port: str = PORT, timeout: int = 120, pins: list[str] | None = None) -> tuple[bool, str]:
    ok, why = available()
    if not ok:
        return False, why
    if running(port):
        return True, "already running"
    env = None
    if pins:
        env = dict(os.environ, CHROMIUM_SPKI_PINS=",".join(pins))
        env.pop("CHROMIUM_INSECURE", None)
    r = subprocess.run(["sh", LAUNCH, port], capture_output=True, text=True,
                       timeout=timeout, env=env)
    if r.returncode == 0 and running(port):
        _ACTIVE_PINS.update(pins or [])
        return True, "started"
    return False, (r.stdout + r.stderr).strip()[:300]


def _load_cdp_driver():
    """Resolve the CDP driver whether or not its directory is on sys.path.

    A bare ``import osworld_v21_browser_cdp_v1`` only resolves when
    ``canonical/runtime`` happens to be importable as a top-level path. The
    runtime loads its modules by file path instead -- that is what
    ``goal_compiler._load_sibling_runtime_module`` does -- and under that
    loader the bare import raised ``ModuleNotFoundError``, so every entry point
    that drives a browser (``bind``, and therefore ``state`` and ``act``) failed
    even with a live Chromium on the port. Resolved next to this file first,
    with the bare import kept as the fallback for callers that do have the
    directory on their path.
    """
    import importlib.util
    import sys

    try:
        import osworld_v21_browser_cdp_v1 as OC
        return OC
    except ImportError:
        pass
    path = Path(__file__).resolve().with_name("osworld_v21_browser_cdp_v1.py")
    spec = importlib.util.spec_from_file_location("osworld_v21_browser_cdp_v1", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load CDP driver from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def bind(port: str = PORT):
    """The repo's own browser capability, pointed at our running Chromium."""
    import types

    OC = _load_cdp_driver()
    b = OC.BrowserCDP()
    b.bind_environment(types.SimpleNamespace(vm_ip="127.0.0.1", chromium_port=int(port)))
    return b


def state(url: str, timeout: int = 180) -> dict:
    """Load a page and report it: title, text, and every interactive element
    with the name a person would call it.

    Choosing between those elements is the loop's job, not ours.
    """
    ok, why = ensure([host_of(url)])
    if not ok:
        return {"schema": SCHEMA, "ok": False, "reason": why, "url": url}
    b = bind()
    b.act({"type": "NAVIGATE", "url": url})
    snap = b.snapshot()
    page = (snap.get("pages") or [{}])[0]
    elements = page.get("elements") or []
    # The words actually on the page: the title plus the text of every
    # control and link. Enough to judge whether the page is about the goal.
    blob = " ".join([page.get("title") or ""] +
                    [(e.get("text") or "") + " " + (e.get("aria") or "") + " " +
                     (e.get("name") or "") + " " + (e.get("placeholder") or "")
                     for e in elements])
    text = re.sub(r"\s+", " ", blob).strip()
    return {"schema": SCHEMA, "ok": True, "url": url,
            "data": {"url": page.get("url") or url, "title": page.get("title") or "",
                     "chars": len(text), "text": text[:8000], "elements": elements,
                     "page_count": snap.get("page_count", 0)}}


def act(ops, port: str = PORT) -> list[dict]:
    """Drive the page: NAVIGATE, CLICK_SELECTOR, CLICK_TEXT, FILL, PRESS,
    SELECT, CHECK, NEW_TAB, CLOSE_TAB. Which ops to run is the loop's call,
    so this takes them as given and returns what each produced.

    One op or several -- the repo's capability acts on a single mapping.
    """
    b = bind(port)
    single = isinstance(ops, dict)
    out = [b.act(o) for o in ([ops] if single else ops)]
    return out[0] if single else out
