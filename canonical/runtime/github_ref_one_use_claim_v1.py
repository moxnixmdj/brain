"""Atomic one-use shadow-lease claim backend using GitHub Git refs.

A lease claim is materialized as exactly one immutable-by-protocol Git reference
whose key is the lease digest. The GitHub create-reference transaction is the
linearization point: only an exact HTTP 201 with the requested ref and target
commit counts as a first claim. Existing/conflicting refs, ambiguous responses,
network errors, malformed inputs, or receipt drift fail closed.

This module grants no benchmark execution or acceptance authority by itself.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any, Callable, Mapping

from canonical.runtime.shadow_reality_lease_v2 import CLAIM_SCHEMA, claim_digest

SCHEMA = "PROJECT_BRAIN_GITHUB_REF_ONE_USE_CLAIM_V1"
HEX = set("0123456789abcdef")
OWNER_REPO = re.compile(r"^[A-Za-z0-9_.-]+$")
NONCE = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")


class ClaimBackendBlocked(RuntimeError):
    pass


def _sha(value: Any, n: int) -> bool:
    return isinstance(value, str) and len(value) == n and set(value.lower()) <= HEX


def claim_ref(lease_digest_sha256: str) -> str:
    digest = str(lease_digest_sha256 or "").lower()
    if not _sha(digest, 64):
        raise ClaimBackendBlocked("LEASE_DIGEST_SHA256_INVALID")
    return f"refs/heads/shadow-claims/v1/{digest}"


def _receipt(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and isinstance(value.get("path"), str)
        and bool(value.get("path"))
        and _sha(value.get("git_blob_sha"), 40)
    )


def _safe_identity(owner: str, repo: str) -> None:
    if not OWNER_REPO.fullmatch(owner or ""):
        raise ClaimBackendBlocked("OWNER_INVALID")
    if not OWNER_REPO.fullmatch(repo or ""):
        raise ClaimBackendBlocked("REPO_INVALID")


def _blocked(reason: str, *, ref: str | None = None, http_status: int | None = None) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "ref": ref,
        "http_status": http_status,
        "durable_unique_insert_succeeded": False,
        "claim_store_previously_absent": False,
        "backend_verification_receipt": dict(backend_verification_receipt),
        "case_reveal_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_authorized": False,
    }


def create_claim(
    *,
    owner: str,
    repo: str,
    lease_digest_sha256: str,
    one_use_nonce: str,
    target_commit_sha: str,
    preflight_event_sequence: int,
    token: str,
    backend_verification_receipt: Mapping[str, Any] | None,
    api_base: str = "https://api.github.com",
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, Any]:
    try:
        _safe_identity(owner, repo)
        ref = claim_ref(lease_digest_sha256)
        nonce = str(one_use_nonce or "")
        if not NONCE.fullmatch(nonce):
            raise ClaimBackendBlocked("ONE_USE_NONCE_INVALID")
        target = str(target_commit_sha or "").lower()
        if not _sha(target, 40):
            raise ClaimBackendBlocked("TARGET_COMMIT_SHA_INVALID")
        if isinstance(preflight_event_sequence, bool) or not isinstance(preflight_event_sequence, int):
            raise ClaimBackendBlocked("PREFLIGHT_EVENT_SEQUENCE_INVALID")
        if preflight_event_sequence < 0:
            raise ClaimBackendBlocked("PREFLIGHT_EVENT_SEQUENCE_NEGATIVE")
        if not isinstance(token, str) or not token:
            raise ClaimBackendBlocked("GITHUB_TOKEN_REQUIRED")
        if not _receipt(backend_verification_receipt):
            raise ClaimBackendBlocked("BACKEND_VERIFICATION_RECEIPT_REQUIRED")
    except ClaimBackendBlocked as exc:
        return _blocked(str(exc))

    url = f"{api_base.rstrip('/')}/repos/{owner}/{repo}/git/refs"
    body = json.dumps({"ref": ref, "sha": target}, separators=(",", ":")).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2026-03-10",
            "Content-Type": "application/json",
            "User-Agent": "project-brain-shadow-claim-v1",
        },
    )

    try:
        with opener(req, timeout=30) as response:
            status = int(getattr(response, "status", response.getcode()))
            raw = response.read()
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        if status in {409, 422}:
            return _blocked("CLAIM_REF_ALREADY_EXISTS_OR_CONFLICT", ref=ref, http_status=status)
        return _blocked("GITHUB_CREATE_REF_HTTP_ERROR", ref=ref, http_status=status)
    except Exception:
        return _blocked("GITHUB_CREATE_REF_TRANSPORT_ERROR", ref=ref)

    if status != 201:
        return _blocked("GITHUB_CREATE_REF_NON_201", ref=ref, http_status=status)

    try:
        payload = json.loads(raw.decode("utf-8"))
    except Exception:
        return _blocked("GITHUB_CREATE_REF_RESPONSE_NOT_JSON", ref=ref, http_status=status)

    if not isinstance(payload, Mapping):
        return _blocked("GITHUB_CREATE_REF_RESPONSE_NOT_OBJECT", ref=ref, http_status=status)
    if payload.get("ref") != ref:
        return _blocked("GITHUB_CREATE_REF_RESPONSE_REF_MISMATCH", ref=ref, http_status=status)
    obj = payload.get("object")
    if not isinstance(obj, Mapping) or str(obj.get("sha") or "").lower() != target:
        return _blocked("GITHUB_CREATE_REF_RESPONSE_TARGET_MISMATCH", ref=ref, http_status=status)

    claim = {
        "schema": CLAIM_SCHEMA,
        "lease_digest_sha256": str(lease_digest_sha256).lower(),
        "one_use_nonce": nonce,
        "claim_store_key": f"github-ref://{owner}/{repo}/{ref}",
        "preflight_event_sequence": preflight_event_sequence,
        "claim_event_sequence": preflight_event_sequence + 1,
        "case_reveal_has_occurred": False,
        "execution_has_started": False,
        "durable_unique_insert_succeeded": True,
        "claim_backend_independently_verified": True,
        "point_of_use_preflight_pass": True,
        "claim_store_previously_absent": True,
        "claim_backend_receipt": dict(backend_verification_receipt),
    }
    claim["claim_digest_sha256"] = claim_digest(claim)
    return {
        "schema": SCHEMA,
        "status": "FIRST_CLAIM_CREATED__VERIFIED_BACKEND_BOUND",
        "ref": ref,
        "target_commit_sha": target,
        "http_status": status,
        "durable_unique_insert_succeeded": True,
        "claim_store_previously_absent": True,
        "claim": claim,
        "case_reveal_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_authorized": False,
        "rule": "BACKEND_VERIFICATION_MUST_PREEXIST_THE_CREATE_TRANSACTION__CREATE_SUCCESS_STILL_REQUIRES_V2_CLAIM_ADJUDICATION_BEFORE_CASE_REVEAL",
    }
