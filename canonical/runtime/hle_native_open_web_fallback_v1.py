#!/usr/bin/env python3
"""Answer-blind HLE retrieval fallback over Brain-owned open-web discovery.

This adapter exists to prevent one unhealthy retrieval surface from becoming a
silent recall failure. It consumes only visible question text and a query plan,
uses no gold and no model cognition, and emits candidate evidence plus explicit
backend-health receipts. Candidates have zero answer/correctness authority.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Mapping

SCHEMA = "PROJECT_BRAIN_HLE_NATIVE_OPEN_WEB_FALLBACK_V1"


def _canon(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _default_plan(**kwargs):
    from canonical.runtime.hle_native_retrieval_query_planner_v1 import plan_queries
    return plan_queries(**kwargs)


def _default_discover(objective, **kwargs):
    from canonical.runtime.bound_capabilities.open_web_source_candidate_discovery import discover
    return discover(objective, **kwargs)


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
            "FAILED_BACKENDS_ARE_RETRYABLE_NOT_NEGATIVE_EVIDENCE",
            "SUCCESSFUL_EMPTY_RESULTS_DO_NOT_AUTHORIZE_NONEXISTENCE",
            "CANDIDATES_HAVE_ZERO_ANSWER_OR_CORRECTNESS_AUTHORITY",
        ],
    }
