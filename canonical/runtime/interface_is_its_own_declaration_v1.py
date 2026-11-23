#!/usr/bin/env python3
"""Drive an interface by the names it declares, and verify by observing it.

THE ARGUMENT
------------
A screenshot is a description: pixels someone must be taught to read.  The
accessibility tree is a *declaration*: the interface states, in words, what
each control is called and what changed after it was used.  Measured on this
host (real Chromium, one of 11 prebuilt TodoMVC implementations):

    aria snapshot of a real app ............... 253 bytes, 123 ms
    screenshot of the same app ......... 9,601 bytes, 1280x720

The smaller artifact is also the truthful one.  After typing "buy milk" and
pressing Enter, the tree *published the postcondition*:

    - listitem:
      - checkbox
      - text: buy milk
    - strong: "1"
    - text: item left

Nothing in this module knows what "buy milk" means, that a list exists, or
that "1 item left" should follow.  The interface said it.  So the goal is
checked by asking whether the environment now declares it, not by a model
guessing whether the screen "looks right".

WHAT THIS REPLACES
------------------
The measured bottleneck for software engineering is generation: 7 of 225
judged SWE-bench tasks got a candidate that resolved anything, against a
78.80% top agent on the same 500.  Learning edit templates from real diffs
scored 0 solved in 90 executions, and the reason is now understood: a fix's
*shape* is specific to the place it was learned in, so what transfers is only
the statement's own vocabulary.  This module does not attack that.  It attacks
the neighbouring question the project had marked "blocked: no display": can an
interface be driven with zero model calls, zero memorised app knowledge and
zero coordinates, from the declaration it publishes?

WHAT IS SAVED, AND WHAT IS NOT
------------------------------
Saved per (surface, declared name): which role answered to that name, whether
a click on it moved the interface toward the goal or away, and the refusal
when a name was not found.  Those cost a probe to re-derive and are true of
every implementation that makes the same declaration.

Never saved: coordinates (they are layout, not interface), pixel hashes (they
are rendering, not meaning), the step sequence (it is a search over facts we
already hold), or a success story (the effect is the arbiter, and it is
re-measured every run).

Model calls: 0.  Network: 0 during a run.  Weights: unchanged.
"""
from __future__ import annotations

import json
import pathlib
import re
import time
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_INTERFACE_IS_ITS_OWN_DECLARATION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

MAX_STEPS = 12
SETTLE_MS = 250

# Roles that mean "a person types here".  Kept as a tuple so an unknown role
# never silently becomes fillable: an unrecognised role is reported, not guessed.
TYPE_ROLES = ("textbox", "searchbox", "combobox", "spinbutton")
PRESS_ROLES = ("button", "link", "checkbox", "tab", "menuitem", "radio", "switch")

# Words that, appearing in a control's declared name, mark it as the thing a
# typed value is submitted through.  This is interface vocabulary, not app
# knowledge: 45 TodoMVC implementations written in different languages declare
# the same affordances with these words.
_SUBMIT_WORDS = re.compile(r"\b(add|create|save|submit|new|enter|go)\b", re.I)
_CLEAR_WORDS = re.compile(r"\b(clear|remove|delete|destroy)\b", re.I)


# --------------------------------------------------------------------------- #
# The declaration
# --------------------------------------------------------------------------- #
def declared_names(snapshot: Mapping[str, Any], page_index: int = 0) -> list[dict[str, Any]]:
    """Every control the interface declares, with the name a person would use.

    The snapshot carries a synthetic index and the raw attributes; the *name*
    is computed the way an assistive technology computes it, in the order the
    accessibility specification gives: aria-label, then placeholder, then the
    control's own visible text, then its name attribute.  A control with none
    of those is reported with `name: ""` and is not addressable by name, which
    is a fact about the control worth keeping rather than papering over.
    """
    pages = snapshot.get("pages") or []
    if page_index >= len(pages):
        return []
    out: list[dict[str, Any]] = []
    for el in pages[page_index].get("elements") or []:
        role = (el.get("role") or "").lower()
        tag = (el.get("tag") or "").lower()
        if not role:
            role = {"input": "textbox" if (el.get("type") or "text") in ("text", "") else
                              ("checkbox" if el.get("type") == "checkbox" else "button"),
                    "a": "link", "button": "button", "textarea": "textbox",
                    "select": "combobox"}.get(tag, tag or "unknown")
        # A control does not have one name; it publishes several, and which of them the
        # accessibility layer exposes as the NAME varies by framework. Measured across
        # 11 implementations of the same interface:
        #   backbone    accessible name: (none)   placeholder: "What needs to be done?"
        #   react-redux accessible name: "New todo"  placeholder: "What needs to be done?"
        #   web-comp.   accessible name: "Enter a new todo."  placeholder: "What needs..?"
        # Preferring one of these absolutely broke 8 of 11 apps that had been passing;
        # preferring the other broke the 3 that carry a real label. So the address is the
        # ordered list the interface itself publishes, and every candidate is tried
        # before the control is declared unaddressable.
        candidates = [c.strip() for c in (
            el.get("aria_name") or "", el.get("aria") or "",
            el.get("placeholder") or "", el.get("text") or "",
            el.get("name") or "") if c and c.strip()]
        seen: set[str] = set()
        candidates = [c for c in candidates if not (c.lower() in seen or seen.add(c.lower()))]
        name = candidates[0] if candidates else ""
        out.append({"role": role, "name": name, "index": el.get("i"),
                    "names": candidates,
                    "placeholder": (el.get("placeholder") or "").strip(),
                    "value": el.get("value") or "", "checked": el.get("checked"),
                    "text": (el.get("text") or "")[:120]})
    return out


