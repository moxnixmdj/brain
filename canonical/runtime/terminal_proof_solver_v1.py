"""Fail-closed terminal proof solver v1.

This is a zero-credit coordinator over explicitly declared propositions, Horn-style
implications, proof actions, and fixed-context learned blocker clauses.

It does not invent semantic implication, estimate unknown proof cost, authorize
reality execution, or grant acceptance/family credit.

The solver answers four exact questions for the declared finite model:
1. What is already derivable?
2. Which learned blocker clauses are active and which actions do they forbid?
3. What is the maximum closure reachable from all admissible actions?
4. If every goal is reachable, what minimum declared-cost action bundle closes it?

For a terminal-false model, every goal missing from the all-admissible-action
closure is individually unreachable under the declared model and is returned as
an exact singleton unsatisfied core.
"""
from __future__ import annotations

from itertools import combinations
from math import isfinite
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TERMINAL_PROOF_SOLVER_V1"
MAX_EXACT_ACTIONS = 20


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "terminal_sat": False,
        "derived_facts": [],
        "active_learned_clauses": [],
        "blocked_action_ids": [],
        "unreachable_goals": [],
        "minimal_unsatisfied_cores": [],
        "minimum_action_bundle": None,
        "counterfactual_action_deltas": [],
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def _strings(value: Any, *, allow_empty: bool = True) -> list[str] | None:
    if not isinstance(value, list):
        return None
    if any(not isinstance(x, str) or not x for x in value):
        return None
    if len(set(value)) != len(value):
        return None
    if not allow_empty and not value:
        return None
    return list(value)


