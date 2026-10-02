"""Fail-closed proof transmutation compiler for Project Brain Opus 5.5 acceptance.

This module is scheduling/proof-routing authority only. It never grants capability or
family credit. It asks whether an OPEN frozen acceptance protocol can be satisfied by
a strictly stronger admissible proof route without weakening the protocol.

Allowed stronger routes:
1. universal proof over the complete frozen scope;
2. exhaustive finite proof over the complete frozen scope;
3. absolute dominance (Brain reaches a theoretical optimum, or Brain's conservative
   bound dominates an admissible target bound);
4. the protocol's own public fixed bar;
5. the protocol's own matched comparator.

Every closing witness must be verified, independent, contamination-clean, bind the
frozen protocol, cover the entire claimed protocol scope, and explicitly declare that
it closes the entire protocol. Behavioral-only evidence can never close ownership.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

PASS = "PASS"
OPEN = "DEFINED_RESULT_OPEN"

PROOF_PRIORITY = (
    "UNIVERSAL",
    "EXHAUSTIVE_FINITE",
    "ABSOLUTE_DOMINANCE",
    "PUBLIC_FIXED_BAR",
    "MATCHED_COMPARATOR",
)


def _truthy_bool(value: Any) -> bool:
    return value is True


def _scope_admissible(evidence: Mapping[str, Any]) -> bool:
    return evidence.get("scope_relation") in {"EXACT", "PROVEN_STRONGER"}


def _base_admissible(evidence: Mapping[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    if not _truthy_bool(evidence.get("verified")):
        failures.append("NOT_VERIFIED")
    if not _truthy_bool(evidence.get("independent")):
        failures.append("NOT_INDEPENDENT")
    if not _truthy_bool(evidence.get("contamination_clean")):
        failures.append("CONTAMINATION_NOT_CLEAN")
    if not _truthy_bool(evidence.get("binds_frozen_protocol")):
        failures.append("DOES_NOT_BIND_FROZEN_PROTOCOL")
    if not _scope_admissible(evidence):
        failures.append("SCOPE_NOT_EXACT_OR_PROVEN_STRONGER")
    if not _truthy_bool(evidence.get("closes_entire_protocol")):
        failures.append("DOES_NOT_CLOSE_ENTIRE_PROTOCOL")
    return not failures, failures


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _absolute_dominance(result: Mapping[str, Any]) -> tuple[bool, str]:
    direction = result.get("direction")
    if direction not in {"higher", "lower"}:
        return False, "DIRECTION_INVALID"

    if direction == "higher":
        brain_lb = _num(result.get("brain_lower_bound"))
        theoretical_ub = _num(result.get("theoretical_upper_bound"))
        target_ub = _num(result.get("target_upper_bound"))
        if brain_lb is None:
            return False, "BRAIN_LOWER_BOUND_MISSING"
        if theoretical_ub is not None and brain_lb >= theoretical_ub:
            return True, "THEORETICAL_CEILING_DOMINANCE"
        if target_ub is not None and brain_lb >= target_ub:
            return True, "TARGET_UPPER_BOUND_SQUEEZE"
        return False, "NO_HIGHER_IS_BETTER_DOMINANCE"

    brain_ub = _num(result.get("brain_upper_bound"))
    theoretical_lb = _num(result.get("theoretical_lower_bound"))
    target_lb = _num(result.get("target_lower_bound"))
    if brain_ub is None:
        return False, "BRAIN_UPPER_BOUND_MISSING"
    if theoretical_lb is not None and brain_ub <= theoretical_lb:
        return True, "THEORETICAL_FLOOR_DOMINANCE"
    if target_lb is not None and brain_ub <= target_lb:
        return True, "TARGET_LOWER_BOUND_SQUEEZE"
    return False, "NO_LOWER_IS_BETTER_DOMINANCE"


def _mode_pass(evidence: Mapping[str, Any]) -> tuple[bool, str]:
    mode = evidence.get("mode")
    result = evidence.get("result")
    if not isinstance(result, Mapping):
        return False, "RESULT_MISSING"

    if mode == "BEHAVIORAL_ONLY":
        return False, "BEHAVIORAL_ONLY_NEVER_CLOSES_OPUS55_ACCEPTANCE"
    if mode == "UNIVERSAL":
        ok = (
            _truthy_bool(result.get("all_admissible_inputs_proved"))
            and _truthy_bool(result.get("formal_completeness"))
        )
        return ok, "UNIVERSAL_COMPLETE" if ok else "UNIVERSAL_INCOMPLETE"
    if mode == "EXHAUSTIVE_FINITE":
        ok = (
            _truthy_bool(result.get("exhaustive"))
            and _truthy_bool(result.get("all_cases_pass"))
        )
        return ok, "EXHAUSTIVE_FINITE_COMPLETE" if ok else "EXHAUSTIVE_FINITE_INCOMPLETE"
    if mode == "ABSOLUTE_DOMINANCE":
        return _absolute_dominance(result)
    if mode == "PUBLIC_FIXED_BAR":
        ok = _truthy_bool(result.get("threshold_pass"))
        return ok, "PUBLIC_FIXED_BAR_PASS" if ok else "PUBLIC_FIXED_BAR_NOT_PASS"
    if mode == "MATCHED_COMPARATOR":
        ok = _truthy_bool(result.get("noninferiority_pass"))
        return ok, "MATCHED_NONINFERIORITY_PASS" if ok else "MATCHED_NONINFERIORITY_NOT_PASS"
    return False, "UNKNOWN_PROOF_MODE"


def _candidate_modes(protocol: Mapping[str, Any]) -> list[str]:
    modes = ["UNIVERSAL", "EXHAUSTIVE_FINITE", "ABSOLUTE_DOMINANCE"]
    proof_mode = str(protocol.get("proof_mode") or "")
    if "PUBLIC" in proof_mode or "BAR" in proof_mode:
        modes.append("PUBLIC_FIXED_BAR")
    if (
        "MATCHED" in proof_mode
        or "NONINFERIORITY" in proof_mode
        or "OSWORLD" in proof_mode
    ):
        modes.append("MATCHED_COMPARATOR")
    return modes


def evaluate(
    protocols_doc: Mapping[str, Any],
    evidence_doc: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    rows = protocols_doc.get("protocols")
    if not isinstance(rows, list):
        return {
            "schema": "PROJECT_BRAIN_ACCEPTANCE_PROOF_TRANSMUTATION_VERDICT_V1",
            "status": "FAIL_CLOSED",
            "errors": ["PROTOCOLS_NOT_LIST"],
            "families": [],
            "closed_family_count": 0,
            "open_family_count": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    evidence_rows = []
    if evidence_doc is not None:
        raw = evidence_doc.get("evidence")
        if raw is not None and not isinstance(raw, list):
            return {
                "schema": "PROJECT_BRAIN_ACCEPTANCE_PROOF_TRANSMUTATION_VERDICT_V1",
                "status": "FAIL_CLOSED",
                "errors": ["EVIDENCE_NOT_LIST"],
                "families": [],
                "closed_family_count": 0,
                "open_family_count": 0,
                "capability_credit_delta": 0,
                "family_credit_delta": 0,
            }
        evidence_rows = raw or []

    by_family: dict[str, list[Mapping[str, Any]]] = {}
    for item in evidence_rows:
        if isinstance(item, Mapping) and isinstance(item.get("family"), str):
            by_family.setdefault(item["family"], []).append(item)

    out_rows: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()

    for protocol in rows:
        if not isinstance(protocol, Mapping) or not isinstance(protocol.get("family"), str):
            errors.append("MALFORMED_PROTOCOL_ROW")
            continue
        family = protocol["family"]
        if family in seen:
            errors.append(f"DUPLICATE_PROTOCOL_FAMILY:{family}")
            continue
        seen.add(family)

        if protocol.get("status") == PASS:
            out_rows.append({
                "family": family,
                "input_status": PASS,
                "result_status": PASS,
                "closure_mode": "ALREADY_PASS",
                "witness_id": None,
                "candidate_transmutations": [],
                "rejections": [],
            })
            continue

        witnesses: list[dict[str, Any]] = []
        rejections: list[dict[str, Any]] = []
        for evidence in by_family.get(family, []):
            eid = evidence.get("id")
            mode = evidence.get("mode")
            base_ok, base_failures = _base_admissible(evidence)
            if not base_ok:
                rejections.append({
                    "evidence_id": eid,
                    "mode": mode,
                    "reasons": base_failures,
                })
                continue
            mode_ok, reason = _mode_pass(evidence)
            if not mode_ok:
                rejections.append({
                    "evidence_id": eid,
                    "mode": mode,
                    "reasons": [reason],
                })
                continue
            try:
                rank = PROOF_PRIORITY.index(str(mode))
            except ValueError:
                rank = len(PROOF_PRIORITY)
            witnesses.append({
                "evidence_id": eid,
                "mode": mode,
                "reason": reason,
                "rank": rank,
            })

        witnesses.sort(key=lambda x: (x["rank"], str(x["evidence_id"])))
        if witnesses:
            winner = witnesses[0]
            out_rows.append({
                "family": family,
                "input_status": protocol.get("status"),
                "result_status": PASS,
                "closure_mode": winner["mode"],
                "witness_id": winner["evidence_id"],
                "witness_reason": winner["reason"],
                "candidate_transmutations": _candidate_modes(protocol),
                "rejections": rejections,
            })
        else:
            out_rows.append({
                "family": family,
                "input_status": protocol.get("status"),
                "result_status": OPEN,
                "closure_mode": None,
                "witness_id": None,
                "candidate_transmutations": _candidate_modes(protocol),
                "rejections": rejections,
            })

    closed = sum(1 for r in out_rows if r["result_status"] == PASS)
    open_count = sum(1 for r in out_rows if r["result_status"] != PASS)
    return {
        "schema": "PROJECT_BRAIN_ACCEPTANCE_PROOF_TRANSMUTATION_VERDICT_V1",
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "family_count": len(out_rows),
        "closed_family_count": closed,
        "open_family_count": open_count,
        "families": out_rows,
        "rule": (
            "NO_ACCEPTANCE_PROMOTION_WITHOUT_FULL_FROZEN_SCOPE_WITNESS__"
            "UNIVERSAL_EXHAUSTIVE_OR_ABSOLUTE_DOMINANCE_MAY_SUPERSEDE_WEAKER_"
            "COMPARATOR_WORK_ONLY_WHEN_THE_WITNESS_BINDS_THE_ENTIRE_FROZEN_PROTOCOL"
        ),
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("protocols", type=Path)
    ap.add_argument("--evidence", type=Path)
    args = ap.parse_args()
    out = evaluate(_load(args.protocols), _load(args.evidence) if args.evidence else None)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
