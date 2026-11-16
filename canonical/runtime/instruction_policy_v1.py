"""The instruction is the policy: produce the first action with NO experience and NO reward.

Why this file exists
--------------------
`demonstration_version_space_v1` settled what one success buys: not "everything, permanently", but
about 60% on unseen instances, and the information bound is ~2.76 *chosen* experiences rather than
one. That answer is correct and it is not the question that decides the plan.

The question that decides the plan is one layer beneath it:

    A demonstration has to be PRODUCED before it can be learned from.

On 2026-11-14 the one-success numbers were obtained by exploring until the page's own reward fired.
A deployed agent has no such oracle: the reward is exactly what it does not get. So every
"learn from one demonstration" result quietly assumes the hardest part has already been solved for
it -- by a search that was allowed to see the answer. That assumption is the whole load.

This module removes it. It emits actions from the instruction and the observation alone:

    no reward is read          (a test scans this file's source for it)
    no `done` flag is read     (same)
    no search, no retries against a signal -- one action at a time, in the order the instruction
    gives, and if the instruction does not say what to do next, it says so and stops

What that means in one sentence: if this arm succeeds, the knowledge was in the instruction, and
there were no parameters, no experiences and no reward anywhere in the path.

The shared-vocabulary law
-------------------------
The planner resolves a clause to an element with the SAME functions the checker uses
(`instruction_contract_v1`): one notion of "what the instruction said", used both to act and to
judge. Two vocabularies would let the machine do one thing and certify another, which is the
failure mode this tree has paid for before. Import, never re-derive.

What this arm is NOT
--------------------
It is not a skill learner and it does not remember anything. It is the floor: the capability
available at time zero. Every learner in the tree should be measured against it, because a skill
that does not beat "read the instruction" has learned nothing worth keeping.
"""

from __future__ import annotations

import re
import sys
import pathlib
from typing import Any, Mapping, Sequence

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from canonical.runtime import anchored_frame_v1 as anchored  # noqa: E402
from canonical.runtime import instruction_contract_v1 as contract_lib  # noqa: E402

SCHEMA = "PROJECT_BRAIN_INSTRUCTION_POLICY_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

plain = contract_lib.plain
element_label = contract_lib.element_label

#: How many presses the arm will spend bringing a control out of hiding ("find and click"). This is
#: not a search against a reward -- the press is chosen because the instruction said the thing must
#: be found, and the count is fixed before the episode starts so it cannot be tuned per page.
_REVEAL_BUDGET = 3

#: Presses that END an episode by submitting what was built. They must come last: pressing Submit
#: before choosing, typing or picking is a trace a wrong answer makes. Measured 2026-11-16 --
#: find-greatest pressed Submit first and lost, with the right pick already in the contract.
_TERMINAL = frozenset("submit ok login log in sign in agree confirm done continue save".split())

#: Clauses that legitimately need MORE THAN ONE action: a sequence of presses, a set of selections,
#: every container opened, an ordered run. Everything else is one action and is finished by it.
# Clause kinds whose every step legitimately looks like the last one: a multi-press sequence, a
# set of selections, a slider nudged repeatedly. Only these may repeat an identical action; a
# single CLICK_NAMED that repeats is always a no-op loop and is blocked.
#: The clauses a sentence's LATER half can compile to, once the page has what the earlier half
#: was for. Kept in one place so "read again" cannot quietly become a different compiler.
_LATE_OPERATORS = ("TYPE_VALUE", "NUMBER_PREDICATE", "SELECT_SET", "PRESS_CLASS")
_WRITES = ("TYPE_VALUE", "NUMBER_PREDICATE", "SELECT_SET")

_REPEATABLE = frozenset({"PRESS_SEQUENCE", "PRESS_SEQUENCE_BY_INDEX", "SELECT_SET", "EXPAND",
                         "ORDER", "SET_CONTROL", "DRAG_DESCRIBED", "MOVE_DIRECTION"})


# --------------------------------------------------------------------------- #
# clause -> the element it wants, on the page as it is now
# --------------------------------------------------------------------------- #
def _pressable(elements: Sequence[Mapping[str, Any]], index: int) -> bool:
    return 0 <= index < len(elements) and bool(
        elements[index].get("can_click") or elements[index].get("can_type"))


def _first_matching(elements, wanted: Sequence[str], *, also: Sequence[str] = (),
                    prefer_kind: str | None = None) -> int | None:
    """The first element whose label (or one of `also`) contains one of `wanted`."""
    keys = [plain(word) for word in wanted if plain(word)]
    if not keys:
        return None
    for element in elements:
        if not (element.get("can_click") or element.get("can_type")):
            continue
        if prefer_kind and str(element.get("tag")) != str(prefer_kind):
            continue
        shown = [plain(element_label(element))]
        shown += [plain(element.get(field)) for field in also]
        for key in keys:
            for text in shown:
                # "ut" must not select "vulputate." -- containment is allowed, substrings are not
                if text and (text == key or contract_lib._contains_word(text, key)
                             or (len(text) > len(key) and contract_lib._contains_word(key, text))):
                    return int(element["index"])
    return None


