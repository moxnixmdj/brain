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
5. Unknown state fails closed and is scheduled for reconciliation, not promotion.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

BASIS = "canonical/governance/ACTIVE_TERMINAL_PROOF_BASIS_V1.json"
DEADLOCK_AUDIT = "canonical/governance/OPEN_DOMAIN_PREQUALIFICATION_DEADLOCK_AUDIT_V1.json"

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


def _load(root: Path) -> dict[str, Any]:
    data = json.loads((root / BASIS).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("ACTIVE_TERMINAL_PROOF_BASIS_NOT_OBJECT")
    return data


def _open_domain_contracts(root: Path) -> set[str]:
    """Return contracts canonically classified as open-domain matched routes.

    If the deadlock audit is absent or malformed, fail closed by returning an empty
    set; the scheduler will retain the older conservative scope-expansion behavior.
    """
    path = root / DEADLOCK_AUDIT
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return set()
    rows = data.get("affected_contract_classes")
    if not isinstance(rows, list) or any(not isinstance(x, str) or not x for x in rows):
        return set()
    return set(rows)


def _portfolio_count(value: Any) -> int:
    if not isinstance(value, str) or not value:
        return 0
    return len([x for x in value.split("_") if x.startswith("T") and x[1:].isdigit()])


def _classify(blocker: str) -> str:
    if any(tok in blocker for tok in _BINDING_TOKENS):
        return "BINDING"
    if any(tok in blocker for tok in _SCOPE_GATE_TOKENS):
        return "SCOPE_GATE"
    if any(tok in blocker for tok in _SCOPE_EXPANSION_TOKENS):
        return "SCOPE_EXPANSION"
    return "OTHER"


def evaluate(root: Path) -> dict[str, Any]:
    basis = _load(root)
    open_domain = _open_domain_contracts(root)
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
        other = sum(x == "OTHER" for x in classes)
        is_open_domain = bid in open_domain
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

        # Lower score closes sooner. For canonically open-domain matched routes,
        # synthetic whole-scope expansion is not a valid prequalification target.
        # Route those to matched-protocol freeze/comparator resolution instead of
        # rewarding workers for generating ever-larger synthetic populations.
        effective_expansion = 0 if is_open_domain else expansion
        score = (
            effective_expansion * 100
            + other * 50
            + gate * 10
            + binding
            - min(leverage, 4) * 3
            - (8 if preflight else 0)
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
                "other": other,
            },
            "independent_or_information_safe_preflight_present": preflight,
            "portfolio_leverage": leverage,
            "proof_route_class": "OPEN_DOMAIN_MATCHED" if is_open_domain else "FINITE_OR_FORMAL",
            "priority_score": score,
            "next_action_class": (
                "FREEZE_MATCHED_PROTOCOL_AND_RESOLVE_COMPARATOR_ACCESS"
                if is_open_domain
                else (
                    "FREEZE_BINDING_AND_ACCEPTANCE"
                    if expansion == 0 and other == 0 and (binding or gate)
                    else "CLOSE_SCOPE_EQUIVALENCE_THEN_FREEZE_BINDING"
                )
            ),
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
        "queue": queue,
        "top_priority_behavior_id": queue[0]["behavior_id"] if queue else None,
        "errors": sorted(set(errors)),
        "rule": (
            "SCHEDULER_ONLY__NO_CAPABILITY_CREDIT__NO_TERMINAL_EXECUTION_AUTHORITY__"
            "OPEN_DOMAIN_MATCHED_ROUTES_MUST_NOT_BE_PROMOTED_BY_FINITE_SYNTHETIC_SCOPE_SUPERSET__"
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
