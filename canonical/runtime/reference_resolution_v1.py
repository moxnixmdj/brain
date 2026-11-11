"""Resolution: pick the ONE element a referring expression means, among look-alikes.

WHY THIS MODULE EXISTS, AND WHY IT IS NOT A GRAMMAR
---------------------------------------------------
r137-r142 raised GUI reach from 10% to 50% on a fixed 40-task sample, and then ran out. The
failure list was audited by hand and the twenty remaining zero-rate tasks split like this:

    no procedure at all            8
    resolution                     7      <-- this module
    read/compute                   2
    other                          1

On all seven resolution tasks the PROCEDURE IS ALREADY KNOWN. social-media, click-menu,
click-collapsible-2, click-color and hot-cold each fail with the actuator clicking the wrong
thing -- 'click-miss', 'menu-miss' -- or clicking a correct-*looking* thing that is the
wrong sibling. That is not a learning gap and a demonstration would not close it.

What was missing is the operation a person performs when told "for the user @leonie, click
Report": find a row of look-alike rows, pick the one whose OTHER cell names @leonie, then act
inside it. Four kinds of reference, and they collapse into one:

    TEXT     the expression is the element's own name            "click the link egestas"
    SCOPE    the expression names a container; act inside it     "@leonie ... Report"
    RELATION the expression names a value; find the element that carries it
                                                                 "click the red box"
    ORDER    the expression names a position among siblings      "the third row"

THE 2026 LITERATURE HAS ALREADY NAMED THIS GAP
-----------------------------------------------
Trace2Ground (ACL REALM 2026) splits web GUI grounding into three stress regimes --
PragmaMind (scenario stated, element not named), ContextTwin (several elements share
identical visible text, choose by context) and RelateLoc (target named by spatial or
structural relation to an anchor). Their result: specialist grounders that reach ~90% on
ScreenSpot underperform on all three. A production browser agent (browser-service #45, #49,
Oct 2026) is hitting the same thing in the same month: "the agent sends a positional row-1
candidate for a row named by its data ... a click on the wrong row succeeds, so the test
stays green on the wrong element."

THE DISCRIMINATOR IS THE WHOLE POINT
------------------------------------
A resolver that returns its best guess on an ambiguous reference reproduces that bug. So
resolve() returns one of three statuses and never a silent guess:

    RESOLVED     exactly one candidate survived
    AMBIGUOUS    two or more survived -- the reference does not determine the answer
    NOT_FOUND    nothing survived

The caller must handle AMBIGUOUS. On a page where "Report" appears nine times and none of
them is inside a block naming @leonie, six of those nine are wrong and the seventh is a
coin flip. Saying so is worth more than a click.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_RESOLUTION_V1"

# Colour words as they appear in these interfaces, with the forms that name them.
COLOUR_WORDS = (
    "black", "white", "red", "green", "blue", "yellow", "olive", "cyan",
    "magenta", "pink", "gray", "grey", "orange", "purple", "brown", "navy", "teal",
)

_SHAPE_WORDS = ("circle", "square", "box", "triangle", "rectangle", "star", "rect", "polygon")


def _declared_names(c: Mapping[str, Any], want: str) -> bool:
    """Does the page declare this control by the word the goal used?

    class/aria-label/title/alt/id, matched on word boundaries so "star" does not match
    "starving" and "trash" does not match "trashcan-2". The goal word may carry a suffix
    ("star icon"), so the declaration is required to CONTAIN the goal word, not equal it.
    """
    if not want:
        return False
    for key in ("declared", "cls", "aria", "title", "alt", "id"):
        val = _norm(str(c.get(key) or ""))
        if val and re.search(r"(?:^|[\s_\-])" + re.escape(want) + r"(?:$|[\s_\-])", val):
            return True
    return False


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def colour_in(text: str) -> str | None:
    """The colour a referring expression names, if any."""
    low = _norm(text)
    for word in COLOUR_WORDS:
        if re.search(r"\b" + word + r"\b", low):
            return "gray" if word == "grey" else word
    return None


def shape_in(text: str) -> str | None:
    low = _norm(text)
    for word in _SHAPE_WORDS:
        if re.search(r"\b" + word + r"\b", low):
            return {"rect": "rectangle", "box": "square"}.get(word, word)
    return None


def _rank(cands: Iterable[Mapping[str, Any]], base: float) -> list[dict[str, Any]]:
    """Deterministic ordering: higher base first, then smaller area, then reading order."""
    out = []
    for c in cands:
        d = dict(c)
        d["_score"] = base + (1.0 if d.get("exact") else 0.0)
        out.append(d)
    out.sort(key=lambda c: (-c["_score"], c.get("a", 0), c.get("cy", 0), c.get("cx", 0)))
    return out


# ---------------------------------------------------------------------------------------
# The browser side of the resolver. One evaluate, so a resolution costs one round trip.
# ---------------------------------------------------------------------------------------
_JS_CANDIDATES = r"""
(sel) => {
  // THE INSTRUCTION IS NOT THE TARGET. The sentence "click on the link posuere" is itself
  // a text node on the page, so a substring search matches the instruction banner before it
  // matches the link. MiniWob keeps the task in #area and the chrome in #query/#reward/
  // #display; restrict to the task area when it exists. This rule is general: a page that
  // tells you what to click is never the thing to click.
  const CHROME = ['#query', '#reward', '#display', '#side', '#sync-task-cover', '#wrap > #query'];
  const inChrome = (e) => CHROME.some(s => { const c = document.querySelector(s); return c && c.contains(e); });
  const area = document.querySelector('#area');
  let all = [...document.querySelectorAll(sel)];
  const scope = area && area.querySelectorAll(sel).length > 0
      ? [...area.querySelectorAll(sel)] : all;
  all = scope.filter(e => !inChrome(e));
  const out = [];
  for (const e of all) {
    const r = e.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) continue;
    const cs = getComputedStyle(e);
    if (cs.visibility === 'hidden' || cs.display === 'none' || cs.opacity === '0') continue;
    // OWN text, not the concatenation of the subtree. A <div> wrapping the whole page has
    // innerText equal to the whole page, so a substring test against it matches every word
    // on screen -- that is how 'egestas' resolved to the query banner instead of the link.
    let own = '';
    for (const n of e.childNodes) {
      if (n.nodeType === 3) own += n.nodeValue;
    }
    own = own.replace(/\s+/g, ' ').trim();
    const shown = (e.innerText || '').replace(/\s+/g, ' ').trim();
    const m = (cs.backgroundColor || '').match(/\d+/g);
    // A control with no visible text still has a NAME: its class, aria-label, title or id.
    // social-media renders .reply / .retweet / .like / .report as empty spans; the words in
    // the goal are the class names. Matching text alone finds nothing and clicks the wrong
    // sibling. Declared names are first-class, and they are read from the element, not
    // guessed from the sentence.
    const declared = [
      e.getAttribute('aria-label') || '',
      e.getAttribute('title') || '',
      e.id || '',
      (typeof e.className === 'string' ? e.className : '')
    ].join(' ').replace(/[-_]/g, ' ').replace(/\s+/g, ' ').trim();
    out.push({
      t: own || shown,
      own: own,
      shown: shown,
      declared: declared,
      cx: r.x + r.width / 2, cy: r.y + r.height / 2,
      x: r.x, y: r.y, w: r.width, h: r.height, a: r.width * r.height,
      tag: e.tagName,
      bg: m ? [Number(m[0]), Number(m[1]), Number(m[2])] : null,
      vis: true
    });
  }
  return out;
}
"""

_JS_TREE = r"""
(sel) => {
  const all = [...document.querySelectorAll(sel)];
  const out = [];
  for (const e of all) {
    const r = e.getBoundingClientRect();
    out.push({
      t: (e.innerText || e.textContent || '').trim(),
      x: r.x, y: r.y, w: r.width, h: r.height,
      a: Math.max(1, r.width * r.height),
      cx: r.x + r.width / 2, cy: r.y + r.height / 2,
      tag: e.tagName,
      vis: r.width > 0 && r.height > 0
    });
  }
  return out;
}
"""

# Named colour -> RGB, matching CSS keywords these pages actually use.
_RGB = {
    "black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0),
    "green": (0, 128, 0), "blue": (0, 0, 255), "yellow": (255, 255, 0),
    "olive": (128, 128, 0), "cyan": (0, 255, 255), "magenta": (255, 0, 255),
    "pink": (255, 192, 203), "gray": (128, 128, 128), "orange": (255, 165, 0),
    "purple": (128, 0, 128), "brown": (165, 42, 42), "navy": (0, 0, 128),
    "teal": (0, 128, 128), "lime": (0, 255, 0),
}


class Resolver:
    """Resolve referring expressions against a live page.

    `act` is the miniwob actuator (or anything with js/ev/box/click/drag). The resolver
    never clicks by itself: it returns candidates with coordinates and the caller decides.
    Resolution and action stay separate so that a wrong pick is never blamed on the actuator.
    """

    def __init__(self, act: Any) -> None:
        self.act = act

    # -- reading ------------------------------------------------------------------
    def text_candidates(self, selector: str = "button,a,li,div,span,input,label,td,th,h3") -> list[dict]:
        return self.act.ev("(" + _JS_CANDIDATES + ")(%s)" % json.dumps(selector)) or []

    def shape_candidates(self) -> list[dict]:
        """Figures, including SVG. A circle drawn in an <svg> is not a div and was invisible
        to every earlier candidate query -- which is how 'click the center of the circle'
        resolved to the Submit button."""
        raw = self.act.ev("(" + _JS_CANDIDATES + ")(%s)"
                          % json.dumps("svg,circle,rect,polygon,path,ellipse,canvas")) or []
        return raw

    def tree(self, selector: str = "*") -> list[dict]:
        return self.act.ev("(" + _JS_TREE + ")(%s)" % json.dumps(selector)) or []

    # -- TEXT ---------------------------------------------------------------------
    def resolve_text(self, expression: str, selector: str | None = None
                     ) -> dict[str, Any]:
        """The expression IS the element's name."""
        cands = self.text_candidates(selector or "button,a,li,div,span,input,label,td,th")
        want = _norm(expression)
        if not want:
            return {"status": "NOT_FOUND", "reason": "EMPTY_EXPRESSION", "candidates": []}
        exact = [c for c in cands if _norm(c.get("own") or "") == want]
        if len(exact) == 1:
            return {"status": "RESOLVED", "kind": "TEXT", "by": "exact",
                    "choice": exact[0], "n": 1}
        if len(exact) > 1:
            return {"status": "AMBIGUOUS", "kind": "TEXT", "by": "exact",
                    "candidates": exact[:12], "n": len(exact)}
        contains = [c for c in cands
                    if (c.get("own") or "") and want in _norm(c["own"])]
        if len(contains) == 1:
            return {"status": "RESOLVED", "kind": "TEXT", "by": "substring",
                    "choice": contains[0], "n": 1}
        if len(contains) > 1:
            # prefer the smallest element whose text is closest in length to the expression
            contains.sort(key=lambda c: (abs(len(_norm(c["own"])) - len(want)), c["a"]))
            return {"status": "AMBIGUOUS", "kind": "TEXT", "by": "substring",
                    "choice": contains[0], "candidates": contains[:12], "n": len(contains)}
        # THIRD TIER: the expression names the element but not in its text.
        declared = [c for c in cands
                    if want and re.search(r"\b" + re.escape(want) + r"\b",
                                          _norm(c.get("declared") or ""))]
        if len(declared) == 1:
            return {"status": "RESOLVED", "kind": "TEXT", "by": "declared-name",
                    "choice": declared[0], "n": 1}
        if len(declared) > 1:
            declared.sort(key=lambda c: c["a"])
            return {"status": "AMBIGUOUS", "kind": "TEXT", "by": "declared-name",
                    "choice": declared[0], "candidates": declared[:12], "n": len(declared)}
        return {"status": "NOT_FOUND", "kind": "TEXT", "reason": "NO_TEXT_MATCH",
                "candidates": []}

    # -- SCOPE --------------------------------------------------------------------
    def resolve_scope(self, anchor: str, target: str, container: str = "div,li,tr,article,section"
                      ) -> dict[str, Any]:
        """The anchor names a CONTAINER; the target is resolved INSIDE it.

        This is ContextTwin: nine blocks each containing the word 'Report'. Without the
        anchor there is no answer, only a guess.
        """
        blocks = [b for b in self.tree(container)
                  if b["vis"] and b["a"] > 0 and _norm(anchor) in _norm(b["t"])]
        if not blocks:
            return {"status": "NOT_FOUND", "kind": "SCOPE", "reason": "ANCHOR_NOT_ON_PAGE",
                    "anchor": anchor, "candidates": []}
        # The block must contain the anchor AND the target. Sorting by area alone picks the
        # username span itself, which cannot contain the Reply button -- the target lives in
        # a sibling panel of the same row. So walk outward: smallest block that holds both.
        blocks.sort(key=lambda b: b["a"])
        want = _norm(target)
        # An icon is named by the page, not by its text.
        #
        # Measured 2026-11-09 on `email-inbox`: the goal says "click the star icon", the row
        # holds <span class="star"> with NO text, and own-text matching therefore found
        # nothing -- TARGET_NOT_INSIDE_ANCHOR on a page where the target was present and
        # correctly nested. The page declares the control's name in class/aria-label/title/
        # alt/id; the goal uses the same word. This is the same mechanism as a CLI flag whose
        # documented words match the goal, which is the one that worked in r154: the match is
        # on declared names, not on a table of what I happen to know about email pages.
        # A declared match is only accepted inside the anchor and only when exactly one
        # element carries it, so it cannot turn a guess into a click.
        for block in blocks[:12]:
            box = (lambda c: block["x"] <= c["cx"] <= block["x"] + block["w"]
                   and block["y"] <= c["cy"] <= block["y"] + block["h"])
            inside = [c for c in self.text_candidates("button,a,li,div,span,input,label")
                      if c["vis"] and _norm(c.get("own") or "") == want and box(c)]
            if not inside:
                declared = [c for c in self.text_candidates("button,a,li,div,span,input,label")
                            if c["vis"] and box(c) and _declared_names(c, want)]
                named = [c for c in declared if c.get("cx") is not None]
                uniq = [c for c in named
                        if sum(1 for d in named if (d["cx"], d["cy"]) == (c["cx"], c["cy"])) == 1]
                inside = uniq[:1]
            if len(inside) == 1:
                return {"status": "RESOLVED", "kind": "SCOPE", "by": "anchor+target",
                        "choice": inside[0], "anchor_box": block, "n": 1}
            if len(inside) > 1:
                inside.sort(key=lambda c: c["a"])
                return {"status": "AMBIGUOUS", "kind": "SCOPE", "by": "anchor+target",
                        "choice": inside[0], "candidates": inside[:12], "n": len(inside)}
        return {"status": "NOT_FOUND", "kind": "SCOPE",
                "reason": "TARGET_NOT_INSIDE_ANCHOR", "anchor": anchor,
                "blocks": len(blocks), "candidates": []}

    # -- RELATION -----------------------------------------------------------------
    def resolve_relation(self, value: str, kind: str = "colour",
                         selector: str = "div,span,button,li"
                         ) -> dict[str, Any]:
        """The expression names a VALUE; find the element that renders it.

        click-color says "click on the red colored box": no element is called 'red', several
        share the same shape, and only the painted colour distinguishes them. This is
        RelateLoc, and it is why a text matcher reports NOT_FOUND on a page where the answer
        is plainly visible.
        """
        val = _norm(value)
        if kind == "colour":
            want = _RGB.get(val)
            if want is None:
                return {"status": "NOT_FOUND", "kind": "RELATION",
                        "reason": "UNKNOWN_COLOUR:" + val, "candidates": []}
            scored = []
            for c in self.text_candidates(selector):
                if not c.get("bg"):
                    continue
                d = (abs(c["bg"][0] - want[0]) + abs(c["bg"][1] - want[1])
                     + abs(c["bg"][2] - want[2]))
                if c["bg"] == [0, 0, 0] and val != "black":
                    continue          # transparent resolves to 0,0,0 in computed style
                scored.append((d, c))
            if not scored:
                return {"status": "NOT_FOUND", "kind": "RELATION",
                        "reason": "NO_PAINTED_ELEMENT", "candidates": []}
            scored.sort(key=lambda dc: (dc[0], dc[1]["a"]))  # exact colour, then tightest
            best = scored[0][0]
            tied = [c for d, c in scored if d <= best + 12]
            if len(tied) == 1:
                return {"status": "RESOLVED", "kind": "RELATION", "by": "colour",
                        "choice": tied[0], "distance": best, "n": 1}
            tied.sort(key=lambda c: c["a"])
            return {"status": "AMBIGUOUS", "kind": "RELATION", "by": "colour",
                    "choice": tied[0], "candidates": tied[:12], "n": len(tied),
                    "distance": best}
        if kind == "shape":
            # A SHAPE is drawn, not spelled. Anything with its own visible text is a control
            # or a label, not the figure -- 'circle-center' resolved to the Submit button
            # because Submit is a button and therefore square. Exclude text first, then
            # compare geometry.
            figures = [c for c in self.shape_candidates() if c["a"] > 16]
            cands = [c for c in (figures or self.text_candidates(selector))
                     if c["a"] > 16 and not _norm(c.get("own") or "")
                     and c["tag"] not in ("BUTTON", "A", "INPUT", "LABEL")]
            if val in ("circle",):
                cands = [c for c in cands if abs(c["w"] - c["h"]) <= 2]
            elif val in ("square", "box", "rectangle", "rect"):
                cands = [c for c in cands if abs(c["w"] - c["h"]) <= 4]
            if len(cands) == 1:
                return {"status": "RESOLVED", "kind": "RELATION", "by": "shape",
                        "choice": cands[0], "n": 1}
            if not cands:
                return {"status": "NOT_FOUND", "kind": "RELATION",
                        "reason": "NO_SHAPE_MATCH", "candidates": []}
            return {"status": "AMBIGUOUS", "kind": "RELATION", "by": "shape",
                    "candidates": cands[:12], "n": len(cands)}
        return {"status": "NOT_FOUND", "kind": "RELATION", "reason": "UNKNOWN_KIND",
                "candidates": []}

    # -- ORDER --------------------------------------------------------------------
    def resolve_order(self, index: int, container: str = "li,tr,div,button",
                      label: str | None = None) -> dict[str, Any]:
        """The expression names a POSITION among siblings. Same-container, reading order."""
        blocks = self.tree(container)
        if label:
            blocks = [b for b in blocks if _norm(label) in _norm(b["t"])]
        blocks = [b for b in blocks if b["vis"] and b["a"] > 0]
        if not blocks:
            return {"status": "NOT_FOUND", "kind": "ORDER", "reason": "NO_CONTAINER",
                    "candidates": []}
        # keep the outermost grouping: drop boxes that contain other boxes with the same area
        blocks.sort(key=lambda b: (b["y"], b["x"]))
        # dedupe near-identical boxes from nested markup
        seen, uniq = set(), []
        for b in blocks:
            key = (round(b["x"]), round(b["y"]), round(b["w"]), round(b["h"]))
            if key in seen:
                continue
            seen.add(key)
            uniq.append(b)
        if index < 0 or index >= len(uniq):
            return {"status": "NOT_FOUND", "kind": "ORDER",
                    "reason": "INDEX_OUT_OF_RANGE", "n": len(uniq), "candidates": []}
        return {"status": "RESOLVED", "kind": "ORDER", "by": "position",
                "choice": uniq[index], "n": len(uniq)}


