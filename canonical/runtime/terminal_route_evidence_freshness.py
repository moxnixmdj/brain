"""Exact-byte freshness guard for terminal-route proof evidence."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping

VERIFICATION_KEYS = (
    "current_blob_revalidation",
    "terminal_acceptance_mode_verification",
    "population_binding_verification",
    "scope_gate_verification",
    "structural_variety_verification",
    "render_preflight",
    "independent_preflight",
    "preflight_verification",
    "scope_audit_verification",
)
ARTIFACT_KEYS = (
    "candidate",
    "route",
    "preflight_manifest",
    "whole_dimension_preflight",
    "scope_gate_input",
    "scope_equivalence_relation",
    "structural_variety_route",
    "render_route",
    "terminal_population_binding",
    "terminal_population_binding_test",
    "terminal_acceptance_binding",
    "terminal_acceptance_mode",
)

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()

def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON_NOT_OBJECT:" + str(path))
    return value

def _exact_map(receipt: Mapping[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in ("exact_bound_blobs", "exact_brain_blobs"):
        value = receipt.get(key)
        if isinstance(value, Mapping):
            for p, sha in value.items():
                if isinstance(p, str) and isinstance(sha, str) and p and sha:
                    out[p] = sha
    return out

def evaluate_row_evidence_freshness(root: Path, row: Mapping[str, Any]) -> dict[str, Any]:
    bid = str(row.get("behavior_id") or "")
    receipt_rows = []
    receipt_errors = []
    for key in VERIFICATION_KEYS:
        rel = row.get(key)
        if not isinstance(rel, str) or not rel.startswith("canonical/"):
            continue
        path = root / rel
        if not path.is_file():
            receipt_errors.append("VERIFICATION_RECEIPT_MISSING:" + key + ":" + rel)
            continue
        try:
            rec = _json(path)
        except Exception as exc:
            receipt_errors.append("VERIFICATION_RECEIPT_INVALID:" + key + ":" + type(exc).__name__)
            continue
        status = str(rec.get("status") or "")
        if "PASS" not in status:
            receipt_errors.append("VERIFICATION_RECEIPT_NOT_PASS:" + key + ":" + status)
        receipt_rows.append({"key": key, "path": rel, "exact": _exact_map(rec), "status": status})

    artifacts = []
    seen = set()
    for key in ARTIFACT_KEYS:
        rel = row.get(key)
        if not isinstance(rel, str) or not rel.startswith("canonical/") or rel in seen:
            continue
        path = root / rel
        if not path.is_file():
            continue
        seen.add(rel)
        artifacts.append({"key": key, "path": rel, "current_blob_sha": git_blob_sha(path)})

    mismatches = []
    bindings = []
    for art in artifacts:
        for receipt in receipt_rows:
            expected = receipt["exact"].get(art["path"])
            if not expected:
                continue
            binding = {
                "artifact_key": art["key"],
                "artifact_path": art["path"],
                "receipt_key": receipt["key"],
                "receipt_path": receipt["path"],
                "expected_blob_sha": expected,
                "current_blob_sha": art["current_blob_sha"],
            }
            bindings.append(binding)
            if expected != art["current_blob_sha"]:
                mismatches.append(binding)
            break

    blockers = [
        "STALE_INDEPENDENT_EVIDENCE_BINDING:"
        + m["artifact_path"]
        + ":verified=" + m["expected_blob_sha"]
        + ":current=" + m["current_blob_sha"]
        for m in mismatches
    ]
    blockers += ["EVIDENCE_RECEIPT_ERROR:" + x for x in receipt_errors]
    return {
        "schema": "PROJECT_BRAIN_TERMINAL_ROUTE_EVIDENCE_FRESHNESS_V1",
        "behavior_id": bid,
        "status": "STALE_OR_INVALID" if blockers else "NO_DETECTED_STALENESS",
        "stale": bool(blockers),
        "blockers": blockers,
        "mismatches": mismatches,
        "receipt_errors": receipt_errors,
        "bindings_checked": bindings,
        "execution_authority": False,
        "promotion_authority": False,
    }
