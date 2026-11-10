#!/usr/bin/env python3
"""Act on a rendered page: click, type, select, submit -- and prove it by the page's own grader.

WHY THIS EXISTS (r101). The unified model held 444 capabilities and exactly ZERO that
performs a UI action. The one row that advertised `web.browser.rendered.interact` could
only CAPTURE, and its own verification receipt carried a recorded BLOCKER:
`SELECT_TARGET_NOT_FOUND`. The model believed it could click. It could not.

That is the difference between the two halves of the goal. Every capability in the
registry READS: extract, parse, count, verify, audit. `text.file.write` and
`pdf.document.create.from_text` produce files. Nothing touched a screen.

THE ORACLE IS NOT MINE. MiniWob++ graders are written by strangers and live inside the
page: `WOB_DONE_GLOBAL` / `WOB_REWARD_GLOBAL`. A page reports whether it was satisfied.
Self-report ("I clicked and it said ok") is the defect the adapter already refuses
elsewhere, so the same standard applies here: the capability returns the page's verdict,
never its own.

WHAT IS DELIBERATELY NOT CLAIMED: this does not plan, ground, or decide what to click.
It executes a named action at a named target and reports what the page did. Grounding is
a separate capability and a separate measurement (page_first_grounding_v1, r92/r93).
Conflating the two is how a 21/130 became an unexplained number for ten rounds.
"""
from __future__ import annotations
import time
import urllib.request
import json

import websocket

_METHODS = {
    "Runtime.evaluate", "Page.navigate", "Runtime.enable", "Page.enable",
    "Input.dispatchMouseEvent", "Input.dispatchKeyEvent",
}
# The ONLY expressions this capability may evaluate. Anything else raises, so the
# capability cannot be bent into an arbitrary-code channel.
_EXPR = {
    "goal": "document.querySelector('#query') ? document.querySelector('#query').innerText : ''",
    "done": ("JSON.stringify({done: !!WOB_DONE_GLOBAL,"
             "reward: (typeof WOB_REWARD_GLOBAL==='number'?WOB_REWARD_GLOBAL:null)})"),
    "find": None,   # filled per call, see _find_expr
}


def _find_expr(target: str) -> str:
    esc = json.dumps(str(target))
    return (
        "(()=>{const want=%s.trim();const els=Array.from(document.querySelectorAll("
        "'#area button,#area a,#area input,#area select,#area option,#area [role=button],#area [id]'));"
        "for(const e of els){const n=(e.innerText||e.value||e.getAttribute('aria-label')||e.id||'').trim();"
        "if(n===want){const r=e.getBoundingClientRect();"
        "if(r.width>0&&r.height>0)return JSON.stringify({x:r.x+r.width/2,y:r.y+r.height/2,tag:e.tagName});}}"
        "return '';})()" % esc
    )


def _connect():
    pages = [x for x in json.loads(
        urllib.request.urlopen("http://127.0.0.1:9222/json/list").read())
        if x["type"] == "page"]
    if not pages:
        raise RuntimeError("NO_ATTACHABLE_PAGE")
    return websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=25,
                                       origin="http://127.0.0.1:9222")


def _call(ws, i, method, params=None):
    if method not in _METHODS:
        raise RuntimeError("METHOD_NOT_ALLOWED:" + method)
    ws.send(json.dumps({"id": i, "method": method, "params": params or {}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == i:
            if "error" in msg:
                raise RuntimeError("CDP_ERROR:" + str(msg["error"])[:120])
            return msg.get("result", {})


def run(args, root):
    url = str(args.get("url") or "").strip()
    action = str(args.get("action") or "").strip().lower()
    target = str(args.get("target") or "").strip()
    value = args.get("value")
    x, y = args.get("x"), args.get("y")
    if url and not url.startswith("http://127.0.0.1:") and not url.startswith("http://localhost:"):
        # A rendered-page actuator that can be pointed at the open internet is not a
        # capability, it is an egress channel. Benchmark pages are local.
        raise RuntimeError("URL_NOT_LOCAL_BENCHMARK_PAGE")
    if action not in ("click", "type", "select", "press", "focus"):
        raise RuntimeError("ACTION_NOT_SUPPORTED:" + action)

    ws = _connect()
    try:
        _call(ws, 1, "Page.enable")
        _call(ws, 2, "Runtime.enable")
        if url:
            _call(ws, 3, "Page.navigate", {"url": url})
            time.sleep(1.2)
        # MEASURED (r101). Several MiniWob tasks render an EMPTY #area and an empty
        # #query until the first user interaction starts the episode: click-button,
        # click-option and click-tab all reported goal='' area='' immediately after
        # navigation, while click-test was fully rendered. The benchmark's own driver
        # has always clicked once to start. Without this the actuator cannot see the
        # page it is supposed to act on and reports TARGET_NOT_ON_PAGE for a target
        # that does not exist yet.
        if url:
            for t in ("mousePressed", "mouseReleased"):
                _call(ws, 4, "Input.dispatchMouseEvent",
                      {"type": t, "x": 80.0, "y": 104.0, "button": "left", "clickCount": 1})
            time.sleep(1.4)

        def ev(expr, i):
            r = _call(ws, i, "Runtime.evaluate", {"expression": expr, "returnByValue": True})
            return (r.get("result") or {}).get("value")

        goal = (ev(_EXPR["goal"], 10) or "").strip()
        if action == "press":
            for ch in ("\r",):
                _call(ws, 20, "Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter",
                                                         "windowsVirtualKeyCode": 13})
                _call(ws, 21, "Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter",
                                                         "windowsVirtualKeyCode": 13})
            where = {"via": "enter"}
        else:
            if x is not None and y is not None:
                h = {"x": float(x), "y": float(y), "tag": "COORDINATE"}
            else:
                hit = ev(_find_expr(target), 11)
                if not hit:
                    raise RuntimeError("TARGET_NOT_ON_PAGE:" + target[:60])
                h = json.loads(hit)
            _call(ws, 12, "Input.dispatchMouseEvent",
                  {"type": "mousePressed", "x": h["x"], "y": h["y"], "button": "left",
                   "clickCount": 1})
            _call(ws, 13, "Input.dispatchMouseEvent",
                  {"type": "mouseReleased", "x": h["x"], "y": h["y"], "button": "left",
                   "clickCount": 1})
            if value is not None and action in ("type", "select"):
                for ch in str(value):
                    _call(ws, 14, "Input.dispatchKeyEvent", {"type": "keyDown"})
                    _call(ws, 15, "Input.dispatchKeyEvent", {"type": "char", "text": ch})
                    _call(ws, 16, "Input.dispatchKeyEvent", {"type": "keyUp"})
                    time.sleep(0.012)
            where = {"x": h["x"], "y": h["y"], "tag": h.get("tag")}
        time.sleep(0.5)
        verdict = json.loads(ev(_EXPR["done"], 30) or "{}")
    finally:
        try:
            ws.close()
        except Exception:
            pass

    done = bool(verdict.get("done"))
    reward = verdict.get("reward")
    if not done:
        raise RuntimeError("PAGE_DID_NOT_ACCEPT:done=False")
    return {
        "adapter": "rendered_page_act",
        "url": url,
        "goal_seen_on_page": goal,
        "action": action,
        "target": target,
        "acted_at": where,
        "page_reported_done": done,
        "page_reported_reward": reward,
        "output_verified": bool(done and isinstance(reward, (int, float)) and reward > 0),
    }
