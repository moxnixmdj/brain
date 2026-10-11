"""Fail-closed materialization of an authority-domain discovery candidate.

This closes only the transport/materialization seam after
r2_authority_domain_discovery_provider_v1. A discovered URL remains a candidate
until this module re-fetches it, verifies the final authority domain, bounds the
bytes, hashes the exact bytes, and decodes them without replacement.

The result is raw source material only. It has no semantic truth, policy
adequacy, acceptance, promotion, or terminal authority.
"""
from __future__ import annotations

from hashlib import sha256
import ipaddress
import urllib.parse
import urllib.request
from typing import Any, Callable, Mapping

SCHEMA = "PROJECT_BRAIN_R2_AUTHORITY_CANDIDATE_MATERIALIZER_V1"
REQUEST_SCHEMA = "PROJECT_BRAIN_MINIMUM_POLICY_CHANGING_INFORMATION_REQUEST_V1"
DISCOVERY_SCHEMA = "PROJECT_BRAIN_R2_AUTHORITY_DOMAIN_DISCOVERY_PROVIDER_V1"
KIND = "R2_AUTHORITY_CANDIDATE_RAW_SOURCE_MATERIAL_V1"
ACTION = "RESEARCH_MINIMUM_AUTHENTICATED_FACT"
SCOPE_KIND = "UNBOUND_SOURCE"
MAX_BYTES_HARD = 8_000_000


