from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_CREDITED_TRANSFORM_CERTIFICATE_COMPILER_V1"
REGISTRY = ROOT / "canonical/governance/CREDITED_TRANSFORM_CERTIFICATE_REGISTRY_20261007_V1.json"
MATRIX = ROOT / "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"
CREDITED_STATUS = "VERIFIED_OWNED_EQUAL_OR_BETTER"

REQUIRED_CERTIFICATE_FLAGS = (
    "source_state_complete",
    "target_state_complete",
    "external_controls_accounted",
    "randomness_accounted",
    "target_evaluator_set_complete",
    "target_hard_constraint_set_complete",
    "interactive_state_accounted",
    "independent_verification_bound",
)


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"OBJECT_REQUIRED:{path}")
    return value


def _token_list(value: Any, label: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        errors.append(label + "_INVALID")
        return []
    if len(value) != len(set(value)):
        errors.append(label + "_DUPLICATE")
    return list(value)


def _validate_certificate(family: str, cert: Mapping[str, Any] | None) -> list[str]:
    errors: list[str] = []
    prefix = family + ":"
    if not isinstance(cert, Mapping):
        return [prefix + "CERTIFICATE_MISSING"]

    for key in REQUIRED_CERTIFICATE_FLAGS:
        if cert.get(key) is not True:
            errors.append(prefix + key.upper() + "_NOT_TRUE")

    law = cert.get("transform_law")
    if law not in {"DETERMINISTIC", "STOCHASTIC"}:
        errors.append(prefix + "TRANSFORM_LAW_INVALID")

    source_state = _token_list(cert.get("source_state_ids"), prefix + "SOURCE_STATE_IDS", errors)
    target_state = _token_list(cert.get("target_state_ids"), prefix + "TARGET_STATE_IDS", errors)
    if not source_state:
        errors.append(prefix + "SOURCE_STATE_EMPTY")
    if not target_state:
        errors.append(prefix + "TARGET_STATE_EMPTY")

    evaluators = _token_list(cert.get("target_evaluator_ids"), prefix + "TARGET_EVALUATOR_IDS", errors)
    pullbacks = cert.get("evaluator_pullbacks")
    if not isinstance(pullbacks, list):
        errors.append(prefix + "EVALUATOR_PULLBACKS_INVALID")
        pullbacks = []
    pb_targets: list[str] = []
    for i, row in enumerate(pullbacks):
        if not isinstance(row, Mapping):
            errors.append(prefix + f"PULLBACK_{i}_INVALID")
            continue
        target = row.get("target_evaluator_id")
        source = row.get("source_evaluator_id")
        proof = row.get("proof_ref")
        if not isinstance(target, str) or not target:
            errors.append(prefix + f"PULLBACK_{i}_TARGET_INVALID")
        else:
            pb_targets.append(target)
        if not isinstance(source, str) or not source:
            errors.append(prefix + f"PULLBACK_{i}_SOURCE_INVALID")
        if not isinstance(proof, str) or not proof:
            errors.append(prefix + f"PULLBACK_{i}_PROOF_INVALID")
    if set(pb_targets) != set(evaluators) or len(pb_targets) != len(set(pb_targets)):
        errors.append(prefix + "EVALUATOR_PULLBACK_COVERAGE_INCOMPLETE")

    constraints = _token_list(cert.get("target_hard_constraint_ids"), prefix + "TARGET_HARD_CONSTRAINT_IDS", errors)
    preimages = cert.get("hard_constraint_preimages")
    if not isinstance(preimages, list):
        errors.append(prefix + "HARD_CONSTRAINT_PREIMAGES_INVALID")
        preimages = []
    hc_targets: list[str] = []
    for i, row in enumerate(preimages):
        if not isinstance(row, Mapping):
            errors.append(prefix + f"PREIMAGE_{i}_INVALID")
            continue
        target = row.get("target_hard_constraint_id")
        witness = row.get("source_preimage_or_invariant_id")
        proof = row.get("proof_ref")
        if not isinstance(target, str) or not target:
            errors.append(prefix + f"PREIMAGE_{i}_TARGET_INVALID")
        else:
            hc_targets.append(target)
        if not isinstance(witness, str) or not witness:
            errors.append(prefix + f"PREIMAGE_{i}_WITNESS_INVALID")
        if not isinstance(proof, str) or not proof:
            errors.append(prefix + f"PREIMAGE_{i}_PROOF_INVALID")
    if set(hc_targets) != set(constraints) or len(hc_targets) != len(set(hc_targets)):
        errors.append(prefix + "HARD_CONSTRAINT_PREIMAGE_COVERAGE_INCOMPLETE")

    semantics = cert.get("acceptance_semantics_completeness_ref")
    if not isinstance(semantics, str) or not semantics:
        errors.append(prefix + "ACCEPTANCE_SEMANTICS_COMPLETENESS_REF_MISSING")

    verification = cert.get("independent_verification_ref")
    if not isinstance(verification, str) or not verification:
        errors.append(prefix + "INDEPENDENT_VERIFICATION_REF_MISSING")

    return errors


def compile_current() -> dict[str, Any]:
    errors: list[str] = []
    if not REGISTRY.is_file():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["REGISTRY_MISSING"], "c_closed": False}
    if not MATRIX.is_file():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["OWNERSHIP_MATRIX_MISSING"], "c_closed": False}

    registry = _read(REGISTRY)
    matrix = _read(MATRIX)

    expected_matrix_sha = registry.get("ownership_matrix", {}).get("git_blob_sha")
    if _git_blob_sha(MATRIX) != expected_matrix_sha:
        errors.append("OWNERSHIP_MATRIX_DRIFT")

    credited = sorted(
        str(row.get("family"))
        for row in matrix.get("rows", [])
        if isinstance(row, Mapping) and row.get("status") == CREDITED_STATUS
    )

    routes = registry.get("routes")
    if not isinstance(routes, list):
        errors.append("ROUTES_INVALID")
        routes = []

    declared = sorted(
        str(row.get("family"))
        for row in routes
        if isinstance(row, Mapping) and isinstance(row.get("family"), str)
    )

    if credited != declared:
        errors.append("CREDITED_ROUTE_SET_MISMATCH")

    route_results: dict[str, Any] = {}
    complete = 0
    for row in routes:
        if not isinstance(row, Mapping):
            errors.append("ROUTE_NOT_OBJECT")
            continue
        family = str(row.get("family") or "")
        row_errors: list[str] = []

        artifacts = row.get("implementation_artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            row_errors.append("IMPLEMENTATION_ARTIFACTS_INVALID")
            artifacts = []
        seen_paths: set[str] = set()
        for i, binding in enumerate(artifacts):
            if not isinstance(binding, Mapping):
                row_errors.append(f"IMPLEMENTATION_ARTIFACT_{i}_INVALID")
                continue
            rel = binding.get("path")
            sha = binding.get("git_blob_sha")
            if not isinstance(rel, str) or not rel:
                row_errors.append(f"IMPLEMENTATION_ARTIFACT_{i}_PATH_INVALID")
                continue
            if rel in seen_paths:
                row_errors.append("IMPLEMENTATION_ARTIFACT_DUPLICATE:" + rel)
            seen_paths.add(rel)
            path = ROOT / rel
            if not path.is_file():
                row_errors.append(f"IMPLEMENTATION_ARTIFACT_{i}_MISSING")
                continue
            if not isinstance(sha, str) or _git_blob_sha(path) != sha:
                row_errors.append(f"IMPLEMENTATION_ARTIFACT_{i}_DRIFT")

        binding = row.get("acceptance_anchor")
        if not isinstance(binding, Mapping):
            row_errors.append("ACCEPTANCE_ANCHOR_INVALID")
        else:
            rel = binding.get("path")
            sha = binding.get("git_blob_sha")
            if not isinstance(rel, str) or not rel:
                row_errors.append("ACCEPTANCE_ANCHOR_PATH_INVALID")
            else:
                path = ROOT / rel
                if not path.is_file():
                    row_errors.append("ACCEPTANCE_ANCHOR_MISSING")
                elif not isinstance(sha, str) or _git_blob_sha(path) != sha:
                    row_errors.append("ACCEPTANCE_ANCHOR_DRIFT")

        row_errors.extend(_validate_certificate(family, row.get("certificate")))
        passed = not row_errors
        if passed:
            complete += 1
        route_results[family] = {"pass": passed, "errors": sorted(set(row_errors))}
        errors.extend(family + "::" + e for e in row_errors)

    c_closed = (
        not errors
        and len(credited) == 5
        and complete == len(credited)
    )
    return {
        "schema": SCHEMA,
        "status": "PASS__C_CLOSED" if c_closed else "PASS__REGISTRY_BOUND__C_OPEN",
        "credited_family_count": len(credited),
        "credited_families": credited,
        "declared_route_count": len(routes),
        "complete_transform_certificate_count": complete,
        "open_transform_certificate_count": len(credited) - complete,
        "route_results": route_results,
        "errors": sorted(set(errors)),
        "c_closed": c_closed,
        "b9_independent_escape_deleted": c_closed,
        "terminal": False,
        "terminal_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(compile_current(), indent=2, sort_keys=True))
