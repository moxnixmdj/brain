"""Fail-closed verifier for scope-safe synthesis implication residual v2."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.protocol_implication_scope_algebra_v2 import evaluate as algebra_evaluate

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "canonical/governance/OPUS55_SYNTHESIS_IMPLICATION_RESIDUAL_INPUT_V2.json"
TARGETS = ROOT / "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_CANDIDATE_V1.json"
BINDING = ROOT / "canonical/governance/OPUS55_SYNTHESIS_WITNESS_TARGET_BINDING_CANDIDATE_V1.json"
RECEIPT = ROOT / "canonical/verification/OPUS55_SYNTHESIS_WITNESS_TARGET_BINDING_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
ALGEBRA = ROOT / "canonical/runtime/protocol_implication_scope_algebra_v2.py"
TARGET_ID = "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"
TARGET_SCOPE = "scope://opus55/SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"
WITNESS_SCOPE = "scope://brain/EVIDENCE_TO_AUDIENCE_SYNTHESIS_001/T1_T3_TERMINAL"


def load(p: Path) -> Mapping[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def blob_sha(p: Path) -> str:
    b = p.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


def fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": "PROJECT_BRAIN_OPUS55_SYNTHESIS_IMPLICATION_RESIDUAL_VERDICT_V2",
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "new_reality_units_consumed": 0,
    }


def evaluate(
    doc: Mapping[str, Any],
    targets: Mapping[str, Any],
    binding: Mapping[str, Any],
    receipt: Mapping[str, Any],
    source_shas: Mapping[str, str],
) -> dict[str, Any]:
    errors: list[str] = []
    if doc.get("schema") != "PROJECT_BRAIN_OPUS55_SYNTHESIS_IMPLICATION_RESIDUAL_INPUT_V2":
        errors.append("INPUT_SCHEMA_MISMATCH")

    auth = doc.get("authority")
    expected = {
        "target_normalization_candidate": (
            "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_CANDIDATE_V1.json",
            source_shas["targets"],
        ),
        "synthesis_binding_candidate": (
            "canonical/governance/OPUS55_SYNTHESIS_WITNESS_TARGET_BINDING_CANDIDATE_V1.json",
            source_shas["binding"],
        ),
        "synthesis_binding_verification": (
            "canonical/verification/OPUS55_SYNTHESIS_WITNESS_TARGET_BINDING_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
            source_shas["receipt"],
        ),
        "algebra_runtime": (
            "canonical/runtime/protocol_implication_scope_algebra_v2.py",
            source_shas["algebra"],
        ),
    }
    if not isinstance(auth, Mapping):
        return fail("AUTHORITY_MISSING")
    for key, (path, sha) in expected.items():
        row = auth.get(key)
        if not isinstance(row, Mapping) or row.get("path") != path or row.get("git_blob_sha") != sha:
            errors.append(f"AUTHORITY_MISMATCH:{key}")

    target_rows = targets.get("targets")
    target_row = next(
        (x for x in target_rows if isinstance(x, Mapping) and x.get("predicate_id") == TARGET_ID),
        None,
    ) if isinstance(target_rows, list) else None
    ai = doc.get("algebra_input")
    if not isinstance(ai, Mapping) or not isinstance(target_row, Mapping):
        errors.append("INPUT_OR_TARGET_MISSING")
    else:
        target = ai.get("target")
        witness = ai.get("witness")
        canonical_target = {
            "scope_ref": TARGET_SCOPE,
            "required_atoms": target_row.get("required_atoms"),
            "metric_requirements": target_row.get("metric_requirements", []),
        }
        if target != canonical_target:
            errors.append("TARGET_INPUT_NOT_EXACT_CANONICAL_ROW_PLUS_SCOPE_REF")
        if not isinstance(witness, Mapping):
            errors.append("WITNESS_MISSING")
        else:
            if witness.get("scope_ref") != WITNESS_SCOPE:
                errors.append("WITNESS_SCOPE_REF_MISMATCH")
            if witness.get("proved_atoms") != binding.get("proved_atoms"):
                errors.append("WITNESS_ATOMS_NOT_EXACT_VERIFIED_BINDING")
            if witness.get("metric_bounds") != binding.get("metric_bounds") or witness.get("metric_bounds") != {}:
                errors.append("WITNESS_METRIC_BOUND_INVENTION")
            for flag in ("verified", "independent", "contamination_clean"):
                if witness.get(flag) is not True:
                    errors.append(f"WITNESS_{flag.upper()}_REQUIRED")
        if ai.get("verified_implications") != []:
            errors.append("UNVERIFIED_IMPLICATION_EDGE_FORBIDDEN")
        if ai.get("verified_scope_relations") != []:
            errors.append("UNVERIFIED_SCOPE_RELATION_FORBIDDEN")

    if receipt.get("public_runner", {}).get("conclusion") != "success":
        errors.append("INDEPENDENT_BINDING_RECEIPT_NOT_SUCCESS")
    if (
        receipt.get("proved_atom_count") != 7
        or receipt.get("numeric_metric_bounds_verified") is not False
        or receipt.get("contamination_clean") is not True
    ):
        errors.append("BINDING_RECEIPT_SCOPE_MISMATCH")
    if receipt.get("remaining_target_atoms") != ["metric:matched_quality"]:
        errors.append("BINDING_RECEIPT_REMAINING_ATOM_MISMATCH")
    if set(receipt.get("remaining_metric_requirements", [])) != {
        "matched_quality_noninferiority",
        "required_claim_coverage_noninferiority",
    }:
        errors.append("BINDING_RECEIPT_REMAINING_METRICS_MISMATCH")

    if errors:
        return fail(*errors)

    result = algebra_evaluate(ai)
    exp = doc.get("expected_residual")
    if not isinstance(exp, Mapping):
        return fail("EXPECTED_RESIDUAL_MISSING")
    missing_metric_bounds = sorted(
        x["metric"]
        for x in result.get("metric_results", [])
        if isinstance(x, Mapping) and x.get("pass") is False and x.get("reason") == "BOUND_MISSING"
    )
    checks = [
        result.get("status") == exp.get("status") == "TARGET_SCOPE_NOT_COVERED",
        result.get("implies_target") is exp.get("implies_target") is False,
        result.get("candidate_scope_relation") is exp.get("candidate_scope_relation") is None,
        result.get("verified_scope_relation") is exp.get("verified_scope_relation") is None,
        result.get("missing_atoms") == exp.get("missing_atoms") == ["metric:matched_quality"],
        missing_metric_bounds == sorted(exp.get("missing_metric_bounds", [])),
        exp.get("missing_scope_relation") is True,
    ]
    if not all(checks):
        return fail("SCOPE_SAFE_ALGEBRA_RESIDUAL_MISMATCH")

    return {
        "schema": "PROJECT_BRAIN_OPUS55_SYNTHESIS_IMPLICATION_RESIDUAL_VERDICT_V2",
        "status": "PASS__SCOPE_SAFE_SYNTHESIS_RESIDUAL_IS_SCOPE_RELATION_PLUS_ONE_ATOM_PLUS_TWO_NUMERIC_BOUNDS__ZERO_CREDIT",
        "pass": True,
        "target_predicate_id": TARGET_ID,
        "proved_atom_count": len(result.get("witness_direct_atoms", [])),
        "missing_scope_relation": True,
        "missing_atoms": result.get("missing_atoms"),
        "missing_metric_bounds": missing_metric_bounds,
        "implies_target": False,
        "candidate_scope_relation": None,
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "rule": "V1_RESIDUAL_IS_NOT_SCHEDULING_AUTHORITY__V2_SCOPE_FIREWALL_REMAINS_LOAD_BEARING",
    }


def main() -> int:
    out = evaluate(
        load(INPUT),
        load(TARGETS),
        load(BINDING),
        load(RECEIPT),
        {
            "targets": blob_sha(TARGETS),
            "binding": blob_sha(BINDING),
            "receipt": blob_sha(RECEIPT),
            "algebra": blob_sha(ALGEBRA),
        },
    )
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
