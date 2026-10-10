"""Audit professional whole-leaf readiness against the claim-scoped V2 gate.

V1 readiness scans legacy certificate/verification pairs.  Once the V2 gate
became canonical, that is insufficient: V2 admission additionally requires one
content-addressed whole-leaf claim scope and its independent domain-equivalence
verification.  This audit discovers only V2 candidate quartets and delegates
authority to the V2 gate.  Legacy V1-only artifacts are intentionally invisible
to admission.

The audit grants no property truth, quality, execution, acceptance, promotion,
or terminal authority.
"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_whole_leaf_claim_scope_gate_v2 as gate

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_WHOLE_LEAF_CLAIM_SCOPE_READINESS_AUDIT_V2"
LEDGER_PATH = "canonical/governance/PROFESSIONAL_QUALITY_WHOLE_LEAF_RESIDUAL_LEDGER_20261010_V1.json"
LEDGER_BLOB = "ae5503829ad340cccef287f37ff70e4ab9288d33"


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _load(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def _scan_schema(
    root: Path,
    base: str,
    schema: str,
) -> dict[str, list[tuple[str, str, dict[str, Any]]]]:
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
        "admissible_claim_scope_count": 0,
        "admissible_scope_certificate_count": 0,
        "claim_scope_or_totality_required_count": 0,
        "candidate_rejected_or_ambiguous_count": 0,
        "legacy_v1_artifacts_have_v2_admission_authority": False,
        "new_primitive_required": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def audit(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    ledger_path = root / LEDGER_PATH
    if not ledger_path.is_file() or ledger_path.is_symlink():
        return _fail("WHOLE_LEAF_LEDGER_MISSING")
    if _blob(ledger_path) != LEDGER_BLOB:
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

    claim_scopes = _scan_schema(root, "canonical/governance", gate.CLAIM_SCOPE_SCHEMA)
    claim_verifies = _scan_schema(root, "canonical/verification", gate.CLAIM_VERIFY_SCHEMA)
    certificates = _scan_schema(root, "canonical/governance", gate.CERT_SCHEMA)
    certificate_verifies = _scan_schema(root, "canonical/verification", gate.CERT_VERIFY_SCHEMA)

    results: list[dict[str, Any]] = []
    for leaf in sorted(leaf_ids):
        groups = (
            claim_scopes.get(leaf, []),
            claim_verifies.get(leaf, []),
            certificates.get(leaf, []),
            certificate_verifies.get(leaf, []),
        )
        counts = tuple(len(x) for x in groups)

        if counts == (0, 0, 0, 0):
            results.append({
                "leaf_id": leaf,
                "state": "CLAIM_SCOPE_OR_TOTALITY_PROOF_REQUIRED",
                "candidate_claim_scope_count": 0,
                "candidate_claim_verification_count": 0,
                "candidate_certificate_count": 0,
                "candidate_certificate_verification_count": 0,
                "whole_leaf_domain_equivalence_proved": False,
                "whole_leaf_scope_complete": False,
                "next": (
                    "FREEZE_EXACT_WHOLE_LEAF_CLAIM_SCOPE_AND_INDEPENDENTLY_PROVE_"
                    "DOMAIN_EQUIVALENCE__THEN_PROVE_SCOPE_COVER"
                ),
            })
            continue

        if counts != (1, 1, 1, 1):
            results.append({
                "leaf_id": leaf,
                "state": "FAIL_CLOSED_AMBIGUOUS_OR_INCOMPLETE_V2_CANDIDATE_SET",
                "candidate_claim_scope_count": counts[0],
                "candidate_claim_verification_count": counts[1],
                "candidate_certificate_count": counts[2],
                "candidate_certificate_verification_count": counts[3],
                "whole_leaf_domain_equivalence_proved": False,
                "whole_leaf_scope_complete": False,
                "next": (
                    "REDUCE_TO_ONE_EXACT_CLAIM_SCOPE_ONE_DOMAIN_EQUIVALENCE_VERIFICATION_"
                    "ONE_SCOPE_CERTIFICATE_AND_ONE_CERTIFICATE_VERIFICATION"
                ),
            })
            continue

        cs_path, cs_blob, _ = groups[0][0]
        cv_path, cv_blob, _ = groups[1][0]
        cert_path, cert_blob, _ = groups[2][0]
        sv_path, sv_blob, _ = groups[3][0]
        verdict = gate.verify_entry({
            "claim_scope": {"path": cs_path, "git_blob_sha": cs_blob},
            "claim_verification": {"path": cv_path, "git_blob_sha": cv_blob},
            "certificate": {"path": cert_path, "git_blob_sha": cert_blob},
            "certificate_verification": {"path": sv_path, "git_blob_sha": sv_blob},
        }, repo_root=root)
        passed = verdict.get("pass") is True
        results.append({
            "leaf_id": leaf,
            "state": (
                "ADMISSIBLE_V2_CLAIM_SCOPE_AND_SCOPE_CERTIFICATE"
                if passed else "V2_CANDIDATE_REJECTED_BY_CLAIM_SCOPED_GATE"
            ),
            "candidate_claim_scope_count": 1,
            "candidate_claim_verification_count": 1,
            "candidate_certificate_count": 1,
            "candidate_certificate_verification_count": 1,
            "claim_scope_path": cs_path,
            "claim_verification_path": cv_path,
            "certificate_path": cert_path,
            "certificate_verification_path": sv_path,
            "whole_leaf_domain_equivalence_proved": (
                verdict.get("whole_leaf_domain_equivalence_proved") is True
            ),
            "whole_leaf_scope_complete": verdict.get("whole_leaf_scope_complete") is True,
            "gate_status": verdict.get("status"),
            "gate_reason": verdict.get("reason"),
            "next": (
                "RUN_PROPERTY_TRUTH_VERIFICATION_FOR_THIS_SCOPE_COMPLETE_LEAF"
                if passed
                else "REPAIR_ONLY_THE_EXACT_V2_GATE_REJECTION_PREMISE"
            ),
        })

    admitted = sum(
        x["state"] == "ADMISSIBLE_V2_CLAIM_SCOPE_AND_SCOPE_CERTIFICATE"
        for x in results
    )
    no_candidate = sum(
        x["state"] == "CLAIM_SCOPE_OR_TOTALITY_PROOF_REQUIRED"
        for x in results
    )
    rejected = len(results) - admitted - no_candidate
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": (
            "PASS__ALL_CURRENT_LEAVES_AUDITED_UNDER_V2__NO_ADMISSIBLE_CERTIFICATES"
            if admitted == 0 else
            "PASS__CURRENT_V2_LEAF_CERTIFICATE_READINESS_AUDITED"
        ),
        "leaf_count": len(results),
        "admissible_claim_scope_count": admitted,
        "admissible_scope_certificate_count": admitted,
        "claim_scope_or_totality_required_count": no_candidate,
        "candidate_rejected_or_ambiguous_count": rejected,
        "leaves": results,
        "scheduler_rule": (
            "PROPERTY_TRUTH_WORK_ONLY_AFTER_V2_CLAIM_SCOPE_DOMAIN_EQUIVALENCE_AND_"
            "SCOPE_CERTIFICATE_ADMISSION__LEGACY_V1_CERTIFICATES_HAVE_ZERO_V2_AUTHORITY"
        ),
        "legacy_v1_artifacts_have_v2_admission_authority": False,
        "new_primitive_required": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))
