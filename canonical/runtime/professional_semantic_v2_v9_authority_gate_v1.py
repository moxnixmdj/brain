"""Claim-local certify-or-fail-closed semantic-authority gate for V2/V9.

For each exact current V2/V9 semantic claim, this authority layer has only two
authorized dispositions:

* SAFE_POSITIVE_VERIFIED: an exact content-addressed local-totality certificate
  passed the fixed trusted verifier.
* SAFE_NONPOSITIVE_FAIL_CLOSED: no valid positive proof exists; return an
  explicit blocking diagnostic.

The gate is an evaluation/authority mechanism over the exact V9 subject. It
does not mutate the V9 subject or create a new positive professional route.

Universal safety is structural: the only code path that returns positive
semantic authority follows trusted.verify_certificate(...).pass == True.
Nonvacuity is a separate evidence obligation and is intentionally not inferred
from the gate itself.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_semantic_v2_v9_claim_batch_v1 as claim_batch
from canonical.runtime import professional_trusted_local_semantic_totality_verifier_v2 as trusted

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_V2_V9_AUTHORITY_GATE_V1"
POSITIVE = "SAFE_POSITIVE_VERIFIED"
NEGATIVE = "SAFE_NONPOSITIVE_FAIL_CLOSED"


def _zero() -> dict[str, Any]:
    return {
        "positive_semantic_authority": False,
        "semantic_property_truth_authority": False,
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
        "disposition": NEGATIVE,
        "blocking_diagnostic": reason,
        **_zero(),
        **extra,
    }


def _claim_index(root: Path) -> tuple[dict[str, dict[str, Any]] | None, dict[str, Any] | None]:
    batch = claim_batch.verify(root=root)
    if batch.get("pass") is not True:
        return None, _fail("CURRENT_V2_V9_CLAIM_BATCH_NOT_PASS", claim_batch=batch)
    rows = batch.get("rows") or []
    claims = {
        str(row.get("claim_id")): dict(row)
        for row in rows
        if isinstance(row, Mapping) and isinstance(row.get("claim_id"), str) and row.get("claim_id")
    }
    if len(claims) != 12 or batch.get("unique_claim_id_count") != 12:
        return None, _fail("CURRENT_V2_V9_CLAIM_SET_NOT_EXACTLY_12", observed=len(claims))
    return claims, None


def _safe_certificate(root: Path, ref: Any) -> Path | None:
    if not isinstance(ref, Mapping):
        return None
    rel = ref.get("path")
    expected = ref.get("git_blob_sha")
    if not isinstance(rel, str) or not rel.startswith("canonical/evidence/") or rel.startswith("/"):
        return None
    p = Path(rel)
    if ".." in p.parts:
        return None
    full = (root / p).resolve()
    try:
        full.relative_to(root.resolve())
    except ValueError:
        return None
    if not full.is_file() or full.is_symlink() or not isinstance(expected, str):
        return None
    raw = full.read_bytes()
    got = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    return full if got == expected else None


def evaluate_claim(
    claim_id: str,
    *,
    certificate_ref: Mapping[str, Any] | None = None,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    claims, error = _claim_index(root)
    if claims is None:
        assert error is not None
        return error
    if claim_id not in claims:
        return _fail("CLAIM_NOT_CURRENT_V2_V9_SEMANTIC_CLAIM", claim_id=claim_id)

    row = claims[claim_id]
    leaf_id = row.get("leaf_id")
    root_id = row.get("root_id")

    if certificate_ref is None:
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__EXPLICIT_NONPOSITIVE_FAIL_CLOSED",
            "claim_id": claim_id,
            "leaf_id": leaf_id,
            "root_id": root_id,
            "disposition": NEGATIVE,
            "blocking_diagnostic": "CLAIM_BOUND_POSITIVE_SEMANTIC_CERTIFICATE_REQUIRED",
            "positive_proof_present": False,
            **_zero(),
        }

    certificate = _safe_certificate(root, certificate_ref)
    if certificate is None:
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__EXPLICIT_NONPOSITIVE_FAIL_CLOSED",
            "claim_id": claim_id,
            "leaf_id": leaf_id,
            "root_id": root_id,
            "disposition": NEGATIVE,
            "blocking_diagnostic": "POSITIVE_SEMANTIC_CERTIFICATE_REFERENCE_INVALID",
            "positive_proof_present": False,
            **_zero(),
        }

    verdict = trusted.verify_certificate(
        root=root,
        certificate_path=certificate,
        expected_claim_id=claim_id,
    )
    if verdict.get("pass") is not True or verdict.get("local_positive_semantic_witness_verified") is not True:
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__EXPLICIT_NONPOSITIVE_FAIL_CLOSED",
            "claim_id": claim_id,
            "leaf_id": leaf_id,
            "root_id": root_id,
            "disposition": NEGATIVE,
            "blocking_diagnostic": "TRUSTED_LOCAL_SEMANTIC_TOTALITY_NOT_PROVED",
            "positive_proof_present": True,
            "trusted_verifier_result": verdict,
            **_zero(),
        }

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__SAFE_POSITIVE_SEMANTIC_AUTHORITY",
        "claim_id": claim_id,
        "leaf_id": leaf_id,
        "root_id": root_id,
        "disposition": POSITIVE,
        "blocking_diagnostic": None,
        "positive_proof_present": True,
        "positive_semantic_authority": True,
        "trusted_verifier_result": verdict,
        "semantic_property_truth_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def evaluate_all(
    certificate_refs: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    claims, error = _claim_index(root)
    if claims is None:
        assert error is not None
        return error
    refs = certificate_refs or {}
    unknown = sorted(set(refs) - set(claims))
    if unknown:
        return _fail("UNKNOWN_SEMANTIC_CLAIM_BINDINGS", unknown_claim_ids=unknown)

    dispositions = {
        claim_id: evaluate_claim(
            claim_id,
            certificate_ref=refs.get(claim_id),
            repo_root=root,
        )
        for claim_id in sorted(claims)
    }
    if any(result.get("pass") is not True for result in dispositions.values()):
        return _fail("CLAIM_DISPOSITION_EVALUATION_FAILED", claim_results=dispositions)

    positive = sorted(
        claim_id
        for claim_id, result in dispositions.items()
        if result.get("disposition") == POSITIVE
    )
    negative = sorted(set(claims) - set(positive))
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__12_CLAIM_CERTIFY_OR_FAIL_CLOSED_AUTHORITY_DISPOSITIONS",
        "claim_count": 12,
        "positive_claim_ids": positive,
        "nonpositive_claim_ids": negative,
        "positive_claim_count": len(positive),
        "nonpositive_claim_count": len(negative),
        "claim_results": dispositions,
        "universal_positive_requires_trusted_claim_bound_totality": True,
        "missing_or_invalid_proof_is_explicit_nonpositive": True,
        "positive_route_nonvacuity_proved": False,
        "semantic_property_truth_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
