from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

TARGET = "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V1.json"
P3 = "canonical/governance/P3_SYNTHESIS_T1_T3_MULTIPLEX_TERMINAL_BINDING_V1.json"
WAVE = "canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"
P3V = "canonical/verification/P3_SYNTHESIS_T1_T3_MULTIPLEX_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
BRIDGE = "canonical/governance/OPUS55_SYNTHESIS_SEMANTIC_BRIDGE_V1.json"

BEHAVIOR_ID = "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
PREDICATE_ID = "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"

EXPECTED_SUPPORTED = {
    "dimension:audience_adaptation",
    "dimension:claim_to_source_fidelity",
    "dimension:compression_without_decision_relevant_loss",
    "dimension:format_and_style_constraints",
    "dimension:required_evidence_coverage",
    "dimension:uncertainty_and_disagreement_preservation",
}
EXPECTED_OPEN = {
    "metric:matched_quality",
    "metric:required_claim_coverage",
}
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
    "dimension:audience_adaptation": {
        "AUDIENCE_AND_FORMAT_CONSTRAINTS_PASS",
    },
    "dimension:format_and_style_constraints": {
        "AUDIENCE_AND_FORMAT_CONSTRAINTS_PASS",
    },
    "dimension:compression_without_decision_relevant_loss": {
        "NO_DECISION_RELEVANT_EVIDENCE_DROPPED_UNDER_COMPRESSION",
    },
}
REQUIRED_VISIBLE_INPUTS = {
    "dimension:audience_adaptation": "AUDIENCE",
    "dimension:format_and_style_constraints": "FORMAT_AND_STYLE_CONSTRAINTS",
}


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\x00" + raw).hexdigest()


def _load(root: Path, rel: str) -> dict[str, Any]:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def _walk_dicts(x: Any):
    if isinstance(x, dict):
        yield x
        for value in x.values():
            yield from _walk_dicts(value)
    elif isinstance(x, list):
        for value in x:
            yield from _walk_dicts(value)