def _field_for(elements, index: int) -> int | None:
    """The element that actually receives text for the thing at `index`."""
    if _pressable(elements, index) and elements[index].get("can_type"):
        return index
    for other in elements:
        if int(other.get("parent", -2)) == index and other.get("can_type"):
            return int(other["index"])
    return index if _pressable(elements, index) else None


def _horizontal(elements, index: int, track: int | None = None) -> bool:
    """Whether the control lies along the x axis.

    Read from the TRACK, never from the handle: a handle is a small square and says nothing about
    the axis. With a displayed value the "index" is the display, so the track is the container
    that holds the handle.
    """
    measurements = []
    for candidate in (_container_of(elements, track) if track is not None else None,
                      _container_of(elements, index), track, index):
        if candidate is None:
            continue
        box = elements[candidate].get("box") if candidate < len(elements) else None
        if isinstance(box, (list, tuple)) and len(box) == 4:
            measurements.append((float(box[2]), float(box[3])))
    for width, height in measurements:
        if width != height:
            return width > height
    return True


def _holding(observation: Mapping[str, Any]) -> bool:
    return observation.get("holding") is not None


def _inside(element: Mapping[str, Any], box) -> bool:
    own = element.get("box")
    if not isinstance(own, (list, tuple)) or len(own) != 4 or not isinstance(box, (list, tuple)):
        return False
    return (own[0] >= box[0] and own[1] >= box[1]
            and own[0] + own[2] <= box[0] + box[2] and own[1] + own[3] <= box[1] + box[3])


def _one_step_along(elements, member: int, direction: str) -> int:
    """The element one step along the axis: the nearest addressable box in that direction."""
    source = next((e for e in elements if int(e["index"]) == member), None)
    if source is None or not isinstance(source.get("box"), (list, tuple)):
        return member
    x, y, w, h = source["box"]
    sx, sy = x + w / 2.0, y + h / 2.0
    best, best_distance = member, None
    for element in elements:
        index = int(element.get("index", -1))
        box = element.get("box")
        if index == member or not _pressable(elements, index) or not isinstance(box, (list, tuple)):
            continue
        cx, cy = box[0] + box[2] / 2.0, box[1] + box[3] / 2.0
        delta = (cy - sy) if direction == "down" else (sy - cy)
        if delta <= 0:
            continue
        distance = abs(delta) + abs(cx - sx) * 0.01
        if best_distance is None or distance < best_distance:
            best, best_distance = index, distance
    return best


def _nearest_box(elements, box, used=frozenset(), tolerance: float = 14.0,
                 claimed=()) -> int | None:
    """The pressable element occupying a remembered position, when its text is gone.

    Only unnamed elements qualify: a labelled element is matched by its label, never by
    proximity, so this cannot steal a press from a target the page still names.

    `claimed` are the positions already accounted for. A candidate that sits closer to a claimed
    position than to this one belongs to that other target: the page may renumber its elements
    between two observations, so an index proves nothing and only a position can be owned.
    """
    if not box or len(box) != 4:
        return None
    cx, cy = float(box[0]) + float(box[2]) / 2.0, float(box[1]) + float(box[3]) / 2.0
    claimed_centres = [(float(b[0]) + float(b[2]) / 2.0, float(b[1]) + float(b[3]) / 2.0)
                       for b in claimed if isinstance(b, (list, tuple)) and len(b) == 4]
    best, best_distance = None, tolerance
    for element in elements:
        index = int(element.get("index", -1))
        if str(index) in {str(x) for x in used} or not _pressable(elements, index):
            continue
        if plain(element_label(element)):
            continue
        other = element.get("box")
        if not isinstance(other, (list, tuple)) or len(other) != 4:
            continue
        ox = float(other[0]) + float(other[2]) / 2.0
        oy = float(other[1]) + float(other[3]) / 2.0
        distance = max(abs(ox - cx), abs(oy - cy))
        if any(max(abs(ox - qx), abs(oy - qy)) <= distance for qx, qy in claimed_centres):
            continue
        if distance < best_distance:
            best, best_distance = index, distance
    return best


_OPENS_ON_HOVER = ("caret", "menu-icon", "arrow", "expander", "has-submenu", "submenu")


def _opens_on_hover(elements, index: int) -> bool:
    """Whether pressing this element only opens a submenu, so it must be HOVERED.

    Measured 2026-11-16 on click-menu: pressing the item "Milissent" ended the episode with
    `done` true and the trail unpressed -- the item is a submenu header, and clicking it closes
    the menu. Hovering it opened the next level. The evidence is on the page: the header carries
    a caret/arrow icon that a leaf item does not.
    """
    # An element's `index` field is its identity; a list position is not (observations are
    # dense, but nothing here may depend on that).
    by_index = {int(element.get("index", position)): element
                for position, element in enumerate(elements)}

    def subtree(root: int):
        stack, seen = [root], set()
        while stack and len(seen) < 400:
            current = stack.pop()
            if current in seen or current not in by_index:
                continue
            seen.add(current)
            yield by_index[current]
            stack.extend(key for key, element in by_index.items()
                         if int(element.get("parent", -1)) == current)

    element = next((e for e in elements if int(e.get("index", -1)) == index), None)
    if element is None:
        return False
    start = int(element.get("index", index))
    parent = int(element.get("parent", -1))
    for root in (start, parent):
        if root not in by_index:
            continue
        for element in subtree(root):
            haystack = " ".join(str(element.get(key) or "")
                                for key in ("classes", "id", "text", "aria-label", "title"))
            if any(word in haystack.lower() for word in _OPENS_ON_HOVER):
                return True
    return False


