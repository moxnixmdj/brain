"""The operand for places: an action of the answer's SHAPE, derived from the page, not listed.

THE CLAIM UNDER TEST
--------------------
After derived_value_v1 closed the typing vocabulary, exactly 46 of the suite's pages remained
unsolved -- and every one of them has ZERO typeable fields (DECLARED_TRIGGER_AND_OPERAND_TAXONOMY:
39 typeable / 84 no-field overall; unsolved 46 = 46 no-field). The typing algebra's wall is
already at zero remaining pages. What those pages ask for instead is a PLACE: the center of a
circle, the track position of "Select 108 with the slider", the date cell of 11/10/2016, the
row that is the shortest flight, the third checkbox, the nth word, the odd/even column.

Two things were missing, and this module supplies the derivations for both:

  a new primitive       the shipped hand can act only AT AN ELEMENT (`press`, `type`, `hover`,
                        `grab`, `drop`, `nudge`, `triple`, each with an element index). A point
                        that is not an element's middle -- the inside of a circle, a proportion
                        along a slider, a place to let go of a dragged thing -- cannot be named,
                        so no search over the existing actions can ever reach it. The chromium
                        bridge now also takes `pressat@x,y`, `moveat@x,y`, `dropat@x,y` (a
                        place, element or not); this module computes the places.

  a prior over choices   many of the remaining pages are pressable already -- the right row,
                        the right cell, the right column -- but nothing ranks the right index
                        above the thousands that are wrong. These rules emit those indices as
                        early, cheap candidates with their witnesses attached, the same
                        discipline GuidedPrices gives named elements.

THE RULE (one rule, its gates are facts about pages and language, never about one page)
--------------------------------------------------------------------------------------
Each operator has a structural gate (the shape on the page: a slider with aria bounds, a table
of times, two columns of radio buttons) and a language gate (an English phrase or a literal in
the instruction: "center", "shortest", a date, a colour, an ordinal). Both gates are facts in
general -- no operator is keyed to a page name, and no gate quotes a page-specific phrase. A
candidate arrives with a witness (which boxes and which words produced it) so that a success is
replayable and `rule_of` can name the rule that mattered -- the learnable unit, the same
contract derived_value's `rule_of` gives its typed values.

WHAT IS DELIBERATELY NOT HERE (the honest scope)
------------------------------------------------
  * semantic similarity ("words similar to homes, unhappy ...") needs a model of meaning, not
    an algebra over structure -- refused, not faked;
  * multi-turn reactive play (guess-number's feedback, simon-says, tic-tac-toe) is a policy
    over feedback, not a derived operand;
  * a drawn PATH (draw-circle, bisect-angle, resize-by-drag) needs choreography across several
    held states; only the single drag THROUGH a known point (draw-line) is offered, as
    grab@point + dropat@point;
  * the colorwheel is reached by an ordered ring of points around the wheel's own box -- the
    hue's angle convention is a fact about that widget's implementation, so the ring is tried
    in hue order instead of betting on the convention.

Usage
-----
    from canonical.runtime import aimed_action_v1 as aimed
    aimed.aimed_actions(observation)     # -> ["pressat@61,120", "click@9", ...]
    aimed.rule_of(observation, action)   # -> {"rule": "CENTER_OF", "witness": {...}} | None
    aimed.decoy_actions(observation, seed=...)   # same count/shape, drawn from the wrong witness
"""
from __future__ import annotations

import math
import random
import re
import zlib
from typing import Any, Mapping, Sequence

from canonical.runtime import derived_value_v1 as dv  # words_of / visible_texts: the shared reading

# --------------------------------------------------------------------------- reading the page

SVG_SHAPES = {"circle", "ellipse", "rect", "polygon", "polyline", "line", "path"}
STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "all", "then", "when", "into", "onto",
    "press", "hit", "click", "select", "find", "search", "enter", "type", "give", "create",
    "book", "order", "keep", "stay", "using", "after", "once", "done", "below", "above", "their",
    "there", "here", "what", "which", "whose", "must", "should", "would", "will", "each", "every",
    "post", "posts", "button", "buttons", "field", "fields", "item", "items", "number", "numbers",
    "value", "values", "label", "labels", "form", "text", "word", "words", "page", "menu",
    "use", "used", "using", "wanted", "was", "are", "has", "have", "had", "its", "not", "you",
    "your", "one", "two", "three", "then", "than", "over", "under", "inside", "outside",
}
CONTROL_VOCAB = ("reply", "mute", "forward", "delete", "send", "agree", "submit", "approve",
                 "confirm", "post", "share", "like", "remove", "erase", "add")
MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december")
NAMED_COLOURS = {
    "red": 0, "orange": 30, "yellow": 60, "green": 120, "lime": 90, "teal": 160, "cyan": 180,
    "aqua": 180, "blue": 220, "navy": 230, "purple": 280, "violet": 280, "magenta": 300,
    "pink": 330, "fuchsia": 300, "brown": 20, "grey": 0, "gray": 0, "black": 0, "white": 0,
}
_SUPERLATIVES = {
    "shortest": ("dur", "min"), "longest": ("dur", "max"),
    "earliest": ("dep", "min"), "latest": ("dep", "max"),
    "cheapest": ("price", "min"), "most expensive": ("price", "max"),
    "slowest": ("dur", "max"), "fastest": ("dur", "min"),
}

_TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})\b")
_DATE_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_HEX_RE = re.compile(r"#([0-9a-fA-F]{6})\b")
_PRICE_RE = re.compile(r"(?:\$|€|£)\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:dollars|USD)\b")
_ORDINAL_RE = re.compile(r"\b(\d+)(?:st|nd|rd|th)\s+([a-z ]+?)\b")
_WORD_ORDINAL = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
                 "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12}


def _squash(text: Any) -> str:
    return " ".join(str(text or "").split())


def _lower(text: Any) -> str:
    return _squash(text).lower()


def _box(element: Mapping[str, Any]) -> list[float] | None:
    box = element.get("box")
    if not (isinstance(box, (list, tuple)) and len(box) == 4):
        return None
    x, y, w, h = (float(v) for v in box)
    if w <= 0 or h <= 0:
        return None
    return [x, y, w, h]


def _centre(box: Sequence[float]) -> tuple[float, float]:
    return box[0] + box[2] / 2, box[1] + box[3] / 2


def _clamp(x: float, y: float) -> tuple[float, float]:
    return max(1.0, min(479.0, x)), max(1.0, min(359.0, y))


def _point_action(x: float, y: float) -> str:
    cx, cy = _clamp(x, y)
    return f"pressat@{cx:.1f},{cy:.1f}"


def _move_action(x: float, y: float) -> str:
    cx, cy = _clamp(x, y)
    return f"moveat@{cx:.1f},{cy:.1f}"


def _drop_action(x: float, y: float) -> str:
    cx, cy = _clamp(x, y)
    return f"dropat@{cx:.1f},{cy:.1f}"


