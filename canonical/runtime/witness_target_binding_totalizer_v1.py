"""Totalize the Brain-witness -> normalized-target binding surface.

This closes a representation gate, not an acceptance predicate. Every current
witness/target pair is emitted, and every target atom/metric is either backed by
an independently verified explicit binding or recorded as missing.

The current witness catalog intentionally has zero semantic bindings, so the
correct live result is a complete ledger of holes. That is sufficient for the
implication algebra to run and return TARGET_NOT_IMPLIED instead of being
blocked before execution.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
TARGETS = ROOT / "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json"
WITNESSES = ROOT / "canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json"

SCHEMA = "PROJECT_BRAIN_WITNESS_TARGET_BINDING_TOTALIZATION_V1"


def _fail(errors: list[str]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "binding_surface_totalized": False,
        "semantic_implication_verified": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "new_reality_units_consumed": 0,
    }


def totalize(target_doc: Mapping[str, Any], witness_doc: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    targets = target_doc.get("targets")
    witnesses = witness_doc.get("witnesses")
    if not isinstance(targets, list) or not isinstance(witnesses, list):
        return _fail(["TARGETS_OR_WITNESSES_NOT_LIST"])

    normalized_targets: list[dict[str, Any]] = []
    all_target_atoms: set[str] = set()
    all_target_metrics: set[str] = set()

    for i, t in enumerate(targets):
        if not isinstance(t, Mapping) or not isinstance(t.get("predicate_id"), str):
            errors.append(f"TARGET_{i}_INVALID")
            continue
        atom_rows = t.get("atom_sources")
        metric_rows = t.get("metric_requirement_sources")
        if not isinstance(atom_rows, list) or not isinstance(metric_rows, list):
            errors.append(f"TARGET_{i}_PROVENANCE_INVALID")
            continue
        atoms = []
        for j, row in enumerate(atom_rows):
            atom = row.get("atom") if isinstance(row, Mapping) else None
            sources = row.get("sources") if isinstance(row, Mapping) else None
            if not isinstance(atom, str) or not atom or not isinstance(sources, list) or not sources:
                errors.append(f"TARGET_{i}_ATOM_{j}_INVALID")
                continue
            atoms.append(atom)
            all_target_atoms.add(atom)
        metrics = []
        for j, row in enumerate(metric_rows):
            metric = row.get("metric") if isinstance(row, Mapping) else None
            sources = row.get("sources") if isinstance(row, Mapping) else None
            if not isinstance(metric, str) or not metric or not isinstance(sources, list) or not sources:
                errors.append(f"TARGET_{i}_METRIC_{j}_INVALID")
                continue
            metrics.append(metric)
            all_target_metrics.add(metric)
        normalized_targets.append({
            "predicate_id": t["predicate_id"],
            "family": t.get("family"),
            "required_atoms": atoms,
            "required_metrics": metrics,
        })

    normalized_witnesses: list[dict[str, Any]] = []
    for i, w in enumerate(witnesses):
        if not isinstance(w, Mapping) or not isinstance(w.get("witness_id"), str):
            errors.append(f"WITNESS_{i}_INVALID")
            continue

        atoms = w.get("normalized_target_atoms", [])
        implications = w.get("semantic_implications", [])
        metric_bounds = w.get("normalized_metric_bounds", {})
        atom_receipts = w.get("target_atom_binding_receipts", {})
        metric_receipts = w.get("metric_binding_receipts", {})

        if not isinstance(atoms, list) or any(not isinstance(x, str) or not x for x in atoms):
            errors.append(f"WITNESS_{i}_ATOMS_INVALID")
            continue
        if not isinstance(implications, list):
            errors.append(f"WITNESS_{i}_IMPLICATIONS_INVALID")
            continue
        if not isinstance(metric_bounds, Mapping):
            errors.append(f"WITNESS_{i}_METRIC_BOUNDS_INVALID")
            continue
        if not isinstance(atom_receipts, Mapping) or not isinstance(metric_receipts, Mapping):
            errors.append(f"WITNESS_{i}_BINDING_RECEIPTS_INVALID")
            continue

        # V1 is deliberately a hole-totalizer only. Positive semantics require
        # a separate independently verified semantic-binding compiler, not a
        # receipt-shaped string smuggled into this representation pass.
        if atoms or metric_bounds or implications:
            errors.append(f"WITNESS_{i}_POSITIVE_SEMANTIC_BINDING_FORBIDDEN_IN_V1")

        # Defensive checks remain below so malformed positive assertions fail
        # with specific reasons too.
        for atom in atoms:
            if atom not in all_target_atoms:
                errors.append(f"WITNESS_{i}_ATOM_OUTSIDE_TARGET_VOCAB:{atom}")
            receipt = atom_receipts.get(atom)
            if not isinstance(receipt, str) or not receipt:
                errors.append(f"WITNESS_{i}_ATOM_BINDING_RECEIPT_MISSING:{atom}")
        for metric in metric_bounds:
            if metric not in all_target_metrics:
                errors.append(f"WITNESS_{i}_METRIC_OUTSIDE_TARGET_VOCAB:{metric}")
            receipt = metric_receipts.get(metric)
            if not isinstance(receipt, str) or not receipt:
                errors.append(f"WITNESS_{i}_METRIC_BINDING_RECEIPT_MISSING:{metric}")
        for j, edge in enumerate(implications):
            if not isinstance(edge, Mapping) or edge.get("verified") is not True or not isinstance(edge.get("receipt"), str):
                errors.append(f"WITNESS_{i}_SEMANTIC_EDGE_{j}_NOT_INDEPENDENTLY_VERIFIED")

        normalized_witnesses.append({
            "witness_id": w["witness_id"],
            "source_predicate_id": w.get("source_predicate_id"),
            "declared_bound_atoms": list(atoms),
            "declared_metric_bounds": dict(metric_bounds),
            "verified_implication_count": len(implications),
        })

    if errors:
        return _fail(errors)

    pairs: list[dict[str, Any]] = []
    direct_atom_binding_count = 0
    direct_metric_binding_count = 0
    for w in normalized_witnesses:
        witness_atoms = set(w["declared_bound_atoms"])
        witness_metrics = set(w["declared_metric_bounds"].keys())
        for t in normalized_targets:
            required_atoms = set(t["required_atoms"])
            required_metrics = set(t["required_metrics"])
            bound_atoms = sorted(required_atoms & witness_atoms)
            bound_metrics = sorted(required_metrics & witness_metrics)
            direct_atom_binding_count += len(bound_atoms)
            direct_metric_binding_count += len(bound_metrics)
            pairs.append({
                "witness_id": w["witness_id"],
                "target_predicate_id": t["predicate_id"],
                "bound_atoms": bound_atoms,
                "missing_atoms": sorted(required_atoms - witness_atoms),
                "bound_metrics": bound_metrics,
                "missing_metrics": sorted(required_metrics - witness_metrics),
            })

    expected_pairs = len(normalized_witnesses) * len(normalized_targets)
    if len(pairs) != expected_pairs:
        return _fail(["PAIR_TOTALIZATION_COUNT_MISMATCH"])

    return {
        "schema": SCHEMA,
        "status": "PASS__BINDING_SURFACE_TOTALIZED__EXPLICIT_HOLES_PRESERVED__ZERO_SEMANTIC_CREDIT",
        "pass": True,
        "binding_surface_totalized": True,
        "target_count": len(normalized_targets),
        "witness_count": len(normalized_witnesses),
        "pair_count": len(pairs),
        "target_atom_occurrence_count": sum(len(t["required_atoms"]) for t in normalized_targets),
        "target_metric_occurrence_count": sum(len(t["required_metrics"]) for t in normalized_targets),
        "direct_atom_binding_count": direct_atom_binding_count,
        "direct_metric_binding_count": direct_metric_binding_count,
        "pairs": pairs,
        "semantic_implication_verified": False,
        "rule": (
            "TOTALIZATION_PASS_MEANS_EVERY_BINDING_OR_HOLE_IS_EXPLICIT__"
            "IT_DOES_NOT_MEAN_ANY_TARGET_IS_IMPLIED__"
            "V1_FORBIDS_ALL_POSITIVE_SEMANTIC_BINDINGS__A_SEPARATE_INDEPENDENT_SEMANTIC_VERIFIER_IS_REQUIRED"
        ),
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "new_reality_units_consumed": 0,
        "errors": [],
    }


def main() -> int:
    target_doc = json.loads(TARGETS.read_text(encoding="utf-8"))
    witness_doc = json.loads(WITNESSES.read_text(encoding="utf-8"))
    out = totalize(target_doc, witness_doc)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
