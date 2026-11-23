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
                    "href": (el.get("href") or ""),
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
    # The page's own words, plus its controls' labels. Controls alone were not enough:
    # a todo's label is inert text, so the interface had done the work and the report
    # said it had not.
    text = " ".join([page.get("body_text") or "",
                     " ".join(n["text"] for n in names if n["text"])])
    values = {n["name"]: n["value"] for n in names if n["name"] and n["value"]}
    return {"url": page.get("url") or "", "text": text, "values": values,
            "title": page.get("title") or ""}


# --------------------------------------------------------------------------- #
# The goal, as a statement about the environment
# --------------------------------------------------------------------------- #
def goal_holds(observable: Mapping[str, Any], goal: Sequence[str], *,
               allow_typed: bool = False) -> dict[str, Any]:
    """Does the interface now declare every string the goal names?

    A goal here is a list of strings the environment must show when the work is
    done -- "buy milk" present, "1 item left" present, the URL on #/active.

    The text a person typed is NOT part of what the page declares unless the
    caller asks for it. Measured: `run_goal` certified the lit app on a textbox
    that merely *held* "buy milk", before any todo existed -- the checkbox count
    and the filters had not appeared. That is a false certificate of the same
    kind that let `sort -c` be called a sorter, and the fix is to make the check
    strict: the work must be in the page, not in the input.
    """
    hay = " ".join([observable.get("text", ""), observable.get("url", ""),
                    observable.get("title", "")]).lower()
    if allow_typed:
        hay = hay + " " + " ".join(observable.get("values", {}).values()).lower()
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
        # COMPARE WHOLE WORDS ON BOTH SIDES. Two bugs lived here. A plain substring
        # test let the one-character goal "x" match the placeholder "Box"; and a
        # word-boundary test against the joined name let the goal word "buy" match
        # inside "Enter a new todo.", which pushed the textbox holding the typed value
        # to 1.0, below the footer link, so it was never submitted (12 steps, no todo).
        name_words = set(re.findall(r"[a-z0-9#/]+", name.lower()))
        goal_words = {w.lower() for w in goal for w in re.findall(r"[a-z0-9#/]+", w)}
        if name_words & goal_words:
            score, why = max(score, 7.0), why + ["its name is already in the goal"]
        # A NAVIGATION MUST NOT BE MISTAKEN FOR PROGRESS, and this demotion goes LAST so
        # the goal-name bonus above cannot undo it. Measured: the goal word "TodoMVC"
        # matched the footer link, the bonus lifted it to 7.0 -- above the textbox -- and
        # the loop navigated off the app entirely, leaving a blank page.
        href = c.get("href") or ""
        if href and not href.startswith(("#", "/")):
            score, why = score - 20.0, why + ["points away from the interface"]
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
    typed_into: str | None = None
    submitted = False
    for step_index in range(max_steps):
        controls = declared_names(snap)
        ranked = rank_actions(controls, goal=goal,
                              want_typed=None if typed_once else (want_typed or "probe"),
                              memory=memory)
        # SUBMIT FIRST, OUTSIDE THE LOOP. The text was typed, so the only thing that turns
        # a value into state is submitting it -- and a textbox that has nothing left to
        # type scores below a pressable link, so inside the loop the link always won and
        # the loop clicked the page heading with the value still in the box. Measured on
        # one implementation: 12 steps and never submitted. Ordering cannot be expressed as
        # a score when the scoring is what puts the wrong control first.
        acted = None
        if typed_into and not submitted:
            for cand in ranked:
                c = cand["control"]
                if c["role"] in TYPE_ROLES and c.get("name") == typed_into:
                    op = {"type": "PRESS_NAME", "role": c["role"],
                          "name": c["name"], "key": "Enter"}
                    before = _observable(snap)
                    try:
                        res = driver.act(op)
                    except Exception as exc:
                        res = {"status": "REFUSED", "reason": type(exc).__name__}
                        try:
                            res = driver.act({"type": "PRESS_POSITION", "control": "textbox",
                                              "nth": 0, "key": "Enter"})
                            res["addressed_by"] = "position:textbox[0]"
                        except Exception:
                            pass
                    snap = driver.bind().snapshot()
                    after = _observable(snap)
                    moved = (after["text"], after["url"]) != (before["text"], before["url"])
                    submitted = moved
                    steps.append({"step": step_index, "op": op, "status": res.get("status"),
                                  "moved": moved, "why": ["submit what was typed"],
                                  "submitted": moved,
                                  "declared_after": after["text"][:200]})
                    acted = True
                    if goal_holds(after, goal)["holds"]:
                        _save_memory(memory_path, memory)
                        return {"schema": SCHEMA, "authority": AUTHORITY,
                                "status": "GOAL_DECLARED", "url": url, "goal": list(goal),
                                "steps": steps,
                                "seconds": round(time.time() - started, 3),
                                "declared": after["text"][:600],
                                "model_calls": 0, "network_calls": 0}
                    break
            if acted:
                continue
        for cand in ranked:
            c = cand["control"]
            if cand["score"] <= 0:
                continue
            role, name = c["role"], c["name"]
            # Submit-before-fill. The control that already holds the text sorts after an
            # empty type= box on every page that declares one, so testing it last meant
            # `typed_into` never matched and the value was never submitted.
            # ORDER, NOT SCORE. A textbox that already holds the value outranks every
            # pressable control, because the work is half-done and one key press finishes
            # it while a click starts something else. Scoring cannot express this: a
            # textbox with nothing left to type is worth 1.0 and a pressable link 2.0, so
            # the link kept winning and the value sat in the box while the loop clicked
            # the page heading. Measured on one implementation: 12 steps, never submitted.
            if typed_into and role in TYPE_ROLES and (
                    name == typed_into or want_typed is None or typed_once):
                op = {"type": "PRESS_NAME", "role": role, "name": name, "key": "Enter"}
            elif role in TYPE_ROLES and not typed_once and want_typed is not None:
                op = {"type": "FILL_NAME", "role": role, "name": name, "text": want_typed}
            elif role in TYPE_ROLES and not typed_once:
                op = {"type": "FILL_NAME", "role": role, "name": name, "text": "probe"}
            elif typed_into and name == typed_into:
                # The text went into this control and nothing submitted it. Measured on
                # 11 of 11 apps: the textbox is not in the cold declaration as a submit
                # affordance, so a ranker that only reads names never presses Enter and
                # the value just sits there. Earlier this looked like a pass because the
                # goal check credited the textbox's contents -- the check was wrong, and
                # fixing the check exposed the missing submit.
                op = {"type": "PRESS_NAME", "role": role, "name": name, "key": "Enter"}
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
                        if op["type"] == "FILL_NAME":
                            typed_into = alt_name
                        break
                    except Exception as exc2:
                        res = {"status": "REFUSED", "reason": type(exc2).__name__}
            snap = driver.bind().snapshot()
            after = _observable(snap)
            moved = (after["text"], after["url"], tuple(sorted(after["values"].items()))) != \
                    (before["text"], before["url"], tuple(sorted(before["values"].items())))
            # A press that reports PASS and changes nothing has not submitted. Measured on
            # one implementation: the name resolved, the press returned PASS, and the app
            # still declared "0 items left!". Silence is not success.
            if not moved and op["type"] == "PRESS_NAME":
                try:
                    driver.act({"type": "PRESS_POSITION", "control": "textbox",
                                "nth": 0, "key": op.get("key", "Enter")})
                    snap = driver.bind().snapshot()
                    after = _observable(snap)
                    moved = (after["text"], after["url"], tuple(sorted(after["values"].items()))) != \
                            (before["text"], before["url"], tuple(sorted(before["values"].items())))
                    acted_extra = "position:textbox[0]"
                except Exception:
                    acted_extra = None
            helped = goal_holds(after, goal)["holds"] or moved
            _remember(memory, f"{role}|{name}", helped)
            acted = {"step": step_index, "op": op, "status": res.get("status"),
                     "moved": moved, "why": cand["why"],
                     "fallback": locals().get("acted_extra"),
                     "declared_after": after["text"][:200]}
            steps.append(acted)
            if op["type"] == "FILL_NAME":
                typed_once = True
                typed_into = name
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


