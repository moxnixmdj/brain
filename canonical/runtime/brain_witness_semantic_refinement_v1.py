"""Fail-closed Brain witness semantic refinement normalizer.

This runtime does not infer semantics from raw text and does not grant acceptance credit.
It converts only independently verified, source-traceable semantic bindings and metric
bounds into the exact witness shape consumed by protocol_implication_scope_algebra_v1.

Every semantic atom must carry its own semantic-binding verification receipt. Merely
sharing words with a target atom is never sufficient.
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_EXECUTABLE_SEMANTIC_REFINEMENT_V1"


def _nonempty(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _finite(v: Any) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    x = float(v)
    return x if isfinite(x) else None


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "normalized_witness": None,
        "direct_target_coverage": False,
        "missing_atoms": [],
        "missing_metrics": [],
        "semantic_binding_receipts": [],
        "metric_binding_receipts": [],
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def evaluate(doc: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, Mapping):
        return _fail("INPUT_NOT_OBJECT")

    target = doc.get("target")
    claims = doc.get("witness_claims", [])
    metrics = doc.get("metric_bounds", [])
    scope_id = doc.get("scope_id")

    if not isinstance(target, Mapping):
        return _fail("TARGET_REQUIRED")
    if not _nonempty(target.get("predicate_id")):
        return _fail("TARGET_PREDICATE_ID_REQUIRED")
    if not _nonempty(scope_id):
        return _fail("SCOPE_ID_REQUIRED")
    if not isinstance(claims, list) or not isinstance(metrics, list):
        return _fail("CLAIMS_OR_METRICS_NOT_LIST")

    required_atoms = target.get("required_atoms", [])
    metric_requirements = target.get("metric_requirements", [])
    if (
        not isinstance(required_atoms, list)
        or any(not _nonempty(x) for x in required_atoms)
        or len(required_atoms) != len(set(required_atoms))
    ):
        return _fail("TARGET_ATOMS_INVALID")
    if not isinstance(metric_requirements, list):
        return _fail("TARGET_METRICS_INVALID")

    proved_atoms: set[str] = set()
    semantic_receipts: set[str] = set()

    for i, row in enumerate(claims):
        if not isinstance(row, Mapping):
            return _fail(f"CLAIM_{i}_INVALID")
        atom = row.get("atom")
        receipt = row.get("receipt")
        binding_receipt = row.get("semantic_binding_receipt")
        if not _nonempty(atom):
            return _fail(f"CLAIM_{i}_ATOM_REQUIRED")
        if not _nonempty(receipt) or not _nonempty(binding_receipt):
            return _fail(f"CLAIM_{i}_RECEIPTS_REQUIRED")
        if row.get("scope_id") != scope_id:
            return _fail(f"CLAIM_{i}_SCOPE_MISMATCH")
        for flag in (
            "verified",
            "independent",
            "contamination_clean",
            "source_traceable",
            "acceptance_scoped",
            "semantic_binding_verified",
        ):
            if row.get(flag) is not True:
                return _fail(f"CLAIM_{i}_{flag.upper()}_REQUIRED")
        proved_atoms.add(str(atom))
        semantic_receipts.add(str(binding_receipt))

    metric_bounds: dict[str, dict[str, float]] = {}
    metric_receipts: set[str] = set()
    seen_metrics: set[str] = set()

    for i, row in enumerate(metrics):
        if not isinstance(row, Mapping):
            return _fail(f"METRIC_{i}_INVALID")
        metric = row.get("metric")
        receipt = row.get("receipt")
        binding_receipt = row.get("semantic_binding_receipt")
        if not _nonempty(metric):
            return _fail(f"METRIC_{i}_NAME_REQUIRED")
        metric = str(metric)
        if metric in seen_metrics:
            return _fail(f"METRIC_DUPLICATE:{metric}")
        seen_metrics.add(metric)
        if not _nonempty(receipt) or not _nonempty(binding_receipt):
            return _fail(f"METRIC_{i}_RECEIPTS_REQUIRED")
        if row.get("scope_id") != scope_id:
            return _fail(f"METRIC_{i}_SCOPE_MISMATCH")
        for flag in (
            "verified",
            "independent",
            "contamination_clean",
            "source_traceable",
            "acceptance_scoped",
            "semantic_binding_verified",
        ):
            if row.get(flag) is not True:
                return _fail(f"METRIC_{i}_{flag.upper()}_REQUIRED")
        bound: dict[str, float] = {}
        if "lower" in row:
            v = _finite(row.get("lower"))
            if v is None:
                return _fail(f"METRIC_{i}_LOWER_INVALID")
            bound["lower"] = v
        if "upper" in row:
            v = _finite(row.get("upper"))
            if v is None:
                return _fail(f"METRIC_{i}_UPPER_INVALID")
            bound["upper"] = v
        if not bound:
            return _fail(f"METRIC_{i}_BOUND_REQUIRED")
        if "lower" in bound and "upper" in bound and bound["lower"] > bound["upper"]:
            return _fail(f"METRIC_{i}_BOUND_INCONSISTENT")
        metric_bounds[metric] = bound
        metric_receipts.add(str(binding_receipt))

    missing_atoms = sorted(set(required_atoms) - proved_atoms)
    missing_metrics: list[str] = []

    for i, req in enumerate(metric_requirements):
        if not isinstance(req, Mapping):
            return _fail(f"TARGET_METRIC_{i}_INVALID")
        metric = req.get("metric")
        direction = req.get("direction")
        threshold = _finite(req.get("threshold"))
        if not _nonempty(metric) or direction not in {"higher", "lower"} or threshold is None:
            return _fail(f"TARGET_METRIC_{i}_INVALID")
        bound = metric_bounds.get(str(metric))
        if bound is None:
            missing_metrics.append(str(metric))
            continue
        key = "lower" if direction == "higher" else "upper"
        if key not in bound:
            missing_metrics.append(str(metric))

    normalized = {
        "verified": True,
        "independent": True,
        "contamination_clean": True,
        "scope_id": str(scope_id),
        "proved_atoms": sorted(proved_atoms),
        "metric_bounds": {k: metric_bounds[k] for k in sorted(metric_bounds)},
    }

    direct = not missing_atoms and not missing_metrics

    return {
        "schema": SCHEMA,
        "status": "NORMALIZED_WITNESS_READY" if normalized["proved_atoms"] or normalized["metric_bounds"] else "NO_ADMISSIBLE_WITNESS_FACTS",
        "errors": [],
        "target_predicate_id": str(target["predicate_id"]),
        "scope_id": str(scope_id),
        "normalized_witness": normalized,
        "direct_target_coverage": direct,
        "missing_atoms": missing_atoms,
        "missing_metrics": sorted(set(missing_metrics)),
        "semantic_binding_receipts": sorted(semantic_receipts),
        "metric_binding_receipts": sorted(metric_receipts),
        "rule": (
            "ONLY_INDEPENDENTLY_VERIFIED_SOURCE_TRACEABLE_ACCEPTANCE_SCOPED_SEMANTIC_BINDINGS_"
            "ENTER_NORMALIZED_WITNESS__NO_LEXICAL_OR_ANALOGICAL_SEMANTIC_INFERENCE"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
