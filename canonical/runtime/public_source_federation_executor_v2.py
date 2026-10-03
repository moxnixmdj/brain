#!/usr/bin/env python3
"""Strict execution kernel for diversity-preserving Retrieval V5 federation.

Consumes PROJECT_BRAIN_PUBLIC_SOURCE_FEDERATION_V2 requests. Only successfully
executed source/query cells enter the consumed set. Transient or rejected
backend failures remain unconsumed and retryable. A source epoch can be marked
consumed only after every selected request id is successfully queried.

Even a fully consumed epoch is not an open-world completeness or nonexistence
proof. All discovered rows remain candidate-only until separately verified.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import urllib.parse
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_PUBLIC_SOURCE_FEDERATION_EXECUTOR_V2"
FEDERATION_SCHEMA = "PROJECT_BRAIN_PUBLIC_SOURCE_FEDERATION_V2"


class FederationExecutionError(RuntimeError):
    pass


def _canon(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _expected_request_id(row: Mapping[str, Any]) -> str:
    domain = _canon(row.get("domain")).lower()
    query = _canon(row.get("query"))
    if not domain or not query:
        raise FederationExecutionError("REQUEST_DOMAIN_AND_QUERY_REQUIRED")
    return hashlib.sha256(f"{domain}\0{query}".encode()).hexdigest()[:24]


def _host_matches(url: Any, domain: str) -> bool:
    try:
        host = (urllib.parse.urlsplit(str(url or "")).hostname or "").lower().strip(".")
    except Exception:
        return False
    domain = domain.lower().strip(".")
    return bool(host and (host == domain or host.endswith("." + domain)))


def _load_default_discover():
    path = (
        pathlib.Path(__file__).resolve().parent
        / "bound_capabilities"
        / "open_web_source_candidate_discovery.py"
    )
    spec = importlib.util.spec_from_file_location(
        "project_brain_federation_v5_open_web_discovery", path
    )
    if spec is None or spec.loader is None:
        raise FederationExecutionError("OPEN_WEB_DISCOVERY_LOAD_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.discover


def _validated_requests(federation: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(federation, Mapping):
        raise ValueError("FEDERATION_MAPPING_REQUIRED")
    if federation.get("schema") != FEDERATION_SCHEMA:
        raise ValueError("FEDERATION_V2_REQUIRED")
    raw = federation.get("requests")
    if not isinstance(raw, list) or not raw:
        raise ValueError("FEDERATION_REQUESTS_REQUIRED")
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in raw:
        if not isinstance(row, Mapping):
            raise FederationExecutionError("FEDERATION_REQUEST_MAPPING_REQUIRED")
        item = dict(row)
        rid = _canon(item.get("request_id"))
        expected = _expected_request_id(item)
        if rid != expected:
            raise FederationExecutionError("REQUEST_ID_MISMATCH:" + (rid or "MISSING"))
        if rid in seen:
            raise FederationExecutionError("DUPLICATE_REQUEST_ID:" + rid)
        seen.add(rid)
        out.append(item)
    return out


def _normalize_candidates(
    rows: Sequence[Mapping[str, Any]],
    *,
    request: Mapping[str, Any],
) -> list[dict[str, Any]]:
    domain = _canon(request.get("domain")).lower()
    rid = _canon(request.get("request_id"))
    query = _canon(request.get("query"))
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise FederationExecutionError("CANDIDATE_MAPPING_REQUIRED")
        for forbidden in (
            "verified_sufficient",
            "acceptance_credit",
            "family_credit",
            "capability_credit",
            "verified_witness",
        ):
            if row.get(forbidden) not in (None, False, 0, [], {}):
                raise FederationExecutionError(
                    "CANDIDATE_AUTHORITY_VIOLATION:" + forbidden
                )
        url = _canon(row.get("url"))
        if not url or not _host_matches(url, domain) or url in seen:
            continue
        seen.add(url)
        item = dict(row)
        item.update(
            {
                "federation_request_id": rid,
                "federation_source_class": _canon(request.get("source_class")),
                "federation_domain": domain,
                "federation_query": query,
                "federation_script": _canon(request.get("script")) or "UNKNOWN",
                "federation_selection_class": _canon(
                    request.get("selection_class")
                ) or "UNSPECIFIED",
                "sufficiency_status": "UNVERIFIED",
                "authority_status": "UNVERIFIED",
            }
        )
        out.append(item)
    return out


def execute(
    federation: Mapping[str, Any],
    *,
    consumed_request_ids: Sequence[str] | None = None,
    max_requests: int = 16,
    limit_per_request: int = 8,
    timeout: int = 15,
    discover_fn: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    requests = _validated_requests(federation)
    all_ids = [str(x["request_id"]) for x in requests]
    allowed_ids = set(all_ids)
    consumed = {str(x) for x in (consumed_request_ids or []) if str(x)}
    unknown_consumed = sorted(consumed - allowed_ids)
    if unknown_consumed:
        raise FederationExecutionError(
            "CONSUMED_REQUEST_OUTSIDE_PROGRAM:" + ",".join(unknown_consumed)
        )

    max_requests = max(1, min(int(max_requests), 256))
    limit_per_request = max(1, min(int(limit_per_request), 20))
    discover_fn = discover_fn or _load_default_discover()

    cells: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    newly_consumed: list[str] = []
    failed_ids: list[str] = []
    skipped = 0
    executed = 0

    for request in requests:
        if executed >= max_requests:
            break
        rid = str(request["request_id"])
        if rid in consumed:
            skipped += 1
            continue
        executed += 1
        query = _canon(request.get("query"))
        domain = _canon(request.get("domain")).lower()
        try:
            result = discover_fn(
                query,
                limit=limit_per_request,
                timeout=timeout,
                query_override=query,
            )
            if not isinstance(result, Mapping):
                raise FederationExecutionError("DISCOVERY_RESULT_MAPPING_REQUIRED")
            raw_candidates = result.get("candidates") or []
            if not isinstance(raw_candidates, list):
                raise FederationExecutionError("DISCOVERY_CANDIDATES_LIST_REQUIRED")
            normalized = _normalize_candidates(raw_candidates, request=request)
            traces = result.get("retrieval_provenance") or []
            errors = result.get("backend_errors") or []
            if not normalized and not traces and errors:
                raise FederationExecutionError("ALL_DISCOVERY_BACKENDS_FAILED")
            status = "QUERIED_CANDIDATE" if normalized else "QUERIED_NO_CANDIDATE"
            newly_consumed.append(rid)
            candidates.extend(normalized)
            cells.append(
                {
                    "request_id": rid,
                    "domain": domain,
                    "query": query,
                    "status": status,
                    "candidate_count": len(normalized),
                    "backend_status": _canon(result.get("status")) or None,
                    "backend_errors": errors,
                    "consumed": True,
                    "retryable": False,
                    "nonexistence_claim_authorized": False,
                }
            )
        except Exception as exc:
            failed_ids.append(rid)
            cells.append(
                {
                    "request_id": rid,
                    "domain": domain,
                    "query": query,
                    "status": "FAILED_RETRYABLE",
                    "candidate_count": 0,
                    "error_class": type(exc).__name__,
                    "error": str(exc)[:800],
                    "consumed": False,
                    "retryable": True,
                    "nonexistence_claim_authorized": False,
                }
            )

    consumed_after = consumed | set(newly_consumed)
    remaining = [rid for rid in all_ids if rid not in consumed_after]
    epoch_consumption_authorized = not remaining and not failed_ids

    epoch_payload = {
        "federation_program_sha256": federation.get("federation_program_sha256"),
        "all_request_ids": all_ids,
        "consumed_request_ids": sorted(consumed_after),
        "remaining_request_ids": remaining,
        "failed_request_ids": sorted(failed_ids),
        "candidate_urls": sorted(
            {
                str(x.get("url"))
                for x in candidates
                if isinstance(x, Mapping) and x.get("url")
            }
        ),
    }
    source_epoch_sha256 = hashlib.sha256(
        json.dumps(
            epoch_payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__ALL_SELECTED_SOURCE_QUERY_CELLS_SUCCESSFULLY_EXECUTED"
            if epoch_consumption_authorized
            else "PARTIAL__REMAINING_OR_RETRYABLE_SOURCE_QUERY_CELLS"
        ),
        "all_request_count": len(all_ids),
        "executed_request_count": executed,
        "skipped_consumed_request_count": skipped,
        "newly_consumed_request_ids": newly_consumed,
        "failed_retryable_request_ids": failed_ids,
        "consumed_request_ids_after": sorted(consumed_after),
        "remaining_request_ids": remaining,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "cells": cells,
        "source_epoch_sha256": source_epoch_sha256,
        "epoch_consumption_authorized": epoch_consumption_authorized,
        "complete": False,
        "nonexistence_claim_authorized": False,
        "acceptance_credit": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "incremental_spend_usd": 0,
        "hard_rules": [
            "ONLY_SUCCESSFULLY_EXECUTED_QUERY_CELLS_ARE_CONSUMED",
            "TRANSIENT_OR_REJECTED_FAILURES_REMAIN_RETRYABLE_AND_UNCONSUMED",
            "PARTIAL_BATCH_EXECUTION_CANNOT_CONSUME_THE_SOURCE_EPOCH",
            "ALL_SELECTED_CELLS_MUST_BE_CONSUMED_BEFORE_EPOCH_CONSUMPTION",
            "OFF_DOMAIN_RESULTS_DO_NOT_SATISFY_A_SOURCE_CELL",
            "EMPTY_SUCCESSFUL_RESULT_IS_NOT_NONEXISTENCE",
            "FEDERATED_RESULTS_ARE_CANDIDATE_ONLY",
            "EPOCH_CONSUMPTION_IS_NOT_OPEN_WORLD_COMPLETENESS",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_EXECUTION_OR_PROMOTION_CREDIT",
        ],
    }
