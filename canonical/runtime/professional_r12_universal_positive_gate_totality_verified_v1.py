"""Verified composition of the R12 universal positive-gate theorem into CC_R3.

This adapter consumes:
- the exact local universal positive-gate reduction,
- its independent Sprite replay receipt,
- the current R12 reconciliation, and
- the existing material-defeater generator/universal-closure adapter.

It grants CC_R3 material-totality closure only.  R4, semantic property truth,
quality, acceptance, promotion, and terminal authority remain separate.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_r12_universal_positive_gate_totality_v1 as candidate
from canonical.runtime import professional_r12_material_defeater_generator_closure_v1 as closure

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_R12_UNIVERSAL_POSITIVE_GATE_TOTALITY_VERIFIED_V1"

RECEIPT_PATH = "canonical/verification/PROFESSIONAL_R12_UNIVERSAL_POSITIVE_GATE_TOTALITY_INDEPENDENT_VERIFY_20261011_V1.json"
RECEIPT_BLOB = "415ffd01600487a3fd46bf3ee0962924358d8b62"
RECON_PATH = candidate.RECON_PATH
RECON_BLOB = candidate.RECON_BLOB
CANDIDATE_PATH = "canonical/runtime/professional_r12_universal_positive_gate_totality_v1.py"
CANDIDATE_BLOB = "d1030eaf687110f5ca34de24c37e595973a596ac"
CLOSURE_PATH = "canonical/runtime/professional_r12_material_defeater_generator_closure_v1.py"
CLOSURE_BLOB = "fb1c80a25a387085da0c3a3b570d34f3bc5a455a"


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _load_json(root: Path, rel: str, expected: str) -> Mapping[str, Any]:
    p = root / rel
    if not p.is_file() or p.is_symlink():
        raise ValueError("PIN_MISSING:" + rel)
    got = _blob(p)
    if got != expected:
        raise ValueError("PIN_BLOB_DRIFT:" + rel + ":" + got)
    obj = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(obj, Mapping):
        raise ValueError("PIN_NOT_OBJECT:" + rel)
    return obj


def _pin(root: Path, rel: str, expected: str) -> None:
    p = root / rel
    if not p.is_file() or p.is_symlink():
        raise ValueError("PIN_MISSING:" + rel)
    got = _blob(p)
    if got != expected:
        raise ValueError("PIN_BLOB_DRIFT:" + rel + ":" + got)


def _zero() -> dict[str, Any]:
    return {
        "semantic_property_truth_authority": False,
        "r4_proof_realization_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "material_defeater_totality_proved": False,
        "cc_r3_terminal_closure_proved": False,
        **_zero(),
        **extra,
    }


def verify(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    try:
        _pin(root, CANDIDATE_PATH, CANDIDATE_BLOB)
        _pin(root, CLOSURE_PATH, CLOSURE_BLOB)
        receipt = _load_json(root, RECEIPT_PATH, RECEIPT_BLOB)
        recon = _load_json(root, RECON_PATH, RECON_BLOB)
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))

    local = candidate.verify(repo_root=root)
    if local.get("pass") is not True or local.get("universal_positive_gate_totality_candidate_proved") is not True:
        return _fail("LOCAL_UNIVERSAL_REDUCTION_NOT_PROVED", local=local)
    if local.get("proof_basis") != "UNIVERSAL_FORMAL_SCOPE_PROOF":
        return _fail("LOCAL_PROOF_BASIS_DRIFT")
    if local.get("independent_verified") is not False:
        return _fail("LOCAL_CANDIDATE_SELF_AUTHORIZED")

    if not str(receipt.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE"):
        return _fail("INDEPENDENT_RECEIPT_NOT_PASS")
    subj = receipt.get("subject") or {}
    runtime = subj.get("runtime") or {}
    if runtime.get("path") != CANDIDATE_PATH or runtime.get("git_blob_sha") != CANDIDATE_BLOB:
        return _fail("INDEPENDENT_RECEIPT_RUNTIME_BINDING_DRIFT")
    replay = receipt.get("independent_replay") or {}
    if replay.get("tests_failed") != 0 or replay.get("tests_passed") != 7 or replay.get("py_compile") != "PASS":
        return _fail("INDEPENDENT_REPLAY_NOT_COMPLETE")
    truth = receipt.get("truth") or {}
    required_truth = {
        "universal_positive_gate_totality_candidate_proved": True,
        "proof_basis": "UNIVERSAL_FORMAL_SCOPE_PROOF",
        "whole_domain_identity_carrier_bound": True,
        "positive_route_requires_executable_totality_semantics": True,
        "stable_c8_nonvacuity_separate_and_proved": True,
        "finite_catalog_only": False,
        "eight_clause_count_only": False,
        "cross_subject_property_authority_transport": False,
        "independent_verified": True,
        "cc_r3_terminal_closure_proved_by_this_receipt_alone": False,
    }
    for key, expected in required_truth.items():
        if truth.get(key) != expected:
            return _fail("INDEPENDENT_RECEIPT_TRUTH_DRIFT:" + key)

    verifier_id = (replay.get("carrier_id") or "").strip()
    if not verifier_id:
        return _fail("INDEPENDENT_VERIFIER_ID_REQUIRED")

    cert = {
        "schema": closure.CERT_SCHEMA,
        "property_claim_id": closure.PROPERTY_CLAIM_ID,
        "scope_claim_id": closure.SCOPE_CLAIM_ID,
        "leaf_id": closure.LEAF_ID,
        "obligation": closure.OBLIGATION,
        "proof_basis": "UNIVERSAL_FORMAL_SCOPE_PROOF",
        "scope_complete": local.get("scope_complete") is True,
        "generator_or_universal_cover_complete": local.get("generator_or_universal_cover_complete") is True,
        "all_material_defeaters_in_scope_covered": local.get("all_material_defeaters_in_scope_covered") is True,
        "uncovered_material_defeater_complement_empty": local.get("uncovered_material_defeater_complement_empty") is True,
        "decision_null_or_resolved_for_every_covered_defeater": local.get("decision_null_or_resolved_for_every_covered_defeater") is True,
        "independent_verified": True,
        "independent_verifier_id": verifier_id,
        "content_addressed": True,
        "fail_closed_on_unknown": local.get("fail_closed_on_unknown") is True,
        "finite_catalog_only": False,
        "eight_clause_count_only": False,
        "unknown_remainder": [],
    }
    closed = closure.evaluate(recon, cert)
    if closed.get("pass") is not True:
        return _fail("GENERATOR_CLOSURE_REJECTED", closure=closed)
    if closed.get("material_defeater_totality_proved") is not True or closed.get("cc_r3_terminal_closure_proved") is not True:
        return _fail("GENERATOR_CLOSURE_DID_NOT_PROVE_CC_R3", closure=closed)

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__INDEPENDENTLY_VERIFIED_UNIVERSAL_FORMAL_SCOPE_PROOF__R12_MATERIAL_TOTALITY__CC_R3_ONLY",
        "proof_basis": "UNIVERSAL_FORMAL_SCOPE_PROOF",
        "claim_id": closure.PROPERTY_CLAIM_ID,
        "scope_claim_id": closure.SCOPE_CLAIM_ID,
        "leaf_id": closure.LEAF_ID,
        "obligation": closure.OBLIGATION,
        "material_defeater_totality_proved": True,
        "cc_r3_terminal_closure_proved": True,
        "stable_c8_nonvacuity_proved": True,
        "finite_catalog_only": False,
        "cross_subject_property_authority_transport": False,
        "independent_replay_receipt": {
            "path": RECEIPT_PATH,
            "git_blob_sha": RECEIPT_BLOB,
        },
        "generator_closure": closed,
        "exact_next": "MINT_CC_R3_ROOT_CERTIFICATE_BOUND_TO_THIS_EXECUTABLE_PROOF__INDEPENDENTLY_REPLAY_CC_R3_VERIFIER__UPDATE_STABLE_R12_ROOT_REGISTRY__RERUN_R4",
        **_zero(),
    }
