"""The browser: one more sense the loop can consult.

Scope, deliberately narrow. This module perceives a page and acts on it. It
does not decide which element serves a goal -- the loop does that, using
the same machinery it already uses to choose between commands. Scoring
fields by keyword overlap inside the driver was tried and removed: it put a
decision in the wrong layer, and the loop is better placed to make it
because it knows the goal.

Everything here is deterministic. No model call describes a page; a page is
loaded and reported.
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

SCHEMA = "PROJECT_BRAIN_BROWSER_V1"
BUILD = os.environ.get("BRAIN_BROWSER_BUILD", os.path.expanduser("~/browser_build"))
NODE = os.path.join(BUILD, "node_modules")
HERE = Path(__file__).resolve().parent
BRIDGE = str(HERE / "browser_bridge_v1.js")
LAUNCH = str(HERE / "browser_launch_v1.sh")
PORT = os.environ.get("BRAIN_BROWSER_PORT", "9222")
_URL = re.compile(r"https?://[^\s\"'<>)\]]+")

_ACTIVE_PINS: set = set()


def urls_in(text: str) -> list[str]:
    """Every URL a goal or file mentions -- how the loop notices a task is
    about a page at all."""
    seen, out = set(), []
    for u in _URL.findall(text or ""):
        u = u.rstrip(".,;:")
        if u not in seen:
            seen.add(u); out.append(u)
    return out


def host_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def available() -> tuple[bool, str]:
    if not shutil.which("node"):
        return False, "node is not installed"
    if not os.path.exists(os.path.join(BUILD, "chromium")):
        return False, f"no browser built yet (run {LAUNCH})"
    if not os.path.exists(os.path.join(NODE, "playwright-core")):
        return False, "playwright-core missing"
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
    validate against the system trust store, and the browser is then held
    to it. A different key means a different server, and the page fails to
    load rather than loading quietly from whoever answered.
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

    Pins can only be set at launch, so a new host means one restart. Without
    the right pins a page cannot load at all, so this is what makes HTTPS
    work, not a security extra.
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
    _ACTIVE_PINS.clear(); _ACTIVE_PINS.update(pins)
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


def _bridge(args: list[str], timeout: int = 180) -> dict:
    env = dict(os.environ, NODE_PATH=NODE, BROWSER_PORT=PORT)
    r = subprocess.run(["node", BRIDGE] + args, capture_output=True, text=True,
                       timeout=timeout, env=env)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "browser failed").strip()[:400])
    return json.loads(r.stdout)


def state(url: str) -> dict:
    """Load a page and report it: text, plus every interactive element with
    the name a person would call it.

    Choosing between those elements is the loop's job, not ours.
    """
    ok, why = ensure([host_of(url)])
    if not ok:
        return {"schema": SCHEMA, "ok": False, "reason": why, "url": url}
    return {"schema": SCHEMA, "ok": True, "url": url, "data": _bridge(["state", url])}


def click(selector: str) -> dict:
    return _bridge(["click", selector])


def type_into(selector: str, text: str, enter: bool = False) -> dict:
    return _bridge(["type", selector, text] + (["--enter"] if enter else []))


def screenshot(url: str, path: str) -> dict:
    ok, why = ensure([host_of(url)])
    if not ok:
        return {"ok": False, "reason": why}
    return {"ok": True, "data": _bridge(["shot", url, path])}
