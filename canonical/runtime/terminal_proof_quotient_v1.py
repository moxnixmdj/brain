"""Exact zero-credit quotient over the live terminal proof frontier.

This compiler does not infer semantic equivalence.  It validates an explicit
causal-front manifest against the compiled acceptance IR and proves only that:
  * every unresolved predicate appears in exactly one declared front;
  * no proved predicate is smuggled into a front;
  * every front target is actually reachable by at least one declared
    hypergraph action;
  * the resulting quotient is a lossless partition of the unresolved set.

The quotient is scheduling metadata only.  It grants no acceptance, capability,
family, execution, or promotion credit.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TERMINAL_PROOF_QUOTIENT_V1"


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "fronts": [],
        "unresolved_predicate_count": 0,
        "quotient_front_count": 0,
        "covered_predicates": [],
        "uncovered_predicates": [],
        "multiply_assigned_predicates": [],
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def evaluate(ir: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    if ir.get("status") not in {"PASS", "PASS_WITH_UNCOVERED_ACTION_TARGETS"}:
        return _fail("IR_NOT_PASS")
    predicates = ir.get("predicates")
    actions = ir.get("actions")
    fronts = manifest.get("fronts")
    if not isinstance(predicates, list) or not isinstance(actions, list):
        return _fail("IR_SHAPE_INVALID")
    if not isinstance(fronts, list) or not fronts:
        return _fail("FRONTS_NOT_NONEMPTY_LIST")

    unresolved = {
        row.get("id")
        for row in predicates
        if isinstance(row, Mapping)
        and isinstance(row.get("id"), str)
        and row.get("state") != "PROVED"
    }
    proved = {
        row.get("id")
        for row in predicates
        if isinstance(row, Mapping)
        and isinstance(row.get("id"), str)
        and row.get("state") == "PROVED"
    }
    action_by_id = {
        row.get("id"): row
        for row in actions
        if isinstance(row, Mapping) and isinstance(row.get("id"), str)
    }
    if len(action_by_id) != len(actions):
        return _fail("ACTION_IDS_INVALID_OR_DUPLICATE")

    errors: list[str] = []
    assigned: dict[str, list[str]] = {}
    front_out = []
    seen_front_ids: set[str] = set()

    for i, front in enumerate(fronts):
        if not isinstance(front, Mapping):
            errors.append(f"FRONT_{i}_INVALID")
            continue
        fid = front.get("id")
        targets = front.get("target_predicates")
        source_actions = front.get("source_actions")
        if not isinstance(fid, str) or not fid:
            errors.append(f"FRONT_{i}_ID_INVALID")
            continue
        if fid in seen_front_ids:
            errors.append(f"DUPLICATE_FRONT_ID:{fid}")
            continue
        seen_front_ids.add(fid)
        if (
            not isinstance(targets, list)
            or not targets
            or any(not isinstance(x, str) or not x for x in targets)
            or len(targets) != len(set(targets))
        ):
            errors.append(f"FRONT_TARGETS_INVALID:{fid}")
            continue
        if (
            not isinstance(source_actions, list)
            or not source_actions
            or any(not isinstance(x, str) or not x for x in source_actions)
            or len(source_actions) != len(set(source_actions))
        ):
            errors.append(f"FRONT_SOURCE_ACTIONS_INVALID:{fid}")
            continue

        target_set = set(targets)
        illegal_proved = sorted(target_set & proved)
        unknown_targets = sorted(target_set - unresolved)
        if illegal_proved:
            errors.append(f"FRONT_CONTAINS_PROVED:{fid}:{','.join(illegal_proved)}")
        if unknown_targets:
            errors.append(f"FRONT_TARGET_NOT_UNRESOLVED:{fid}:{','.join(unknown_targets)}")

        unknown_actions = sorted(set(source_actions) - set(action_by_id))
        if unknown_actions:
            errors.append(f"FRONT_UNKNOWN_ACTIONS:{fid}:{','.join(unknown_actions)}")
            continue

        action_target_union: set[str] = set()
        available = []
        blocked = []
        for aid in source_actions:
            action = action_by_id[aid]
            action_targets = set(action.get("unresolved_target_predicates", []))
            action_target_union.update(action_targets)
            if action.get("available_now") is True:
                available.append(aid)
            else:
                blocked.append({
                    "action_id": aid,
                    "unsatisfied_preconditions": action.get("unsatisfied_preconditions", []),
                })

        unsupported = sorted(target_set - action_target_union)
        if unsupported:
            errors.append(f"FRONT_TARGET_WITHOUT_DECLARED_ACTION:{fid}:{','.join(unsupported)}")

        for pid in targets:
            assigned.setdefault(pid, []).append(fid)

        front_out.append({
            "id": fid,
            "obligation_class": front.get("obligation_class"),
            "target_predicates": sorted(targets),
            "target_count": len(targets),
            "source_actions": sorted(source_actions),
            "available_source_actions": sorted(available),
            "blocked_source_actions": sorted(blocked, key=lambda x: x["action_id"]),
            "certificate_slots": front.get("certificate_slots", []),
            "rule": front.get("rule"),
        })

    if errors:
        return _fail(*errors)

    multiply = sorted(pid for pid, owners in assigned.items() if len(owners) != 1)
    covered = set(assigned)
    uncovered = sorted(unresolved - covered)
    overcovered = sorted(covered - unresolved)
    if multiply:
        errors.append("PREDICATE_NOT_EXACTLY_ONCE:" + ",".join(multiply))
    if uncovered:
        errors.append("UNRESOLVED_NOT_COVERED:" + ",".join(uncovered))
    if overcovered:
        errors.append("NONUNRESOLVED_COVERED:" + ",".join(overcovered))
    if errors:
        return _fail(*errors)

    return {
        "schema": SCHEMA,
        "status": "PASS_EXACT_LOSSLESS_UNRESOLVED_QUOTIENT",
        "errors": [],
        "unresolved_predicate_count": len(unresolved),
        "quotient_front_count": len(front_out),
        "fronts": sorted(front_out, key=lambda x: x["id"]),
        "covered_predicates": sorted(covered),
        "covered_predicate_count": len(covered),
        "uncovered_predicates": [],
        "multiply_assigned_predicates": [],
        "rule": (
            "EXPLICIT_MANIFEST_PARTITION_ONLY__NO_SEMANTIC_EQUIVALENCE__"
            "NO_FRONT_OR_CERTIFICATE_SLOT_IS_ACCEPTANCE_EVIDENCE"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
