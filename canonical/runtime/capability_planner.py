#!/usr/bin/env python3
"""Zero-dependency capability-graph planner for Project Brain.

This is deliberately small: it plans over externally declared capabilities
(preconditions/effects/cost/action contracts). It does not interpret arbitrary
natural language and it does not call a model. Unknown effects fail closed so
the acquisition layer can search for a missing capability instead of guessing.
"""
from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass


class PlanningFailure(RuntimeError):
    def __init__(self, code, detail=None):
        self.code = code
        self.detail = detail
        msg = code if detail is None else f"{code}:{detail}"
        super().__init__(msg)


@dataclass(frozen=True)
class Capability:
    capability_id: str
    requires: frozenset[str]
    provides: frozenset[str]
    cost: float
    action: dict
    result_fields: frozenset[str]


def _string_set(value, field):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise PlanningFailure("INVALID_STRING_SET", field)
    return frozenset(x.strip() for x in value)


def _normalize(problem):
    if not isinstance(problem, dict):
        raise PlanningFailure("INVALID_PROBLEM")
    initial = _string_set(problem.get("initial_facts", []), "initial_facts")
    targets = _string_set(problem.get("target_effects", []), "target_effects")
    if not targets:
        raise PlanningFailure("TARGET_EFFECTS_REQUIRED")
    raw_caps = problem.get("capabilities", [])
    if not isinstance(raw_caps, list) or not raw_caps:
        raise PlanningFailure("CAPABILITIES_REQUIRED")
    caps = []
    seen = set()
    for raw in raw_caps:
        if not isinstance(raw, dict):
            raise PlanningFailure("INVALID_CAPABILITY")
        cid = str(raw.get("id", "")).strip()
        if not cid or cid in seen:
            raise PlanningFailure("INVALID_OR_DUPLICATE_CAPABILITY_ID", cid)
        seen.add(cid)
        requires = _string_set(raw.get("requires", []), f"{cid}.requires")
        provides = _string_set(raw.get("provides", []), f"{cid}.provides")
        if not provides:
            raise PlanningFailure("CAPABILITY_PROVIDES_REQUIRED", cid)
        try:
            cost = float(raw.get("cost", 1.0))
        except Exception as exc:
            raise PlanningFailure("INVALID_CAPABILITY_COST", cid) from exc
        if cost < 0:
            raise PlanningFailure("NEGATIVE_CAPABILITY_COST", cid)
        action = raw.get("action")
        if not isinstance(action, dict) or not isinstance(action.get("type"), str):
            raise PlanningFailure("EXECUTABLE_ACTION_REQUIRED", cid)
        result_fields = _string_set(raw.get("result_fields", []), f"{cid}.result_fields")
        caps.append(Capability(cid, requires, provides, cost, action, result_fields))
    return initial, targets, caps


def reachable_effects(initial, caps):
    facts = set(initial)
    changed = True
    while changed:
        changed = False
        for cap in caps:
            if cap.requires.issubset(facts) and not cap.provides.issubset(facts):
                facts.update(cap.provides)
                changed = True
    return frozenset(facts)


def plan_capabilities(problem):
    initial, targets, caps = _normalize(problem)
    if targets.issubset(initial):
        return {
            "status": "SOLVED",
            "plan": [],
            "total_cost": 0.0,
            "expanded_states": 0,
            "initial_facts": sorted(initial),
            "target_effects": sorted(targets),
        }

    reachable = reachable_effects(initial, caps)
    unreachable = sorted(targets - reachable)
    if unreachable:
        raise PlanningFailure("UNREACHABLE_TARGET_EFFECTS", ",".join(unreachable))

    cap_by_id = {c.capability_id: c for c in caps}
    counter = itertools.count()
    frontier = [(0.0, 0, next(counter), initial, tuple())]
    best = {initial: 0.0}
    expanded = 0
    max_expansions = max(1, min(int(problem.get("max_expansions", 5000)), 100000))

    while frontier:
        cost, depth, _, facts, path = heapq.heappop(frontier)
        if cost != best.get(facts):
            continue
        if targets.issubset(facts):
            return {
                "status": "SOLVED",
                "plan": list(path),
                "total_cost": cost,
                "expanded_states": expanded,
                "initial_facts": sorted(initial),
                "target_effects": sorted(targets),
            }
        expanded += 1
        if expanded > max_expansions:
            raise PlanningFailure("MAX_EXPANSIONS_EXCEEDED", str(max_expansions))

        for cap in caps:
            if not cap.requires.issubset(facts):
                continue
            if cap.provides.issubset(facts):
                continue
            new_facts = frozenset(set(facts) | set(cap.provides))
            new_cost = cost + cap.cost
            if new_cost >= best.get(new_facts, float("inf")):
                continue
            best[new_facts] = new_cost
            heapq.heappush(
                frontier,
                (new_cost, depth + 1, next(counter), new_facts, path + (cap.capability_id,))
            )

    raise PlanningFailure("NO_CAPABILITY_PLAN")


def _resolve_effect_bindings(value, consumer, providers):
    if isinstance(value, dict):
        if set(value.keys()) == {"$effect_result"}:
            spec = value["$effect_result"]
            if not isinstance(spec, dict):
                raise PlanningFailure("INVALID_EFFECT_RESULT_BINDING", consumer.capability_id)
            effect = str(spec.get("effect", "")).strip()
            field = str(spec.get("field", "")).strip()
            if not effect or not field:
                raise PlanningFailure("INVALID_EFFECT_RESULT_BINDING", consumer.capability_id)
            if effect not in consumer.requires:
                raise PlanningFailure(
                    "BINDING_EFFECT_NOT_REQUIRED",
                    f"{consumer.capability_id}:{effect}",
                )
            provider = providers.get(effect)
            if provider is None:
                raise PlanningFailure(
                    "BINDING_PROVIDER_MISSING",
                    f"{consumer.capability_id}:{effect}",
                )
            cycle, producer = provider
            if field not in producer.result_fields:
                raise PlanningFailure(
                    "BINDING_RESULT_FIELD_UNDECLARED",
                    f"{producer.capability_id}:{field}",
                )
            return {"$result": {"cycle": cycle, "field": field}}
        return {
            key: _resolve_effect_bindings(item, consumer, providers)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_resolve_effect_bindings(item, consumer, providers) for item in value]
    return value


def plan_actions(problem):
    result = plan_capabilities(problem)
    _, _, caps = _normalize(problem)
    cap_by_id = {c.capability_id: c for c in caps}
    actions = []
    providers = {}
    for cid in result["plan"]:
        cap = cap_by_id[cid]
        action = _resolve_effect_bindings(cap.action, cap, providers)
        action.setdefault("args", {})
        action["capability_id"] = cid
        cycle = len(actions)
        actions.append(action)
        for effect in cap.provides:
            providers[effect] = (cycle, cap)
    finish_summary = str(problem.get("finish_summary", "CAPABILITY_PLAN_COMPLETE")).strip()
    if not finish_summary:
        raise PlanningFailure("FINISH_SUMMARY_REQUIRED")
    actions.append({
        "type": "finish",
        "args": {"summary": finish_summary},
        "why": "All target effects have an executable minimum-cost capability plan."
    })
    return {"planning": result, "actions": actions}
