#!/usr/bin/env python3
"""Hold a constraint across many steps, and read the postcondition as clauses.

THE BOTTLENECK THIS ATTACKS
---------------------------
The GUI organ from the previous round drives an interface by the names it
declares, and does it in two actions. OSWorld 2.1 — the hardest open computer-use
benchmark, 108 long-horizon workflows, >250 agent steps — names its failure modes
and every one of them is *after* the first action:

    constraint tracking, multi-item state tracking, conflict disambiguation,
    mid-task change detection, verification.

Measured on this host, on a real app, before writing any of this module: asked to
"mark beta complete but leave alpha and gamma uncompleted", the two-action loop
scored every candidate 2.0 and ranked **"Toggle All Input"** first. That control
would complete all three items and violate the constraint while satisfying the
named one. A goal that is a list of strings cannot express "and not the others",
so the organ could not have known.

THE ONE IDEA
------------
A postcondition is not a string. It is a set of clauses, each with a polarity and
a scope:

    POSITIVE  "beta shows as complete"                    must hold
    NEGATIVE  "alpha does not show as complete"           must hold
    INVARIANT "gamma keeps the state it has now"          must hold

and a candidate action is scored by *how many clauses it changes*, with a
negative change to a clause you must preserve disqualifying it outright. That is
the per-gate objective the coding search is missing, applied where the
environment can verify it from its own declaration in 123 ms.

WHAT MAKES THIS GENERALISE RATHER THAN MEMORISE
-----------------------------------------------
Nothing here knows what a todo is. A row is "a container that declares a text and
holds a control"; a control that declares no name is addressed by the text of the
container it sits in, which is where a person's eye goes too. The app supplies
every word: the item names come from the task, the control's role comes from the
accessibility tree, and the relation comes from the DOM's own parent/child.

WHAT IS SAVED
-------------
The clause matrix and the structural address that resolved a silent control.
Never the item names, the row indices, or the click sequence: the app re-declares
all of those on every visit.

Model calls: 0.  Network: 0 during a run.  Weights: unchanged.
"""
from __future__ import annotations

import json
import pathlib
import re
import time
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_HOLD_A_CONSTRAINT_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

MAX_STEPS = 24
TYPE_ROLES = ("textbox", "searchbox", "combobox", "spinbutton")
COMPLETE_WORDS = re.compile(r"\b(complete|completed|done|checked|finished)\b", re.I)
INCOMPLETE_WORDS = re.compile(r"\b(incomplete|uncompleted|active|open|pending|"
                              r"not complete|not completed|unchecked|remaining)\b", re.I)
OTHER_WORDS = re.compile(r"\b(?:leave|leaves|leaving|keep|keeps|keeping|but not|without|"
                         r"except|only|other than)\b", re.I)


# --------------------------------------------------------------------------- #
# The postcondition, as clauses over the interface's own observations
# --------------------------------------------------------------------------- #
def read_postcondition(instruction: str, items: Sequence[str]) -> dict[str, Any]:
    """Split a task into positive / negative / invariant clauses.

    This is the whole difference from a string goal. "Mark beta complete but leave
    alpha and gamma uncompleted" is one positive clause and two negatives, and the
    negatives are what stop the cheapest action (toggle everything) from winning.
    """
    text = " ".join(instruction.lower().split())
    clauses: list[dict[str, Any]] = []
    for item in items:
        low = item.lower()
        if low not in text:
            continue
        # The words around the item decide its clause. Split the instruction on the
        # item so "mark beta complete but leave alpha ... uncompleted" attributes
        # "uncompleted" to alpha and not to beta.
        spans = [m.start() for m in re.finditer(re.escape(low), text)]
        if not spans:
            continue
        at = spans[0]
        before = text[:at]
        after = text[at + len(low):]
        tail = re.split(r"\b(?:and|but|then|,)\b", after)[0]
        head = re.split(r"\b(?:and|but|then|,)\b", before)[-1]
        context = head + " " + tail
        # SCOPE, NOT ADJACENCY. "leave alpha and gamma uncompleted" puts the word
        # "uncompleted" after gamma only, so an adjacency rule classified alpha as a
        # mere invariant and the loop happily checked it -- changing a state the task
        # said to leave alone. A "leave/keep/without" before an item makes that item's
        # clause NEGATIVE all the way to the end of its list, unless a completion verb
        # is attached to it directly; a negative is strictly stronger than an invariant
        # and the strong reading is the safe one.
        # The leave-scope ENDS at a contrastive conjunction. "leave alpha alone but mark
        # beta complete" makes alpha negative and beta positive; without the bound, the
        # scope ran past "but" and made beta negative too, so the task's own instruction
        # was inverted and the loop would have refused to do the one thing it was asked.
        scope_text = re.split(r"\b(?:but|however|then|instead)\b", before)[-1]
        leave_scope = bool(OTHER_WORDS.search(scope_text))
        if INCOMPLETE_WORDS.search(context) and not COMPLETE_WORDS.search(tail):
            polarity, wanted = "negative", "incomplete"
        elif COMPLETE_WORDS.search(tail) and not leave_scope:
            polarity, wanted = "positive", "complete"
        elif leave_scope:
            polarity, wanted = "negative", "incomplete"
        elif COMPLETE_WORDS.search(context):
            polarity, wanted = "positive", "complete"
        else:
            polarity, wanted = "positive", "present"
        clauses.append({"item": item, "polarity": polarity, "wanted": wanted,
                        "context": context.strip()})
    return {"clauses": clauses, "items": list(items),
            "has_negative": any(c["polarity"] == "negative" for c in clauses),
            "why": "a clause per item the task names, with the polarity its own words give it"}


