"""Fail-closed contamination admissibility verifier for normalized Brain witnesses.

This verifier proves only that the evidence objects behind the currently
normalized witness catalog are admissible with respect to case-exposure/tuning
contamination. It grants zero witness-to-target semantic implication,
acceptance, family, execution, or promotion credit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
NORMALIZATION = ROOT / "canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V1.json"

TERMINAL_V3 = "canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"
ARTIFACT_SCOPE = "canonical/verification/ARTIFACT_UNCOVERED_SCOPE_PARTITION_PROOF_20261002_V1.json"
TOOL_CEILING = "canonical/governance/TOOL_DISCOVERY_ACCEPTANCE_CEILING_WITNESS_V1.json"
DELEGATION_CEILING = "canonical/governance/DELEGATION_ACCEPTANCE_CEILING_WITNESS_V1.json"

SCHEMA = "PROJECT_BRAIN_OPUS55_BRAIN_WITNESS_CONTAMINATION_ADMISSIBILITY_VERDICT_V1"


def git_blob_sha(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


def _load(rel: str) -> dict[str, Any]:
    obj = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(rel)
    return obj


def _terminal_v3_admissible(doc: Mapping[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if doc.get("status") != "ONE_SHOT_TERMINAL_WAVE_PASS__IMMUTABLE_PUBLIC_RUNNER_RECEIPT__NO_REPLAY_AUTHORIZED":
        errors.append("TERMINAL_V3_STATUS_NOT_IMMUTABLE_ONE_SHOT_PASS")
    if not isinstance(doc.get("execution_snapshot_commit"), str) or not doc.get("execution_snapshot_commit"):
        errors.append("TERMINAL_V3_EXECUTION_SNAPSHOT_MISSING")
    if not isinstance(doc.get("package_commitment"), str) or not doc.get("package_commitment"):
        errors.append("TERMINAL_V3_PACKAGE_COMMITMENT_MISSING")
    guards = doc.get("result_guards")
    if not isinstance(guards, Mapping):
        errors.append("TERMINAL_V3_RESULT_GUARDS_MISSING")
    else:
        expected = {
            "no_case_replacement": True,
            "no_tuning_replay": True,
            "result_to_runtime_feedback_during_wave": False,
            "direct_route_duplicate_execution_count": 0,
        }
        for k, v in expected.items():
            if guards.get(k) != v:
                errors.append(f"TERMINAL_V3_GUARD_MISMATCH:{k}")
    if doc.get("fresh_terminal_evidence_consumed") != doc.get("total_fresh_terminal_case_executions"):
        errors.append("TERMINAL_V3_FRESH_EVIDENCE_COUNT_MISMATCH")
    return (not errors, errors)


def _ceiling_admissible(doc: Mapping[str, Any], expected_family: str) -> tuple[bool, list[str]]:
    errors: list[str] = []
    expected = {
        "verified": True,
        "independent": True,
        "contamination_clean": True,
        "binds_frozen_protocol": True,
        "scope_relation": "PROVEN_STRONGER",
        "closes_entire_protocol": True,
        "family": expected_family,
    }
    for k, v in expected.items():
        if doc.get(k) != v:
            errors.append(f"CEILING_WITNESS_MISMATCH:{expected_family}:{k}")
    result = doc.get("result")
    if not isinstance(result, Mapping):
        errors.append(f"CEILING_WITNESS_RESULT_MISSING:{expected_family}")
    else:
        if result.get("brain_lower_bound") != 1 or result.get("theoretical_upper_bound") != 1:
            errors.append(f"CEILING_WITNESS_NOT_OBJECTIVE_CEILING:{expected_family}")
    return (not errors, errors)


def _artifact_scope_admissible(doc: Mapping[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not str(doc.get("status", "")).startswith("PASS__FROZEN_CONTRACTED_ARTIFACT_SCOPE_PARTITIONS_COMPLETELY"):
        errors.append("ARTIFACT_SCOPE_PARTITION_NOT_PASS")
    if doc.get("no_uncovered_contracted_leaf") is not True:
        errors.append("ARTIFACT_SCOPE_PARTITION_NOT_COMPLETE")
    if doc.get("new_reality_units_consumed") != 0:
        errors.append("ARTIFACT_SCOPE_PARTITION_CONSUMED_REALITY")
    if doc.get("incremental_spend_usd") != 0:
        errors.append("ARTIFACT_SCOPE_PARTITION_SPEND_NONZERO")
    exclusions = set(doc.get("exclusions") or [])
    required = {
        "DOES_NOT_INHERIT_PUBLIC_BAR_PERFORMANCE_CREDIT",
        "DOES_NOT_PROMOTE_ARTIFACT_CREATION_FAMILY",
    }
    if not required.issubset(exclusions):
        errors.append("ARTIFACT_SCOPE_PARTITION_CREDIT_EXCLUSIONS_MISSING")
    return (not errors, errors)


def evaluate(normalization: Mapping[str, Any], docs: Mapping[str, Mapping[str, Any]], blob_shas: Mapping[str, str]) -> dict[str, Any]:
    errors: list[str] = []
    witnesses = normalization.get("witnesses")
    if not isinstance(witnesses, list):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["WITNESS_CATALOG_INVALID"],
            "contamination_admissible_witness_count": 0,
            "witness_count": 0,
            "semantic_implication_verified": False,
            "execution_authority": False,
            "promotion_authority": False,
        }

    allowed_paths = {TERMINAL_V3, ARTIFACT_SCOPE, TOOL_CEILING, DELEGATION_CEILING}
    rows = []
    for i, w in enumerate(witnesses):
        if not isinstance(w, Mapping):
            errors.append(f"WITNESS_{i}_INVALID")
            continue
        wid = w.get("witness_id")
        path = w.get("source_path")
        sha = w.get("source_sha")
        row_errors: list[str] = []
        if path not in allowed_paths:
            row_errors.append("SOURCE_PATH_NOT_IN_FROZEN_ADMISSIBILITY_SET")
        elif path not in docs:
            row_errors.append("SOURCE_DOCUMENT_MISSING")
        elif blob_shas.get(path) != sha:
            row_errors.append("SOURCE_BLOB_SHA_MISMATCH")
        else:
            doc = docs[path]
            if path == TERMINAL_V3:
                _, e = _terminal_v3_admissible(doc)
                row_errors.extend(e)
            elif path == TOOL_CEILING:
                _, e = _ceiling_admissible(doc, "TOOL_DISCOVERY_SELECTION_AND_LEARNING")
                row_errors.extend(e)
            elif path == DELEGATION_CEILING:
                _, e = _ceiling_admissible(doc, "SUBAGENT_DELEGATION_AND_COORDINATION")
                row_errors.extend(e)
            elif path == ARTIFACT_SCOPE:
                _, e = _artifact_scope_admissible(doc)
                row_errors.extend(e)

        if w.get("independent_or_objective") is not True:
            row_errors.append("NORMALIZED_WITNESS_NOT_INDEPENDENT_OR_OBJECTIVE")
        if w.get("scope_complete") is not True:
            row_errors.append("NORMALIZED_WITNESS_NOT_SCOPE_COMPLETE")

        if row_errors:
            errors.extend(f"{wid}:{e}" for e in row_errors)
        rows.append({
            "witness_id": wid,
            "source_path": path,
            "contamination_admissible": not row_errors,
            "errors": sorted(set(row_errors)),
        })

    admissible = sum(1 for r in rows if r["contamination_admissible"])
    expected_count = normalization.get("witness_count")
    if expected_count != len(witnesses):
        errors.append("NORMALIZATION_WITNESS_COUNT_MISMATCH")
    if admissible != len(witnesses):
        errors.append("NOT_ALL_WITNESSES_CONTAMINATION_ADMISSIBLE")

    errors = sorted(set(errors))
    return {
        "schema": SCHEMA,
        "status": "PASS__ALL_NORMALIZED_WITNESS_SOURCES_CONTAMINATION_ADMISSIBLE__ZERO_SEMANTIC_CREDIT" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "witness_count": len(witnesses),
        "unique_source_count": len({w.get("source_path") for w in witnesses if isinstance(w, Mapping)}),
        "contamination_admissible_witness_count": admissible,
        "witnesses": rows,
        "semantic_implication_verified": False,
        "target_atom_metric_bindings_verified": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "new_reality_units_consumed": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "errors": errors,
    }


def evaluate_live() -> dict[str, Any]:
    normalization = json.loads(NORMALIZATION.read_text(encoding="utf-8"))
    source_paths = {w.get("source_path") for w in normalization.get("witnesses", []) if isinstance(w, Mapping)}
    docs = {p: _load(p) for p in source_paths}
    shas = {p: git_blob_sha(ROOT / p) for p in source_paths}
    return evaluate(normalization, docs, shas)


def main() -> int:
    out = evaluate_live()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
