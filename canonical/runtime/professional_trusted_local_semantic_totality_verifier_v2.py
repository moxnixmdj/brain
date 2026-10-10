"""Trusted exact-run local semantic-totality verifier for current V2/V9 claims.

This is the truth-repaired successor of the unpromoted generic V11 verifier.
It is deliberately claim-local: one exact current V2/V9 semantic claim, one
exact-run policy-relevant world model, and independently verified typed policy
coverage.

It proves a *positive witness* only.  Universal certify-or-fail-closed safety
is owned by professional_semantic_v2_v9_authority_gate_v1.  This module grants
no whole-leaf property, quality, acceptance, promotion, or terminal authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import observable_policy_cover_totality_gate_v1 as cover
from canonical.runtime import professional_semantic_v2_v9_claim_batch_v1 as claim_batch

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_TRUSTED_LOCAL_SEMANTIC_TOTALITY_VERIFIER_V2"
CERT_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_V2_V9_LOCAL_TOTALITY_CERTIFICATE_V1"
POSITIVE_BAR = (
    "DOMAIN_SPECIFIC_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_AND_ALL_"
    "DECISION_RELEVANT_ROOT_RELEVANT_DEFEATERS_ARE_RESOLVED_OR_PROVED_DECISION_"
    "NULL_WITH_TYPED_EVIDENCE"
)
FULL_ACCEPTANCE = (
    "FOR_EVERY_ADMISSIBLE_INPUT__POSITIVE_SEMANTIC_AUTHORITY_ONLY_IF_"
    + POSITIVE_BAR
    + "__OTHERWISE_FAIL_CLOSED_NONPOSITIVE_WITH_EXPLICIT_BLOCKING_DIAGNOSTIC"
    "__AND_POSITIVE_ROUTE_NONVACUOUS"
)


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _safe(root: Path, ref: Any, prefix: str) -> Path | None:
    if not isinstance(ref, Mapping):
        return None
    rel = ref.get("path")
    expected = ref.get("git_blob_sha")
    if not isinstance(rel, str) or not rel.startswith(prefix) or rel.startswith("/"):
        return None
    p = Path(rel)
    if ".." in p.parts:
        return None
    full = (root / p).resolve()
    try:
        full.relative_to(root.resolve())
    except ValueError:
        return None
    if not full.is_file() or full.is_symlink():
        return None
    if not isinstance(expected, str) or _blob(full) != expected:
        return None
    return full


def _zero() -> dict[str, Any]:
    return {
        "local_positive_semantic_witness_verified": False,
        "semantic_positive_bar_bound": False,
        "whole_leaf_property_truth_authority": False,
        "semantic_truth_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": reason, **_zero(), **extra}


def _current_claim(root: Path, claim_id: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    batch = claim_batch.verify(root=root)
    if batch.get("pass") is not True:
        return None, _fail("CURRENT_V2_V9_CLAIM_BATCH_NOT_PASS", claim_batch=batch)
    rows = [r for r in batch.get("rows") or [] if isinstance(r, Mapping) and r.get("claim_id") == claim_id]
    if len(rows) != 1:
        return None, _fail("CLAIM_ID_NOT_UNIQUE_CURRENT_V2_V9_CLAIM", claim_id=claim_id, match_count=len(rows))
    row = dict(rows[0])
    scope = row.get("claim_scope") or {}
    if scope.get("leaf_acceptance") != FULL_ACCEPTANCE:
        return None, _fail("CURRENT_CLAIM_ACCEPTANCE_DRIFT", claim_id=claim_id)
    return row, {}


def verify_certificate(
    *,
    root: Path,
    certificate_path: Path,
    expected_claim_id: str,
) -> dict[str, Any]:
    root = Path(root).resolve()
    row, error = _current_claim(root, expected_claim_id)
    if row is None:
        return error
    try:
        cert = json.loads(Path(certificate_path).read_text(encoding="utf-8"))
    except Exception:
        return _fail("CERTIFICATE_JSON_INVALID", claim_id=expected_claim_id)
    if not isinstance(cert, Mapping) or cert.get("schema") != CERT_SCHEMA:
        return _fail("CERTIFICATE_SCHEMA_INVALID", claim_id=expected_claim_id)

    scope_cert = row.get("scope_certificate") or {}
    target_scope_id = (scope_cert.get("scope_certificate") or {}).get("target_scope_id")
    claim_scope = row.get("claim_scope") or {}
    domain_def = (claim_scope.get("scope_definition") or {}).get("domain_definition") or {}
    obligation = domain_def.get("leaf_obligation")
    exact = {
        "semantic_property_claim_id": expected_claim_id,
        "semantic_scope_claim_id": target_scope_id,
        "semantic_obligation": obligation,
        "positive_semantic_bar": POSITIVE_BAR,
        "real_exact_run": True,
        "content_addressed": True,
    }
    for key, expected in exact.items():
        if cert.get(key) != expected:
            return _fail("CERTIFICATE_BINDING_MISMATCH:" + key, claim_id=expected_claim_id)

    problem_path = _safe(root, cert.get("policy_cover_problem_ref"), "canonical/evidence/")
    verify_path = _safe(root, cert.get("policy_cover_verification_ref"), "canonical/verification/")
    if problem_path is None:
        return _fail("POLICY_COVER_PROBLEM_REF_INVALID", claim_id=expected_claim_id)
    if verify_path is None:
        return _fail("POLICY_COVER_VERIFICATION_REF_INVALID", claim_id=expected_claim_id)
    try:
        problem = json.loads(problem_path.read_text(encoding="utf-8"))
        independent = json.loads(verify_path.read_text(encoding="utf-8"))
    except Exception:
        return _fail("BOUND_JSON_INVALID", claim_id=expected_claim_id)

    for key, expected in exact.items():
        if problem.get(key) != expected:
            return _fail("PROBLEM_BINDING_MISMATCH:" + key, claim_id=expected_claim_id)

    cover_problem = problem.get("policy_cover_problem")
    if not isinstance(cover_problem, Mapping):
        return _fail("POLICY_COVER_PROBLEM_REQUIRED", claim_id=expected_claim_id)

    completeness = cover_problem.get("world_set_completeness_receipt")
    if (
        not isinstance(completeness, Mapping)
        or completeness.get("semantic_claim_id") != expected_claim_id
        or completeness.get("claim_scoped_world_set_complete") is not True
    ):
        return _fail("WORLD_SET_COMPLETENESS_NOT_CLAIM_BOUND", claim_id=expected_claim_id)

    expected_bar_hash = hashlib.sha256(POSITIVE_BAR.encode()).hexdigest()
    for policy in cover_problem.get("policies") or []:
        if not isinstance(policy, Mapping):
            return _fail("POLICY_NOT_MAPPING", claim_id=expected_claim_id)
        receipt = policy.get("adequacy_receipt")
        if not isinstance(receipt, Mapping):
            return _fail("POLICY_ADEQUACY_RECEIPT_REQUIRED", claim_id=expected_claim_id)
        if receipt.get("semantic_claim_id") != expected_claim_id:
            return _fail("POLICY_ADEQUACY_CLAIM_MISMATCH", claim_id=expected_claim_id)
        if receipt.get("positive_semantic_bar_satisfied_on_every_listed_world") is not True:
            return _fail("POSITIVE_SEMANTIC_BAR_NOT_PROVED", claim_id=expected_claim_id)
        if receipt.get("positive_semantic_bar_sha256") != expected_bar_hash:
            return _fail("POSITIVE_SEMANTIC_BAR_HASH_MISMATCH", claim_id=expected_claim_id)

    verdict = cover.evaluate(cover_problem)
    if verdict.get("pass") is not True or verdict.get("bound_state_totality_proved") is not True:
        return _fail("POLICY_COVER_TOTALITY_NOT_PROVED", claim_id=expected_claim_id, policy_cover_verdict=verdict)

    problem_sha = _digest(problem)
    required_independent = {
        "pass": True,
        "independent_verified": True,
        "problem_sha256": problem_sha,
        "semantic_property_claim_id": expected_claim_id,
        "semantic_scope_claim_id": target_scope_id,
        "positive_semantic_bar_sha256": expected_bar_hash,
        "policy_relevant_world_set_complete": True,
        "policy_cover_replay_pass": True,
    }
    for key, expected in required_independent.items():
        if independent.get(key) != expected:
            return _fail("INDEPENDENT_VERIFY_MISMATCH:" + key, claim_id=expected_claim_id)
    verifier_id = independent.get("independent_verifier_id")
    if not isinstance(verifier_id, str) or not verifier_id:
        return _fail("INDEPENDENT_VERIFIER_ID_REQUIRED", claim_id=expected_claim_id)
    if cert.get("policy_cover_problem_sha256") != problem_sha:
        return _fail("PROBLEM_DIGEST_MISMATCH", claim_id=expected_claim_id)

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__TRUSTED_EXACT_RUN_V2_V9_POSITIVE_SEMANTIC_WITNESS",
        "claim_id": expected_claim_id,
        "leaf_id": row.get("leaf_id"),
        "root_id": row.get("root_id"),
        "scope_claim_id": target_scope_id,
        "positive_semantic_bar_sha256": expected_bar_hash,
        "semantic_positive_bar_bound": True,
        "local_positive_semantic_witness_verified": True,
        "policy_cover_result_sha256": _digest(verdict),
        "proof_basis": "CONTENT_ADDRESSED_CLAIM_BOUND_EXACT_RUN_POLICY_COVER",
        **{k: v for k, v in _zero().items() if k not in ("local_positive_semantic_witness_verified", "semantic_positive_bar_bound")},
    }
