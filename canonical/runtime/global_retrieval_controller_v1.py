#!/usr/bin/env python3
"""Global anti-blind-spot retrieval controller.

This layer sits above query-driven Retrieval V5.  It does not replace large
external indexes.  It orchestrates them with direct enumeration, graph
snowballing, monotonic candidate memory, and empirical marginal-novelty
scheduling.

Authority rules:
- every external result is candidate-only until independently verified;
- candidates are monotonic: reranking may change priority but cannot delete a
  discovered identity;
- queryless enumeration is permitted only for an explicitly bounded source
  with an authoritative/complete enumeration interface;
- a miss in an open world never authorizes nonexistence;
- correlated channels are discounted rather than counted as independent
  evidence.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import unicodedata
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_GLOBAL_RETRIEVAL_CONTROLLER_V1"
STATE_SCHEMA = "PROJECT_BRAIN_GLOBAL_RETRIEVAL_STATE_V1"

EDGE_FIELDS = (
    "dependencies", "dependents", "forks", "mirrors", "citations",
    "references", "imports", "related", "submodules", "packages",
    "releases", "branches", "tags", "authors", "maintainers",
)

MECHANISMS = (
    "UNICODE_MULTILINGUAL_QUERYING",
    "TECHNICAL_ANCHOR_QUERYING",
    "CONTENT_INSPECTION",
    "MULTI_SURFACE_INSPECTION",
    "REVISION_AND_HISTORY_ENUMERATION",
    "QUERYLESS_BOUNDED_ENUMERATION",
    "DEPENDENCY_AND_REFERENCE_GRAPH_EXPANSION",
    "MONOTONIC_CANDIDATE_MEMORY",
    "PROVENANCE_AWARE_RERANKING",
    "CONDITIONAL_NOVELTY_SCHEDULING",
    "CORRELATED_CHANNEL_DISCOUNT",
    "OPEN_WORLD_UNKNOWN_FIREWALL",
)


def _canon(value: Any) -> str:
    return " ".join(
        unicodedata.normalize("NFKC", str(value or "")).strip().split()
    )


def _stable_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def candidate_id(candidate: Mapping[str, Any]) -> str:
    if not isinstance(candidate, Mapping):
        raise ValueError("CANDIDATE_MAPPING_REQUIRED")
    for key in (
        "content_id", "canonical_url", "url", "repository", "package",
        "project", "tool_id", "name",
    ):
        value = _canon(candidate.get(key))
        if value:
            return value.casefold()
    payload = {
        str(k): v for k, v in candidate.items()
        if str(k) not in {
            "score", "rank", "retrieval_score", "priority",
            "verified_sufficient", "acceptance_credit",
        }
    }
    return "anon:" + hashlib.sha256(
        _stable_json(payload).encode("utf-8")
    ).hexdigest()


def new_state() -> dict[str, Any]:
    return {
        "schema": STATE_SCHEMA,
        "candidates": [],
        "consumed_action_ids": [],
        "consumed_upstream_groups": [],
        "verified_witnesses": [],
        "declared_closed_scopes": [],
        "nonexistence_claim_authorized": False,
    }


def _merge_payload(old: Mapping[str, Any], new: Mapping[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(dict(old))
    for key, value in new.items():
        if key in {
            "verified_sufficient", "acceptance_credit", "family_credit",
            "capability_credit", "ownership_credit", "promotion_authority",
        } and value not in (None, False, 0, [], {}):
            raise ValueError("CANDIDATE_AUTHORITY_SMUGGLING:" + str(key))
        if key not in out or out[key] in (None, "", [], {}):
            out[key] = copy.deepcopy(value)
    return out


def add_candidates(
    state: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    *,
    source_id: str,
    upstream_group: str,
    action_id: str,
) -> dict[str, Any]:
    """Append/merge discoveries without destructive filtering."""
    if state.get("schema") != STATE_SCHEMA:
        raise ValueError("GLOBAL_RETRIEVAL_STATE_REQUIRED")
    out = copy.deepcopy(dict(state))
    rows = out.setdefault("candidates", [])
    by_id = {
        str(row.get("candidate_id")): row
        for row in rows if isinstance(row, Mapping)
    }
    for raw in candidates:
        if not isinstance(raw, Mapping):
            raise ValueError("CANDIDATE_MAPPING_REQUIRED")
        cid = candidate_id(raw)
        provenance = {
            "source_id": _canon(source_id),
            "upstream_group": _canon(upstream_group),
            "action_id": _canon(action_id),
        }
        if cid in by_id:
            row = by_id[cid]
            row["payload"] = _merge_payload(row.get("payload") or {}, raw)
            prov = row.setdefault("provenance", [])
            if provenance not in prov:
                prov.append(provenance)
            row["seen_count"] = int(row.get("seen_count") or 1) + 1
        else:
            row = {
                "candidate_id": cid,
                "payload": _merge_payload({}, raw),
                "provenance": [provenance],
                "seen_count": 1,
                "priority_history": [],
                "authority": "CANDIDATE_ONLY",
                "active": True,
            }
            rows.append(row)
            by_id[cid] = row
    return out


def apply_rerank(
    state: Mapping[str, Any],
    scores: Mapping[str, float],
    *,
    reason: str,
) -> dict[str, Any]:
    """Record priorities; never delete or deactivate discovered candidates."""
    if state.get("schema") != STATE_SCHEMA:
        raise ValueError("GLOBAL_RETRIEVAL_STATE_REQUIRED")
    out = copy.deepcopy(dict(state))
    before = {str(x.get("candidate_id")) for x in out.get("candidates") or []}
    for row in out.get("candidates") or []:
        cid = str(row.get("candidate_id"))
        if cid in scores:
            row.setdefault("priority_history", []).append({
                "score": float(scores[cid]),
                "reason": _canon(reason),
            })
            row["latest_priority"] = float(scores[cid])
        row["active"] = True
    after = {str(x.get("candidate_id")) for x in out.get("candidates") or []}
    if before != after:
        raise AssertionError("RERANK_MUST_BE_MONOTONIC")
    return out


def compile_queryless_enumeration(
    sources: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for src in sources:
        if not isinstance(src, Mapping):
            continue
        sid = _canon(src.get("source_id"))
        if not sid:
            continue
        bounded = src.get("bounded_scope") is True
        complete_interface = src.get("authoritative_enumeration") is True
        scope_id = _canon(src.get("scope_id"))
        if not (bounded and complete_interface and scope_id):
            continue
        transport = _canon(src.get("enumeration_transport")) or "DIRECT_API"
        payload = f"{sid}\0{scope_id}\0{transport}"
        actions.append({
            "action": "ENUMERATE_BOUNDED_SOURCE",
            "action_id": "ENUM:" + hashlib.sha256(payload.encode()).hexdigest()[:24],
            "source_id": sid,
            "scope_id": scope_id,
            "transport": transport,
            "upstream_group": _canon(src.get("upstream_group")) or sid,
            "complete_interface_asserted": True,
            "candidate_authority": "CANDIDATE_ONLY",
            "nonexistence_claim_authorized": False,
        })
    return actions


def graph_snowball_actions(
    candidate: Mapping[str, Any],
    *,
    parent_candidate_id: str | None = None,
    depth: int = 0,
    max_depth: int = 3,
    max_edges: int = 128,
) -> list[dict[str, Any]]:
    if depth >= max_depth:
        return []
    payload = candidate.get("payload") if isinstance(candidate.get("payload"), Mapping) else candidate
    parent = parent_candidate_id or candidate_id(payload)
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for field in EDGE_FIELDS:
        raw = payload.get(field)
        if raw is None:
            continue
        values = raw if isinstance(raw, (list, tuple, set)) else [raw]
        for value in values:
            target = _canon(value)
            if not target:
                continue
            key = (field, target.casefold())
            if key in seen:
                continue
            seen.add(key)
            digest = hashlib.sha256(
                f"{parent}\0{field}\0{target}\0{depth}".encode()
            ).hexdigest()[:24]
            out.append({
                "action": "EXPAND_CANDIDATE_GRAPH_EDGE",
                "action_id": "EDGE:" + digest,
                "parent_candidate_id": parent,
                "edge_type": field,
                "target": target,
                "depth": depth + 1,
                "candidate_authority": "CANDIDATE_ONLY",
                "nonexistence_claim_authorized": False,
            })
            if len(out) >= max_edges:
                return out
    return out


def marginal_novelty(
    stats: Mapping[str, Any],
    *,
    already_consumed_upstream_group: bool = False,
) -> dict[str, float]:
    """Bayesian-smoothed next-action utility from empirical unique discoveries."""
    attempts = max(0, int(stats.get("attempts") or 0))
    novel = max(0, min(attempts, int(stats.get("novel_candidate_actions") or 0)))
    sufficient = max(0, min(novel, int(stats.get("sufficient_witness_actions") or 0)))
    failures = max(0, min(attempts, int(stats.get("failures") or 0)))
    latency = max(0.001, float(stats.get("mean_latency_seconds") or 1.0))
    requests = max(0.0, float(stats.get("mean_requests") or 1.0))
    risk = max(0.0, float(stats.get("risk") or 0.0))

    # Beta(1,1) smoothing prevents zero-history channels from receiving zero utility.
    p_novel = (novel + 1.0) / (attempts + 2.0)
    p_sufficient_given_novel = (sufficient + 1.0) / (novel + 2.0)
    reliability = 1.0 - ((failures + 1.0) / (attempts + 2.0))
    reliability = max(0.05, reliability)
    independence = 0.70 if already_consumed_upstream_group else 1.25
    denominator = latency + 0.06 * requests + 0.35 * risk + 0.001
    utility = (
        p_novel * p_sufficient_given_novel * reliability * independence
    ) / denominator
    return {
        "p_novel": p_novel,
        "p_sufficient_given_novel": p_sufficient_given_novel,
        "reliability": reliability,
        "independence_multiplier": independence,
        "utility": utility,
    }


def rank_actions(
    actions: Sequence[Mapping[str, Any]],
    source_stats: Mapping[str, Mapping[str, Any]],
    *,
    consumed_upstream_groups: Sequence[str] = (),
) -> list[dict[str, Any]]:
    consumed = {_canon(x) for x in consumed_upstream_groups}
    ranked: list[dict[str, Any]] = []
    for raw in actions:
        row = dict(raw)
        sid = _canon(row.get("source_id") or row.get("domain") or row.get("backend_id"))
        group = _canon(row.get("upstream_group") or sid)
        stat = source_stats.get(sid) or source_stats.get(group) or {}
        score = marginal_novelty(
            stat,
            already_consumed_upstream_group=group in consumed,
        )
        # Queryless bounded enumeration receives a modest bonus because it can
        # recover zero-lexical-overlap artifacts that search cannot.
        if row.get("action") == "ENUMERATE_BOUNDED_SOURCE":
            score["utility"] *= 1.35
        row["retrieval_priority"] = score
        ranked.append(row)
    ranked.sort(
        key=lambda x: (
            -float(x["retrieval_priority"]["utility"]),
            str(x.get("action_id") or ""),
        )
    )
    return ranked


def compile_global_plan(
    *,
    query_actions: Sequence[Mapping[str, Any]],
    sources: Sequence[Mapping[str, Any]],
    source_stats: Mapping[str, Mapping[str, Any]] | None = None,
    state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    state = state or new_state()
    source_stats = source_stats or {}
    queryless = compile_queryless_enumeration(sources)
    combined: list[dict[str, Any]] = []

    source_by_id = {
        _canon(x.get("source_id")): x
        for x in sources if isinstance(x, Mapping) and _canon(x.get("source_id"))
    }
    for raw in query_actions:
        row = dict(raw)
        sid = _canon(row.get("source_id") or row.get("domain") or row.get("backend_id"))
        src = source_by_id.get(sid, {})
        row.setdefault("action", "QUERY_SOURCE")
        row.setdefault("source_id", sid)
        row.setdefault("upstream_group", _canon(src.get("upstream_group")) or sid)
        row.setdefault("candidate_authority", "CANDIDATE_ONLY")
        row["nonexistence_claim_authorized"] = False
        combined.append(row)
    combined.extend(queryless)

    ranked = rank_actions(
        combined,
        source_stats,
        consumed_upstream_groups=state.get("consumed_upstream_groups") or [],
    )
    return {
        "schema": SCHEMA,
        "status": "COMPILED_GLOBAL_ANTI_BLIND_SPOT_PLAN",
        "actions": ranked,
        "query_action_count": len(combined) - len(queryless),
        "queryless_enumeration_action_count": len(queryless),
        "mechanisms": list(MECHANISMS),
        "candidate_memory_monotonic": True,
        "external_search_engines_are_candidate_generators_only": True,
        "open_world_nonexistence_claim_authorized": False,
        "incremental_spend_usd": 0,
        "hard_rules": [
            "NO_SINGLE_SEARCH_ENGINE_IS_COMPLETENESS_AUTHORITY",
            "USE_EXTERNAL_INDEXES_FOR_REACH_NOT_NEGATIVE_PROOF",
            "QUERYLESS_ENUMERATION_ONLY_FOR_BOUNDED_AUTHORITATIVE_INTERFACES",
            "DISCOVERED_CANDIDATES_ARE_MONOTONIC_AND_CANNOT_BE_RERANKED_OUT_OF_EXISTENCE",
            "CORRELATED_UPSTREAM_CHANNELS_ARE_DISCOUNTED",
            "GRAPH_NEIGHBORS_FEED_BACK_INTO_DISCOVERY",
            "OPEN_WORLD_MISS_REMAINS_UNKNOWN",
            "STOP_ON_FIRST_INDEPENDENTLY_VERIFIED_SUFFICIENT_WITNESS",
        ],
    }


def terminal_state(
    state: Mapping[str, Any],
    *,
    open_world: bool = True,
) -> dict[str, Any]:
    witnesses = [
        w for w in state.get("verified_witnesses") or []
        if isinstance(w, Mapping) and w.get("verified_sufficient") is True
        and _canon(w.get("independent_receipt"))
    ]
    if witnesses:
        return {
            "status": "VERIFIED_SUFFICIENT_WITNESS_FOUND",
            "stop": True,
            "witness": witnesses[0],
            "nonexistence_claim_authorized": False,
        }
    if open_world:
        return {
            "status": "UNKNOWN_CONTINUE_OR_WAIT_FOR_MATERIAL_WAKE",
            "stop": False,
            "nonexistence_claim_authorized": False,
        }
    closed = state.get("declared_closed_scopes") or []
    if closed and all(
        isinstance(x, Mapping)
        and x.get("independently_verified_complete") is True
        for x in closed
    ):
        return {
            "status": "DECLARED_FINITE_SCOPE_CLOSED",
            "stop": True,
            "scope_limited": True,
            "nonexistence_claim_authorized": True,
        }
    return {
        "status": "UNKNOWN_FINITE_SCOPE_NOT_PROVED_COMPLETE",
        "stop": False,
        "nonexistence_claim_authorized": False,
    }