def _label_served(clause, elements, index: int, positions, pressed=()) -> str | None:
    """Which label a press on `index` served, when the element no longer shows one.

    The inverse of `_nearest_box`: if a press can be decided by geometry because the page hides
    its labels, then the ledger must also be written by geometry, or the same target is served
    twice and the next one can never be found (measured 2026-11-16 on ascending-numbers).
    """
    if clause.get("operator") != "PRESS_SEQUENCE_BY_INDEX":
        return None
    shown = plain(element_label(elements[index])) if index < len(elements) else ""
    done = {plain(str(label)) for label in pressed}
    if shown and shown in {plain(str(l)) for l in clause.get("labels") or []}:
        return shown
    box = elements[index].get("box") if index < len(elements) else None
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        return None
    cx, cy = float(box[0]) + float(box[2]) / 2.0, float(box[1]) + float(box[3]) / 2.0
    best, best_distance = None, 14.0
    for label in clause.get("labels") or []:
        label = plain(str(label))
        if label in done:
            continue
        other = (positions or {}).get(label)
        if not isinstance(other, (list, tuple)) or len(other) != 4:
            continue
        distance = max(abs(float(other[0]) + float(other[2]) / 2.0 - cx),
                       abs(float(other[1]) + float(other[3]) / 2.0 - cy))
        if distance < best_distance:
            best, best_distance = label, distance
    return best


def _container_of(elements, index: int) -> int | None:
    """The nearest ancestor that has a box of its own."""
    parent = int(elements[index].get("parent", -1)) if index < len(elements) else -1
    depth = 0
    while 0 <= parent < len(elements) and depth < 4:
        box = elements[parent].get("box")
        if isinstance(box, (list, tuple)) and len(box) == 4:
            return parent
        parent = int(elements[parent].get("parent", -1))
        depth += 1
    return None


def _slider_track(elements, index: int) -> int | None:
    """The element whose drag actually moves a slider.

    The bridge drags FROM the element's centre, so grabbing the HANDLE moves the handle to where
    it already was. What moves a slider is the handle inside its track -- the handle is also the
    one element that gives a fine response (one nudge = a few units), while grabbing the track
    jumps the value by however far the press landed. The handle is a pressable element strictly
    inside a container that carries the slider's own class.
    """
    box = elements[index].get("box") if index < len(elements) else None
    for element in elements:
        if not element.get("can_click") or int(element["index"]) == index:
            continue
        classes = str(element.get("classes") or "")
        if "handle" not in classes:
            continue
        return int(element["index"])
    return int(index) if isinstance(box, (list, tuple)) else None


def _spinner_arrows(elements, index: int) -> tuple[int, int] | None:
    """The (up, down) controls a spinner draws beside its input, if it draws them."""
    parent = int(elements[index].get("parent", -2)) if index < len(elements) else -2
    beside = [element for element in elements
              if int(element.get("parent", -3)) == parent
              and int(element.get("index", -1)) != index
              and element.get("can_click")]
    if len(beside) < 2:
        return None
    beside.sort(key=lambda element: int(element.get("index", 0)))
    return int(beside[0]["index"]), int(beside[-1]["index"])


def _control_values(elements) -> list[tuple[int, float]]:
    """(element, the number it shows) for every settable control.

    A jQuery slider has no input: the handle is a pressable div and the value is DISPLAYED in a
    sibling. Both forms are collected, value first so a real input wins.
    """
    out: list[tuple[int, float]] = []
    for element in elements:
        if not (element.get("can_type") or element.get("can_click")):
            continue
        for field in ("value", "text"):
            found = re.findall(r"-?\d+(?:\.\d+)?", str(element.get(field) or ""))
            if found:
                out.append((int(element["index"]), float(found[0])))
                break
    return out


