"""A PUBLIC benchmark: MiniWob++, 130 tasks written by strangers.

Every score before this round was on pages I authored -- a closed loop, worthless as evidence.

THE THREE CHANNELS, kept apart on purpose:

  ADDRESS   address_v1: role, accessible name, geometry. Read-only CDP, allowlisted.
  DECIDE    the agent. Rung 1 only: no model. Structure says where; the goal says what.
  SCORE     a separate, auditable channel that can run exactly TWO fixed expressions:
                GOAL    document.querySelector('#query').innerText
                REWARD  WOB_DONE_GLOBAL, WOB_REWARD_GLOBAL
            Nothing else. Any other expression raises. The reward is read AFTER the episode
            and is never in scope when an action is chosen.

READING RULES, stated because a benchmark score is only worth its reading rules:
  allowed   the goal sentence, from the live page at run time (it is the user's instruction)
  allowed   roles/names/geometry of the current screen (that is what looking gives you)
  banned    the task's HTML or JS to find the answer
  banned    the reward before or during the action

MiniWob++ rewards decay with time inside each episode, so these numbers are not comparable to
an untimed benchmark. Reported as-is.
"""
from __future__ import annotations

import base64
import json
import time
import urllib.request
import websocket

BASE = "http://127.0.0.1:8893/html/miniwob/{task}.html"
VIEW = (1280, 900)

GOAL_EXPR = "document.querySelector('#query') ? document.querySelector('#query').innerText : ''"
REWARD_EXPR = ("JSON.stringify({done: !!WOB_DONE_GLOBAL, "
               "reward: (typeof WOB_REWARD_GLOBAL==='number'?WOB_REWARD_GLOBAL:null), "
               "reason: (typeof WOB_REWARD_REASON==='string'?WOB_REWARD_REASON:null)})")


class ScoreChannel:
    """Separate from the act path. Two fixed expressions, no arbitrary evaluation."""
    ALLOWED_METHODS = {"Runtime.enable", "Runtime.evaluate", "Page.enable", "Page.navigate",
                       "Page.captureScreenshot", "Input.dispatchMouseEvent",
                       "Input.dispatchKeyEvent", "Input.insertText",
                       "Emulation.setDeviceMetricsOverride"}
    ALLOWED_EXPRESSIONS = {GOAL_EXPR, REWARD_EXPR}

    def __init__(self):
        pages = [x for x in json.loads(
            urllib.request.urlopen("http://127.0.0.1:9222/json/list").read())
            if x["type"] == "page"]
        self.ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=25,
                                              origin="http://127.0.0.1:9222")
        self.i = 0
        self.calls = []
        self.call("Page.enable")
        self.call("Emulation.setDeviceMetricsOverride",
                  {"width": VIEW[0], "height": VIEW[1], "deviceScaleFactor": 1,
                   "mobile": False})

    def call(self, method, params=None):
        if method not in self.ALLOWED_METHODS:
            raise RuntimeError("SCORE_CHANNEL_FORBIDDEN:" + method)
        self.i += 1
        rid = self.i
        self.calls.append(method)
        self.ws.send(json.dumps({"id": rid, "method": method, "params": params or {}},
                                separators=(",", ":")))
        while True:
            x = json.loads(self.ws.recv())
            if x.get("id") != rid:
                continue
            if "error" in x:
                raise RuntimeError("CDP_ERROR:" + json.dumps(x["error"], sort_keys=True))
            return x.get("result", {})

    def evaluate(self, expr):
        if expr not in self.ALLOWED_EXPRESSIONS:
            raise RuntimeError("SCORE_CHANNEL_FORBIDDEN_EXPRESSION")
        r = self.call("Runtime.evaluate",
                      {"expression": expr, "returnByValue": True, "awaitPromise": False})
        return r.get("result", {}).get("value")

    def navigate(self, url):
        return self.call("Page.navigate", {"url": url})

    def screenshot(self, path):
        r = self.call("Page.captureScreenshot",
                      {"format": "png", "fromSurface": True, "captureBeyondViewport": False})
        open(path, "wb").write(base64.b64decode(r["data"]))

    def click(self, x, y):
        for t in ("mousePressed", "mouseReleased"):
            self.call("Input.dispatchMouseEvent",
                      {"type": t, "x": float(x), "y": float(y), "button": "left",
                       "clickCount": 1})

    def type_text(self, text):
        """Printable characters only. MiniWob inputs are plain ASCII.

        MEASURED FAILURE (r85). This sent `type: "char"` alone, which inserts a character
        but fires no keyDown/keyUp and therefore no `input` event. A plain <input> that
        polls .value still looked fine, so the defect stayed invisible -- but jQuery UI's
        datepicker and any listener-bound field never saw the text. Typing into
        `choose-date` left the box EMPTY while the coordinate was confirmed correct by
        elementFromPoint. A real key press is down + char + up.
        """
        # keyDown with a `text` field INSERTS the character, and a following `char` inserts
        # it AGAIN: "abc" arrived as "aabbcc" (measured r85). keyDown must carry no text;
        # `char` carries it; keyUp closes the press.
        for ch in text:
            self.call("Input.dispatchKeyEvent", {"type": "keyDown"})
            self.call("Input.dispatchKeyEvent", {"type": "char", "text": ch})
            self.call("Input.dispatchKeyEvent", {"type": "keyUp"})
            time.sleep(0.012)

    def goal(self):
        return (self.evaluate(GOAL_EXPR) or "").strip()

    def reward(self):
        v = self.evaluate(REWARD_EXPR)
        try:
            return json.loads(v) if isinstance(v, str) else (v or {})
        except Exception:
            return {}

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass
