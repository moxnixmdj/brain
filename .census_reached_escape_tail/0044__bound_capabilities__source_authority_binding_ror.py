#!/usr/bin/env python3
"""Fail-closed model-independent source authority binding via ROR v2.

Scope:
- Bind a provenance-verified candidate URL host to a ROR organization only when
  the normalized candidate domain exactly matches a domain declared by exactly
  one active ROR record.
- This proves only host/domain -> organization identity association.
- It does NOT prove primary-source status, relevance, factual correctness, or
  evidence sufficiency.

Deliberate omissions:
- No fuzzy entity-name matching.
- No parent-domain inference.
- No task-specific whitelist.
- No model cognition.
"""
from __future__ import annotations

import json
import pathlib
import re
import urllib.parse
import urllib.request

SCHEMA = "PROJECT_BRAIN_SOURCE_AUTHORITY_BINDING_ROR_V1"
ROR_API = "https://api.ror.org/v2/organizations"
UA = "ProjectBrain-SourceAuthorityBinding-ROR/1.0"


def _safe_host(raw):
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        if "://" in text:
            host = urllib.parse.urlsplit(text).hostname or ""
        else:
            host = text
    except Exception:
        return None
    host = host.lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    if (
        not host
        or "." not in host
        or host in {"localhost", "127.0.0.1", "::1"}
        or host.endswith((".local", ".internal"))
        or not re.fullmatch(r"[a-z0-9.-]+", host)
    ):
        return None
    return host


def _candidate_host(candidate):
    c = dict(candidate or {})
    for key in ("final_host", "final_url", "candidate_url", "url", "host"):
        host = _safe_host(c.get(key))
        if host:
            return host
    return None


def _ror_query_url(domain):
    q = f'domains:"{domain}"'
    return ROR_API + "?" + urllib.parse.urlencode({"query.advanced": q})


def _fetch_ror(domain, timeout=20):
    url = _ror_query_url(domain)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=max(2, min(int(timeout), 30))) as r:
        raw = r.read(3_000_000)
        final = r.geturl()
        parsed = urllib.parse.urlsplit(final)
        if (parsed.hostname or "").lower() != "api.ror.org":
            raise RuntimeError("ROR_REDIRECT_OUTSIDE_API")
        return json.loads(raw.decode("utf-8", "replace")), final, int(getattr(r, "status", 200))


def _normalized_domains(record):
    out = []
    for raw in (record or {}).get("domains") or []:
        host = _safe_host(raw)
        if host and host not in out:
            out.append(host)
    return out


def _display_name(record):
    for item in (record or {}).get("names") or []:
        types = {str(x) for x in (item or {}).get("types") or []}
        if "ror_display" in types:
            value = " ".join(str((item or {}).get("value") or "").split())
            if value:
                return value
    for item in (record or {}).get("names") or []:
        value = " ".join(str((item or {}).get("value") or "").split())
        if value:
            return value
    return None


