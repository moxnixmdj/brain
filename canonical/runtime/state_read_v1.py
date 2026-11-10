"""A READ-ONLY state channel: observe the end state without looking at pixels.

WHY THIS EXISTS (r85). In r84 I classified 129 of 130 MiniWob families as having "no
code-readable terminal state". That was wrong, and the error was mine: MiniWob's own
scorer reads `WOB_DONE_GLOBAL` and `WOB_REWARD_GLOBAL` -- JavaScript globals -- through
`Runtime.evaluate`. The state was always readable as code. What made it unreadable was a
decision I took in r82: the vision channel forbids `Runtime.evaluate` so that a click
cannot become arbitrary script.

That decision is right for the ACT path and wrong for the VERIFY path. Reading cannot
cause an effect. So the two capabilities are split here:

    ACT    -> pixels and input events only (astra_hidden_visual_executor, unchanged)
    VERIFY -> typed, read-only state questions   (this module)

This is StateAct's state-grounding principle (arXiv 2607.22798): act on state where a
code path exists, verify on state, and keep the gate narration-blind -- it sees the
machine, never the agent's account of its work.

THE SAFETY RULE THAT MAKES THIS NOT A BACKDOOR
`Runtime.evaluate` is not exposed. The channel can ask only a fixed set of typed
questions about the DOM -- text of a node, presence of a node, count of rows -- and the
selector is data, never code. A read that could mutate is not expressible, so this module
cannot become an unguarded execution path even if its input is hostile.
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

# Only these methods may be used. No Input.*, no Page.navigate, no storage writes.
ALLOWED_METHODS = {"Runtime.enable", "Runtime.evaluate", "Page.enable", "Page.captureScreenshot",
                   "Emulation.setDeviceMetricsOverride"}

# The ONLY question shapes this channel can ask. Each is a template with a data-only
# selector. There is deliberately no template that assigns, calls, or navigates.
QUESTIONS: dict[str, str] = {
    # text of the first node matching a CSS selector
    "text_of": "(()=>{const e=document.querySelector(%s);return e?e.textContent:null})()",
    # how many nodes match
    "count_of": "(()=>{return document.querySelectorAll(%s).length})()",
    # list every matching node as {i, tag, id, text, visible} -- one call, no per-node
    # selectors. Added r85 because a legitimate CSS selector (":nth-of-type(1)") tripped the
    # data guard on parentheses. The fix is a wider QUESTION, never a looser guard.
    "list_of": ("(()=>{const out=[];const ns=document.querySelectorAll(%s);"
                "for(let i=0;i<ns.length&&i<60;i++){const e=ns[i];"
                "const r=e.getBoundingClientRect();"
                "out.push({i:i,tag:e.tagName,id:e.id||'',"
                "text:(e.innerText||e.value||'').slice(0,60).replace(/\\s+/g,' '),"
                "vis:r.width>0&&r.height>0});}return out})()"),
    # centre point of a node, in CSS pixels -- location reported by STRUCTURE, not pixels
    "centre_of": ("(()=>{const e=document.querySelector(%s);if(!e)return null;"
                  "const r=e.getBoundingClientRect();"
                  "return [r.x+r.width/2, r.y+r.height/2]})()"),
    # WHAT is actually at a point? The page answers, so a click that lands on an overlay
    # is detected instead of silently doing nothing (r85: typing went nowhere).
    "hit_at": ("(()=>{const e=document.elementFromPoint(%s,%s);"
               "return e?{tag:e.tagName,id:e.id,cls:e.className||'',"
               "z:getComputedStyle(e).zIndex} : null})()"),
    # the raw .value of a node -- list_of reports innerText||value, which HIDES a typed
    # value on an <input> because innerText is "" while value is not. That collapse is why
    # "input value now: ''" looked like typing had failed (r85).
    "value_of": "(()=>{const e=document.querySelector(%s);return e?(e.value===undefined?null:e.value):null})()",
    # is a node present and visible
    "visible_of": ("(()=>{const e=document.querySelector(%s);if(!e)return false;"
                   "const r=e.getBoundingClientRect();"
                   "return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'})()"),
}


class StateReadChannel:
    """Ask typed, read-only questions about a page's DOM. Cannot act."""

    ALLOWED_METHODS = ALLOWED_METHODS
    QUESTIONS = QUESTIONS

    def __init__(self, ws: Any, view: Sequence[int] = (320, 320)) -> None:
        self.ws = ws
        self.i = 0
        self.reads: list[str] = []
        self.call("Runtime.enable")
        self.call("Page.enable")
        self.call("Emulation.setDeviceMetricsOverride",
                  {"width": view[0], "height": view[1], "deviceScaleFactor": 1,
                   "mobile": False})

    def call(self, method: str, params: Mapping[str, Any] | None = None) -> Any:
        if method not in self.ALLOWED_METHODS:
            raise RuntimeError("STATE_READ_FORBIDDEN:" + method)
        self.i += 1
        rid = self.i
        self.ws.send(json.dumps({"id": rid, "method": method, "params": dict(params or {})},
                                separators=(",", ":")))
        while True:
            x = json.loads(self.ws.recv())
            if x.get("id") != rid:
                continue
            if "error" in x:
                raise RuntimeError("STATE_READ_ERROR:" + json.dumps(x["error"])[:200])
            return x.get("result", {})

    def ask(self, question: str, selector: str) -> Any:
        """Ask one typed question. `selector` is DATA; it is never executed as code."""
        if question not in self.QUESTIONS:
            raise RuntimeError("STATE_READ_UNKNOWN_QUESTION:" + question)
        if not _selector_is_data(selector):
            raise RuntimeError("STATE_READ_SELECTOR_NOT_DATA:" + selector[:80])
        expr = self.QUESTIONS[question] % json.dumps(selector)
        self.reads.append(f"{question}({selector})")
        res = self.call("Runtime.evaluate",
                        {"expression": expr, "returnByValue": True, "awaitPromise": False})
        return (res.get("result") or {}).get("value")

    def close(self) -> None:
        try:
            self.ws.close()
        except Exception:
            pass


