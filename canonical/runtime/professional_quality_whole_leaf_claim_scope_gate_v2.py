"""Professional-quality whole-leaf claim-scoped certificate gate V2.

V1 made whole-leaf scope certificates content-addressed. V2 closes the remaining
scope-substitution seam: a certificate is admissible only after an independently
verified frozen claim scope is proved equivalent to the *whole admissible leaf
input domain*. Coverage of that exact claim is then verified separately.

This gate grants scope completeness only. Leaf property truth, professional
quality, acceptance, promotion and terminal authority remain separate.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.coverage_claim_scope_guard_v1 import (
    compute_claim_id,
    validate_claim,
)
from canonical.runtime.universal_scope_closure_compiler_v1 import evaluate as evaluate_scope

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_CLAIM_SCOPE_GATE_V2"
CLAIM_SCOPE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_CLAIM_SCOPE_V1"
CLAIM_VERIFY_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_CLAIM_SCOPE_VERIFY_V1"
CERT_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_CERTIFICATE_V2"
CERT_VERIFY_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_SEMANTIC_VERIFY_V2"

MANIFEST_PATH = "canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json"
MANIFEST_BLOB = "a7cad32c9fd969ff2c3857bb924c7bd746237ec2"
SUBJECT_PATH = "canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json"
SUBJECT_BLOB = "1d598bc8757017ceb34928d0df9f5fce859ef868"
SUBJECT_KIND = "DECLARED_SYSTEM"
SUBJECT_ID = "PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA256 = "d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
MISSION_PATH = "canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json"
MISSION_BLOB = "13c470645b037bbb46245c687dd35197b420d51a"
CLAIM_GUARD_PATH = "canonical/runtime/coverage_claim_scope_guard_v1.py"
CLAIM_GUARD_BLOB = "d1de61aa9bc00a184772a50f7ec9d5ee2853d747"
SCOPE_COMPILER_PATH = "canonical/runtime/universal_scope_closure_compiler_v1.py"
SCOPE_COMPILER_BLOB = "b208255789b14e44e86c82c196e06b5c41b3d039"

def _git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

def _canon_sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256(raw).hexdigest()

def _text_sha(value: Any) -> str:
    return sha256((value if isinstance(value, str) else "").encode("utf-8")).hexdigest()

def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "whole_leaf_domain_equivalence_proved": False,
        "whole_leaf_scope_complete": False,
        "leaf_property_truth_authority": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }

def _resolve_bytes(repo_root: Path, ref: Any, label: str) -> tuple[Path | None, str | None, str | None]:
    if not isinstance(ref, Mapping):
        return None, None, label + "_REF_INVALID"
    rel, expected = ref.get("path"), ref.get("git_blob_sha")
    if not isinstance(rel, str) or not rel.startswith("canonical/"):
        return None, None, label + "_PATH_INVALID"
    if not isinstance(expected, str) or len(expected) != 40:
        return None, None, label + "_BLOB_INVALID"
    path = (repo_root / rel).resolve()
    try:
        path.relative_to(repo_root.resolve())
    except ValueError:
        return None, None, label + "_PATH_ESCAPE"
    if not path.is_file() or path.is_symlink():
        return None, None, label + "_MISSING"
    actual = _git_blob(path)
    if actual != expected:
        return None, actual, label + "_BLOB_STALE"
    return path, actual, None

def _resolve_json(repo_root: Path, ref: Any, label: str) -> tuple[dict[str, Any] | None, str | None, str | None]:
    path, blob, error = _resolve_bytes(repo_root, ref, label)
    if error:
        return None, blob, error
    assert path is not None and blob is not None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, blob, label + "_JSON_INVALID"
    if not isinstance(doc, dict):
        return None, blob, label + "_NOT_OBJECT"
    return doc, blob, None

def _manifest_leaf(manifest: Mapping[str, Any], leaf_id: str) -> dict[str, Any] | None:
    for row in manifest.get("roots") or []:
        if not isinstance(row, Mapping):
            continue
        for kind, field in (("SEMANTIC", "semantic_leaf"), ("EXECUTION", "execution_leaf")):
            leaf = row.get(field)
            if isinstance(leaf, Mapping) and leaf.get("id") == leaf_id:
                return {
                    "leaf_id": leaf_id,
                    "root_id": row.get("root_id"),
                    "kind": kind,
                    "contract": row.get("contract"),
                    "obligation": leaf.get("obligation"),
                    "acceptance": leaf.get("acceptance"),
                }
    return None

def expected_claim_material(leaf_meta: Mapping[str, Any], scope_definition: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "leaf_id": leaf_meta["leaf_id"],
        "root_id": leaf_meta["root_id"],
        "kind": leaf_meta["kind"],
        "behavior_id": "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001",
        "subject_kind": SUBJECT_KIND,
        "subject_id": SUBJECT_ID,
        "subject_sha256": SUBJECT_SHA256,
        "leaf_contract": leaf_meta["contract"],
        "leaf_obligation": leaf_meta["obligation"],
        "leaf_acceptance": leaf_meta["acceptance"],
        "scope_definition": scope_definition,
    }

def build_claim(leaf_meta: Mapping[str, Any], scope_definition: Mapping[str, Any], *, epoch: str) -> dict[str, Any]:
    material = expected_claim_material(leaf_meta, scope_definition)
    claim = {
        "claim_kind": "PROPERTY_CERTIFICATE",
        "mission_blob_sha": MISSION_BLOB,
        "scope_sha256": _canon_sha(scope_definition),
        "target_predicate_sha256": _text_sha(leaf_meta["acceptance"]),
        "semantics_sha256": _canon_sha(material),
        "epoch": epoch,
        "authority_id": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF",
        "terminal_credit_delta": 0,
    }
    claim["claim_id"] = compute_claim_id(claim)
    return claim

def evaluate_documents(
    *,
    manifest: Mapping[str, Any],
    claim_scope: Mapping[str, Any],
    claim_verification: Mapping[str, Any],
    certificate: Mapping[str, Any],
    certificate_verification: Mapping[str, Any],
    claim_scope_blob: str,
    certificate_blob: str,
    claim_semantic_verifier_blob: str,
    claim_semantic_tests_blob: str,
    certificate_semantic_verifier_blob: str,
    certificate_semantic_tests_blob: str,
) -> dict[str, Any]:
    leaf_id = claim_scope.get("leaf_id")
    if not isinstance(leaf_id, str) or not leaf_id:
        return _fail("CLAIM_SCOPE_LEAF_ID_REQUIRED")
    meta = _manifest_leaf(manifest, leaf_id)
    if meta is None:
        return _fail("LEAF_NOT_IN_MANIFEST")
    if claim_scope.get("schema") != CLAIM_SCOPE_SCHEMA:
        return _fail("CLAIM_SCOPE_SCHEMA_INVALID")
    if claim_scope.get("root_id") != meta["root_id"] or claim_scope.get("kind") != meta["kind"]:
        return _fail("CLAIM_SCOPE_LEAF_METADATA_DRIFT")
    if claim_scope.get("behavior_id") != "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001":
        return _fail("CLAIM_SCOPE_BEHAVIOR_DRIFT")
    if (
        claim_scope.get("subject_kind"),
        claim_scope.get("subject_id"),
        claim_scope.get("subject_sha256"),
    ) != (SUBJECT_KIND, SUBJECT_ID, SUBJECT_SHA256):
        return _fail("CLAIM_SCOPE_SUBJECT_DRIFT")
    if claim_scope.get("leaf_acceptance") != meta["acceptance"]:
        return _fail("CLAIM_SCOPE_ACCEPTANCE_DRIFT")
    scope_definition = claim_scope.get("scope_definition")
    if not isinstance(scope_definition, Mapping) or not scope_definition:
        return _fail("SCOPE_DEFINITION_REQUIRED")
    domain_schema = scope_definition.get("domain_schema_id")
    if not isinstance(domain_schema, str) or not domain_schema:
        return _fail("DOMAIN_SCHEMA_ID_REQUIRED")
    if scope_definition.get("entire_admissible_leaf_domain") is not True:
        return _fail("ENTIRE_LEAF_DOMAIN_ASSERTION_REQUIRED")
    if not isinstance(scope_definition.get("domain_definition"), Mapping):
        return _fail("DOMAIN_DEFINITION_REQUIRED")

    expected_claim = build_claim(meta, scope_definition, epoch=str(claim_scope.get("epoch") or ""))
    if claim_scope.get("claim") != expected_claim:
        return _fail("CLAIM_SCOPE_CONTENT_ADDRESS_MISMATCH", expected_claim_id=expected_claim["claim_id"])
    claim_check = validate_claim(expected_claim, current_mission_blob_sha=MISSION_BLOB)
    if claim_check.get("pass") is not True:
        return _fail("CLAIM_GUARD_REJECTED", claim_guard=claim_check)
    claim_id = expected_claim["claim_id"]

    if claim_verification.get("schema") != CLAIM_VERIFY_SCHEMA:
        return _fail("CLAIM_VERIFY_SCHEMA_INVALID")
    if claim_verification.get("status", "").startswith("PASS__") is not True:
        return _fail("CLAIM_VERIFY_NOT_PASS")
    if claim_verification.get("leaf_id") != leaf_id or claim_verification.get("claim_id") != claim_id:
        return _fail("CLAIM_VERIFY_IDENTITY_MISMATCH")
    if claim_verification.get("claim_scope_git_blob_sha") != claim_scope_blob:
        return _fail("CLAIM_VERIFY_SCOPE_BLOB_MISMATCH")
    if claim_verification.get("leaf_manifest_git_blob_sha") != MANIFEST_BLOB:
        return _fail("CLAIM_VERIFY_MANIFEST_BLOB_MISMATCH")
    if claim_verification.get("subject_git_blob_sha") != SUBJECT_BLOB:
        return _fail("CLAIM_VERIFY_SUBJECT_BLOB_MISMATCH")
    if claim_verification.get("mission_authority_git_blob_sha") != MISSION_BLOB:
        return _fail("CLAIM_VERIFY_MISSION_BLOB_MISMATCH")
    if claim_verification.get("claim_guard_git_blob_sha") != CLAIM_GUARD_BLOB:
        return _fail("CLAIM_VERIFY_GUARD_BLOB_MISMATCH")
    if claim_verification.get("semantic_verifier_git_blob_sha") != claim_semantic_verifier_blob:
        return _fail("CLAIM_VERIFY_SEMANTIC_VERIFIER_BLOB_MISMATCH")
    if claim_verification.get("semantic_tests_git_blob_sha") != claim_semantic_tests_blob:
        return _fail("CLAIM_VERIFY_SEMANTIC_TESTS_BLOB_MISMATCH")
    if claim_verification.get("whole_leaf_domain_equivalence_proved") is not True:
        return _fail("WHOLE_LEAF_DOMAIN_EQUIVALENCE_REQUIRED")
    if claim_verification.get("scope_definition_sha256") != _canon_sha(scope_definition):
        return _fail("CLAIM_VERIFY_SCOPE_DEFINITION_DIGEST_MISMATCH")
    if claim_verification.get("leaf_acceptance_sha256") != _text_sha(meta["acceptance"]):
        return _fail("CLAIM_VERIFY_ACCEPTANCE_DIGEST_MISMATCH")
    replay = claim_verification.get("independent_replay")
    if not isinstance(replay, Mapping) or replay.get("pass") is not True:
        return _fail("CLAIM_VERIFY_INDEPENDENT_REPLAY_REQUIRED")
    if not isinstance(replay.get("transcript_sha256"), str) or len(replay["transcript_sha256"]) != 64:
        return _fail("CLAIM_VERIFY_TRANSCRIPT_INVALID")

    if certificate.get("schema") != CERT_SCHEMA:
        return _fail("CERT_SCHEMA_INVALID")
    if certificate.get("leaf_id") != leaf_id or certificate.get("claim_id") != claim_id:
        return _fail("CERT_CLAIM_IDENTITY_MISMATCH")
    if certificate.get("claim_scope_git_blob_sha") != claim_scope_blob:
        return _fail("CERT_CLAIM_SCOPE_BLOB_MISMATCH")
    for field in (
        "semantic_truth_authority","execution_authority","quality_authority",
        "acceptance_authority","promotion_authority","terminal_authority",
    ):
        if certificate.get(field) is not False:
            return _fail("CERT_SELF_AUTHORITY_FORBIDDEN:" + field)
    if certificate.get("terminal_credit_delta") != 0:
        return _fail("CERT_TERMINAL_CREDIT_FORBIDDEN")
    scope_cert = certificate.get("scope_certificate")
    if not isinstance(scope_cert, Mapping):
        return _fail("SCOPE_CERTIFICATE_REQUIRED")
    expected_scope_id = "scope://professional-quality/whole-leaf/" + claim_id
    if scope_cert.get("target_scope_id") != expected_scope_id:
        return _fail("SCOPE_CERTIFICATE_TARGET_MISMATCH")
    if scope_cert.get("claim_id") != claim_id:
        return _fail("SCOPE_CERTIFICATE_CLAIM_ID_MISMATCH")
    scope_out = evaluate_scope(scope_cert)
    if scope_out.get("scope_complete") is not True:
        return _fail("UNIVERSAL_SCOPE_COMPILER_REJECTED", scope_verdict=scope_out)

    if certificate_verification.get("schema") != CERT_VERIFY_SCHEMA:
        return _fail("CERT_VERIFY_SCHEMA_INVALID")
    if certificate_verification.get("status", "").startswith("PASS__") is not True:
        return _fail("CERT_VERIFY_NOT_PASS")
    if certificate_verification.get("leaf_id") != leaf_id or certificate_verification.get("claim_id") != claim_id:
        return _fail("CERT_VERIFY_IDENTITY_MISMATCH")
    if certificate_verification.get("claim_scope_git_blob_sha") != claim_scope_blob:
        return _fail("CERT_VERIFY_CLAIM_SCOPE_BLOB_MISMATCH")
    if certificate_verification.get("certificate_git_blob_sha") != certificate_blob:
        return _fail("CERT_VERIFY_CERTIFICATE_BLOB_MISMATCH")
    if certificate_verification.get("scope_compiler_git_blob_sha") != SCOPE_COMPILER_BLOB:
        return _fail("CERT_VERIFY_SCOPE_COMPILER_BLOB_MISMATCH")
    if certificate_verification.get("semantic_verifier_git_blob_sha") != certificate_semantic_verifier_blob:
        return _fail("CERT_VERIFY_SEMANTIC_VERIFIER_BLOB_MISMATCH")
    if certificate_verification.get("semantic_tests_git_blob_sha") != certificate_semantic_tests_blob:
        return _fail("CERT_VERIFY_SEMANTIC_TESTS_BLOB_MISMATCH")
    if certificate_verification.get("scope_complete") is not True:
        return _fail("CERT_VERIFY_SCOPE_COMPLETE_REQUIRED")
    if certificate_verification.get("verified_basis") != scope_out.get("basis"):
        return _fail("CERT_VERIFY_BASIS_MISMATCH")
    creplay = certificate_verification.get("independent_replay")
    if not isinstance(creplay, Mapping) or creplay.get("pass") is not True:
        return _fail("CERT_VERIFY_INDEPENDENT_REPLAY_REQUIRED")
    if not isinstance(creplay.get("transcript_sha256"), str) or len(creplay["transcript_sha256"]) != 64:
        return _fail("CERT_VERIFY_TRANSCRIPT_INVALID")

    for source, prefix in ((claim_verification, "CLAIM_VERIFY"), (certificate_verification, "CERT_VERIFY")):
        for field in (
            "semantic_truth_authority","execution_authority","quality_authority",
            "acceptance_authority","promotion_authority","terminal_authority",
        ):
            if source.get(field) is not False:
                return _fail(prefix + "_AUTHORITY_OVERCLAIM:" + field)
        if source.get("terminal_credit_delta") != 0:
            return _fail(prefix + "_TERMINAL_CREDIT_FORBIDDEN")

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__CLAIM_SCOPED_WHOLE_LEAF_DOMAIN_AND_SCOPE_COVER_ADMISSIBLE__PROPERTY_TRUTH_SEPARATE",
        "leaf_id": leaf_id,
        "claim_id": claim_id,
        "claim_scope_git_blob_sha": claim_scope_blob,
        "certificate_git_blob_sha": certificate_blob,
        "whole_leaf_domain_equivalence_proved": True,
        "whole_leaf_scope_complete": True,
        "scope_basis": scope_out.get("basis"),
        "leaf_property_truth_authority": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }

def verify_entry(entry: Mapping[str, Any], *, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    fixed = (
        (MANIFEST_PATH, MANIFEST_BLOB, "MANIFEST"),
        (SUBJECT_PATH, SUBJECT_BLOB, "SUBJECT"),
        (MISSION_PATH, MISSION_BLOB, "MISSION"),
        (CLAIM_GUARD_PATH, CLAIM_GUARD_BLOB, "CLAIM_GUARD"),
        (SCOPE_COMPILER_PATH, SCOPE_COMPILER_BLOB, "SCOPE_COMPILER"),
    )
    for rel, expected, label in fixed:
        path = root / rel
        if not path.is_file() or path.is_symlink() or _git_blob(path) != expected:
            return _fail(label + "_STALE")
    manifest = json.loads((root / MANIFEST_PATH).read_text(encoding="utf-8"))

    claim_scope, claim_scope_blob, error = _resolve_json(root, entry.get("claim_scope"), "CLAIM_SCOPE")
    if error:
        return _fail(error)
    claim_verify, _, error = _resolve_json(root, entry.get("claim_verification"), "CLAIM_VERIFICATION")
    if error:
        return _fail(error)
    cert, cert_blob, error = _resolve_json(root, entry.get("certificate"), "CERTIFICATE")
    if error:
        return _fail(error)
    cert_verify, _, error = _resolve_json(root, entry.get("certificate_verification"), "CERTIFICATE_VERIFICATION")
    if error:
        return _fail(error)
    assert claim_scope is not None and claim_scope_blob is not None
    assert claim_verify is not None and cert is not None and cert_blob is not None and cert_verify is not None

    cv_path, cv_blob, error = _resolve_bytes(root, claim_verify.get("semantic_verifier"), "CLAIM_SEMANTIC_VERIFIER")
    if error:
        return _fail(error)
    ct_path, ct_blob, error = _resolve_bytes(root, claim_verify.get("semantic_tests"), "CLAIM_SEMANTIC_TESTS")
    if error:
        return _fail(error)
    sv_path, sv_blob, error = _resolve_bytes(root, cert_verify.get("semantic_verifier"), "CERT_SEMANTIC_VERIFIER")
    if error:
        return _fail(error)
    st_path, st_blob, error = _resolve_bytes(root, cert_verify.get("semantic_tests"), "CERT_SEMANTIC_TESTS")
    if error:
        return _fail(error)
    assert cv_path is not None and cv_blob is not None and ct_path is not None and ct_blob is not None
    assert sv_path is not None and sv_blob is not None and st_path is not None and st_blob is not None

    for ref in cert.get("evidence_refs") or []:
        _, _, error = _resolve_bytes(root, ref, "EVIDENCE")
        if error:
            return _fail(error)

    return evaluate_documents(
        manifest=manifest,
        claim_scope=claim_scope,
        claim_verification=claim_verify,
        certificate=cert,
        certificate_verification=cert_verify,
        claim_scope_blob=claim_scope_blob,
        certificate_blob=cert_blob,
        claim_semantic_verifier_blob=cv_blob,
        claim_semantic_tests_blob=ct_blob,
        certificate_semantic_verifier_blob=sv_blob,
        certificate_semantic_tests_blob=st_blob,
    )