def action_for_clause(clause: Mapping[str, Any], observation: Mapping[str, Any],
                      already: Sequence[str] = (),
                      pressed: Sequence[str] = (),
                      positions: Mapping[str, Any] | None = None) -> str | None:
    """`already` is the indices already acted on (containers opened, elements pressed);
    `pressed` is the LABELS already pressed. The two are different ledgers on purpose."""
    """One action that moves the page towards this clause, or None if it cannot be taken yet.

    Nothing here inspects a reward. The only inputs are the clause (which came from the
    instruction) and the observation.
    """
    elements = observation.get("elements") or []
    operator = clause.get("operator")

    if operator in ("TYPE_VALUE",):
        target = clause.get("index")
        field = _field_for(elements, int(target)) if target is not None else None
        if field is None:
            fields = [int(e["index"]) for e in elements if e.get("can_type")]
            field = fields[0] if fields else None
        if field is None:
            return None
        if plain(elements[field].get("value")) == plain(clause.get("value")):
            return None                       # already done; the caller drops the clause
        return f"type@{field}={clause.get('value')}"

    if operator == "TYPE_MATCHING":
        index = int(clause["index"])
        current = plain(elements[index].get("value")) if index < len(elements) else ""
        tests, parts = clause.get("tests") or [], clause.get("parts") or []
        ok = current and all(
            (current.startswith(plain(p)) if t == "startswith" else
             current.endswith(plain(p)) if t == "endswith" else plain(p) in current)
            for t, p in zip(tests, parts))
        if ok:
            return None
        # the literal the instruction quoted is the best permitted candidate; typing the first
        # quoted piece and then letting the page suggest is not available without the page's
        # suggestion list, so the arm types the pieces joined -- and FAILS loudly if that is wrong
        return f"type@{index}={''.join(parts)}"

    if operator == "SELECT_SET":
        # a name is selected by pressing the thing that carries the state for it
        for name in clause.get("names") or []:
            if plain(name) in {plain(x) for x in pressed}:
                continue
            index = _first_matching(elements, [name])
            if index is None:
                continue
            states = contract_lib._choosable(elements, index)
            carrier = next((i for i in states if elements[i].get("checked") is not None), index)
            if elements[carrier].get("checked") or elements[carrier].get("selected"):
                continue
            return f"click@{carrier}"
        return None

    if operator == "SET_CONTROL":
        values = clause.get("values") or []
        if not values:
            return None
        pairs = _control_values(elements)
        if not pairs:
            return None
        for (index, current), wanted in zip(pairs, values):
            if abs(current - wanted) < 1e-6:
                continue
            # A jQuery spinner is an input plus UP/DOWN arrows, and its keydown handler calls
            # preventDefault -- typing changes nothing (measured 2026-11-16: type@5=7 left the
            # value at 0 and the page rejected the answer). The arrows ARE the control.
            arrows = _spinner_arrows(elements, index)
            if arrows:
                return f"click@{arrows[0] if wanted > current else arrows[1]}"
            if elements[index].get("can_type"):
                return f"type@{index}={int(wanted)}"
            # The bridge's nudge drags FROM the element's centre. On a slider handle that is a
            # no-op (you grabbed the handle and put it back); the element that moves is the
            # TRACK, which is the pressable element that carries the value. Measured 2026-11-16:
            # nudge@5=right left the value at 107 and the page rejected the answer.
            track = _slider_track(elements, index)
            if _horizontal(elements, index, track):
                word = "right" if wanted > current else "left"
            else:
                # a vertical slider counts the other way: dragging the handle DOWN raises the
                # value. Measured 2026-11-16: "down" took 107 to 104, i.e. the inverse.
                word = "up" if wanted > current else "down"   # measured: up raised 107 -> 110
            return f"nudge@{track if track is not None else index}={word}"
        return None

    if operator == "FOCUS":
        for index in clause.get("indices") or []:
            index = int(index)
            if index < len(elements) and elements[index].get("focused"):
                return None
            if _pressable(elements, index):
                return f"click@{index}"
        return None

    if operator == "PRESS_CLASS":
        # The name may be a class OR the element's id: measured 2026-11-16, `send-forward` is an
        # id, so a classes-only lookup found nothing and the filled-in form was never sent.
        token = str(clause.get("token") or "").lower()
        for element in elements:
            names = {str(t).lower() for t in str(element.get("classes") or "").split()}
            names.add(str(element.get("id") or "").lower())
            if token in names and element.get("can_click"):
                return f"click@{int(element['index'])}"
        return None

    if operator == "OPEN_THEN_CLICK":
        # The record's own frame is what opens it -- the thread responds to a click anywhere in it,
        # and the frame is the largest thing that is entirely this record. Then the control the
        # instruction asked for is looked for INSIDE the opened record.
        frame = anchored.find_frame(str(clause.get("identifier") or ""), observation,
                                    controls=[str(w) for w in clause.get("wanted") or []])
        if frame.outcome != anchored.RESOLVED:
            return None
        hits = [c for c in frame.controls if c["can_click"] and c["index"] != frame.container]
        # A WRAPPER IS NOT A CONTROL. Measured 2026-11-16: inside the opened email the word
        # `reply` matched `#reply` (the whole reply screen, index 0) before it matched anything a
        # person would press, so the arm "pressed reply" by clicking the page container.
        hits = sorted(hits, key=lambda c: (len(str(c["carried"])), c["index"]))
        named = [c for c in hits if c["word"] in str(clause.get("provenance") or "").lower()]
        hits = named or hits
        if hits:
            return f"click@{hits[0]['index']}"
        if frame.container is not None and frame.container not in [
                int(i) for i in already if str(i).isdigit()]:
            return f"click@{frame.container}"
        return None

    if operator == "CLICK_IN_FRAME" and clause.get("opens") is not None and clause.get("wants_text"):
        # The control is inside a record that is not open yet. Opening it is not a different
        # language: the frame that names the record names what opens it.
        frame = anchored.find_frame(str(clause.get("identifier") or ""), observation,
                                    controls=[str(clause.get("control") or "")])
        if frame.outcome != anchored.RESOLVED:
            return None
        openable = [c for c in frame.controls if c["can_click"]
                    and c["word"] == str(clause.get("control") or "")]
        if openable and openable[0]["index"] not in [int(i) for i in already if str(i).isdigit()]:
            return f"click@{openable[0]['index']}"
        return None

    if operator == "CLICK_IN_FRAME":
        # Re-resolve the frame on the LIVE page. An index captured at compile time is not an
        # action: the page renumbers between observations, and the whole point of the frame is
        # that it names the record again rather than trusting a number.
        frame = anchored.find_frame(str(clause.get("identifier") or ""), observation,
                                    controls=[str(clause.get("control") or "")])
        if frame.outcome != anchored.RESOLVED:
            return None
        for control in frame.controls:
            if control["can_click"] and control["word"] == str(clause.get("control") or ""):
                return f"click@{control['index']}"
        return None

    if operator == "CLICK_NAMED":
        index = _first_matching(elements, [clause.get("name") or ""],
                                also=("aria-label", "title", "value"))
        if index is None:
            return None
        return f"click@{index}"

    if operator == "CLICK_LABELLED":
        # A clause from the DESCRIPTOR path names one index and no labels: its subject was resolved
        # from an observable attribute ("the black box"), so the press is at that element -- and it
        # is re-resolved on the LIVE page by the same descriptor, because an index captured at
        # compile time is not an action (measured: these pages renumber between observations).
        if "labels" not in clause and clause.get("index") is not None:
            if _pressable(elements, int(clause["index"])):
                return f"click@{int(clause['index'])}"
            again = contract_lib.descriptor.describe(str(clause.get("provenance") or ""), observation)
            if again.outcome in (contract_lib.descriptor.RESOLVED,) and again.subject is not None:
                return f"click@{again.subject}"
            return None
        index = _first_matching(elements, clause.get("labels") or [],
                                also=tuple(clause.get("also_match") or ()))
        if index is None:
            return None
        return f"click@{index}"

    if operator == "DRAG_DESCRIBED":
        # grab each named thing, then drop it inside the target -- computed from the boxes present
        # NOW, never from an index captured earlier.
        target = int(clause.get("target") or -1)
        elements_by_index = {int(e["index"]): e for e in elements}
        if target not in elements_by_index:
            return None
        target_box = elements_by_index[target].get("box")
        members = [int(m) for m in clause.get("members") or []]
        for member in members:
            element = elements_by_index.get(member)
            if element is None:
                continue
            if _holding(observation):
                return f"drop@{target}"
            if isinstance(target_box, (list, tuple)) and len(target_box) == 4 \
                    and _inside(element, target_box):
                continue                      # this one already arrived
            return f"grab@{member}"
        return None

    if operator == "MOVE_DIRECTION":
        members = [int(m) for m in clause.get("members") or []]
        direction = str(clause.get("direction") or "")
        for member in members:
            if not _pressable(elements, member):
                return None
            if _holding(observation):
                return f"drop@{_one_step_along(elements, member, direction)}"
            return f"grab@{member}"
        return None

    if operator == "PRESS_SEQUENCE":
        for label in clause.get("labels") or []:
            if plain(label) in {plain(x) for x in pressed}:
                continue
            index = _first_matching(elements, [label])
            if index is None:
                continue
            # A trail item that carries a submenu caret is opened by HOVER; pressing it ends the
            # episode (measured 2026-11-16 on click-menu).
            verb = "hover" if _opens_on_hover(elements, index) else "click"
            return f"{verb}@{index}"
        return None

    if operator == "CLICK_ORDINAL":
        kind, n = clause.get("kind"), int(clause.get("ordinal") or 0)
        same = [e for e in elements if contract_lib._kind_of(e) == kind
                and (e.get("can_click") or e.get("can_type"))]
        if 0 < n <= len(same):
            return f"click@{int(same[n - 1]['index'])}"
        return None

    if operator == "ORDINAL_PRESS":
        n = int(clause.get("ordinal") or 0)
        groups: dict[str, list[int]] = {}
        for element in elements:
            if element.get("can_click") or element.get("can_type"):
                groups.setdefault(str(element.get("tag")), []).append(int(element["index"]))
        for tag, indices in groups.items():
            if len(indices) >= n and tag != "button":
                return f"click@{indices[n - 1]}"
        return None

    if operator == "ORDER":
        # the numbers shown on the pressable things, in the direction the instruction asked for
        shown: list[tuple[float, int]] = []
        for element in elements:
            if not (element.get("can_click") or element.get("can_type")):
                continue
            found = re.findall(r"-?\d+", str(element_label(element)))
            if found:
                shown.append((float(found[0]), int(element["index"])))
        if not shown:
            return None
        shown.sort(reverse=str(clause.get("direction")) == "descending")
        for _value, index in shown:
            if index not in already:
                return f"click@{index}"
        return None

    if operator == "EXPAND":
        for index in clause.get("indices") or []:
            if int(index) not in {int(x) for x in already}:
                return f"click@{int(index)}"
        return None     # nothing left to open; the clause is finished

    if operator == "READ_PAIR":
        index = int(clause["index"])
        partner = contract_lib._table_neighbour(elements, clause["label"])
        if partner is None:
            return None
        answer = element_label(elements[partner])
        if plain(elements[index].get("value")) == plain(answer):
            return None
        return f"type@{index}={answer}"

    if operator == "RANK_PICK":
        return f"click@{int(clause['index'])}"

    if operator == "PRESS_SEQUENCE_BY_INDEX":
        """Resolve each label on the LIVE page, in the stated order.

        Measured 2026-11-16 on ascending-numbers: the page rewrites itself on the first press
        (numbers become an overlay of rects), so indices captured at opening named different
        elements by the second step and the run scored 0.2. A label re-resolved each step is the
        only form of an action that survives a page rewriting itself.
        """
        labels = [plain(str(label)) for label in clause.get("labels") or []]
        # the ledger for a LABEL-keyed clause is the labels pressed, not the indices
        done = [plain(str(label)) for label in pressed]
        for position, label in enumerate(labels):
            if label in done:
                continue
            index = _first_matching(elements, [label], prefer_kind=clause.get("kind"))
            if index is not None:
                verb = "hover" if _opens_on_hover(elements, index) else "click"
                return f"{verb}@{index}"
            # Never fall back to a bare index: only to an index that still SHOWS the label it was
            # chosen for. A stale index silently names whatever is there now.
            for candidate in clause.get("indices") or []:
                if not _pressable(elements, int(candidate)):
                    continue
                if plain(element_label(elements[int(candidate)])) == label:
                    return f"click@{int(candidate)}"
            # A label that VANISHED is still the same element when it is still in the same
            # place. Measured 2026-11-16 on ascending-numbers: pressing "1" replaces every
            # remaining number with a blank rect at that number's own coordinates, so after the
            # first press no label exists anywhere on the page and text can never resolve again.
            # Geometry is the only identity that survives a page rewriting its own text.
            box = (positions or {}).get(label)
            # Ownership is positional only. The page RENUMBERS its elements between two
            # observations (measured: the pressed rect disappears and every later index shifts),
            # so an index ledger cannot say which target was already served.
            index = _nearest_box(elements, box,
                                 claimed=[(positions or {}).get(other) for other in done])
            if index is not None:
                verb = "hover" if _opens_on_hover(elements, index) else "click"
                return f"{verb}@{index}"
            return None
        return None

    if operator == "LABEL_ON_TRACE":
        # If the thing the instruction said to FIND is visible now, press it. Only when it is not
        # visible is opening a container the right move.
        index = _first_matching(elements, [clause.get("label") or ""],
                                also=("aria-label", "title", "classes", "id", "alt"))
        if index is not None and plain(str(clause.get("label") or "")) not in {
                plain(x) for x in pressed}:
            return f"click@{index}"
        return _reveal(clause, observation, already)

    return None