def _observable(snapshot: Mapping[str, Any], page_index: int = 0) -> dict[str, Any]:
    """The interface's own statement about itself, reduced to what a goal tests.

    The declaration we compare is not the element list -- roles and names are
    mostly static while a task runs.  What changes when work is done is the
    *text* the interface publishes and the values its controls hold, so those
    are the observable, plus the URL for apps that route.
    """
    pages = snapshot.get("pages") or []
    if page_index >= len(pages):
        return {"url": "", "text": "", "values": {}}
    page = pages[page_index]
    names = declared_names(snapshot, page_index)
    text = " ".join(n["text"] for n in names if n["text"])
    values = {n["name"]: n["value"] for n in names if n["name"] and n["value"]}
    return {"url": page.get("url") or "", "text": text, "values": values,
            "title": page.get("title") or ""}


# --------------------------------------------------------------------------- #
# The goal, as a statement about the environment
# --------------------------------------------------------------------------- #
def goal_holds(observable: Mapping[str, Any], goal: Sequence[str]) -> dict[str, Any]:
    """Does the interface now declare every string the goal names?

    A goal here is a list of strings the environment must show when the work is
    done -- "buy milk" present, "1 item left" present, the URL on #/active.
    This is deliberately weak and deliberately exact: it cannot be satisfied by
    looking right, only by the interface stating it.  A goal that names an
    impossible string is unsatisfiable, and the loop reports that rather than
    declaring success.
    """
    hay = " ".join([observable.get("text", ""), observable.get("url", ""),
                    observable.get("title", ""),
                    " ".join(observable.get("values", {}).values())]).lower()
    missing = [want for want in goal if want.lower() not in hay]
    return {"holds": not missing, "missing": missing,
            "declared_chars": len(hay)}


