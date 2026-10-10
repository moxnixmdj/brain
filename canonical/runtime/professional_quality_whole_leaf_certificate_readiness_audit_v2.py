"""Audit professional whole-leaf certificate readiness under claim-scoped V2.

A leaf is ready for property-truth work only after one exact quartet exists:
1. frozen whole-leaf claim scope,
2. independent whole-domain equivalence verification,
3. claim-bound whole-leaf scope certificate,
4. independent scope-cover verification.

The V2 shared gate adjudicates the quartet. Absence is ordinary certificate
construction work, not evidence of a missing capability primitive.
"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_whole_leaf_claim_scope_gate_v2 as gate

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_WHOLE_LEAF_CERTIFICATE_READINESS_AUDIT_V2"
LEDGER_PATH = "canonical/governance/PROFESSIONAL_QUALITY_WHOLE_LEAF_RESIDUAL_LEDGER_20261010_V1.json"
LEDGER_BLOB = "ae5503829ad340cccef287f37ff70e4ab9288d33"
ACTIVATION_PATH = "canonical/governance/PROFESSIONAL_QUALITY_WHOLE_LEAF_CERTIFICATE_GATE_ACTIVATION_20261010_V2.json"
ACTIVATION_BLOB = "34fdaf7f4a91d0e28d446a9d554c3aa0fbec8222"

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

def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "leaf_count": 0,
        "admissible_chain_count": 0,
        "claim_scope_construction_required_count": 0,
        "incomplete_or_ambiguous_chain_count": 0,
        "property_truth_ready_count": 0,
        "new_primitive_required": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }

def audit(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    for rel, expected, label in (
        (LEDGER_PATH, LEDGER_BLOB, "WHOLE_LEAF_LEDGER"),
        (ACTIVATION_PATH, ACTIVATION_BLOB, "V2_GATE_ACTIVATION"),
    ):
        path = root / rel
        if not path.is_file() or path.is_symlink():
            return _fail(label + "_MISSING")
        if _blob(path) != expected:
            return _fail(label + "_STALE")

    ledger = _load(root / LEDGER_PATH)
    activation = _load(root / ACTIVATION_PATH)
    if not ledger:
        return _fail("WHOLE_LEAF_LEDGER_INVALID")
    if not activation or not str(activation.get("status") or "").startswith("ACTIVE_CANDIDATE__INDEPENDENTLY_VERIFIED_CLAIM_SCOPED_WHOLE_LEAF_GATE"):
        return _fail("V2_GATE_ACTIVATION_INVALID")

    rows = ledger.get("leaves")
    if not isinstance(rows, list) or len(rows) != 24:
        return _fail("WHOLE_LEAF_LEDGER_ROWS_INVALID")
    leaf_ids: list[str] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            return _fail("WHOLE_LEAF_LEDGER_ROW_INVALID")
        leaf = row.get("leaf_id")
        if not isinstance(leaf, str) or not leaf or leaf in seen:
            return _fail("WHOLE_LEAF_LEDGER_LEAF_ID_INVALID")
        if row.get("whole_leaf_closed") is not False:
            return _fail("LEDGER_UNEXPECTED_WHOLE_LEAF_CLOSURE")
        seen.add(leaf)
        leaf_ids.append(leaf)

    claim_scopes = _scan_schema(root, "canonical/governance", gate.CLAIM_SCOPE_SCHEMA)
    claim_verifies = _scan_schema(root, "canonical/verification", gate.CLAIM_VERIFY_SCHEMA)
    certs = _scan_schema(root, "canonical/governance", gate.CERT_SCHEMA)
    cert_verifies = _scan_schema(root, "canonical/verification", gate.CERT_VERIFY_SCHEMA)

    results: list[dict[str, Any]] = []
    for leaf in sorted(leaf_ids):
        groups = {
            "claim_scope": claim_scopes.get(leaf, []),
            "claim_verification": claim_verifies.get(leaf, []),
            "certificate": certs.get(leaf, []),
            "certificate_verification": cert_verifies.get(leaf, []),
        }
        counts = {name: len(items) for name, items in groups.items()}
        if all(n == 0 for n in counts.values()):
            results.append({
                "leaf_id": leaf,
                "state": "CLAIM_SCOPE_AND_TOTALITY_CHAIN_REQUIRED",
                "counts": counts,
                "whole_leaf_domain_equivalence_proved": False,
                "whole_leaf_scope_complete": False,
                "property_truth_ready": False,
                "next": "FREEZE_EXACT_WHOLE_LEAF_CLAIM_SCOPE_AND_INDEPENDENTLY_PROVE_DOMAIN_EQUIVALENCE__THEN_BUILD_CLAIM_BOUND_TOTALITY_OR_COMPLETE_UNION_CERTIFICATE",
            })
            continue
        if any(n != 1 for n in counts.values()):
            results.append({
                "leaf_id": leaf,
                "state": "FAIL_CLOSED_INCOMPLETE_OR_AMBIGUOUS_V2_CHAIN",
                "counts": counts,
                "whole_leaf_domain_equivalence_proved": False,
                "whole_leaf_scope_complete": False,
                "property_truth_ready": False,
                "next": "REDUCE_TO_EXACTLY_ONE_CONTENT_ADDRESSED_CLAIM_SCOPE_DOMAIN_VERIFICATION_CERTIFICATE_AND_CERTIFICATE_VERIFICATION",
            })
            continue

        refs = {}
        for name, items in groups.items():
            rel, blob, _ = items[0]
            refs[name] = {"path": rel, "git_blob_sha": blob}
        verdict = gate.verify_entry(refs, repo_root=root)
        passed = verdict.get("pass") is True
        results.append({
            "leaf_id": leaf,
            "state": "ADMISSIBLE_V2_WHOLE_LEAF_SCOPE_CHAIN" if passed else "V2_CHAIN_REJECTED_BY_SHARED_GATE",
            "counts": counts,
            "claim_id": verdict.get("claim_id"),
            "whole_leaf_domain_equivalence_proved": verdict.get("whole_leaf_domain_equivalence_proved") is True,
            "whole_leaf_scope_complete": verdict.get("whole_leaf_scope_complete") is True,
            "property_truth_ready": passed,
            "gate_status": verdict.get("status"),
            "gate_reason": verdict.get("reason"),
            "next": (
                "RUN_SEPARATE_LEAF_PROPERTY_TRUTH_AND_EXECUTION_VERIFICATION"
                if passed else
                "REPAIR_ONLY_THE_EXACT_V2_GATE_REJECTION_PREMISE"
            ),
        })

    admitted = sum(r["state"] == "ADMISSIBLE_V2_WHOLE_LEAF_SCOPE_CHAIN" for r in results)
    construction = sum(r["state"] == "CLAIM_SCOPE_AND_TOTALITY_CHAIN_REQUIRED" for r in results)
    incomplete = len(results) - admitted - construction
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": (
            "PASS__ALL_24_LEAVES_AUDITED__ZERO_V2_ADMISSIBLE_CHAINS"
            if admitted == 0 else
            "PASS__V2_WHOLE_LEAF_READINESS_AUDITED"
        ),
        "leaf_count": len(results),
        "admissible_chain_count": admitted,
        "claim_scope_construction_required_count": construction,
        "incomplete_or_ambiguous_chain_count": incomplete,
        "property_truth_ready_count": admitted,
        "leaves": results,
        "scheduler_rule": (
            "PROPERTY_TRUTH_WORK_ONLY_AFTER_V2_CLAIM_SCOPE_DOMAIN_EQUIVALENCE_AND_SCOPE_COVER_ADMISSION__"
            "OTHERWISE_WORK_ONLY_CLAIM_SCOPE_FACTORIZATION_TOTALITY_COMPLETE_UNION_OR_EXACT_GATE_REJECTION_PREMISES"
        ),
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