def _elements(observation: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return list(observation.get("elements") or [])


def _in_instruction_region(element: Mapping[str, Any], index: dict[int, Mapping[str, Any]]) -> bool:
    """The instruction region repeats the utterance on the page; it is shown, but nothing the
    hand does THERE is a page action -- targets and controls inside it are echoes, not cells."""
    if _lower(element.get("id")) == "query":
        return True
    return any(_lower(p.get("id")) == "query" for p in _parent_chain(element, index))


def _by_index(observation: Mapping[str, Any]) -> dict[int, Mapping[str, Any]]:
    return {int(e["index"]): e for e in _elements(observation) if "index" in e}


def _parent_chain(element: Mapping[str, Any], index: dict[int, Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    chain: list[Mapping[str, Any]] = []
    cursor = element
    for _ in range(12):
        parent = index.get(int(cursor.get("parent", -1)))
        if parent is None:
            break
        chain.append(parent)
        cursor = parent
    return chain


def _colour_hue(text: Any) -> float | None:
    """Hue in degrees of an inline colour (hex or a named colour), None when it has no hue."""
    value = _lower(text)
    if not value or value in {"none", "transparent"}:
        return None
    found = _HEX_RE.search(value)
    if found:
        raw = found.group(1)
        r, g, b = (int(raw[i:i + 2], 16) / 255 for i in (0, 2, 4))
        high, low = max(r, g, b), min(r, g, b)
        if high == low:
            return 0.0
        if high == r:
            hue = ((g - b) / (high - low)) % 6
        elif high == g:
            hue = (b - r) / (high - low) + 2
        else:
            hue = (r - g) / (high - low) + 4
        return (hue * 60) % 360
    for name, hue in NAMED_COLOURS.items():
        if name in value.split() or value == name:
            return float(hue)
    return None


def _hue_near(hue: float, target: float, band: float = 32.0) -> bool:
    return abs((hue - target + 180) % 360 - 180) <= band


def _hours(text: str) -> float | None:
    found = _TIME_RE.search(text)
    if not found:
        return None
    return int(found.group(1)) + int(found.group(2)) / 60


def _rows_of(observation: Mapping[str, Any]) -> list[tuple[Mapping[str, Any], list[Mapping[str, Any]]]]:
    """Rows of a record structure: <tr> cells when there is a table, else sibling groups that
    repeat the same tag -- records first (every row itself a container of several elements,
    so a page whose posts each hold three divs is grouped into the POSTS, not the posts'
    parts), and only if no such group exists, any repeating siblings. Empty: no records."""
    elements = _elements(observation)
    children: dict[int, list[Mapping[str, Any]]] = {}
    for element in elements:
        children.setdefault(int(element.get("parent", -1)), []).append(element)
    rows: list[tuple[Mapping[str, Any], list[Mapping[str, Any]]]] = []
    trs = [e for e in elements if e.get("tag") == "tr"]
    if trs:
        for tr in trs:
            cells = [c for c in elements if int(c.get("parent", -1)) == int(tr["index"])]
            if cells:
                rows.append((tr, cells))
        return rows

    record_groups: list[list[Mapping[str, Any]]] = []
    loose_groups: list[list[Mapping[str, Any]]] = []
    for _parent, kids in children.items():
        if len(kids) < 3:
            continue
        # A record SAYS something: siblings that carry real text ARE the rows (a post does,
        # its three part-divs do not; the trailing <p> of a submit does not ungroup them).
        strong = [k for k in kids
                  if len(str(k.get("full_text") or k.get("text") or "")) >= 15 and _box(k)]
        if len(strong) >= 3:
            record_groups.append(strong)
        tags = {k.get("tag") for k in kids}
        if len(tags) == 1 and tags <= {"div", "li", "option", "td"} and all(_box(k) for k in kids):
            loose_groups.append(kids)
    chosen = record_groups or loose_groups
    for kids in chosen:
        for kid in kids:
            rows.append((kid, [kid]))
    return rows


# --------------------------------------------------------------------------- the operators


def _centre_of(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"click on the center of the circle" / "the mid-point between the two points": every
    small point-like shape the instruction can mean contributes a candidate at its own centre,
    and a midpoint request adds the pairwise midpoints of the two smallest points."""
    utterance = _lower(observation.get("utterance"))
    if not re.search(r"\b(center|centre|middle|mid-?point)\b", utterance):
        return []
    elements = _elements(observation)
    points = [e for e in elements if _box(e) and (
        e.get("tag") in SVG_SHAPES
        or re.search(r"circle|point|dot|ball|shape|target", str(e.get("classes") or "")))]
    points = [e for e in points if (lambda b: b[2] * b[3])(_box(e) or [0, 0, 0, 0]) <= 40 * 40 * 8][:10]
    out: list[tuple[str, str, dict[str, Any]]] = []
    if re.search(r"mid-?point|midpoint|between the two", utterance):
        small = sorted(points, key=lambda e: (_box(e) or [0] * 4)[2] * (_box(e) or [0] * 4)[3])[:3]
        for i in range(len(small)):
            for j in range(i + 1, len(small)):
                a, b = _centre(_box(small[i]) or [0] * 4), _centre(_box(small[j]) or [0] * 4)
                out.append((_point_action((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), "MIDPOINT_OF_TWO_POINTS",
                            {"points": [small[i]["index"], small[j]["index"]]}))
        if out:
            return out[:6]
    for element in points[:6]:
        x, y = _centre(_box(element) or [0] * 4)
        out.append((_point_action(x, y), "CENTER_OF", {"element": element["index"]}))
    for element in elements:
        if element.get("tag") == "svg" and _box(element):
            x, y = _centre(_box(element) or [0] * 4)
            out.append((_point_action(x, y), "CENTER_OF_SVG", {"element": element["index"]}))
    if not out and re.search(r"\b(center|centre|middle)\b", utterance):
        body = next((e for e in elements if _box(e)), None)
        if body:
            x, y = _centre(_box(body) or [0] * 4)
            out.append((_point_action(x, y), "CENTER_OF_THE_PAGE", {"element": body["index"]}))
    return out[:8]


def _right_angle(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Add a third point to create a right angle": two known points P, Q give a family of
    right-angle vertices; the two rotations by 90 degrees of the segment at each endpoint are
    members of that family and cost four presses."""
    if "right angle" not in _lower(observation.get("utterance")):
        return []
    elements = [e for e in _elements(observation)
                if _box(e) and (e.get("tag") in SVG_SHAPES
                                or re.search(r"point|dot|circle|marker", str(e.get("classes") or "")))]
    elements = sorted(elements, key=lambda e: (_box(e) or [0] * 4)[2] * (_box(e) or [0] * 4)[3])[:3]
    if len(elements) < 2:
        return []
    p, q = _centre(_box(elements[0]) or [0] * 4), _centre(_box(elements[1]) or [0] * 4)
    out: list[tuple[str, str, dict[str, Any]]] = []
    for base, other in ((p, q), (q, p)):
        dx, dy = other[0] - base[0], other[1] - base[1]
        for sx, sy in ((-dy, dx), (dy, -dx)):
            out.append((_point_action(base[0] + sx, base[1] + sy), "RIGHT_ANGLE_VERTEX",
                        {"points": [elements[0]["index"], elements[1]["index"]]}))
    return out[:6]


# -- exact stated geometry -----------------------------------------------------------------------------
# The three pages whose score frame refused every correct press (OUT_SCORE_FRAME_NOT_STATED:
# circle-center, find-midpoint, right-angle) score against the page's OWN canvas numbers: the
# click is mapped into canvas space by a y-offset the page prints (`y-QUERY_PADDING`) and
# compared against the marks' exact geometry, where the ROUNDED box has already thrown the
# fractions away. These operators read `box_f`/`geom` (additive fields; an old observation
# produces nothing, so every previously measured hand is unchanged), do the exact math in
# canvas coordinates, and offer it at each plausible page y-offset -- the one number the DOM
# does not state. After any press the page SHOWS its own blue mark, and with the bridge's
# pointer proprioception the offset is measured, not guessed.
#
# Presses are INTEGERS on purpose: the DOM exposes pageX/pageY as `long`, so a fractional
# coordinate is truncated on arrival. A half-pixel optimum (circle-center's, whenever the
# mark radius and the printed padding differ by a half) is therefore UNREACHABLE by any
# click -- that is the page's score frame demanding a point the actuator cannot express,
# and no candidate here pretends otherwise.
SVG_Y_OFFSETS_ABOUT_TOP = (0, 1, 2)            # plausible printed offsets at or under the svg top


def _float_box(element: Mapping[str, Any]) -> list[float] | None:
    """The unrounded rectangle, when the observation carries one."""
    box = element.get("box_f")
    if not (isinstance(box, (list, tuple)) and len(box) == 4):
        return None
    try:
        x, y, w, h = (float(v) for v in box)
    except (TypeError, ValueError):
        return None
    if not (w > 0 and h > 0):
        return None
    return [x, y, w, h]


def _svg_frame(observation: Mapping[str, Any]) -> tuple[float, float] | None:
    """The svg element's own unrounded origin, the translation between its canvas and the page."""
    for element in _elements(observation):
        if element.get("tag") == "svg":
            box = _float_box(element)
            if box is not None:
                return box[0], box[1]
    return None


def _geom_number(element: Mapping[str, Any], key: str) -> float | None:
    geom = element.get("geom")
    if not isinstance(geom, Mapping):
        return None
    try:
        return float(str(geom[key]))
    except (KeyError, TypeError, ValueError):
        return None


def _svg_local_point(element: Mapping[str, Any], frame: tuple[float, float]) -> tuple[float, float] | None:
    """The element's centre in the page's OWN canvas: the stated cx/cy when the element states
    them, else the unrounded rectangle translated out of page coordinates."""
    cx, cy = _geom_number(element, "cx"), _geom_number(element, "cy")
    if cx is not None and cy is not None:
        return cx, cy
    box = _float_box(element)
    if box is None:
        return None
    return (box[0] + box[2] / 2.0 - frame[0], box[1] + box[3] / 2.0 - frame[1])


def _page_y_offsets(observation: Mapping[str, Any]) -> list[float]:
    """Every plausible page-y-offset: the svg top, and each value a printed constant under it.
    None of these is stated by the DOM; the list is the honest small set the layout can be in,
    and the first press makes the page reveal which one it is (see _measured_y_offset)."""
    frame = _svg_frame(observation)
    if frame is None:
        return []
    top = frame[1]
    return [top - k for k in SVG_Y_OFFSETS_ABOUT_TOP]


def _measured_y_offset(observation: Mapping[str, Any]) -> float | None:
    """The page's own click-to-canvas offset, MEASURED from evidence the page itself shows:
    once the hand has pressed anywhere, the blue mark it drew sits at (press - offset) in its
    canvas, the bridge reports where the pointer last was, and the mark states its radius."""
    frame = _svg_frame(observation)
    pointer = observation.get("pointer")
    if frame is None or not (isinstance(pointer, (list, tuple)) and len(pointer) == 2):
        return None
    for element in _elements(observation):
        ident = f"{element.get('id') or ''} {element.get('classes') or ''}"
        if not re.search(r"blue", ident):
            continue
        box = _float_box(element)
        if box is None:
            continue
        radius = _geom_number(element, "r")
        if radius is None:
            radius = box[2] / 2.0
        try:
            return frame[1] + float(pointer[1]) - box[1] - radius
        except (TypeError, ValueError):
            return None
    return None


def _press(x: float, y: float) -> str:
    """An integer press: the DOM truncates fractional page coordinates on arrival, so the
    candidate is the point the hand can actually reach."""
    cx, cy = _clamp(float(x), float(y))
    return f"pressat@{int(cx)},{int(cy)}"


def _point_marks(observation: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """The small point-like marks whose exact canvas position can be taken."""
    elements = _elements(observation)
    marks = [e for e in elements if (_float_box(e) is not None or _geom_number(e, "cx") is not None) and (
        e.get("tag") in SVG_SHAPES
        or re.search(r"circle|point|dot|ball|shape|target", str(e.get("classes") or "")))]
    marks = [e for e in marks
             if (lambda b: b is None or b[2] * b[3] <= 40 * 40 * 8)(_float_box(e))][:10]
    return marks


def _exact_centre(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"click on the center of the circle": the exact canvas centre at each plausible page
    offset, and -- when the page has already shown its own blue mark -- at the measured one."""
    utterance = _lower(observation.get("utterance"))
    if not re.search(r"\b(center|centre|middle)\b", utterance) or re.search(r"mid-?point|between the two", utterance):
        return []
    frame = _svg_frame(observation)
    offsets = _page_y_offsets(observation)
    if frame is None or not offsets:
        return []
    marks = [e for e in _point_marks(observation) if _svg_local_point(e, frame) is not None]
    if not marks:
        return []
    top = _svg_local_point(marks[0], frame)
    assert top is not None
    out: list[tuple[str, str, dict[str, Any]]] = []
    for k in offsets:
        out.append((_press(top[0], top[1] + k), "EXACT_CENTER_OF",
                    {"element": marks[0]["index"], "offset": k, "nudge": [0.0, 0.0]}))
    measured = _measured_y_offset(observation)
    if measured is not None:
        for k in (measured, measured - 1, measured + 1):
            out.append((_press(top[0], top[1] + k), "EXACT_CENTER_NUDGE",
                        {"element": marks[0]["index"], "offset": k, "nudge": [0.0, 0.0]}))
    return out[:16]


def _exact_midpoint(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"the mid-point between the two points": the exact canvas midpoint of the two smallest
    marks at each plausible page offset, and at the measured one. When the two marks' sum is
    odd the true midpoint is a half-pixel the actuator cannot press -- the candidate floors
    to the reachable neighbour and the page's own reward stays honest about the rest."""
    utterance = _lower(observation.get("utterance"))
    if not re.search(r"mid-?point|between the two", utterance):
        return []
    frame = _svg_frame(observation)
    offsets = _page_y_offsets(observation)
    if frame is None or not offsets:
        return []
    marks = sorted((e for e in _point_marks(observation) if _svg_local_point(e, frame) is not None),
                   key=lambda e: ((_float_box(e) or [0] * 4)[2] * (_float_box(e) or [0] * 4)[3]))[:2]
    if len(marks) < 2:
        return []
    a = _svg_local_point(marks[0], frame)
    b = _svg_local_point(marks[1], frame)
    if a is None or b is None:
        return []
    mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
    witness0 = {"points": [marks[0]["index"], marks[1]["index"]]}
    out: list[tuple[str, str, dict[str, Any]]] = []
    for k in offsets:
        out.append((_press(mid[0], mid[1] + k), "EXACT_MIDPOINT_OF_TWO_POINTS",
                    dict(witness0, offset=k, nudge=[0.0, 0.0])))
    measured = _measured_y_offset(observation)
    if measured is not None:
        for k in (measured, measured - 1, measured + 1):
            out.append((_press(mid[0], mid[1] + k), "EXACT_MIDPOINT_NUDGE",
                        dict(witness0, offset=k, nudge=[0.0, 0.0])))
    return out[:16]


def _exact_right_angle(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"create a right angle": the two exact canvas points rotated +-90 degrees -- the law of
    cosines then lands on 90 degrees to within float noise, well inside the page's 1e-9 full
    reward -- carried into page coordinates at each plausible offset and the measured one."""
    if "right angle" not in _lower(observation.get("utterance")):
        return []
    frame = _svg_frame(observation)
    offsets = _page_y_offsets(observation)
    if frame is None or not offsets:
        return []
    marks = sorted((e for e in _point_marks(observation) if _svg_local_point(e, frame) is not None),
                   key=lambda e: ((_float_box(e) or [0] * 4)[2] * (_float_box(e) or [0] * 4)[3]))[:2]
    if len(marks) < 2:
        return []
    p = _svg_local_point(marks[0], frame)
    q = _svg_local_point(marks[1], frame)
    if p is None or q is None:
        return []
    witness = {"points": [marks[0]["index"], marks[1]["index"]]}
    out: list[tuple[str, str, dict[str, Any]]] = []
    vertices: list[tuple[float, float, dict[str, Any]]] = []
    for base, other in ((p, q), (q, p)):
        dx, dy = other[0] - base[0], other[1] - base[1]
        for sx, sy in ((-dy, dx), (dy, -dx)):
            vertices.append((base[0] + sx, base[1] + sy, witness))
    for k in offsets:
        for vx, vy, w in vertices:
            out.append((_press(vx, vy + k), "EXACT_RIGHT_ANGLE_VERTEX",
                        dict(w, offset=k, nudge=[0.0, 0.0])))
    measured = _measured_y_offset(observation)
    if measured is not None:
        for vx, vy, w in vertices:
            out.append((_press(vx, vy + measured), "EXACT_RIGHT_ANGLE_NUDGE",
                        dict(w, offset=measured, nudge=[0.0, 0.0])))
    return out[:16]


def _slider_targets(utterance: str) -> list[float]:
    bracket = re.search(r"\[([\d,\s]+)\]", utterance)
    if bracket:
        return [float(v) for v in re.findall(r"\d+", bracket.group(1))]
    if "slider" not in utterance:
        return []
    plain = [float(v) for v in re.findall(
        r"(?<![\d./])\d{1,4}(?![\d./])(?!\s*(?:st|nd|rd|th)\b)", utterance)]
    return plain[-1:]


def _slider_to_value(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Select 108 with the slider" / "set the sliders to [15,15,16]": a widget that carries
    aria (or native) bounds and a handle position is a solved linear map from value to point."""
    utterance = _lower(observation.get("utterance"))
    values = _slider_targets(str(observation.get("utterance") or ""))
    if not values or "slider" not in utterance:
        return []
    elements = _elements(observation)
    tracks: list[tuple[Mapping[str, Any], float, float, Mapping[str, Any] | None]] = []
    for element in elements:
        box = _box(element)
        if not box:
            continue
        lo, hi = element.get("aria-valuemin"), element.get("aria-valuemax")
        handle: Mapping[str, Any] | None = None
        if lo is not None and hi is not None:
            handle = element
        elif _lower(element.get("type")) == "range" and element.get("min") is not None and element.get("max") is not None:
            lo, hi, handle = element.get("min"), element.get("max"), element
        if handle is None:
            continue
        try:
            minimum, maximum = float(lo), float(hi)
        except (TypeError, ValueError):
            continue
        if maximum == minimum:
            continue
        track = next((e for e in elements
                      if int(e.get("parent", -1)) == int(element["index"]) and _box(e)), None)
        track_box = _box(track) if track is not None and _box(track) else box
        if track is None:
            parent = next((e for e in elements if int(e["index"]) == int(element.get("parent", -1))), None)
            if parent is not None and _box(parent):
                track, track_box = parent, _box(parent)
        if track_box is None:
            continue
        tracks.append((track if track is not None else element, minimum, maximum, handle))
    if not tracks:
        return []
    tracks.sort(key=lambda t: (round(((_box(t[0]) or [0])[1]) / 60), (_box(t[0]) or [0])[0]))
    out: list[tuple[str, str, dict[str, Any]]] = []
    for i, (track, minimum, maximum, handle) in enumerate(tracks):
        if i >= len(values) and len(values) == 1:
            value = values[0]
        elif i < len(values):
            value = values[i]
        else:
            break
        box = _box(track) or [0, 0, 0, 0]
        proportion = (value - minimum) / (maximum - minimum)
        proportion = max(0.0, min(1.0, proportion))
        if box[3] > box[2] * 1.5:  # a vertical slider: min at the bottom, as the widgets draw it
            x, y = box[0] + box[2] / 2, box[1] + (1 - proportion) * box[3]
        else:
            x, y = box[0] + proportion * box[2], box[1] + box[3] / 2
        witness = {"track": track["index"], "value": value, "min": minimum, "max": maximum}
        if handle is not None:
            witness["handle"] = handle["index"]
        out.append((_point_action(x, y), "SLIDER_TO_VALUE", witness))
    return out


def _move_on_target(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Keep your mouse inside the circle ..." / "hovered over the colored square": a pointer
    that must STAY on something is the same derived point, re-derived every look, taken with
    moveat -- the boxes are the page's own and they update as the page moves."""
    utterance = _lower(observation.get("utterance"))
    if not re.search(r"\b(keep|stay|remain)\b.*\b(mouse|cursor|pointer)\b|\bhovered over\b|\bhover over\b",
                     utterance):
        return []
    wanted = re.search(r"\b(circle|square|ball|shape|target|item|rectangle|triangle|colored|colour(?:ed)?)\b",
                       utterance)
    out: list[tuple[str, str, dict[str, Any]]] = []
    for element in _elements(observation):
        box = _box(element)
        if not box:
            continue
        shape = element.get("tag") in SVG_SHAPES or re.search(
            r"circle|square|ball|shape|target|marker|moving|colored|colour", str(element.get("classes") or ""))
        if not shape:
            continue
        if wanted and not re.search(wanted.group(1), _lower(element.get("classes"))
                                    + " " + _lower(element.get("id")) + " " + element.get("tag", ""), ):
            if not (element.get("colour") or element.get("tag") in SVG_SHAPES):
                continue
        x, y = _centre(box)
        out.append((_move_action(x, y), "MOVE_ON_TARGET", {"element": element["index"]}))
        if len(out) >= 4:
            break
    return out


def _click_moving_shapes(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Click as many moving circles as possible": every current instance of the named shape is
    a candidate NOW; the boxes change each look, so the candidates change with them."""
    utterance = _lower(observation.get("utterance"))
    if not re.search(r"as many|\bas possible\b", utterance) or "click" not in utterance:
        return []
    noun = re.search(r"\b(circles?|squares?|shapes?|items?|balls?)\b", utterance)
    if not noun:
        return []
    noun = noun.group(1)
    stem = noun[:-1] if len(noun) > 3 and noun.endswith("s") else noun
    out: list[tuple[str, str, dict[str, Any]]] = []
    for element in _elements(observation):
        if not element.get("can_click") or not _box(element):
            continue
        where = _lower(element.get("classes")) + " " + _lower(element.get("id")) + " " + _lower(element.get("tag"))
        if stem in where or noun in where:
            out.append((f"click@{element['index']}", "CLICK_NAMED_SHAPE", {"element": element["index"]}))
            if len(out) >= 6:
                break
    return out


def _date_cell(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Select 11/10/2016 as the date": the day is a literal in the instruction; the calendar
    is a grid of cells; when the grid shows more than one month the cells of the right month
    are the ones whose ancestors say that month."""
    found = _DATE_RE.search(str(observation.get("utterance") or ""))
    if not found:
        return []
    month, day = int(found.group(1)), int(found.group(2))
    month_name = MONTHS[month - 1]
    index = _by_index(observation)
    scored: list[tuple[int, int, Mapping[str, Any]]] = []
    for element in _elements(observation):
        text = _squash(element.get("text"))
        if text.strip(".,") != str(int(day)) or not _box(element):
            continue
        if not element.get("can_click"):
            continue
        in_month = any(month_name in _lower(p.get("text")) or month_name in _lower(p.get("full_text"))
                       for p in _parent_chain(element, index))
        grid = element.get("tag") in {"td", "th", "li"} or bool(element.get("id") or element.get("classes"))
        scored.append((1 if in_month else 0, 1 if grid else 0, element))
    scored.sort(key=lambda row: (-row[0], -row[1]))
    return [(f"click@{e['index']}", "DATE_CELL",
             {"element": e["index"], "date": found.group(0), "month_named": bool(s)})
            for s, _g, e in scored[:8]]


def _path_segments(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Select Milissent>Harmonia>Anita": each segment names the next element to press; the
    later segments are invisible until the earlier ones are pressed, and that is the search's
    business -- this rule only makes each visible segment cheap to find."""
    utterance = str(observation.get("utterance") or "")
    if ">" not in utterance:
        return []
    segments = [_squash(s) for s in re.split("[>,]", utterance) if _squash(s)]
    segments = [re.sub(r"^(select|choose|pick|click(?: on)?|press|find|open)\s+", "", s, flags=re.I)
                for s in segments]
    segments = [s for s in segments if 0 < len(s) <= 40][:6]
    if len(segments) < 2:
        return []
    out: list[tuple[str, str, dict[str, Any]]] = []
    for segment in segments:
        needle = _lower(segment)
        index = _by_index(observation)
        for element in _elements(observation):
            if not element.get("can_click") or not _box(element):
                continue
            if _in_instruction_region(element, index):
                continue                      # the instruction region says the segment; it is not it
            own = _lower(element.get("text")) or _lower(element.get("full_text"))
            if own and needle in own:
                out.append((f"click@{element['index']}", "PATH_SEGMENT",
                            {"element": element["index"], "segment": segment}))
                break
    return out


def _superlative_records(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Book the shortest one-way flight ...": among rows of records, the one the superlative
    names -- a duration from pairs of times, a price from a money cell, a departure from the
    first time -- is the row to press, and every cell of that row is offered."""
    utterance = _lower(observation.get("utterance"))
    keyword = next((k for k in _SUPERLATIVES if k in utterance), None)
    if keyword is None:
        return []
    what, direction = _SUPERLATIVES[keyword]
    rows = _rows_of(observation)
    parsed: list[tuple[Mapping[str, Any], list[Mapping[str, Any]], dict[str, Any]]] = []
    for _row, cells in rows:
        times = [t for c in cells if (t := _hours(str(c.get("text") or "") + " " + str(c.get("full_text") or "")))]
        prices = [float(m.group(1) or m.group(2))
                  for c in cells if (m := _PRICE_RE.search(str(c.get("text") or "")))]
        numbers = [float(v) for c in cells
                   for v in re.findall(r"(?<![\d:./])\d+(?:\.\d+)?(?![\d:/])",
                                       str(c.get("text") or "") + " " + str(c.get("full_text") or ""))]
        metrics: dict[str, float] = {}
        if len(times) >= 2:
            duration = max(times) - min(times)
            if duration < 0:
                duration += 24
            metrics["dur"] = duration
            metrics["dep"] = min(t for t in times)
        if prices:
            metrics["price"] = min(prices) if direction == "min" else max(prices)
        if what == "dur" and "dur" not in metrics and len(numbers) >= 1:
            metrics["dur"] = numbers[0]
        if metrics:
            parsed.append((_row, cells, metrics))
    if not parsed:
        return []
    values = [metrics[what] for _r, _c, metrics in parsed if what in metrics]
    if not values:
        return []
    chosen_value = (min if direction == "min" else max)(values)
    for _row, cells, metrics in parsed:
        if metrics.get(what) == chosen_value:
            out = [(f"click@{c['index']}", "SUPERLATIVE_RECORD",
                    {"element": c["index"], "measure": what, "value": chosen_value, "word": keyword})
                   for c in cells if c.get("can_click") and _box(c)][:8]
            if out:
                return out
            element = _row if isinstance(_row, Mapping) else None
            if element is not None and element.get("can_click") and _box(element):
                return [(f"click@{element['index']}", "SUPERLATIVE_RECORD",
                        {"element": element["index"], "measure": what, "value": chosen_value,
                         "word": keyword})]
            return []
    return []


def _odd_even_marks(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Mark the numbers below as odd or even": two columns of choices and a column of numbers
    are told apart by their boxes -- same row band, nearest header -- and the choice is parity."""
    if "odd" not in _lower(observation.get("utterance")) or "even" not in _lower(observation.get("utterance")):
        return []
    elements = _elements(observation)
    numbers = [e for e in elements
               if re.fullmatch(r"\d{1,4}", _squash(e.get("text")).strip()) and _box(e)]
    headers: dict[str, float] = {}
    for element in elements:
        text = _lower(element.get("text")).strip()
        if text in {"odd", "even"} and _box(element):
            headers.setdefault(text, _centre(_box(element) or [0] * 4)[0])
    choices: list[tuple[str, Mapping[str, Any]]] = []
    for element in elements:
        if not element.get("can_click") or not _box(element):
            continue
        if _lower(element.get("text")).strip() in {"odd", "even"}:
            choices.append((_lower(element.get("text")).strip(), element))
        elif _lower(element.get("type")) == "radio":
            # a radio with no words of its own: its column is the header whose x it stands under
            if headers:
                x = _centre(_box(element) or [0] * 4)[0]
                column = min(headers.items(), key=lambda pair: abs(pair[1] - x))
                if abs(column[1] - x) <= 60:
                    choices.append((column[0], element))
    if not numbers or len({c for c, _e in choices}) < 2:
        return []
    out: list[tuple[str, str, dict[str, Any]]] = []
    for number in sorted(numbers, key=lambda e: ((_box(e) or [0] * 4)[1], (_box(e) or [0] * 4)[0])):
        value = int(_squash(number.get("text")).strip())
        parity = "odd" if value % 2 else "even"
        ny = _centre(_box(number) or [0] * 4)[1]
        same_row = [(word, element) for word, element in choices
                    if word == parity and _box(element)
                    and abs(_centre(_box(element) or [0] * 4)[1] - ny) <= max(18.0, (_box(number) or [0] * 4)[3])]
        if same_row:
            word, element = same_row[0]
            out.append((f"click@{element['index']}", "ODD_EVEN_BY_PARITY",
                        {"element": element["index"], "number": value, "marks": word}))
        elif not out and choices:
            # one column of choices beside one column of numbers: pair by rank instead of by row
            ranked = sorted([c for c in choices if c[0] == parity],
                            key=lambda pair: _centre(_box(pair[1]) or [0] * 4)[1])
            position = sorted(numbers, key=lambda e: _centre(_box(e) or [0] * 4)[1]).index(number)
            if position < len(ranked):
                word, element = ranked[position]
                out.append((f"click@{element['index']}", "ODD_EVEN_BY_PARITY",
                            {"element": element["index"], "number": value, "marks": word}))
        if len(out) >= 12:
            break
    return out


def _count_noun(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Type the total number of blocks ...": count the things the noun names on the page --
    matched by the noun against the page's own words for its parts -- and type the count."""
    utterance = _lower(observation.get("utterance"))
    match = re.search(r"\b(?:total number of|number of|how many)\s+([a-z]+)", utterance)
    if not match:
        return []
    noun = match.group(1).rstrip("s") or match.group(1)
    stem = noun[:-1] if len(noun) > 3 and noun.endswith("s") else noun
    hits = []
    for element in _elements(observation):
        if not _box(element) or element.get("tag") in {"button", "input", "textarea", "select", "option"}:
            continue
        where = _lower(element.get("classes")) + " " + _lower(element.get("id"))
        if re.search(rf"\b{re.escape(stem)}s?\b", where):
            hits.append(element)
    if len(hits) < 1:
        return []
    count = len(hits)
    out: list[tuple[str, str, dict[str, Any]]] = []
    for element in _elements(observation):
        if element.get("can_type"):
            out.append((f"type@{element['index']}={count}", "COUNT_THEN_TYPE",
                        {"element": element["index"], "count": count, "of": noun,
                         "sample": [h["index"] for h in hits[:5]]}))
            if len(out) >= 3:
                break
    return out


def _nth_word_type(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Find the 5th word in the paragraph, type that ...": the nth word of the longest text
    on the page is a value no literal pool contains; it is arithmetic over the page."""
    utterance = _lower(observation.get("utterance"))
    ordinal = None
    match = re.search(r"\b(\d+)(?:st|nd|rd|th)\s+word\b", utterance)
    if match:
        ordinal = int(match.group(1))
    else:
        for word, n in _WORD_ORDINAL.items():
            if re.search(rf"\b{word}\s+word\b", utterance):
                ordinal = n
                break
    if ordinal is None:
        return []
    paragraph = max(_elements(observation), key=lambda e: len(str(e.get("text") or e.get("full_text") or "")),
                    default=None)
    if paragraph is None:
        return []
    text = str(paragraph.get("text") or paragraph.get("full_text") or "")
    words = re.findall(r"[\w'']+", text)
    if len(words) < ordinal:
        return []
    target = words[ordinal - 1]
    out: list[tuple[str, str, dict[str, Any]]] = []
    for element in _elements(observation):
        if element.get("can_type") and str(element.get("value") or "") != target:
            out.append((f"type@{element['index']}={target}", "NTH_WORD_TYPE",
                        {"element": element["index"], "nth": ordinal, "word": target,
                         "paragraph": paragraph["index"]}))
            if len(out) >= 3:
                break
    return out


def _pair_transfer(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Enter the value that corresponds with each label": a table of label/value rows and a
    run of fields of the same count pair up by position; the value moves by being typed."""
    utterance = _lower(observation.get("utterance"))
    if "correspond" not in utterance and not ("label" in utterance and "value" in utterance):
        return []
    fields = sorted([e for e in _elements(observation) if e.get("can_type") and _box(e)],
                    key=lambda e: ((_box(e) or [0] * 4)[1], (_box(e) or [0] * 4)[0]))
    rows = _rows_of(observation)
    values: list[str] = []
    for _row, cells in rows:
        texts = [t for t in (_squash(c.get("text")) for c in cells) if t]
        if len(texts) >= 2:
            values.append(texts[-1])
        elif len(texts) == 1 and re.search(r"\d", texts[0]):
            values.append(texts[0])
    if not fields or len(values) < len(fields) or not len(values) == len(fields):
        return []
    out: list[tuple[str, str, dict[str, Any]]] = []
    for field, value in zip(fields, values):
        if str(field.get("value") or "") == value:
            continue
        out.append((f"type@{field['index']}={value}", "PAIR_TRANSFER",
                    {"element": field["index"], "value": value}))
    return out[:8]


def _ordinal_widget(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"click the 3rd checkbox, then enter the number \"10\" into the 2nd textbox": ordinals
    are geometry over a kind -- sort the widgets of the named kind by position, take the nth --
    and the value that follows is paired with that field, which no pool of literals pairs."""
    utterance = str(observation.get("utterance") or "")
    matches = list(_ORDINAL_RE.finditer(_lower(utterance)))
    if not matches:
        return []
    elements = _elements(observation)
    out: list[tuple[str, str, dict[str, Any]]] = []
    for match in matches:
        ordinal = int(match.group(1))
        kind = match.group(2).split()[0].strip()
        kind = {"checkbox": "checkbox", "radio": "radio", "textbox": "text", "box": "text",
                "text": "text", "field": "text", "input": "text", "textarea": "text",
                "button": "button", "dropdown": "select", "slider": "slider"}.get(kind, kind)
        if kind == "text":
            widgets = [e for e in elements if e.get("can_type") and _box(e)]
        elif kind in {"checkbox", "radio"}:
            widgets = [e for e in elements
                       if _lower(e.get("type")) == kind or (kind == "checkbox" and "check" in _lower(e.get("classes")))
                       or (kind == "radio" and "radio" in _lower(e.get("classes")))]
            widgets = [e for e in widgets if _box(e)]
        elif kind == "button":
            widgets = [e for e in elements if e.get("can_click") and _box(e) and _lower(e.get("tag")) == "button"]
        else:
            widgets = [e for e in elements if e.get("can_click") and _box(e)]
        widgets.sort(key=lambda e: ((_box(e) or [0] * 4)[1], (_box(e) or [0] * 4)[0]))
        if len(widgets) < ordinal:
            continue
        target = widgets[ordinal - 1]
        if kind == "text":
            quoted = re.search(r"\"([^\"]{1,60})\"", utterance)
            spelled = re.search(r"(?:enter|type|set)\s+(?:the\s+)?(?:number\s+)?\"?([^\s\",]+)\"?", _lower(utterance))
            value = quoted.group(1) if quoted else (spelled.group(1) if spelled else None)
            if value is not None and str(target.get("value") or "") != value:
                out.append((f"type@{target['index']}={value}", "ORDINAL_FIELD_VALUE",
                            {"element": target["index"], "ordinal": ordinal, "value": value}))
        else:
            out.append((f"click@{target['index']}", "ORDINAL_WIDGET",
                        {"element": target["index"], "ordinal": ordinal, "kind": kind}))
    return out


def _match_all_records(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Search for thriller movies directed by George from year 1994" / "the email from Janot"
    / "Reply ... on all posts by @eget": rows whose text carries every instruction word that
    appears anywhere on the page are the rows that mean it; the control the instruction names
    inside them is what to press, all of them when the instruction says all, the first few when
    it says a count."""
    utterance = _lower(observation.get("utterance"))
    if "extension" in utterance and "no file" in utterance:
        return _files_without_extension(observation)
    content = [w for w in re.findall(r"[\w@.']+", utterance)
               if (len(w) >= 3 and w not in STOP_WORDS and not w.isdigit()
                   or (w.isdigit() and len(w) == 4))]
    if not content:
        return []
    rows = _rows_of(observation)
    if not rows:
        return []
    row_texts = [
        _lower(" ".join(str(c.get("text") or "") + " " + str(c.get("full_text") or "") for c in cells))
        for _row, cells in rows
    ]
    salient = [w for w in content if any(w in text for text in row_texts)]
    if not salient:
        return []
    matched = [(row, cells, text) for (row, cells), text in zip(rows, row_texts)
               if all(w in text for w in salient)]
    if not matched:
        return []
    controls = [w for w in CONTROL_VOCAB if w in utterance]
    limit = 10
    count = re.search(r"\b(\d+)\s+(?:posts?|items?|rows?|entries|emails?)", utterance)
    if count:
        limit = int(count.group(1))
    out: list[tuple[str, str, dict[str, Any]]] = []
    for row, cells, _text in matched[:limit]:
        pressed = False
        for control in controls:
            for cell in cells:
                for element in _descendants(cell, observation):
                    where = _lower(element.get("text")) + " " + _lower(element.get("classes")) \
                        + " " + _lower(element.get("id"))
                    if element.get("can_click") and control in where and _box(element):
                        out.append((f"click@{element['index']}", "CONTROL_IN_MATCHING_RECORD",
                                    {"element": element["index"], "control": control,
                                     "record": row["index"] if isinstance(row, Mapping) else None}))
                        pressed = True
                        break
                if pressed:
                    break
            if pressed:
                break
        if not pressed:
            # The instruction names a control the surface does not show: a row's own
            # disclosure ("more") is what shows it -- press that and the control exists next
            # state. Only when the row shows no disclosure does the row itself get pressed.
            for cell in cells:
                for element in _descendants(cell, observation):
                    where = _lower(element.get("classes")) + " " + _lower(element.get("id")) \
                        + " " + _lower(element.get("title"))
                    if element.get("can_click") and _box(element) and \
                            any(flag in where for flag in ("more", "menu", "options", "overflow", "kebab")):
                        out.append((f"click@{element['index']}", "REVEAL_CONTROL",
                                    {"element": element["index"], "record": row["index"] if isinstance(row, Mapping) else None}))
                        pressed = True
                        break
                if pressed:
                    break
        if not pressed:
            for cell in cells:
                if cell.get("can_click") and _box(cell):
                    out.append((f"click@{cell['index']}", "RECORD_MATCHING_ALL_WORDS",
                                {"element": cell["index"], "words": salient[:6]}))
                    pressed = True
                    break
            if not pressed and isinstance(row, Mapping) and row.get("can_click"):
                out.append((f"click@{row['index']}", "RECORD_MATCHING_ALL_WORDS",
                            {"element": row["index"], "words": salient[:6]}))
        if len(out) >= 16:
            break
    return out


def _descendants(element: Mapping[str, Any], observation: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """The element itself and everything under it -- used to find the control inside a record."""
    by_index = _by_index(observation)
    out: list[Mapping[str, Any]] = []
    for candidate in _elements(observation):
        cursor: Mapping[str, Any] | None = candidate
        for _ in range(12):
            if cursor is None:
                break
            if int(cursor.get("index", -1)) == int(element.get("index", -2)):
                out.append(candidate)
                break
            parent = cursor.get("parent", -1)
            if parent is None or int(parent) < 0:
                break
            cursor = by_index.get(int(parent))
    return out


def _files_without_extension(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    utterance = _lower(observation.get("utterance"))
    out: list[tuple[str, str, dict[str, Any]]] = []
    controls = [w for w in CONTROL_VOCAB if w in utterance]
    for element in _elements(observation):
        text = _squash(element.get("text")).strip()
        if not element.get("can_click") or not _box(element) or not text or len(text) > 40 or " " in text:
            continue
        if not (re.fullmatch(r"[A-Za-z0-9_\-]+", text) and "." not in text
                and text.lower() not in _CHROME_WORDS and re.search(r"[A-Za-z]", text)):
            continue
        in_output = any("output" in _lower(p.get("classes")) + _lower(p.get("id"))
                        or "file" in _lower(p.get("classes")) + _lower(p.get("id"))
                        for p in _parent_chain(element, _by_index(observation)))
        if in_output:
            out.append((f"click@{element['index']}", "FILE_WITHOUT_EXTENSION",
                        {"element": element["index"], "name": text}))
    if len(out) > 6:
        out = out[:6]
    index = _by_index(observation)
    for element in _elements(observation):
        if _in_instruction_region(element, index):
            continue
        where = _lower(element.get("text")) + " " + _lower(element.get("classes")) + " " + _lower(element.get("id"))
        if element.get("can_click") and _box(element) and any(c in where for c in controls):
            out.append((f"click@{element['index']}", "DELETE_CONTROL",
                        {"element": element["index"]}))
    return out[:9]


def _drag_coloured(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Drag all blue shapes into the left box": the sources are the shapes whose own colour the
    instruction names, the destination is the box the instruction names by side; grabbing the
    right sources cheap is the whole contribution -- drops are offered while holding."""
    utterance = _lower(observation.get("utterance"))
    if "drag" not in utterance:
        return []
    colour = next((name for name in NAMED_COLOURS if re.search(rf"\b{name}s?\b", utterance)), None)
    if colour is None:
        found = _HEX_RE.search(utterance)
        colour = found.group(1) if found else None
    if colour is None:
        return []
    target_hue = NAMED_COLOURS.get(colour, _colour_hue(colour))
    out: list[tuple[str, str, dict[str, Any]]] = []
    for element in _elements(observation):
        if not element.get("can_click") or not _box(element):
            continue
        where = _lower(element.get("classes")) + " " + _lower(element.get("id"))
        hue = _colour_hue(element.get("colour"))
        named = colour and re.search(rf"\b{re.escape(colour)}\b", where)
        if not (named or (hue is not None and target_hue is not None and _hue_near(hue, target_hue))):
            continue
        if element.get("tag") not in SVG_SHAPES and not re.search(
                r"shape|square|circle|box|item|drag", where) and element.get("tag") not in {"img", "canvas"}:
            if not named:
                continue
        out.append((f"grab@{element['index']}", "GRAB_INSTRUCTED_COLOUR",
                    {"element": element["index"], "colour": colour}))
        if len(out) >= 8:
            break
    return out


def _colour_wheel_points(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Select magenta with the color picker": the wheel is a round widget; its own box gives
    the centre and radius; a ring of points around it covers every hue, ordered by the hue the
    instruction (or a shown swatch) names -- the widget's angle convention is never assumed."""
    utterance = _lower(observation.get("utterance"))
    if not re.search(r"colou?r (picker|wheel)|colou?rwheel|picker", utterance):
        return []
    elements = _elements(observation)
    # A page whose colour goes into a FIELD is the typed route's page (the picker that opens
    # under the field is a dialog of coloured cells, not a wheel); ring points belong to a
    # page that shows the wheel itself.
    if any(e.get("can_type") and _box(e) and (
            _lower(e.get("id")) + _lower(e.get("classes")) + _lower(e.get("type"))
            or e.get("colour")) for e in elements):
        return []
    wheel = None
    for element in elements:
        box = _box(element)
        if not box or min(box[2], box[3]) < 40:
            continue
        where = _lower(element.get("classes")) + " " + _lower(element.get("id")) + " " + _lower(element.get("tag"))
        if element.get("tag") == "canvas" or re.search(r"wheel|picker|colou?r", where):
            wheel = element
            break
    if wheel is None:
        candidates = [e for e in elements if e.get("tag") in {"svg", "canvas", "img"} and _box(e)
                      and min((_box(e) or [0] * 4)[2], (_box(e) or [0] * 4)[3]) >= 40]
        wheel = candidates[0] if candidates else None
    if wheel is None:
        return []
    box = _box(wheel) or [0, 0, 0, 0]
    cx, cy = _centre(box)
    radius = 0.34 * min(box[2], box[3])
    wanted_hue: float | None = None
    found = _HEX_RE.search(utterance)
    if found:
        wanted_hue = _colour_hue("#" + found.group(1))
    if wanted_hue is None:
        for name, hue in NAMED_COLOURS.items():
            if re.search(rf"\b{name}\b", utterance):
                wanted_hue = float(hue)
                break
    if wanted_hue is None:
        for element in elements:  # "the following color": the small swatch the page shows
            swatch_box = _box(element)
            if not swatch_box or max(swatch_box[2], swatch_box[3]) > 40:
                continue
            hue = _colour_hue(element.get("colour"))
            if hue is not None and element is not wheel:
                wanted_hue = hue
                break
    ring = [k * 22.5 for k in range(16)]
    if wanted_hue is not None:
        ring.sort(key=lambda a: abs((a - wanted_hue + 180) % 360 - 180))
    out: list[tuple[str, str, dict[str, Any]]] = []
    for angle in ring:
        x = cx + radius * math.cos(math.radians(angle - 90))
        y = cy + radius * math.sin(math.radians(angle - 90))
        out.append((_point_action(x, y), "COLOUR_WHEEL_RING",
                    {"wheel": wheel["index"], "angle": angle,
                     "wanted_hue": wanted_hue}))
    return out


def _drag_through_point(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Draw a vertical line that runs through the dot": the dot is an element, so the hand can
    take hold of it there; the release is a PLACE, and the vertical through the dot gives two."""
    utterance = _lower(observation.get("utterance"))
    if "line" not in utterance or not re.search(r"through the (dot|point|circle)", utterance):
        return []
    dot = next((e for e in _elements(observation)
                if _box(e) and (lambda b: b[2] * b[3] <= 40 * 40)(
                    _box(e) or [0, 0, 0, 0])
                and re.search(r"dot|point|circle|marker|black", _lower(e.get("classes"))
                              + " " + _lower(e.get("id")) + " " + _lower(e.get("tag")))), None)
    if dot is None:
        small = sorted([e for e in _elements(observation)
                        if _box(e) and (e.get("tag") in SVG_SHAPES)
                        and (_box(e) or [0] * 4)[2] * (_box(e) or [0] * 4)[3] <= 40 * 40],
                       key=lambda e: (_box(e) or [0] * 4)[2] * (_box(e) or [0] * 4)[3])
        dot = small[0] if small else None
    if dot is None:
        return []
    return [(f"grab@{dot['index']}", "GRAB_THE_POINT_TO_DRAW_THROUGH", {"element": dot["index"]})]


def _dropat_places(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """While the hand HOLDS something: the places a release through the held point means --
    the vertical through a dot, both ways, keeps the drag on the line the instruction names."""
    utterance = _lower(observation.get("utterance"))
    if observation.get("holding") is None:
        return []
    if not re.search(r"vertical line|through the (dot|point)", utterance):
        return []
    held = _elements(observation)
    holding_index = observation.get("holding")
    target = next((e for e in held if int(e.get("index", -1)) == int(holding_index)), None)
    if target is None or not _box(target):
        return []
    x, y = _centre(_box(target) or [0] * 4)
    return [(_drop_action(x, y - 70), "RELEASE_ABOVE_THE_POINT", {"point": target["index"]}),
            (_drop_action(x, y + 70), "RELEASE_BELOW_THE_POINT", {"point": target["index"]})]


def _copy_value(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Copy the text in the textarea ..., paste it into the textbox": the value the page holds
    already -- a textarea's own content -- paired with the input it must be pasted into; the
    "3rd text area" form picks which source by position."""
    utterance = _lower(observation.get("utterance"))
    if "copy" not in utterance or "paste" not in utterance:
        return []
    sources = sorted([e for e in _elements(observation)
                      if e.get("tag") == "textarea" and _box(e)],
                     key=lambda e: ((_box(e) or [0] * 4)[1], (_box(e) or [0] * 4)[0]))
    if not sources:
        return []
    ordinal = re.search(r"\b(\d+)(?:st|nd|rd|th)\s+text\s?area", utterance)
    source = sources[int(ordinal.group(1)) - 1] if ordinal and int(ordinal.group(1)) <= len(sources) else sources[0]
    value = str(source.get("value") or "")
    if not value:
        return []
    out: list[tuple[str, str, dict[str, Any]]] = []
    for element in _elements(observation):
        if element.get("can_type") and element.get("tag") == "input" and _box(element):
            if str(element.get("value") or "") == value:
                continue
            out.append((f"type@{element['index']}={value}", "COPY_PASTE_VALUE",
                        {"element": element["index"], "source": source["index"]}))
    return out[:3]


_FIELD_SPAN_RE = (
    ("from", re.compile(r"\bfrom:\s*([A-Z][^:]{2,42}?)(?=\s*(?:\bto:|\bon\b))")),
    ("to", re.compile(r"\bto:\s*([^:]{2,42}?)(?=\s+\bon\b)")),
    ("date", re.compile(r"\bon\s+(\d{1,2}/\d{1,2}/\d{4})\b")),
)


def _field_span_fill(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Book the shortest flight from: X to: Y on D": instruction fields the page gives no
    literal pool for -- a place name is a phrase, not a quoted span -- paired with the input
    whose own name says which field it is (id/class/label hint: 'from', 'to', 'date')."""
    utterance = str(observation.get("utterance") or "")
    elements = _elements(observation)
    out: list[tuple[str, str, dict[str, Any]]] = []
    for hint, pattern in _FIELD_SPAN_RE:
        found = pattern.search(utterance)
        if not found:
            continue
        span = _squash(found.group(1))
        if not span:
            continue
        for element in elements:
            if not element.get("can_type") or not _box(element):
                continue
            where = _lower(element.get("id")) + " " + _lower(element.get("classes"))
            labels = _lower(" ".join(str(p.get("text") or "") for p in _parent_chain(element, _by_index(observation))))
            if hint == "date":
                if "date" not in where + " " + labels and element.get("type") != "date":
                    continue
            elif hint not in where:
                continue
            if str(element.get("value") or "") == span:
                continue
            out.append((f"type@{element['index']}={span}", "FIELD_SPAN_FILL",
                        {"element": element["index"], "field": hint, "span": span}))
    return out[:4]


def _labelled_pair_transfer(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Enter the value that corresponds with each label" where the form's order is NOT the
    table's order: each field's own label words pick the row, and that row's value is typed."""
    utterance = _lower(observation.get("utterance"))
    if "correspond" not in utterance and "label" not in utterance:
        return []
    index = _by_index(observation)
    rows = _rows_of(observation)
    if not rows:
        return []
    out: list[tuple[str, str, dict[str, Any]]] = []
    for field in _elements(observation):
        if not field.get("can_type") or not _box(field):
            continue
        label_text = ""
        parent = index.get(int(field.get("parent", -1)))
        if parent is not None:
            siblings = [e for e in _elements(observation) if int(e.get("parent", -1)) == int(parent["index"])]
            label_text = " ".join(str(e.get("text") or "") for e in siblings if e.get("tag") == "label")
            if not label_text:
                label_text = str(parent.get("text") or "")
        stem = _lower(label_text).strip(" :")
        if not stem:
            continue
        value = None
        for _row, cells in rows:
            texts = [_squash(c.get("text")) for c in cells]
            if any(t and _lower(t) == stem for t in texts) and len(texts) >= 2:
                value = texts[-1]
                break
        if value is None or str(field.get("value") or "") == value:
            continue
        out.append((f"type@{field['index']}={value}", "LABELLED_PAIR_TRANSFER",
                    {"element": field["index"], "label": stem, "value": value}))
    return out[:8]


NAMED_HEX = {
    "red": "ff0000", "green": "00ff00", "blue": "0000ff", "yellow": "ffff00", "cyan": "00ffff",
    "magenta": "ff00ff", "fuchsia": "ff00ff", "black": "000000", "white": "ffffff",
    "orange": "ffa500", "purple": "800080", "violet": "ee82ee", "pink": "ffc0cb",
    "grey": "808080", "gray": "808080", "brown": "a52a2a", "lime": "00ff00", "teal": "008080",
    "navy": "000080", "aqua": "00ffff", "silver": "c0c0c0", "maroon": "800000", "olive": "808000",
}


def _colour_hex(text: Any) -> str | None:
    """Six hex digits of an inline colour (hex, rgb(...), or a name), None when unstateable."""
    value = _lower(text)
    if not value or value in {"none", "transparent"}:
        return None
    found = _HEX_RE.search(value)
    if found:
        raw = found.group(1)
        return (raw if len(raw) == 6 else "".join(c * 2 for c in raw)).lower()
    rgb = re.search(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})", value)
    if rgb:
        return "".join(f"{int(v):02x}" for v in rgb.groups())
    if value in NAMED_HEX:
        return NAMED_HEX[value]
    for name, hex_value in NAMED_HEX.items():
        if re.search(rf"\b{name}\b", value):
            return hex_value
    return None


def _named_colour_type(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Select magenta with the color picker": a colour NAME is a fact about the colour
    vocabulary, and a field that shows colours takes its value as the six hex digits -- so the
    derived value is the colour's own hex, not a position on a wheel nobody states a rule for.
    ""Select the following color" shows a swatch; its own stated colour is the value. Both
    forms close with a press somewhere the dialog cannot be, because opening the field opens
    a picker that would otherwise take the submit click."""
    utterance = _lower(observation.get("utterance"))
    if not re.search(r"colou?r", utterance):
        return []
    elements = _elements(observation)
    field = next((e for e in elements
                  if e.get("can_type") and _box(e) and any(
                      word in _lower(e.get("id")) + " " + _lower(e.get("classes"))
                      for word in ("color", "colour", "jscolor", "swatch", "picker"))
                      or (e.get("can_type") and e.get("colour") and _box(e))), None)
    if field is None:
        return []
    target_hex = None
    source = "name"
    found = next((name for name in NAMED_HEX if re.search(rf"\b{name}\b", utterance)), None)
    if found is not None:
        target_hex = NAMED_HEX[found]
    else:
        for element in elements:
            if element is field or not _box(element):
                continue
            box = _box(element) or [0, 0, 0, 0]
            if max(box[2], box[3]) > 40:
                continue
            stated = _colour_hex(element.get("colour"))
            if stated:
                target_hex, source = stated, "swatch"
                break
    if target_hex is None:
        return []
    if str(field.get("value") or "").lower() == target_hex:
        # The value is already the colour's own: the field can still be showing its picker
        # over the button, so the dismissal stays offered (it is a free press on empty page)
        # while the typing does not repeat.
        return [("pressat@240.0,8.0", "DISMISS_DIALOG", {"field": field["index"]})]
    return [
        (f"type@{field['index']}={target_hex}", "NAMED_COLOUR_HEX",
         {"element": field["index"], "source": source, "hex": target_hex}),
        ("pressat@240.0,8.0", "DISMISS_DIALOG", {"field": field["index"]}),
    ]


def _select_and_style(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"give the text viverra. the style underlined": select the named run of text (three
    fast presses on whatever shows it) and press the control the style word names."""
    utterance = _lower(observation.get("utterance"))
    style = next((w for w in ("underline", "bold", "italic", "strike", "strikethrough",
                              "overline", "align-left", "align-center", "align-right")
                  if w in utterance), None)
    if style is None:
        return []
    target = None
    # the phrasing that NAMES a run: 'give the text <run>' -- a bare 'text' matches the
    # instruction's own "the text editor" first and would select the wrong thing entirely.
    match = re.search(r"give the text\s+([\w.]{2,30})", utterance)
    if match:
        target = match.group(1)
    if not target:
        quoted = re.search(r"\"([\w.]{2,30})\"", utterance)
        target = quoted.group(1) if quoted else None
    out: list[tuple[str, str, dict[str, Any]]] = []
    elements = _elements(observation)
    index = _by_index(observation)
    if target:
        stem = target.strip(".,;:!")
        matches = []
        for element in elements:
            if not _box(element):
                continue
            if _in_instruction_region(element, index):
                continue
            shown = str(element.get("text") or "") + " " + str(element.get("full_text") or "")
            if stem in shown and element.get("tag") in {"textarea", "div", "span", "p", "input"}:
                matches.append(element)
        if matches:
            # the most specific place the run shows: a typing field first, else the element
            # whose shown text is SHORTEST -- a page's wrapper also 'contains' the word.
            chosen = min(matches, key=lambda e: (
                0 if (e.get("can_type") or e.get("tag") == "textarea") else 1,
                len(str(e.get("text") or "")) or len(str(e.get("full_text") or "")) + 10_000))
            out.append((f"triple@{chosen['index']}", "SELECT_NAMED_RUN",
                        {"element": chosen["index"], "run": stem}))
    stems = {style, style.rstrip("d"), style.rstrip("ed"), style + "d", style + "ed"}
    for element in elements:
        if not element.get("can_click") or not _box(element):
            continue
        if _in_instruction_region(element, index):
            continue
        where = _lower(element.get("text")) + " " + _lower(element.get("classes")) \
            + " " + _lower(element.get("title")) + " " + _lower(element.get("aria-label"))
        if any(s and s in where for s in stems):
            out.append((f"click@{element['index']}", "STYLE_CONTROL",
                        {"element": element["index"], "style": style}))
            break
    return out[:3]


_CHROME_WORDS = {"terminal", "file", "files", "commands", "command", "help", "ls", "dir", "welcome",
                 "login", "available", "list", "delete", "output", "input", "user"}


def _terminal_commands(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Use the terminal to delete a file that has no file extension": a terminal takes
    COMMANDS -- listing is 'ls', removing is 'rm' -- and the files themselves are whatever the
    listing shows afterwards. Before any listing, the only move is the listing."""
    utterance = _lower(observation.get("utterance"))
    if "terminal" not in utterance and "command" not in utterance:
        return []
    fields = [e for e in _elements(observation) if e.get("can_type") and _box(e)]
    if not fields:
        return []
    out: list[tuple[str, str, dict[str, Any]]] = []
    dotless: list[str] = []
    for element in _elements(observation):
        text = _squash(element.get("text")).strip()
        if not text or len(text) > 40 or " " in text or not _box(element):
            continue
        if re.fullmatch(r"[A-Za-z0-9_\-]+", text) and "." not in text \
                and text.lower() not in _CHROME_WORDS and re.search(r"[A-Za-z]", text):
            in_output = any(c in _lower(p.get("classes")) + _lower(p.get("id"))
                            for p in _parent_chain(element, _by_index(observation)))
            if in_output:
                dotless.append(text)
    if "delete" in utterance or "remove" in utterance:
        for name in dict.fromkeys(dotless):
            out.append((f"type@{fields[0]['index']}=rm {name}", "TERMINAL_RM_FILE",
                        {"element": fields[0]["index"], "file": name}))
        if not out:
            out.append((f"type@{fields[0]['index']}=ls", "TERMINAL_LIST_FIRST",
                        {"element": fields[0]["index"]}))
    return out[:5]


def _finalize(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """The button the instruction sends at the end -- offered with the derivations so it is
    priced with them, last of them in declared order, and free rather than contending with
    every other turn-2 button for the search's attention. The instruction region, which also
    SAYS submit, is never it."""
    utterance = _lower(observation.get("utterance"))
    if not re.search(r"\b(submit|press ok|then press|hit)\b", utterance):
        return []
    index = _by_index(observation)
    candidates = [e for e in _elements(observation)
                  if e.get("can_click") and _box(e) and not _in_instruction_region(e, index)]
    for element in candidates:                      # id/class first: the button says so itself
        where = _lower(element.get("id")) + " " + _lower(element.get("classes"))
        if re.search(r"sub|(^|\W)ok$|\bdone\b|\bfinish\b|\bsave\b", where):
            return [(f"click@{element['index']}", "FINALIZE_BUTTON", {"element": element["index"]})]
    for element in candidates:
        if re.search(r"sub|(^|\W)ok$|\bdone\b|\bfinish\b|\bsave\b", _lower(element.get("text"))):
            return [(f"click@{element['index']}", "FINALIZE_BUTTON", {"element": element["index"]})]
    return []


def _hot_extreme(observation: Mapping[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """"Find and click on the HOT area": among coloured cells the hottest red the page itself
    states (its own fill) is where the word points; no colour stated, no candidate."""
    if "hot" not in _lower(observation.get("utterance")):
        return []
    best: tuple[float, Mapping[str, Any]] | None = None
    for element in _elements(observation):
        hue = _colour_hue(element.get("colour"))
        if hue is None or not _box(element):
            continue
        heat = 1 - abs((hue - 0 + 180) % 360 - 180) / 180  # 1.0 at red, 0 at cyan
        if best is None or heat > best[0]:
            best = (heat, element)
    if best is None or best[0] < 0.6:
        return []
    x, y = _centre(_box(best[1]) or [0] * 4)
    return [(_point_action(x, y), "HOTTEST_STATED_COLOUR",
             {"element": best[1]["index"], "heat": round(best[0], 3)})]


OPERATORS = (
    _centre_of, _right_angle, _slider_to_value, _move_on_target, _click_moving_shapes,
    _date_cell, _path_segments, _superlative_records, _odd_even_marks, _count_noun,
    _nth_word_type, _pair_transfer, _labelled_pair_transfer, _ordinal_widget, _match_all_records,
    _drag_coloured, _colour_wheel_points, _named_colour_type, _copy_value, _field_span_fill,
    _terminal_commands, _drag_through_point, _select_and_style, _hot_extreme, _finalize,
    _dropat_places, _exact_centre, _exact_midpoint, _exact_right_angle,
)

MAX_PER_RULE = 16


def aimed_rows(observation: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every candidate with its rule and witness, first rule wins a duplicated action, bounded
    per rule so one page cannot drown the search in offers. While the hand HOLDS something it
    can do one thing -- let go -- so only the release places are offered then, exactly as the
    shipped hand offers only drops."""
    if observation.get("holding") is not None:
        operators: Sequence[Any] = (_dropat_places,)
    else:
        operators = OPERATORS
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for operator in operators:
        try:
            produced = operator(observation)
        except Exception:                      # an operator that cannot read this page yields nothing
            produced = []
        kept = 0
        for action, rule, witness in produced:
            if action in seen or kept >= MAX_PER_RULE:
                continue
            seen.add(action)
            kept += 1
            out.append({"action": action, "rule": rule, "witness": witness})
    return out


def aimed_actions(observation: Mapping[str, Any]) -> list[str]:
    return [row["action"] for row in aimed_rows(observation)]


def rule_of(observation: Mapping[str, Any], action: str) -> dict[str, Any] | None:
    """Which rule produced this action, and its witness -- the learnable unit of a success."""
    wanted = str(action)
    for row in aimed_rows(observation):
        if row["action"] == wanted:
            return {"rule": row["rule"], "witness": row["witness"]}
    return None


def decoy_actions(observation: Mapping[str, Any], *, seed: int = 20261116) -> list[str]:
    """The same count and the same shape as the aimed actions, drawn from the wrong witness on
    purpose: a random place for a place, a random reachable index for an index, a random word
    for a value. The control arm exists so a gain cannot be explained by more offers."""
    rng = random.Random(seed ^ zlib.crc32(str(observation.get("utterance") or "").encode()))
    real = aimed_actions(observation)
    elements = _elements(observation)
    reachable = [int(e["index"]) for e in elements if e.get("can_click") and _box(e)]
    fields = [int(e["index"]) for e in elements if e.get("can_type")]
    pool = [w for w in dv.words_of(observation.get("utterance")) if w and len(w) <= 40]
    for _, _, text in dv.visible_texts(observation):
        pool += [w for w in dv.words_of(text)[:5] if w and len(w) <= 40]
    out: list[str] = []
    for real_action in real:
        kind = real_action.partition("@")[0]
        if kind in {"pressat", "moveat", "dropat"}:
            out.append(f"{kind}@{rng.uniform(1, 479):.1f},{rng.uniform(1, 359):.1f}")
        elif kind == "click" and reachable:
            out.append(f"click@{rng.choice(reachable)}")
        elif kind == "type" and fields:
            value = rng.choice(pool) if pool else "0"
            out.append(f"type@{rng.choice(fields)}={value}")
        else:
            out.append(real_action)
    return [action for action in out if action]