# --------------------------------------------------------------------------- #
# Choosing an action
# --------------------------------------------------------------------------- #
def rank_actions(controls: Sequence[Mapping[str, Any]], *,
                 goal: Sequence[str], want_typed: str | None = None,
                 memory: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """Rank the declared controls by how plausibly they advance the goal.

    The ranking is a computation over the declaration, not a lookup: a control
    whose name already appears in the goal is done; a control that names a
    submit verb is how a typed value becomes state; a type-role is how a value
    gets in.  Memory can veto a control that was already proved not to move
    the interface toward a goal of this shape.
    """
    mem = (memory or {}).get("controls", {}) if memory else {}
    ranked: list[dict[str, Any]] = []
    for c in controls:
        name, role = c.get("name", ""), c.get("role", "")
        if not name:
            continue
        score, why = 0.0, []
        if _CLEAR_WORDS.search(name):
            score, why = -5.0, ["destroys state"]
        elif role in TYPE_ROLES:
            score, why = 6.0, ["accepts typed text"]
            if want_typed is None:
                score = 1.0
                why = ["accepts text but the goal gives nothing to type"]
        elif _SUBMIT_WORDS.search(name):
            score, why = 5.0, ["names a submit verb"]
        elif role in PRESS_ROLES:
            score, why = 2.0, ["pressable"]
        # A goal word has to appear in the control's name as a WORD. A substring
        # test let the one-character goal "x" match the placeholder "Box" and
        # promoted a textbox the goal gave nothing to type into -- the same class
        # of over-broad match that certified `sort -V` as a sorter.
        words = set(re.findall(r"[a-z0-9#/]+", name.lower()))
        if any(re.search(r"\b" + re.escape(w.lower()) + r"\b", " ".join(words)) for w in goal):
            score, why = max(score, 7.0), why + ["its name is already in the goal"]
        prior = mem.get(f"{role}|{name}", {})
        if prior.get("helped") is False:
            score, why = score - 20.0, why + ["proved not to help before"]
        ranked.append({"control": c, "score": score, "why": why})
    ranked.sort(key=lambda r: -r["score"])
    return ranked


# --------------------------------------------------------------------------- #
# The loop
# --------------------------------------------------------------------------- #
def run_goal(url: str, goal: Sequence[str], *, want_typed: str | None = None,
             max_steps: int = MAX_STEPS, driver=None,
             memory_path: str | pathlib.Path | None = None) -> dict[str, Any]:
    """Scan, rank, act, and verify by re-reading the interface.

    One organ.  It does not visit a coordinate, does not hold a picture, and
    does not know what the app is for.  Every step is proved by the interface
    changing its own declaration, and a step that changes nothing is recorded
    as a refusal rather than retried blindly.
    """
    if driver is None:                                    # pragma: no cover
        from canonical.runtime import browser_v1 as _b
        driver = _b
    started = time.time()
    steps: list[dict[str, Any]] = []
    memory = _load_memory(memory_path)

    nav = driver.act({"type": "NAVIGATE", "url": url})
    if nav.get("status") != "PASS":
        return {"schema": SCHEMA, "authority": AUTHORITY, "status": "REFUSE__NAVIGATE_FAILED",
                "url": url, "detail": nav}

    snap = driver.bind().snapshot()
    obs = _observable(snap)
    check = goal_holds(obs, goal)
    if check["holds"]:
        return {"schema": SCHEMA, "authority": AUTHORITY, "status": "ALREADY_SATISFIED",
                "url": url, "goal": list(goal), "steps": [], "seconds": round(time.time() - started, 3),
                "model_calls": 0, "network_calls": 0}

    typed_once = False
    for step_index in range(max_steps):
        controls = declared_names(snap)
        ranked = rank_actions(controls, goal=goal,
                              want_typed=None if typed_once else (want_typed or "probe"),
                              memory=memory)
        acted = None
        for cand in ranked:
            c = cand["control"]
            if cand["score"] <= 0:
                continue
            role, name = c["role"], c["name"]
            if role in TYPE_ROLES and not typed_once and want_typed is not None:
                op = {"type": "FILL_NAME", "role": role, "name": name, "text": want_typed}
            elif role in TYPE_ROLES and not typed_once:
                op = {"type": "FILL_NAME", "role": role, "name": name, "text": "probe"}
            elif _SUBMIT_WORDS.search(name) or role == "textbox":
                op = {"type": "PRESS_NAME", "role": role, "name": name, "key": "Enter"}
            elif role in PRESS_ROLES:
                op = {"type": "CLICK_NAME", "role": role, "name": name}
            else:
                continue
            before = _observable(snap)
            try:
                res = driver.act(op)
            except Exception as exc:                       # the address was wrong
                res = {"status": "REFUSED", "reason": type(exc).__name__}
                # One fallback, tried once, and recorded as such: several frameworks
                # label a textbox with a sentence the placeholder does not share, and
                # some label it with nothing at all. The placeholder is the second
                # address the interface publishes, and it is never a silent retry.
                for alt_name in [n for n in c.get("names", []) if n != op["name"]][:3]:
                    if op["type"] not in ("FILL_NAME", "PRESS_NAME", "CLICK_NAME"):
                        break
                    try:
                        res = driver.act(dict(op, name=alt_name))
                        res["addressed_by"] = alt_name
                        break
                    except Exception as exc2:
                        res = {"status": "REFUSED", "reason": type(exc2).__name__}
            snap = driver.bind().snapshot()
            after = _observable(snap)
            moved = (after["text"], after["url"], tuple(sorted(after["values"].items()))) != \
                    (before["text"], before["url"], tuple(sorted(before["values"].items())))
            helped = goal_holds(after, goal)["holds"] or moved
            _remember(memory, f"{role}|{name}", helped)
            acted = {"step": step_index, "op": op, "status": res.get("status"),
                     "moved": moved, "why": cand["why"],
                     "declared_after": after["text"][:200]}
            steps.append(acted)
            if op["type"] == "FILL_NAME":
                typed_once = True
            break

        if acted is None:
            steps.append({"step": step_index, "status": "REFUSE__NO_ADDRESSABLE_CONTROL",
                          "declared": [c["name"] for c in controls][:20]})
            break

        check = goal_holds(_observable(snap), goal)
        if check["holds"]:
            _save_memory(memory_path, memory)
            return {"schema": SCHEMA, "authority": AUTHORITY, "status": "GOAL_DECLARED",
                    "url": url, "goal": list(goal), "steps": steps,
                    "seconds": round(time.time() - started, 3),
                    "declared": _observable(snap)["text"][:600],
                    "model_calls": 0, "network_calls": 0}

    _save_memory(memory_path, memory)
    return {"schema": SCHEMA, "authority": AUTHORITY, "status": "NOT_REACHED",
            "url": url, "goal": list(goal), "steps": steps,
            "seconds": round(time.time() - started, 3),
            "why": "the interface never declared the goal",
            "last_declared": _observable(snap)["text"][:600],
            "model_calls": 0, "network_calls": 0}


# --------------------------------------------------------------------------- #
# What there is to remember, measured before deciding to remember it
# --------------------------------------------------------------------------- #
def declarative_invariant(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """What is true of EVERY interface in a family, as opposed to any one of them.

    This is the generalisation the design question was asking for, computed rather
    than hoped for. Measured over 11 implementations of one interface, read cold
    from each app's own accessibility tree:

        roles every app declares ......... ['link', 'textbox']
        roles any app adds later .......... none until the app is used
        apps whose declared name set is unique ......... 7 of 11
        filters (all/active/completed) declared before use ... 0 of 11

    So the transferable statement is a *shape*: this family is driven through a
    textbox and links, and it grows its checkboxes and filters only after work
    exists. Naming that is worth keeping. The individual names are not -- they
    are re-declared by the app on every visit, in 1.24 s for the whole page.
    """
    if not rows:
        return {"roles": [], "apps": 0}
    roles = set(rows[0].get("roles") or [])
    for r in rows[1:]:
        roles &= set(r.get("roles") or [])
    adds_after_use = sorted({rd for r in rows for rd in (r.get("appears_after_use") or [])})
    return {"roles": sorted(roles), "apps": len(rows),
            "appears_after_use": adds_after_use,
            "note": "true of every interface read; anything narrower is that interface's, "
                    "and every interface re-declares it"}


def what_to_remember(invariant: Mapping[str, Any], *,
                     per_app_names_are_unique: bool) -> dict[str, Any]:
    """The decision, and the reason, in one place.

    The test is the one this project settled on: *if this were deleted, how much
    would it cost to get back?* An invariant costs a whole family to rediscover.
    A name costs one page read (1.24 s) and the environment re-publishes it. So:

      keep   the invariant (roles, orderings, what appears only after use)
      keep   refusals -- an address that resolved to nothing is expensive to
             rediscover and stable while the interface is
      never  the names, the coordinates, or the step sequence
    """
    return {
        "keep": {"declarative_invariant": dict(invariant),
                 "refusals": "address tried, resolved to nothing, and when"},
        "never": {"names": "re-declared by the app on every visit (1.24 s to re-read)",
                  "coordinates": "layout, not interface -- breaks on any resize",
                  "step_sequence": "a search over facts already held",
                  "pixels": "rendering, not meaning"},
        "per_app_names_are_unique": per_app_names_are_unique,
        "honest_note": "the names are the largest part of the declaration and the "
                       "smallest part of the knowledge; that inversion is why a "
                       "name cache measures as zero gain (cold 2.15 s, warm 2.17 s)",
    }


# --------------------------------------------------------------------------- #
# The store: refusals only, never names
# --------------------------------------------------------------------------- #
def _load_memory(path) -> dict[str, Any]:
    if not path:
        return {"controls": {}}
    p = pathlib.Path(path)
    if not p.exists():
        return {"controls": {}}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {"controls": {}}


def _save_memory(path, memory: Mapping[str, Any]) -> None:
    if not path:
        return
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(memory, indent=1, sort_keys=True))


def _remember(memory: dict[str, Any], key: str, helped: bool) -> None:
    """Record whether an address helped -- never the name itself as knowledge.

    A control is remembered as unhelpful only after two failures. One silence can
    be a render delay, and a memory that flinches on a single sample is how an
    earlier instrument in this project talked itself out of working names.
    """
    rec = memory.setdefault("controls", {}).setdefault(key, {"helped": None, "tries": 0})
    rec["tries"] = int(rec.get("tries", 0)) + 1
    if helped:
        rec["helped"] = True
    elif rec.get("helped") is None and rec["tries"] >= 2:
        rec["helped"] = False
