"""A per-step oracle that can see a control's STATE, and checks the step against the goal.

WHY (r109). verify_before_submit_v1 (r108) produced three numbers for the same instrument:
15/20, then 11/12, then 0/3 against the real grader. The third is the true one. The reason
is in the observation, not the reasoning: bench_capability_graph_v1.facts_from_nodes builds
facts from (role, content) only. A checkbox that gets CHECKED keeps its role and its text.

    before:  role=checkbox  name=bOFt
    after :  role=checkbox  name=bOFt        <- identical fact, real state change

So a diff over that fact set cannot see the most common computer-use action at all, and any
oracle built on it verifies liveness, never correctness.

This module carries STATE: checked, selected, disabled, value, plus the accessible label. A
step is then judged against the GOAL: it counts only if the control whose label the goal
names is the control whose state moved. That is the difference between "something happened"
and "the thing the goal asked for happened".
"""
from __future__ import annotations
import json
import re
import time
from typing import Any, Callable

_STATE_EXPR = (
    "JSON.stringify(Array.from(document.querySelectorAll("
    "'#area input,#area button,#area select,#area textarea,#area option,#area [id]'))"
    ".filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0;})"
    ".map(e=>({id:e.id||'',tag:e.tagName,"
    "name:((e.labels&&e.labels[0])?e.labels[0].innerText:(e.innerText||e.value||'')).trim().slice(0,40),"
    "checked:!!e.checked,selected:!!e.selected,disabled:!!e.disabled,"
    "value:(e.value||'').slice(0,30),cls:(e.className||'').slice(0,24)})))")


def read_state(evaluate: Callable[[str], Any]) -> list[dict[str, Any]]:
    raw = evaluate(_STATE_EXPR)
    try:
        return json.loads(raw) if isinstance(raw, str) else (raw or [])
    except Exception:
        return []


def state_facts(state: list[dict[str, Any]]) -> frozenset[str]:
    """ONE fact per control, carrying every state field. 'checked' now changes a fact."""
    out = set()
    for e in state:
        key = e.get("id") or f"{e.get('tag')}::{e.get('name')}"
        out.add("ctl:%s|chk=%d|sel=%d|dis=%d|val=%s" % (
            key, bool(e.get("checked")), bool(e.get("selected")),
            bool(e.get("disabled")), e.get("value", "")))
    return frozenset(out)


def _moved(facts_before: frozenset, facts_after: frozenset) -> set[str]:
    """Which control keys changed state."""
    def by_key(fs):
        d = {}
        for f in fs:
            k = f.split("|", 1)[0][4:]
            d[k] = f
        return d
    a, b = by_key(facts_before), by_key(facts_after)
    return {k for k in a if k in b and a[k] != b[k]}


def goal_names(goal: str, state: list[dict[str, Any]]) -> list[str]:
    """Which control keys the goal's own words point at. No lexicon, no capitals rule:
    a control is named if its label appears in the goal."""
    g = " ".join(str(goal or "").lower().split())
    hits = []
    for e in state:
        nm = " ".join(str(e.get("name") or "").lower().split())
        if nm and len(nm) >= 2 and nm in g:
            hits.append(e.get("id") or f"{e.get('tag')}::{e.get('name')}")
    return hits


def judged_step(evaluate: Callable[[str], Any], act: Callable[[], Any],
                goal: str) -> dict[str, Any]:
    """Do the step, then say whether THE CONTROL THE GOAL NAMES is what moved."""
    before = state_facts(read_state(evaluate))
    t0 = time.perf_counter()
    act()
    dt = (time.perf_counter() - t0) * 1000.0
    time.sleep(0.20)
    state = read_state(evaluate)
    after = state_facts(state)
    moved = _moved(before, after)
    named = goal_names(goal, state)
    correct = sorted(set(moved) & set(named))
    return {
        "status": "STEP_CORRECT" if correct else ("STEP_MOVED_WRONG_CONTROL" if moved else "STEP_HAD_NO_EFFECT"),
        "moved": sorted(moved)[:6],
        "goal_named": sorted(named)[:6],
        "matched": correct[:6],
        "elapsed_ms": round(dt, 1),
    }
