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


# ============================================================================ routing
# The collapse this section answers, measured before writing a line of it:
#
#   a library of ten skills, goals phrased in the library's own words   10/10 planned
#   the SAME ten tasks, phrased the way a person asks                    0/10 planned
#
# So a library's value is not what it contains.  It is what can be FOUND in it.  A literal
# planner is a filing cabinet with no index: everything is there and nothing can be reached.
#
# The router below is deliberately mechanical -- word overlap, nothing learned, no model --
# because the point is to measure the ceiling of cheap retrieval before spending anything
# expensive on it.  It reports its own confidence, refuses to guess between close
# candidates, and names the words it did not account for.  Those three behaviours matter
# more than the accuracy: a router that guesses silently is worse than one that asks.

_STOP = frozenset("""a an the this that these those me my it its of in on at to for with and or
but then please show give put get make do does did be is are was were some any""".split())


def _words(s: str) -> list[str]:
    w = []
    for t in "".join(c.lower() if c.isalnum() else " " for c in s).split():
        if t in _STOP or len(t) <= 2:
            continue
        w.append(t[:-1] if len(t) > 4 and t.endswith("s") else t)
    return w


def _stem_set(s: str) -> frozenset[str]:
    return frozenset(_words(s))


def route(goal: str, library: Mapping[str, Any], *, min_margin: float = 0.15,
          min_hits: int = 1) -> dict[str, Any]:
    """Pick skills for a goal, or refuse.  No model, no learning, no scores that flatter.

    Each stage of the goal is routed separately: the goal is split on the connectors the
    planner already knows, and every piece is matched against every trigger.  Overlap is
    measured on stems, weighted by how rare a word is across the library -- a word that
    appears in every trigger distinguishes nothing.
    """
    pieces = [p for p in goal.replace(",", " then ").split(" then ") if p.strip()]
    chosen: list[dict[str, Any]] = []
    for piece in pieces:
        gw = _stem_set(piece)
        if not gw:
            continue
        # rarity weight: 1/(how many triggers contain the word)
        df: dict[str, int] = {}
        for s in library.values():
            for w in _stem_set(s["trigger"].replace(SLOT, " ")):
                df[w] = df.get(w, 0) + 1
        scored = []
        for name, skill in library.items():
            tw = _stem_set(skill["trigger"].replace(SLOT, " "))
            hits = gw & tw
            if len(hits) < min_hits:
                continue
            score = sum(1.0 / df.get(w, len(library)) for w in hits) / max(1, len(tw))
            scored.append((score, len(hits), name, sorted(hits)))
        scored.sort(reverse=True)
        if not scored:
            return {"schema": "ROUTE_V1", "verdict": "NO_ROUTE", "unrouted": piece.strip(),
                    "chosen": chosen, "because": "no trigger shares a word with this"}
        best = scored[0]
        if len(scored) > 1:
            margin = best[0] - scored[1][0]
            if margin < min_margin or (best[1] == scored[1][1] and abs(margin) < 1e-9):
                return {"schema": "ROUTE_V1", "verdict": "AMBIGUOUS",
                        "between": [best[2], scored[1][2]], "margin": round(margin, 4),
                        "unrouted": piece.strip(), "chosen": chosen,
                        "because": "two skills explain this request equally well"}
        chosen.append({"skill": best[2], "piece": piece.strip(), "matched": best[3],
                       "score": round(best[0], 4)})
    if not chosen:
        return {"schema": "ROUTE_V1", "verdict": "NO_ROUTE", "unrouted": goal, "chosen": []}
    return {"schema": "ROUTE_V1", "verdict": "ROUTED", "chosen": chosen,
            "confidence": round(min(c["score"] for c in chosen), 4)}
