"""Candidate-only default provider for delegated authority-domain source discovery.

This module reuses the already-verified model-independent
discover_authoritative_web_source primitive in astra_runtime. Discovery is
strictly candidate generation. It grants no source-material, semantic-truth,
policy-adequacy, acceptance, promotion, or terminal authority.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Callable, Mapping

SCHEMA = "PROJECT_BRAIN_R2_AUTHORITY_DOMAIN_DISCOVERY_PROVIDER_V1"
REQUEST_SCHEMA = "PROJECT_BRAIN_MINIMUM_POLICY_CHANGING_INFORMATION_REQUEST_V1"
ACTION = "RESEARCH_MINIMUM_AUTHENTICATED_FACT"
SCOPE_KIND = "UNBOUND_SOURCE"


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": status,
        "candidate_only": True,
        "materialization_authority": False,
        "source_truth_authority": False,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _validated_scope(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping) or raw.get("kind") != SCOPE_KIND:
        raise ValueError("UNBOUND_SOURCE_SCOPE_REQUIRED")
    allowed = {
        "kind",
        "query",
        "authority_domains",
        "timeout_s",
        "max_bytes",
    }
    extra = set(raw) - allowed
    if extra:
        raise ValueError(
            "UNMODELED_DISCOVERY_SCOPE_FIELDS:"
            + ",".join(sorted(str(x) for x in extra))
        )
    query = str(raw.get("query") or "").strip()
    domains = raw.get("authority_domains")
    if not query:
        raise ValueError("DISCOVERY_QUERY_REQUIRED")
    if (
        not isinstance(domains, list)
        or not domains
        or len(domains) > 16
        or any(not isinstance(x, str) or not x.strip() for x in domains)
    ):
        raise ValueError("AUTHORITY_DOMAINS_REQUIRED")
    normalized = []
    for item in domains:
        domain = item.casefold().strip().lstrip(".")
        if (
            not re.fullmatch(r"[a-z0-9.-]+", domain)
            or domain.startswith("-")
            or domain.endswith("-")
            or ".." in domain
            or "." not in domain
        ):
            raise ValueError("AUTHORITY_DOMAIN_INVALID:" + domain)
        if domain not in normalized:
            normalized.append(domain)
    timeout = raw.get("timeout_s", 20)
    max_bytes = raw.get("max_bytes", 1_500_000)
    if isinstance(timeout, bool) or not isinstance(timeout, int) or timeout < 1 or timeout > 60:
        raise ValueError("DISCOVERY_TIMEOUT_INVALID")
    if (
        isinstance(max_bytes, bool)
        or not isinstance(max_bytes, int)
        or max_bytes < 10_000
        or max_bytes > 8_000_000
    ):
        raise ValueError("DISCOVERY_MAX_BYTES_INVALID")
    return {
        "query": query,
        "authority_domains": normalized,
        "timeout_s": timeout,
        "max_bytes": max_bytes,
    }


def provide(
    request: Mapping[str, Any],
    round_index: int = 0,
    *,
    discoverer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> Mapping[str, Any] | None:
    if not isinstance(request, Mapping) or request.get("schema") != REQUEST_SCHEMA:
        return None
    plan = request.get("acquisition_plan")
    if not isinstance(plan, Mapping) or plan.get("action") != ACTION:
        return None
    if request.get("external_research_authorized") is not True:
        return _base("FAIL_CLOSED", reason="EXTERNAL_RESEARCH_NOT_AUTHORIZED")

    try:
        scope = _validated_scope(request.get("source_scope"))
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))

    digest = sha256(
        _canon(
            {
                "predicate_id": request.get("predicate_id"),
                "query": scope["query"],
                "authority_domains": scope["authority_domains"],
            }
        ).encode("utf-8")
    ).hexdigest()[:24]
    output_path = (
        "canonical/astra_runtime/tmp/"
        "R2_AUTHORITY_DISCOVERY_" + digest + ".json"
    )
    action = {
        "type": "discover_authoritative_web_source",
        "args": {
            **scope,
            "output_path": output_path,
        },
    }

    try:
        if discoverer is None:
            from canonical.runtime import astra_runtime
            discoverer = astra_runtime._goal_action
        result = discoverer(action)
    except Exception as exc:
        return _base(
            "FAIL_CLOSED",
            reason="DISCOVERY_EXECUTION_FAILED:" + type(exc).__name__ + ":" + str(exc),
        )
    if not isinstance(result, Mapping) or result.get("verified") is not True:
        return _base(
            "OPEN__NO_AUTHORITY_DOMAIN_CANDIDATE_DISCOVERED",
            reason=(
                str(result.get("error") or "DISCOVERY_NOT_VERIFIED")
                if isinstance(result, Mapping)
                else "DISCOVERY_RESULT_NOT_OBJECT"
            ),
            query=scope["query"],
            authority_domains=scope["authority_domains"],
            discovery_evidence_path=output_path,
        )

    chosen_url = str(result.get("chosen_url") or "").strip()
    chosen_host = str(result.get("chosen_host") or "").casefold().strip()
    if not chosen_url or not chosen_host:
        return _base("FAIL_CLOSED", reason="DISCOVERY_CANDIDATE_IDENTITY_MISSING")
    allowed = any(
        chosen_host == domain or chosen_host.endswith("." + domain)
        for domain in scope["authority_domains"]
    )
    if not allowed:
        return _base("FAIL_CLOSED", reason="DISCOVERY_CANDIDATE_OUTSIDE_AUTHORITY")

    return _base(
        "PASS__AUTHORITY_DOMAIN_SOURCE_CANDIDATE_DISCOVERED",
        passed=True,
        query=scope["query"],
        authority_domains=scope["authority_domains"],
        chosen_url=chosen_url,
        chosen_host=chosen_host,
        discovery_evidence_path=str(result.get("output_path") or output_path),
        candidate_count=int(result.get("candidate_count") or 1),
        next_required_edge="CHECKER_CONSUMABLE_MATERIALIZATION_FROM_AUTHORITY_CANDIDATE",
        trust_claim="DOMAIN_FILTERED_DISCOVERY_ONLY_NOT_FACT_VERIFICATION",
    )
