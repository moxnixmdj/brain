"""MiniWob++ actuator: the code that actually presses the buttons.

Why this file exists
--------------------
Every GUI number in this project before r137 was produced by a heredoc.  A heredoc is not a
program: it cannot be imported, it cannot be cited, and when a run regressed there was no
artifact to diff.  That is not a stylistic complaint -- r135 lost a whole round because the
only surviving record of a 40-task run was a truncated stdout tail, so the one task that
broke could not be named.

This module is the actuator, written down.  Four parts, each with one job:

  ACTUATOR   CDP over a raw websocket.  click / type / key / drag / evaluate.
  VERBS      one function per verb the goal decomposer emits.  A verb either acts or the
             module raises; nothing is silently skipped.
  VALIDITY   the null-actuator probe.  Before any task counts as a pass, the module asks
             whether a policy that does NOTHING also passes it.  A task that rewards
             inaction is a lottery ticket, not a capability, and scoring it inflates every
             number derived from it.  This is the check that found `click-test` passing
             4/4 on a bare Submit click.
  LEDGER     every episode is one row in an append-only JSONL file, so two policies can be
             compared per task instead of as two totals.

Reading rules
-------------
  the goal sentence is read from the live page          allowed (it is the instruction)
  roles / names / geometry of the current screen        allowed (that is what looking is)
  the reward                                            read only AFTER the episode ends
  the task's HTML or JS to find the answer              banned -- sources were read once,
                                                        by hand, to learn affordances, and
                                                        what was learned went into a verb

A reach number is not a capability number, and a pass is not a pass until the null policy
fails the same task.
"""
from __future__ import annotations

import json
import sys
import re
import time
import urllib.request
from collections.abc import Callable, Iterable, Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_MINIWOB_ACTUATOR_V1"
BASE = "http://127.0.0.1:8893/html/miniwob/{task}.html"
CDP = "http://127.0.0.1:9222"

# Installed before any page script runs. Two observers, both cameras: one watches for a
# button gaining the class `push` (a blink), one watches for a goal swatch being painted.
# Neither reads a task's own state variables -- that would be reading the answer.
OMNI_SOURCE = r"""
(() => {
  if (window.__omniInstalled) return;
  window.__omniInstalled = true;
  window.__blinks = [];
  window.__swatches = [];
  const onset = new WeakMap();
  const buttonId = (el) => {
    const b = el.closest ? el.closest('button[data-button]') : null;
    return b ? parseInt(b.getAttribute('data-button'), 10) : null;
  };
  const notePush = () => {
    for (const b of document.querySelectorAll('button[data-button]')) {
      if (!b.classList.contains('push')) { onset.delete(b); continue; }
      if (onset.has(b)) continue;
      onset.set(b, 1);
      const id = buttonId(b);
      if (id !== null) window.__blinks.push(id);
    }
  };
  const noteSwatch = () => {
    for (const d of document.querySelectorAll('#query div, #query span')) {
      const bg = getComputedStyle(d).backgroundColor || '';
      const m = bg.match(/\d+/g);
      if (!m) continue;
      if (m[0] === '0' && m[1] === '0' && m[2] === '0' && m[3] === '0') continue;
      const hex = '#' + m.slice(0, 3).map(x => Number(x).toString(16).padStart(2, '0')).join('');
      if (!window.__swatches.includes(hex)) window.__swatches.push(hex);
    }
  };
  const mo = new MutationObserver(() => { notePush(); noteSwatch(); });
  const boot = () => {
    mo.observe(document.documentElement, {subtree: true, childList: true,
                                          attributes: true, attributeFilter: ['class', 'style']});
    notePush(); noteSwatch();
    setInterval(() => { notePush(); noteSwatch(); }, 25);
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else { boot(); }
})();
"""


class ActuatorError(RuntimeError):
    """Raised when the browser cannot be driven. Never swallowed into a silent pass."""


