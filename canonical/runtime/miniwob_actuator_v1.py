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

    def click_el(self, selector_js: str, dom: bool = False) -> bool:
        """Press the element a selector names.

        A POINT IS NOT AN ELEMENT. Measured 2026-11-09 on `phone-book`: the handler is
          $('#contact a').on('click', function(){
            var correctProperty = expectedDetails.property === this.getAttribute('class') ...
          })
        It reads `this`, so it needs a real element as the target. A CDP mouse event at
        the element's centre produces one -- the browser hit-tests it -- but a page that
        re-renders between the box measurement and the event, or that delegates the
        handler, can lose that link. `dom=True` dispatches click() directly on the element
        that matches, which is the element the handler expects.
        """
        if dom:
            return bool(self.ev(
                "(()=>{const e=%s;if(!e)return false;e.click();return true})()"
                % selector_js))
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
        """A DRAG IS A BUTTON THAT STAYS DOWN, AND CDP NEEDS TO BE TOLD SO ON EVERY MOVE.

        Measured 2026-11-09: all eight drag tasks scored 0/3 and the cause was here, not
        in the goal parsing. `drag-items` is a jQuery UI Sortable, whose `_mouseMove`
        handler returns early unless the event reports a button still held. CDP's
        Input.dispatchMouseEvent defaults `buttons` to 0, so a move carrying only
        `"button": "left"` looks like a hover and the widget never starts dragging. The
        gesture completed, released, and changed nothing -- 0/24 across the family while
        the action string said "drag".

        `buttons: 1` on the press and on every move is the bit that makes it a drag.
        """
        self.call("Input.dispatchMouseEvent",
                  {"type": "mousePressed", "x": float(x0), "y": float(y0),
                   "button": "left", "buttons": 1, "clickCount": 1})
        time.sleep(0.03)
        for i in range(1, steps + 1):
            self.call("Input.dispatchMouseEvent",
                      {"type": "mouseMoved", "x": float(x0 + (x1 - x0) * i / steps),
                       "y": float(y0 + (y1 - y0) * i / steps),
                       "button": "left", "buttons": 1})
            time.sleep(0.03)
        self.call("Input.dispatchMouseEvent",
                  {"type": "mouseReleased", "x": float(x1), "y": float(y1),
                   "button": "left", "buttons": 1, "clickCount": 1})

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
                "(()=>{return [...document.querySelectorAll('button')]"
                ".find(b=>/submit|done/i.test(b.innerText||''))})()"):
        if act.click_el(sel):
            time.sleep(settle)
            return True
    if required:
        raise ActuatorError("NO_SUBMIT_CONTROL")
    return False


def candidates(act: Actuator) -> list[dict[str, Any]]:
    """Everything on the page that can be pressed, EXCEPT the instruction.

    THE INSTRUCTION CONTAINS THE WORD IT NAMES.
    Measured 2026-11-09 in two different families: "Drag the circle left..." matched the
    candidate 'Drag the circle left then press Submit.' at (80,25), and "Select
    Jaquelyn>Nonna" matched 'Nonna' to the sentence at (80,25) as well -- the #query box.
    Both drivers then acted on the sentence. Fixing it in the drag path only, as I did
    first, left the menu path broken; the exclusion belongs in the reader every verb uses.
    #query can never be the thing to manipulate, and neither can anything drawn on top of
    it, so a candidate whose centre falls inside the #query box is dropped.
    """
    return act.js(
        "(()=>{const q=document.querySelector('#query');"
        "const qb=q?q.getBoundingClientRect():null;"
        "return [...document.querySelectorAll('button,a,li,div,span,input,label')]"
        ".filter(e=>{const r=e.getBoundingClientRect();return r.width>4&&r.height>4})"
        # THE TEST IS CONTAINMENT, NOT THE CENTRE POINT.
        #
        # Measured 2026-11-09 on click-collapsible-2: the chosen candidate was the ENTIRE
        # PAGE div (33600 px) because it contains the instruction text mixed with the
        # section bodies, so a substring match on a short token matched the whole document.
        # Testing whether a candidate's CENTRE lies inside #query passed, because the page
        # div's centre is below the query box. What matters is that the candidate CONTAINS
        # #query -- a wrapper of the instruction is not a control.
        ".filter(e=>{if(!qb)return true;if(e.contains(q))return false;"
        "const r=e.getBoundingClientRect();if(r.width*r.height>30000)return false;"
        "const cx=r.x+r.width/2,cy=r.y+r.height/2;"
        "return !(cx>=qb.x&&cx<=qb.x+qb.width&&cy>=qb.y&&cy<=qb.y+qb.height)})"
        ".map(e=>{const r=e.getBoundingClientRect();"
        "return {t:(e.innerText||'').trim(),cx:r.x+r.width/2,cy:r.y+r.height/2,"
        "a:r.width*r.height,tag:e.tagName}})})().slice(0,160)") or []


def best_candidate(cands: Iterable[Mapping[str, Any]], text: str) -> Mapping[str, Any] | None:
    """Exact match first, then case-insensitive, then substring; smallest area wins."""
    """Exact match first, then case-insensitive, then WHOLE-WORD substring, then any.

    A SHORT TOKEN MATCHED A WHOLE PARAGRAPH. Measured 2026-11-09 on click-collapsible-2:
    the goal names the link "non" and the third tier (`text in c["t"]`) matched the
    enclosing paragraph, whose text happens to contain "non" -- a 10488 px block instead
    of the 297 px link. Sorting by area does not help when only one candidate matches.
    A whole-word match is tried first, and a substring match must not be more than four
    times longer than the token, so a short word can no longer select a paragraph.
    """
    cands = list(cands)
    low = (text or "").lower().strip()
    for pred in (lambda c: c["t"] == text,
                 lambda c: c["t"].lower() == low):
        hits = [c for c in cands if c["t"] and pred(c)]
        if hits:
            return sorted(hits, key=lambda c: c["a"])[0]
    word = [c for c in cands
            if c["t"] and re.search(r"(?:^|[^\w])" + re.escape(low) + r"(?:$|[^\w])",
                                    c["t"].lower())]
    if word:
        return sorted(word, key=lambda c: c["a"])[0]
    hits = [c for c in cands
            if c["t"] and low and low in c["t"].lower()
            and len(c["t"]) <= max(24, 4 * len(low))]
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


_SOCIAL_MAP = {"share": "share", "share via dm": "share", "copy": "copy",
                "copy link to tweet": "copy", "embed": "embed",
                "embed tweet": "embed", "mute": "menu-user", "block": "block-user",
                "block user": "block-user", "report": "report", "reply": "reply",
                "retweet": "retweet", "like": "like"}

_ARTICLES = {"the", "a", "an", "this", "that", "its", "of", "value", "text", "field"}


def _table_lookup(act: Actuator, goal: str) -> str | None:
    """When the goal names a LABEL, the value is in the page's own table.

    Measured 2026-11-09 on `read-table`: the page is a two-column table
    (First name -> Allys, Last name -> Hooper, Color -> olive, ...) and the goal is
    "Enter the value of First name into the text field". The decomposer produced
    ENTER with token='the' -- the article -- so the agent typed "the" into the box.
    The label is right there in the sentence and the value is right there in the page.

    The lookup is by the sentence's own words against the table's first column, and it
    returns nothing when no row matches, so a page without a table is unaffected.
    """
    rows = act.ev("(()=>{return [...document.querySelectorAll('tr')]"
                  ".map(r=>[...r.children].map(c=>c.innerText.trim()))})()") or []
    if not rows:
        return None
    g = (goal or "").lower()
    best = None
    for cells in rows:
        if len(cells) < 2 or not cells[0]:
            continue
        label = cells[0].strip().lower()
        if label and label in g:
            if best is None or len(label) > len(best[0]):
                best = (label, cells[1].strip())
    if best:
        return best[1]
    # a table whose labels the sentence does not quote: use the sentence's own noun phrase
    m = re.search(r"(?:value\s+of|the)\s+(.+?)\s+(?:into|in|to)\s+the\s+(?:text\s+)?(?:field|box|input)",
                  (goal or ""), re.I)
    if m:
        want = m.group(1).strip().lower()
        for cells in rows:
            if len(cells) >= 2 and cells[0].strip().lower() == want:
                return cells[1].strip()
    return None