def _reveal(clause: Mapping[str, Any], observation: Mapping[str, Any],
            already: Sequence[str]) -> str | None:
    """The instruction said the control must be FOUND: open things until it appears.

    The choice of what to open is fixed by the page's structure (a collapsed header, a tab, a
    tree row) and the count is capped before the episode begins, so this is not a search against a
    signal. If the label never appears the arm stops and says so.
    """
    if len(already) >= _REVEAL_BUDGET:
        return None
    elements = observation.get("elements") or []
    for element in elements:
        if not element.get("can_click"):
            continue
        classes = str(element.get("classes") or "")
        tag = str(element.get("tag") or "")
        if ("collapsed" in classes or "ui-accordion-header" in classes or tag == "h3"
                or tag == "summary"):
            index = int(element["index"])
            if index not in already:
                return f"click@{index}"
    return None


def satisfied_by_construction(clause: Mapping[str, Any], observation: Mapping[str, Any]) -> bool:
    """Whether this clause is already true on the page as it stands (nothing left to do)."""
    return action_for_clause(clause, observation) is None and bool(
        contract_lib.check_contract(
            {"clauses": [clause]}, [(observation, "")])["verdict"] == contract_lib.PASS)


# --------------------------------------------------------------------------- #
# the arm
# --------------------------------------------------------------------------- #
class ContractArm:
    """Act from the instruction alone. No memory, no search, no reward, no parameters.

    Implements the arm interface the tree's measurement harness already uses:
    `begin(observation, seed)`, `next_action(observation) -> str | None`, and a `refused` flag.
    """

    name = "contract_only"
    searched = 0                        # never spends actions looking for a target

    def __init__(self) -> None:
        self.contract: dict[str, Any] = {}
        self._clauses: list[dict[str, Any]] = []
        self._done: list[str] = []      # clauses already satisfied
        self._reveal: list[str] = []
        self._asked = 0
        self._partial = False
        self._blocked: list[str] = []   # (operator, action) pairs that changed nothing
        self._done_ops: dict[int, list[str]] = {}   # clauses finished by their own action
        self._pressed_labels: list[str] = []        # labels actually pressed, for LABEL_ON_TRACE
        self._pressed_indices: list[str] = []       # indices already acted on
        self._last_page = ""
        self._stuck = 0
        self._seen: list[tuple[str, str]] = []   # (page fingerprint, action) already emitted
        self._last_page = ""
        self._stuck = 0

    def begin(self, observation: Mapping[str, Any], seed: int) -> None:
        self._utterance = str(observation.get("utterance") or "")
        self.contract = contract_lib.compile_contract(self._utterance, observation)
        # The sentence asks for something to be typed but no field on THIS page can hold it. That is
        # not a reason to drop it; it is a reason to look again once the page has changed.
        self._wants_text = bool(self.contract.get("wants_text"))
        self._clauses = order_for_execution(self.contract.get("clauses") or [])
        # ACT only on an instruction that was fully understood. A contract may honestly verify
        # HALF an instruction ("...then press submit") but executing that half is how a wrong
        # answer gets submitted: circle-center's decidable half is literally "press submit".
        # Measuring a partial contract is legitimate; acting on one is not.
        if self.contract.get("refused_part"):
            self._clauses = []
        self._done, self._reveal, self._asked = [], [], 0
        self._done_ops, self._blocked, self._seen, self._stuck = {}, [], [], 0
        self._pressed_labels, self._pressed_indices = [], []
        self._positions = {}          # label -> box, remembered while the label is visible
        self._last_page = ""
        self.refused = (bool(self.contract.get("refusal")) or not self._clauses
                        or bool(self.contract.get("refused_part")))

    def _remember_positions(self, clause, observation) -> None:
        """Capture where each label lives while the page still shows it."""
        elements = list(observation.get("elements") or [])
        for label in clause.get("labels") or []:
            label = plain(str(label))
            if label in self._positions:
                continue
            index = _first_matching(elements, [label], prefer_kind=clause.get("kind"))
            if index is None:
                continue
            box = elements[index].get("box")
            if isinstance(box, (list, tuple)) and len(box) == 4:
                self._positions[label] = list(box)

    def _read_again(self, observation: Mapping[str, Any]) -> None:
        """Read the SAME sentence against THIS page and add whatever half it can now act on.

        A sentence can ask for two things that become possible at different times -- the record to
        press and the field to write in. Compiling once at time zero silently dropped the second.
        Each look asks the words again; a clause already held is not added twice, so the cost is
        one comparison and no action.
        """
        late = contract_lib.compile_contract(self._utterance, observation)
        found = [c for c in late.get("clauses") or [] if c.get("operator") in _LATE_OPERATORS]
        # The form compiler is a DIFFERENT reading of the same words, not a fallback for an empty
        # one: on the inbox the late compile returns the record clause AND the form's send control
        # is only ever found by asking the form reader. Asking only when the first came back empty
        # meant the reply was typed and never sent -- the exact failure the clause exists to fix.
        form = contract_lib._form_action(self._utterance, observation)
        if form:
            found = list(form["clause"]) + found
        # A clause already held and already applied does not block; one merely held does not block
        # either -- it is about to be acted on. Only what is DONE stops a repeat.
        done = {(c.get("operator"), c.get("index"), c.get("value"), c.get("token"))
                for c in self._clauses
                if c.get("operator") not in _WRITES or _applied(c, observation)}
        new = [c for c in found
               if (c.get("operator"), c.get("index"), c.get("value"), c.get("token")) not in done]
        if new:
            self._clauses = order_for_execution(new) + list(self._clauses)

    def next_action(self, observation: Mapping[str, Any]) -> str | None:
        """The next action, or None when nothing left can change the page.

        A REPEATED no-op is the defect this guard removes. Measured 2026-11-16: 14 of 43 failures
        were the same action pressed twenty-five times, because a clause whose action changed
        nothing kept producing it. Repeating an action that left the observable page identical
        cannot succeed -- there is no state it could depend on -- so the pair (page, action) is
        refused for the rest of the episode and the next clause is tried. This reads no reward;
        it only compares the page with itself.
        """
        self._asked += 1
        fingerprint = _fingerprint(observation)
        # If the page did not change at all since the last look, the last action achieved nothing
        # observable. Two such in a row means this contract cannot be executed on this page: say
        # so and stop, instead of spending the whole budget re-taking an action that does nothing.
        self._last_page = fingerprint
        # a clause is finished when its action is no longer available AND the clause holds
        for clause in list(self._clauses):
            action = action_for_clause(clause, observation, self._reveal)
            finished_target = (clause.get("operator") == "LABEL_ON_TRACE"
                               and plain(str(clause.get("label") or ""))
                               in {plain(x) for x in self._pressed_labels})
            opened = (clause.get("operator") == "EXPAND"
                      and {str(index) for index in clause.get("indices") or []}
                      <= {str(index) for index in self._reveal})
            if clause.get("operator") == "OPEN_THEN_CLICK" and any(
                    e.get("can_type") for e in observation.get("elements") or []):
                # THE RECORD IS OPEN: a field exists that could not exist before it was.
                self._clauses.remove(clause)
                self._done.append("OPEN_THEN_CLICK")
                continue
            if opened or finished_target or id(clause) in self._done_ops or (
                    action is None and satisfied_by_construction(clause, observation)):
                self._clauses.remove(clause)
                self._done.append(str(clause.get("operator")))
        # A PLACE TO PUT THE TEXT MUST BE FOUND ON THE PAGE THAT HAS ONE. Measured 2026-11-16 on
        # `email-inbox-reply`: the text box does not exist until the email is opened, so compiling
        # the typed value at time zero found no field and dropped the sentence's text. What was
        # missing at time zero was not a word -- it was a page. So the SAME sentence is read again
        # against the page that now exists. Nothing is remembered and nothing is guessed; the
        # reading is repeated where it can be done. It happens AFTER the finished clauses are
        # removed: measured 2026-11-16, doing it before meant the control that SENDS the typed
        # text was never asked for, and the episode ended with the field filled and nothing
        # pressed.
        if self._wants_text:
            self._read_again(observation)

        for clause in self._clauses:
            self._remember_positions(clause, observation)
            action = action_for_clause(clause, observation, self._pressed_indices,
                                       self._pressed_labels, self._positions)
            # A SET_CONTROL legitimately repeats one arrow: the page DOES change each press, and
            # the value is the evidence. Only an action that changed nothing is blocked.
            repeatable = clause.get("operator") in _REPEATABLE
            if action is None or ((fingerprint, action) in self._seen and not repeatable):
                # A press already tried on this very page cannot help again. What can help is a
                # DIFFERENT press that reveals the thing the instruction says to find, so fall
                # through to the reveal clause instead of re-opening what is already open.
                reveal = next((other for other in self._clauses
                               if other.get("operator") == "LABEL_ON_TRACE"), None)
                if reveal is None or action is None:
                    continue
                action = _reveal(reveal, observation, self._reveal)
                if action is None or (fingerprint, action) in self._seen:
                    continue
            if (fingerprint, action) in self._seen:
                self._blocked.append(f"{clause.get('operator')}::{action}")
                continue
            self._seen.append((fingerprint, action))
            if action.startswith("click@") or action.startswith("hover@"):
                index = action.split("@")[1]
                label = _label_at(observation, int(index))
                if not label:
                    label = _label_served(clause, list(observation.get("elements") or []),
                                          int(index), self._positions, self._pressed_labels)
                if label and label not in self._pressed_labels:
                    self._pressed_labels.append(label)
                if index not in self._pressed_indices:
                    self._pressed_indices.append(index)
                if index not in self._reveal:
                    self._reveal.append(index)
                if clause.get("operator") == "OPEN_THEN_CLICK":
                    # Opening the record is the FIRST half of this clause, not the whole of it.
                    # Marking it done here is how the email got opened and then abandoned.
                    pass
                elif clause.get("operator") not in _REPEATABLE:
                    self._done_ops[id(clause)] = [str(clause.get("operator"))]
            return action
        self.refused = bool(self._clauses) or bool(self.contract.get("refused_part"))
        return None

    def blocked(self) -> list[str]:
        return list(self._blocked)

    def remaining(self) -> list[str]:
        return [str(clause.get("operator")) for clause in self._clauses]