# ---------------------------------------------------------------------------------------
# Orchestration: go from a goal sentence to one resolved target, or an honest refusal.
# ---------------------------------------------------------------------------------------
_ORDINALS = {"first": 0, "second": 1, "third": 2, "fourth": 3, "fifth": 4,
             "last": -1}


def plan_reference(goal: str) -> list[dict[str, Any]]:
    """Turn a goal into an ORDERED list of resolutions to attempt.

    Order matters and mirrors how a person reads the sentence: if a container is named,
    resolve it first and work inside it; only then reach for the flat text.
    """
    g = _norm(goal)
    steps: list[dict[str, Any]] = []

    quoted = re.findall(r'"([^"]+)"', goal) or re.findall(r"\u201c([^\u201d]+)\u201d", goal)
    quoted = [q.strip() for q in quoted if q.strip()]

    # ANCHOR + TARGET: "Find the email by Jeniece and click the star icon."
    #
    # The sentence names TWO things: a row (the anchor) and a control inside it (the
    # target). plan_reference used to extract only the target -- it returned
    # [{'kind':'RELATION','value':'star','by':'shape'}] for the goal above, discarding
    # Jeniece entirely and then resolving "star" by shape on the whole page, where it
    # found the instruction text. resolve_scope(anchor, target) already existed and was
    # called for nothing in this shape.
    #
    # This is a ROUTING rule, not a task rule: it fires on the sentence having a
    # "by <name>" / "from <name>" anchor and a later control verb, which is how the
    # instruction itself is written, and it defers entirely to resolve_scope, whose
    # anchor+target discipline refuses when the pair is not unique.
    _m = re.search(r"\b(?:by|from)\s+([A-Z][A-Za-z'\-]+)\b", goal)
    if _m:
        _anchor = _m.group(1).strip(" ,.")
        _tail = goal[_m.end():].lower()
        _tm = re.search(r"\b(?:the\s+)?([a-z]+(?:\s+[a-z]+)?)\s+(?:icon|button|link|field)\b", _tail)
        _tgt = (_tm.group(1).split()[-1] if _tm else None)
        if _tgt and _anchor.lower() not in ("the", "a", "an"):
            steps.append({"kind": "SCOPE", "anchor": _anchor, "target": _tgt})
            # the anchor+target pair is tried FIRST and, if it resolves, is the answer;
            # later steps stay as fallbacks so a refusal is not the end of the plan
    # SCOPE: "For the user @leonie, click on the 'Report' button."
    m = re.search(r"for the (?:user|person|account)\s+(\S+?)\s*,", goal, re.I)
    if m and quoted:
        steps.append({"kind": "SCOPE", "anchor": m.group(1).strip(" ,."),
                      "target": quoted[-1]})
        return steps

    # RELATION: a named colour or shape, with no element carrying that name
    colour = colour_in(goal)
    if colour and re.search(r"\b(click|select|choose|pick|find)\b", g):
        steps.append({"kind": "RELATION", "value": colour, "by": "colour"})

    shape = shape_in(goal)
    if shape and re.search(r"\b(click|select|choose|pick|find)",
                           g) and "colored box" not in g:
        steps.append({"kind": "RELATION", "value": shape, "by": "shape"})

    # ORDER: "the third row"
    for word, idx in _ORDINALS.items():
        if re.search(r"\bthe " + word + r"\b", g):
            label = None
            m2 = re.search(r"\b(?:row|item|entry|list|button)s?\b", g)
            if m2:
                label = None
            steps.append({"kind": "ORDER", "index": idx})
            break

    if quoted:
        for q in quoted:
            steps.append({"kind": "TEXT", "expression": q})

    return steps