def evaluate(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        target = _load(root, TARGET)
        p3 = _load(root, P3)
        wave = _load(root, WAVE)
        p3v = _load(root, P3V)
        bridge = _load(root, BRIDGE)
    except Exception as exc:
        return {
            "schema": "PROJECT_BRAIN_SYNTHESIS_SEMANTIC_BRIDGE_VERDICT_V1",
            "pass": False,
            "errors": ["INPUT_UNREADABLE:" + type(exc).__name__],
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    auth = bridge.get("authority") or {}
    expected_auth = {
        "target_normalization": (TARGET, git_blob_sha(root / TARGET)),
        "p3_binding": (P3, git_blob_sha(root / P3)),
        "terminal_wave": (WAVE, git_blob_sha(root / WAVE)),
        "p3_preflight_independent_verification": (P3V, git_blob_sha(root / P3V)),
    }
    for key, (path, sha) in expected_auth.items():
        row = auth.get(key) or {}
        if row.get("path") != path:
            errors.append("AUTHORITY_PATH:" + key)
        if row.get("git_blob_sha") != sha:
            errors.append("AUTHORITY_SHA:" + key)

    rows = [x for x in target.get("targets", []) if x.get("predicate_id") == PREDICATE_ID]
    if len(rows) != 1:
        errors.append("TARGET_PREDICATE_ROW")
        target_atoms: set[str] = set()
    else:
        target_atoms = {x.get("atom") for x in rows[0].get("atom_sources", []) if isinstance(x.get("atom"), str)}
    if target_atoms != EXPECTED_SUPPORTED | EXPECTED_OPEN:
        errors.append("TARGET_ATOM_SET")

    supported = set(bridge.get("supported_target_atoms") or [])
    opened = set(bridge.get("open_target_atoms") or [])
    if supported != EXPECTED_SUPPORTED:
        errors.append("SUPPORTED_ATOM_SET")
    if opened != EXPECTED_OPEN:
        errors.append("OPEN_ATOM_SET")
    if supported & EXPECTED_OPEN:
        errors.append("METRIC_ATOM_PREMATURE_SUPPORT")
    if supported | opened != target_atoms:
        errors.append("TARGET_PARTITION")

    required_checks = set(((p3.get("evaluator") or {}).get("required_checks") or []))
    visible_inputs = set(p3.get("candidate_visible_information") or [])
    mapping = {}
    for row in bridge.get("bindings") or []:
        atom = row.get("target_atom")
        checks = set(row.get("source_checks") or [])
        if isinstance(atom, str):
            mapping[atom] = checks
        if not checks <= required_checks:
            errors.append("SOURCE_CHECK_NOT_FROZEN:" + str(atom))
        req = REQUIRED_VISIBLE_INPUTS.get(atom)
        if req is not None:
            if row.get("required_candidate_input") != req:
                errors.append("VISIBLE_INPUT_BINDING:" + str(atom))
            if req not in visible_inputs:
                errors.append("VISIBLE_INPUT_NOT_FROZEN:" + req)
    if mapping != EXPECTED_BINDINGS:
        errors.append("SEMANTIC_BINDING_TABLE")

    contamination = p3.get("contamination") or {}
    for key in (
        "post_freeze_case_specific_tuning",
        "case_replacement",
        "result_to_runtime_feedback_during_wave",
        "evaluator_or_threshold_edit_after_first_terminal_result",
        "terminal_case_selection_before_route_freeze",
    ):
        if contamination.get(key) is not False:
            errors.append("P3_CONTAMINATION:" + key)

    exact = (p3v.get("exact_brain_blobs") or {}).get(P3)
    if exact != git_blob_sha(root / P3):
        errors.append("P3_INDEPENDENT_VERIFICATION_BLOB")
    if not str(p3v.get("status") or "").startswith("INDEPENDENT_PASS"):
        errors.append("P3_INDEPENDENT_VERIFICATION_STATUS")

    receipts = [
        d for d in _walk_dicts(wave)
        if d.get("behavior_id") == BEHAVIOR_ID
        and d.get("portfolio") in {"T1", "T3"}
        and d.get("binding_blob") == git_blob_sha(root / P3)
        and isinstance(d.get("case_id"), str)
    ]
    for portfolio in ("T1", "T3"):
        matched = [d for d in receipts if d.get("portfolio") == portfolio]
        if len(matched) != 1:
            errors.append("TERMINAL_RECEIPT_COUNT:" + portfolio)
            continue
        row = matched[0]
        expected_flags = {
            "direct_instrumentation_pass": True,
            "load_bearing": True,
            "parent_terminal_acceptance_pass": True,
            "case_replaced": False,
            "result_to_runtime_feedback": False,
            "tuning_replay": False,
        }
        for key, value in expected_flags.items():
            if row.get(key) is not value:
                errors.append(f"TERMINAL_RECEIPT_FLAG:{portfolio}:{key}")

    src_contam = bridge.get("source_contamination_admissibility") or {}
    if src_contam.get("admissible_for_qualitative_behavior_support") is not True:
        errors.append("QUALITATIVE_ADMISSIBILITY")
    if src_contam.get("admissible_for_matched_metric_noninferiority") is not False:
        errors.append("METRIC_ADMISSIBILITY_OVERCLAIM")

    residual = bridge.get("residual_after_bridge") or {}
    if residual.get("target_atom_count") != 8:
        errors.append("RESIDUAL_TARGET_COUNT")
    if residual.get("qualitative_atoms_supported") != 6:
        errors.append("RESIDUAL_SUPPORTED_COUNT")
    if residual.get("matched_metric_atoms_open") != 2:
        errors.append("RESIDUAL_OPEN_COUNT")

    if bridge.get("capability_credit_delta") != 0 or bridge.get("family_credit_delta") != 0:
        errors.append("CREDIT_DELTA")
    if bridge.get("execution_authority") is not False or bridge.get("promotion_authority") is not False:
        errors.append("AUTHORITY_OVERCLAIM")

    return {
        "schema": "PROJECT_BRAIN_SYNTHESIS_SEMANTIC_BRIDGE_VERDICT_V1",
        "pass": not errors,
        "errors": sorted(set(errors)),
        "predicate_id": PREDICATE_ID,
        "supported_target_atoms": sorted(supported),
        "open_target_atoms": sorted(opened),
        "qualitative_atom_count": len(supported),
        "matched_metric_atom_count_open": len(opened),
        "source_terminal_portfolios_verified": sorted({d.get("portfolio") for d in receipts}),
        "matched_population_noninferiority_proved": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "new_reality_units_consumed": 0,
    }


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    out = evaluate(root)
    print(json.dumps(out, indent=2, sort_keys=True))
    if not out["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
