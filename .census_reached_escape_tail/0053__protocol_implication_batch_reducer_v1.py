"""Batch the normalized witness/target surface through implication algebra.

Representation closure is not semantic closure. This reducer runs every
witness/target pair through the fail-closed algebra and exposes the exact
remaining scope/atom/metric holes. It cannot manufacture bindings or acceptance credit.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.protocol_implication_scope_algebra_v2 import evaluate as evaluate_pair
from canonical.runtime.witness_target_binding_totalizer_v1 import totalize

ROOT = Path(__file__).resolve().parents[2]
TARGETS = ROOT / "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json"
WITNESSES = ROOT / "canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json"
CONTAMINATION = ROOT / "canonical/verification/OPUS55_BRAIN_WITNESS_CONTAMINATION_ADMISSIBILITY_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"

SCHEMA = "PROJECT_BRAIN_PROTOCOL_IMPLICATION_BATCH_REDUCTION_V1"


def reduce_batch(
    target_doc: Mapping[str, Any],
    witness_doc: Mapping[str, Any],
    contamination_doc: Mapping[str, Any],
) -> dict[str, Any]:
    ledger = totalize(target_doc, witness_doc)
    if ledger.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["BINDING_SURFACE_NOT_TOTALIZED"] + list(ledger.get("errors", [])),
            "closed_target_count": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "new_reality_units_consumed": 0,
        }

    if contamination_doc.get("contamination_admissibility_verified") is not True:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["CONTAMINATION_ADMISSIBILITY_NOT_INDEPENDENTLY_VERIFIED"],
            "closed_target_count": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "new_reality_units_consumed": 0,
        }

    targets = target_doc["targets"]
    witnesses = witness_doc["witnesses"]
    witness_normalization_verified = witness_doc.get("witness_normalization_verified") is True

    pair_results: list[dict[str, Any]] = []
    target_results: list[dict[str, Any]] = []

    for t in targets:
        required_atoms = [row["atom"] for row in t["atom_sources"]]
        metric_requirements = [
            {
                "metric": row["metric"],
                "direction": row["direction"],
                "threshold": row["threshold"],
            }
            for row in t["metric_requirement_sources"]
        ]
        per_target = []
        for w in witnesses:
            candidate = {
                "target": {
                    "scope_ref": "opus55://target/" + t["predicate_id"],
                    "required_atoms": required_atoms,
                    "metric_requirements": metric_requirements,
                },
                "witness": {
                    "scope_ref": "brain://witness/" + w["witness_id"],
                    "verified": witness_normalization_verified,
                    "independent": w.get("independent_or_objective") is True,
                    "contamination_clean": True,
                    "proved_atoms": list(w.get("normalized_target_atoms", [])),
                    "metric_bounds": dict(w.get("normalized_metric_bounds", {})),
                },
                "verified_implications": list(w.get("semantic_implications", [])),
                # Scope-safe v2 forbids this batch layer from inventing a relation.
                # Independently verified EXACT/SUPERSET relations must be injected
                # by a separate content-addressed binding stage.
                "verified_scope_relations": [],
            }
            verdict = evaluate_pair(candidate)
            row = {
                "target_predicate_id": t["predicate_id"],
                "witness_id": w["witness_id"],
                "status": verdict["status"],
                "implies_target": verdict["implies_target"],
                "missing_atoms": verdict.get("missing_atoms", []),
                "metric_results": verdict.get("metric_results", []),
                "candidate_scope_relation": verdict.get("candidate_scope_relation"),
                "scope_relation_missing": verdict.get("status") == "TARGET_SCOPE_NOT_COVERED",
            }
            pair_results.append(row)
            per_target.append(row)

        implied = [r for r in per_target if r["implies_target"]]
        best = min(
            per_target,
            key=lambda r: (
                (1 if r["scope_relation_missing"] else 0)
                + len(r["missing_atoms"])
                + sum(1 for m in r["metric_results"] if not m.get("pass")),
                r["witness_id"],
            ),
        )
        target_results.append({
            "predicate_id": t["predicate_id"],
            "implied": bool(implied),
            "implying_witness_ids": sorted(r["witness_id"] for r in implied),
            "best_current_witness_id": best["witness_id"],
            "best_current_scope_relation_missing": best["scope_relation_missing"],
            "best_current_missing_atoms": best["missing_atoms"],
            "best_current_failed_metrics": [
                m["metric"] for m in best["metric_results"] if not m.get("pass")
            ],
        })

    closed = sum(1 for t in target_results if t["implied"])
    return {
        "schema": SCHEMA,
        "status": "PASS__ALL_PAIRS_EVALUATED__RESIDUAL_EXPLICIT__ZERO_CREDIT",
        "pair_count": len(pair_results),
        "target_count": len(target_results),
        "witness_count": len(witnesses),
        "closed_target_count": closed,
        "residual_target_count": len(target_results) - closed,
        "target_results": target_results,
        "pair_results": pair_results,
        "rule": (
            "SCOPE_SAFE_V2_ONLY__BATCH_EXECUTION_MAY_EXPOSE_TARGET_NOT_IMPLIED_WITH_EXPLICIT_HOLES__"
            "NO_SCOPE_RELATION_IS_INFERRED_OR_INJECTED_BY_THIS_LAYER__"
            "ONLY_PAIR_ALGEBRA_PASS_WITH_AN_INDEPENDENT_EXACT_OR_SUPERSET_SCOPE_RECEIPT_CAN_MARK_A_TARGET_IMPLIED__"
            "NO_ACCEPTANCE_PROMOTION_FROM_THIS_REDUCER"
        ),
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "new_reality_units_consumed": 0,
        "errors": [],
    }


def main() -> int:
    out = reduce_batch(
        json.loads(TARGETS.read_text(encoding="utf-8")),
        json.loads(WITNESSES.read_text(encoding="utf-8")),
        json.loads(CONTAMINATION.read_text(encoding="utf-8")),
    )
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
