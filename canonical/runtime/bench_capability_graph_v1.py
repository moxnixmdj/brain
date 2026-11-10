"""The sequencing layer this benchmark needed already existed in the repo.

canonical/runtime/capability_planner.py is a zero-dependency STRIPS/A* planner over a
capability graph: requires -> provides, cost, executable action, typed channels. It is
verified, it fails closed, and it has been in this repository the whole time.

What r73-r78 was doing instead: a hand-written subgoal loop that clicked candidates in list
order and retried on a no-op. That is not planning. This module replaces it.

THE MODELLING PROBLEM, stated honestly. MiniWob pages do not announce "menu is open" or
"tab 2 selected". What they DO announce is a set of addressable NAMES. So:

    fact      = a name is addressable right now
    capability = clicking widget W makes names {..} addressable (learned by observing W)
    goal      = the literal from the instruction becomes addressable

That is a real capability graph, it is built only from observation, and `plan_capabilities`
then finds the shortest route to bring the target into existence. The planner supplies the
ORDER; nothing supplies the semantics of what the page will do -- that comes from probing.
"""
from __future__ import annotations

import sys
from typing import Any

sys.path.insert(0, "/home/user/brain")

from canonical.runtime.capability_planner import (
    PlanningFailure,
    plan_capabilities,
)


def facts_from_nodes(nodes) -> frozenset[str]:
    """A fact is a (role, content) pair, not a bare name.

    MEASURED FAILURE, kept because it was the whole first attempt: MiniWob names its
    expanders "Section #1", "Section #2", "Section #3" whether the section is open or shut.
    A fact keyed on the name alone therefore does not change when a section opens, so the
    planner correctly concluded that clicking it accomplishes nothing and 28 tasks came back
    NO_ROUTE. The open section's PARAGRAPH is the new fact -- role + content."""
    out = set()
    for n in nodes:
        name = (n.get("name") or "").strip().lower()
        if not name or len(name) > 120:
            continue
        out.add(f"name:{name}")
        out.add(f"content:{n.get('role','')}:{name[:60]}")
    return frozenset(out)


def capability_for(name: str, reveals: set[str], role: str, cost: float = 1.0) -> dict:
    """A widget is a capability that (a) does not need to be visible to be used, and
    (b) provides the facts for whatever appeared after it was used."""
    cid = f"use:{role}:{name}"
    return {
        "id": cid,
        "requires": [],
        "provides": [f"name:{r}" for r in sorted(reveals)] or [f"used:{cid}"],
        "cost": cost,
        "action": {"type": "click_named", "target": name, "role": role},
    }


def plan_to_reveal_content(initial: frozenset, target: str, capabilities: list[dict],
                           max_expansions: int = 4000) -> dict[str, Any]:
    """Same planner, target expressed as a content fact (the literal may be body text that
    only exists inside an opened section)."""
    from canonical.runtime.capability_planner import plan_capabilities, PlanningFailure
    want_low = target.strip().lower()
    if any(want_low in f for f in initial if f.startswith("content:")):
        return {"status": "ALREADY_PRESENT", "plan": [], "total_cost": 0.0}
    goal = f"content:{want_low}"
    # content facts carry a role prefix, so declare the target as a provides-string the
    # planner can match exactly by adding a synthetic capability that names it
    caps = list(capabilities) + [{
        "id": "__target__", "requires": [], "provides": [goal],
        "cost": 0.0, "action": {"type": "noop"}}]
    try:
        r = plan_capabilities({"initial_facts": sorted(initial),
                               "target_effects": [goal], "capabilities": caps})
        r["plan"] = [c for c in r["plan"] if c != "__target__"]
        return r
    except PlanningFailure as e:
        return {"status": "NO_ROUTE", "code": getattr(e, "code", str(e))}


def plan_to_reveal(initial: frozenset[str], target: str, capabilities: list[dict],
                   max_expansions: int = 4000) -> dict[str, Any]:
    """Shortest ordered route that makes `target` addressable.

    Returns the planner's own dict, or a stated refusal. A refusal is the useful answer when
    the target cannot be brought into existence by any observed route -- it means probing
    has not yet found the door, and the honest move is to say so rather than click.
    """
    want = f"name:{target.strip().lower()}"
    if want in initial:
        return {"status": "ALREADY_PRESENT", "plan": [], "total_cost": 0.0}
    problem = {
        "initial_facts": sorted(initial),
        "target_effects": [want],
        "capabilities": capabilities,
    }
    try:
        return plan_capabilities(problem)
    except PlanningFailure as e:
        return {"status": "NO_ROUTE", "code": getattr(e, "code", str(e)),
                "detail": getattr(e, "detail", None)}