def _result(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "kind": KIND,
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
        raise ValueError("AUTHORITY_SOURCE_URL_MUST_BE_HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("AUTHORITY_SOURCE_URL_CREDENTIALS_FORBIDDEN")
    host = parsed.hostname.casefold().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".localhost"):
        raise ValueError("AUTHORITY_SOURCE_LOCALHOST_FORBIDDEN")
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
        raise ValueError("AUTHORITY_SOURCE_NONPUBLIC_IP_FORBIDDEN")
    return value


def _host(url: str) -> str:
    return (urllib.parse.urlsplit(url).hostname or "").casefold().rstrip(".")


def _allowed_host(host: str, domains: list[str]) -> bool:
    return bool(host and any(host == d or host.endswith("." + d) for d in domains))


def _domains(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError("AUTHORITY_DOMAINS_REQUIRED")
    out: list[str] = []
    for raw in value:
        d = str(raw or "").strip().casefold().lstrip(".").rstrip(".")
        if not d or "/" in d or ":" in d or d == "localhost" or d.endswith(".localhost"):
            raise ValueError("AUTHORITY_DOMAIN_INVALID")
        if d not in out:
            out.append(d)
    return out


def _default_fetch(url: str, *, max_bytes: int, timeout: float) -> tuple[bytes, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ProjectBrain-R2AuthorityMaterializer/1.0",
            "Accept": "text/*,application/json,application/xml;q=0.9,*/*;q=0.1",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        final_url = _public_https(response.geturl())
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("AUTHORITY_SOURCE_SIZE_LIMIT_EXCEEDED")
    return data, final_url


def materialize(
    request: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    fetcher: Callable[..., tuple[bytes, str]] = _default_fetch,
) -> dict[str, Any]:
    """Re-fetch one discovered authority candidate into content-addressed raw source bytes."""
    if not isinstance(request, Mapping) or request.get("schema") != REQUEST_SCHEMA:
        return _result("FAIL_CLOSED", reason="REQUEST_SCHEMA_INVALID")
    plan = request.get("acquisition_plan")
    scope = request.get("source_scope")
    if not isinstance(plan, Mapping) or plan.get("action") != ACTION:
        return _result("NOT_APPLICABLE__ACTION_NOT_EXTERNAL_RESEARCH")
    if not isinstance(scope, Mapping) or scope.get("kind") != SCOPE_KIND:
        return _result("NOT_APPLICABLE__SOURCE_SCOPE_NOT_UNBOUND")
    if (
        request.get("external_research_authorized") is not True
        or plan.get("external_research_authorized") is not True
    ):
        return _result("FAIL_CLOSED", reason="EXTERNAL_RESEARCH_NOT_AUTHORIZED")

    allowed_scope = {"kind", "query", "authority_domains", "timeout_s", "max_bytes"}
    extra = set(scope) - allowed_scope
    if extra:
        return _result(
            "FAIL_CLOSED",
            reason="UNMODELED_UNBOUND_SOURCE_FIELDS:"
            + ",".join(sorted(str(x) for x in extra)),
        )

    if not isinstance(candidate, Mapping) or candidate.get("schema") != DISCOVERY_SCHEMA:
        return _result("FAIL_CLOSED", reason="DISCOVERY_CANDIDATE_SCHEMA_INVALID")
    if candidate.get("pass") is not True or candidate.get("candidate_only") is not True:
        return _result(
            "FAIL_CLOSED",
            reason="DISCOVERY_CANDIDATE_NOT_VERIFIED_CANDIDATE_ONLY",
        )
    if candidate.get("semantic_truth_authority") is True:
        return _result("FAIL_CLOSED", reason="DISCOVERY_CANDIDATE_AUTHORITY_INFLATION")

    try:
        query = str(scope.get("query") or "").strip()
        if not query:
            raise ValueError("AUTHORITY_QUERY_REQUIRED")
        domains = _domains(scope.get("authority_domains"))
        timeout = float(scope.get("timeout_s", 20))
        if not (0 < timeout <= 60):
            raise ValueError("AUTHORITY_TIMEOUT_INVALID")
        max_bytes = int(scope.get("max_bytes", 2_000_000))
        if isinstance(scope.get("max_bytes"), bool) or not (
            1 <= max_bytes <= MAX_BYTES_HARD
        ):
            raise ValueError("AUTHORITY_MAX_BYTES_INVALID")

        chosen_url = _public_https(candidate.get("chosen_url"))
        chosen_host = _host(chosen_url)
        declared_host = (
            str(candidate.get("chosen_host") or "").strip().casefold().rstrip(".")
        )
        if declared_host != chosen_host:
            raise ValueError("DISCOVERY_CANDIDATE_HOST_MISMATCH")
        if not _allowed_host(chosen_host, domains):
            raise ValueError("DISCOVERY_CANDIDATE_OUTSIDE_AUTHORITY_DOMAINS")

        fetched = fetcher(chosen_url, max_bytes=max_bytes, timeout=timeout)
        if (
            not isinstance(fetched, tuple)
            or len(fetched) != 2
            or not isinstance(fetched[0], bytes)
            or not isinstance(fetched[1], str)
        ):
            raise ValueError("AUTHORITY_FETCHER_RESULT_INVALID")
        raw, final_url = fetched
        final_url = _public_https(final_url)
        final_host = _host(final_url)
        if not _allowed_host(final_host, domains):
            raise ValueError("AUTHORITY_REDIRECT_OUTSIDE_AUTHORITY_DOMAINS")
        if len(raw) > max_bytes:
            raise ValueError("AUTHORITY_SOURCE_SIZE_LIMIT_EXCEEDED")
        source_text = raw.decode("utf-8", errors="strict")
        if not source_text.strip():
            raise ValueError("AUTHORITY_SOURCE_TEXT_EMPTY")
    except Exception as exc:
        return _result("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))

    return _result(
        "PASS__AUTHORITY_CANDIDATE_CONTENT_ADDRESSED_MATERIALIZED",
        passed=True,
        source_text=source_text,
        source_id=final_url,
        source_url=final_url,
        source_host=final_host,
        source_sha256=sha256(raw).hexdigest(),
        source_bytes=len(raw),
        query=query,
        authority_domains=domains,
        discovery_evidence_path=candidate.get("discovery_evidence_path"),
        discovery_candidate_count=candidate.get("candidate_count"),
        retrieval_materialization_verified=True,
        candidate_only=False,
        checker_interpretation_required=True,
        next_required_edge="CHECKER_SPECIFIC_AUTHENTICATED_SOURCE_INTERPRETATION",
        boundary=(
            "EXACT_RETRIEVED_SOURCE_BYTES_ONLY__NO_TRUTH_FROM_URL_OR_TEXT_PRESENCE__"
            "DOWNSTREAM_CHECKER_MUST_RECOMPUTE_PREDICATE_IDENTITY_AND_TRUTH"
        ),
    )