def bind_candidate(candidate, timeout=20):
    host = _candidate_host(candidate)
    base = {
        "schema": SCHEMA,
        "candidate_host": host,
        "authority_status": "UNVERIFIED",
        "primary_source_status": "UNVERIFIED",
        "relevance_status": "UNVERIFIED",
        "evidence_sufficiency_status": "UNVERIFIED",
        "authority_claim_scope": "HOST_TO_ROR_ORGANIZATION_DOMAIN_BINDING_ONLY",
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
    if not host:
        return {**base, "status": "AUTHORITY_UNRESOLVED", "reason": "SAFE_PUBLIC_HOST_REQUIRED"}

    try:
        data, final_url, http_status = _fetch_ror(host, timeout)
    except Exception as exc:
        return {
            **base,
            "status": "AUTHORITY_UNRESOLVED",
            "reason": "ROR_API_UNAVAILABLE_OR_INVALID",
            "error_class": type(exc).__name__,
        }

    exact = []
    for record in (data or {}).get("items") or []:
        if str((record or {}).get("status") or "").lower() != "active":
            continue
        if host in _normalized_domains(record):
            exact.append(record)

    if not exact:
        return {
            **base,
            "status": "AUTHORITY_UNRESOLVED",
            "reason": "NO_ACTIVE_EXACT_ROR_DOMAIN_BINDING",
            "ror_query_url": final_url,
            "http_status": http_status,
            "ror_result_count": int((data or {}).get("number_of_results") or 0),
        }

    if len(exact) != 1:
        return {
            **base,
            "status": "AUTHORITY_AMBIGUOUS",
            "reason": "MULTIPLE_ACTIVE_EXACT_ROR_DOMAIN_BINDINGS",
            "ror_query_url": final_url,
            "http_status": http_status,
            "matching_ror_ids": sorted(str(x.get("id") or "") for x in exact),
        }

    record = exact[0]
    return {
        **base,
        "status": "AUTHORITY_IDENTITY_VERIFIED",
        "verification_method": "ROR_V2_EXACT_ACTIVE_DOMAIN_BINDING",
        "authority_status": "VERIFIED",
        "ror_id": record.get("id"),
        "organization_name": _display_name(record),
        "organization_types": list(record.get("types") or []),
        "matched_domain": host,
        "ror_domains": _normalized_domains(record),
        "ror_query_url": final_url,
        "http_status": http_status,
        "output_verified": True,
    }


def bind_discovery(discovery, timeout=20, max_candidates=12):
    if not isinstance(discovery, dict):
        raise ValueError("DISCOVERY_OBJECT_REQUIRED")
    candidates = discovery.get("candidates") or []
    if not isinstance(candidates, list):
        raise ValueError("CANDIDATES_LIST_REQUIRED")
    results = [bind_candidate(c, timeout=timeout) for c in candidates[: max(1, min(int(max_candidates), 20))]]
    verified = [x for x in results if x.get("status") == "AUTHORITY_IDENTITY_VERIFIED"]
    return {
        "schema": SCHEMA,
        "status": "AUTHORITY_BOUND_CANDIDATES_AVAILABLE" if verified else "AUTHORITY_UNRESOLVED",
        "input_candidate_count": len(candidates),
        "verified_candidate_count": len(verified),
        "verified_candidates": verified,
        "results": results,
        "authority_claim_scope": "HOST_TO_ROR_ORGANIZATION_DOMAIN_BINDING_ONLY",
        "primary_source_verification": "NOT_PERFORMED",
        "relevance_verification": "NOT_PERFORMED",
        "evidence_sufficiency_verification": "NOT_PERFORMED",
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }


def _safe_path(root, raw):
    root = pathlib.Path(root).resolve()
    p = (root / str(raw or "")).resolve()
    if p == root or root not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p


def run(args, root):
    args = dict(args or {})
    inp = _safe_path(root, args.get("discovery_path") or args.get("input_path"))
    out = _safe_path(root, args.get("output_path"))
    if not inp.is_file():
        raise ValueError("AUTHORITY_BINDING_INPUT_MISSING")
    discovery = json.loads(inp.read_text(encoding="utf-8"))
    if isinstance(discovery, dict) and isinstance(discovery.get("candidates"), list):
        result = bind_discovery(
            discovery,
            timeout=int(args.get("timeout_s") or args.get("timeout") or 20),
            max_candidates=int(args.get("max_candidates") or 12),
        )
    else:
        result = bind_candidate(
            discovery.get("candidate") if isinstance(discovery, dict) and "candidate" in discovery else discovery,
            timeout=int(args.get("timeout_s") or args.get("timeout") or 20),
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["output_path"] = str(out.relative_to(pathlib.Path(root).resolve())).replace("\\", "/")
    result["output_verified"] = bool(
        result.get("status") in {"AUTHORITY_IDENTITY_VERIFIED", "AUTHORITY_BOUND_CANDIDATES_AVAILABLE"}
        and (
            result.get("status") == "AUTHORITY_IDENTITY_VERIFIED"
            or int(result.get("verified_candidate_count") or 0) > 0
        )
    )
    return result