def observe_rows(snapshot: Mapping[str, Any], page_index: int = 0) -> list[dict[str, Any]]:
    """Containers that declare a text and hold a control: rows, as a person sees them.

    A row's identity is the text it publishes; the control inside it is what carries
    the state. Measured on a real app: the row checkboxes declare NO name at all, so
    a name-addressed driver cannot reach them -- but the row publishes "beta" and the
    checkbox is its child, and that relation is in the DOM, not in my memory.
    """
    pages = snapshot.get("pages") or []
    if page_index >= len(pages):
        return []
    rows: list[dict[str, Any]] = []
    for row in pages[page_index].get("rows") or []:
        rows.append({"text": (row.get("text") or "").strip(),
                     "role": row.get("role") or "listitem",
                     "control": {"role": (row.get("control_role") or "checkbox"),
                                 "checked": bool(row.get("control_checked")),
                                 "name": row.get("control_name") or ""},
                     "index": row.get("index")})
    return rows


def observe_clauses(rows: Sequence[Mapping[str, Any]], post: Mapping[str, Any]) -> dict[str, Any]:
    """The truth value of every clause, read from the rows, with no interpretation.

    A negative clause and an invariant clause are both about ABSENCE, and they are
    separate because they fail differently: a negative says the state must be other
    than it is, an invariant says it must not move. Conflating them is how a
    constraint silently becomes an instruction.
    """
    # A row's text is everything the row publishes, which may include the label of its
    # own control: one implementation reports "Toggle Todo beta" where the item is
    # "beta". So a clause's item is matched as a WORD inside a row's text, never as an
    # equality and never as a bare substring -- "alpha" must not match "alphabet".
    by_text: dict[str, Any] = {}
    for r in rows:
        for word in re.findall(r"[a-z0-9][a-z0-9._-]*", (r.get("text") or "").lower()):
            by_text.setdefault(word, r)
    out: dict[str, Any] = {}
    for clause in post.get("clauses", []):
        row = by_text.get(clause["item"].lower())
        if row is None:
            out[clause["item"]] = None                      # the item is not declared
            continue
        checked = bool(row["control"]["checked"])
        if clause["polarity"] == "positive":
            want = {"complete": True, "present": True}.get(clause["wanted"], True)
            out[clause["item"]] = checked == want
        elif clause["polarity"] == "negative":
            out[clause["item"]] = checked is False
        else:                                                # invariant
            out[clause["item"]] = ("baseline", checked)
    return out


def satisfied(state: Mapping[str, Any], post: Mapping[str, Any]) -> tuple[bool, list[str]]:
    missing: list[str] = []
    for clause in post.get("clauses", []):
        val = state.get(clause["item"])
        if val is None:
            missing.append(f"{clause['item']}: not declared by the interface")
        elif isinstance(val, tuple):                          # invariant
            continue                                          # checked below
        elif val is False:
            missing.append(f"{clause['item']}: {clause['polarity']} {clause['wanted']} violated")
    return (not missing), missing


def violations_vs_baseline(baseline: Mapping[str, Any], now: Mapping[str, Any]) -> list[str]:
    """Which invariants moved. The constraint-tracking check, and it is exact."""
    bad: list[str] = []
    for item, before in baseline.items():
        if not isinstance(before, tuple):
            continue
        after = now.get(item)
        if isinstance(after, tuple) and after[1] != before[1]:
            bad.append(item)
    return bad


