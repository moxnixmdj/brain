"""Fail-closed verifier for the synthesis witness-to-target binding candidate.

This verifier permits only the predeclared singleton synthesis behavioral contract
to discharge target atoms whose operational obligations are explicit in the
frozen contract/binding. Numeric matched noninferiority bounds remain forbidden.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "canonical/governance/OPUS55_SYNTHESIS_WITNESS_TARGET_BINDING_CANDIDATE_V1.json"
REGISTRY = ROOT / "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
P3 = ROOT / "canonical/governance/P3_SYNTHESIS_T1_T3_MULTIPLEX_TERMINAL_BINDING_V1.json"
P3_VERIFY = ROOT / "canonical/verification/P3_SYNTHESIS_T1_T3_MULTIPLEX_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
WAVE = ROOT / "canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"
POST = ROOT / "canonical/verification/TERMINAL_V3_POSTWAVE_CONTRACT_AND_FAMILY_REDUCTION_20261002_V1.json"
TARGETS = ROOT / "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json"

BEHAVIOR = "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
FAMILY = "COMMUNICATION_AND_SYNTHESIS"
TARGET = "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"

EXPECTED_BINDINGS = {
    "dimension:claim_to_source_fidelity": {
        "ZERO_UNSUPPORTED_MATERIAL_CLAIMS",
        "PROVENANCE_PRESERVED_FOR_MATERIAL_CLAIMS",
    },
    "dimension:required_evidence_coverage": {
        "ALL_REQUIRED_CLAIMS_OR_DECISION_REQUIREMENTS_COVERED",
    },
    "dimension:uncertainty_and_disagreement_preservation": {
        "MATERIAL_CONFLICT_AND_UNCERTAINTY_PRESERVED",
    },
    "dimension:audience_adaptation": {"AUDIENCE_AND_FORMAT_CONSTRAINTS_PASS"},
    "dimension:format_and_style_constraints": {"AUDIENCE_AND_FORMAT_CONSTRAINTS_PASS"},
    "dimension:compression_without_decision_relevant_loss": {
        "NO_DECISION_RELEVANT_EVIDENCE_DROPPED_UNDER_COMPRESSION",
    },
    "metric:required_claim_coverage": {
        "ALL_REQUIRED_CLAIMS_OR_DECISION_REQUIREMENTS_COVERED",
    },
}
EXPECTED_UNPROVED_ATOMS = {"metric:matched_quality"}
EXPECTED_UNPROVED_METRICS = {
    "matched_quality_noninferiority",
    "required_claim_coverage_noninferiority",
}


def blob_sha(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


def load(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": "PROJECT_BRAIN_OPUS55_SYNTHESIS_WITNESS_TARGET_BINDING_VERDICT_V1",
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "proved_atoms": [],
        "metric_bounds": {},
        "contamination_clean": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "new_reality_units_consumed": 0,
    }


def evaluate(
    candidate: Mapping[str, Any],
    registry: Mapping[str, Any],
    p3: Mapping[str, Any],
    p3_verify: Mapping[str, Any],
    wave: Mapping[str, Any],
    post: Mapping[str, Any],
    targets: Mapping[str, Any],
    source_shas: Mapping[str, str],
) -> dict[str, Any]:
    errors: list[str] = []

    auth = candidate.get("authority")
    if not isinstance(auth, Mapping):
        return fail("AUTHORITY_MISSING")
    expected_paths = {
        "behavioral_contract_registry": ("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json", source_shas["registry"]),
        "p3_binding": ("canonical/governance/P3_SYNTHESIS_T1_T3_MULTIPLEX_TERMINAL_BINDING_V1.json", source_shas["p3"]),
        "p3_binding_independent_verification": ("canonical/verification/P3_SYNTHESIS_T1_T3_MULTIPLEX_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json", source_shas["p3_verify"]),
        "terminal_wave": ("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json", source_shas["wave"]),
        "postwave_reduction": ("canonical/verification/TERMINAL_V3_POSTWAVE_CONTRACT_AND_FAMILY_REDUCTION_20261002_V1.json", source_shas["post"]),
        "target_normalization": ("canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json", source_shas["targets"]),
    }
    for key, (path, sha) in expected_paths.items():
        row = auth.get(key)
        if not isinstance(row, Mapping) or row.get("path") != path or row.get("git_blob_sha") != sha:
            errors.append(f"AUTHORITY_MISMATCH:{key}")

    if candidate.get("target_predicate_id") != TARGET or candidate.get("family") != FAMILY or candidate.get("behavior_id") != BEHAVIOR:
        errors.append("IDENTITY_MISMATCH")

    rows = registry.get("active_contracted_residuals")
    contract = None
    if isinstance(rows, list):
        contract = next((x for x in rows if isinstance(x, Mapping) and x.get("behavior_id") == BEHAVIOR), None)
    if not isinstance(contract, Mapping):
        errors.append("SYNTHESIS_CONTRACT_MISSING")
    else:
        if contract.get("success_condition") != candidate.get("operational_basis", {}).get("contract_success_condition"):
            errors.append("SUCCESS_CONDITION_MISMATCH")
        if contract.get("required_output_or_action") != candidate.get("operational_basis", {}).get("contract_required_output"):
            errors.append("REQUIRED_OUTPUT_MISMATCH")

    family_map = registry.get("family_to_residual_contracts", {})
    if not isinstance(family_map, Mapping) or family_map.get(FAMILY) != [BEHAVIOR]:
        errors.append("SYNTHESIS_FAMILY_NOT_SINGLETON_BOUND_TO_BEHAVIOR")

    if p3.get("behavior_id") != BEHAVIOR:
        errors.append("P3_BEHAVIOR_MISMATCH")
    required_checks = p3.get("evaluator", {}).get("required_checks") if isinstance(p3.get("evaluator"), Mapping) else None
    if not isinstance(required_checks, list):
        errors.append("P3_REQUIRED_CHECKS_MISSING")
        check_set: set[str] = set()
    else:
        check_set = set(required_checks)

    if p3_verify.get("workflow_conclusion") != "success" or p3_verify.get("behavior_id") != BEHAVIOR:
        errors.append("P3_PREWAVE_INDEPENDENT_VERIFICATION_MISSING")

    target_rows = targets.get("targets")
    target = None
    if isinstance(target_rows, list):
        target = next((x for x in target_rows if isinstance(x, Mapping) and x.get("predicate_id") == TARGET), None)
    if not isinstance(target, Mapping):
        errors.append("TARGET_NORMALIZATION_MISSING")
        target_atoms: set[str] = set()
        target_metrics: set[str] = set()
    else:
        atom_sources = target.get("atom_sources")
        target_atoms = {
            x.get("atom") for x in atom_sources
            if isinstance(x, Mapping) and isinstance(x.get("atom"), str)
        } if isinstance(atom_sources, list) else set()
        metric_sources = target.get("metric_requirement_sources")
        target_metrics = {
            x.get("metric") for x in metric_sources
            if isinstance(x, Mapping) and isinstance(x.get("metric"), str)
        } if isinstance(metric_sources, list) else set()

    bindings = candidate.get("atom_bindings")
    actual_bindings: dict[str, set[str]] = {}
    if not isinstance(bindings, list):
        errors.append("ATOM_BINDINGS_INVALID")
    else:
        for row in bindings:
            if not isinstance(row, Mapping) or not isinstance(row.get("target_atom"), str) or not isinstance(row.get("operational_evidence"), list):
                errors.append("ATOM_BINDING_ROW_INVALID")
                continue
            atom = row["target_atom"]
            ev = row["operational_evidence"]
            if any(not isinstance(x, str) for x in ev):
                errors.append(f"ATOM_BINDING_EVIDENCE_INVALID:{atom}")
                continue
            if atom in actual_bindings:
                errors.append(f"DUPLICATE_ATOM_BINDING:{atom}")
                continue
            actual_bindings[atom] = set(ev)

    if actual_bindings != EXPECTED_BINDINGS:
        errors.append("ATOM_BINDING_SET_MISMATCH")
    for atom, checks in EXPECTED_BINDINGS.items():
        if atom not in target_atoms:
            errors.append(f"BOUND_ATOM_NOT_IN_FROZEN_TARGET:{atom}")
        if not checks <= check_set:
            errors.append(f"OPERATIONAL_CHECK_MISSING:{atom}")

    proved = candidate.get("proved_atoms")
    if not isinstance(proved, list) or set(proved) != set(EXPECTED_BINDINGS) or len(proved) != len(set(proved)):
        errors.append("PROVED_ATOMS_MISMATCH")

    if candidate.get("metric_bounds") != {}:
        errors.append("NUMERIC_METRIC_BOUNDS_FORBIDDEN")

    unproved = candidate.get("deliberately_unproved")
    if not isinstance(unproved, Mapping):
        errors.append("UNPROVED_DECLARATION_MISSING")
    else:
        if set(unproved.get("target_atoms", [])) != EXPECTED_UNPROVED_ATOMS:
            errors.append("UNPROVED_ATOM_SET_MISMATCH")
        if set(unproved.get("metric_requirements", [])) != EXPECTED_UNPROVED_METRICS:
            errors.append("UNPROVED_METRIC_SET_MISMATCH")
    if not EXPECTED_UNPROVED_ATOMS <= target_atoms:
        errors.append("EXPECTED_UNPROVED_ATOM_NOT_IN_TARGET")
    if not EXPECTED_UNPROVED_METRICS <= target_metrics:
        errors.append("EXPECTED_UNPROVED_METRIC_NOT_IN_TARGET")

    parent = wave.get("reduction_input", {}).get("wave", {}).get("parent_portfolio_receipts", {})
    if not isinstance(parent, Mapping):
        errors.append("TERMINAL_PARENT_RECEIPTS_MISSING")
    else:
        for tier in ("T1", "T3"):
            tier_rows = parent.get(tier)
            hits = [
                x for x in tier_rows
                if isinstance(x, Mapping) and x.get("behavior_id") == BEHAVIOR
            ] if isinstance(tier_rows, list) else []
            if len(hits) != 1:
                errors.append(f"{tier}_SYNTHESIS_RECEIPT_COUNT")
                continue
            x = hits[0]
            required_true = ("load_bearing", "direct_instrumentation_pass", "parent_terminal_acceptance_pass")
            if any(x.get(k) is not True for k in required_true):
                errors.append(f"{tier}_TERMINAL_PASS_REQUIREMENTS_MISSING")
            required_false = ("case_replaced", "result_to_runtime_feedback", "tuning_replay")
            if any(x.get(k) is not False for k in required_false):
                errors.append(f"{tier}_CONTAMINATION_FLAG_FAIL")

    cv = post.get("contract_verdict")
    fv = post.get("family_verdict")
    if not isinstance(cv, Mapping) or cv.get("all_contracts_pass") is not True or BEHAVIOR not in cv.get("passed_contracts", []):
        errors.append("POSTWAVE_CONTRACT_PASS_MISSING")
    if not isinstance(fv, Mapping) or fv.get("all_families_pass") is not True or FAMILY not in fv.get("passed_families", []):
        errors.append("POSTWAVE_FAMILY_PASS_MISSING")
    if not isinstance(post.get("status"), str) or not post["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("POSTWAVE_NOT_INDEPENDENTLY_VERIFIED")

    contamination = p3.get("contamination")
    if not isinstance(contamination, Mapping) or any(v is not False for v in contamination.values()):
        errors.append("P3_CONTAMINATION_POLICY_NOT_CLEAN")

    if errors:
        return fail(*errors)

    return {
        "schema": "PROJECT_BRAIN_OPUS55_SYNTHESIS_WITNESS_TARGET_BINDING_VERDICT_V1",
        "status": "PASS__7_TARGET_ATOMS_OPERATIONALLY_BOUND__MATCHED_METRIC_BOUNDS_REMAIN_OPEN__ZERO_CREDIT",
        "pass": True,
        "errors": [],
        "target_predicate_id": TARGET,
        "behavior_id": BEHAVIOR,
        "proved_atoms": sorted(EXPECTED_BINDINGS),
        "remaining_target_atoms": sorted(EXPECTED_UNPROVED_ATOMS),
        "metric_bounds": {},
        "remaining_metric_requirements": sorted(EXPECTED_UNPROVED_METRICS),
        "verified": True,
        "independent_input_chain": True,
        "contamination_clean": True,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "new_reality_units_consumed": 0,
        "rule": "OPERATIONAL_ATOM_BINDING_ONLY__NO_MATCHED_NUMERIC_NONINFERIORITY_INFERRED",
    }


def main() -> int:
    docs = [load(x) for x in (CANDIDATE, REGISTRY, P3, P3_VERIFY, WAVE, POST, TARGETS)]
    shas = {
        "registry": blob_sha(REGISTRY),
        "p3": blob_sha(P3),
        "p3_verify": blob_sha(P3_VERIFY),
        "wave": blob_sha(WAVE),
        "post": blob_sha(POST),
        "targets": blob_sha(TARGETS),
    }
    out = evaluate(*docs, shas)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
