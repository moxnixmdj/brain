"""Audit current professional whole-leaf certificate readiness.

This module does not prove scope completeness. It discovers content-addressed
whole-leaf certificate candidates already present in the repository, pairs them
with independent semantic-verification receipts, and asks the already-verified
shared gate to admit or reject them. Leaves without an admissible candidate are
classified as residual partition work, not as missing primitive capabilities.
"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_whole_leaf_certificate_gate_v1 as gate

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_WHOLE_LEAF_CERTIFICATE_READINESS_AUDIT_V1"

def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

def _load(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return value if isinstance(value, dict) else None

def _scan_schema(root: Path, base: str, schema: str) -> dict[str, list[tuple[str, str, dict[str, Any]]]]:
    out: dict[str, list[tuple[str, str, dict[str, Any]]]] = defaultdict(list)
    start = root / base
    if not start.is_dir():
        return out
    for path in sorted(start.rglob("*.json")):
        if path.is_symlink() or not path.is_file():
            continue
        doc = _load(path)
        if not doc or doc.get("schema") != schema:
            continue
        leaf = doc.get("leaf_id")
        if not isinstance(leaf, str) or not leaf:
            continue
        rel = path.relative_to(root).as_posix()
        out[leaf].append((rel, _blob(path), doc))
    return out

def audit(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    ledger_path = root / gate.LEDGER_PATH
    if not ledger_path.is_file() or ledger_path.is_symlink():
        return _fail("WHOLE_LEAF_LEDGER_MISSING")
    if _blob(ledger_path) != gate.LEDGER_BLOB:
        return _fail("WHOLE_LEAF_LEDGER_STALE")
    ledger = _load(ledger_path)
    if not ledger:
        return _fail("WHOLE_LEAF_LEDGER_INVALID")
    rows = ledger.get("leaves")
    if not isinstance(rows, list) or not rows:
        return _fail("WHOLE_LEAF_LEDGER_ROWS_INVALID")

    leaf_ids: list[str] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            return _fail("WHOLE_LEAF_LEDGER_ROW_INVALID")
        leaf = row.get("leaf_id")
        if not isinstance(leaf, str) or not leaf or leaf in seen:
            return _fail("WHOLE_LEAF_LEDGER_LEAF_ID_INVALID")
        seen.add(leaf)
        leaf_ids.append(leaf)

    certs = _scan_schema(root, "canonical/governance", gate.CERT_SCHEMA)
    verifies = _scan_schema(root, "canonical/verification", gate.VERIFY_SCHEMA)

    results: list[dict[str, Any]] = []
    for leaf in sorted(leaf_ids):
        cs = certs.get(leaf, [])
        vs = verifies.get(leaf, [])
        if not cs and not vs:
            results.append({
                "leaf_id": leaf,
                "state": "PARTITION_OR_TOTALITY_PROOF_REQUIRED",
                "candidate_certificate_count": 0,
                "candidate_verification_count": 0,
                "whole_leaf_scope_complete": False,
                "next": "PROVE_CLAIM_SCOPED_TOTALITY_OR_CONSTRUCT_CERTIFIED_COMPLETE_UNION",
            })
            continue
        if len(cs) != 1 or len(vs) != 1:
            results.append({
                "leaf_id": leaf,
                "state": "FAIL_CLOSED_AMBIGUOUS_OR_INCOMPLETE_CANDIDATE_SET",
                "candidate_certificate_count": len(cs),
                "candidate_verification_count": len(vs),
                "whole_leaf_scope_complete": False,
                "next": "REDUCE_TO_ONE_EXACT_CONTENT_ADDRESSED_CERTIFICATE_AND_ONE_INDEPENDENT_VERIFICATION",
            })
            continue

        cert_path, cert_blob, _ = cs[0]
        verify_path, verify_blob, _ = vs[0]
        verdict = gate.verify_entry({
            "leaf_id": leaf,
            "certificate": {"path": cert_path, "git_blob_sha": cert_blob},
            "verification": {"path": verify_path, "git_blob_sha": verify_blob},
        }, repo_root=root)
        results.append({
            "leaf_id": leaf,
            "state": "ADMISSIBLE_SCOPE_CERTIFICATE" if verdict.get("pass") is True else "CANDIDATE_REJECTED_BY_SHARED_GATE",
            "candidate_certificate_count": 1,
            "candidate_verification_count": 1,
            "certificate_path": cert_path,
            "verification_path": verify_path,
            "whole_leaf_scope_complete": verdict.get("whole_leaf_scope_complete") is True,
            "gate_status": verdict.get("status"),
            "gate_reason": verdict.get("reason"),
            "next": (
                "RUN_PROPERTY_TRUTH_VERIFICATION_FOR_THIS_SCOPE_COMPLETE_LEAF"
                if verdict.get("pass") is True
                else "REPAIR_ONLY_THE_SHARED_GATE_REJECTION_PREMISE"
            ),
        })

    admitted = sum(r["state"] == "ADMISSIBLE_SCOPE_CERTIFICATE" for r in results)
    partition = sum(r["state"] == "PARTITION_OR_TOTALITY_PROOF_REQUIRED" for r in results)
    rejected = len(results) - admitted - partition
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": (
            "PASS__ALL_CURRENT_LEAVES_AUDITED__NO_ADMISSIBLE_CERTIFICATES"
            if admitted == 0 else
            "PASS__CURRENT_LEAF_CERTIFICATE_READINESS_AUDITED"
        ),
        "leaf_count": len(results),
        "admissible_scope_certificate_count": admitted,
        "partition_or_totality_required_count": partition,
        "candidate_rejected_or_ambiguous_count": rejected,
        "leaves": results,
        "scheduler_rule": (
            "PROPERTY_TRUTH_WORK_ONLY_AFTER_SCOPE_CERTIFICATE_ADMISSION__"
            "OTHERWISE_WORK_ONLY_TOTALITY_COMPLETE_UNION_OR_EXACT_GATE_REJECTION_PREMISES"
        ),
        "new_primitive_required": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }

def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "leaf_count": 0,
        "admissible_scope_certificate_count": 0,
        "partition_or_totality_required_count": 0,
        "candidate_rejected_or_ambiguous_count": 0,
        "new_primitive_required": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }

if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))