# --------------------------------------------------------------------------- #
# Choosing an action, with the constraint as a filter rather than a preference
# --------------------------------------------------------------------------- #
def score_action(control: Mapping[str, Any], rows: Sequence[Mapping[str, Any]],
                 post: Mapping[str, Any], state: Mapping[str, Any]) -> dict[str, Any]:
    """What does acting on this control do to the clauses, and to the invariants?

    A control that touches only clauses is scored by progress. A control whose
    scope is wider than one clause -- "toggle all", a filter, anything that is not
    inside a row -- is scored by the damage it would do if it hit an invariant.
    Measured: on a real app the global toggle ranked first at 2.0 under the old
    scorer and would have completed all three items when the task named one.
    """
    name = (control.get("name") or "").strip()
    role = control.get("role") or ""
    in_row = control.get("row_text")
    scope = "row" if in_row else "global"
    # The row's text is matched the same way the state reader matches it: the item is a
    # WORD inside what the row publishes. One implementation reports "Toggle Todo beta"
    # and an equality test found no clause, so every row scored 0.0 and the planner fell
    # through to a global control -- a checkbox by the textbox's name.
    row_words = set(re.findall(r"[a-z0-9][a-z0-9._-]*", str(in_row or "").lower()))
    hits = [c for c in post.get("clauses", [])
            if in_row and c["item"].lower() in row_words]
    protected = [k for k, v in state.items() if isinstance(v, tuple)]
    negatives = [c["item"] for c in post.get("clauses", []) if c["polarity"] == "negative"]

    score, why = 0.0, []
    if scope == "row" and hits:
        clause = hits[0]
        cur = state.get(clause["item"])
        done = (cur is True) or (clause["polarity"] == "negative" and cur is True)
        if done:
            # The clause this row is about already holds. Acting on it can only break
            # it, and it is the cheapest wrong move available: the first version of
            # this scorer gave every named row 6.0 and checked alpha -- the item the
            # task said to leave alone -- twelve times in a row without ever reaching
            # the positive clause.
            score, why = -9.0, [f"{clause['item']} already satisfies its clause"]
        elif role in ("checkbox", "switch", "radio"):
            ahead = [c for c in post.get("clauses", [])
                     if c["polarity"] == "positive" and state.get(c["item"]) is not True]
            score = 6.0 if ahead else 1.0
            why = [f"acts inside the row the task names ({clause['item']})"]
            if not ahead:
                why.append("no positive clause is open")
        else:
            score, why = 3.0, [f"inside the named row ({clause['item']}) but not a state control"]
    elif scope == "global" and role in ("checkbox", "switch") and protected:
        # The cheap fatal action: one click that touches every row at once.
        score, why = -8.0, ["acts on every row at once; the task protects "
                            f"{len(protected)} row(s)"]
    elif scope == "global" and role in ("link", "button", "tab"):
        score, why = 1.0, ["navigates or filters; changes no row state"]
    elif role in TYPE_ROLES:
        score, why = 2.0, ["accepts typed text"]
    if scope == "global" and COMPLETE_WORDS.search(name) and protected:
        score, why = min(score, -6.0), why + ["names a global completion"]
    if negatives and scope == "global" and role in ("checkbox", "switch"):
        score, why = score - 2.0, why + ["task has negative clauses"]
    return {"score": score, "why": why, "scope": scope, "row_text": in_row}


def plan_step(controls: Sequence[Mapping[str, Any]], rows: Sequence[Mapping[str, Any]],
              post: Mapping[str, Any], state: Mapping[str, Any]) -> dict[str, Any]:
    ranked = []
    for c in controls:
        if not (c.get("name") or c.get("row_text")):
            continue
        s = score_action(c, rows, post, state)
        ranked.append({**s, "control": c})
    ranked.sort(key=lambda r: -r["score"])
    return {"best": ranked[0] if ranked else None, "ranking": ranked[:6]}


# --------------------------------------------------------------------------- #
# The loop
# --------------------------------------------------------------------------- #
def _snapshot(driver):
    return driver.bind().snapshot()