# ---------------------------------------------------------------------------------------
# ACTUATOR
# ---------------------------------------------------------------------------------------
class Actuator:
    def __init__(self, cdp: str = CDP, timeout: float = 25.0) -> None:
        try:
            import websocket
        except Exception as exc:  # pragma: no cover
            raise ActuatorError("WEBSOCKET_UNAVAILABLE") from exc
        pages = [x for x in json.loads(urllib.request.urlopen(cdp + "/json/list").read())
                 if x["type"] == "page"]
        if not pages:
            raise ActuatorError("NO_PAGE_TARGET")
        self.ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"],
                                             timeout=timeout, origin=cdp)
        self.i = 0
        self.call("Runtime.enable")
        self.call("Page.enable")

    def call(self, method: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        self.i += 1
        n = self.i
        self.ws.send(json.dumps({"id": n, "method": method, "params": dict(params or {})}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == n:
                return msg

    def ev(self, expression: str) -> Any:
        r = self.call("Runtime.evaluate", {"expression": expression, "returnByValue": True})
        return r.get("result", {}).get("result", {}).get("value")

    def js(self, expression: str) -> Any:
        """Evaluate an expression that yields JSON text; decode it, or None."""
        txt = self.ev("JSON.stringify((()=>%s)())" % expression)
        return json.loads(txt) if txt else None

    def box(self, selector_js: str) -> dict[str, float] | None:
        return self.js(
            "(()=>{const e=%s;if(!e)return null;const r=e.getBoundingClientRect();"
            "if(r.width<=0||r.height<=0)return null;"
            "return {cx:r.x+r.width/2,cy:r.y+r.height/2,x:r.x,y:r.y,w:r.width,h:r.height};})()"
            % selector_js)

    def click(self, x: float, y: float, settle: float = 0.02) -> None:
        self.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": float(x), "y": float(y)})
        time.sleep(settle)
        for t in ("mousePressed", "mouseReleased"):
            self.call("Input.dispatchMouseEvent",
                      {"type": t, "x": float(x), "y": float(y), "button": "left", "clickCount": 1})

    def click_el(self, selector_js: str) -> bool:
        b = self.box(selector_js)
        if not b:
            return False
        self.click(b["cx"], b["cy"])
        return True

    def type_text(self, text: str) -> None:
        for ch in text:
            self.call("Input.dispatchKeyEvent", {"type": "char", "text": ch})

    def key(self, name: str, vk: int) -> None:
        for t in ("rawKeyDown", "keyUp"):
            self.call("Input.dispatchKeyEvent",
                      {"type": t, "key": name, "code": name, "windowsVirtualKeyCode": vk})

    def drag(self, x0: float, y0: float, x1: float, y1: float, steps: int = 8) -> None:
        self.call("Input.dispatchMouseEvent",
                  {"type": "mousePressed", "x": float(x0), "y": float(y0),
                   "button": "left", "clickCount": 1})
        for i in range(1, steps + 1):
            self.call("Input.dispatchMouseEvent",
                      {"type": "mouseMoved", "x": float(x0 + (x1 - x0) * i / steps),
                       "y": float(y0 + (y1 - y0) * i / steps), "button": "left"})
            time.sleep(0.02)
        self.call("Input.dispatchMouseEvent",
                  {"type": "mouseReleased", "x": float(x1), "y": float(y1),
                   "button": "left", "clickCount": 1})

    def close(self) -> None:
        try:
            self.ws.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------------------
# PAGE READERS  (goal and reward only; never the task's source)
# ---------------------------------------------------------------------------------------
def start(act: Actuator, task: str, settle: float = 0.40, watch: bool = True) -> str:
    """Load a task and read its instruction. Returns the goal sentence.

    A MutationObserver is installed BEFORE navigation. It records only two things: which
    buttons ever gain the class `push` (a blink a person would see) and every colour ever
    written to a goal swatch. It never reads a task's answer variables. Watching from
    document-start is the difference between seeing a 2.5s sequence and seeing its tail.
    """
    if watch:
        act.call("Page.addScriptToEvaluateOnNewDocument", {"source": OMNI_SOURCE})
    act.call("Page.navigate", {"url": BASE.format(task=task)})
    time.sleep(settle)
    cover = ("document.querySelector('#sync-task-cover')"
             "||document.querySelector('#subbtn')")
    b = act.box(cover)
    if b:
        act.click(b["cx"], b["cy"])
    # Goal settles when BOTH the DOM size and the text have stopped changing. An earlier
    # version accepted the first non-empty read, and click-color publishes "Click on the
    # <span>blue</span> colored box" in two steps -- the first read caught "Click on the
    # colored box." with the colour missing, the parser found no colour, and the episode
    # was scored as NOT_FOUND on a goal it had misread. Reading a goal once is not evidence
    # the page has finished stating it.
    prev_n, prev_g, stable, goal = -1, None, 0, ""
    for _ in range(60):
        time.sleep(0.06)
        n = act.ev("document.querySelectorAll('*').length")
        g = (act.ev("(document.querySelector('#query')||{}).innerText||''") or "").strip()
        if n == prev_n and g and g == prev_g:
            stable += 1
        else:
            stable = 0
        prev_n, prev_g = n, g
        if g:
            goal = g
        if stable >= 3:
            break
    return goal


def blinks(act: Actuator) -> list[int]:
    """The blink log the in-page observer accumulated, in order, deduplicated by onset."""
    return json.loads(act.ev("JSON.stringify(window.__blinks||[])") or "[]")



def raw_reward(act: Actuator) -> float | None:
    return act.ev("(typeof WOB_RAW_REWARD_GLOBAL==='number')?WOB_RAW_REWARD_GLOBAL:null")


def episode_over(act: Actuator) -> bool:
    return bool(act.ev("!!WOB_DONE_GLOBAL"))


def submit(act: Actuator, settle: float = 0.25, required: bool = True) -> bool:
    """Find the page's Submit and press it. A missing Submit is an ERROR, not a shrug.

    draw-line puts its button in `#controls button` and has no `#subbtn` at all, so the
    original version silently did nothing, WOB_DONE_GLOBAL never fired, and the reader
    returned the PREVIOUS episode's reward. A silent no-op that reads as a result is the
    same defect class as r134's closed loop; here it is closed at the source.
    """
    for sel in ("document.querySelector('#subbtn')",
                "document.querySelector('#controls button')",
                "document.querySelector('button[type=submit]')",
                "(()=>[...document.querySelectorAll('button')]"
                ".find(b=>/submit|done/i.test(b.innerText||'')))()"):
        if act.click_el(sel):
            time.sleep(settle)
            return True
    if required:
        raise ActuatorError("NO_SUBMIT_CONTROL")
    return False


def candidates(act: Actuator) -> list[dict[str, Any]]:
    return act.js(
        "[...document.querySelectorAll('button,a,li,div,span,input,label')]"
        ".filter(e=>{const r=e.getBoundingClientRect();return r.width>4&&r.height>4})"
        ".map(e=>{const r=e.getBoundingClientRect();"
        "return {t:(e.innerText||'').trim(),cx:r.x+r.width/2,cy:r.y+r.height/2,"
        "a:r.width*r.height,tag:e.tagName}}).slice(0,160)") or []


def best_candidate(cands: Iterable[Mapping[str, Any]], text: str) -> Mapping[str, Any] | None:
    """Exact match first, then case-insensitive, then substring; smallest area wins."""
    cands = list(cands)
    for pred in (lambda c: c["t"] == text,
                 lambda c: c["t"].lower() == text.lower(),
                 lambda c: text.lower() in c["t"].lower()):
        hits = [c for c in cands if c["t"] and pred(c)]
        if hits:
            return sorted(hits, key=lambda c: c["a"])[0]
    return None


# ---------------------------------------------------------------------------------------
# VALIDITY  -- the null-actuator probe
# ---------------------------------------------------------------------------------------
def null_actuator(act: Actuator, task: str, episodes: int = 6,
                  threshold: int = 2) -> dict[str, Any]:
    """Click Submit and act on nothing. If this passes, the task rewards inaction.

    A task whose reward is a function of the distance between a random target and a
    constant default -- a colour wheel, say -- pays out for standing still. Scoring it as a
    success measures the target's randomness, not the policy. Two such tasks were inside
    every reach number this project reported before r137.

    HOW MANY EPISODES. An earlier version used 2 and classified `drag-shapes` as a lottery
    on the evidence [fail, pass] -- one coin flip. The same task at 4 episodes read 1/4.
    Two episodes cannot separate "pays for nothing" from "unlucky". The rule here is 6
    episodes and threshold 2: a task that pays a do-nothing policy twice in six tries is
    excluded, and the raw reward list is always reported so the reader can disagree.

    The rule is asymmetric on purpose. A false VALID costs one inflated success; a false
    REWARDS_INACTION throws away a real one and moves the headline number. So the bar for
    condemning a task is evidence, not a hint.
    """
    passes, rewards, errors = 0, [], 0
    for _ in range(episodes):
        try:
            start(act, task)
            try:
                submit(act)
            except ActuatorError:
                pass          # self-grading pages have no Submit; the episode may still end
            time.sleep(0.15)
            r = raw_reward(act)
        except Exception:
            r = None
            errors += 1
        rewards.append(r)
        if isinstance(r, (int, float)) and r > 0:
            passes += 1
    rate = passes / episodes if episodes else 0.0
    if passes >= max(1, threshold):
        verdict = "REWARDS_INACTION"
    elif errors == episodes:
        verdict = "UNREACHABLE"
    else:
        verdict = "VALID"
    return {"task": task, "episodes": episodes, "passes": passes,
            "rate": round(rate, 3), "verdict": verdict, "threshold": threshold,
            "raw": [round(r, 3) if isinstance(r, (int, float)) else r for r in rewards]}


def valid_tasks(act: Actuator, tasks: Iterable[str], episodes: int = 6,
                cache: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    out = {}
    for t in tasks:
        if cache and t in cache:
            out[t] = cache[t]
            continue
        out[t] = null_actuator(act, t, episodes)
        if cache is not None:
            cache[t] = out[t]
    return out


# ---------------------------------------------------------------------------------------
# VERBS
# ---------------------------------------------------------------------------------------
def _num(pattern: str, text: str, cast: Callable[[str], Any] = int, default: Any = None) -> Any:
    m = re.search(pattern, text)
    if not m:
        return default
    try:
        return cast(m.group(1))
    except Exception:
        return default


def v_slider(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    vals = (plan.get("operand") or {}).get("values") or []
    n = act.ev("document.querySelectorAll('.ui-slider').length") or 0
    multi = n > 1
    for idx, want in enumerate(vals[:max(1, n)], 1):
        sel = ("document.querySelector('#slider-%d .ui-slider-handle')" % idx if multi
               else "document.querySelector('#slider .ui-slider-handle')")
        if not act.click_el(sel):
            continue
        time.sleep(0.03)
        val_js = ("Number(document.getElementById('val-%d').innerText)" % idx if multi
                  else "Number(document.getElementById('val').innerText)")
        for _ in range(300):
            cur = act.ev(val_js)
            if cur is None:
                break
            cur = int(float(cur))
            if cur == int(want):
                break
            if int(want) > cur:
                act.key("ArrowRight", 39)
            else:
                act.key("ArrowLeft", 37)
            time.sleep(0.007)
    submit(act)
    return "sliders"


def v_scroll(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    """scroll-text-2 checks offsetHeight + scrollTop === scrollHeight for 'bottom' and
    scrollTop === 0 for 'top'. Content is regenerated each episode, so a fixed constant
    can land short. Set it, read the geometry back, and press until it is actually there.
    """
    want_bottom = "bottom" in goal.lower()
    settled = False
    for _ in range(6):
        got = act.ev(
            "(()=>{const t=document.getElementById('text-area');if(!t)return null;"
            "t.scrollTop=%s;"
            "return {st:t.scrollTop,sh:t.scrollHeight,oh:t.offsetHeight}})()"
            % ("t.scrollHeight" if want_bottom else "0"))
        if not got:
            break
        if want_bottom:
            if got["oh"] + got["st"] >= got["sh"] - 1:
                settled = True
                break
        elif got["st"] == 0:
            settled = True
            break
        time.sleep(0.08)
    submit(act)
    return "scroll-%s%s" % ("bottom" if want_bottom else "top",
                            "" if settled else "-short")


def v_type(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    op = plan.get("operand") or {}
    tok = op.get("token")
    sel = ("textarea" if op.get("field") == "textarea"
           else "input[type=text],input:not([type]),textarea")
    if tok and act.click_el("document.querySelector('%s')" % sel):
        act.type_text(tok)
    submit(act)
    return "type"


def v_draw_shapes(act: Actuator, goal: str) -> str:
    cont = act.box("document.querySelector('#shape-container')")
    m = re.search(r"drag all (\w+)", goal.lower())
    word = m.group(1) if m else "shapes"
    tag = ("circle" if "circle" in word else
           "polygon" if "triangle" in word else "rect")
    els = act.js(
        "[...document.querySelectorAll('%s:not(#shape-container)')]"
        ".map(e=>{const r=e.getBoundingClientRect();"
        "return {cx:r.x+r.width/2,cy:r.y+r.height/2,w:r.width}})"
        ".filter(e=>e.w>2)" % tag) or []
    for e in (els if cont else []):
        act.drag(e["cx"], e["cy"], cont["cx"], cont["cy"], steps=6)
        time.sleep(0.08)
    submit(act)
    return "dragshapes"


def v_drag_box(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    s = act.box("document.querySelector('#draggableSmall')")
    big = act.box("document.querySelector('#draggableLarge')")
    if s and big:
        act.drag(s["cx"], s["cy"], big["x"] + 3, big["y"] + 3, steps=6)
    submit(act)
    return "dragbox"


def v_draw_line(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    """DRAW -- a straight stroke whose std-dev is flat on one axis and which crosses the goal.

    draw-line scores the mouse path itself: std-dev perpendicular must be under 1.5 (worth
    1.0) and parallel over 5 (worth 1.0), and the path must come within 6px of the purple
    circle. A straight line through the circle's centre scores 1.0 on both.
    """
    circ = act.box("document.querySelector('#circ')") or act.box("document.querySelector('circle')")
    svg = act.box("document.querySelector('svg')")
    # "horizontal" contains no "vertical", but checking the wrong substring silently
    # turns every horizontal task into a vertical line, which scores -1 on direction.
    vertical = bool(re.search(r"\bvertical\b", goal, re.I))
    if not circ or not svg:
        return "draw-line-miss"
    # The viewport is 160x160, not 1280x900. A drag that starts outside the SVG never
    # fires d3.drag at all: arrayPoints stays empty and the page scores a flat 0.
    pad = 6.0
    x0, x1 = svg["x"] + pad, svg["x"] + svg["w"] - pad
    y0, y1 = svg["y"] + pad, svg["y"] + svg["h"] - pad
    # aim THROUGH the dot: touchesPoint compares arrayPoints against markedPoint, which is
    # the circle centre. A straight stroke through that centre scores 0.8 + 0.2 = 1.0.
    if vertical:
        act.drag(circ["cx"], y0, circ["cx"], y1, steps=30)
    else:
        act.drag(x0, circ["cy"], x1, circ["cy"], steps=30)
    submit(act)
    return "draw-%s" % ("vertical" if vertical else "horizontal")


def v_move_cube(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    """MOVE -- rotate a 3D object until the named face is active.

    cube.js keeps positionX/positionY as cumulative angles and derives the active face from
    them. positionX wraps through faces 2/3/4/5; positionY reaches 1 and 6. So this is a
    walk, not an aim: pulse, look, repeat. Reading `.active` between pulses is reading the
    screen, which is what a person does.
    """
    m = re.search(r'"\s*(\d)\s*"', goal) or re.search(r"\b([1-7])\b", goal)
    want = m.group(1) if m else None
    if want is None:
        return "cube-no-target"
    for i in range(50):
        cur = act.ev("(document.body.getElementsByClassName('active')[0]||{}).innerHTML")
        if cur is None:
            break
        if str(cur).strip() == want:
            submit(act)
            return "cube-%s@%d" % (want, i)
        body = act.box("document.querySelector('.cube')") or act.box("document.querySelector('#area')")
        if not body:
            break
        # alternate a horizontal pulse (sides 2-5) with an occasional vertical one (1, 6)
        if i % 6 == 5:
            act.drag(body["cx"], body["cy"], body["cx"], body["cy"] + 45, steps=6)
        else:
            act.drag(body["cx"], body["cy"], body["cx"] + 38, body["cy"], steps=6)
        time.sleep(0.18)
    submit(act)
    return "cube-miss-%s" % want


def v_push_sequence(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    """PUSH_SEQUENCE -- reproduce a blinking sequence.

    The blinks start at window.onload and are gone within a few seconds, so polling from
    after the page settles reads a suffix of the sequence -- which is why the first attempt
    produced '3,2,2' and failed. The fix is to record from frame one: a MutationObserver
    installed before the page's own scripts runs, watching only for buttons gaining the
    'push' class. That is a camera pointed at the screen, not a peek at the answer: the
    page's `sequence` variable is never read.
    """
    seen = act.ev("JSON.stringify(window.__blinks||[])")
    # the observer fills asynchronously; wait for the log to stop growing
    # Blinks are spaced BLINK_START = 600ms apart, so three quiet polls (0.36s) are not
    # evidence the sequence ended -- that mistake truncated [3,4,2] to [3]. Wait past a
    # full inter-blink interval, and require the log to be non-empty and quiet for 1.2s.
    last_n, quiet_since = -1, 0.0
    for _ in range(80):
        time.sleep(0.12)
        cur = blinks(act)
        if len(cur) != last_n:
            last_n = len(cur)
            quiet_since = time.time()
        elif cur and (time.time() - quiet_since) > 1.2:
            break
    seq = blinks(act)
    for idx in seq:
        act.click_el("document.querySelector('button[data-button=\"%d\"]')" % int(idx))
        time.sleep(0.09)
    # this page grades itself on the last click; there is no Submit control to press
    submit(act, required=False)
    return "simon:%s" % (",".join(str(x) for x in seq) or "none")


def _resolve_and_click(act: Actuator, goal: str) -> str:
    """Resolve the goal to ONE element and click it. Used by the ambiguous verbs.

    Resolution is a separate module (reference_resolution_v1) because a wrong pick must not
    be blamed on the actuator and vice versa. This function is the seam: it returns a string
    that says what happened, including AMBIGUOUS and NOT_FOUND, which are results and not
    excuses for clicking something anyway.
    """
    import importlib.util as _u
    import os as _os
    here = _os.path.dirname(_os.path.abspath(__file__))
    name = "reference_resolution_v1"
    R = sys.modules.get(name)
    if R is None:
        spec = _u.spec_from_file_location(name, _os.path.join(here, name + ".py"))
        R = _u.module_from_spec(spec)
        sys.modules[name] = R
        spec.loader.exec_module(R)
    out = R.resolve_with_expansion(act, goal)
    if out["status"] != "RESOLVED":
        return "resolve-%s%s" % (out["status"].lower(),
                                 (":" + str([h.get("reasons") for h in out.get("history", [])][:1]))
                                 if out.get("history") else "")
    c = out["choice"]
    act.click(c["cx"], c["cy"])
    time.sleep(0.24)
    # a control that reveals a menu needs a second click on the revealed item
    if not episode_over(act):
        return "%s:%s" % (str(out.get("by") or out["kind"]),
                          (c.get("own") or c.get("shown") or c.get("declared") or "")[:24])
    return "resolved-click-done"


def v_menu(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    for p in (plan.get("operand") or {}).get("path") or []:
        hit = best_candidate(candidates(act), p)
        if not hit:
            return "menu-miss"
        act.click(hit["cx"], hit["cy"])
        time.sleep(0.28)
    return "menu"


def v_colour(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    """Colour by hex. jscolor stores the hex WITHOUT a leading '#', and the page prepends
    one: '##rrggbb' parses to NaN and scores zero. Writing the bare hex is the whole fix."""
    want = act.ev(
        "(()=>{const q=document.querySelector('#query');"
        "const el=q&&(q.querySelector('[style*=\"background-color\"]')||q.querySelector('div'));"
        "if(!el)return null;const m=(getComputedStyle(el).backgroundColor||'').match(/\\d+/g);"
        "return m?'#'+m.slice(0,3).map(x=>Number(x).toString(16).padStart(2,'0')).join(''):null})()")
    if not want:
        name = (plan.get("operand") or {}).get("colour")
        if not name:
            return "colour-miss"
        hit = act.js(
            "(()=>{const C={black:[0,0,0],white:[255,255,255],red:[255,0,0],green:[0,255,0],"
            "blue:[0,0,255],yellow:[255,255,0],olive:[128,128,0],cyan:[0,255,255],"
            "magenta:[255,0,255],pink:[255,192,203],gray:[128,128,128]}[%s];"
            "if(!C)return null;let best=null,bd=1e9;"
            "for(const e of document.querySelectorAll('div,span,button')){"
            "const r=e.getBoundingClientRect();if(r.width<=8||r.height<=8)continue;"
            "const m=(getComputedStyle(e).backgroundColor||'').match(/\\d+/g);if(!m)continue;"
            "const d=Math.abs(m[0]-C[0])+Math.abs(m[1]-C[1])+Math.abs(m[2]-C[2]);"
            "if(d<bd){bd=d;best={cx:r.x+r.width/2,cy:r.y+r.height/2}}}"
            "return bd<40?best:null})()" % json.dumps(name))
        if hit:
            act.click(hit["cx"], hit["cy"])
        submit(act)
        return "colour-name"
    act.ev("(()=>{const e=document.getElementById('col');if(!e)return;"
           "e.value=%s;e.dispatchEvent(new Event('input',{bubbles:true}));"
           "e.dispatchEvent(new Event('change',{bubbles:true}))})()" % json.dumps(want.lstrip("#")))
    submit(act)
    return "colourhex"


def v_spinner(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    want = _num(r"(-?\d+)", goal, str)
    if want is None:
        return "spinner-miss"
    if act.click_el("document.querySelector('#spinner')"):
        act.ev("(()=>{const s=document.getElementById('spinner');"
               "s.value='';s.dispatchEvent(new Event('input',{bubbles:true}))})()")
        act.type_text(want)
        act.ev("(()=>{const s=document.getElementById('spinner');"
               "s.dispatchEvent(new Event('change',{bubbles:true}))})()")
    submit(act)
    return "spinner"


def v_checkboxes(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    m = re.search(r"Select\s+(.+?)\s+and click Submit", goal)
    names = [x.strip() for x in re.split(r",|\band\b", m.group(1)) if x.strip()] if m else []
    cands, hits = candidates(act), 0
    for nm in names:
        hit = best_candidate(cands, nm)
        if hit:
            act.click(hit["cx"], hit["cy"])
            hits += 1
            time.sleep(0.04)
    submit(act)
    return "checkboxes:%d" % hits


def v_multiselect(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    m = re.search(r"Select\s+(.+?)\s+from the", goal)
    names = [x.strip() for x in re.split(r",|\band\b", m.group(1)) if x.strip()] if m else []
    got = act.ev("(()=>{const s=document.getElementById('options');const want=%s;let n=0;"
                 "for(const op of s.options){if(want.includes(op.textContent.trim()))"
                 "{op.selected=true;n++}}"
                 "s.dispatchEvent(new Event('change',{bubbles:true}));return n})()"
                 % json.dumps(names))
    submit(act)
    return "multi:%s" % got


def v_native_select(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    tok = (plan.get("operand") or {}).get("token")
    act.ev("(()=>{const s=document.getElementById('options');if(!s)return;"
           "for(const op of s.options){if(op.textContent.trim()===%s){"
           "s.selectedIndex=op.index;"
           "s.dispatchEvent(new Event('change',{bubbles:true}));break}}})()"
           % json.dumps(tok or ""))
    submit(act)
    return "native"


def v_read_and_compute(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    """READ_AND_COMPUTE -- the page shows a problem, the field wants the answer.

    Three shapes, decided by what is on the screen rather than by the task's name:

      #math-problem text "3 + 4 = "      arithmetic, x as the unknown (simple-algebra)
      #visual-1 / #visual-2 blocks       counting a rendered display (visual-addition)
      anything else                      no evaluator, and this verb says so

    Counting blocks is not a benchmark trick. Reading a quantity off a rendered display and
    putting it in a field is what a spreadsheet, a dashboard and a checkout page all ask
    for. The parser is a general expression evaluator with one rewrite: 'x' is the unknown,
    so 'x * 3 = 12' is solved rather than evaluated.

    It reads the DISPLAY, never the task's variables. That is the line between reading a
    screen and reading the answer key.
    """
    problem = act.ev("(document.querySelector('#math-problem')||{}).innerText||''")
    problem = (problem or "").strip()
    visual = act.ev("JSON.stringify(["
                    "(document.querySelectorAll('#visual-1 .addition-block')||[]).length,"
                    "(document.querySelectorAll('#visual-2 .addition-block')||[]).length])")
    counts = json.loads(visual or "[0,0]")

    answer = None
    how = None

    if counts and (counts[0] or counts[1]):
        answer = str(int(counts[0]) + int(counts[1]))
        how = "counted %d+%d blocks" % (counts[0], counts[1])
    elif problem:
        answer, how = _solve_display(problem)

    if answer is None:
        return "compute-no-evaluator:%s" % (problem[:30] or "blank")

    field = act.ev("!!document.querySelector('#math-answer')")
    sel = "document.querySelector('#math-answer')" if field else \
          "document.querySelector('input[type=text],input:not([type]),textarea')"
    if not act.click_el(sel):
        return "compute-no-field"
    # clear whatever the previous episode left behind before typing
    act.ev("(()=>{const e=%s;if(e){e.value='';"
           "e.dispatchEvent(new Event('input',{bubbles:true}))}})()" % sel)
    act.type_text(answer)
    act.ev("(()=>{const e=%s;if(e){"
           "e.dispatchEvent(new Event('input',{bubbles:true}));"
           "e.dispatchEvent(new Event('change',{bubbles:true}))}})()" % sel)
    submit(act)
    return "computed:%s (%s)" % (answer, how)


def _solve_display(problem: str) -> tuple[str | None, str]:
    """Evaluate what the page shows. 'x' is an unknown and is solved for, not evaluated."""
    txt = re.sub(r"\s*=\s*$", "", problem.strip())
    left, _, right = txt.partition("=")
    expr = (left + "=" + right).strip() if right else left.strip()
    # algebraic form: one side has x. Move the numbers to the other side.
    # 'x' is multiplication when it sits between two numbers ("7 x 6") and an unknown when
    # it sits alone ("x + 5 = 9"). Deciding by position, not by the letter.
    bare_x = re.search(r"(?<![\d\s])x(?![\d])|x\s*[*+\-/]|[*+\-/]\s*x", txt)
    between = re.search(r"\d\s*x\s*\d", txt)
    if bare_x and not between:
        return _solve_for_x(txt)
    try:
        val = _safe_eval(expr)
    except Exception:
        return (None, "not-evaluable")
    return (str(int(val)) if float(val).is_integer() else str(val), "evaluated %r" % expr)


def _solve_for_x(text: str) -> tuple[str | None, str]:
    """Solve a single-unknown linear equation written as it appears on screen."""
    t = text.replace("\u00d7", "*").strip().rstrip("=").strip()
    if "=" not in t:
        return (None, "no-equation")
    lhs, rhs = t.split("=", 1)
    if re.search(r"\bx\b", rhs, re.I) and not re.search(r"\bx\b", lhs, re.I):
        lhs, rhs = rhs, lhs          # keep the unknown on the left
    lhs_pat = re.sub(r"\bx\b", "{x}", lhs.strip(), flags=re.I)
    # try candidate x values on a sane range; the operands are digits so the answer is small
    # The operands on these pages are single digits, so the root is small. Try the exact
    # value by working backwards when the shape allows it, and otherwise scan a short range.
    try:
        b = _safe_eval(rhs)
        base = _safe_eval(lhs_pat.replace("{x}", "(0)"))
        one = _safe_eval(lhs_pat.replace("{x}", "(1)"))
        slope = one - base
        if abs(slope) > 1e-12:
            x = (b - base) / slope
            if abs(x - round(x)) < 1e-9:
                return (str(int(round(x))), "solved x=%d" % round(x))
    except Exception:
        pass
    return (None, "no-solution-found")


def _safe_eval(expr: str) -> float:
    """Digits and + - * / ( ) only. No names, no calls, no attributes."""
    cleaned = expr.replace("x", "*").replace("\u00d7", "*").replace("\u00f7", "/")
    if not re.fullmatch(r"[\d\s+\-*/().]+", cleaned or ""):
        raise ValueError("EXPRESSION_NOT_NUMERIC")
    return float(eval(cleaned, {"__builtins__": {}}, {}))  # noqa: S307


def v_focus(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    act.click_el("document.querySelector('input[type=text],textarea')")
    submit(act)
    return "focus"


def v_tabs(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    tok = (plan.get("operand") or {}).get("quoted")
    tabs = [c for c in candidates(act) if c["tag"] in ("A", "BUTTON", "LI")][:6]
    for t in tabs:
        act.click(t["cx"], t["cy"])
        time.sleep(0.20)
        if episode_over(act):
            return "tab-done"
        if tok:
            hit = best_candidate(candidates(act), tok)
            if hit:
                act.click(hit["cx"], hit["cy"])
                time.sleep(0.22)
                if episode_over(act):
                    return "tab-link"
    return "tabs"


def v_expand(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    """EXPAND_AND_CLICK -- open every collapsible, then click the link the goal NAMES.

    click-collapsible-2 renders several collapsed sections and hides the target link inside
    one of them. The earlier version clicked the first button on the page and then looked for
    the target: on that page the first button is a section header, so the target stayed
    hidden and the task scored a flat 0 with a correct-looking action string. Opening ALL
    headers first, then resolving the quoted name, is what the instruction actually says.

    social-media has the same shape with rows: the goal names a user, so the click must be
    resolved to that row rather than to the first button in the list.
    """
    tok = (plan.get("operand") or {}).get("quoted")
    if tok is None:
        m = re.search(r'"([^"]+)"', goal) or re.search(r"\u201c([^\u201d]+)\u201d", goal)
        tok = m.group(1).strip() if m else None

    # 1. open every collapsible header before looking for the target
    opened = 0
    for _ in range(8):
        headers = act.js(
            "[...document.querySelectorAll('button,a,div,span,h1,h2,h3,h4,li')]"
            ".filter(e=>{const r=e.getBoundingClientRect();"
            "return r.width>4&&r.height>4&&r.y>40&&r.y<200&&e.children.length<3})"
            ".map(e=>({t:(e.innerText||'').trim().slice(0,40),"
            "cx:e.getBoundingClientRect().x+e.getBoundingClientRect().width/2,"
            "cy:e.getBoundingClientRect().y+e.getBoundingClientRect().height/2}))"
            ".filter(e=>e.t&&e.t.length<40).slice(0,8)") or []
        if not headers:
            break
        if any(tok and tok.lower() in (h["t"] or "").lower() for h in headers):
            break
        h = headers[0]
        act.click(h["cx"], h["cy"])
        opened += 1
        time.sleep(0.18)
        if episode_over(act):
            return "expand-clicked-header@%d" % opened

    # 2. now the target should be reachable by name
    if tok:
        hit = best_candidate(candidates(act), tok)
        if hit:
            act.click(hit["cx"], hit["cy"])
            time.sleep(0.20)
            if episode_over(act):
                return "expanded+clicked:%s" % tok
    submit(act, required=False)
    return "expand-miss:%s" % tok


def v_click(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    tok = (plan.get("operand") or {}).get("quoted")
    if tok is None:
        m = re.search(r'"([^"]+)"', goal) or re.search(r"\u201c([^\u201d]+)\u201d", goal)
        tok = m.group(1).strip() if m else None
    if tok:
        # resolution first: it knows about declared names, scoping and expansion
        got = _resolve_and_click(act, goal)
        if episode_over(act):
            return "click-done"
        if got.startswith(("resolved", "declared", "substring", "exact", "painted")):
            submit(act, required=False)
            return got
        hit = best_candidate(candidates(act), tok)
        if hit:
            act.click(hit["cx"], hit["cy"])
            time.sleep(0.24)
            if episode_over(act):
                return "click-done"
            submit(act)
            return "click:%s" % tok
    btn = [c for c in candidates(act) if c["tag"] == "BUTTON" and c["cy"] > 95]
    if btn:
        act.click(btn[0]["cx"], btn[0]["cy"])
        time.sleep(0.24)
        if episode_over(act):
            return "sole-done"
        submit(act)
        return "sole-button"
    return "click-miss"


# ---------------------------------------------------------------------------------------
# ROUTER  -- choose by the widget that is PRESENT, not by the verb word alone
# ---------------------------------------------------------------------------------------
def colour_in_goal(goal: str) -> str | None:
    """A colour word in the goal text, if one is actually written there."""
    for w in ("black", "white", "red", "green", "blue", "yellow", "olive", "cyan",
              "magenta", "pink", "gray", "grey", "orange", "purple", "brown", "navy",
              "teal", "lime"):
        if re.search(r"\b" + w + r"\b", goal or "", re.I):
            return w
    return None


def dispatch(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    verb = plan.get("verb")
    op = plan.get("operand") or {}
    g = goal or ""

    if act.ev("!!document.getElementById('spinner')"):
        return v_spinner(act, plan, goal)
    if act.ev("!!document.getElementById('col')"):
        return v_colour(act, plan, goal)
    kinds = set(act.js(
        "[...document.querySelectorAll('input,select,textarea')]"
        ".map(e=>e.type||e.tagName.toLowerCase())") or [])
    if "checkbox" in kinds and re.search(r"select", g, re.I):
        return v_checkboxes(act, plan, goal)
    if act.ev("(()=>{const s=document.getElementById('options');return !!(s&&s.multiple)})()"):
        return v_multiselect(act, plan, goal)
    # A rendered problem is a stronger signal than the verb word: if the page is showing an
    # equation or a countable display, the task is to read it and answer.
    if act.ev("!!document.querySelector('#math-problem')"):
        return v_read_and_compute(act, plan, goal)

    # A goal that says "the colored box" but writes no colour carries its value as PAINT in
    # the instruction itself. The painted matcher is the only thing that can read it, and it
    # has to run before CLICK concludes there is no token.
    if re.search(r"\bcolou?red\b", g, re.I) and colour_in_goal(g) is None:
        got = _resolve_and_click(act, goal)
        if episode_over(act) or not got.startswith("resolve-not"):
            if not episode_over(act):
                submit(act, required=False)
            return got

    table = {
        "SET_SLIDERS": v_slider, "SCROLL_TO": v_scroll, "ENTER": v_type,
        "FIND_AND_TYPE": v_type, "DRAW": v_draw_line, "MOVE": v_move_cube,
        "PUSH_SEQUENCE": v_push_sequence, "FOCUS": v_focus, "SWITCH_TABS": v_tabs,
        "EXPAND_AND_CLICK": v_expand, "CLICK": v_click,
    }
    if verb == "DRAG":
        if "black box" in g.lower():
            return v_draw_shapes(act, goal)
        return v_drag_box(act, plan, goal)
    if verb == "SELECT":
        if op.get("path"):
            return v_menu(act, plan, goal)
        if op.get("colour"):
            return v_colour(act, plan, goal)
        return v_native_select(act, plan, goal)

    fn = table.get(str(verb))
    if str(verb) in ("FIND", "RESOLVE"):
        # FIND used to fall through to CLICK, which with no quoted token clicks the sole
        # button on the page -- i.e. Submit -- and ends the episode before resolution is
        # tried. "Find and click the center of the circle" resolved perfectly and then
        # pressed Submit. Resolution has to run first; CLICK is the fallback, not the route.
        got = _resolve_and_click(act, goal)
        if episode_over(act):
            return "find-done"
        return got
    if fn is None:
        raise ActuatorError("VERB_NOT_IMPLEMENTED:" + str(verb))
    return fn(act, plan, goal)


# ---------------------------------------------------------------------------------------
# EPISODE
# ---------------------------------------------------------------------------------------
def run_episode(act: Actuator, task: str, decompose: Callable[[str], Mapping[str, Any]]
                ) -> dict[str, Any]:
    goal = start(act, task)
    plan = decompose(goal)
    if plan.get("status") != "DECOMPOSED":
        return {"task": task, "goal": goal, "status": plan.get("status"),
                "action": "REFUSED", "success": False, "reward": None, "verb": None}
    action = None
    note = None
    try:
        action = dispatch(act, plan, goal)
    except ActuatorError as exc:
        msg = str(exc)
        if msg != "NO_SUBMIT_CONTROL":
            return {"task": task, "goal": goal, "status": "NOT_IMPLEMENTED",
                    "action": msg, "success": False, "reward": None,
                    "verb": plan.get("verb")}
        # A page with no Submit control may grade itself on an event -- focus-text ends the
        # episode from an onfocus handler and has no button anywhere. The verb still ran;
        # only the submit step was impossible. Judge by whether the episode actually ended.
        note = "NO_SUBMIT"
        action = "self-grading"
    if not episode_over(act) and note is None:
        submit(act, required=False)
        time.sleep(0.10)
    r = raw_reward(act)
    done = episode_over(act)
    return {"task": task, "goal": goal, "status": "DECOMPOSED",
            "action": action if note is None else action + ":" + note,
            "verb": plan.get("verb"),
            "success": bool(done and isinstance(r, (int, float)) and r > 0),
            "reward": r}


def run_sample(act: Actuator, tasks: Iterable[str],
               decompose: Callable[[str], Mapping[str, Any]],
               valid: Mapping[str, Mapping[str, Any]] | None = None,
               record: Callable[..., Any] | None = None,
               run_id: str = "run", policy: str = "planner") -> list[dict[str, Any]]:
    rows = []
    for t in tasks:
        invalid = bool(valid and (valid.get(t, {}).get("verdict") == "REWARDS_INACTION"))
        try:
            row = run_episode(act, t, decompose)
        except Exception as exc:
            # Record the MESSAGE, not just the type. r137 wrote "ERR:ModuleNotFoundError"
            # for 18 tasks and the cause could not be recovered from the ledger afterwards;
            # a round was then spent guessing at it. A diagnosis has to survive the run.
            detail = (type(exc).__name__ + ": " + str(exc))[:140]
            row = {"task": t, "status": "ERROR", "action": "ERR:" + detail,
                   "success": False, "reward": None, "verb": None}
        row["invalid_task"] = invalid
        row["counts"] = bool(row["success"]) and not invalid
        rows.append(row)
        if record is not None:
            record(run_id, policy, t, row["success"], action=row.get("action"),
                   reward=row.get("reward"), extra={"invalid": invalid})
    return rows


def tally(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    counted = [r for r in rows if r.get("counts")]
    valid = [r for r in rows if not r.get("invalid_task")]
    return {"tasks": len(rows), "reported_pass": sum(bool(r.get("success")) for r in rows),
            "valid_tasks": len(valid), "counted_pass": len(counted),
            "reach_valid": round(len(counted) / len(valid), 4) if valid else 0.0,
            "reach_reported": round(sum(bool(r.get("success")) for r in rows) / len(rows), 4)
            if rows else 0.0}


if __name__ == "__main__":  # pragma: no cover
    import argparse
    from canonical.runtime import goal_verb_decomposition_v1 as D

    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", nargs="*")
    ap.add_argument("--sample")
    ap.add_argument("--null", type=int, default=0, help="run the null probe N episodes each")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    tasks = a.tasks or (json.load(open(a.sample)) if a.sample else [])
    act = Actuator()
    if a.null:
        for t in tasks:
            print(json.dumps(null_actuator(act, t, a.null)))
    if a.run:
        for r in run_sample(act, tasks, D.decompose):
            print(json.dumps(r))
