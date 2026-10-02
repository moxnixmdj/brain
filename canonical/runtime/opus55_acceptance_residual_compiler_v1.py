"""Fail-closed predicate compiler for the 17 open Project Brain Opus 5.5 acceptance residuals.

This kernel does not award capability credit. It turns frozen family protocols into atomic
proof predicates, binds only content-addressed evidence, issues blocker certificates for
unavailable matched comparisons, and authorizes only actions whose result can change the
terminal acceptance state.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

EXPECTED_RESIDUAL_FAMILY_COUNT = 17
VALID_STATES = {"OPEN", "PROVED", "REFUTED", "EXTERNAL_BLOCKED"}
VALID_KINDS = {
    "PUBLIC_FIXED_BAR",
    "ABSOLUTE_CEILING",
    "DIRECT_SCOPE_AUDIT",
    "INVARIANT",
    "DEPENDENCY_PROOF",
    "MATCHED_NONINFERIORITY",
    "MATCHED_SCOPE_AUDIT",
}
MATCHED_KINDS = {"MATCHED_NONINFERIORITY", "MATCHED_SCOPE_AUDIT"}
PUBLIC_KINDS = {"PUBLIC_FIXED_BAR"}
DIRECT_KINDS = {"ABSOLUTE_CEILING", "DIRECT_SCOPE_AUDIT", "INVARIANT", "DEPENDENCY_PROOF"}
PROOF_KINDS = {
    "RECEIPT",
    "PUBLIC_BAR_RESULT",
    "DIRECT_ORACLE",
    "ABSOLUTE_CEILING",
    "BOUND_DOMINANCE",
    "MATCHED_COMPARATOR",
}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_proved_claim(pid: str, claim: Mapping[str, Any], errors: list[str]) -> None:
    proof_kind = claim.get("proof_kind")
    if proof_kind not in PROOF_KINDS:
        errors.append(f"INVALID_PROOF_KIND:{pid}")
        return
    if claim.get("independent_or_objective") is not True:
        errors.append(f"NONINDEPENDENT_EVIDENCE:{pid}")
    if claim.get("scope_complete") is not True:
        errors.append(f"INCOMPLETE_SCOPE_EVIDENCE:{pid}")

    if proof_kind == "PUBLIC_BAR_RESULT":
        measured = claim.get("measured_value")
        threshold = claim.get("threshold")
        if not (_is_number(measured) and _is_number(threshold) and measured >= threshold):
            errors.append(f"PUBLIC_BAR_NOT_PROVED:{pid}")

    elif proof_kind == "ABSOLUTE_CEILING":
        value = claim.get("brain_value")
        ceiling = claim.get("objective_ceiling_value")
        if claim.get("objective_ceiling") is not True:
            errors.append(f"OBJECTIVE_CEILING_NOT_ESTABLISHED:{pid}")
        if not (_is_number(value) and _is_number(ceiling) and value == ceiling):
            errors.append(f"CEILING_NOT_REACHED:{pid}")

    elif proof_kind == "BOUND_DOMINANCE":
        brain_lower = claim.get("brain_lower_bound")
        opus_upper = claim.get("opus_upper_bound")
        if not (_is_number(brain_lower) and _is_number(opus_upper) and brain_lower >= opus_upper):
            errors.append(f"BOUND_DOMINANCE_NOT_PROVED:{pid}")

    elif proof_kind == "MATCHED_COMPARATOR":
        brain_lower = claim.get("brain_lower_bound")
        opus_upper = claim.get("opus_upper_bound")
        if claim.get("same_frozen_scope") is not True:
            errors.append(f"MATCHED_SCOPE_NOT_IDENTICAL:{pid}")
        if not (_is_number(brain_lower) and _is_number(opus_upper) and brain_lower >= opus_upper):
            errors.append(f"MATCHED_NONINFERIORITY_NOT_PROVED:{pid}")


def evaluate(
    registry: Mapping[str, Any],
    evidence: Mapping[str, Any],
    comparator: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    rows = registry.get("predicates")
    if not isinstance(rows, list):
        return {
            "schema": "PROJECT_BRAIN_OPUS55_ACCEPTANCE_RESIDUAL_COMPILER_VERDICT_V1",
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["PREDICATE_REGISTRY_MISSING"],
            "terminal_promotion_allowed": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    by_id: dict[str, Mapping[str, Any]] = {}
    families: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            errors.append("INVALID_PREDICATE_ROW")
            continue
        pid = row.get("id")
        family = row.get("family")
        kind = row.get("kind")
        if not isinstance(pid, str) or not pid:
            errors.append("PREDICATE_ID_INVALID")
            continue
        if pid in by_id:
            errors.append(f"DUPLICATE_PREDICATE_ID:{pid}")
        by_id[pid] = row
        if not isinstance(family, str) or not family:
            errors.append(f"PREDICATE_FAMILY_INVALID:{pid}")
        else:
            families.add(family)
        if kind not in VALID_KINDS:
            errors.append(f"PREDICATE_KIND_INVALID:{pid}")

    declared_families = registry.get("residual_families")
    if not isinstance(declared_families, list) or set(declared_families) != families:
        errors.append("RESIDUAL_FAMILY_SET_MISMATCH")
    if len(families) != EXPECTED_RESIDUAL_FAMILY_COUNT:
        errors.append("RESIDUAL_FAMILY_COUNT_INVALID")

    claims = evidence.get("claims", [])
    if not isinstance(claims, list):
        errors.append("EVIDENCE_CLAIMS_INVALID")
        claims = []

    claim_by_id: dict[str, Mapping[str, Any]] = {}
    for claim in claims:
        if not isinstance(claim, Mapping):
            errors.append("INVALID_EVIDENCE_CLAIM")
            continue
        pid = claim.get("predicate_id")
        if pid not in by_id:
            errors.append(f"EVIDENCE_FOR_UNKNOWN_PREDICATE:{pid}")
            continue
        if pid in claim_by_id:
            errors.append(f"DUPLICATE_EVIDENCE_CLAIM:{pid}")
            continue
        state = claim.get("state")
        if state not in VALID_STATES:
            errors.append(f"INVALID_EVIDENCE_STATE:{pid}")
            continue
        if state in {"PROVED", "REFUTED"}:
            if not claim.get("source_path") or not claim.get("source_sha"):
                errors.append(f"UNBOUND_EVIDENCE:{pid}")
                continue
            if claim.get("independent_or_objective") is not True:
                errors.append(f"NONINDEPENDENT_EVIDENCE:{pid}")
                continue
        if state == "PROVED":
            before = len(errors)
            _validate_proved_claim(pid, claim, errors)
            if len(errors) != before:
                continue
        if state == "EXTERNAL_BLOCKED":
            if not claim.get("blocker") or not claim.get("discharge_condition"):
                errors.append(f"BLOCKER_CERTIFICATE_INCOMPLETE:{pid}")
                continue
        claim_by_id[pid] = claim

    comparator_available = comparator.get("exact_opus55_zero_incremental_route") is True

    predicate_rows: list[dict[str, Any]] = []
    family_states: dict[str, list[str]] = {}
    candidate_actions: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []

    for pid, row in sorted(by_id.items()):
        claim = claim_by_id.get(pid)
        state = claim.get("state") if claim else "OPEN"
        kind = row.get("kind")
        family = row.get("family")

        if state == "OPEN" and kind in MATCHED_KINDS and not comparator_available:
            state = "EXTERNAL_BLOCKED"
            blockers.append(
                {
                    "predicate_id": pid,
                    "family": family,
                    "reason": "EXACT_OPUS55_ZERO_INCREMENTAL_COMPARATOR_UNAVAILABLE",
                    "discharge_condition": (
                        "ADMISSIBLE_CASE_LEVEL_OPUS55_COMPARATOR_OR_SCOPE_COMPLETE_"
                        "STRONGER_PROOF_SUCH_AS_OBJECTIVE_CEILING_OR_BOUND_DOMINANCE"
                    ),
                }
            )
        elif state == "OPEN":
            action_class = (
                "RUN_PUBLIC_FIXED_BAR"
                if kind in PUBLIC_KINDS
                else "RUN_DIRECT_ORACLE_OR_PROOF"
                if kind in DIRECT_KINDS
                else "RUN_MATCHED_NONINFERIORITY"
            )
            candidate_actions.append(
                {
                    "action_id": f"ACTION::{pid}",
                    "predicate_id": pid,
                    "family": family,
                    "action_class": action_class,
                    "verdict_changing": True,
                    "execution_authorized": True,
                    "authorization_basis": "OPEN_TERMINAL_ACCEPTANCE_PREDICATE",
                }
            )

        predicate_rows.append(
            {
                "predicate_id": pid,
                "family": family,
                "kind": kind,
                "state": state,
                "source_path": claim.get("source_path") if claim else None,
                "source_sha": claim.get("source_sha") if claim else None,
            }
        )
        family_states.setdefault(str(family), []).append(state)

    family_rows: list[dict[str, Any]] = []
    for family in sorted(family_states):
        states = family_states[family]
        if "REFUTED" in states:
            family_state = "REFUTED"
        elif all(s == "PROVED" for s in states):
            family_state = "PROVED"
        elif "EXTERNAL_BLOCKED" in states:
            family_state = "EXTERNAL_BLOCKED"
        else:
            family_state = "OPEN"
        family_rows.append(
            {
                "family": family,
                "state": family_state,
                "predicate_count": len(states),
                "proved": sum(s == "PROVED" for s in states),
                "open": sum(s == "OPEN" for s in states),
                "blocked": sum(s == "EXTERNAL_BLOCKED" for s in states),
                "refuted": sum(s == "REFUTED" for s in states),
            }
        )

    all_proved = (
        not errors
        and len(family_rows) == EXPECTED_RESIDUAL_FAMILY_COUNT
        and predicate_rows
        and all(row["state"] == "PROVED" for row in predicate_rows)
    )

    return {
        "schema": "PROJECT_BRAIN_OPUS55_ACCEPTANCE_RESIDUAL_COMPILER_VERDICT_V1",
        "status": "PASS__RESIDUAL_ZERO" if all_proved else "ACTIVE_FAIL_CLOSED",
        "pass": bool(all_proved),
        "errors": sorted(set(errors)),
        "predicate_count": len(predicate_rows),
        "family_count": len(family_rows),
        "proved_predicate_count": sum(r["state"] == "PROVED" for r in predicate_rows),
        "open_predicate_count": sum(r["state"] == "OPEN" for r in predicate_rows),
        "blocked_predicate_count": sum(r["state"] == "EXTERNAL_BLOCKED" for r in predicate_rows),
        "refuted_predicate_count": sum(r["state"] == "REFUTED" for r in predicate_rows),
        "families": family_rows,
        "predicates": predicate_rows,
        "candidate_actions": candidate_actions,
        "authorized_actions": candidate_actions,
        "blocker_certificates": blockers,
        "terminal_promotion_allowed": bool(all_proved),
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "rule": (
            "NO_ACTION_EXECUTION_UNLESS_ITS_RESULT_CAN_CHANGE_A_FROZEN_TERMINAL_ACCEPTANCE_PREDICATE__"
            "NO_FAMILY_PROMOTION_UNTIL_ALL_FAMILY_PREDICATES_ARE_PROVED__"
            "MATCHED_PREDICATES_WITHOUT_EXACT_ZERO_COST_COMPARATOR_FAIL_CLOSED_UNLESS_A_SCOPE_COMPLETE_STRONGER_PROOF_EXISTS"
        ),
    }


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("registry", type=Path)
    ap.add_argument("evidence", type=Path)
    ap.add_argument("comparator", type=Path)
    args = ap.parse_args()
    out = evaluate(_load(args.registry), _load(args.evidence), _load(args.comparator))
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not out["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
