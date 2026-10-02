"""Fail-closed activation-only equivalence for independently verified bindings.

This module proves that a current activated binding differs from the exact blob
independently verified earlier only in a tiny allow-list of activation metadata.
It does not grant family, acceptance, execution, or promotion credit.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_ACTIVATION_ONLY_BINDING_EQUIVALENCE_V1"


def git_blob_sha_text(text: str) -> str:
    b = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()


def git_blob_sha_path(path: Path) -> str:
    return git_blob_sha_text(path.read_text(encoding="utf-8"))


def _project(doc: Mapping[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(dict(doc))
    out.pop("status", None)
    out.pop("prewave_admissible", None)
    out.pop("independent_verification", None)
    gates = out.get("route_gates")
    if isinstance(gates, dict):
        gates.pop("independent_verification_pass", None)
    return out


def _certifies(ver: Mapping[str, Any], path: str, sha: str) -> bool:
    exact = ver.get("exact_brain_blobs")
    if isinstance(exact, Mapping) and exact.get(path) == sha:
        return True
    jobs = ver.get("verified_jobs")
    if isinstance(jobs, list):
        for row in jobs:
            if (
                isinstance(row, Mapping)
                and row.get("binding_path") == path
                and row.get("binding_blob_sha") == sha
                and row.get("conclusion") == "success"
            ):
                return True
    return False


def _independent_pass(ver: Mapping[str, Any]) -> bool:
    status = ver.get("status")
    return isinstance(status, str) and "INDEPENDENT" in status and "PASS" in status


def evaluate_capsule(capsule: Mapping[str, Any], root: Path) -> dict[str, Any]:
    errors: list[str] = []
    rows_out: list[dict[str, Any]] = []
    bindings = capsule.get("bindings")
    if capsule.get("schema") != "PROJECT_BRAIN_OBJECTIVE_BINDING_ACTIVATION_EQUIVALENCE_CAPSULE_V1":
        errors.append("CAPSULE_SCHEMA_MISMATCH")
    if not isinstance(bindings, list) or not bindings:
        errors.append("BINDINGS_REQUIRED")
        bindings = []

    seen: set[str] = set()
    for row in bindings:
        if not isinstance(row, Mapping):
            errors.append("BINDING_ROW_INVALID")
            continue
        bid = row.get("binding_id")
        if not isinstance(bid, str) or not bid or bid in seen:
            errors.append("BINDING_ID_INVALID_OR_DUPLICATE")
            continue
        seen.add(bid)
        prefix = f"{bid}:"

        current_path = row.get("current_path")
        old_raw = row.get("verified_blob_content")
        old_sha = row.get("verified_blob_sha")
        current_sha = row.get("current_blob_sha")
        act_path = row.get("activation_verification_path")
        act_sha = row.get("activation_verification_blob_sha")
        scope_path = row.get("scope_verification_path")
        scope_sha = row.get("scope_verification_blob_sha")
        required_markers = row.get("required_scope_markers")
        component_id = row.get("component_id")
        interface_id = row.get("interface_id")

        scalar_strings = [
            current_path, old_raw, old_sha, current_sha, act_path, act_sha,
            scope_path, scope_sha, component_id, interface_id,
        ]
        if any(not isinstance(x, str) or not x for x in scalar_strings):
            errors.append(prefix + "REQUIRED_STRING_FIELD_INVALID")
            continue
        if not isinstance(required_markers, list) or any(not isinstance(x, str) or not x for x in required_markers):
            errors.append(prefix + "REQUIRED_SCOPE_MARKERS_INVALID")
            continue

        current_file = root / current_path
        act_file = root / act_path
        scope_file = root / scope_path
        if not current_file.is_file() or not act_file.is_file() or not scope_file.is_file():
            errors.append(prefix + "REQUIRED_FILE_MISSING")
            continue

        current_raw = current_file.read_text(encoding="utf-8")
        act_raw = act_file.read_text(encoding="utf-8")
        scope_raw = scope_file.read_text(encoding="utf-8")
        if git_blob_sha_text(old_raw) != old_sha:
            errors.append(prefix + "EMBEDDED_VERIFIED_BLOB_SHA_MISMATCH")
        if git_blob_sha_text(current_raw) != current_sha:
            errors.append(prefix + "CURRENT_BLOB_SHA_MISMATCH")
        if git_blob_sha_text(act_raw) != act_sha:
            errors.append(prefix + "ACTIVATION_VERIFICATION_BLOB_SHA_MISMATCH")
        if git_blob_sha_text(scope_raw) != scope_sha:
            errors.append(prefix + "SCOPE_VERIFICATION_BLOB_SHA_MISMATCH")

        try:
            old_doc = json.loads(old_raw)
            current_doc = json.loads(current_raw)
            act_doc = json.loads(act_raw)
            scope_doc = json.loads(scope_raw)
        except Exception:
            errors.append(prefix + "JSON_PARSE_FAILURE")
            continue

        if not _independent_pass(act_doc) or not _certifies(act_doc, current_path, old_sha):
            errors.append(prefix + "ACTIVATION_VERIFICATION_DOES_NOT_CERTIFY_OLD_BLOB")
        if not _independent_pass(scope_doc) or not _certifies(scope_doc, current_path, old_sha):
            errors.append(prefix + "SCOPE_VERIFICATION_DOES_NOT_CERTIFY_OLD_BLOB")

        markers = set(scope_doc.get("verified") or [])
        missing_markers = sorted(set(required_markers) - markers)
        if missing_markers:
            errors.append(prefix + "SCOPE_VERIFICATION_MARKERS_MISSING:" + ",".join(missing_markers))

        old_gates = old_doc.get("route_gates")
        current_gates = current_doc.get("route_gates")
        if not isinstance(old_gates, Mapping) or old_gates.get("independent_verification_pass") is not False:
            errors.append(prefix + "OLD_BINDING_NOT_PREACTIVATION")
        if not isinstance(current_gates, Mapping) or current_gates.get("independent_verification_pass") is not True:
            errors.append(prefix + "CURRENT_BINDING_NOT_ACTIVATED")
        if old_doc.get("prewave_admissible") is not False:
            errors.append(prefix + "OLD_PREWAVE_ADMISSIBLE_NOT_FALSE")
        if current_doc.get("prewave_admissible") is not True:
            errors.append(prefix + "CURRENT_PREWAVE_ADMISSIBLE_NOT_TRUE")
        if current_doc.get("independent_verification") != act_path:
            errors.append(prefix + "CURRENT_VERIFICATION_POINTER_MISMATCH")

        if _project(old_doc) != _project(current_doc):
            errors.append(prefix + "NON_ACTIVATION_SEMANTIC_MUTATION_DETECTED")

        rows_out.append({
            "binding_id": bid,
            "component_id": component_id,
            "interface_id": interface_id,
            "current_path": current_path,
            "verified_pre_activation_blob_sha": old_sha,
            "current_activated_blob_sha": current_sha,
            "activation_verification_path": act_path,
            "scope_verification_path": scope_path,
            "required_scope_markers": sorted(required_markers),
            "activation_only_equivalent": not any(e.startswith(prefix) for e in errors),
        })

    passed = not errors and len(rows_out) == len(bindings)
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__CURRENT_BINDINGS_EQUIVALENT_TO_INDEPENDENTLY_VERIFIED_BLOBS_MODULO_ACTIVATION_METADATA"
            if passed else "FAIL_CLOSED"
        ),
        "pass": passed,
        "errors": sorted(set(errors)),
        "binding_count": len(bindings),
        "rows": rows_out,
        "rule": "ONLY_STATUS_PREWAVE_ADMISSIBLE_INDEPENDENT_VERIFICATION_POINTER_AND_ROUTE_GATE_VERIFICATION_BOOLEAN_MAY_CHANGE",
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    capsule_path = root / "canonical/governance/OBJECTIVE_BINDING_ACTIVATION_EQUIVALENCE_V1.json"
    capsule = json.loads(capsule_path.read_text(encoding="utf-8"))
    out = evaluate_capsule(capsule, root)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
