"""Channel 4: CAPTURE the transport. Never act, never decide, never evaluate.

The visual executor forbids `Network.*` because a vision agent that reads the network is
cheating at DECIDING. But capturing a human demonstration is not deciding -- it is recording
what already happened. Separating the two is the same discipline as ADDRESS / DECIDE / SCORE:

    ADDRESS  address_v1      where things are        allowlisted reads
    DECIDE   the model       what to do              sees pixels only
    SCORE    bench channel   what the page scored    two fixed expressions
    CAPTURE  this module     what the wire carried   Network events only

The allowlist here cannot click, type, navigate or evaluate. It can only subscribe to the
browser's own network events. `FORBIDDEN_HERE` is the set a capture channel must never have,
and it is asserted in the tests rather than trusted.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
from typing import Any

import websocket

ALLOWED_HERE = {"Network.enable", "Network.disable"}
FORBIDDEN_HERE = (
    "Input.dispatchMouseEvent", "Input.dispatchKeyEvent", "Input.insertText",
    "Page.navigate", "Runtime.evaluate", "Page.captureScreenshot", "DOM.querySelectorAll",
)

# response bodies are useful but this channel does not need them; leaving them out keeps the
# capture unable to read the answer to anything
SKIP_METHODS = {"Network.getResponseBody"}


class CaptureError(RuntimeError):
    pass


class NetworkCapture:
    """Subscribe to Network events for a window of time and return the exchanges."""

    def __init__(self, ws_url: str | None = None):
        if ws_url is None:
            pages = [x for x in json.loads(
                urllib.request.urlopen("http://127.0.0.1:9222/json/list").read())
                if x["type"] == "page"]
            ws_url = pages[0]["webSocketDebuggerUrl"]
        self.ws = websocket.create_connection(ws_url, timeout=20,
                                              origin="http://127.0.0.1:9222")
        self.i = 0
        self.events: list[dict[str, Any]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ---- the only thing this channel may send
    def call(self, method: str, params: dict | None = None) -> dict:
        if method not in ALLOWED_HERE:
            raise CaptureError("CAPTURE_CHANNEL_FORBIDDEN:" + method)
        self.i += 1
        rid = self.i
        self.ws.send(json.dumps({"id": rid, "method": method, "params": params or {}},
                                separators=(",", ":")))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == rid:
                if "error" in msg:
                    raise CaptureError("CDP_ERROR:" + json.dumps(msg["error"]))
                return msg.get("result", {})

    def _pump(self) -> None:
        self.ws.settimeout(0.4)
        while not self._stop.is_set():
            try:
                msg = json.loads(self.ws.recv())
            except Exception:
                continue
            m = msg.get("method")
            if isinstance(m, str) and m.startswith("Network."):
                self.events.append(msg)

    def start(self) -> "NetworkCapture":
        self.call("Network.enable", {"maxTotalBufferSize": 20000000})
        self._stop.clear()
        self._thread = threading.Thread(target=self._pump, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> list[dict[str, Any]]:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        try:
            self.call("Network.disable")
        except Exception:
            pass
        try:
            self.ws.close()
        except Exception:
            pass
        return self.events

    # ---- reduction: raw Network events -> the compiler's observed_effects shape
    def http_exchanges(self) -> list[dict[str, Any]]:
        """Turn captured events into `observed_effects.http_exchanges`.

        Only requests that actually MUTATE are interesting to a skill: POST/PUT/PATCH/DELETE.
        A GET is included only when it carried a form or set a cookie, because those steps are
        session state the replay needs.
        """
        reqs: dict[str, dict[str, Any]] = {}
        for ev in self.events:
            if ev.get("method") != "Network.requestWillBeSent":
                continue
            p = ev.get("params", {})
            rid = p.get("requestId")
            r = p.get("request", {})
            reqs[rid] = {
                "requestId": rid,
                "url": r.get("url"),
                "method": (r.get("method") or "GET").upper(),
                "headers": dict(r.get("headers") or {}),
                "postData": r.get("postData"),
                "type": p.get("type"),
            }
        statuses: dict[str, int] = {}
        for ev in self.events:
            if ev.get("method") == "Network.responseReceived":
                p = ev.get("params", {})
                statuses[p.get("requestId")] = int((p.get("response") or {}).get("status") or 0)

        out: list[dict[str, Any]] = []
        for rid, q in reqs.items():
            method = q["method"]
            if method in ("POST", "PUT", "PATCH", "DELETE"):
                ex: dict[str, Any] = {"url": q["url"], "method": method,
                                      "headers": _keep_headers(q["headers"])}
                body = _parse_body(q.get("postData"), q["headers"])
                if body is not None:
                    ex["form_body" if isinstance(body, dict) else "body"] = body
                ex["status"] = statuses.get(rid)
                out.append(ex)
            elif q.get("postData"):
                out.append({"url": q["url"], "method": method,
                            "headers": _keep_headers(q["headers"]),
                            "body": q["postData"], "status": statuses.get(rid)})
        return out


def _keep_headers(h: dict[str, str]) -> dict[str, str]:
    keep = {"content-type", "accept", "x-requested-with", "x-csrf-token"}
    return {k: v for k, v in h.items() if k.lower() in keep}


def _parse_body(post_data: str | None, headers: dict[str, str]):
    if not post_data:
        return None
    ctype = (headers.get("Content-Type") or headers.get("content-type") or "").lower()
    if "json" in ctype:
        try:
            return json.loads(post_data)
        except Exception:
            return post_data
    try:
        q = urllib.parse.parse_qs(post_data, keep_blank_values=True)
        if q:
            return {k: v[0] for k, v in q.items()}
    except Exception:
        pass
    return post_data