def v_type(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    op = plan.get("operand") or {}
    tok = op.get("token")
    # AN ARTICLE IS NOT A VALUE.
    #
    # token='the' means the decomposer found the verb but not the reference. Before
    # typing a word that is plainly not the answer, read the page: a two-column table
    # answers most of these outright.
    # A FORM THAT ASKS FOR EVERY LABEL IS FILLED LABEL BY LABEL.
    #
    # Measured 2026-11-09 on `read-table-2`: "Enter the value that corresponds with each
    # label into the form" -- the page shows a two-column table (Color => aqua,
    # Year of Birth => 1993, ...) and a form with a labelled box per requested label.
    # There is no single token to type; every box takes the value of the label beside it.
    # Each box is read together with the nearest label text, the table answers that label,
    # and the box receives the answer. A box whose label has no row is left alone.
    if re.search(r"each label|all (?:the )?label", (goal or ""), re.I):
        _rows = act.ev("(()=>{return [...document.querySelectorAll('tr')]"
                       ".map(r=>[...r.children].map(c=>c.innerText.trim()))})()") or []
        _tbl = {}
        for _cells in _rows:
            if len(_cells) >= 2 and _cells[0]:
                _tbl[_cells[0].strip().rstrip(":").lower()] = _cells[1].strip()
        _boxes = act.ev(
            "(()=>{const out=[];"
            "for(const e of document.querySelectorAll('#form input[type=text],#form textarea')){"
            "const r=e.getBoundingClientRect();if(r.width<=0||r.height<=0)continue;"
            "let lab='';let p=e.parentElement;"
            "for(let i=0;i<3&&p;i++){const l=p.querySelector('.label,label,td');"
            "if(l&&l!==e){lab=l.innerText.trim();break}p=p.parentElement}"
            "out.push({id:e.id||'',lab:lab.replace(/:$/,'').toLowerCase(),"
            "cx:r.x+r.width/2,cy:r.y+r.height/2})}return out})()") or []
        if _tbl and _boxes:
            _n = 0
            for _b in _boxes:
                _v = None
                if _b["lab"] and _b["lab"] in _tbl:
                    _v = _tbl[_b["lab"]]
                else:
                    for _k, _val in _tbl.items():
                        if _b["lab"] and (_b["lab"] in _k or _k in _b["lab"]):
                            _v = _val
                            break
                if not _v:
                    continue
                _sel = ("document.getElementById(%s)" % json.dumps(_b["id"])) \
                    if _b["id"] else \
                    ("document.elementFromPoint(%f,%f)" % (_b["cx"], _b["cy"]))
                act.ev("(()=>{const e=%s;if(!e)return;e.focus();e.value='';"
                       "e.value=%s;e.dispatchEvent(new Event('input',{bubbles:true}));"
                       "e.dispatchEvent(new Event('change',{bubbles:true}))})()"
                       % (_sel, json.dumps(_v)))
                _n += 1
            if _n:
                submit(act, required=False)
                return "type-labels:%d" % _n
    # THE INSTRUCTION CAN NAME A TRANSFORMATION, NOT A LITERAL.
    #
    # Measured 2026-11-09 on `enter-text-2`: the goal reads
    #   Type "MICHAEL" in all lower case letters in the text input and press Submit.
    # and the page scores  t === expectedText  where expectedText is the quoted token with
    # the named transformation applied. Typing the quoted token verbatim is a certain
    # failure, and nothing before this looked at the words AFTER the quote. The rule is
    # general: if the goal names a case/shape operation, apply it to the token.
    if tok:
        _g = goal or ""
        _t = str(tok)
        if re.search(r"all\s+upper|upper\s*case", _g, re.I):
            _t = _t.upper()
        elif re.search(r"all\s+lower|lower\s*case", _g, re.I):
            _t = _t.lower()
        elif re.search(r"capitali[sz]", _g, re.I):
            _t = _t[:1].upper() + _t[1:].lower()
        elif re.search(r"revers", _g, re.I):
            _t = _t[::-1]
        elif re.search(r"without\s+(?:any\s+)?spaces", _g, re.I):
            _t = re.sub(r"\s+", "", _t)
        op = dict(op)
        op["token"] = _t
        tok = _t
    # THE ANSWER CAN BE PRINTED ON THE PAGE RATHER THAN QUOTED IN THE SENTENCE.
    #
    # Measured 2026-11-09 on `text-transform`: the goal is the constant
    # "Type the text below into the text field and press Submit." -- there is no token at
    # all, and the answer is a set of <span>s inside #captcha, one character each, each
    # with its own skewX/skewY. The instruction's own words say where to look ("below").
    # Read the spans in DOM order and concatenate; a captcha is a string the page shows
    # you, so no OCR and no vision is needed.
    if (not tok or len(str(tok).strip()) < 3
            or str(tok).strip().lower() in _ARTICLES):
        _shown = act.ev(
            "(()=>{const c=document.querySelector('#captcha');"
            "const es=c?[...c.children]:[];"
            "if(!es.length)return null;"
            "return es.map(e=>e.textContent).join('')})()")
        if _shown and len(str(_shown).strip()) >= 2:
            op = dict(op); op["token"] = str(_shown).strip(); tok = str(_shown).strip()

    # ONE TOKEN, MANY FIELDS: "Enter the password X into BOTH text fields".
    #
    # Measured 2026-11-09 on `enter-password`, 0/30: the page scores
    # (p === password && v === password) over #password AND #verify, and the old path
    # filled only the first box, so the episode ended on a half-filled form.
    if tok and re.search(r"\bboth\b|each (?:text )?field", (goal or ""), re.I):
        _boxes = ("'input[type=text],input[type=password],input[type=date],"
                  "input[type=time],input[type=number],input:not([type]),textarea'")
        _f = act.ev(
            "(()=>{return [...document.querySelectorAll(%s)]"
            ".filter(e=>{const r=e.getBoundingClientRect();"
            "return r.width>0&&r.height>0}).length})()" % _boxes)
        if isinstance(_f, int) and _f >= 2:
            _n = 0
            for _i in range(min(_f, 6)):
                _s = ("(()=>{const es=[...document.querySelectorAll(%s)]"
                      ".filter(e=>{const r=e.getBoundingClientRect();"
                      "return r.width>0&&r.height>0});"
                      # click_el resolves an EXPRESSION TO AN ELEMENT. Returning
                      # !!es[i] hands it `true`, and the press silently never happens.
                      "return es[%d]||null})()" % (_boxes, _i))
                if act.click_el(_s):
                    act.type_text(str(tok))
                    _n += 1
            if _n:
                submit(act, required=False)
                return "type-both:%d" % _n

    if not tok or str(tok).strip().lower() in _ARTICLES or len(str(tok).strip()) < 3:
        _from_table = _table_lookup(act, goal)
        if _from_table:
            op = dict(op)
            op["token"] = _from_table
            tok = _from_table
    # A DATE FIELD TAKES ISO AND THE PAGE REARRANGES IT.
    #
    # Measured 2026-11-09 on `enter-date`, 0/30: the goal quotes 12/03/2017 and the page
    # does  value.split('-') -> t[1]+'/'+t[2]+'/'+t[0], i.e. it expects YYYY-MM-DD.
    # Typing the quoted mm/dd/yyyy produced an empty split and a certain miss.
    if tok and re.search(r"\bas the date\b|\bdate field\b", (goal or ""), re.I):
        # PARSE THE GOAL, NOT THE TOKEN. The decomposer turns "Enter 12/03/2017 as the
        # date..." into token='12' -- the first number it sees -- so the token can never
        # match a date pattern. The date is in the sentence; take it from there.
        _md = (re.search(r'(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})', str(goal or ""))
               or re.search(r'(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})', str(tok)))
        if _md:
            _iso = "%s-%02d-%02d" % (_md.group(3), int(_md.group(1)), int(_md.group(2)))
            op = dict(op); op["token"] = _iso; tok = _iso

    # A NATIVE DATE INPUT IGNORES KEYSTROKES.
    #
    # Measured 2026-11-09 on `enter-date`: click_el focused input[type=date], type_text
    # sent "2011-07-19", and the field read back ''. A typed value is not an accepted
    # value -- the same law as r169, on a control where the browser owns the editor.
    # Set the value through the element's own setter and fire the events the page
    # listens for, then read it back before believing it.
    if tok and re.search(r"^\d{4}-\d{2}-\d{2}$", str(tok)):
        _did = act.ev(
            "(()=>{const e=document.querySelector('input[type=date],input[type=time]');"
            "if(!e)return null;e.focus();e.value=%s;"
            "e.dispatchEvent(new Event('input',{bubbles:true}));"
            "e.dispatchEvent(new Event('change',{bubbles:true}));"
            "return e.value})()" % json.dumps(str(tok)))
        if _did == str(tok):
            submit(act, required=False)
            time.sleep(0.25)
            if episode_over(act):
                return "type-date:%s" % str(tok)[:10]

    sel = ("textarea" if op.get("field") == "textarea"
           # TYPE=DATE IS A TEXT FIELD. `input[type=text]` does not match it, so
           # enter-date was reaching for a box that was not there and typing at nothing.
           else ("input[type=text],input[type=date],input[type=time],"
                 "input[type=number],input:not([type]),textarea"))
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


_ORD = {"1st": 1, "first": 1, "2nd": 2, "second": 2, "3rd": 3, "third": 3,
        "4th": 4, "fourth": 4, "5th": 5, "fifth": 5, "6th": 6, "sixth": 6}


def v_sort(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    """SORT -- the page states the values, the goal states the order, the gap is arithmetic.

    Measured 2026-11-09: `drag-sort-numbers` returns SORT and dispatch had no handler, so
    it raised VERB_NOT_IMPLEMENTED and the episode ended without touching the page. This
    task reaches that branch on every rep, so "emitted but unreachable" was wrong.

    BUBBLE SORT BY ADJACENT DRAGS, not placement at an absolute target. The sortable
    resolves a drop against the slot the pointer lands in; a drag computed from a target
    index drifts as rows move under it. Swapping neighbours one pair at a time is stable,
    needs no absolute coordinate, and terminates:
      ['76','-26','-42','15'] -> ['-42','-26','15','76'] in 4 moves, reward 1.
    """
    want_desc = bool(re.search(r"decreas|descend|largest", (goal or ""), re.I))
    R = ("[...document.querySelectorAll('#sortable li')]"
         ".map(e=>{const r=e.getBoundingClientRect();"
         "return {t:e.innerText.trim(),y:r.y+r.height/2,x:r.x+r.width/2}})")
    moves = 0
    for _pass in range(12):
        cur = act.ev(R) or []
        if len(cur) < 2:
            return "sort-no-list"
        try:
            vals = [float(re.sub(r"[^0-9.\-]", "", c["t"]) or 0) for c in cur]
        except Exception:  # noqa: BLE001
            return "sort-not-numeric"
        target = sorted(vals, reverse=want_desc)
        if vals == target:
            break
        swapped = False
        for i in range(len(vals) - 1):
            bad = (vals[i] < vals[i + 1]) if want_desc else (vals[i] > vals[i + 1])
            if bad:
                a, b = cur[i], cur[i + 1]
                act.drag(a["x"], a["y"], a["x"], b["y"] + 10, steps=14)
                time.sleep(0.18)
                moves += 1
                swapped = True
                break
        if not swapped:
            break
    submit(act, required=False)
    return "sort-%s:%d-moves" % ("desc" if want_desc else "asc", moves)


def v_drag_box(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    """DRAG -- the source and the destination come from the sentence, not from an id.

    Measured 2026-11-09: every one of the eight drag tasks scored 0/3 (0/24 total, the
    largest single zero in the corpus) and this function was the reason. It read
    `#draggableSmall` and `#draggableLarge` -- the element ids of exactly one page --
    and every other drag task silently dragged the same two elements that were not
    there, then pressed Submit. A transcription of one instance presented as a verb.

    Two shapes are read here, both from words the instruction supplies:
      "Drag <name> to the <Nth> position."   source is the element whose text is <name>,
                                             destination is walk N-1 places down the
                                             list of sibling items that share its x.
      "Drag the smaller box ... larger box"  source is the smaller of the two boxes,
                                             destination the larger one's top-left corner.
    When neither shape is present it refuses rather than dragging something arbitrary.
    """
    g = (goal or "").lower()
    cands = [c for c in candidates(act) if (c.get("t") or "").strip()]
    # A DESTINATION IS ABSOLUTE OR RELATIVE, AND BOTH ARE STATED.
    #
    # Measured 2026-11-09: the corpus writes four shapes and this function read one.
    #   "Drag X to the 4th position."   absolute, read before
    #   "Drag X to the bottom."         absolute, last
    #   "Drag X up by one position."    relative, current index minus one
    #   "Drag X down by one position."  relative, current index plus one
    # The three unread shapes were reported as drag-not-understood on a verb that was
    # understood perfectly well.
    # A DIRECTION IS A DISTANCE IN PIXELS, AND THE PAGE ONLY CHECKS THE SIGN.
    #
    # Measured 2026-11-09 from drag-circle's own source: the checker compares the element's
    # position to its initial box and rewards any movement with the right sign --
    #   'right' -> currentCoords.x > initialCoords.x
    # Nothing about magnitude is tested, so the drag only has to clear the widget's own
    # slop. drag-single-shape, drag-circle and drag-items-grid all state a bare direction.
    _dir = re.search(r"drag\s+(?:the\s+)?(.+?)\s+(up|down|left|right)\b(?!\s*by)", g)
    if _dir and not re.search(r"by\s+\w+\s+position", g):
        _what = _dir.group(1).strip()
        _side = _dir.group(2)
        # THE SHAPE IS NOT TEXT, SO IT IS NOT IN `candidates`.
        #
        # Measured 2026-11-09 on drag-circle: the circle sits at (61,105) as an SVG
        # <circle>, and candidates() only queries button,a,li,div,span,input,label -- so
        # the list held the instruction div (80,105) and this code dragged the sentence.
        # Draggable geometry is read directly from the page for circle/rect/image/svg
        # descendants, and only falls back to text candidates when there is none.
        _geo = act.ev("(()=>{const out=[];"
                      "for(const e of document.querySelectorAll('circle,rect,image,svg,polygon')){"
                      "const r=e.getBoundingClientRect();"
                      "if(r.width>6&&r.height>6){out.push({t:'',cx:r.x+r.width/2,cy:r.y+r.height/2,"
                      "a:r.width*r.height})}}return out})()") or []
        # THE SENTENCE ITSELF CONTAINS THE WORD IT NAMES.
        #
        # Measured 2026-11-09 on drag-circle: the candidate matching "circle" was
        # 'Drag the circle left then press Submit.' at (80,25) -- the instruction div --
        # and dragging it moved nothing. #query is the instruction and it can never be the
        # thing to manipulate. It is excluded by position, using the element the page
        # itself puts the instruction in.
        _qbox = act.box("document.querySelector('#query')") or {}
        def _is_instruction(c):
            if not _qbox:
                return False
            return (_qbox.get("x", -1) <= c["cx"] <= _qbox.get("x", 0) + _qbox.get("w", 0)
                    and _qbox.get("y", -1) <= c["cy"] <= _qbox.get("y", 0) + _qbox.get("h", 0))
        _named = [c for c in cands if _what and _what in (c["t"] or "").lower()
                  and (c.get("a") or 0) < 20000 and not _is_instruction(c)]
        # the SVG canvas is also "geometry" and it is the largest thing on the page;
        # the draggable is the SMALLEST element that can be seen -- a 784 px circle, not a
        # 20800 px canvas. Sorting by area and taking the first picked the canvas and
        # dragged nothing. The smallest is the shape.
        _geo.sort(key=lambda c: c["a"])
        _cand = _named or _geo or [c for c in cands if (c.get("a") or 0) > 100]
        _cand = sorted(_cand, key=lambda c: c["a"])
        if _cand:
            _c = sorted(_cand, key=lambda c: c["a"])[0]
            _D = 60
            _dx = _D if _side == "right" else (-_D if _side == "left" else 0)
            _dy = _D if _side == "down" else (-_D if _side == "up" else 0)
            act.drag(_c["cx"], _c["cy"], _c["cx"] + _dx, _c["cy"] + _dy, steps=16)
            time.sleep(0.30)
            if not episode_over(act):
                submit(act, required=False)
            return "drag-dir:%s" % _side
    m = re.search(r"drag\s+(.+?)\s+to\s+the\s+([\w]+)\s+position", g)
    _rel = re.search(r"drag\s+(.+?)\s+(up|down)\s+by\s+(\w+)\s+position", g)
    _bot = re.search(r"drag\s+(.+?)\s+to\s+the\s+bottom", g)
    if _rel:
        _want = _rel.group(1).strip()
        _names = [c for c in cands if (c["t"] or "").strip().lower() == _want]
        if not _names:
            _names = [c for c in cands if _want and _want in (c["t"] or "").lower()]
        if _names:
            _src = sorted(_names, key=lambda c: c["a"])[0]
            _col, _seen = [], set()
            for c in sorted([c for c in cands if abs(c["cx"] - _src["cx"]) < 26],
                            key=lambda c: c["cy"]):
                k = (round(c["cx"]), round(c["cy"]))
                if k not in _seen:
                    _seen.add(k)
                    _col.append(c)
            _cur = next((i for i, c in enumerate(_col)
                         if abs(c["cy"] - _src["cy"]) < 4), None)
            _steps = _ORD.get(_rel.group(3), 1) or 1
            if _cur is not None:
                _tgt = max(0, _cur - _steps) if _rel.group(2) == "up" \
                    else min(len(_col) - 1, _cur + _steps)
                _step = (_col[1]["cy"] - _col[0]["cy"]) if len(_col) > 1 else 29
                _sign = 1.0 if _col[_tgt]["cy"] >= _src["cy"] else -1.0
                act.drag(_src["cx"], _src["cy"], _src["cx"],
                         _col[_tgt]["cy"] + _step * 0.6 * _sign, steps=16)
                time.sleep(0.30)
                if not episode_over(act):
                    submit(act, required=False)
                return "drag-rel:%s%s%d" % (_want[:10], _rel.group(2), _steps)
    if _bot:
        _want = _bot.group(1).strip()
        _names = [c for c in cands if (c["t"] or "").strip().lower() == _want]
        if _names:
            _src = sorted(_names, key=lambda c: c["a"])[0]
            _col, _seen = [], set()
            for c in sorted([c for c in cands if abs(c["cx"] - _src["cx"]) < 26],
                            key=lambda c: c["cy"]):
                k = (round(c["cx"]), round(c["cy"]))
                if k not in _seen:
                    _seen.add(k)
                    _col.append(c)
            if _col:
                _step = (_col[1]["cy"] - _col[0]["cy"]) if len(_col) > 1 else 29
                act.drag(_src["cx"], _src["cy"], _src["cx"],
                         _col[-1]["cy"] + _step * 0.7, steps=18)
                time.sleep(0.30)
                if not episode_over(act):
                    submit(act, required=False)
                return "drag-bottom:%s" % _want[:12]
    if m:
        want = m.group(1).strip()
        n = _ORD.get(m.group(2))
        if n:
            items = [c for c in cands if (c["t"] or "").strip().lower() == want]
            if not items:
                items = [c for c in cands if want and want in (c["t"] or "").lower()]
            if items:
                src = sorted(items, key=lambda c: c["a"])[0]
                col = sorted([c for c in cands if abs(c["cx"] - src["cx"]) < 26],
                             key=lambda c: c["cy"])
                # de-duplicate nested elements that share a centre
                seen, stack = set(), []
                for c in col:
                    key = (round(c["cx"]), round(c["cy"]))
                    if key in seen:
                        continue
                    seen.add(key)
                    stack.append(c)
                if len(stack) >= n:
                    # A SORTABLE MOVES THE ITEM PAST THE TARGET SLOT, NOT ONTO IT.
                    #
                    # Measured 2026-11-09: dragging the source onto the target slot's
                    # centre left the order unchanged (jQuery UI resolves the drop to the
                    # slot the item already occupies when the pointer lands exactly on a
                    # boundary). Dragging to the target's centre PLUS most of one row
                    # height lands the item in that slot: 'Drag Annis to the 4th position'
                    # with Annis 3rd moved it to 4th and scored 1.
                    step = (stack[1]["cy"] - stack[0]["cy"]) if len(stack) > 1 else 29
                    dst = stack[n - 1]
                    # the overshoot must be AWAY from where the item came from: moving an
                    # item up needs the pointer above the slot, moving it down needs it
                    # below. A fixed +0.6 row worked only when the target was lower.
                    sign = 1.0 if dst["cy"] >= src["cy"] else -1.0
                    act.drag(src["cx"], src["cy"], src["cx"],
                             dst["cy"] + step * 0.6 * sign, steps=16)
                    time.sleep(0.30)
                    if not episode_over(act):
                        submit(act, required=False)
                    return "drag-pos:%s->%d" % (want[:12], n)
                return "drag-pos-not-enough-items"
            return "drag-pos-no-source"

    s = act.box("document.querySelector('#draggableSmall')")
    big = act.box("document.querySelector('#draggableLarge')")
    if s and big:
        act.drag(s["cx"], s["cy"], big["x"] + 3, big["y"] + 3, steps=6)
        submit(act)
        return "dragbox"
    # last resort: two box-like candidates, smaller into larger
    if "smaller" in g and "larger" in g:
        boxes = sorted([c for c in cands if c["a"] > 400], key=lambda c: c["a"])
        if len(boxes) >= 2:
            act.drag(boxes[0]["cx"], boxes[0]["cy"],
                     boxes[-1]["cx"], boxes[-1]["cy"], steps=8)
            submit(act, required=False)
            return "drag-size-inferred"
    return "drag-not-understood"


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
    # the handler may read `this`; when the choice carries a selector, click the element
    if c.get("sel"):
        act.click_el(c["sel"], dom=True)
    else:
        act.click(c["cx"], c["cy"])
    time.sleep(0.24)
    # a control that reveals a menu needs a second click on the revealed item
    if not episode_over(act):
        return "%s:%s" % (str(out.get("by") or out["kind"]),
                          (c.get("own") or c.get("shown") or c.get("declared") or "")[:24])
    return "resolved-click-done"


def v_menu(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    """SELECT a path through a nested menu.

    A SUBMENU OPENS ON A REAL POINTER MOVE, NOT ON A SYNTHETIC EVENT.
    Measured 2026-11-09 on `click-menu`: the page is `$('#menu').menu({...})`, jQuery UI
    Menu, which opens a submenu on the jQuery `mouseenter` it synthesises from a genuine
    mousemove. Dispatching MouseEvent('mouseover') from page script did nothing, the
    submenu stayed collapsed, and the next path token was matched against whatever text
    happened to be at that point -- usually the task cover. With three real
    Input.dispatchMouseEvent moves onto each level, two- and three-level paths scored 1:
        Mireielle>Muriel              1
        Thia>Madelin>Vilma            1
        Yolande>Rosalia>Stephie       1
    The click is issued only on the final token; intermediate levels are hovered.
    """
    path = list((plan.get("operand") or {}).get("path") or [])
    if not path:
        return "menu-no-path"
    for i, tok in enumerate(path):
        hit = best_candidate(candidates(act), tok)
        if not hit:
            return "menu-miss:%s" % str(tok)[:12]
        for _ in range(3):
            act.call("Input.dispatchMouseEvent",
                     {"type": "mouseMoved", "x": float(hit["cx"]),
                      "y": float(hit["cy"]), "buttons": 0})
            time.sleep(0.10)
        time.sleep(0.30)
        if i == len(path) - 1:
            act.click(hit["cx"], hit["cy"])
            time.sleep(0.30)
    return "menu:%d" % len(path)


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


_MONTHS = {x: i + 1 for i, x in enumerate(
    "january february march april may june july august september october "
    "november december".split())}


def v_social(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    """A feed with per-post action toggles: click <action> on <n> posts by <user>, then Submit.

    Measured 2026-11-09 on `social-media-all` and `social-media-some`, both 0/30.

    THE CHECKER IS A TOTAL CONDITION, NOT A LOCAL ONE. It walks EVERY
    .reply/.retweet/.like/.share on the page and fails if a post that does not match
    (user, action) is active, exactly as it fails if a matching one is not. So the job is
    not "click the right button" -- it is "leave the page in exactly one state", and an
    extra click is as fatal as a missing one. Take the matching set, click precisely those,
    and count.

    `-some` names HOW MANY posts ("on 1 post by @briana") and the count is a third
    span.bold -- the page supplies every operand, including the quantity.
    """
    bold = act.ev("(()=>{return [...document.querySelectorAll('#query .bold')]"
                  ".map(e=>e.textContent.trim())})()") or []
    if len(bold) < 2:
        return "social-no-operands"
    # THE OPERAND ORDER IS NOT STABLE ACROSS THE FAMILY. `-all`/`-some` put the action
    # first ("Click the \"Share\" button on all posts by @x"); plain `social-media` puts
    # the USER first ("For the user @x, click on the \"Share\" button"). Classify each
    # span by what it IS -- a @handle vs a verb -- instead of by where it sits.
    # THE LABEL IS NOT THE CLASS. 'Mute' is <li class="menu-user">, 'Share via DM' is
    # <li class="share">, 'Copy link to Tweet' is <li class="copy">. And SIX of the nine
    # actions live inside a ul.hide "more" menu that has to be opened before they exist
    # on screen. So resolve the label to a class by asking the page's own menu for it.
    _LABEL2CLASS = _SOCIAL_MAP
    ACT_WORDS = tuple(_LABEL2CLASS)
    action, user = "", ""
    _acts = [b for b in bold if str(b).strip().lower().strip() in _LABEL2CLASS]
    _users = [b for b in bold if str(b).strip().startswith("@")]
    if _acts:
        action = _LABEL2CLASS[str(_acts[0]).strip().lower()]
    if _users:
        user = _users[0].strip()
    rest = [b for b in bold[1:]]
    want_n = None
    for b in rest:
        if re.fullmatch(r"\d+", str(b).strip()):
            want_n = int(b)
        elif not user and str(b).strip():
            user = str(b).strip()
    if not action:
        return "social-no-action"
    if not user:
        return "social-no-user"
    # (a hardcoded four-action set used to live here and OVERWROTE the resolved class.
    #  'Mute' resolves to 'menu-user', which contains none of those four words, so every
    #  menu action returned social-bad-action even though the map had it right.)

    # THE PLAIN VARIANT SCORES ON THE CLICK ITSELF AND COMPARES THE CLASS NAME:
    #   r = user === expectedUser && clickedElem === expectedAction
    # so there is no Submit and no "active" toggling -- the element's class must BE the
    # action. Detect it by whether the page has a Submit control at all.
    _has_submit = act.ev("(()=>{return [...document.querySelectorAll('button')]"
                         ".some(b=>/submit/i.test(b.textContent||''))})()")
    if not _has_submit:
        for _slot in ("first", "last"):
            if want_n is None and _slot == "last":
                break
            _hit = act.ev(
                "(()=>{const lim=%s,which=%s,a=%s,u=%s;"
                "const posts=[...document.querySelectorAll('.media')];"
                "const mine=posts.filter(p=>{const n=p.querySelector('.username');"
                "return n&&n.textContent.trim()===u});"
                "if(!mine.length)return 'NOUSER';"
                "const list=which==='last'?mine.slice(-1):mine;"
                "let n=0;"
                "for(const p of list){if(lim!==null&&n>=lim)break;"
                "let b=p.querySelector('.controls > .'+a)||p.querySelector('.'+a);"
                "if(!b){const mo=p.querySelector('.controls .more');"
                "if(mo){mo.click();b=p.querySelector('.'+a)}}"
                "if(!b)continue;"
                "b.click();n++;if(window.core&&core.endEpisode){break}}"
                "return n})()" % ("null" if want_n is None else str(want_n),
                                  json.dumps(_slot), json.dumps(action),
                                  json.dumps(user)))
            time.sleep(0.40)
            if episode_over(act):
                return "social-click:%s/%s" % (action, user[:10])
        return "social-click-miss:%s/%s" % (action, user[:10])

    # deselect everything first, then select exactly the matching set
    act.ev("(()=>{document.querySelectorAll('.like,.reply,.retweet,.share')"
           ".forEach(e=>e.classList.remove('active'))})()")
    n = act.ev(
        "(()=>{const u=%s,a=%s,lim=%s;let n=0;"
        "for(const p of document.querySelectorAll('.media')){"
        "const name=(p.querySelector('.username')||{}).textContent||'';"
        "if(name.trim()!==u)continue;"
        "if(lim!==null&&n>=lim)break;"
        "const b=p.querySelector('.'+a);"
        "if(b){b.classList.add('active');n++}}"
        "return n})()" % (json.dumps(user), json.dumps(action),
                          json.dumps(want_n)))
    act.ev("(()=>{const s=[...document.querySelectorAll('button')]"
           ".find(b=>/submit/i.test(b.textContent||''));if(s)s.click()})()")
    time.sleep(0.45)
    if episode_over(act):
        return "social:%s/%s/%s" % (action, user[:10], n)
    return "social-miss:%s/%s/n=%s" % (action, user[:10], n)


def v_email(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    """The email inbox: one app, four verbs, one entry point.

    Measured 2026-11-09, 0/50 across ten tasks. The app is NOT ten shapes -- it is one
    list of `#main .email-thread`, each showing `.email-sender`, and a detail view that
    binds its reply/forward/delete/star handlers only AFTER the thread is opened. So the
    procedure is: find the thread by sender, open it, act.

    THE PAGE STATES ITS OWN OPERANDS. In the plain variants the goal marks them up with
    <span class="bold">; in the `-nl` variants the goal is free text drawn from ~30
    alternate phrasings, and reading it is a parser problem with no stable surface. But
    both variants leave `core.currentFields` on the page -- {"by":..., "to":...} or
    {"task":"star","by":...} -- which is the page telling you its own answer. Ask the
    page, never the sentence (r169: an article is not a value).
    """
    cf = act.ev("(()=>{try{const c=window.core&&core.currentFields;"
                "return c?JSON.stringify(c):null}catch(e){return null}})()")
    fields = {}
    if cf:
        try:
            fields = json.loads(cf) if isinstance(cf, str) else dict(cf)
        except Exception:
            fields = {}
    bold = act.ev("(()=>{return [...document.querySelectorAll('#query .bold')]"
                  ".map(e=>e.textContent.trim())})()") or []
    g = goal or ""

    sender = str(fields.get("by") or (bold[0] if bold else "")).strip()
    dest = str(fields.get("to") or (bold[1] if len(bold) > 1 else "")).strip()
    # which verb? the page's own field first, then the sentence
    task = str(fields.get("task") or "").strip().lower()
    if not task:
        if re.search(r"\breply\b", g, re.I):
            task = "reply"
        elif re.search(r"\bforward\b|\bsend\b|\bsent to\b", g, re.I):
            task = "forward"
        elif re.search(r"\bdelete\b|\btrash\b|\bremove\b", g, re.I):
            task = "delete"
        elif re.search(r"\bimportant\b|\bstar\b", g, re.I):
            task = "star"
    if not sender:
        return "email-no-sender"
    if not task:
        return "email-no-verb"

    # the reply text is quoted in the plain variants and held in the page's own fields
    body = str(fields.get("reply") or "").strip()
    if not body:
        m2 = re.search(r'"([^"]+)"', g) or re.search(r"\u201c([^\u201d]+)\u201d", g)
        body = m2.group(1).strip() if m2 else ""

    opened = act.ev(
        "(()=>{const n=%s;const ts=[...document.querySelectorAll('#main .email-thread')];"
        "const t=ts.find(x=>{const s=x.getElementsByClassName('email-sender')[0];"
        "return s&&s.textContent.trim()===n});"
        "if(!t)return 'NOTHREAD';t.click();return 'ok'})()" % json.dumps(sender))
    if opened != "ok":
        # the list can be scrolled out of view or behind the search pane; try the search box
        return "email-%s:%s" % (str(opened).lower()[:12], str(sender)[:10])
    time.sleep(0.35)

    if task == "reply":
        act.click_el("document.querySelector('#email .email-reply')")
        time.sleep(0.30)
        if body:
            act.ev("(()=>{const t=document.querySelector('#reply-text');if(!t)return null;"
                   "t.focus();t.value=%s;"
                   "t.dispatchEvent(new Event('input',{bubbles:true}))})()" % json.dumps(body))
        act.click_el("document.querySelector('#send-reply')")
    elif task == "forward":
        act.click_el("document.querySelector('#email .email-forward')")
        time.sleep(0.30)
        if dest:
            act.ev("(()=>{const t=document.querySelector('#forward .forward-sender');"
                   "if(!t)return null;t.focus();t.value=%s;"
                   "t.dispatchEvent(new Event('input',{bubbles:true}))})()" % json.dumps(dest))
        # the body is pre-filled by the page: do not overwrite it, the score compares
        # the forwarded text to the original body exactly
        act.click_el("document.querySelector('#send-forward')")
    elif task == "delete":
        act.click_el("document.querySelector('#email .email-actions span.trash')")
    elif task == "star":
        act.click_el("document.querySelector('#email .email-actions span.star')")
    else:
        return "email-unknown-verb:%s" % task
    time.sleep(0.45)
    if episode_over(act):
        return "email-%s:%s" % (task, str(sender)[:10])
    return "email-miss-%s:%s" % (task, str(sender)[:10])


def v_date(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    """CHOOSE_DATE -- drive a jQuery UI datepicker to the date the goal names.

    Measured 2026-11-09, family 0/20 across four tasks.

    THE INPUT IS readOnly. #datepicker cannot be typed into, and the page scores
    `d3.select('#datepicker')[0][0].value === q` -- an EXACT string compare against the
    goal's own date text. So filling the field is not the task; picking the day is.

    THE PICKER OPENS ON A MOUSE PRESS, NOT ON ELEMENT.CLICK(). element.click() left
    .ui-datepicker at display:none; a real press at the input's centre opened it. This is
    the r170 lesson on a different control: a point is not an element, and here the
    converse -- the element is not a point.

    THE GRID SHOWS A MONTH THAT IS OFTEN NOT THE ONE ASKED FOR (opened on December 2016
    while the goal read 11/15/2016), so navigate the header with prev/next until the
    header matches, THEN take the day link. Other-month cells are
    ui-state-disabled with no <a>, so a day number alone is not enough -- match a cell
    that still has its link.

    The day is taken by exact text, not by index: the widget zero-pads the value itself
    (clicking 3 on April produced 04/03/2016), and the score is the exact string.
    """
    txt = goal or ""
    got = act.ev("(()=>{const q=document.querySelector('#query');return q?q.innerText:''})()") or txt
    md = re.search(r'(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})', got)
    if md:
        mo, day, yr = int(md.group(1)), int(md.group(2)), int(md.group(3))
    else:
        mn = re.search(r'([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})', got)
        if not mn or mn.group(1).lower() not in _MONTHS:
            return "date-noparse"
        mo, day, yr = _MONTHS[mn.group(1).lower()], int(mn.group(2)), int(mn.group(3))

    inp = ("document.querySelector('#datepicker')"
           "||document.querySelector('input[readonly]')"
           "||document.querySelector('.ui-datepicker-trigger')")
    if not act.ev("(()=>{return !!((()=>{try{return %s}catch(e){return null}})())})()" % inp):
        return "date-noinput"
    if act.ev("(()=>{const d=document.querySelector('.ui-datepicker');"
              "return d?getComputedStyle(d).display!=='none':false})()") is not True:
        b = act.box(inp)
        if not b:
            return "date-nobox"
        act.click(b["cx"], b["cy"])
        time.sleep(0.55)

    for _ in range(30):
        hdr = act.ev("(()=>{const t=document.querySelector('.ui-datepicker-title');"
                     "return t?t.innerText:null})()")
        if not hdr:
            return "date-noheader"
        hm = re.search(r'([A-Za-z]+)\s*(\d{4})', hdr)
        if not hm or hm.group(1).lower() not in _MONTHS:
            return "date-badheader:%s" % str(hdr)[:10]
        cm, cy = _MONTHS[hm.group(1).lower()], int(hm.group(2))
        if cm == mo and cy == yr:
            break
        # jQuery UI's own next/prev: this is the widget's navigation, not a guess
        act.click_el("document.querySelector('.ui-datepicker-%s')"
                     % ("next" if (cy, cm) < (yr, mo) else "prev"))
        time.sleep(0.30)
    else:
        return "date-navfail"

    ok = act.ev(
        "(()=>{const d=String(%d);const tds=[...document.querySelectorAll("
        "'.ui-datepicker-calendar td')];"
        "const td=tds.find(x=>{const a=x.querySelector('a');"
        "return a&&a.textContent.trim()===d&&!x.className.includes('other-month')});"
        "if(!td)return 'NODAY';td.querySelector('a').click();return 'ok'})()" % day)
    if ok != "ok":
        return "date-noday:%s" % str(ok)[:10]
    time.sleep(0.40)
    if not episode_over(act):
        submit(act, required=False)
        time.sleep(0.25)
    val = act.ev("document.querySelector('#datepicker').value")
    return "date:%s" % (val or "?")


_SIZE_WORDS = {"large", "small", "big", "little"}
_COLOUR_WORDS = {"red", "orange", "yellow", "green", "blue", "purple", "violet",
                 "black", "white", "gray", "grey", "brown", "pink", "cyan", "magenta"}


def v_count(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    """Read the page, count what the sentence describes, and answer the question.

    Measured 2026-11-09 on `count-shape`, 0/30 and REFUSED. The decomposer has no verb for
    a QUESTION at all: "How many small Qs are there?" contains none of the 19 action
    words, so it was refused before anything looked at the page.

    THE PAGE DESCRIBES ITS OWN OBJECTS, and the description grammar is exactly three
    parts (see common/shapes.js generalDesc): SIZE, COLOUR, TEXT/TYPE. The glyphs are SVG
    <text> elements that carry `fill` and `font-size` -- 20px is large, 10px is small --
    so every attribute the sentence can name is readable without vision.

    THE ANSWER IS ENTERED BY PRESSING ONE OF FIVE OFFERED NUMBERS. The page renders the
    true count and four decoys as buttons, so the count has to be exact: pressing a
    decoy is a -1, not a retry.
    """
    g = goal or ""
    low = g.lower()
    want_col = next((c for c in _COLOUR_WORDS if re.search(r"\b%s\b" % c, low)), None)
    if want_col == "violet":
        want_col = "purple"
    if want_col == "grey":
        want_col = "gray"
    want_size = None
    if re.search(r"\blarge\b|\bbig\b", low):
        want_size = "large"
    elif re.search(r"\bsmall\b|\blittle\b", low):
        want_size = "small"
    # THE NOUN. The page's description grammar is SIZE + COLOUR + TEXT, and the text part
    # is either a single character ("How many small Qs") or the literal word "item"
    # ("How many green items"), which describes NOTHING and must not become a filter.
    # Take the last word of the question as the noun and keep it only when it is one
    # character -- anything longer is a class word the page never stores per glyph.
    # THE NOUN CAN NAME A CLASS OF NODE, A SINGLE CHARACTER, OR NOTHING.
    # The grid draws THREE kinds of node -- rect, circle, and <text> glyphs -- and the
    # question can ask about any of them: "How many red shapes" counts all three,
    # "How many digits" counts only numeric glyphs, "How many small Qs" counts one
    # letter. Enumerating only <text> made every "shapes" and "digits" question wrong.
    want_text = None
    _noun = re.search(r"how many\s+(.+?)\s+(?:are|is)\b", low)
    _noun_words = []
    if _noun:
        # KEEP CASE. "How many Is" and "How many 0s" name a GLYPH, and lowercasing turns
        # "Is" into the English word "is" and "0s" into a token that matches no glyph.
        # Only the colour and size words are case-insensitive; the rest is a symbol.
        # ONE RULE, and the noun is only ever the LAST word: "small aqua ts" -> "ts".
        # A single glyph may be written alone ("Q") or pluralised ("Qs", "0s", "Is");
        # every other word is a class word ("items", "shapes", "rectangles") and is
        # classified below, never treated as a glyph. Splitting these into two competing
        # rules is what broke this function the first time.
        _raw = [w.strip(".,;:!?") for w in re.split(r"\s+", _noun.group(1).strip())
                if w.strip(".,;:!?")]
        _raw = [w for w in _raw
                if w.lower() not in _COLOUR_WORDS and w.lower() not in _SIZE_WORDS]
        if _raw:
            _lastn = _raw[-1]
            if len(_lastn) == 1:
                _noun_words = [_lastn]
            elif len(_lastn) == 2 and _lastn.endswith("s") and _lastn[0].isalnum():
                _noun_words = [_lastn[0]]
            else:
                _noun_words = [_lastn.lower()]
    want_kind = None
    if _noun_words:
        _w = _noun_words[-1]
        if _w in ("shapes", "shape", "items", "item", "objects", "object"):
            pass                      # everything counts
        elif _w in ("digits", "digit", "numbers", "number"):
            want_kind = "digit"
        elif _w in ("letters", "letter", "characters", "character"):
            want_kind = "letter"
        # A NAMED GEOMETRY IS A TAG FILTER. "How many rectangles" counts <rect>
        # nodes, not every node -- copying the whole node set gave 9 where the offered
        # answers were 1,3,5,8,9 and the truth was one of them.
        elif _w.rstrip("s") in ("rectangle", "square", "box"):
            want_kind = "rect"
        elif _w.rstrip("s") in ("circle", "ring", "dot"):
            want_kind = "circle"
        elif _w.rstrip("s") in ("triangle", "polygon"):
            want_kind = "polygon"
        elif _w.rstrip("s") == "ellipse":
            want_kind = "ellipse"
        elif len(_w) == 1:
            want_text = _w.upper()
        elif _w.endswith("s") and len(_w) == 2:
            want_text = _w[0].upper()

    nodes = act.ev(
        "(()=>{try{const out=[];"
        "document.querySelectorAll('#area svg text,#area svg rect,#area svg circle,"
        "#area svg ellipse,#area svg polygon').forEach(function(e){"
        "const fs=parseFloat(e.getAttribute('font-size')||'10');"
        "out.push({tag:e.tagName,t:(e.textContent||'').trim(),"
        "col:(e.getAttribute('fill')||'').toLowerCase(),fs:fs})});"
        "return out}catch(err){return 'ERR:'+err.message}})()")
    if not isinstance(nodes, list):
        return "count-nodes:%s" % str(nodes)[:16]
    n = 0
    for o in nodes:
        col = str(o.get("col") or "")
        txt = str(o.get("t") or "")
        size = "large" if float(o.get("fs") or 10) >= 16 else "small"
        if want_col and want_col not in col:
            continue
        if want_size and size != want_size:
            continue
        if want_text and txt.upper() != want_text:
            continue
        if want_kind == "digit" and not txt.isdigit():
            continue
        if want_kind == "letter" and not (txt.isalpha() and len(txt) == 1):
            continue
        if want_kind in ("rect", "circle", "polygon", "ellipse"):
            if str(o.get("tag") or "").lower() != want_kind:
                continue
        n += 1
    pressed = act.ev(
        "(()=>{try{const bs=[...document.querySelectorAll('#count-buttons button')];"
        "const b=bs.find(x=>(x.textContent||'').trim()===String(%d));"
        "if(!b)return 'NOBTN:'+bs.map(x=>x.textContent.trim()).join(',');"
        "b.click();return 'ok'}catch(err){return 'ERR:'+err.message}})()" % n)
    time.sleep(0.40)
    if episode_over(act):
        return "count:%d" % n
    return "count-miss:%d/%s" % (n, str(pressed)[:26])


def v_highlight(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    """Select the paragraph's text with a real Range, then Submit.

    Measured 2026-11-09: `highlight-text` and `highlight-text-2`, both 0/30 and both
    VERB_NOT_IMPLEMENTED. The decomposer already emitted HIGHLIGHT; nothing listened.

    A HIGHLIGHT IS NOT A DRAG. The page scores
        window.getSelection().toString().replace(/[\n\r\s]/g, '')
    so what matters is that the DOCUMENT'S SELECTION covers exactly the paragraph --
    whitespace is ignored, so a Range over the whole node is correct even though it
    includes trailing spaces. Dragging across the text is slower, breaks when the
    paragraph wraps, and cannot reach the last line reliably. Set the Range.

    `-2` shows several paragraphs and names ONE by position; the goal's own words carry
    the ordinal, and every paragraph is in DOM order, so take that index.
    """
    g = goal or ""
    # which paragraph? the goal says "the first/second/third ... paragraph"
    # THE ORDINAL CAN BE A WORD OR A NUMERAL: highlight-text-2 says "the 2nd paragraph",
    # not "the second". Matching only the word left idx at 0, which then selected the
    # CONTAINER and produced 103-128 characters instead of one paragraph.
    idx = 0
    _o = re.search(r"\b(\d+)(?:st|nd|rd|th)\b", g)
    if _o:
        idx = max(0, int(_o.group(1)) - 1)
    else:
        for _i, _w in enumerate(("first", "second", "third", "fourth", "fifth")):
            if re.search(r"\b%s\b" % _w, g, re.I):
                idx = _i
                break
    # A PARAGRAPH IS A LEAF, and the JS must never throw silently: without a try/catch a
    # syntax error returns null, which the caller reads as "nothing found" (r171's bug).
    JS_HL = (
        "(()=>{try{"
        "var ps=[...document.querySelectorAll('#area p,#area div,#area span')].filter(function(e){"
        "var r=e.getBoundingClientRect();"
        "if(!(r.width>20&&r.height>8))return false;"
        "var t=(e.innerText||'').trim();"
        "if(t.length<2)return false;"
        "if(e.querySelector('button'))return false;"
        "var kids=e.children,i;"
        "for(i=0;i<kids.length;i++){if(((kids[i].innerText||'').trim().length>2))return false}"
        "return true});"
        "if(!ps.length)return 'NOPARA';"
        "var p=ps[Math.min(%d,ps.length-1)];"
        "var rg=document.createRange();rg.selectNodeContents(p);"
        "var s=window.getSelection();s.removeAllRanges();s.addRange(rg);"
        "return (s.toString()||'').replace(/[\\n\\r\\s]/g,'').length"
        "}catch(err){return 'ERR:'+err.message}})()" % idx)
    done = act.ev(JS_HL)
    if not isinstance(done, int) or done <= 0:
        return "highlight-%s" % str(done)[:12]
    submit(act, required=False)
    time.sleep(0.30)
    if episode_over(act):
        return "highlight:%d" % done
    return "highlight-miss:%d" % done


def v_copy_paste(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    """Copy the text out of one field and put it in another.

    Measured 2026-11-09: `copy-paste` and `copy-paste-2`, both VERB_NOT_IMPLEMENTED.
    The decomposer was already emitting COPY_PASTE with a correct status; nothing was
    listening. That is the r120 defect exactly -- a verb the pipeline produces and the
    dispatcher does not have.

    THE SOURCE IS A FIELD, NOT A CLIPBOARD. The page writes a sentence into a textarea
    and scores the SECOND field against it, so this is a value transfer inside the DOM.
    Reading `.value` is exact and instant; driving a real clipboard through focus,
    select-all and copy is slower and depends on permissions the page never grants.
    Read the value, write the value, read it back.
    """
    g = goal or ""
    # which field is which? "the 2nd input into the 3rd input" -- the page supplies
    # the order in the sentence, and the fields are the typed controls in DOM order
    nums = [int(x) for x in re.findall(r"\b(\d+)(?:st|nd|rd|th)\b", g)]
    # WHICH FIELD IS THE SOURCE? In `copy-paste-2` ALL the textareas are full and the
    # goal names one by position ("from the <2nd> text area"), so 'the first non-empty
    # field' is wrong two times in three. The page marks the position in span.bold --
    # read the ordinal from there, and only fall back to 'first non-empty' when the goal
    # names no position at all.
    _ord = act.ev("(()=>{const p=document.querySelector('#query .bold');"
                  "return p?p.textContent.trim():null})()")
    _which = None
    if _ord:
        _m = re.search(r"(\d+)", str(_ord))
        if _m:
            _which = int(_m.group(1))
        else:
            for _i, _w in enumerate(("first", "second", "third", "fourth", "fifth",
                                     "1st", "2nd", "3rd", "4th", "5th")):
                if _w in str(_ord).lower():
                    _which = ("first second third fourth fifth".split()).index(
                        _w.rstrip("0123456789nrdst")) + 1 if _w.rstrip("0123456789nrdst") in (
                        "first second third fourth fifth") else _i % 5 + 1
                    break
    src = act.ev(
        "(()=>{const es=[...document.querySelectorAll('textarea,input[type=text],"
        "input:not([type])')].filter(e=>{const r=e.getBoundingClientRect();"
        "return r.width>0&&r.height>0});"
        "const areas=[...document.querySelectorAll('textarea')]"
        ".filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0});"
        "const want=%s;"
        "if(want!==null&&areas[want-1]&&String(areas[want-1].value||'').length)"
        "return {n:es.length,v:areas[want-1].value,i:es.indexOf(areas[want-1])};"
        "const withText=es.filter(e=>String(e.value||'').length>0);"
        "if(!withText.length)return null;"
        "return {n:es.length,v:withText[0].value,"
        "i:es.indexOf(withText[0])}})()" % ("null" if _which is None else str(_which)))
    if not isinstance(src, dict) or not src.get("v"):
        return "copy-nosource"
    seq = 0 if nums else None
    # target: the visible empty typed field; if the goal numbers them, honour the order
    ok = act.ev(
        "(()=>{const want=%s;const es=[...document.querySelectorAll("
        "'textarea,input[type=text],input:not([type])')]"
        ".filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0});"
        "let t=null;"
        "if(want!==null&&es[want-1]&&es[want-1]!==document.activeElement)t=es[want-1];"
        "if(!t)t=es.find(e=>e!==null&&e!==es[%d]&&String(e.value||'').length===0);"
        "if(!t)return null;"
        "t.focus();t.value=%s;"
        "t.dispatchEvent(new Event('input',{bubbles:true}));"
        "t.dispatchEvent(new Event('change',{bubbles:true}));"
        "return t.value})()" % ("null" if seq is None else "null",
                                int(src.get("i") or 0),
                                json.dumps(str(src["v"]))))
    if not ok:
        return "copy-notarget"
    # index from the sentence, when it names one (1-based, "the 3rd input")
    if len(nums) >= 2:
        act.ev(
            "(()=>{const es=[...document.querySelectorAll('textarea,input[type=text],"
            "input:not([type])')].filter(e=>{const r=e.getBoundingClientRect();"
            "return r.width>0&&r.height>0});const t=es[%d];if(!t)return null;"
            "t.focus();t.value=%s;"
            "t.dispatchEvent(new Event('input',{bubbles:true}));"
            "t.dispatchEvent(new Event('change',{bubbles:true}))})()"
            % (nums[-1] - 1, json.dumps(str(src["v"]))))
    submit(act, required=False)
    time.sleep(0.30)
    if episode_over(act):
        return "copy-paste:%d->ok" % len(str(src["v"]))
    return "copy-paste-miss"


def v_pie(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    """EXPAND_AND_CLICK on a wheelnav (Raphael SVG) pie menu.

    Measured 2026-11-09 on `click-pie`, 0/30 before this. Every step below was found by
    printing what the code chose; each one alone was enough to score zero:

      * THE WHEEL STARTS COLLAPSED at currentPercent 0 behind a centre spreader path.
        Until it is pressed the slices exist with d="M78,78L78,78" -- zero length.
      * IT IS STILL ANIMATING WHEN YOU CAN SEE IT. Raphael grows the slices over ~1 s;
        a geometry read taken as soon as the spreader is pressed samples the animation
        (path length 22 -> 135 -> 212). Sample until it stops changing.
      * THE LABEL IS ON THE PAGE, NOT IN THE SENTENCE: #query wraps the answer in
        span.bold, so the goal's own markup hands over the target.
      * GETPOINTATLENGTH IS NOT A POINT INSIDE THE SHAPE. A donut sector's path is its
        OUTLINE, so 50% of the length is the radial edge, and elementFromPoint there
        returns the NEIGHBOURING slice (this page: 261/400 sampled points on the edge
        hit-tested to slice 5 and 6, not the slice whose path they came from).
        So do not compute a point -- ask the page which points belong to the slice by
        sweeping the SVG bounds with elementFromPoint and taking the CENTROID of its own
        hits. That is the same hit-test the click will use.
      * SVGElement has no .click(); that is HTMLElement-only, and the throw is swallowed
        by the caller's `or []`, which reads as "nothing found".
    """
    want = act.ev("(()=>{const b=document.querySelector('#query .bold');"
                  "return b?b.textContent.trim():null})()")
    if not want:
        m = re.search(r'labeled\s*"?\s*([^".\u201d]+)', goal, re.I)
        want = m.group(1).strip() if m else (plan.get("operand") or {}).get("quoted")
    if not want:
        return "pie-no-label"
    sp = act.ev("(()=>{const e=[...document.querySelectorAll('[id$=-spreader]')]"
                ".find(x=>x.getBoundingClientRect().width>0);"
                "if(!e)return null;const r=e.getBoundingClientRect();"
                "return {x:r.x+r.width/2,y:r.y+r.height/2}})()")
    if not sp:
        return "pie-no-spreader"
    act.click(sp["x"], sp["y"])

    sid = act.ev("(()=>{const want=%s;"
                 "const t=[...document.querySelectorAll('[id*=-title-]')]"
                 ".find(e=>e.textContent.trim()===want);"
                 "return t?t.id.replace('-title-','-slice-'):''})()" % json.dumps(str(want)))
    if not sid:
        return "pie-nolabel:%s" % str(want)[:8]
    # wait for Raphael's expansion animation to finish, then take the page's own hit-test
    prev = -1.0
    pt = None
    for _ in range(24):
        time.sleep(0.10)
        r = act.ev(
            "(()=>{const sid=%s;const s=document.getElementById(sid);"
            "if(!s)return null;const L=s.getTotalLength();"
            "const svg=document.querySelector('#divWheel svg');"
            "if(!svg)return null;const R=svg.getBoundingClientRect();"
            "let n=0,sx=0,sy=0;"
            "for(let x=R.x;x<R.x+R.width;x+=3){for(let y=R.y;y<R.y+R.height;y+=3){"
            "const el=document.elementFromPoint(x,y);"
            "if(el&&el.id===sid){n++;sx+=x;sy+=y}}}"
            "return {L:L,n:n,x:n?sx/n:0,y:n?sy/n:0}})()" % json.dumps(sid))
        if not r:
            continue
        if r["n"] and prev > 0 and abs(r["L"] - prev) < 0.5:
            pt = r
            break
        prev = r["L"]
        if r["n"]:
            pt = r
    if not pt or not pt["n"]:
        return "pie-nohit:%s" % str(want)[:8]
    act.click(pt["x"], pt["y"])
    time.sleep(0.45)
    if episode_over(act):
        return "pie-click:%s" % str(want)[:8]
    return "pie-miss:%s" % str(want)[:8]


def v_expand(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    """EXPAND_AND_CLICK -- open the hidden sections, then click the link the goal NAMES.

    Measured 2026-11-09 on `click-collapsible-2`: the page is a jQuery UI Accordion,
    h3.ui-accordion-header with aria-expanded. Two things had to be right and both were
    wrong before this:
      * the headers must be CLICKED ONE AT A TIME -- the accordion closes the previously
        open panel, so the target is only reachable while its own section is open;
      * the target is a <span> inside the panel and the score comes from clicking THE
        ELEMENT. A CDP mouse event at its centre scored 0 on the same page where
        element.click() scored 1. A point is not an element -- the same defect that made
        phone-book fail.
    """
    # A WHEEL IS NOT AN ACCORDION. One element in the DOM says which shape this is, so
    # ask it before touching any header -- click-pie has no header to click at all.
    if act.ev("document.querySelectorAll('[id*=-slice-]').length") > 2:
        return v_pie(act, plan, goal)

    tok = (plan.get("operand") or {}).get("quoted")
    if tok is None:
        m = re.search(r'"([^"]+)"', goal) or re.search(r"\u201c([^\u201d]+)\u201d", goal)
        tok = m.group(1).strip() if m else None
    if not tok:
        # NOT EVERY EXPAND NAMES A LINK. "Expand the section below and click submit."
        # names no target at all -- the instruction is to open the section and press the
        # page's own submit. My r171 rewrite returned expand-no-token here and broke a task
        # that had been passing 5/5 before it.
        #
        # AND AN ACCORDION HAS MORE THAN ONE HEADER. jQuery UI wraps EVERY direct child in
        # one: this page has the <h3> AND the <p> that holds #subbtn. Clicking "every
        # collapsed header" opens the section then closes it again, and the loop ended on
        # the closed state. jQuery UI reports openness with aria-expanded, which IS valid
        # CSS -- read that, and stop as soon as the page says a panel is open.
        # (Also: `:visible` is a jQuery extension, not CSS. querySelectorAll(':visible')
        # THROWS, and a probe that swallows the throw prints null as if it were a state.)
        opened = 0
        for _ in range(6):
            if act.ev("document.querySelectorAll('#area .ui-accordion-header[aria-expanded=true]"
                      ",#area [role=tab][aria-expanded=true]').length"):
                break
            h = act.ev(
                "(()=>{const e=document.querySelector('#area .ui-accordion-header');"
                "if(!e)return null;const r=e.getBoundingClientRect();"
                "return {cx:r.x+r.width/2,cy:r.y+r.height/2}})()")
            if not h:
                break
            act.click(h["cx"], h["cy"])
            time.sleep(0.35)
            opened += 1
        submit(act, required=False)
        return "expand-all-submit:%d" % opened

    heads = act.ev(
        # the arrow body was a BARE expression, so `(()=>[...].map(...)()` invoked the
        # map's result as a function and returned undefined. It has to return.
        "(()=>{return [...document.querySelectorAll('h3.ui-accordion-header,h4.ui-accordion-header,"
        ".ui-accordion-header,[role=tab]')].map(e=>{const r=e.getBoundingClientRect();"
        "return {cx:r.x+r.width/2,cy:r.y+r.height/2,exp:e.getAttribute('aria-expanded')}})})()"
    ) or []
    if not heads:
        heads = act.ev(
            "(()=>{return [...document.querySelectorAll('#area button,#area div,#area h1,"
            "#area h2,#area h3')].filter(e=>{const r=e.getBoundingClientRect();"
            "return r.width>20&&r.height>6&&(e.innerText||'').trim()}).map(e=>{"
            "const r=e.getBoundingClientRect();"
            "return {cx:r.x+r.width/2,cy:r.y+r.height/2}})})()"
        ) or []

    for h in heads:
        act.click(h["cx"], h["cy"])
        time.sleep(0.30)
        # the target only exists while its section is open
        el = act.ev(
            # compare with punctuation REMOVED ON BOTH SIDES. The goal quotes
            # "scelerisque" and the span reads "scelerisque." -- an exact test failed on
            # the full stop for every token in this task.
            "(()=>{const norm=x=>(x||'').trim().toLowerCase().replace(/[.,;:!?]+$/,'');"
            "const want=norm(%s);"
            "for(const e of document.querySelectorAll('#area a,#area span,#area div')){"
            "if(norm(e.innerText)===want){"
            "const r=e.getBoundingClientRect();"
            "if(r.width>0&&r.height>0){e.setAttribute('data-agent-target','1');"
            "return 'ok'}}}return ''})()" % json.dumps(tok))
        if el:
            # THE ELEMENT, NOT ITS CENTRE: the accordion re-renders on animation frames
            # and a coordinate resolved a moment earlier can land on the panel instead.
            act.ev("(()=>{const e=document.querySelector('[data-agent-target=\"1\"]');"
                   "if(e)e.click()})()")
            time.sleep(0.45)
            if episode_over(act):
                return "expand-click:%s" % str(tok)[:12]
    return "expand-miss:%s" % str(tok)[:12]


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
_POSITIONAL_PLAN: dict = {}
_POSITIONAL_ROLES = {"genre", "director", "year"}

_ROLE_WORDS = {
    "origin": ("departurecity", "departure city", "origin", "from", "departure", "source"),
    "destination": ("arrivalcity", "arrival city", "destination", "to", "arrival", "dest"),
    "depart": ("departuredate", "departure date", "depart", "start date", "checkin", "on"),
    "return": ("returndate", "return date", "return", "checkout", "back"),
    "date": ("date", "day"),
    "amount": ("amount", "total", "price", "sum", "value"),
    "email": ("email", "mail", "user", "login", "account"),
}


def _control_identity(c: Mapping[str, Any]) -> str:
    """Everything a control says about what it is, as one lowercase string.

    Real applications name their inputs structurally, not narratively: the Alaska booking
    page calls its departure field `SearchFields.DepartureCity`. Matching the goal's words
    against the element's TEXT finds nothing there, because an empty input has no text.
    """
    return " ".join(str(c.get(k) or "") for k in
                    ("id", "name", "declared", "placeholder", "aria", "type")).lower()


def v_fill_form(act: Actuator, plan: Mapping[str, Any], goal: str) -> str:
    """FILL_FORM -- bind the values a sentence states to the controls a page offers.

    This is the general case of most computer use, and its absence was measured: the Alaska
    flight page exposes SearchFields.DepartureCity / ArrivalCity / DepartureDate /
    ReturnDate, the goal states all four values, and the pipeline answered UNSUPPORTED_VERB.

    Binding is by ROLE, not by order: a field receives a value because its name or label
    says what it is. A slot with no matching control is skipped and reported; a control that
    matches two slots takes the first. Nothing is guessed into a field.
    """
    wanted = dict((plan.get("operand") or {}).get("slots") or {})
    if not wanted:
        return "fill-no-slots"

    controls = act.ev(
        "(()=>{const out=[];"
        "for(const e of document.querySelectorAll('input,select,textarea')){"
        "const r=e.getBoundingClientRect();"
        "if(r.width<=0||r.height<=0)continue;"
        "if(['hidden','submit','button','checkbox','radio','file'].includes(e.type))continue;"
        "out.push({id:e.id||'',name:e.name||'',placeholder:e.placeholder||'',"
        "aria:e.getAttribute('aria-label')||'',type:e.type||e.tagName.toLowerCase(),"
        "declared:((typeof e.className==='string')?e.className:''),"
        "cx:r.x+r.width/2,cy:r.y+r.height/2,a:r.width*r.height});}"
        "return out})()") or []
    if not controls:
        return "fill-no-controls"

    filled, skipped = [], []
    used: set = set()
    # A PLAN, NOT A SEARCH. If the sentence supplies exactly the three fields an
    # anonymous form offers, the assignment is decided before any typing starts.
    _POSITIONAL_PLAN[id(plan)] = {}
    if _POSITIONAL_ROLES.issubset(set(wanted)):
        _order = [r for r in ("genre", "director", "year") if r in wanted]
        _anon = list(controls)
        if len(_anon) >= len(_order):
            for _r, _c in zip(_order, _anon[:len(_order)]):
                _POSITIONAL_PLAN[id(plan)][_r] = _c
    for role, value in wanted.items():
        words = _ROLE_WORDS.get(role, (role,))
        best, best_score = None, 0
        for c in controls:
            key = (c["cx"], c["cy"])
            if key in used:
                continue
            ident = _control_identity(c)
            score = sum(3 if w in ident else 0 for w in words)
            if any(_norm_eq(w) == _norm_eq(c.get("id", "")) for w in words):
                score += 4
            if score > best_score:
                best, best_score = c, score
        if not best or best_score == 0:
            # AN ANONYMOUS FIELD TAKES THE VALUE BY POSITION, BUT ONLY AS A FALLBACK.
            #
            # multi-layouts renders three <input type=text> with no id, no placeholder and
            # no label. Nothing on the page says which is which, so name binding scores
            # zero for every role. The sentence states genre, director, year in that order
            # and the task source declares genreBox, nameBox, yearBox in that order. This
            # branch runs ONLY when no field matched by name and ONLY for the remaining
            # unbound controls in document order, so a page that names its fields is
            # completely unaffected by it.
            # The positional plan is computed ONCE from the ORIGINAL control order and
            # held for the whole loop. Recomputing a "free" list inside the loop shifted
            # the indices as controls were used, so multi-layouts filled genre into box1
            # and director into box3 with box2 empty, then skipped year.
            _pin = _POSITIONAL_PLAN.get(id(plan)) or {}
            if role in _pin:
                best, best_score = _pin[role], 1
        if not best or best_score == 0:
            skipped.append(role)
            continue
        used.add((best["cx"], best["cy"]))
        # FOCUS IS NOT A CLICK. On the Alaska booking page a click on the date field leaves
        # document.activeElement as BODY -- the page takes focus back -- so typing after a
        # click wrote nothing and the action string still said "filled:depart=March 2". The
        # correction is to assert the focus target and VERIFY it before typing, then verify
        # the value after. A fill that cannot be read back is not a fill.
        act.ev("(()=>{const e=document.elementFromPoint(%f,%f);"
               "if(e)e.focus();})()" % (best["cx"], best["cy"]))
        time.sleep(0.05)
        focused = act.ev("(()=>{const e=document.activeElement;"
                         "return e?(e.id||e.name||e.tagName):''})()")
        act.ev("(()=>{const e=document.activeElement;"
               "if(e&&e.value!==undefined){e.value='';"
               "e.dispatchEvent(new Event('input',{bubbles:true}))}})()")
        # A SUGGESTION FIELD ACCEPTS ONLY WHAT WAS CHOSEN FROM ITS LIST.
        #
        # Measured 2026-11-09 on `book-flight`: the field is a jQuery autocomplete.
        # Typing the whole value ("Pasco, WA") opens NO list, because the list matches on
        # the leading text; the field then holds text the page never accepted, `search`
        # does nothing, and the reward stays 0 while the action string says filled. Typing
        # a prefix ("Roche") opens "Roche Harbor, WA (RCE) / Rochester, MN (RST) / ...".
        # So: type a PREFIX, wait for the list, and click the entry that contains the
        # value the sentence supplied. If no list appears the field is a plain input and
        # the old behaviour is unchanged.
        _typed_as_prefix = False
        try:
            _probe = str(value).split(",")[0].strip()
            _probe = _probe.split("/")[0].strip()[:5] or str(value)[:5]
            act.type_text(_probe)
            _typed_as_prefix = True
            time.sleep(0.55)
        except Exception:  # noqa: BLE001
            _typed_as_prefix = False
        if not _typed_as_prefix:
            act.type_text(str(value))
        act.ev("(()=>{const e=document.activeElement;if(e){"
               "e.dispatchEvent(new Event('input',{bubbles:true}));"
               "e.dispatchEvent(new Event('change',{bubbles:true}));"
               "e.dispatchEvent(new Event('blur',{bubbles:true}))}})()")
        time.sleep(0.10)
        # FALLBACK, not replacement: if the keystrokes did not land, set the value directly.
        # READ THE FIELD BACK BY POINT, NOT BY ID.
        #
        # Measured 2026-11-09 on multi-layouts: three anonymous <input type=text> with
        # id === "". This read-back used document.getElementById("") which is null for
        # every one of them, so a fill that HAD landed was judged not-landed and the role
        # was skipped -- "filled:none;skipped:genre,director,year" on a form that was
        # filling correctly. The control is identified by the point the page gave for it;
        # elementFromPoint is the same point the focus step used.
        _READ_BACK = ("(()=>{const e=document.elementFromPoint(%f,%f);"
                      "if(!e||e.value===undefined)return null;return e.value;})()"
                      % (best["cx"], best["cy"]))
        landed = act.ev("(()=>{const e=document.getElementById(%s);"
                        "if(!e)return null;return e.value;})()" % json.dumps(best["id"])) \
            if best.get("id") else act.ev(_READ_BACK)
        if not landed:
            _SEL = ("document.getElementById(%s)" % json.dumps(best["id"])) \
                if best.get("id") else ("document.elementFromPoint(%f,%f)" % (best["cx"], best["cy"]))
            act.ev("(()=>{const e=%s;"
                   "if(!e)return;e.focus();e.value=%s;"
                   "e.dispatchEvent(new Event('input',{bubbles:true}));"
                   "e.dispatchEvent(new Event('change',{bubbles:true}));})()"
                   % (_SEL, json.dumps(str(value))))
            time.sleep(0.06)
            landed = act.ev("(()=>{const e=document.getElementById(%s);"
                            "return e?e.value:null})()" % json.dumps(best["id"])) \
                if best.get("id") else act.ev(_READ_BACK)
        if not landed:
            skipped.append(role + ":NOT_APPLIED")
            continue
        # A FIELD THAT OFFERS A MENU IS NOT FILLED UNTIL THE MENU IS CHOSEN.
        # (this runs after the prefix typing above, which is what opens the menu)
        #
        # Measured 2026-11-09 on `book-flight`: the page exposes #flight-from with
        # placeholder "From:". Typing "BWD" leaves e.value == "BWD" and opens a single
        # suggestion, "Brawnwood, TX (BWD)". The field LOOKS filled and the page's own
        # state is still unset, so the booking validates as empty and the episode scores
        # zero -- with an action string that says filled. Reading the value back is not
        # proof the page accepted it; the page's suggestion list is the thing that has to
        # be answered. The menu is matched on the value the goal supplied, so this cannot
        # pick a suggestion the instruction did not ask for.
        try:
            _item = act.ev(
                "(()=>{const want=%s.toLowerCase();"
                "const li=[...document.querySelectorAll('.ui-menu-item,.ui-autocomplete li,[role=option]')];"
                "for(const e of li){const t=(e.innerText||'').toLowerCase();"
                "if(t.includes(want)){const r=e.getBoundingClientRect();"
                "if(r.width>0&&r.height>0)return r.x+r.width/2+','+(r.y+r.height/2)}}"
                "return ''})()" % json.dumps(str(value)))
            if _item:
                _cx, _cy = [float(x) for x in str(_item).split(",")]
                act.click(_cx, _cy)
                time.sleep(0.12)
        except Exception:  # noqa: BLE001 - a menu that is not there is not a failure
            pass
        filled.append("%s=%s" % (role, value))

    # submit, if the page has anything that looks like one
    for sel in ("document.querySelector('input[type=submit]')",
                "(()=>{return [...document.querySelectorAll('button,input[type=button],a')]"
                ".find(b=>/find flights|search|submit|book|go|continue/i.test("
                "(b.innerText||b.value||'')))})()"):
        if act.click_el(sel):
            time.sleep(0.35)
            break
    # A FORM IS NOT SUBMITTED UNTIL THE CONTROL THAT SUBMITS IT IS PRESSED.
    #
    # Measured 2026-11-09 on `book-flight`: after this filler ran, the page held
    # flight-from=Manistee, flight-to=Anchorage, datepicker=12/27/2016 -- every value the
    # sentence supplied, correctly bound -- and the reward was 0, because the page's own
    # `search` button was never pressed. The form was complete and unfinished. Submit is
    # attempted only when a submit-shaped control exists, and it is not required, so a
    # page without one is unchanged.
    try:
        if filled:
            _btn = act.ev(
                # A SUBMIT CONTROL IS NOT ALWAYS A BUTTON.
                #
                # Measured 2026-11-09 on multi-layouts: the five layouts each render their
                # own submit control, and the one this page sampled was a styled
                # div.ui-submit with a click handler -- `button,input[type=submit],
                # [role=button]` matched nothing and the checker never ran, so a form with
                # every value correct scored 0 forever. The selector now includes the
                # class-based control the corpus actually uses.
                "(()=>{const b=[...document.querySelectorAll("
                "'button,input[type=submit],[role=button],.ui-submit,.submit,.btn')]"
                ".filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0});"
                "const h=b.find(e=>/search|submit|find|go|book|continue/i.test("
                "(e.id||'')+' '+(e.innerText||'')+' '+(e.value||'')));"
                "if(!h)return '';const r=h.getBoundingClientRect();"
                "return (r.x+r.width/2)+','+(r.y+r.height/2)})()")
            if _btn:
                _bx, _by = [float(x) for x in str(_btn).split(",")]
                act.click(_bx, _by)
                time.sleep(0.20)
    except Exception:  # noqa: BLE001
        pass
    return "filled:%s%s" % (";".join(filled) or "none",
                            (";skipped:" + ",".join(skipped)) if skipped else "")


def _norm_eq(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(text or "").lower())


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

    # A RADIO IS A CHECKBOX THAT PERMITS ONE.
    #
    # Measured 2026-11-09 on the public task `click-option`: 1 success in 12 runs.
    # The goal is "Select RzWv and click Submit." with six radios and NO <select>.
    # The verb was SELECT, so dispatch went to v_native_select, which drives
    # #options, found nothing, submitted with nothing checked, and scored -1.
    # Called directly, v_checkboxes scored 1.0 on the first try -- the solver was
    # never wrong, the ROUTE was. The matcher is "the page has radios and the goal
    # names something to select", which is the same shape as the checkbox case and
    # does not depend on the verb word.
    if "radio" in kinds and "select" in g.lower():
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
        "FILL_FORM": v_fill_form,
        "SET_SLIDERS": v_slider, "SCROLL_TO": v_scroll, "ENTER": v_type,
        "FIND_AND_TYPE": v_type, "DRAW": v_draw_line, "MOVE": v_move_cube,
        "PUSH_SEQUENCE": v_push_sequence, "FOCUS": v_focus, "SWITCH_TABS": v_tabs,
        "EXPAND_AND_CLICK": v_expand, "CLICK": v_click, "CHOOSE_DATE": v_date,
        "COPY_PASTE": v_copy_paste, "HIGHLIGHT": v_highlight, "COUNT": v_count,
    }
    if verb == "DRAG":
        if "black box" in g.lower():
            return v_draw_shapes(act, goal)
        return v_drag_box(act, plan, goal)
    if verb == "SELECT":
        # A DATEPICKER IS A SELECT AND NONE OF THE OTHER DRIVERS CAN SEE IT. The input is
        # readOnly, so the generic path types at a field that refuses text; the score is
        # the widget's own value string. Ask the page which shape it is, first.
        if act.ev("(()=>{return !!document.querySelector('.ui-datepicker')"
                  "||!!document.querySelector('input[readonly]')})()"):
            return v_date(act, plan, goal)
        if op.get("path"):
            return v_menu(act, plan, goal)
        if op.get("colour"):
            return v_colour(act, plan, goal)
        # THE VERB IS A CLAIM ABOUT THE PAGE, AND IT CAN BE WRONG.
        #
        # SELECT had three page-specific drivers and no fallback. On any page that is
        # none of those three -- click-option's radios were exactly this -- v_native_select
        # found no #options, dispatched nothing, and SUBMITTED. The episode ended on a
        # submit that selected nothing, which is a -1 the route produced by itself.
        # A driver that cannot find its own page feature must say so, not act anyway;
        # the generic candidate click below then does the only thing that can be right
        # without knowing more about the page: click what the goal names.
        if act.ev("!!document.getElementById('options')"):
            return v_native_select(act, plan, goal)
        got = _resolve_and_click(act, goal)
        if not episode_over(act):
            submit(act, required=False)
        return got

    # AN APP IS NOT A WIDGET. Ten tasks share one email application, and none of the
    # per-control verbs can see it: the target is a row in a list, the handler is bound
    # only after the row is opened, and the operands are page state rather than sentence
    # text. Identify the APP from the page and hand the whole procedure over.
    if act.ev("(()=>{return !!(document.querySelector('#main .email-thread')"
              "||document.querySelector('#email')||document.querySelector('#search-results'))})()"):
        return v_email(act, plan, goal)

    # a feed with per-post action toggles, checked as a TOTAL condition
    if act.ev("(()=>{return document.querySelectorAll('.media').length>0"
              "&&document.querySelectorAll('.like,.reply,.retweet,.share').length>0})()"):
        return v_social(act, plan, goal)

    if verb == "SORT":
        return v_sort(act, plan, goal)
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
        # A REFUSAL IS THE DECOMPOSER DECLINING, NOT THE PAGE FAILING. If the APP on
        # screen is one whose procedure does not depend on the sentence, the refusal is
        # not a reason to stop -- email-inbox-nl-turk scored REFUSED on a goal the page
        # itself had already answered in core.currentFields. Check the app first.
        if act.ev("(()=>{return !!(document.querySelector('#main .email-thread')"
                  "||document.querySelector('#search-results'))})()"):
            try:
                _a = v_email(act, plan, goal)
                return {"task": task, "goal": goal, "status": "DECOMPOSED_BY_APP",
                        "action": _a, "success": episode_over(act),
                        "reward": raw_reward(act), "verb": "APP_EMAIL"}
            except ActuatorError as exc:
                return {"task": task, "goal": goal, "status": plan.get("status"),
                        "action": "APP_ERR:" + str(exc)[:30], "success": False,
                        "reward": None, "verb": "APP_EMAIL"}
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