def _parse_model(doc: Mapping[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    facts = _strings(doc.get("facts", []))
    goals = _strings(doc.get("goals"), allow_empty=False)
    rules_raw = doc.get("rules", [])
    actions_raw = doc.get("actions", [])
    clauses_raw = doc.get("learned_clauses", [])

    if facts is None:
        errors.append("FACTS_INVALID")
    if goals is None:
        errors.append("GOALS_INVALID")
    if not isinstance(rules_raw, list):
        errors.append("RULES_INVALID")
    if not isinstance(actions_raw, list):
        errors.append("ACTIONS_INVALID")
    if not isinstance(clauses_raw, list):
        errors.append("LEARNED_CLAUSES_INVALID")
    if errors:
        return None, errors

    rules: list[dict[str, Any]] = []
    rule_ids: set[str] = set()
    for i, row in enumerate(rules_raw):
        if not isinstance(row, Mapping):
            errors.append(f"RULE_INVALID:{i}")
            continue
        rid = row.get("id")
        req = _strings(row.get("requires", []))
        proves = _strings(row.get("proves"), allow_empty=False)
        if not isinstance(rid, str) or not rid or rid in rule_ids:
            errors.append(f"RULE_ID_INVALID_OR_DUPLICATE:{i}")
            continue
        rule_ids.add(rid)
        if req is None or proves is None:
            errors.append(f"RULE_SHAPE_INVALID:{rid}")
            continue
        rules.append({"id": rid, "requires": frozenset(req), "proves": frozenset(proves)})

    actions: list[dict[str, Any]] = []
    action_ids: set[str] = set()
    for i, row in enumerate(actions_raw):
        if not isinstance(row, Mapping):
            errors.append(f"ACTION_INVALID:{i}")
            continue
        aid = row.get("id")
        req = _strings(row.get("requires", []))
        proves = _strings(row.get("proves"), allow_empty=False)
        cost = row.get("declared_cost", 0)
        if not isinstance(aid, str) or not aid or aid in action_ids:
            errors.append(f"ACTION_ID_INVALID_OR_DUPLICATE:{i}")
            continue
        action_ids.add(aid)
        if req is None or proves is None:
            errors.append(f"ACTION_SHAPE_INVALID:{aid}")
            continue
        if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not isfinite(float(cost)) or float(cost) < 0:
            errors.append(f"ACTION_COST_INVALID:{aid}")
            continue
        actions.append({
            "id": aid,
            "requires": frozenset(req),
            "proves": frozenset(proves),
            "declared_cost": float(cost),
            "admissible": row.get("admissible", True) is True,
        })

    clauses: list[dict[str, Any]] = []
    clause_ids: set[str] = set()
    for i, row in enumerate(clauses_raw):
        if not isinstance(row, Mapping):
            errors.append(f"CLAUSE_INVALID:{i}")
            continue
        cid = row.get("id")
        when_all = _strings(row.get("when_all"), allow_empty=False)
        blocks = _strings(row.get("blocks_actions"), allow_empty=False)
        if not isinstance(cid, str) or not cid or cid in clause_ids:
            errors.append(f"CLAUSE_ID_INVALID_OR_DUPLICATE:{i}")
            continue
        clause_ids.add(cid)
        if when_all is None or blocks is None or any(a not in action_ids for a in blocks):
            errors.append(f"CLAUSE_SHAPE_INVALID:{cid}")
            continue
        clauses.append({
            "id": cid,
            "when_all": frozenset(when_all),
            "blocks_actions": frozenset(blocks),
            "reason": row.get("reason"),
        })

    if len(actions) > MAX_EXACT_ACTIONS:
        errors.append(f"ACTION_COUNT_EXCEEDS_{MAX_EXACT_ACTIONS}")

    if errors:
        return None, errors
    return {
        "facts": frozenset(facts or []),
        "goals": frozenset(goals or []),
        "rules": rules,
        "actions": actions,
        "clauses": clauses,
    }, []


def _rule_closure(seed: set[str], rules: list[dict[str, Any]]) -> set[str]:
    out = set(seed)
    changed = True
    while changed:
        changed = False
        for rule in rules:
            if rule["requires"] <= out:
                before = len(out)
                out.update(rule["proves"])
                changed = changed or len(out) != before
    return out


def _execute_selected(
    base_facts: set[str],
    rules: list[dict[str, Any]],
    selected: list[dict[str, Any]],
) -> tuple[set[str], set[str]]:
    facts = _rule_closure(set(base_facts), rules)
    pending = {a["id"]: a for a in selected}
    applied: set[str] = set()
    changed = True
    while changed:
        changed = False
        facts = _rule_closure(facts, rules)
        for aid in sorted(list(pending)):
            action = pending[aid]
            if action["requires"] <= facts:
                before = len(facts)
                facts.update(action["proves"])
                applied.add(aid)
                del pending[aid]
                changed = True
                changed = changed or len(facts) != before
    return _rule_closure(facts, rules), applied


def evaluate(doc: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, Mapping):
        return _fail("INPUT_NOT_OBJECT")
    model, errors = _parse_model(doc)
    if errors or model is None:
        return _fail(*errors)

    base = _rule_closure(set(model["facts"]), model["rules"])

    active_clauses = [c for c in model["clauses"] if c["when_all"] <= base]
    blocked_ids: set[str] = set()
    for clause in active_clauses:
        blocked_ids.update(clause["blocks_actions"])

    candidates = [
        a for a in model["actions"]
        if a["admissible"] and a["id"] not in blocked_ids
    ]

    max_closure, max_applied = _execute_selected(base, model["rules"], candidates)
    unreachable = sorted(model["goals"] - max_closure)
    terminal_sat = not unreachable

    deltas = []
    for action in sorted(candidates, key=lambda x: x["id"]):
        closure, applied = _execute_selected(base, model["rules"], [action])
        deltas.append({
            "action_id": action["id"],
            "executable_from_current_base": action["id"] in applied,
            "new_goal_count": len((closure - base) & model["goals"]),
            "new_goals": sorted((closure - base) & model["goals"]),
            "new_proposition_count": len(closure - base),
            "new_propositions": sorted(closure - base),
            "declared_cost": action["declared_cost"],
        })

    minimum = None
    if terminal_sat:
        best_key = None
        best_row = None
        n = len(candidates)
        for size in range(n + 1):
            for idxs in combinations(range(n), size):
                selected = [candidates[i] for i in idxs]
                closure, applied = _execute_selected(base, model["rules"], selected)
                if len(applied) != len(selected) or not model["goals"] <= closure:
                    continue
                ids = tuple(sorted(a["id"] for a in selected))
                cost = sum(a["declared_cost"] for a in selected)
                key = (cost, len(ids), ids)
                if best_key is None or key < best_key:
                    best_key = key
                    best_row = {
                        "action_ids": list(ids),
                        "declared_cost": cost,
                        "action_count": len(ids),
                    }
            if best_key is not None and best_key[0] == 0:
                # A larger bundle cannot beat zero cost + smaller cardinality.
                break
        minimum = best_row

    return {
        "schema": SCHEMA,
        "status": "SAT_DECLARED_MODEL" if terminal_sat else "UNSAT_CURRENT_DECLARED_MODEL",
        "errors": [],
        "terminal_sat": terminal_sat,
        "derived_facts": sorted(base),
        "active_learned_clauses": sorted(c["id"] for c in active_clauses),
        "blocked_action_ids": sorted(blocked_ids),
        "maximally_applied_action_ids": sorted(max_applied),
        "max_reachable_facts": sorted(max_closure),
        "unreachable_goals": unreachable,
        "minimal_unsatisfied_cores": [[g] for g in unreachable],
        "minimum_action_bundle": minimum,
        "counterfactual_action_deltas": deltas,
        "rule": (
            "EXACT_ONLY_OVER_DECLARED_FINITE_MONOTONE_MODEL__"
            "NO_SEMANTIC_EDGE_OR_PROOF_COST_INVENTION__"
            "LEARNED_CLAUSES_BIND_ONLY_WHEN_ALL_DECLARED_CONTEXT_FACTS_HOLD__"
            "ZERO_ACCEPTANCE_EXECUTION_PROMOTION_OR_FAMILY_CREDIT"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
