"""Fail-closed implication algebra for normalized acceptance protocols.

This compiler replaces hand-authored "PROVEN_STRONGER" assertions only after both
the target protocol and candidate witness have been normalized into explicit,
content-addressed atoms and metric bounds. It does not perform semantic
normalization itself and therefore cannot manufacture scope equivalence.

Only independently verified implication edges are propagated.
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA_V1"


def _finite(v: Any) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    x = float(v)
    return x if isfinite(x) else None


def _string_set(v: Any) -> set[str] | None:
    if not isinstance(v, list):
        return None
    if any(not isinstance(x, str) or not x for x in v):
        return None
    if len(v) != len(set(v)):
        return None
    return set(v)


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "implies_target": False,
        "candidate_scope_relation": None,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "new_reality_units_consumed": 0,
    }


def evaluate(doc: Mapping[str, Any]) -> dict[str, Any]:
    target = doc.get("target")
    witness = doc.get("witness")
    implications = doc.get("verified_implications", [])
    if not isinstance(target, Mapping) or not isinstance(witness, Mapping):
        return _fail("TARGET_AND_WITNESS_REQUIRED")
    if not isinstance(implications, list):
        return _fail("IMPLICATIONS_INVALID")

    for flag in ("verified", "independent", "contamination_clean"):
        if witness.get(flag) is not True:
            return _fail(f"WITNESS_{flag.upper()}_REQUIRED")

    target_atoms = _string_set(target.get("required_atoms"))
    witness_atoms = _string_set(witness.get("proved_atoms"))
    if target_atoms is None or witness_atoms is None:
        return _fail("NORMALIZED_ATOMS_INVALID")

    edges: list[tuple[set[str], set[str], str]] = []
    for i, row in enumerate(implications):
        if not isinstance(row, Mapping) or row.get("verified") is not True:
            return _fail(f"IMPLICATION_{i}_NOT_VERIFIED")
        antecedent = _string_set(row.get("if_all"))
        consequent = _string_set(row.get("then"))
        receipt = row.get("receipt")
        if antecedent is None or consequent is None or not consequent:
            return _fail(f"IMPLICATION_{i}_INVALID")
        if not isinstance(receipt, str) or not receipt:
            return _fail(f"IMPLICATION_{i}_RECEIPT_REQUIRED")
        edges.append((antecedent, consequent, receipt))

    closure = set(witness_atoms)
    used_receipts: set[str] = set()
    changed = True
    while changed:
        changed = False
        for antecedent, consequent, receipt in edges:
            if antecedent <= closure and not consequent <= closure:
                closure.update(consequent)
                used_receipts.add(receipt)
                changed = True

    missing_atoms = sorted(target_atoms - closure)

    target_metrics = target.get("metric_requirements", [])
    witness_bounds = witness.get("metric_bounds", {})
    if not isinstance(target_metrics, list) or not isinstance(witness_bounds, Mapping):
        return _fail("METRIC_NORMALIZATION_INVALID")

    metric_results = []
    metrics_pass = True
    for i, req in enumerate(target_metrics):
        if not isinstance(req, Mapping):
            return _fail(f"METRIC_REQUIREMENT_{i}_INVALID")
        metric = req.get("metric")
        direction = req.get("direction")
        threshold = _finite(req.get("threshold"))
        if not isinstance(metric, str) or not metric or direction not in {"higher", "lower"} or threshold is None:
            return _fail(f"METRIC_REQUIREMENT_{i}_INVALID")
        bound = witness_bounds.get(metric)
        if not isinstance(bound, Mapping):
            metric_results.append({"metric": metric, "pass": False, "reason": "BOUND_MISSING"})
            metrics_pass = False
            continue
        key = "lower" if direction == "higher" else "upper"
        value = _finite(bound.get(key))
        passed = value is not None and (value >= threshold if direction == "higher" else value <= threshold)
        if not passed:
            metrics_pass = False
        metric_results.append({
            "metric": metric,
            "direction": direction,
            "threshold": threshold,
            "witness_bound_kind": key,
            "witness_bound": value,
            "pass": passed,
        })

    implies = not missing_atoms and metrics_pass
    relation = None
    if implies:
        relation = "EXACT" if closure == target_atoms and not used_receipts else "PROVEN_STRONGER"

    return {
        "schema": SCHEMA,
        "status": "PASS" if implies else "TARGET_NOT_IMPLIED",
        "errors": [],
        "implies_target": implies,
        "candidate_scope_relation": relation,
        "target_required_atoms": sorted(target_atoms),
        "witness_direct_atoms": sorted(witness_atoms),
        "witness_closure_atoms": sorted(closure),
        "missing_atoms": missing_atoms,
        "metric_results": metric_results,
        "implication_receipts_used": sorted(used_receipts),
        "rule": (
            "SCOPE_RELATION_IS_DERIVED_ONLY_FROM_NORMALIZED_ATOMS_VERIFIED_IMPLICATIONS_"
            "AND_METRIC_BOUNDS__SEMANTIC_NORMALIZATION_REMAINS_SEPARATE_AND_FAIL_CLOSED"
        ),
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "new_reality_units_consumed": 0,
    }