_JS_TOGGLES = r"""
() => {
  // Things that reveal hidden content: accordion headers, disclosure triangles, "more".
  const out = [];
  for (const e of document.querySelectorAll('h1,h2,h3,h4,button,[role=button],.ui-accordion-header,.more')) {
    const r = e.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) continue;
    const cs = getComputedStyle(e);
    if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    out.push({t: (e.innerText || '').trim().slice(0, 40),
              cx: r.x + r.width / 2, cy: r.y + r.height / 2,
              a: r.width * r.height, tag: e.tagName});
  }
  out.sort((p, q) => p.cy - q.cy || p.cx - q.cx);
  return out;
}
"""


def expand_once(act: Any, seen: set | None = None) -> int:
    """Open one collapsed region. Returns the number actually clicked.

    click-collapsible-2 hides its links inside a jQuery accordion, so the correct resolver
    answer at time zero is NOT_FOUND -- the target genuinely is not on screen. A person does
    not conclude the task is impossible; they open the panels. The rule is general and
    applies to any disclosure UI, which is most of the web.
    """
    seen = seen if seen is not None else set()
    toggles = act.ev("(" + _JS_TOGGLES + ")()") or []
    for t in toggles:
        key = (round(t["cx"]), round(t["cy"]))
        if key in seen:
            continue
        seen.add(key)
        act.click(t["cx"], t["cy"])
        return 1
    return 0


