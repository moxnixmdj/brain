"""Stable R12 CC_R3 semantic verifier V4.

V4 accepts the independently replayed universal positive-gate formal reduction
as the exact CC_R3 route. It does not require a finite defeater catalog or a
new V9 positive witness. Stable C8 remains separately bound and already proved.

This verifier grants CC_R3 only. R4 and semantic-property truth remain separate.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_r12_universal_positive_gate_totality_verified_v1 as universal

SCHEMA = "PROJECT_BRAIN_CC_R3_PROFESSIONAL_R12_SEMANTIC_VERIFIER_V4"
CERT_SCHEMA = "PROJECT_BRAIN_CC_R3_PROFESSIONAL_R12_SEMANTIC_CERTIFICATE_V4"
ROOT_ID = "CC_R3_TERMINAL_CLOSURE_V1"
CLAIM_ID = "11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
CLAIM_PATH = "canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261010_V2.json"
CLAIM_BLOB = "7b26ddba501358d42d6fa342efd27d389bb30654"
RECON_PATH = "canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_TRUTH_RECONCILIATION_20261010_V3.json"
RECON_BLOB = "56a5f85e6133661dd7afbc8fc5041ad799f0736f"
C8_PATH = "canonical/verification/PROFESSIONAL_R12_STABLE_C8_NONVACUITY_VERIFY_20261010_V1.json"
C8_BLOB = "6ed0f5d253d0fc734af2998e86ad72f73fe8c073"
UNIVERSAL_PATH = "canonical/runtime/professional_r12_universal_positive_gate_totality_verified_v1.py"
UNIVERSAL_BLOB = "6e71ad867307b8d905dd998183562e2e7c3cf52a"
UNIVERSAL_VERIFY_PATH = "canonical/verification/PROFESSIONAL_R12_UNIVERSAL_POSITIVE_GATE_CC_R3_COMPOSITION_INDEPENDENT_VERIFY_20261011_V1.json"
UNIVERSAL_VERIFY_BLOB = "bb9eaa24afa423c638e4cd3e619d843ee9e7e042"
AUTH_KEYS = (
    "semantic_truth_authority",
    "quality_authority",
    "acceptance_authority",
    "promotion_authority",
    "terminal_authority",
)


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _safe(root: Path, ref: Any, prefixes: tuple[str, ...]) -> Path | None:
    if not isinstance(ref, Mapping):
        return None
    rel = ref.get("path")
    expected = ref.get("git_blob_sha")
    if not isinstance(rel, str) or not rel or rel.startswith("/") or ".." in Path(rel).parts:
        return None
    if not any(rel.startswith(prefix) for prefix in prefixes):
        return None
    full = (root / rel).resolve()
    try:
        full.relative_to(root.resolve())
    except ValueError:
        return None
    if not full.is_file() or full.is_symlink():
        return None
    if not isinstance(expected, str) or _blob(full) != expected:
        return None
    return full


def _fail(root_id: str, claim_id: str, *errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED__CC_R3_STABLE_R12_V4_UNPROVED",
        "root_id": root_id,
        "claim_id": claim_id,
        "errors": sorted(set(errors)),
        "semantic_claim_verified": False,
        "material_defeater_totality_verified": False,
        "stable_c8_nonvacuity_verified": False,
        "cc_r3_terminal_closure_proved": False,
        "semantic_truth_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def verify_certificate(
    *,
    root: Path,
    certificate_path: Path,
    active_claim: Mapping[str, Any],
    root_id: str,
) -> dict[str, Any]:
    root = root.resolve()
    claim_id = str(active_claim.get("claim_id") or "")
    if root_id != ROOT_ID:
        return _fail(root_id, claim_id, "ROOT_ID_MISMATCH")
    if claim_id != CLAIM_ID:
        return _fail(root_id, claim_id, "ACTIVE_CLAIM_ID_MISMATCH")

    try:
        cert = json.loads(certificate_path.read_text(encoding="utf-8"))
    except Exception:
        return _fail(root_id, claim_id, "CERTIFICATE_JSON_INVALID")
    if not isinstance(cert, Mapping) or cert.get("schema") != CERT_SCHEMA:
        return _fail(root_id, claim_id, "CERTIFICATE_SCHEMA_INVALID")

    errors: list[str] = []
    if cert.get("root_id") != ROOT_ID:
        errors.append("CERTIFICATE_ROOT_ID_MISMATCH")
    if cert.get("claim_id") != CLAIM_ID:
        errors.append("CERTIFICATE_CLAIM_ID_MISMATCH")
    if any(cert.get(k) is not False for k in AUTH_KEYS):
        errors.append("CERTIFICATE_AUTHORITY_OVERCLAIM")
    if (cert.get("accounting") or {}).get("terminal_credit_delta", 0) != 0:
        errors.append("CERTIFICATE_NONZERO_TERMINAL_CREDIT")

    expected_refs = (
        ("active_claim", CLAIM_PATH, CLAIM_BLOB, ("canonical/governance/",)),
        ("r12_reconciliation", RECON_PATH, RECON_BLOB, ("canonical/governance/",)),
        ("stable_c8_verification", C8_PATH, C8_BLOB, ("canonical/verification/",)),
        ("universal_totality_runtime", UNIVERSAL_PATH, UNIVERSAL_BLOB, ("canonical/runtime/",)),
        (
            "universal_totality_independent_verification",
            UNIVERSAL_VERIFY_PATH,
            UNIVERSAL_VERIFY_BLOB,
            ("canonical/verification/",),
        ),
    )
    bound: dict[str, Path] = {}
    for key, expected_path, expected_blob, prefixes in expected_refs:
        ref = cert.get(key)
        if not isinstance(ref, Mapping) or ref.get("path") != expected_path or ref.get("git_blob_sha") != expected_blob:
            errors.append(key.upper() + "_REF_MISMATCH")
            continue
        resolved = _safe(root, ref, prefixes)
        if resolved is None:
            errors.append(key.upper() + "_REF_INVALID")
        else:
            bound[key] = resolved
    if errors:
        return _fail(root_id, claim_id, *errors)

    try:
        frozen = json.loads(bound["active_claim"].read_text(encoding="utf-8"))
        recon = json.loads(bound["r12_reconciliation"].read_text(encoding="utf-8"))
        c8 = json.loads(bound["stable_c8_verification"].read_text(encoding="utf-8"))
        uverify = json.loads(
            bound["universal_totality_independent_verification"].read_text(encoding="utf-8")
        )
    except Exception:
        return _fail(root_id, claim_id, "BOUND_SUPPORT_JSON_INVALID")

    for key in (
        "claim_id",
        "claim_kind",
        "mission_blob_sha",
        "scope_sha256",
        "target_predicate_sha256",
        "semantics_sha256",
        "epoch",
        "authority_id",
    ):
        if frozen.get(key) != active_claim.get(key):
            errors.append("ACTIVE_CLAIM_BINDING_MISMATCH:" + key)

    d = recon.get("derived") or {}
    if d.get("all_eight_root_contract_clauses_verified") is not True or d.get("verified_clause_count") != 8:
        errors.append("R12_C1_C8_NOT_CURRENT")
    residual = recon.get("stronger_target_residual") or {}
    if residual.get("obligation") != universal.candidate.OBLIGATION:
        errors.append("R12_MATERIAL_TOTALITY_OBLIGATION_DRIFT")

    reasoning = c8.get("reasoning") or {}
    consequence = c8.get("consequence") or {}
    if c8.get("claim_id") != CLAIM_ID:
        errors.append("C8_CLAIM_DRIFT")
    if reasoning.get("witness_is_real_executed_route") is not True or reasoning.get("witness_is_independently_replayed") is not True:
        errors.append("C8_REAL_INDEPENDENT_ROUTE_NOT_PROVED")
    if consequence.get("r12_c8_nonvacuity_proved") is not True:
        errors.append("C8_NONVACUITY_NOT_PROVED")

    truth = uverify.get("truth") or {}
    if not str(uverify.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE"):
        errors.append("UNIVERSAL_COMPOSITION_VERIFY_NOT_PASS")
    if truth.get("proof_basis") != "UNIVERSAL_FORMAL_SCOPE_PROOF":
        errors.append("UNIVERSAL_PROOF_BASIS_DRIFT")
    if truth.get("material_defeater_totality_proved") is not True:
        errors.append("UNIVERSAL_MATERIAL_TOTALITY_NOT_INDEPENDENTLY_PROVED")
    if truth.get("cc_r3_terminal_closure_proved") is not True:
        errors.append("UNIVERSAL_CC_R3_NOT_INDEPENDENTLY_PROVED")
    if truth.get("stable_c8_nonvacuity_proved") is not True:
        errors.append("UNIVERSAL_C8_BINDING_NOT_PROVED")
    if truth.get("finite_catalog_only") is not False:
        errors.append("FINITE_CATALOG_SUBSTITUTION")
    if truth.get("cross_subject_property_authority_transport") is not False:
        errors.append("CROSS_SUBJECT_AUTHORITY_TRANSPORT")

    theorem = cert.get("theorem") or {}
    if theorem.get("proof_basis") != "UNIVERSAL_FORMAL_SCOPE_PROOF":
        errors.append("CERTIFICATE_PROOF_BASIS_DRIFT")
    if theorem.get("material_defeater_totality_proved") is not True:
        errors.append("CERTIFICATE_MATERIAL_TOTALITY_NOT_TRUE")
    if theorem.get("stable_c8_nonvacuity_proved") is not True:
        errors.append("CERTIFICATE_C8_NOT_TRUE")
    if theorem.get("cc_r3_terminal_closure_proved") is not True:
        errors.append("CERTIFICATE_CC_R3_NOT_TRUE")
    if theorem.get("finite_catalog_used") is not False:
        errors.append("CERTIFICATE_FINITE_CATALOG_USED")
    if theorem.get("cross_subject_property_authority_transport") is not False:
        errors.append("CERTIFICATE_CROSS_SUBJECT_AUTHORITY_TRANSPORT")

    if errors:
        return _fail(root_id, claim_id, *errors)

    live = universal.verify(repo_root=root)
    if live.get("pass") is not True:
        return _fail(root_id, claim_id, "UNIVERSAL_RUNTIME_REJECTED_CURRENT_BYTES")
    if live.get("material_defeater_totality_proved") is not True:
        return _fail(root_id, claim_id, "UNIVERSAL_RUNTIME_TOTALITY_NOT_PROVED")
    if live.get("cc_r3_terminal_closure_proved") is not True:
        return _fail(root_id, claim_id, "UNIVERSAL_RUNTIME_CC_R3_NOT_PROVED")

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__CC_R3_STABLE_R12_V4__INDEPENDENT_UNIVERSAL_FORMAL_SCOPE_TOTALITY_PLUS_STABLE_C8",
        "root_id": ROOT_ID,
        "claim_id": CLAIM_ID,
        "semantic_claim_verified": True,
        "proof_basis": "UNIVERSAL_FORMAL_SCOPE_PROOF",
        "material_defeater_totality_verified": True,
        "stable_c8_nonvacuity_verified": True,
        "cc_r3_terminal_closure_proved": True,
        "finite_catalog_used": False,
        "cross_subject_property_authority_transport": False,
        "semantic_truth_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "errors": [],
    }