def order_for_execution(clauses: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """The clauses in the order they must happen: state first, the terminal press last.

    A contract is a conjunction, so its clauses have no order in logic -- but an episode does.
    Emission order is the order the words appeared, which is not the order actions must happen in
    ("... then press submit"). Sorting is stable, so within each group the instruction's own order
    is kept exactly.
    """
    def terminal(clause: Mapping[str, Any]) -> int:
        if clause.get("operator") != "CLICK_NAMED":
            return 0
        name = plain(str(clause.get("name") or ""))
        return 1 if name in _TERMINAL else 0

    return [dict(clause) for clause in sorted(clauses, key=terminal)]


def _label_at(observation: Mapping[str, Any], index: int) -> str:
    elements = observation.get("elements") or []
    if 0 <= index < len(elements):
        return plain(element_label(elements[index]))
    return ""


def _applied(clause: Mapping[str, Any], observation: Mapping[str, Any]) -> bool:
    """Whether a writing clause has already happened on this page."""
    index = clause.get("index")
    if index is None:
        return False
    elements = observation.get("elements") or []
    if not (0 <= int(index) < len(elements)):
        return False
    value = clause.get("value")
    if value is None:
        return False
    return plain(elements[int(index)].get("value")) == plain(value)


def _fingerprint(observation: Mapping[str, Any]) -> str:
    """The page's observable state, hashed. Used only to notice that an action changed nothing."""
    import hashlib

    # GEOMETRY IS PART OF THE OBSERVABLE. Measured 2026-11-16 on ascending-numbers: a press turns
    # five labelled numbers into three blank rects and a fourth into an unlabelled one, while
    # text/tag/value are unchanged for the rest -- a text-only hash called that "the page did not
    # change" and the arm re-pressed the same element forever. Where a thing IS is observable.
    parts = []
    for element in observation.get("elements") or []:
        parts.append("|".join(str(element.get(key) or "") for key in
                              ("index", "tag", "text", "value", "checked", "selected", "focused",
                               "box", "classes")))
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def first_action(utterance: str, observation: Mapping[str, Any]) -> dict[str, Any]:
    """The very first action, and the contract it came from -- for measuring time zero directly."""
    arm = ContractArm()
    arm.begin(observation, 0)
    return {"action": arm.next_action(observation), "refused": arm.refused,
            "refusal": arm.contract.get("refusal"),
            "operators": [clause["operator"] for clause in arm.contract.get("clauses") or []]}


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="the instruction as a policy, offline")
    parser.add_argument("--utterance")
    parser.add_argument("--observation", help="path to a JSON observation")
    args = parser.parse_args(argv)
    if not (args.utterance and args.observation):
        parser.error("--utterance and --observation are required")
    observation = json.loads(pathlib.Path(args.observation).read_text())
    print(json.dumps(first_action(args.utterance, observation), indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