def resolve_with_expansion(act: Any, goal: str, rounds: int = 6) -> dict[str, Any]:
    """Resolve; if the target is not on screen, open things and look again."""
    tried: set = set()
    history = []
    for i in range(rounds + 1):
        out = resolve(act, goal)
        history.append({"round": i, "status": out["status"],
                        "kind": out.get("kind"),
                        "reasons": [a.get("reason") for a in out.get("attempts", [])
                                    if a.get("reason")]})
        if out["status"] in ("RESOLVED", "AMBIGUOUS"):
            out["history"] = history
            return out
        if i == rounds:
            break
        if not expand_once(act, tried):
            break
    out = resolve(act, goal)
    out["history"] = history
    return out


_JS_QUERY_SWATCH = r"""
() => {
  // A reference value that is PAINTED rather than written. click-color puts the target
  // colour in a styled <div id="query-color"> inside the instruction, so the words say
  // "Click on the colored box" and the colour exists only as pixels.
  const q = document.querySelector('#query');
  if (!q) return null;
  for (const e of q.querySelectorAll('div,span,i,b,em')) {
    const r = e.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) continue;
    const m = (getComputedStyle(e).backgroundColor || '').match(/\d+/g);
    if (!m) continue;
    if (m[3] === '0') continue;                       // fully transparent
    if (m[0] === '255' && m[1] === '255' && m[2] === '255' && r.width > 40) continue;
    return {rgb: [Number(m[0]), Number(m[1]), Number(m[2])],
            ref: {cx: r.x + r.width / 2, cy: r.y + r.height / 2}};
  }
  return null;
}
"""