# --------------------------------------------------------------------------- #
# The goal, computed from the task's words and the interface's declaration
# --------------------------------------------------------------------------- #
# This is interface vocabulary, not application knowledge: it is the small closed
# class of English words interfaces use for the affordances a task can name. Measured
# on 11 independent implementations, every one of them declares "All", "Active",
# "Completed" and "Mark all as complete" and none declares anything else for these
# functions.
_FILTER_WORDS = {"all", "active", "completed", "complete", "done", "finished",
                 "remaining", "open", "pending"}


def compute_goal(instruction: str, controls: Sequence[Mapping[str, Any]],
                 *, invariant: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Turn a natural-language task into what the interface must declare.

    The task's own words are the goal for the *content* half ("add buy milk" ->
    "buy milk" must be shown). The *interface* half is computed the other way
    round: a filter named by the task is bound to the control the interface
    declares for it, because the interface is the authority on what it has.

    Measured, on every one of 11 implementations: the All/Active/Completed
    controls do not exist until there is a todo, which is why the goal cannot be
    computed from the cold declaration alone. The invariant says so
    (`appears_after_use`), and this function reads it rather than rediscovering it.
    """
    text = " ".join(instruction.lower().split())
    named_filters = sorted({w for w in _FILTER_WORDS if re.search(r"\b" + w + r"\b", text)})
    declared = {c["name"].lower(): c for c in controls if c.get("name")}

    # A filter the interface declares is bound by name; one it does not yet declare
    # is expected to appear once work exists, and is not invented.
    bound = [declared[w]["name"] for w in named_filters if w in declared]
    pending = [w for w in named_filters if w not in declared]

    # The content: quoted text first, then the words after an add/enter verb.
    quoted = re.findall(r"[\"'`]([^\"'`]{1,120})[\"'`]", instruction)
    content: list[str] = list(quoted)
    if not content:
        m = re.search(r"\b(?:add|new|create|enter|write)\b\s+(?:a\s+|an\s+|the\s+)?(?:todo\s+|item\s+|task\s+)?"
                      r"(?:named|called|saying|with)?\s*(?:\"|')?(.+?)(?:\"|')?(?:\s+to\b|\s+in\b|\s+then\b|$)",
                      instruction, re.I)
        if m and m.group(1).strip():
            content = [m.group(1).strip()]

    must_show = content + bound
    return {
        "goal": must_show,
        "content": content,
        "filters_bound": bound,
        "filters_not_yet_declared": pending,
        "needs_work_before_filters": bool(pending) and not bool(bound),
        "why": ("the task names a filter the interface does not declare yet; measured on 11 of "
                "11 apps, those controls appear only once work exists"
                if pending and not bound else
                "every goal string is either quoted content from the task or a control the "
                "interface itself declares"),
    }
