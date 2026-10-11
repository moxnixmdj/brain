"""Field-level generic goal-to-tool-effect planner for Project Brain.

V2 upgrades the V1 coarse "intent grounded" prerequisite into explicit
semantic evidence obligations. It remains benchmark- and vendor-agnostic.

Pipeline:
  plain goal -> ordered intents
  arbitrary REST-like schemas -> action/effect profiles
  mutation schemas -> required semantic evidence fields
  observations / earlier mutation results -> evidence producers
  existing capability_planner -> minimum-cost causal plan

No tool is executed here. Unknown, ambiguous, or ungroundable routes fail closed.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence

from canonical.runtime.capability_planner import PlanningFailure, plan_capabilities
from canonical.runtime.generic_goal_tool_effect_planner_v1 import (
    compile_goal_contract,
    endpoint_rows_from_search_payloads,
    profile_endpoint as _profile_v1,
)
from canonical.runtime.generic_tool_argument_binder_v1 import (
    canonical_field,
    endpoint_grounding_contract,
)

SCHEMA = "PROJECT_BRAIN_GENERIC_GOAL_TOOL_EFFECT_PLANNER_V2"
_RELATION_SEMANTICS = {"id","project","workspace","section","task","tag","person"}
_TEXT_MARKERS = {
    "text","body","body_plain","content","message","messages","snippet","payload",
    "description","notes","note","comment","comments","subject",
}


def _tokens(value: Any) -> list[str]:
    return [
        x.lower()
        for x in re.findall(r"[A-Za-z][A-Za-z0-9_-]*", str(value or ""))
        if len(x) > 1
    ]


def _response_semantics(endpoint: Mapping[str, Any]) -> list[str]:
    raw = " ".join(
        str(x or "")
        for x in (
            endpoint.get("response"),
            endpoint.get("responseBody"),
            endpoint.get("response_body"),
            endpoint.get("description"),
        )
    )
    out: set[str] = set()
    for token in _tokens(raw):
        canonical = canonical_field(token)
        if canonical:
            out.add(canonical)
        if token in _TEXT_MARKERS:
            out.add("text")
        if token in {"id","gid","key","identifier","identifiers"}:
            out.add("id")
    return sorted(out)


def profile_endpoint(endpoint: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(_profile_v1(endpoint))
    row["response_semantics"] = _response_semantics(endpoint)
    return row


def _resource_overlap(intent: Mapping[str, Any], profile: Mapping[str, Any]) -> list[str]:
    left = {str(x) for x in (intent.get("resource_terms") or [])}
    right = {str(x) for x in (profile.get("resource_terms") or [])}
    return sorted(left & right)


def _compatibility(
    intent: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> tuple[int, list[str]] | None:
    overlap = _resource_overlap(intent, profile)
    if not overlap:
        return None
    action = str(intent.get("action_class") or "")
    endpoint_action = str(profile.get("action_class") or "")
    if action == "observe":
        if endpoint_action != "observe":
            return None
        base = 24
    elif action != endpoint_action:
        return None
    else:
        base = 30
    return base + min(20, 4 * len(overlap)), overlap


def _done(intent_id: str) -> str:
    return "goal." + intent_id + ".satisfied"


def _evidence(intent_id: str, semantic: str) -> str:
    return "goal." + intent_id + ".evidence." + str(semantic)


def _earlier_observe_match(
    profile: Mapping[str, Any],
    mutation_intent: Mapping[str, Any],
    positive: Sequence[Mapping[str, Any]],
) -> bool:
    m_index = int(mutation_intent.get("clause_index") or 0)
    for intent in positive:
        if intent.get("action_class") != "observe":
            continue
        if int(intent.get("clause_index") or 0) > m_index:
            continue
        if _compatibility(intent, profile) is not None:
            return True
    return False


def _observation_can_supply(
    profile: Mapping[str, Any],
    intent: Mapping[str, Any],
    semantic: str,
    positive: Sequence[Mapping[str, Any]],
) -> bool:
    semantics = set(str(x) for x in profile.get("response_semantics") or [])
    overlap = bool(_resource_overlap(intent, profile))

    if semantic in semantics and overlap:
        return True
    if semantic in _RELATION_SEMANTICS and "id" in semantics and overlap:
        return True
    # Rich text from a causally earlier explicit observation can encode named
    # values (task name, due date, amount, recipient, etc.). The binder still
    # validates that the concrete value actually exists before execution.
    if "text" in semantics and _earlier_observe_match(profile, intent, positive):
        return True
    return False


def _mutation_can_supply_later(
    current_intent: Mapping[str, Any],
    current_profile: Mapping[str, Any],
    later_intent: Mapping[str, Any],
    semantic: str,
) -> bool:
    semantics = set(str(x) for x in current_profile.get("response_semantics") or [])
    shared = bool(
        set(str(x) for x in current_intent.get("resource_terms") or [])
        & set(str(x) for x in later_intent.get("resource_terms") or [])
    )
    if not shared:
        return False
    if semantic in semantics:
        return True
    if semantic in _RELATION_SEMANTICS and "id" in semantics:
        return True
    return False


def _mutation_candidates(
    *,
    goal: str,
    positive: Sequence[Mapping[str, Any]],
    profiles: Sequence[Mapping[str, Any]],
) -> tuple[
    dict[str, list[dict[str, Any]]],
    list[dict[str, Any]],
]:
    by_intent: dict[str, list[dict[str, Any]]] = {}
    ambiguities: list[dict[str, Any]] = []

    for intent in positive:
        if intent.get("action_class") == "observe":
            continue
        rows: list[dict[str, Any]] = []
        for profile in profiles:
            comp = _compatibility(intent, profile)
            if comp is None:
                continue
            score, overlap = comp
            contract = endpoint_grounding_contract(
                goal=goal,
                endpoint=profile["raw"],
            )
            rows.append({
                "profile": profile,
                "score": score,
                "overlap": overlap,
                "required_evidence_semantics": list(
                    contract.get("required_evidence_semantics") or []
                ),
                "grounding_contract": contract,
            })
        rows.sort(
            key=lambda x: (
                -int(x["score"]),
                str(x["profile"].get("id") or ""),
            )
        )
        by_intent[str(intent["id"])] = rows
        if rows:
            best = int(rows[0]["score"])
            top_ids = sorted({
                str(x["profile"]["id"])
                for x in rows
                if int(x["score"]) == best
            })
            if len(top_ids) > 1:
                ambiguities.append({
                    "intent_id": intent["id"],
                    "action_class": intent["action_class"],
                    "score": best,
                    "endpoint_ids": top_ids,
                })
    return by_intent, ambiguities


def build_planning_problem(
    goal: str,
    endpoints: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    contract = compile_goal_contract(goal)
    positive = [
        x for x in (contract.get("intents") or [])
        if not x.get("forbidden")
    ]
    if not positive:
        return {
            "schema": SCHEMA,
            "status": contract.get("status"),
            "contract": contract,
            "problem": None,
            "capability_meta": {},
            "endpoint_profiles": [],
            "route_ambiguities": [],
        }

    profiles: list[dict[str, Any]] = []
    for endpoint in endpoints:
        try:
            profiles.append(profile_endpoint(endpoint))
        except ValueError:
            continue

    candidate_map, ambiguities = _mutation_candidates(
        goal=goal,
        positive=positive,
        profiles=profiles,
    )
    capability_meta: dict[str, dict[str, Any]] = {}
    capabilities: list[dict[str, Any]] = []

    # Read endpoints can both satisfy explicit observation goals and produce
    # field-level evidence required by later mutations.
    for profile in profiles:
        if profile["action_class"] != "observe":
            continue
        provides: set[str] = set()
        matched_intents: list[str] = []
        evidence_rows: list[dict[str, str]] = []
        scores: list[int] = []

        for intent in positive:
            comp = _compatibility(intent, profile)
            if intent["action_class"] == "observe" and comp is not None:
                provides.add(_done(str(intent["id"])))
                matched_intents.append(str(intent["id"]))
                scores.append(int(comp[0]))

            if intent["action_class"] == "observe":
                continue
            candidate_rows = candidate_map.get(str(intent["id"]), [])
            required = sorted({
                semantic
                for row in candidate_rows
                for semantic in row["required_evidence_semantics"]
            })
            for semantic in required:
                if _observation_can_supply(profile, intent, semantic, positive):
                    fact = _evidence(str(intent["id"]), semantic)
                    provides.add(fact)
                    evidence_rows.append({
                        "intent_id": str(intent["id"]),
                        "semantic": semantic,
                    })
                    scores.append(18)

        if not provides:
            continue
        cid = "observe::" + str(profile["id"])
        capabilities.append({
            "id": cid,
            "requires": [],
            "provides": sorted(provides),
            "cost": max(0.2, 1.2 - (max(scores or [10]) / 100.0)),
            "action": {
                "type": "dynamic_tool_endpoint",
                "args": {"endpoint_id": profile["id"]},
            },
        })
        capability_meta[cid] = {
            "role": "observation",
            "endpoint_id": profile["id"],
            "method": profile["method"],
            "url": profile["url"],
            "matched_intents": matched_intents,
            "evidence_rows": evidence_rows,
            "response_semantics": profile["response_semantics"],
            "score": max(scores or [10]),
        }

    # Mutations consume only the evidence fields their concrete schema needs.
    # Their returned state may ground later actions, enabling causal chains such
    # as create-object -> obtain ID -> associate-object.
    positive_index = {
        str(intent["id"]): i for i, intent in enumerate(positive)
    }
    for intent in positive:
        if intent["action_class"] == "observe":
            continue
        rows = candidate_map.get(str(intent["id"]), [])
        for row in rows:
            profile = row["profile"]
            cid = "act::" + str(intent["id"]) + "::" + str(profile["id"])
            requires = [
                _evidence(str(intent["id"]), semantic)
                for semantic in row["required_evidence_semantics"]
            ]
            provides = {_done(str(intent["id"]))}
            later_evidence: list[dict[str, str]] = []

            current_i = positive_index[str(intent["id"])]
            for later in positive[current_i + 1:]:
                if later["action_class"] == "observe":
                    continue
                later_rows = candidate_map.get(str(later["id"]), [])
                later_required = sorted({
                    semantic
                    for later_row in later_rows
                    for semantic in later_row["required_evidence_semantics"]
                })
                for semantic in later_required:
                    if _mutation_can_supply_later(
                        intent, profile, later, semantic
                    ):
                        provides.add(_evidence(str(later["id"]), semantic))
                        later_evidence.append({
                            "intent_id": str(later["id"]),
                            "semantic": semantic,
                        })

            capabilities.append({
                "id": cid,
                "requires": sorted(set(requires)),
                "provides": sorted(provides),
                "cost": max(0.25, 1.5 - (int(row["score"]) / 100.0)),
                "action": {
                    "type": "dynamic_tool_endpoint",
                    "args": {"endpoint_id": profile["id"]},
                },
            })
            capability_meta[cid] = {
                "role": "mutation",
                "endpoint_id": profile["id"],
                "method": profile["method"],
                "url": profile["url"],
                "intent_id": intent["id"],
                "action_class": intent["action_class"],
                "overlap": row["overlap"],
                "score": row["score"],
                "required_evidence_semantics": row[
                    "required_evidence_semantics"
                ],
                "later_evidence": later_evidence,
                "response_semantics": profile["response_semantics"],
                "grounding_contract": row["grounding_contract"],
            }

    problem = {
        "initial_facts": [],
        "target_effects": [_done(str(x["id"])) for x in positive],
        "capabilities": capabilities,
        "max_expansions": 20000,
    }
    return {
        "schema": SCHEMA,
        "status": "READY",
        "contract": contract,
        "problem": problem,
        "capability_meta": capability_meta,
        "endpoint_profiles": profiles,
        "route_ambiguities": ambiguities,
    }



def _verification_endpoint_ids(
    contract: Mapping[str, Any],
    profiles: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Choose read surfaces that can independently observe mutated resources."""
    out: list[str] = []
    positive = [
        x for x in (contract.get("intents") or [])
        if not x.get("forbidden") and x.get("action_class") != "observe"
    ]
    for intent in positive:
        ranked: list[tuple[int, str]] = []
        for profile in profiles:
            if profile.get("action_class") != "observe":
                continue
            overlap = _resource_overlap(intent, profile)
            if not overlap:
                continue
            semantics = set(str(x) for x in profile.get("response_semantics") or [])
            score = 4 * len(overlap)
            if "id" in semantics:
                score += 3
            if "name" in semantics:
                score += 2
            if "status" in semantics:
                score += 2
            if "text" in semantics:
                score += 1
            ranked.append((score, str(profile["id"])))
        ranked.sort(key=lambda x: (-x[0], x[1]))
        for _, endpoint_id in ranked[:2]:
            if endpoint_id not in out:
                out.append(endpoint_id)
    return out