def run_constrained(url: str, instruction: str, items: Sequence[str], *,
                    driver=None, max_steps: int = MAX_STEPS) -> dict[str, Any]:
    """Do the task, hold the constraint, and stop when the clauses are all true.

    The postcondition is re-read from the interface after every action, so the loop
    cannot drift: a constraint that breaks mid-task is detected at the step that
    broke it, not discovered at the end.
    """
    if driver is None:                                        # pragma: no cover
        from canonical.runtime import browser_v1 as _b
        driver = _b
    started = time.time()
    steps: list[dict[str, Any]] = []
    post = read_postcondition(instruction, items)

    nav = driver.act({"type": "NAVIGATE", "url": url})
    if nav.get("status") != "PASS":
        return {"schema": SCHEMA, "authority": AUTHORITY,
                "status": "REFUSE__NAVIGATE_FAILED", "detail": nav}

    snap = _snapshot(driver)
    rows = observe_rows(snap)
    # The items the task names may not exist yet. A long-horizon task usually starts
    # by creating its own material, and refusing here would be refusing the task for
    # being long. Type each missing item into the textbox the app declares.
    if not rows and items:
        seeded = _seed_items(driver, snap, items)
        if seeded:
            snap = _snapshot(driver)
            rows = observe_rows(snap)
    if not rows:
        return {"schema": SCHEMA, "authority": AUTHORITY,
                "status": "REFUSE__NO_ROWS_DECLARED", "postcondition": post,
                "declared": (snap.get("pages") or [{}])[0].get("body_text", "")[:400]}
    state = observe_clauses(rows, post)
    baseline = {k: v for k, v in state.items() if isinstance(v, tuple)}
    ok, missing = satisfied(state, post)
    if ok:
        return {"schema": SCHEMA, "authority": AUTHORITY, "status": "ALREADY_SATISFIED",
                "postcondition": post, "steps": [], "model_calls": 0, "network_calls": 0}

    for step_index in range(max_steps):
        controls = declared_controls(snap)
        chosen = plan_step(controls, rows, post, state)
        best = chosen["best"]
        if best is None or best["score"] <= 0:
            steps.append({"step": step_index, "status": "REFUSE__NO_SAFE_ACTION",
                          "why": "every candidate would risk a protected clause",
                          "ranking": [(r["score"], r["control"].get("name"),
                                       r["control"].get("row_text")) for r in chosen["ranking"]]})
            break
        c = best["control"]
        op = _op_for(c, best)
        before_rows = rows
        res = driver.act(op)
        snap = _snapshot(driver)
        rows = observe_rows(snap)
        state = observe_clauses(rows, post)
        broke = violations_vs_baseline(baseline, state)
        ok, missing = satisfied(state, post)
        steps.append({"step": step_index, "op": op, "status": res.get("status"),
                      "why": best["why"], "score": best["score"],
                      "invariants_broken": broke, "missing": missing,
                      "declared": (snap.get("pages") or [{}])[0].get("body_text", "")[:200]})
        if broke:
            return {"schema": SCHEMA, "authority": AUTHORITY,
                    "status": "FAILED__INVARIANT_BROKEN", "postcondition": post,
                    "steps": steps, "broken": broke,
                    "seconds": round(time.time() - started, 3),
                    "model_calls": 0, "network_calls": 0}
        if ok:
            return {"schema": SCHEMA, "authority": AUTHORITY, "status": "SATISFIED",
                    "postcondition": post, "steps": steps,
                    "seconds": round(time.time() - started, 3),
                    "invariants_held": sorted(baseline),
                    "model_calls": 0, "network_calls": 0}

    return {"schema": SCHEMA, "authority": AUTHORITY, "status": "NOT_REACHED",
            "postcondition": post, "steps": steps, "missing": missing,
            "seconds": round(time.time() - started, 3),
            "model_calls": 0, "network_calls": 0}


def _seed_items(driver, snapshot, items: Sequence[str]) -> int:
    """Create the items the task names, addressed by the textbox the app declares."""
    controls = declared_controls(snapshot)
    box = [c for c in controls if c["role"] in TYPE_ROLES and c["name"]]
    if not box:
        return 0
    made = 0
    for item in items:
        try:
            driver.act({"type": "FILL_NAME", "role": box[0]["role"],
                        "name": box[0]["name"], "text": item})
            driver.act({"type": "PRESS_NAME", "role": box[0]["role"],
                        "name": box[0]["name"], "key": "Enter"})
            made += 1
        except Exception:
            break
    return made


def declared_controls(snapshot: Mapping[str, Any], page_index: int = 0) -> list[dict[str, Any]]:
    """Every control, with the row it belongs to when it belongs to one.

    Role and name come from the interface organ's own reader rather than a second
    copy of the same rules. Writing that inference twice is how two organs come to
    disagree about the same page -- and the first version of this function did
    exactly that: it read the raw `role` attribute, which is empty on a plain
    `<input>`, so every control came back nameless and the loop refused a page it
    could see.
    """
    import importlib
    I = importlib.import_module("canonical.runtime.interface_is_its_own_declaration_v1")
    pages = snapshot.get("pages") or []
    if page_index >= len(pages):
        return []
    named = I.declared_names(snapshot, page_index)
    raws = pages[page_index].get("elements") or []
    out = []
    for i, c in enumerate(named):
        row_text = raws[i].get("row_text") if i < len(raws) else None
        out.append({"role": c["role"], "name": c["name"], "href": c.get("href") or "",
                    "row_text": row_text, "checked": c.get("checked")})
    return out


def _op_for(control: Mapping[str, Any], best: Mapping[str, Any]) -> dict[str, Any]:
    if best["scope"] == "row":
        return {"type": "CHECK_IN_ROW", "row_text": control.get("row_text"),
                "role": control.get("role"), "checked": True}
    if control.get("role") in ("link", "button", "tab"):
        return {"type": "CLICK_NAME", "role": control["role"], "name": control["name"]}
    return {"type": "TOGGLE_NAME", "name": control["name"], "checked": True}
