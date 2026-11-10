"""Routing a goal to a library: mechanical where it can be, a model where it must be.

The measurement that forced this file, taken before it was written:

    library of ten skills, goals in the library's own words      10/10 with no model
    the SAME ten tasks, phrased the way a person asks             0/10 with no model
    ... with a careful mechanical router (stems, rarity weights)  3/10

So retrieval is where the value of a library actually lives, and word overlap buys about
30% of it.  This module does not replace the mechanical router -- it wraps it:

    1. ask the router.  If it routes with confidence and no ambiguity, that answer is free
       and no model is called.
    2. if the router refuses, a model reads (goal, library) and writes a ROUTE FILE.
    3. the route is checked against the library before anything runs: an unknown skill, a
       skill with no binding, or a goal whose pieces outnumber the skills chosen is refused.
    4. the routed plan is then executed by the same composer and the same causal gates.

The model is allowed to NAME a skill.  It is not allowed to invent one, to skip a stage, or
to claim a piece of the request that no skill covers.  Every one of those refusals is
tested, because the failure mode of a router that trusts its proposer is silence.
"""
from __future__ import annotations

import json
import pathlib
from collections.abc import Mapping
from typing import Any

from canonical.runtime import compose_skills_v1 as C

SCHEMA = "ROUTE_WITH_MODEL_V1"


def load_routes(path: str | pathlib.Path) -> dict[str, Any]:
    return json.loads(pathlib.Path(path).read_text())


def check_route(goal: str, route: Mapping[str, Any],
                library: Mapping[str, Any]) -> tuple[bool, str]:
    """Everything wrong with a proposed route, or (True, 'ROUTE_VALID')."""
    if not isinstance(route, Mapping):
        return False, "ROUTE_NOT_A_MAPPING"
    if route.get("abstain"):
        return False, "THE_MODEL_ABSTAINED"
    skills = route.get("skills")
    if not isinstance(skills, list) or not skills:
        return False, "ROUTE_NAMES_NO_SKILLS"
    for s in skills:
        if s not in library:
            return False, f"ROUTED_A_SKILL_THAT_DOES_NOT_EXIST__{s}"
        if library[s].get("binding") is None and not library[s].get("_bindingless_ok"):
            return False, f"SKILL_HAS_NO_BINDING_TO_RUN__{s}"
    if route.get("uncovered"):
        # Naming the part it could not do is required, not optional: a route that stays
        # silent about a gap would look complete.
        return False, f"ROUTE_LEAVES_PART_OF_THE_REQUEST_UNCOVERED__{route['uncovered']}"
    return True, "ROUTE_VALID"


def plan_from_route(goal: str, route: Mapping[str, Any],
                    library: Mapping[str, Any]) -> dict[str, Any]:
    """Turn a checked route into the same plan shape the composer already executes."""
    plan = []
    for s in route["skills"]:
        trig = library[s]["trigger"]
        slot = None
        if C.SLOT in C._normalise(trig):
            slot = (route.get("slots") or {}).get(s)
        plan.append({"skill": s, "trigger": trig, "slot": slot,
                     "because": route.get("because", "routed")})
    return {"schema": C.SCHEMA, "verdict": "PLANNED", "plan": plan, "length": len(plan),
            "covered": goal, "routed_by": route.get("routed_by", "model")}


def route_goal(goal: str, library: Mapping[str, Any],
               routes: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Mechanical first; the model's route file only if the router refused."""
    mech = C.route(goal, library)
    if mech["verdict"] == "ROUTED":
        plan = {"schema": C.SCHEMA, "verdict": "PLANNED",
                "plan": [{"skill": c["skill"], "trigger": library[c["skill"]]["trigger"],
                          "slot": None, "because": f"router matched {c['matched']}"}
                         for c in mech["chosen"]],
                "length": len(mech["chosen"]), "covered": goal, "routed_by": "mechanical"}
        return {"schema": SCHEMA, "verdict": "ROUTED_MECHANICALLY", "plan": plan,
                "router": mech}
    if routes is None:
        return {"schema": SCHEMA, "verdict": "ASK_FOR_A_ROUTE", "router": mech,
                "because": "the router refused and no model route was supplied"}
    route = routes.get(goal)
    if route is None:
        return {"schema": SCHEMA, "verdict": "NO_ROUTE_PROPOSED", "router": mech}
    ok, why = check_route(goal, route, library)
    if not ok:
        return {"schema": SCHEMA, "verdict": "REFUSED_BY_GATE", "because": why,
                "router": mech, "route": dict(route)}
    return {"schema": SCHEMA, "verdict": "ROUTED_BY_MODEL",
            "plan": plan_from_route(goal, route, library), "route": dict(route),
            "router": mech}
