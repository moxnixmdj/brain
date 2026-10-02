"""Deterministic scheduler for closing Project Brain terminal proof routes.

This module never grants terminal or capability credit. It converts the canonical
ACTIVE_TERMINAL_PROOF_BASIS into a stable execution queue so workers do not
rediscover, reorder, or accidentally reopen already-closed proof work.

Scheduling law:
1. Closed terminal routes are excluded.
2. Binding/acceptance-only gaps precede scope-expansion gaps.
3. Already independently preflighted routes precede routes that still need a
   new whole-scope mechanism.
4. Shared multi-portfolio contracts get higher leverage.
5. Open-domain matched protocols are distinct from finite scope-equivalence proofs.
6. Canonically affected open-domain contracts with stale finite whole-scope blockers
   are reclassified before any proof work is scheduled.
7. Exact-comparator gaps with no authorized zero-cost route are marked external-blocked
   and must not consume clean terminal cases.
8. Unknown state fails closed and is scheduled for reconciliation, not promotion.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

BASIS = "canonical/governance/ACTIVE_TERMINAL_PROOF_BASIS_V1.json"
OPEN_DOMAIN_AUDIT = "canonical/governance/OPEN_DOMAIN_PREQUALIFICATION_DEADLOCK_AUDIT_V1.json"

_BINDING_TOKENS = (
    "POST_FREEZE",
    "POPULATION_BINDING_PENDING",
    "ACCEPTANCE_RULE_NOT_YET_FROZEN",
    "ACCEPTANCE_MODE_BINDING_PENDING",
)
_SCOPE_GATE_TOKENS = ("SCOPE_EQUIVALENT_PROOF_GATE_V2_NOT_YET_PASS",)
_SCOPE_EXPANSION_TOKENS = (
    "WHOLE_SCOPE",
    "WHOLE_CONTRACT",
    "WHOLE_OPEN_ENDED",
    "FULL_CROSS_DOMAIN",
    "GENERAL_ACTIVE_CONSTRAINT",
    "DYNAMIC_TOOL_DISCOVERY",
    "ANALYTIC_CURVED",
    "RAW_DRAWING_OCR",
    "NATIVE_SOLID_MATERIALIZATION",
    "BOUNDED_SYNTHETIC_ENVELOPE",
)
_OPEN_DOMAIN_PROTOCOL_TOKENS = (
    "FREEZE_MATCHED_HARNESS",
    "FREEZE_BRAIN_OWNED",
    "FREEZE_POST_FREEZE_SELECTOR",
    "CHALLENGE_SOURCE_POOL_AND_SCORER",
    "OPEN_DOMAIN_MATCHED_TERMINAL_PROTOCOL",
)
_EXTERNAL_BLOCK_TOKENS = (
    "COMPARATOR_UNAVAILABLE_AT_ZERO_INCREMENTAL_SPEND",
    "EXTERNAL_BLOCKED",
)


def _load(root: Path) -> dict[str, Any]:
    data = json.loads((root / BASIS).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("ACTIVE_TERMINAL_PROOF_BASIS_NOT_OBJECT")
    return data


def _load_open_domain_contracts(root: Path) -> set[str]:
    path = root / OPEN_DOMAIN_AUDIT
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("OPEN_DOMAIN_AUDIT_NOT_OBJECT")
    status = data.get("status")
    affected = data.get("affected_contract_classes")
    law = data.get("corrected_prequalification_law")
    if not isinstance(status, str) or "FINITE_SCOPE_EQUIVALENCE_MUST_NOT_BE_REQUIRED" not in status:
        raise ValueError("OPEN_DOMAIN_AUDIT_NOT_CANONICALLY_ACTIVE")
    if not isinstance(affected, list) or any(not isinstance(x, str) or not x for x in affected):
        raise ValueError("OPEN_DOMAIN_AFFECTED_CONTRACTS_INVALID")
    if not isinstance(law, dict) or "open_domain_matched_routes" not in law:
        raise ValueError("OPEN_DOMAIN_CORRECTED_LAW_MISSING")
    return set(affected)


def _portfolio_count(value: Any) -> int:
    if not isinstance(value, str) or not value:
        return 0
    return len([x for x in value.split("_") if x.startswith("T") and x[1:].isdigit()])


def _classify(blocker: str) -> str:
    if any(tok in blocker for tok in _EXTERNAL_BLOCK_TOKENS):
        return "EXTERNAL_BLOCK"
    if any(tok in blocker for tok in _OPEN_DOMAIN_PROTOCOL_TOKENS):
        return "OPEN_DOMAIN_PROTOCOL"
    if any(tok in blocker for tok in _BINDING_TOKENS):
        return "BINDING"
    if any(tok in blocker for tok in _SCOPE_GATE_TOKENS):
        return "SCOPE_GATE"
    if any(tok in blocker for tok in _SCOPE_EXPANSION_TOKENS):
        return "SCOPE_EXPANSION"
    return "OTHER"


def evaluate(root: Path) -> dict[str, Any]:
    basis = _load(root)
    try:
        open_domain_contracts = _load_open_domain_contracts(root)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {
            "schema": "PROJECT_BRAIN_TERMINAL_ROUTE_CLOSURE_QUEUE_V1",
            "status": "FAIL_CLOSED",
            "execution_authority": False,
            "promotion_authority": False,
            "errors": ["OPEN_DOMAIN_AUDIT_INVALID:" + str(exc)],
            "queue": [],
        }

    rows = basis.get("contracts")
    if not isinstance(rows, list):
        return {
            "schema": "PROJECT_BRAIN_TERMINAL_ROUTE_CLOSURE_QUEUE_V1",
            "status": "FAIL_CLOSED",
            "execution_authority": False,
            "errors": ["CONTRACTS_NOT_LIST"],
            "queue": [],
        }

    errors: list[str] = []
    closed: list[str] = []
    queue: list[dict[str, Any]] = []
    reclassification_required: list[str] = []

    seen: set[str] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"ROW_{i}_NOT_OBJECT")
            continue
        bid = row.get("behavior_id")
        if not isinstance(bid, str) or not bid:
            errors.append(f"ROW_{i}_BEHAVIOR_ID_INVALID")
            continue
        if bid in seen:
            errors.append("DUPLICATE_BEHAVIOR_ID:" + bid)
            continue
        seen.add(bid)

        state = row.get("proof_state")
        blockers = row.get("blockers")
        if not isinstance(state, str) or not state:
            errors.append("PROOF_STATE_INVALID:" + bid)
            continue
        if not isinstance(blockers, list) or any(not isinstance(x, str) or not x for x in blockers):
            errors.append("BLOCKERS_INVALID:" + bid)
            continue

        if state == "TERMINAL_ROUTE_FROZEN_ADMISSIBLE":
            if blockers:
                errors.append("CLOSED_ROUTE_HAS_BLOCKERS:" + bid)
            closed.append(bid)
            continue
        if not blockers:
            errors.append("OPEN_ROUTE_WITHOUT_BLOCKER:" + bid)
            continue

        classes = [_classify(x) for x in blockers]
        binding = sum(x == "BINDING" for x in classes)
        gate = sum(x == "SCOPE_GATE" for x in classes)
        expansion = sum(x == "SCOPE_EXPANSION" for x in classes)
        protocol = sum(x == "OPEN_DOMAIN_PROTOCOL" for x in classes)
        external = sum(x == "EXTERNAL_BLOCK" for x in classes)
        other = sum(x == "OTHER" for x in classes)
        preflight = any(
            token in state
            for token in (
                "PREFLIGHT_PASS",
                "INFORMATION_SAFE",
                "INDEPENDENT_",
                "BOUNDED_",
            )
        )
        leverage = _portfolio_count(row.get("portfolio"))
        is_open_domain = bid in open_domain_contracts
        legacy_open_domain_scope = is_open_domain and (gate + expansion > 0)

        if legacy_open_domain_scope:
            score = -1000 - min(leverage, 4) * 3
            next_action = "RECLASSIFY_TO_OPEN_DOMAIN_MATCHED_PROTOCOL"
            reclassification_required.append(bid)
        else:
            score = (
                external * 1000
                + expansion * 100
                + other * 50
                + gate * 10
                + protocol * 4
                + binding
                - min(leverage, 4) * 3
                - (8 if preflight else 0)
            )
            next_action = (
                "EXTERNAL_BLOCKED__FREEZE_INTERNAL_PROTOCOL_FIELDS_ONLY__DO_NOT_SPEND_CLEAN_CASES"
                if external
                else (
                    "FREEZE_OPEN_DOMAIN_MATCHED_PROTOCOL"
                    if protocol and expansion == 0 and other == 0
                    else (
                        "FREEZE_BINDING_AND_ACCEPTANCE"
                        if expansion == 0 and other == 0 and protocol == 0 and (binding or gate)
                        else "CLOSE_SCOPE_EQUIVALENCE_THEN_FREEZE_BINDING"
                    )
                )
            )

        queue.append({
            "behavior_id": bid,
            "portfolio": row.get("portfolio"),
            "proof_state": state,
            "blockers": blockers,
            "blocker_classes": {
                "binding": binding,
                "scope_gate": gate,
                "scope_expansion": expansion,
                "open_domain_protocol": protocol,
                "external_block": external,
                "other": other,
                "legacy_open_domain_scope_equivalence": (gate + expansion) if legacy_open_domain_scope else 0,
            },
            "open_domain_matched_protocol": is_open_domain,
            "independent_or_information_safe_preflight_present": preflight,
            "portfolio_leverage": leverage,
            "priority_score": score,
            "next_action_class": next_action,
        })

    queue.sort(key=lambda x: (x["priority_score"], x["behavior_id"]))

    declared_count = basis.get("active_contract_count")
    declared_closed = basis.get("admissible_frozen_terminal_route_count")
    if declared_count != len(seen):
        errors.append("ACTIVE_CONTRACT_COUNT_MISMATCH")
    if declared_closed != len(closed):
        errors.append("ADMISSIBLE_ROUTE_COUNT_MISMATCH")

    return {
        "schema": "PROJECT_BRAIN_TERMINAL_ROUTE_CLOSURE_QUEUE_V1",
        "status": "FAIL_CLOSED" if errors else "PASS",
        "execution_authority": False,
        "promotion_authority": False,
        "active_contract_count": len(seen),
        "closed_route_count": len(closed),
        "open_route_count": len(queue),
        "closed_behavior_ids": sorted(closed),
        "open_domain_deadlock_audit_applied": bool(open_domain_contracts),
        "open_domain_contract_count": len(open_domain_contracts),
        "reclassification_required_behavior_ids": sorted(reclassification_required),
        "queue": queue,
        "top_priority_behavior_id": queue[0]["behavior_id"] if queue else None,
        "errors": sorted(set(errors)),
        "rule": (
            "SCHEDULER_ONLY__NO_CAPABILITY_CREDIT__NO_TERMINAL_EXECUTION_AUTHORITY__"
            "CANONICAL_OPEN_DOMAIN_MATCHED_ROUTES_MUST_NOT_BE_SENT_TO_IMPOSSIBLE_FINITE_SCOPE_EQUIVALENCE__"
            "ACTUAL_PROMOTION_REQUIRES_ACTIVE_BASIS_AND_PREQUALIFICATION_REDUCERS"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root", type=Path)
    args = ap.parse_args()
    out = evaluate(args.repo_root)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
