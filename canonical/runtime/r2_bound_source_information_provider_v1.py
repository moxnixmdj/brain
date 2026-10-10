"""Fail-closed default information provider for already-bound HTTPS sources.

This provider closes only the OBSERVE_BOUND_SOURCE_ONLY subcase selected by
minimum_information_origin_policy_v1. The source identity, exact policy/fact URLs,
and expected SHA-256 digests must already be bound in the request's source_scope.

Fetched bytes are proposal material only. The downstream R2 source-proof checker
still recomputes canonical predicate identity and truth.
"""
from __future__ import annotations

from hashlib import sha256
import ipaddress
import urllib.parse
import urllib.request
from typing import Any, Callable, Mapping

from canonical.runtime import r2_raw_source_proof_material_adapter_v1 as raw_material

SCHEMA = "PROJECT_BRAIN_R2_BOUND_SOURCE_INFORMATION_PROVIDER_V1"
REQUEST_SCHEMA = "PROJECT_BRAIN_MINIMUM_POLICY_CHANGING_INFORMATION_REQUEST_V1"
BOUND_SOURCE = "BOUND_SOURCE"
ACTION = "OBSERVE_BOUND_SOURCE_ONLY"
MAX_POLICY_BYTES = 2_000_000
MAX_FACT_BYTES = 8_000_000


def _result(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": status,
        "provider_authority": False,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _public_https(url: Any) -> str:
    value = str(url or "").strip()
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("BOUND_SOURCE_URL_MUST_BE_HTTPS")
    host = parsed.hostname.casefold().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost"):
        raise ValueError("BOUND_SOURCE_LOCALHOST_FORBIDDEN")
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        addr = None
    if addr is not None and (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    ):
        raise ValueError("BOUND_SOURCE_NONPUBLIC_IP_FORBIDDEN")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("BOUND_SOURCE_URL_CREDENTIALS_FORBIDDEN")
    return value


def _digest(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text.startswith("sha256:"):
        text = text[7:]
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ValueError("BOUND_SOURCE_SHA256_INVALID")
    return text


def _fetch_https(url: str, *, max_bytes: int, timeout: float = 20.0) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ProjectBrain-BoundSourceProvider/1.0",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        final_url = _public_https(response.geturl())
        if final_url != response.geturl():
            raise ValueError("BOUND_SOURCE_FINAL_URL_INVALID")
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("BOUND_SOURCE_SIZE_LIMIT_EXCEEDED")
    return data


def _load(
    fetcher: Callable[..., bytes],
    url: str,
    expected_sha256: str,
    *,
    max_bytes: int,
) -> bytes:
    raw = fetcher(url, max_bytes=max_bytes)
    if not isinstance(raw, bytes):
        raise ValueError("BOUND_SOURCE_FETCHER_MUST_RETURN_BYTES")
    if len(raw) > max_bytes:
        raise ValueError("BOUND_SOURCE_SIZE_LIMIT_EXCEEDED")
    observed = sha256(raw).hexdigest()
    if observed != expected_sha256:
        raise ValueError("BOUND_SOURCE_SHA256_MISMATCH:" + observed)
    return raw


def provide(
    request: Mapping[str, Any],
    round_index: int = 0,
    *,
    fetcher: Callable[..., bytes] = _fetch_https,
) -> Mapping[str, Any] | None:
    """Return checker-consumable raw material only for an exact bound-source request."""
    if not isinstance(request, Mapping) or request.get("schema") != REQUEST_SCHEMA:
        return None
    plan = request.get("acquisition_plan")
    if not isinstance(plan, Mapping) or plan.get("action") != ACTION:
        return None
    scope = request.get("source_scope")
    if not isinstance(scope, Mapping) or scope.get("kind") != BOUND_SOURCE:
        return None

    allowed = {
        "kind",
        "source_id",
        "policy_url",
        "policy_source_id",
        "policy_sha256",
        "fact_url",
        "fact_source_id",
        "fact_sha256",
    }
    extra = set(scope) - allowed
    if extra:
        return _result(
            "FAIL_CLOSED",
            reason="UNMODELED_BOUND_SOURCE_FIELDS:" + ",".join(sorted(str(x) for x in extra)),
        )

    try:
        source_id = str(scope.get("source_id") or "").strip()
        policy_source_id = str(scope.get("policy_source_id") or source_id).strip()
        fact_source_id = str(scope.get("fact_source_id") or "").strip()
        if not source_id or not policy_source_id or not fact_source_id:
            raise ValueError("BOUND_SOURCE_IDS_REQUIRED")
        if plan.get("source_id") != source_id:
            raise ValueError("BOUND_SOURCE_PLAN_ID_MISMATCH")

        policy_url = _public_https(scope.get("policy_url"))
        fact_url = _public_https(scope.get("fact_url"))
        policy_hash = _digest(scope.get("policy_sha256"))
        fact_hash = _digest(scope.get("fact_sha256"))

        policy_bytes = _load(
            fetcher, policy_url, policy_hash, max_bytes=MAX_POLICY_BYTES
        )
        fact_bytes = _load(
            fetcher, fact_url, fact_hash, max_bytes=MAX_FACT_BYTES
        )
        source_text = policy_bytes.decode("utf-8", errors="strict")
        if not source_text:
            raise ValueError("BOUND_POLICY_TEXT_EMPTY")
    except Exception as exc:
        return _result(
            "FAIL_CLOSED",
            reason=type(exc).__name__ + ":" + str(exc),
        )

    return {
        "kind": raw_material.KIND,
        "source_text": source_text,
        "source_id": policy_source_id,
        "fact_source": fact_bytes,
        "fact_source_id": fact_source_id,
    }
