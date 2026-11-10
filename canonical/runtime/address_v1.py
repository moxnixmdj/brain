"""Addressing by structure, deciding by vision.  The separation, and why it is the right one.

The problem this solves, measured last round:

    an empty text field cannot be located by appearance
    a 40x40 patch of the blank input matched 453 offsets spread over 258 pixels
    every threshold that accepts that is choosing a coin flip and calling it a match

Appearance is the wrong signal for a widget that has almost no appearance.  The page already
knows where its own fields are; the information exists and was being thrown away, because the
visual executor forbids DOM. and Accessibility. outright.

That ban was correct for one purpose and wrong for another, and the distinction is the whole
point of this file:

    DECIDING   what should I do next, and on which thing?     -> vision. A model reading a
               screenshot. If the page's tree chose this, the agent would be following
               instructions written by the page, which is how an agent gets steered by the
               thing it is operating on.

    ADDRESSING given that I must click "the filter field", where is it in pixels?  -> the
               page's own tree. There is no judgement here, only geometry.

So: this module may ask the page where things are.  It may never ask the page what to do, it
never returns anything but rectangles and roles, and the model is never shown the tree.  Every
method it uses is listed in ALLOWED_ADDRESSING and anything else raises.

This is also the honest correction of a mistake I made for several rounds: I kept trying to
recover structure from pixels, which is lossy by construction, while refusing to read the
structure that was sitting one CDP call away.
"""
from __future__ import annotations

import json
import urllib.request

SCHEMA = "ADDRESS_V1"

# The ONLY CDP domains this module may touch.  Reading layout and the accessibility tree is
# addressing.  Everything that could change the page, read values, or execute anything is
# absent by construction, not by a filter that might be bypassed.
ALLOWED_ADDRESSING = frozenset({
    "DOM.enable", "DOM.getDocument", "DOM.querySelectorAll", "DOM.getBoxModel",
    "DOM.describeNode", "Accessibility.enable", "Accessibility.getFullAXTree",
    "Page.getLayoutMetrics", "Page.enable",
})

# The ban the visual executor keeps, restated here so the two cannot drift apart:
DECISION_DOMAINS = frozenset({"Runtime", "Debugger", "CSS", "Profiler", "Schema", "Input",
                              "Page.navigate", "Page.captureScreenshot"})


class AddressingError(RuntimeError):
    pass


class Address:
    """A CDP client that can only look, and only at layout."""

    def __init__(self, ws: str):
        import websocket
        self.ws = websocket.create_connection(ws, timeout=20,
                                              origin="http://127.0.0.1:9222")
        self.i = 0
        self.sent: list[str] = []

    def call(self, method: str, params: dict | None = None) -> dict:
        if method not in ALLOWED_ADDRESSING:
            raise AddressingError(f"NOT_ADDRESSING__{method}")
        self.i += 1
        rid = self.i
        self.sent.append(method)
        self.ws.send(json.dumps({"id": rid, "method": method, "params": params or {}},
                                separators=(",", ":")))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") != rid:
                continue
            if "error" in msg:
                raise AddressingError("CDP_ERROR:" + json.dumps(msg["error"]))
            return msg.get("result", {})

    def close(self) -> None:
        try:
            self.ws.close()
        except Exception:
            pass


def target_url(port: int = 9222) -> str:
    pages = [t for t in json.loads(
        urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5).read())
        if t.get("type") == "page"]
    if not pages:
        raise AddressingError("NO_PAGE_TARGET")
    return pages[0]["webSocketDebuggerUrl"]


def _backend_id(address: Address, selector: str) -> int | None:
    doc = address.call("DOM.getDocument", {"depth": 0})
    nodes = address.call("DOM.querySelectorAll", {"nodeId": doc["root"]["nodeId"],
                                                  "selector": selector})
    ids = nodes.get("nodeIds") or []
    return ids[0] if ids else None


def boxes(address: Address, selector: str) -> list[dict]:
    """Every element matching `selector`, as rectangles.  Geometry only."""
    doc = address.call("DOM.getDocument", {"depth": 0})
    ids = address.call("DOM.querySelectorAll", {"nodeId": doc["root"]["nodeId"],
                                                "selector": selector}).get("nodeIds") or []
    out = []
    for nid in ids:
        try:
            m = address.call("DOM.getBoxModel", {"nodeId": nid})["model"]
        except AddressingError:
            continue
        q = m["content"]
        xs, ys = q[0::2], q[1::2]
        out.append({"x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys),
                    "w": max(xs) - min(xs), "h": max(ys) - min(ys)})
    return out


def ax_nodes(address: Address) -> list[dict]:
    """The accessibility tree, flattened to what addressing needs: role, name, geometry."""
    address.call("Accessibility.enable")
    tree = address.call("Accessibility.getFullAXTree").get("nodes", [])
    out = []
    for n in tree:
        role = (n.get("role") or {}).get("value")
        name = (n.get("name") or {}).get("value")
        bid = n.get("backendDOMNodeId")
        if not role or bid is None:
            continue
        if role in {"generic", "none", "InlineTextBox", "StaticText", "RootWebArea"}:
            continue
        box = None
        try:
            m = address.call("DOM.getBoxModel", {"backendNodeId": bid})["model"]
            q = m["content"]
            xs, ys = q[0::2], q[1::2]
            box = {"x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys),
                   "w": max(xs) - min(xs), "h": max(ys) - min(ys)}
        except AddressingError:
            box = None
        out.append({"role": str(role), "name": str(name or ""), "box": box})
    return out


def find(address: Address, role: str | None = None, name: str | None = None) -> dict | None:
    """The first element with this role and/or accessible name, as a rectangle and a centre."""
    for n in ax_nodes(address):
        if role and role.lower() not in n["role"].lower():
            continue
        if name and name.lower() not in n["name"].lower():
            continue
        if not n["box"]:
            continue
        b = n["box"]
        return {"role": n["role"], "name": n["name"], "box": b,
                "x": int((b["x0"] + b["x1"]) // 2), "y": int((b["y0"] + b["y1"]) // 2)}
    return None


def describe_target(role: str | None = None, name: str | None = None) -> dict:
    """The stable ADDRESS a demonstration should keep for a widget: role + name, not pixels."""
    return {"schema": SCHEMA, "role": role, "name": name}
