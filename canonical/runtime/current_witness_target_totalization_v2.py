"""Current 8-target x 12-witness zero-reality totalization.

This is a fail-closed representation and implication cut over the *current*
independently verified target normalization V3 and witness normalization V2.
It proves only what follows from those exact normalized inputs:

- 8 live matched/scope targets
- 12 current proved witnesses
- 96 witness/target pairs
- zero declared positive semantic atom bindings
- zero declared metric bindings
- zero declared semantic implication edges
- therefore zero targets can be closed by direct reuse of the normalized
  witness catalog alone

It does NOT prove that no other semantic proof exists elsewhere in the repo.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
TARGETS = ROOT / "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json"
TARGET_VERIFY = ROOT / "canonical/verification/OPUS55_MATCHED_TARGET_NORMALIZATION_V3_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
WITNESSES = ROOT / "canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V2.json"
WITNESS_VERIFY = ROOT / "canonical/verification/OPUS55_BRAIN_WITNESS_NORMALIZATION_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"

SCHEMA = "PROJECT_BRAIN_CURRENT_WITNESS_TARGET_TOTALIZATION_V2"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "new_reality_units_consumed": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def totalize(
    target_doc: Mapping[str, Any],
    target_verify: Mapping[str, Any],
    witness_doc: Mapping[str, Any],
    witness_verify: Mapping[str, Any],
    *,
    target_blob_sha: str,
    witness_blob_sha: str,
) -> dict[str, Any]:
    errors: list[str] = []

    if not str(target_verify.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("TARGET_NORMALIZATION_NOT_INDEPENDENT_PASS")
    if not str(witness_verify.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("WITNESS_NORMALIZATION_NOT_INDEPENDENT_PASS")

    tv = target_verify.get("verified", {})
    wv = witness_verify.get("verified", {})
    if not isinstance(tv, Mapping) or tv.get("current_live_target_set_exact") is not True:
        errors.append("TARGET_SET_NOT_INDEPENDENTLY_VERIFIED_EXACT")
    if not isinstance(wv, Mapping) or wv.get("exact_all_and_only_proved_claims") is not True:
        errors.append("WITNESS_SET_NOT_INDEPENDENTLY_VERIFIED_EXACT")

    expected_target_sha = (
        target_verify.get("verified_subjects", {})
        .get("canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json")
    )
    expected_witness_sha = (
        witness_verify.get("exact_brain_blobs", {})
        .get("canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V2.json")
    )
    if expected_target_sha != target_blob_sha:
        errors.append("TARGET_NORMALIZATION_BLOB_DRIFT")
    if expected_witness_sha != witness_blob_sha:
        errors.append("WITNESS_NORMALIZATION_BLOB_DRIFT")

    targets = target_doc.get("targets")
    witnesses = witness_doc.get("witnesses")
    if not isinstance(targets, list):
        errors.append("TARGETS_NOT_LIST")
        targets = []
    if not isinstance(witnesses, list):
        errors.append("WITNESSES_NOT_LIST")
        witnesses = []

    if len(targets) != 8:
        errors.append(f"TARGET_COUNT_NOT_8:{len(targets)}")
    if len(witnesses) != 12:
        errors.append(f"WITNESS_COUNT_NOT_12:{len(witnesses)}")

    target_rows: list[dict[str, Any]] = []
    atom_occurrences = 0
    metric_occurrences = 0
    for i, target in enumerate(targets):
        if not isinstance(target, Mapping) or not isinstance(target.get("predicate_id"), str):
            errors.append(f"TARGET_{i}_INVALID")
            continue
        atom_rows = target.get("atom_sources")
        metric_rows = target.get("metric_requirement_sources")
        if not isinstance(atom_rows, list) or not isinstance(metric_rows, list):
            errors.append(f"TARGET_{i}_NORMALIZATION_INVALID")
            continue
        atoms = [r.get("atom") for r in atom_rows if isinstance(r, Mapping)]
        metrics = [r.get("metric") for r in metric_rows if isinstance(r, Mapping)]
        if any(not isinstance(x, str) or not x for x in atoms):
            errors.append(f"TARGET_{i}_ATOM_INVALID")
        if any(not isinstance(x, str) or not x for x in metrics):
            errors.append(f"TARGET_{i}_METRIC_INVALID")
        atom_occurrences += len(atoms)
        metric_occurrences += len(metrics)
        target_rows.append({
            "predicate_id": target["predicate_id"],
            "required_atoms": atoms,
            "required_metrics": metrics,
        })

    witness_rows: list[dict[str, Any]] = []
    positive_atom_bindings = 0
    positive_metric_bindings = 0
    positive_semantic_edges = 0
    for i, witness in enumerate(witnesses):
        if not isinstance(witness, Mapping) or not isinstance(witness.get("witness_id"), str):
            errors.append(f"WITNESS_{i}_INVALID")
            continue
        atoms = witness.get("normalized_target_atoms", [])
        metrics = witness.get("normalized_metric_bounds", {})
        edges = witness.get("semantic_implications", [])
        if not isinstance(atoms, list):
            errors.append(f"WITNESS_{i}_ATOMS_NOT_LIST")
            atoms = []
        if not isinstance(metrics, Mapping):
            errors.append(f"WITNESS_{i}_METRICS_NOT_MAPPING")
            metrics = {}
        if not isinstance(edges, list):
            errors.append(f"WITNESS_{i}_EDGES_NOT_LIST")
            edges = []
        positive_atom_bindings += len(atoms)
        positive_metric_bindings += len(metrics)
        positive_semantic_edges += len(edges)
        witness_rows.append({
            "witness_id": witness["witness_id"],
            "atoms": list(atoms),
            "metrics": dict(metrics),
            "semantic_edges": list(edges),
        })

    # The independent witness-normalization receipt explicitly verifies these
    # are all empty. Any drift is a hard failure, never silent extra credit.
    if positive_atom_bindings != 0:
        errors.append("POSITIVE_ATOM_BINDING_PRESENT")
    if positive_metric_bindings != 0:
        errors.append("POSITIVE_METRIC_BINDING_PRESENT")
    if positive_semantic_edges != 0:
        errors.append("POSITIVE_SEMANTIC_EDGE_PRESENT")

    if errors:
        return fail(*errors)

    pairs: list[dict[str, Any]] = []
    target_results: list[dict[str, Any]] = []
    for target in target_rows:
        for witness in witness_rows:
            pairs.append({
                "target_predicate_id": target["predicate_id"],
                "witness_id": witness["witness_id"],
                "direct_semantic_binding": False,
                "verified_scope_relation": False,
                "implies_target": False,
            })
        target_results.append({
            "predicate_id": target["predicate_id"],
            "closed_by_current_normalized_witness_reuse": False,
            "reason": "NO_POSITIVE_SEMANTIC_OR_METRIC_BINDING_AND_NO_VERIFIED_SCOPE_RELATION_IN_CURRENT_WITNESS_NORMALIZATION",
        })

    return {
        "schema": SCHEMA,
        "status": "PASS__CURRENT_8X12_SURFACE_TOTALIZED__ZERO_DIRECT_REUSE_CLOSURES__ZERO_CREDIT",
        "pass": True,
        "target_count": len(target_rows),
        "witness_count": len(witness_rows),
        "pair_count": len(pairs),
        "target_atom_occurrence_count": atom_occurrences,
        "target_metric_occurrence_count": metric_occurrences,
        "positive_atom_binding_count": positive_atom_bindings,
        "positive_metric_binding_count": positive_metric_bindings,
        "positive_semantic_edge_count": positive_semantic_edges,
        "closed_target_count": 0,
        "residual_target_count": len(target_rows),
        "target_results": target_results,
        "pairs": pairs,
        "logical_consequence": (
            "THE_CURRENT_NORMALIZED_PROVED_WITNESS_CATALOG_ALONE_CLOSES_NONE_OF_THE_8_LIVE_MATCHED_SCOPE_TARGETS__"
            "THIS_DOES_NOT_PROVE_THAT_NO_OTHER_SEMANTIC_OR_SCOPE_CERTIFICATE_EXISTS_ELSEWHERE"
        ),
        "next": (
            "SEARCH_ONLY_FOR_CONTENT_ADDRESSED_SEMANTIC_BINDING_OR_EXACT_SUPERSET_SCOPE_CERTIFICATES_NOT_YET_IN_THE_NORMALIZED_WITNESS_CATALOG__"
            "RECOMPUTE_IF_FOUND__OTHERWISE_ADVANCE_THESE_8_TARGETS_TO_THE_MINIMUM_IRREDUCIBLE_REALITY_CUT"
        ),
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "new_reality_units_consumed": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "errors": [],
    }


def main() -> int:
    target_doc = json.loads(TARGETS.read_text(encoding="utf-8"))
    target_verify = json.loads(TARGET_VERIFY.read_text(encoding="utf-8"))
    witness_doc = json.loads(WITNESSES.read_text(encoding="utf-8"))
    witness_verify = json.loads(WITNESS_VERIFY.read_text(encoding="utf-8"))
    out = totalize(
        target_doc,
        target_verify,
        witness_doc,
        witness_verify,
        target_blob_sha=git_blob_sha(TARGETS),
        witness_blob_sha=git_blob_sha(WITNESSES),
    )
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
