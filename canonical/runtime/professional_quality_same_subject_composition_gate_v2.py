"""Real-receipt same-subject composition gate for professional quality.

V1 proved the structural rule using one synthetic generic verification schema.
V2 preserves that rule but admits only the exact bounded verification receipt
families already promoted for R1-R12. It does not widen root scope or grant
quality, acceptance, promotion, or terminal authority.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_same_subject_composition_gate_v1 as v1

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_SAME_SUBJECT_COMPOSITION_GATE_V2"
ROOT = v1.ROOT
EXPECTED_ROOTS = v1.EXPECTED_ROOTS
SCOPED_REGISTRY_PATH = "canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json"
SCOPED_REGISTRY_BLOB = "b9ddf7cbe7fbfad0e81fe068a0c19b48703b5aba"
SCOPED_REGISTRY_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_V1"

EXPECTED_VERIFY_SCHEMAS = {
    "R1_TARGET_SPECIFICATION": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R1_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1",
    "R2_CANDIDATE_SEARCH": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R2_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1",
    "R3_REALIZATION_OBSERVATION": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R3_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V2",
    "R4_MEASUREMENT_CONSTRUCT": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R4_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1",
    "R5_EVALUATOR_REFERENCE": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R5_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1",
    "R6_EVIDENCE_GROUNDING_DEPENDENCE": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R6_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1",
    "R7_CAUSAL_PRESCRIPTIVE": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R7_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1",
    "R8_POPULATION_CONTEXT_OPERATOR": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R8_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1",
    "R9_TEMPORAL_DEPLOYMENT": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R9_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1",
    "R10_ANALYSIS_DECISION": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R10_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1",
    "R11_ADAPTIVE_INTEGRITY_SECURITY": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R11_V7_ROOT_SUBJECT_BINDING_PUBLIC_VERIFY_V1",
    "R12_META_COMPOSITION_CLOSURE": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R12_V7_ROOT_SUBJECT_BINDING_PUBLIC_VERIFY_V1",
}


def _authority(doc: Mapping[str, Any], field: str) -> Any:
    if field in doc:
        return doc.get(field)
    nested = doc.get("authority")
    if isinstance(nested, Mapping):
        return nested.get(field)
    return None


def _binding_claim(root_id: str, doc: Mapping[str, Any]) -> tuple[str | None, str | None]:
    if root_id == "R1_TARGET_SPECIFICATION":
        row = (doc.get("current_main_subject") or {}).get("binding") or {}
        return row.get("path"), row.get("git_blob_sha")
    if root_id == "R2_CANDIDATE_SEARCH":
        row = doc.get("exact_subject") or {}
        return row.get("binding_path"), row.get("binding_git_blob_sha")
    if root_id == "R3_REALIZATION_OBSERVATION":
        return None, (doc.get("exact_blobs") or {}).get("v2_binding")
    if root_id in {
        "R4_MEASUREMENT_CONSTRUCT",
        "R5_EVALUATOR_REFERENCE",
        "R6_EVIDENCE_GROUNDING_DEPENDENCE",
        "R7_CAUSAL_PRESCRIPTIVE",
        "R8_POPULATION_CONTEXT_OPERATOR",
        "R9_TEMPORAL_DEPLOYMENT",
        "R10_ANALYSIS_DECISION",
    }:
        return None, (doc.get("exact_blobs") or {}).get("binding")
    if root_id in {"R11_ADAPTIVE_INTEGRITY_SECURITY", "R12_META_COMPOSITION_CLOSURE"}:
        row = doc.get("binding") or {}
        return row.get("path"), row.get("git_blob_sha")
    return None, None


def _subject_claim(root_id: str, doc: Mapping[str, Any]) -> tuple[str | None, str | None, str | None, str | None]:
    if root_id == "R1_TARGET_SPECIFICATION":
        row = (doc.get("current_main_subject") or {}).get("declared_system") or {}
        return row.get("subject_id"), row.get("subject_sha256"), row.get("path"), row.get("git_blob_sha")
    if root_id == "R2_CANDIDATE_SEARCH":
        row = doc.get("exact_subject") or {}
        return row.get("subject_id"), row.get("subject_sha256"), None, None
    if root_id == "R4_MEASUREMENT_CONSTRUCT":
        row = doc.get("subject") or {}
        return row.get("subject_id"), row.get("subject_sha256"), None, (doc.get("exact_blobs") or {}).get("subject")
    if root_id in {"R11_ADAPTIVE_INTEGRITY_SECURITY", "R12_META_COMPOSITION_CLOSURE"}:
        row = doc.get("subject") or {}
        return row.get("id"), row.get("sha256"), row.get("path"), row.get("git_blob_sha")
    exact = doc.get("exact_blobs") or {}
    return None, None, None, exact.get("subject")


def _verification_evidence_ok(
    root_id: str,
    verification: Mapping[str, Any],
    *,
    verification_path: str,
    binding_path: str,
    binding_blob: str,
    binding: Mapping[str, Any],
) -> tuple[bool, str | None]:
    if verification.get("schema") != EXPECTED_VERIFY_SCHEMAS.get(root_id):
        return False, "VERIFY_SCHEMA_NOT_EXPLICITLY_ADMITTED"
    status = str(verification.get("status") or "")
    if root_id in {"R11_ADAPTIVE_INTEGRITY_SECURITY", "R12_META_COMPOSITION_CLOSURE"}:
        if not status.startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__"):
            return False, "PUBLIC_VERIFY_STATUS_NOT_PASS"
        runner = verification.get("public_runner") or {}
        if not (
            runner.get("conclusion") == "success"
            and runner.get("exact_blob_binding_step") == "success"
            and runner.get("root_verifier_step") == "success"
            and runner.get("adversarial_test_step") == "success"
        ):
            return False, "PUBLIC_RUNNER_EVIDENCE_INCOMPLETE"
    elif not status.startswith("PASS__"):
        return False, "VERIFY_STATUS_NOT_PASS"

    if _authority(verification, "root_subject_binding_authority") is not True:
        return False, "ROOT_SUBJECT_BINDING_AUTHORITY_REQUIRED"
    if _authority(verification, "terminal_authority") is not False:
        return False, "VERIFY_TERMINAL_AUTHORITY_FORBIDDEN"

    claimed_path, claimed_blob = _binding_claim(root_id, verification)
    if claimed_blob != binding_blob:
        return False, "VERIFY_BINDING_BLOB_MISMATCH"
    if claimed_path is not None and claimed_path != binding_path:
        return False, "VERIFY_BINDING_PATH_MISMATCH"

    subject_id = binding.get("subject_id")
    subject_sha = binding.get("subject_sha256")
    subject_ref = binding.get("subject") or {}
    sid, ssha, spath, sblob = _subject_claim(root_id, verification)
    if sid is not None and sid != subject_id:
        return False, "VERIFY_SUBJECT_ID_MISMATCH"
    if ssha is not None and ssha != subject_sha:
        return False, "VERIFY_SUBJECT_SHA_MISMATCH"
    if spath is not None and spath != subject_ref.get("path"):
        return False, "VERIFY_SUBJECT_PATH_MISMATCH"
    if sblob is not None and sblob != subject_ref.get("git_blob_sha"):
        return False, "VERIFY_SUBJECT_BLOB_MISMATCH"

    if verification.get("root_id") is not None and verification.get("root_id") != root_id:
        return False, "VERIFY_ROOT_ID_MISMATCH"
    return True, None


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    out = v1._base(status, passed=passed, **extra)
    out["schema"] = SCHEMA
    return out


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return _base("FAIL_CLOSED", reason=reason, **extra)


def evaluate(payload: Mapping[str, Any], *, repo_root: str | Path | None = None) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_NOT_OBJECT")
    root = Path(repo_root).resolve() if repo_root is not None else ROOT

    normal_ok, normal_record = v1._normal_form_ok(root)
    if not normal_ok:
        return _fail("NORMAL_FORM_SAME_SUBJECT_LAW_UNAVAILABLE", normal_form=normal_record)

    scoped_doc, _, scoped_error = v1._read_bound(
        root,
        {"path": SCOPED_REGISTRY_PATH, "git_blob_sha": SCOPED_REGISTRY_BLOB},
        label="SCOPED_EVIDENCE_REGISTRY",
    )
    if scoped_error is not None or scoped_doc is None:
        return _fail("SCOPED_EVIDENCE_REGISTRY_NOT_CURRENT", detail=scoped_error)
    if scoped_doc.get("schema") != SCOPED_REGISTRY_SCHEMA:
        return _fail("SCOPED_EVIDENCE_REGISTRY_SCHEMA_INVALID")
    admitted = scoped_doc.get("entries")
    if not isinstance(admitted, list):
        return _fail("SCOPED_EVIDENCE_ADMITTED_SCOPES_INVALID")
    admitted_roots = {str(row.get("root_id") or "") for row in admitted if isinstance(row, Mapping)}
    if admitted_roots != EXPECTED_ROOTS:
        return _fail("SCOPED_EVIDENCE_ROOT_COVER_INCOMPLETE", admitted_root_ids=sorted(admitted_roots))
    for row in admitted:
        if not isinstance(row, Mapping):
            return _fail("SCOPED_EVIDENCE_ROW_INVALID")
        if row.get("global_leaf_closure") is not False or row.get("global_root_closure") is not False:
            return _fail("SCOPED_EVIDENCE_GLOBAL_AUTHORITY_FORBIDDEN")
        if row.get("terminal_credit_delta") != 0:
            return _fail("SCOPED_EVIDENCE_TERMINAL_CREDIT_FORBIDDEN")

    rows = payload.get("root_subject_bindings")
    if not isinstance(rows, list):
        return _fail("ROOT_SUBJECT_BINDINGS_NOT_LIST")
    if not rows:
        return _base("OPEN__SAME_SUBJECT_BINDINGS_REQUIRED", normal_form=normal_record, scoped_root_count=len(admitted_roots), missing_root_ids=sorted(EXPECTED_ROOTS))

    root_rows: dict[str, Mapping[str, Any]] = {}
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            return _fail("ROOT_SUBJECT_BINDING_ROW_INVALID", row_index=i)
        root_id = row.get("root_id")
        if not isinstance(root_id, str) or root_id not in EXPECTED_ROOTS:
            return _fail("ROOT_SUBJECT_BINDING_ROOT_INVALID", row_index=i)
        if root_id in root_rows:
            return _fail("ROOT_SUBJECT_BINDING_ROOT_DUPLICATE", root_id=root_id)
        root_rows[root_id] = row

    missing = sorted(EXPECTED_ROOTS - set(root_rows))
    extra = sorted(set(root_rows) - EXPECTED_ROOTS)
    if missing or extra:
        return _base("OPEN__SAME_SUBJECT_BINDINGS_INCOMPLETE", normal_form=normal_record, missing_root_ids=missing, extra_root_ids=extra)

    verified_bindings: list[dict[str, Any]] = []
    subject_keys: set[tuple[str, str, str]] = set()
    for root_id in sorted(EXPECTED_ROOTS):
        row = root_rows[root_id]
        binding, binding_blob, error = v1._read_bound(root, row.get("binding"), label="SUBJECT_BINDING")
        if error is not None:
            return _fail(error, root_id=root_id)
        assert binding is not None and binding_blob is not None
        if binding.get("schema") != v1.BINDING_SCHEMA or binding.get("root_id") != root_id:
            return _fail("SUBJECT_BINDING_IDENTITY_INVALID", root_id=root_id)
        subject_kind = binding.get("subject_kind")
        subject_id = binding.get("subject_id")
        subject_sha = binding.get("subject_sha256")
        if (
            not isinstance(subject_kind, str) or not subject_kind.strip()
            or not isinstance(subject_id, str) or not subject_id.strip()
            or not isinstance(subject_sha, str) or len(subject_sha) != 64
            or any(ch not in "0123456789abcdef" for ch in subject_sha)
        ):
            return _fail("SUBJECT_IDENTITY_INVALID", root_id=root_id)
        if binding.get("global_subject_identity_authority") is not False:
            return _fail("GLOBAL_SUBJECT_AUTHORITY_FORBIDDEN", root_id=root_id)
        if binding.get("terminal_authority") is not False:
            return _fail("SUBJECT_BINDING_TERMINAL_AUTHORITY_FORBIDDEN", root_id=root_id)

        verification, _, error = v1._read_bound(root, row.get("verification"), label="SUBJECT_BINDING_VERIFICATION")
        if error is not None:
            return _fail(error, root_id=root_id)
        assert verification is not None
        ok, why = _verification_evidence_ok(
            root_id,
            verification,
            verification_path=str((row.get("verification") or {}).get("path") or ""),
            binding_path=str((row.get("binding") or {}).get("path") or ""),
            binding_blob=binding_blob,
            binding=binding,
        )
        if not ok:
            return _fail(str(why), root_id=root_id)

        key = (subject_kind, subject_id, subject_sha)
        subject_keys.add(key)
        verified_bindings.append({
            "root_id": root_id,
            "subject_kind": subject_kind,
            "subject_id": subject_id,
            "subject_sha256": subject_sha,
            "subject_binding_git_blob_sha": binding_blob,
            "verification_schema": verification.get("schema"),
        })

    if len(subject_keys) != 1:
        return _base(
            "OPEN__ROOT_SUBJECT_BINDINGS_NOT_IDENTICAL",
            normal_form=normal_record,
            scoped_root_count=len(admitted_roots),
            distinct_subject_count=len(subject_keys),
            verified_bindings=verified_bindings,
        )

    subject_kind, subject_id, subject_sha = next(iter(subject_keys))
    out = _base(
        "PASS__SAME_SUBJECT_ROOT_COMPOSITION_ADMISSIBLE",
        passed=True,
        normal_form=normal_record,
        scoped_root_count=len(admitted_roots),
        verified_root_subject_binding_count=len(verified_bindings),
        composed_subject={"subject_kind":subject_kind,"subject_id":subject_id,"subject_sha256":subject_sha},
        verified_bindings=verified_bindings,
    )
    out["composition_admissible"] = True
    out["receipt_normalization"] = "EXACT_BOUNDED_R1_R12_PROMOTED_VERIFICATION_FAMILIES_ONLY"
    return out
