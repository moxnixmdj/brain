"""A skill addressed by ROLE AND NAME, not by pixels.  The reuse that appearance could not do.

Why this exists, in one measurement:

    last round, the learned trajectory could not be reused on a new goal, because it had to
    relocate an empty text field by appearance, and a 40x40 patch of a blank input matched
    453 offsets over 258 pixels.

    this round, the page reports the field as  role=textbox name="filter" box (34,120)-(314,148).
    One call. No ambiguity. No threshold.

So a skill stores, per step:  the ROLE and NAME of the widget, and what to do with it.  The
goal fills the holes.  A new page, a new layout, a moved banner, a different font: none of it
matters, because none of it changes what a textbox called "filter" is.

The model is not in the reuse path at all.  It was in the TEACH path, once, where it looked at
a screenshot and decided what should happen. That division is the entire design:

    MODEL   decides what to do, by looking
    PAGE    reports where things are, by structure
    GATE    checks what happened, by pixels

Each of the three is used for the one job it is actually good at. Every earlier round tried to
do all three with the same signal, and failed in a different way each time.
"""
from __future__ import annotations

import json
import time
from collections.abc import Mapping
from typing import Any

from canonical.runtime import act_loop_v1 as L
from canonical.runtime import address_v1 as A

SCHEMA = "ADDRESS_SKILL_V1"


def teach(goal: str, steps: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Record a trajectory as (role, name, verb, value), with goal-derived values as slots."""
    from canonical.runtime import parameterise_v1 as P
    slots: list[dict[str, Any]] = []
    out = []
    content = P._content_words(goal)
    for s in steps:
        step = {"action": s["action"], "role": s.get("role"), "name": s.get("name")}
        if "text" in s:
            words = str(s["text"]).lower().split()
            if words and all(w in content for w in words):
                slot = f"{{slot{len(slots)}}}"
                slots.append({"slot": slot, "taught_value": s["text"],
                              "from_goal": [w for w in words if w in content]})
                step["text"] = slot
            else:
                step["text"] = s["text"]
        out.append(step)
    return {"schema": SCHEMA, "goal": goal, "steps": out, "slots": slots}


def fill(skill: Mapping[str, Any], new_goal: str) -> dict[str, Any]:
    """Fill the slots from a new goal.  Refuses rather than guessing."""
    from canonical.runtime import parameterise_v1 as P
    tpl = {"actions": [{"action": s["action"], "text": s.get("text")}
                       for s in skill["steps"]],
           "slots": skill["slots"],
           "content_words_in_goal": P._content_words(skill["goal"])}
    r = P.fill(tpl, new_goal)
    if r["verdict"] != "FILLED":
        return r
    steps = []
    for s, a in zip(skill["steps"], r["actions"]):
        s2 = dict(s)
        if "text" in s:
            s2["text"] = a["text"]
        steps.append(s2)
    return {"schema": SCHEMA, "verdict": "FILLED", "steps": steps, "values": r["values"]}


def run(skill: Mapping[str, Any], address: A.Address, browser: Any,
        *, width: int = 1280, height: int = 900) -> dict[str, Any]:
    """Execute an addressed skill.  No model, no pixel matching, no thresholds."""
    done = []
    for i, s in enumerate(skill["steps"], 1):
        target = A.find(address, role=s.get("role"), name=s.get("name"))
        if target is None:
            return {"schema": SCHEMA, "verdict": "REFUSED_TARGET_NOT_ON_PAGE",
                    "at_step": i, "wanted": {"role": s.get("role"), "name": s.get("name")},
                    "steps_done": done}
        proposal = {"action": s["action"], "x": target["x"], "y": target["y"],
                    "because": f"addressed as {target['role']} named {target['name']!r}"}
        if s["action"] == "type":
            proposal["text"] = s.get("text", "")
        ok, why = L.validate_proposal(proposal, width, height)
        if not ok:
            return {"schema": SCHEMA, "verdict": "REFUSED_BY_GATE", "because": why,
                    "at_step": i, "steps_done": done}
        before = f"/tmp/addr_{int(time.time()*1000)}_{i}_a.png"
        browser.screenshot(before)
        L.execute_action(browser, proposal)
        time.sleep(1.0)
        after = f"/tmp/addr_{int(time.time()*1000)}_{i}_b.png"
        browser.screenshot(after)
        done.append({"step": i, "target": {"role": target["role"], "name": target["name"]},
                     "at": (target["x"], target["y"]), "action": s["action"],
                     "value": proposal.get("text")})
    final = f"/tmp/addr_final_{int(time.time()*1000)}.png"
    browser.screenshot(final)
    return {"schema": SCHEMA, "verdict": "RAN_WITHOUT_A_MODEL", "steps_done": done,
            "final_screenshot": final}
