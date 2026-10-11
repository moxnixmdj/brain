#!/usr/bin/env python3
"""Answer-blind HLE retrieval fallback over Brain-owned open-web discovery.

This adapter prevents one unhealthy retrieval surface from becoming a silent
recall failure. Default discovery queries three Brain-owned zero-model backends,
applies the HLE contamination blocklist, and diversity-interleaves admissible
candidates so an earlier backend cannot starve later sources.

It consumes only visible question text and a query plan. No gold or model
cognition is used. Candidate evidence has zero answer/correctness authority.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_HLE_NATIVE_OPEN_WEB_FALLBACK_V1"
_BACKEND_ORDER = ("BING_RSS", "DUCKDUCKGO_HTML", "CROSSREF")


def _canon(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _default_plan(**kwargs):
    from canonical.runtime.hle_native_retrieval_query_planner_v1 import plan_queries
    return plan_queries(**kwargs)


def _host_safe_candidate(row: Mapping[str, Any], policy: Mapping[str, Any]) -> bool:
    from canonical.runtime import root2_hle_opus55_tool_adapter_v1 as hle_tools
    url = _canon(row.get("url"))
    return bool(url and hle_tools.block_match(url, policy) is None)


def _select_diverse_candidates(
    backend_rows: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    limit: int,
    policy: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    """Round-robin admissible candidates across backend pools."""
    limit = max(1, min(int(limit), 40))
    pools = {
        name: [dict(x) for x in (backend_rows.get(name) or []) if isinstance(x, Mapping)]
        for name in _BACKEND_ORDER
    }
    cursor = {name: 0 for name in _BACKEND_ORDER}
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    blocked = 0

    while len(out) < limit:
        progressed = False
        for name in _BACKEND_ORDER:
            rows = pools[name]
            while cursor[name] < len(rows):
                row = rows[cursor[name]]
                cursor[name] += 1
                url = _canon(row.get("url"))
                if not url or url in seen:
                    continue
                if not _host_safe_candidate(row, policy):
                    blocked += 1
                    continue
                seen.add(url)
                item = dict(row)
                item["discovery_backend"] = _canon(item.get("discovery_backend")) or name
                item["rank"] = len(out)
                out.append(item)
                progressed = True
                break
            if len(out) >= limit:
                break
        if not progressed:
            break
    return out, blocked


def _default_discover(objective, *, limit=12, timeout=15, query_override=None):
    """Use exact Brain-owned backend transports with diversity + HLE filtering."""
    from canonical.runtime.bound_capabilities import open_web_source_candidate_discovery as base
    from canonical.runtime import root2_hle_opus55_tool_adapter_v1 as hle_tools

    query = _canon(query_override if query_override is not None else objective)
    if not query:
        raise ValueError("DISCOVERY_QUERY_REQUIRED")
    limit = max(1, min(int(limit), 40))
    timeout = max(2, min(int(timeout), 30))
    policy = hle_tools.load_policy()

    pools: dict[str, list[dict[str, Any]]] = {}
    traces: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for name, fn in (
        ("BING_RSS", base._bing_rss),
        ("DUCKDUCKGO_HTML", base._ddg),
        ("CROSSREF", base._crossref),
    ):
        try:
            found, trace = fn(query, limit, timeout)
            pools[name] = [dict(x) for x in found if isinstance(x, Mapping)]
            traces.append(dict(trace))
        except Exception as exc:
            pools[name] = []
            errors.append({
                "backend": name,
                "error_class": type(exc).__name__,
                "error": str(exc)[:500],
            })

    candidates, blocked = _select_diverse_candidates(
        pools, limit=limit, policy=policy
    )
    return {
        "status": "CANDIDATES_DISCOVERED" if candidates else "DISCOVERY_UNAVAILABLE",
        "query": query,
        "candidates": candidates,
        "candidate_count": len(candidates),
        "retrieval_provenance": traces,
        "backend_errors": errors,
        "blocked_candidate_count": blocked,
        "diversity_policy": "ROUND_ROBIN_BING_DDG_CROSSREF_AFTER_HLE_BLOCKLIST",
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }


def _health(stats: Mapping[str, int]) -> str:
    attempts = int(stats.get("attempts", 0))
    successes = int(stats.get("successful_calls", 0))
    failures = int(stats.get("failed_calls", 0))
    candidates = int(stats.get("candidate_count", 0))
    if attempts == 0:
        return "UNOBSERVED"
    if failures == attempts:
        return "UNAVAILABLE_RETRYABLE"
    if failures:
        return "DEGRADED"
    if successes and candidates == 0:
        return "HEALTHY_EMPTY_ON_THIS_SAMPLE"
    return "HEALTHY"


def retrieve(
    *,
    task_id: str,
    question: str,
    has_nonempty_image_payload: bool = False,
    max_views: int = 5,
    limit_per_view: int = 8,
    timeout: int = 15,
    plan_fn: Callable[..., Mapping[str, Any]] | None = None,
    discover_fn: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError("TASK_ID_REQUIRED")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("QUESTION_REQUIRED")
    if type(has_nonempty_image_payload) is not bool:
        raise ValueError("IMAGE_FLAG_INVALID")

    plan_fn = plan_fn or _default_plan
    discover_fn = discover_fn or _default_discover
    max_views = max(1, min(int(max_views), 10))
    limit_per_view = max(1, min(int(limit_per_view), 20))
    timeout = max(2, min(int(timeout), 30))

    plan = plan_fn(
        task_id=task_id,
        question=question,
        has_nonempty_image_payload=has_nonempty_image_payload,
        max_views=max_views,
    )
    views = plan.get("views") if isinstance(plan, Mapping) else None
    if not isinstance(views, list) or not views:
        raise ValueError("QUERY_PLAN_VIEWS_REQUIRED")

    backend = defaultdict(lambda: {
        "attempts": 0,
        "successful_calls": 0,
        "failed_calls": 0,
        "candidate_count": 0,
    })
    view_receipts: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    blocked_candidate_count = 0

    for rank, view in enumerate(views[:max_views]):
        if not isinstance(view, Mapping):
            raise ValueError("QUERY_VIEW_MAPPING_REQUIRED")
        query = _canon(view.get("query"))
        if not query:
            raise ValueError("QUERY_VIEW_TEXT_REQUIRED")
        try:
            result = discover_fn(
                query,
                limit=limit_per_view,
                timeout=timeout,
                query_override=query,
            )
            if not isinstance(result, Mapping):
                raise ValueError("DISCOVERY_RESULT_MAPPING_REQUIRED")
            traces = result.get("retrieval_provenance") or []
            errors = result.get("backend_errors") or []
            raw_candidates = result.get("candidates") or []
            if not isinstance(traces, list) or not isinstance(errors, list) or not isinstance(raw_candidates, list):
                raise ValueError("DISCOVERY_RESULT_SHAPE_INVALID")
            blocked_candidate_count += max(0, int(result.get("blocked_candidate_count") or 0))

            for trace in traces:
                if not isinstance(trace, Mapping):
                    continue
                name = _canon(trace.get("backend")) or "UNKNOWN"
                backend[name]["attempts"] += 1
                backend[name]["successful_calls"] += 1
                backend[name]["candidate_count"] += max(0, int(trace.get("candidate_count") or 0))
            for err in errors:
                if not isinstance(err, Mapping):
                    continue
                name = _canon(err.get("backend")) or "UNKNOWN"
                backend[name]["attempts"] += 1
                backend[name]["failed_calls"] += 1

            accepted = 0
            for row in raw_candidates:
                if not isinstance(row, Mapping):
                    continue
                url = _canon(row.get("url"))
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                item = dict(row)
                item.update({
                    "hle_task_id": task_id,
                    "query_rank": rank,
                    "query_method": _canon(view.get("method")) or "UNKNOWN",
                    "query": query,
                    "authority_status": "UNVERIFIED_CANDIDATE_ONLY",
                    "answer_authority": False,
                    "correctness_authority": False,
                })
                candidates.append(item)
                accepted += 1

            all_failed = bool(errors) and not traces
            if all_failed:
                status = "FAILED_RETRYABLE"
            elif accepted:
                status = "CANDIDATES_DISCOVERED"
            else:
                status = "SUCCESSFUL_EMPTY__NOT_NONEXISTENCE"
            view_receipts.append({
                "rank": rank,
                "method": _canon(view.get("method")) or "UNKNOWN",
                "query": query,
                "status": status,
                "candidate_count": accepted,
                "backend_error_count": len(errors),
                "blocked_candidate_count": max(0, int(result.get("blocked_candidate_count") or 0)),
                "retryable": all_failed,
                "nonexistence_claim_authorized": False,
            })
        except Exception as exc:
            view_receipts.append({
                "rank": rank,
                "method": _canon(view.get("method")) or "UNKNOWN",
                "query": query,
                "status": "FAILED_RETRYABLE",
                "candidate_count": 0,
                "error_class": type(exc).__name__,
                "error": str(exc)[:500],
                "retryable": True,
                "nonexistence_claim_authorized": False,
            })

    health = {
        name: {**dict(stats), "health": _health(stats)}
        for name, stats in sorted(backend.items())
    }
    failed_views = sum(1 for x in view_receipts if x["status"] == "FAILED_RETRYABLE")
    return {
        "schema": SCHEMA,
        "status": "CANDIDATES_DISCOVERED" if candidates else ("RETRYABLE_SOURCE_FAILURE" if failed_views == len(view_receipts) else "NO_CANDIDATES_YET"),
        "task_id": task_id,
        "query_plan_schema": plan.get("schema") if isinstance(plan, Mapping) else None,
        "view_count": len(view_receipts),
        "failed_retryable_view_count": failed_views,
        "candidate_count": len(candidates),
        "blocked_candidate_count": blocked_candidate_count,
        "candidates": candidates,
        "views": view_receipts,
        "backend_health": health,
        "gold_accessed": False,
        "external_model_calls": 0,
        "external_reasoning_model_calls": 0,
        "model_dependency_count": 0,
        "answer_authority": False,
        "correctness_authority": False,
        "nonexistence_claim_authorized": False,
        "incremental_spend_usd": 0,
        "hard_rules": [
            "VISIBLE_QUESTION_ONLY",
            "NO_GOLD_ACCESS",
            "NO_EXTERNAL_MODEL_COGNITION",
            "HLE_CONTAMINATION_BLOCKLIST_APPLIED_BEFORE_CANDIDATE_ADMISSION",
            "BACKEND_DIVERSITY_PRECEDES_GLOBAL_RESULT_TRUNCATION",
            "FAILED_BACKENDS_ARE_RETRYABLE_NOT_NEGATIVE_EVIDENCE",
            "SUCCESSFUL_EMPTY_RESULTS_DO_NOT_AUTHORIZE_NONEXISTENCE",
            "CANDIDATES_HAVE_ZERO_ANSWER_OR_CORRECTNESS_AUTHORITY",
        ],
    }
