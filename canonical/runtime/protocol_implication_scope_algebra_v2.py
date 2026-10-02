"""Scope-safe fail-closed implication algebra for normalized acceptance protocols.

V2 preserves V1 atom/metric implication semantics and adds an explicit scope firewall:
a witness cannot imply a target unless an independently verified scope relation proves
that the witness scope is exactly the target scope or a superset of it.

The compiler never infers scope from names, prose, family labels, or atom overlap.
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA_V2"


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


def _scope_relation(doc: Mapping[str, Any], target_scope: str, witness_scope: str) -> tuple[str | None, str | None, str | None]:
    rows = doc.get("verified_scope_relations", [])
    if not isinstance(rows, list):
        return None, None, "SCOPE_RELATIONS_INVALID"
    admissible: list[tuple[str, str]] = []
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            return None, None, f"SCOPE_RELATION_{i}_INVALID"
        if row.get("verified") is not True or row.get("independent") is not True:
            return None, None, f"SCOPE_RELATION_{i}_NOT_INDEPENDENTLY_VERIFIED"
        source = row.get("witness_scope")
        target = row.get("target_scope")
        relation = row.get("relation")
        receipt = row.get("receipt")
        if (
            not isinstance(source, str) or not source
            or not isinstance(target, str) or not target
            or relation not in {"EXACT", "SUPERSET", "SUBSET", "DISJOINT", "UNKNOWN"}
            or not isinstance(receipt, str) or not receipt
        ):
            return None, None, f"SCOPE_RELATION_{i}_INVALID"
        if source == witness_scope and target == target_scope and relation in {"EXACT", "SUPERSET"}:
            admissible.append((relation, receipt))
    if not admissible:
        return None, None, None
    # EXACT is stronger/more precise than SUPERSET when both are independently attested.
    admissible.sort(key=lambda x: (0 if x[0] == "EXACT" else 1, x[1]))
    relation, receipt = admissible[0]
    return relation, receipt, None


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

    target_scope = target.get("scope_ref")
    witness_scope = witness.get("scope_ref")
    if not isinstance(target_scope, str) or not target_scope:
        return _fail("TARGET_SCOPE_REF_REQUIRED")
    if not isinstance(witness_scope, str) or not witness_scope:
        return _fail("WITNESS_SCOPE_REF_REQUIRED")

    scope_relation, scope_receipt, scope_error = _scope_relation(doc, target_scope, witness_scope)
    if scope_error:
        return _fail(scope_error)

    target_atoms = _string_set(target.get("required_atoms"))
    witness_atoms = _string_set(witness.get("proved_atoms"))
    if target_atoms is None or witness_atoms is None:
        return _fail("NORMALIZED_ATOMS_INVALID")

    edges: list[tuple[set[str], set[str], str]] = []
    for i, row in enumerate(implications):
        if not isinstance(row, Mapping) or row.get("verified") is not True or row.get("independent") is not True:
            return _fail(f"IMPLICATION_{i}_NOT_INDEPENDENTLY_VERIFIED")
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

    scope_pass = scope_relation in {"EXACT", "SUPERSET"}
    implies = scope_pass and not missing_atoms and metrics_pass

    if not scope_pass:
        status = "TARGET_SCOPE_NOT_COVERED"
        relation = None
    elif implies:
        relation = "EXACT" if scope_relation == "EXACT" and closure == target_atoms and not used_receipts else "PROVEN_STRONGER"
        status = "PASS"
    else:
        relation = scope_relation
        status = "TARGET_NOT_IMPLIED"

    return {
        "schema": SCHEMA,
        "status": status,
        "errors": [],
        "implies_target": implies,
        "candidate_scope_relation": relation,
        "verified_scope_relation": scope_relation,
        "verified_scope_relation_receipt": scope_receipt,
        "verified_scope_relation_receipt": scope_receipt,
        "target_scope_ref": target_scope,
        "witness_scope_ref": witness_scope,
        "target_required_atoms": sorted(target_atoms),
        "witness_direct_atoms": sorted(witness_atoms),
        "witness_closure_atoms": sorted(closure),
        "missing_atoms": missing_atoms,
        "metric_results": metric_results,
        "implication_receipts_used": sorted(used_receipts),
        "rule": (
            "NO_SCOPE_FROM_NAMES_OR_PROSE__WITNESS_SCOPE_MUST_HAVE_AN_INDEPENDENT_EXACT_OR_SUPERSET_RELATION__"
            "ATOMS_AND_METRICS_STILL_REQUIRE_NORMALIZED_VERIFIED_INPUTS__ZERO_CREDIT"
        ),
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "new_reality_units_consumed": 0,
    }
