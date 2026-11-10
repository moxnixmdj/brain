"""Does a library of skills make NEW tasks cheaper, or only OLD ones?

That is the whole question, and it is a measurement, not a position.  r65 showed that a
taught skill transfers to a neighbouring instance of the same task (5/5).  It said nothing
about whether two skills can be line up to do a task neither of them was taught for.

The claim this file tests, in the user's own words: "give it a task once and it learns it
permanently, so we can use this to do anything on a computer".  If that is true, then a
library of taught skills should collapse the cost of a NEW task, because the new task is
usually a composition of things that were each taught.

What is deliberately NOT here: a planner, a search over compositions, or a model in the
composition step.  A first measurement of composition must not smuggle in the intelligence
it is trying to measure.  Here two skills are joined only if the goal literally names both,
in order, in the taught phrasing.  If THAT collapses the cost, composition is real and the
planner is worth building.  If it does not, no amount of planner would help, because there
would be nothing to plan over.
"""
from __future__ import annotations

import json
import pathlib
import re
import time
from collections.abc import Mapping
from typing import Any

SCHEMA = "COMPOSE_SKILLS_V1"


SLOT = "\u0000slot\u0000"
# Connectors glue two triggers together and are never a skill of their own.  Found by
# measuring: "search for eigenvalues then sort the list" planned the first skill and then
# reported the word "then" as an uncovered gap.
CONNECTORS = frozenset({"then", "and", "after", "that", "next", "finally"})


def _normalise(s: str) -> str:
    """Tokens as a list-free string: slang-punctuated words, slots preserved.

    Slots are written `<query>` and survive normalisation as a single token.  Two bugs were
    found here by measuring, and both are the same bug -- being clever about punctuation:
    the first stripped the brackets so a slot became the word "query"; the second turned
    "< query >" into three tokens.  This version finds slots with a regex first and only
    then strips punctuation from everything that is not one.
    """
    out = []
    pos = 0
    for m in re.finditer(r"<([a-z_]+)>", s):
        out.append(re.sub(r"[^a-z0-9 ]", " ", s[pos:m.start()].lower()))
        out.append(" " + SLOT + " ")
        pos = m.end()
    out.append(re.sub(r"[^a-z0-9 ]", " ", s[pos:].lower()))
    return " ".join("".join(out).split())


def find_plan(goal: str, library: Mapping[str, Any]) -> dict[str, Any]:
    """Longest prefix of the goal that a taught skill covers, then the next, and so on.

    Greedy, and deliberately stupid: the point of this round is to find out whether
    composition reduces cost AT ALL, not to build a good planner.  A greedy join needs no
    model and no search, so whatever it achieves is a FLOOR for composition -- anything
    smarter can only do better.
    """
    words = _normalise(goal).split()
    plan: list[dict[str, Any]] = []
    i = 0
    while i < len(words):
        best = None
        for name, skill in library.items():
            trig = _normalise(skill["trigger"]).split()
            # A trigger may contain SLOTS, written "<query>".  A slot consumes exactly one
            # word and its value is carried into the skill, because a skill that could only
            # ever mean one literal string would not be a skill, it would be a recording.
            # Found by measuring: "search for eigenvalues then sort the list" produced no
            # plan at all, because the parameter read as a missing skill.
            if not trig or i + len(trig) > len(words):
                continue
            ok = all(t == SLOT or t == words[i + k] for k, t in enumerate(trig))
            if ok:
                slot = None
                for k, t in enumerate(trig):
                    if t == SLOT:
                        slot = words[i + k]
                if best is None or len(trig) > len(best[1]):
                    best = (name, trig, slot)
        if best is None:
            if words[i] in CONNECTORS:
                i += 1
                continue
            return {"schema": SCHEMA, "verdict": "NO_PLAN",
                    "covered": " ".join(words[:i]), "uncovered": " ".join(words[i:]),
                    "plan": plan,
                    "because": "no taught skill starts at this word"}
        plan.append({"skill": best[0], "trigger": " ".join(best[1]), "slot": best[2]})
        i += len(best[1])
    return {"schema": SCHEMA, "verdict": "PLANNED", "plan": plan,
            "length": len(plan), "covered": goal}


def run_plan(plan: Mapping[str, Any], library: Mapping[str, Any], browser: Any,
             shot_dir: str | pathlib.Path, *, settle: float = 1.0) -> dict[str, Any]:
    """Execute a planned sequence of taught skills.  No model at any point."""
    from canonical.runtime import grounding_v1 as G
    from canonical.runtime import act_loop_v1 as L

    shot_dir = pathlib.Path(shot_dir)
    shot_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    steps_done: list[dict[str, Any]] = []
    for i, item in enumerate(plan["plan"], 1):
        binding = library[item["skill"]]["binding"]
        cur = shot_dir / f"before_{i:02d}.png"
        browser.screenshot(cur)
        g = G.ground(binding, cur)
        if g["verdict"] != "GROUNDED":
            return {"schema": SCHEMA, "verdict": "REFUSED_NOT_GROUNDED",
                    "at_skill": item["skill"], "missing": g.get("missing"),
                    "steps_done": steps_done}
        actions = G.to_actions(g, settle=settle)
        nxt = shot_dir / f"after_{i:02d}.png"
        ok = True
        for a in actions[:-1]:
            L.execute_action(browser, a)
            time.sleep(float(a.get("settle", settle)))
        last = actions[-1]
        browser.screenshot(shot_dir / f"pre_{i:02d}.png")
        L.execute_action(browser, last)
        time.sleep(float(last.get("settle", settle)))
        browser.screenshot(nxt)
        cc = L.causal_check(shot_dir / f"pre_{i:02d}.png", nxt,
                            last.get("expect_region"), expect=str(last.get("expect", "some")))
        steps_done.append({"skill": item["skill"], "actions": len(actions),
                           "causal": cc["verdict"], "detail": cc["detail"]})
        if cc["verdict"] == "CAUSAL_VIOLATION":
            ok = False
        if not ok:
            return {"schema": SCHEMA, "verdict": "REFUSED_CAUSAL_VIOLATION",
                    "at_skill": item["skill"], "steps_done": steps_done}
    return {"schema": SCHEMA, "verdict": "COMPOSED_WITHOUT_A_MODEL",
            "skills": [s["skill"] for s in plan["plan"]],
            "total_actions": sum(s["actions"] for s in steps_done),
            "steps_done": steps_done,
            "seconds": round(time.time() - t0, 2),
            "final_screenshot": str(shot_dir / f"after_{len(plan['plan']):02d}.png")}