def plan_goal_over_tool_schemas(
    goal: str,
    endpoints: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    built = build_planning_problem(goal, endpoints)
    if built.get("problem") is None:
        return {
            **built,
            "pass": built.get("status") == "NO_POSITIVE_ACTION_REQUIRED",
            "plan": [],
            "steps": [],
        }
    if built.get("route_ambiguities"):
        return {
            **built,
            "status": "UNRESOLVED",
            "pass": False,
            "reason": "AMBIGUOUS_TOP_TOOL_EFFECT_ROUTE",
            "plan": [],
            "steps": [],
        }
    problem = built["problem"]
    if not problem.get("capabilities"):
        return {
            **built,
            "status": "UNRESOLVED",
            "pass": False,
            "reason": "NO_COMPATIBLE_TOOL_EFFECTS",
            "plan": [],
            "steps": [],
        }
    try:
        planned = plan_capabilities(problem)
    except PlanningFailure as exc:
        return {
            **built,
            "status": "UNRESOLVED",
            "pass": False,
            "reason": exc.code + (
                (":" + str(exc.detail)) if exc.detail else ""
            ),
            "plan": [],
            "steps": [],
        }

    steps: list[dict[str, Any]] = []
    meta = built["capability_meta"]
    for cid in planned["plan"]:
        row = dict(meta.get(cid) or {})
        row["capability_id"] = cid
        steps.append(row)

    return {
        **built,
        "status": "PLANNED",
        "pass": True,
        "planning": planned,
        "plan": list(planned["plan"]),
        "steps": steps,
        "observation_endpoint_ids": [
            x["endpoint_id"] for x in steps if x.get("role") == "observation"
        ],
        "mutation_endpoint_ids": [
            x["endpoint_id"] for x in steps if x.get("role") == "mutation"
        ],
        "verification_endpoint_ids": _verification_endpoint_ids(
            built["contract"],
            built["endpoint_profiles"],
        ),
    }