def hit_at(channel: "StateReadChannel", x: float, y: float) -> Any:
    """What the page reports at a point. `hit_at` takes numbers, not a selector."""
    expr = channel.QUESTIONS["hit_at"] % (json.dumps(round(float(x), 1)), json.dumps(round(float(y), 1)))
    res = channel.call("Runtime.evaluate",
                       {"expression": expr, "returnByValue": True, "awaitPromise": False})
    return (res.get("result") or {}).get("value")


def centre_of(channel: "StateReadChannel", element_id: str) -> list[float] | None:
    """Where the page says a node is. Never a pixel measurement.

    Accepts "tt" or "#tt". The first version prefixed '#' unconditionally, so a caller
    passing "#tt" produced "##tt" -- an invalid selector, which querySelector rejects, so
    the read silently returned None and the click never happened (measured r87).
    """
    sel = element_id if element_id.startswith("#") else "#" + element_id
    return channel.ask("centre_of", sel)


def _selector_is_data(selector: str) -> bool:
    """Reject anything that could turn a selector into code.

    A CSS selector needs identifiers, classes, ids, attribute tests, and combinator
    punctuation. It never needs quotes-with-parens, semicolons, arrows, or assignment.
    """
    if not selector or len(selector) > 200:
        return False
    bad = (";", "=>", "(", ")", "{", "}", "=", "`", "\\", "eval", "function", "constructor")
    return not any(b in selector for b in bad)


# --------------------------------------------------------------------------- #
# Widget detection: a field may refuse free text and only accept a value chosen
# through its own calendar/list. Knowing that is what lets an actor choose a
# strategy instead of failing silently.
# --------------------------------------------------------------------------- #
WIDGET_QUESTION = (
    "(()=>{const e=document.querySelector(%s);if(!e)return null;"
    "const jq=window.jQuery;"
    "return {cls:String(e.className||''),"
    "hasDatepicker:!!(jq&&jq(e).data&&jq(e).data('datepicker')),"
    "type:String(e.type||''),readonly:!!e.readOnly}})()"
)


def widget_of(channel: "StateReadChannel", selector: str) -> Any:
    """What kind of widget is attached to this node? Read-only."""
    if not _selector_is_data(selector):
        raise RuntimeError("STATE_READ_SELECTOR_NOT_DATA:" + selector[:80])
    expr = WIDGET_QUESTION % json.dumps(selector)
    res = channel.call("Runtime.evaluate",
                       {"expression": expr, "returnByValue": True, "awaitPromise": False})
    return (res.get("result") or {}).get("value")