def resolve_painted_reference(act: Any) -> dict[str, Any]:
    """Match the element in the task area whose paint equals the instruction's swatch."""
    ref = act.ev("(" + _JS_QUERY_SWATCH + ")()")
    if not ref:
        return {"status": "NOT_FOUND", "kind": "RELATION",
                "reason": "NO_PAINTED_REFERENCE", "candidates": []}
    want = ref["rgb"]
    cands = act.ev("(" + _JS_CANDIDATES + ")(%s)"
                   % json.dumps("div,span,button,li")) or []
    scored = []
    for c in cands:
        if not c.get("bg"):
            continue
        d = sum(abs(c["bg"][i] - want[i]) for i in range(3))
        scored.append((d, c))
    if not scored:
        return {"status": "NOT_FOUND", "kind": "RELATION",
                "reason": "NO_PAINTED_CANDIDATE", "candidates": []}
    scored.sort(key=lambda dc: (dc[0], dc[1]["a"]))
    best = scored[0][0]
    tied = [c for d, c in scored if d <= best + 12]
    if len(tied) == 1:
        return {"status": "RESOLVED", "kind": "RELATION", "by": "painted-reference",
                "choice": tied[0], "distance": best, "n": 1, "reference": want}
    tied.sort(key=lambda c: c["a"])
    return {"status": "AMBIGUOUS", "kind": "RELATION", "by": "painted-reference",
            "choice": tied[0], "candidates": tied[:12], "n": len(tied), "reference": want}


