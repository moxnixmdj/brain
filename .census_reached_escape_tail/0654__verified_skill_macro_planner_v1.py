"""Planner adapter for verified executable skills.

A verified skill is reused as a planning macro, never as a new unverified effect
authority. The adapter:

1. validates the exact executable_skill_program_v7 digest and verified-skill flags;
2. requires every skill step to match a currently available underlying capability's
   exact requires/provides contract;
3. checks the stored step chain is composable from the skill preconditions to its
   postconditions;
4. injects a planner-only macro with conservative cost equal to the sum of the
   underlying live capability costs;
5. expands any selected macro back into the underlying capability IDs before
   execution.

Therefore learning can accelerate routing/search while execution still passes
through the live capability verifiers and V3 effect-semantics bindings.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.capability_planner import PlanningFailure, plan_capabilities
from canonical.runtime.executable_skill_program_v7 import (
    candidate_digest,
    normalize_steps,
)

SCHEMA = "PROJECT_BRAIN_VERIFIED_SKILL_MACRO_PLANNER_V1"
SKILL_SCHEMA = "PROJECT_BRAIN_EXECUTABLE_SKILL_PROGRAM_V7"
RELATIONS = {"EXACT", "PROVEN_SUPERSET"}


class SkillMacroError(ValueError):
    pass


def _token(v: Any, label: str) -> str:
    if not isinstance(v, str) or not v.strip() or "\x00" in v:
        raise SkillMacroError(label + "_INVALID")
    return v.strip()


def _items(xs: Any, label: str) -> list[str]:
    if not isinstance(xs, Sequence) or isinstance(xs, (str, bytes)):
        raise SkillMacroError(label + "_INVALID")
    out = sorted({_token(x, label) for x in xs})
    return out


def _validate_skill(skill: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(skill, Mapping):
        raise SkillMacroError("SKILL_NOT_OBJECT")
    if skill.get("schema") != SKILL_SCHEMA:
        raise SkillMacroError("SKILL_SCHEMA_INVALID")
    if skill.get("status") != "VERIFIED_EXECUTABLE_SKILL":
        raise SkillMacroError("SKILL_NOT_VERIFIED")
    if skill.get("verified_skill") is not True or skill.get("reuse_authorized") is not True:
        raise SkillMacroError("SKILL_REUSE_NOT_AUTHORIZED")
    if skill.get("candidate_only") is not False:
        raise SkillMacroError("SKILL_STILL_CANDIDATE_ONLY")
    relation = skill.get("scope_relation")
    if relation not in RELATIONS:
        raise SkillMacroError("SKILL_SCOPE_RELATION_INVALID")
    receipt = _token(skill.get("verification_receipt"), "SKILL_VERIFICATION_RECEIPT")

    ids = sorted(_token(x, "SOURCE_EPISODE_ID") for x in skill.get("source_episode_ids", []))
    steps = normalize_steps(skill.get("steps"))
    pre = _items(skill.get("preconditions", []), "SKILL_PRECONDITIONS")
    post = _items(skill.get("postconditions", []), "SKILL_POSTCONDITIONS")
    invalid = _items(skill.get("invalidators", []), "SKILL_INVALIDATORS")
    expected = candidate_digest(
        source_episode_ids=ids,
        steps=steps,
        preconditions=pre,
        postconditions=post,
        invalidators=invalid,
    )
    if skill.get("candidate_sha256") != expected:
        raise SkillMacroError("SKILL_CANDIDATE_DIGEST_INVALID")
    return {
        "candidate_sha256": expected,
        "steps": steps,
        "preconditions": pre,
        "postconditions": post,
        "invalidators": invalid,
        "scope_relation": relation,
        "verification_receipt": receipt,
    }


def _cap_map(problem: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw = problem.get("capabilities")
    if not isinstance(raw, list) or not raw:
        raise SkillMacroError("CAPABILITIES_REQUIRED")
    out = {}
    for row in raw:
        if not isinstance(row, Mapping):
            raise SkillMacroError("CAPABILITY_NOT_OBJECT")
        cid = _token(row.get("id"), "CAPABILITY_ID")
        if cid in out:
            raise SkillMacroError("CAPABILITY_ID_DUPLICATE:" + cid)
        out[cid] = row
    return out


def compile_macro(problem: Mapping[str, Any], skill: Mapping[str, Any]) -> dict[str, Any]:
    s = _validate_skill(skill)
    caps = _cap_map(problem)

    current = set(s["preconditions"])
    sequence: list[str] = []
    total_cost = 0.0

    for step in s["steps"]:
        cid = _token(step["op"], "SKILL_STEP_OP")
        cap = caps.get(cid)
        if cap is None:
            raise SkillMacroError("SKILL_STEP_CAPABILITY_MISSING:" + cid)
        requires = _items(cap.get("requires", []), cid + ".requires")
        provides = _items(cap.get("provides", []), cid + ".provides")
        if requires != list(step["inputs"]):
            raise SkillMacroError("SKILL_STEP_INPUT_CONTRACT_DRIFT:" + cid)
        if provides != list(step["outputs"]):
            raise SkillMacroError("SKILL_STEP_OUTPUT_CONTRACT_DRIFT:" + cid)
        if not set(requires).issubset(current):
            raise SkillMacroError("SKILL_STEP_PRECONDITION_UNSATISFIED:" + cid)
        try:
            cost = float(cap.get("cost", 1.0))
        except Exception as exc:
            raise SkillMacroError("SKILL_STEP_COST_INVALID:" + cid) from exc
        if cost < 0:
            raise SkillMacroError("SKILL_STEP_COST_NEGATIVE:" + cid)
        total_cost += cost
        current.update(provides)
        sequence.append(cid)

    if not set(s["postconditions"]).issubset(current):
        raise SkillMacroError("SKILL_POSTCONDITIONS_NOT_PRODUCED")

    macro_id = "SKILL_MACRO::" + s["candidate_sha256"].split(":", 1)[-1][:24]
    return {
        "schema": SCHEMA,
        "status": "VERIFIED_SKILL_MACRO_READY",
        "macro_id": macro_id,
        "candidate_sha256": s["candidate_sha256"],
        "requires": list(s["preconditions"]),
        "provides": list(s["postconditions"]),
        "cost": total_cost,
        "underlying_capability_ids": sequence,
        "verification_receipt": s["verification_receipt"],
        "scope_relation": s["scope_relation"],
        "invalidators": list(s["invalidators"]),
        "execution_authority": False,
        "macro_is_planner_only": True,
    }


def plan_with_skills(
    problem: Mapping[str, Any],
    verified_skills: Sequence[Mapping[str, Any]],
    *,
    active_invalidators: Sequence[str] = (),
) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        raise SkillMacroError("PROBLEM_NOT_OBJECT")
    invalid = set(_items(active_invalidators, "ACTIVE_INVALIDATORS"))
    macros = []
    for skill in verified_skills:
        macro = compile_macro(problem, skill)
        if invalid.intersection(macro["invalidators"]):
            continue
        macros.append(macro)

    planning_problem = dict(problem)
    base_caps = list(problem.get("capabilities") or [])
    planner_macros = []
    macro_by_id = {}
    for macro in macros:
        row = {
            "id": macro["macro_id"],
            "requires": macro["requires"],
            "provides": macro["provides"],
            "cost": macro["cost"],
            "result_fields": [],
            "action": {"type": "planner_macro_only"},
        }
        planner_macros.append(row)
        macro_by_id[macro["macro_id"]] = macro
    planning_problem["capabilities"] = base_caps + planner_macros

    try:
        planned = plan_capabilities(planning_problem)
    except PlanningFailure as exc:
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED__NO_PLAN",
            "pass": False,
            "reason": str(exc),
            "macros_considered": [m["macro_id"] for m in macros],
            "execution_authority": False,
        }

    expanded: list[str] = []
    used: list[str] = []
    for cid in planned["plan"]:
        macro = macro_by_id.get(cid)
        if macro is None:
            expanded.append(cid)
        else:
            used.append(cid)
            expanded.extend(macro["underlying_capability_ids"])

    return {
        "schema": SCHEMA,
        "status": "PASS__SKILL_AWARE_PLAN_COMPILED",
        "pass": True,
        "planner_plan": planned["plan"],
        "expanded_execution_plan": expanded,
        "used_verified_skill_macros": used,
        "macros_considered": [m["macro_id"] for m in macros],
        "execution_rule": "EXPANDED_UNDERLYING_CAPABILITIES_MUST_BE_REVERIFIED_BY_THE_LIVE_SOLVER",
        "execution_authority": False,
        "capability_credit_delta": 0,
    }
