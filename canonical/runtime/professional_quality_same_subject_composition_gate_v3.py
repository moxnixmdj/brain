"""Fail-closed same-subject composition gate for professional-quality evidence.

The professional-quality normal form requires all load-bearing root claims to
hold for the same exact artifact or declared system. Claim-scoped evidence for
different roots is therefore not jointly composable merely because every root
has some bounded evidence.

This gate grants no semantic, execution, quality, acceptance, promotion, or
terminal authority. It only decides whether independently verified root-level
subject bindings are structurally admissible for a later assurance composition
step.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_SAME_SUBJECT_COMPOSITION_GATE_V3"
BINDING_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_VERIFY_V1"
NORMAL_FORM_PATH = (
    "canonical/governance/PROFESSIONAL_QUALITY_CLOSURE_NORMAL_FORM_20261009_V1.json"
)
NORMAL_FORM_GIT_BLOB_SHA = "ebcfe5a48efce9df7fbc69a3817ac2f9adb1ff93"
SAME_SUBJECT_RULE = "SAME_EXACT_ARTIFACT_OR_DECLARED_SYSTEM_SATISFIES_ALL_ROOT_CLAIMS"

EXPECTED_ROOTS = frozenset({
    "R1_TARGET_SPECIFICATION",
    "R2_CANDIDATE_SEARCH",
    "R3_REALIZATION_OBSERVATION",
    "R4_MEASUREMENT_CONSTRUCT",
    "R5_EVALUATOR_REFERENCE",
    "R6_EVIDENCE_GROUNDING_DEPENDENCE",
    "R7_CAUSAL_PRESCRIPTIVE",
    "R8_POPULATION_CONTEXT_OPERATOR",
    "R9_TEMPORAL_DEPLOYMENT",
    "R10_ANALYSIS_DECISION",
    "R11_ADAPTIVE_INTEGRITY_SECURITY",
    "R12_META_COMPOSITION_CLOSURE",
})


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("utf-8") + data).hexdigest()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "composition_admissible": False,
        "professional_quality_closed": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return _base("FAIL_CLOSED", reason=reason, **extra)


def _resolve(root: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw.startswith("canonical/"):
        return None
    path = (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None
    return path


def _read_bound(
    root: Path,
    ref: Any,
    *,
    label: str,
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    if not isinstance(ref, Mapping):
        return None, None, f"{label}_REFERENCE_INVALID"
    path = _resolve(root, ref.get("path"))
    declared = ref.get("git_blob_sha")
    if path is None:
        return None, None, f"{label}_PATH_INVALID"
    if not path.is_file() or path.is_symlink():
        return None, None, f"{label}_FILE_INVALID"
    actual = _git_blob_sha(path)
    if not isinstance(declared, str) or actual != declared:
        return None, actual, f"{label}_BLOB_STALE"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, actual, f"{label}_JSON_INVALID"
    if not isinstance(doc, dict):
        return None, actual, f"{label}_DOCUMENT_INVALID"
    return doc, actual, None


def _normal_form_ok(root: Path) -> tuple[bool, dict[str, Any]]:
    path = _resolve(root, NORMAL_FORM_PATH)
    if path is None or not path.is_file() or path.is_symlink():
        return False, {"reason": "NORMAL_FORM_FILE_INVALID"}
    actual = _git_blob_sha(path)
    if actual != NORMAL_FORM_GIT_BLOB_SHA:
        return False, {
            "reason": "NORMAL_FORM_BLOB_DRIFT",
            "actual_git_blob_sha": actual,
        }
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False, {"reason": "NORMAL_FORM_JSON_INVALID"}
    required = set((doc.get("closure_rule") or {}).get("necessary") or [])
    return SAME_SUBJECT_RULE in required, {
        "path": NORMAL_FORM_PATH,
        "git_blob_sha": actual,
        "same_subject_rule_present": SAME_SUBJECT_RULE in required,
    }



ROOT_NUMBERS = {
    "R1_TARGET_SPECIFICATION": 1,
    "R2_CANDIDATE_SEARCH": 2,
    "R3_REALIZATION_OBSERVATION": 3,
    "R4_MEASUREMENT_CONSTRUCT": 4,
    "R5_EVALUATOR_REFERENCE": 5,
    "R6_EVIDENCE_GROUNDING_DEPENDENCE": 6,
    "R7_CAUSAL_PRESCRIPTIVE": 7,
    "R8_POPULATION_CONTEXT_OPERATOR": 8,
    "R9_TEMPORAL_DEPLOYMENT": 9,
    "R10_ANALYSIS_DECISION": 10,
    "R11_ADAPTIVE_INTEGRITY_SECURITY": 11,
    "R12_META_COMPOSITION_CLOSURE": 12,
}


def _receipt_binding_blob(verification: Mapping[str, Any]) -> str | None:
    candidates = [
        verification.get("subject_binding_git_blob_sha"),
        ((verification.get("current_main_subject") or {}).get("binding") or {}).get("git_blob_sha")
        if isinstance(verification.get("current_main_subject"), Mapping) else None,
        (verification.get("exact_subject") or {}).get("binding_git_blob_sha")
        if isinstance(verification.get("exact_subject"), Mapping) else None,
        (verification.get("exact_blobs") or {}).get("binding")
        if isinstance(verification.get("exact_blobs"), Mapping) else None,
        (verification.get("binding") or {}).get("git_blob_sha")
        if isinstance(verification.get("binding"), Mapping) else None,
    ]
    values = [x for x in candidates if isinstance(x, str) and x]
    if not values:
        return None
    if len(set(values)) != 1:
        return "__CONFLICT__"
    return values[0]


def _receipt_subject_tuple(verification: Mapping[str, Any]) -> tuple[str, str, str] | None:
    candidates: list[Mapping[str, Any]] = []
    cms = verification.get("current_main_subject")
    if isinstance(cms, Mapping) and isinstance(cms.get("declared_system"), Mapping):
        candidates.append(cms["declared_system"])
    exact = verification.get("exact_subject")
    if isinstance(exact, Mapping):
        candidates.append(exact)
    subject = verification.get("subject")
    if isinstance(subject, Mapping):
        candidates.append(subject)
    tuples: list[tuple[str, str, str]] = []
    for row in candidates:
        sid = row.get("subject_id") or row.get("id")
        sha = row.get("subject_sha256") or row.get("sha256")
        if isinstance(sid, str) and isinstance(sha, str):
            kind = row.get("subject_kind")
            tuples.append((kind if isinstance(kind, str) else "DECLARED_SYSTEM", sid, sha))
    if not tuples:
        return None
    if len(set(tuples)) != 1:
        return ("__CONFLICT__", "__CONFLICT__", "__CONFLICT__")
    return tuples[0]


def _receipt_authority(verification: Mapping[str, Any], field: str) -> Any:
    top = verification.get(field)
    auth = verification.get("authority")
    nested = auth.get(field) if isinstance(auth, Mapping) else None
    if top is True or nested is True:
        return True
    if top is False or nested is False:
        return False
    return None


def _receipt_execution_passes(verification: Mapping[str, Any]) -> bool:
    if verification.get("schema") == VERIFY_SCHEMA:
        return verification.get("pass") is True
    status = str(verification.get("status") or "")
    if not (
        status.startswith("PASS__")
        or status.startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__")
    ):
        return False
    public = verification.get("public_runner")
    if isinstance(public, Mapping):
        return all(
            public.get(k) == "success"
            for k in (
                "conclusion",
                "exact_blob_binding_step",
                "root_verifier_step",
                "adversarial_test_step",
            )
        )
    replay = verification.get("replay")
    if not isinstance(replay, Mapping):
        return False
    if replay.get("verifier_pass") is True:
        return True
    for prefix in ("tests", "unit_tests"):
        run = replay.get(f"{prefix}_run")
        passed = replay.get(f"{prefix}_passed")
        failed = replay.get(f"{prefix}_failed")
        if isinstance(run, int) and run > 0 and passed == run and failed == 0:
            return True
    return False


def _verification_receipt_error(
    *,
    root_id: str,
    verification: Mapping[str, Any],
    binding_blob: str,
    subject_kind: str,
    subject_id: str,
    subject_sha: str,
) -> str | None:
    schema = verification.get("schema")
    if schema == VERIFY_SCHEMA:
        if verification.get("pass") is not True:
            return "SUBJECT_BINDING_VERIFY_NOT_PASS"
        if verification.get("root_id") != root_id:
            return "SUBJECT_BINDING_VERIFY_ROOT_MISMATCH"
        if verification.get("subject_binding_git_blob_sha") != binding_blob:
            return "SUBJECT_BINDING_VERIFY_BLOB_MISMATCH"
        if (
            verification.get("subject_kind") != subject_kind
            or verification.get("subject_id") != subject_id
            or verification.get("subject_sha256") != subject_sha
        ):
            return "SUBJECT_BINDING_VERIFY_IDENTITY_MISMATCH"
        if verification.get("root_subject_binding_authority") is not True:
            return "ROOT_SUBJECT_BINDING_AUTHORITY_REQUIRED"
        if verification.get("global_subject_identity_authority") is not False:
            return "GLOBAL_SUBJECT_VERIFY_AUTHORITY_FORBIDDEN"
        if verification.get("terminal_authority") is not False:
            return "SUBJECT_BINDING_VERIFY_TERMINAL_AUTHORITY_FORBIDDEN"
        return None

    number = ROOT_NUMBERS[root_id]
    normal_prefix = (
        f"PROJECT_BRAIN_PROFESSIONAL_QUALITY_R{number}_V7_"
        "ROOT_SUBJECT_BINDING_VERIFY_"
    )
    public_prefix = (
        f"PROJECT_BRAIN_PROFESSIONAL_QUALITY_R{number}_V7_"
        "ROOT_SUBJECT_BINDING_PUBLIC_VERIFY_"
    )
    if not isinstance(schema, str) or not (
        schema.startswith(normal_prefix) or schema.startswith(public_prefix)
    ):
        return "SUBJECT_BINDING_VERIFY_SCHEMA_INVALID"
    top_root = verification.get("root_id")
    if top_root is not None and top_root != root_id:
        return "SUBJECT_BINDING_VERIFY_ROOT_MISMATCH"
    if _receipt_binding_blob(verification) != binding_blob:
        return "SUBJECT_BINDING_VERIFY_BLOB_MISMATCH"
    receipt_subject = _receipt_subject_tuple(verification)
    if receipt_subject is not None and receipt_subject != (
        subject_kind, subject_id, subject_sha
    ):
        return "SUBJECT_BINDING_VERIFY_IDENTITY_MISMATCH"
    if not _receipt_execution_passes(verification):
        return "SUBJECT_BINDING_VERIFY_NOT_PASS"
    if _receipt_authority(verification, "root_subject_binding_authority") is not True:
        return "ROOT_SUBJECT_BINDING_AUTHORITY_REQUIRED"
    if _receipt_authority(verification, "global_subject_identity_authority") is True:
        return "GLOBAL_SUBJECT_VERIFY_AUTHORITY_FORBIDDEN"
    if _receipt_authority(verification, "terminal_authority") is True:
        return "SUBJECT_BINDING_VERIFY_TERMINAL_AUTHORITY_FORBIDDEN"
    return None



def _binding_self_authority_error(binding: Mapping[str, Any]) -> str | None:
    if binding.get("global_subject_identity_authority") is True:
        return "GLOBAL_SUBJECT_AUTHORITY_FORBIDDEN"
    if binding.get("terminal_authority") is not False:
        return "SUBJECT_BINDING_TERMINAL_AUTHORITY_FORBIDDEN"
    return None


def evaluate(
    payload: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_NOT_OBJECT")
    root = Path(repo_root).resolve() if repo_root is not None else ROOT

    normal_ok, normal_record = _normal_form_ok(root)
    if not normal_ok:
        return _fail("NORMAL_FORM_SAME_SUBJECT_LAW_UNAVAILABLE", normal_form=normal_record)

    from canonical.runtime import professional_quality_scoped_evidence_overlay_v1 as scoped
    scoped_result = scoped.evaluate(repo_root=root)
    if scoped_result.get("pass") is not True:
        return _fail(
            "SCOPED_EVIDENCE_REGISTRY_NOT_CURRENT",
            scoped_evidence_status=scoped_result.get("status"),
        )
    admitted = scoped_result.get("admitted_scopes")
    if not isinstance(admitted, list):
        return _fail("SCOPED_EVIDENCE_ADMITTED_SCOPES_INVALID")
    admitted_roots = {
        str(row.get("root_id") or "")
        for row in admitted
        if isinstance(row, Mapping)
    }
    if admitted_roots != EXPECTED_ROOTS:
        return _fail(
            "SCOPED_EVIDENCE_ROOT_COVER_INCOMPLETE",
            admitted_root_ids=sorted(admitted_roots),
            admitted_scope_count=len(admitted),
        )

    rows = payload.get("root_subject_bindings")
    if not isinstance(rows, list):
        return _fail("ROOT_SUBJECT_BINDINGS_NOT_LIST")
    if not rows:
        return _base(
            "OPEN__SAME_SUBJECT_BINDINGS_REQUIRED",
            normal_form=normal_record,
            scoped_root_count=len(admitted_roots),
            admitted_scope_count=len(admitted),
            missing_root_ids=sorted(EXPECTED_ROOTS),
        )

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
        return _base(
            "OPEN__SAME_SUBJECT_BINDINGS_INCOMPLETE",
            normal_form=normal_record,
            missing_root_ids=missing,
            extra_root_ids=extra,
        )

    verified_bindings: list[dict[str, Any]] = []
    subject_keys: set[tuple[str, str, str]] = set()

    for root_id in sorted(EXPECTED_ROOTS):
        row = root_rows[root_id]
        binding, binding_blob, error = _read_bound(
            root, row.get("binding"), label="SUBJECT_BINDING"
        )
        if error is not None:
            return _fail(error, root_id=root_id)
        assert binding is not None and binding_blob is not None
        if binding.get("schema") != BINDING_SCHEMA:
            return _fail("SUBJECT_BINDING_SCHEMA_INVALID", root_id=root_id)
        if binding.get("root_id") != root_id:
            return _fail("SUBJECT_BINDING_ROOT_MISMATCH", root_id=root_id)
        subject_kind = binding.get("subject_kind")
        subject_id = binding.get("subject_id")
        subject_sha = binding.get("subject_sha256")
        if (
            not isinstance(subject_kind, str)
            or not subject_kind.strip()
            or not isinstance(subject_id, str)
            or not subject_id.strip()
            or not isinstance(subject_sha, str)
            or len(subject_sha) != 64
            or any(ch not in "0123456789abcdef" for ch in subject_sha)
        ):
            return _fail("SUBJECT_IDENTITY_INVALID", root_id=root_id)
        binding_authority_error = _binding_self_authority_error(binding)
        if binding_authority_error is not None:
            return _fail(binding_authority_error, root_id=root_id)

        verification, _, error = _read_bound(
            root, row.get("verification"), label="SUBJECT_BINDING_VERIFICATION"
        )
        if error is not None:
            return _fail(error, root_id=root_id)
        assert verification is not None
        receipt_error = _verification_receipt_error(
            root_id=root_id,
            verification=verification,
            binding_blob=binding_blob,
            subject_kind=subject_kind,
            subject_id=subject_id,
            subject_sha=subject_sha,
        )
        if receipt_error is not None:
            return _fail(receipt_error, root_id=root_id)

        key = (subject_kind, subject_id, subject_sha)
        subject_keys.add(key)
        verified_bindings.append(
            {
                "root_id": root_id,
                "subject_kind": subject_kind,
                "subject_id": subject_id,
                "subject_sha256": subject_sha,
                "subject_binding_git_blob_sha": binding_blob,
            }
        )

    if len(subject_keys) != 1:
        return _base(
            "OPEN__ROOT_SUBJECT_BINDINGS_NOT_IDENTICAL",
            normal_form=normal_record,
            scoped_root_count=len(admitted_roots),
            admitted_scope_count=len(admitted),
            distinct_subject_count=len(subject_keys),
            verified_bindings=verified_bindings,
        )

    subject_kind, subject_id, subject_sha = next(iter(subject_keys))
    out = _base(
        "PASS__SAME_SUBJECT_ROOT_COMPOSITION_ADMISSIBLE",
        passed=True,
        normal_form=normal_record,
        scoped_root_count=len(admitted_roots),
        admitted_scope_count=len(admitted),
        verified_root_subject_binding_count=len(verified_bindings),
        composed_subject={
            "subject_kind": subject_kind,
            "subject_id": subject_id,
            "subject_sha256": subject_sha,
        },
        verified_bindings=verified_bindings,
    )
    out["composition_admissible"] = True
    return out


if __name__ == "__main__":
    print(json.dumps(evaluate({"root_subject_bindings": []}), indent=2, sort_keys=True))