def _clickable(choice: Any) -> bool:
    """A RESOLVED without coordinates is not a resolution -- it is a status string.

    Measured 2026-11-09 on the public task `email-inbox`: resolve_with_expansion returned
    status RESOLVED with a choice carrying no cx/cy at all, and on the next page a
    `declared: 'click canvas'` element at (245,105) -- the instruction, not a mail row.
    The caller clicks c["cx"], so a choice without coordinates either raises or clicks
    at a phantom. Every surface that reports RESOLVED must carry a point that can be
    pressed, or it must not report RESOLVED.
    """
    if not isinstance(choice, dict):
        return False
    cx, cy = choice.get("cx"), choice.get("cy")
    return isinstance(cx, (int, float)) and isinstance(cy, (int, float))


def resolve(act: Any, goal: str) -> dict[str, Any]:
    """Resolve a goal to ONE element, or say why it cannot.

    Returns the first RESOLVED step; records every attempt so a failure is diagnosable
    instead of being reported as 'click-miss'.
    """
    r = Resolver(act)
    attempts: list[dict[str, Any]] = []

    # Painted reference first when the words do not carry the value.
    if (re.search(r"\bcolou?red\b", goal, re.I) or re.search(r"\bswatch\b", goal, re.I)) \
            and colour_in(goal) is None:
        got = resolve_painted_reference(act)
        attempts.append({"step": {"kind": "RELATION", "value": "painted", "by": "reference"},
                         "status": got.get("status"), "reason": got.get("reason")})
        if got["status"] == "RESOLVED" and not _clickable(got.get("choice")):
            attempts.append({"status": "UNCLICKABLE", "reason": "RESOLVED_WITHOUT_COORDINATES"})
        elif got["status"] == "RESOLVED":
            return {"status": "RESOLVED", "kind": "RELATION", "choice": got["choice"],
                    "attempts": attempts, "by": "painted-reference"}
        if got["status"] == "AMBIGUOUS":
            return {"status": "AMBIGUOUS", "kind": "RELATION",
                    "candidates": got.get("candidates") or [], "attempts": attempts}

    for step in plan_reference(goal):
        kind = step["kind"]
        if kind == "TEXT":
            got = r.resolve_text(step["expression"])
        elif kind == "SCOPE":
            got = r.resolve_scope(step["anchor"], step["target"])
        elif kind == "RELATION":
            got = r.resolve_relation(step["value"], step["by"])
        elif kind == "ORDER":
            got = r.resolve_order(step["index"])
        else:
            continue
        attempts.append({"step": step, "status": got.get("status"),
                         "n": got.get("n"), "reason": got.get("reason")})
        if got["status"] == "RESOLVED" and not _clickable(got.get("choice")):
            # A status without a pressable point is not a resolution. Demote it and go on.
            attempts.append({"step": step, "status": "UNCLICKABLE",
                             "reason": "RESOLVED_WITHOUT_COORDINATES"})
            continue
        if got["status"] == "RESOLVED":
            return {"status": "RESOLVED", "kind": kind, "choice": got["choice"],
                    "attempts": attempts}
        if got["status"] == "AMBIGUOUS":
            return {"status": "AMBIGUOUS", "kind": kind,
                    "candidates": got.get("candidates") or [],
                    "attempts": attempts}
    return {"status": "NOT_FOUND", "kind": None, "attempts": attempts}


if __name__ == "__main__":  # pragma: no cover
    import argparse
    import importlib.util
    import os
    import sys

    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location(
        "miniwob_actuator_v1", os.path.join(here, "miniwob_actuator_v1.py"))
    M = importlib.util.module_from_spec(spec)
    sys.modules["miniwob_actuator_v1"] = M
    spec.loader.exec_module(M)

    ap = argparse.ArgumentParser()
    ap.add_argument("task")
    ap.add_argument("--reps", type=int, default=1)
    a = ap.parse_args()
    act = M.Actuator()
    for _ in range(a.reps):
        goal = M.start(act, a.task)
        out = resolve(act, goal)
        print(json.dumps({"goal": goal, **{k: v for k, v in out.items()
                                           if k != "candidates"}}, indent=1))
        if out["status"] == "AMBIGUOUS":
            for c in out["candidates"][:6]:
                print("   cand:", c["t"][:40], round(c["cx"]), round(c["cy"]))
    act.close()
