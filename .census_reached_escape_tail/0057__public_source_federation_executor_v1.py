#!/usr/bin/env python3
"""Execute public-source federation requests with a content-addressed epoch ledger.

The federation compiler only describes orthogonal source/query cells. This
module actually executes those cells through the existing zero-cost open-web
candidate backend while preserving fail-closed authority boundaries.

A successfully queried empty cell is evidence only that this request was
consumed. It is never evidence that the target does not exist. Transient
backend failure remains retryable and is not added to the consumed set.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import urllib.parse
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_PUBLIC_SOURCE_FEDERATION_EXECUTOR_V1"


class FederationExecutorError(RuntimeError):
    pass


def _canon(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _request_id(row: Mapping[str, Any]) -> str:
    payload = {
        "source_class": _canon(row.get("source_class")),
        "domain": _canon(row.get("domain")).lower(),
        "query": _canon(row.get("query")),
        "base_query": _canon(row.get("base_query")),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


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
        "project_brain_federation_open_web_discovery", path
    )
    if spec is None or spec.loader is None:
        raise FederationExecutorError("OPEN_WEB_DISCOVERY_LOAD_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.discover


def _normalize_candidates(
    rows: Sequence[Mapping[str, Any]],
    *,
    request_id: str,
    source_class: str,
    domain: str,
    query: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise FederationExecutorError("CANDIDATE_MAPPING_REQUIRED")
        for forbidden in (
            "verified_sufficient",
            "acceptance_credit",
            "family_credit",
            "capability_credit",
            "verified_witness",
        ):
            if row.get(forbidden) not in (None, False, 0, [], {}):
                raise FederationExecutorError(
                    "CANDIDATE_AUTHORITY_VIOLATION:" + forbidden
                )
        url = _canon(row.get("url"))
        if not url or not _host_matches(url, domain) or url in seen:
            continue
        seen.add(url)
        item = dict(row)
        item.update(
            {
                "federation_request_id": request_id,
                "federation_source_class": source_class,
                "federation_domain": domain,
                "federation_query": query,
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
    if not isinstance(federation, Mapping):
        raise ValueError("FEDERATION_MAPPING_REQUIRED")
    if federation.get("schema") != "PROJECT_BRAIN_PUBLIC_SOURCE_FEDERATION_V1":
        raise ValueError("FEDERATION_SCHEMA_INVALID")
    requests = federation.get("requests")
    if not isinstance(requests, list) or not requests:
        raise ValueError("FEDERATION_REQUESTS_REQUIRED")

    discover_fn = discover_fn or _load_default_discover()
    max_requests = max(1, min(int(max_requests), 128))
    limit_per_request = max(1, min(int(limit_per_request), 20))
    consumed = {str(x) for x in (consumed_request_ids or []) if str(x)}
    newly_consumed: list[str] = []
    cells: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    executed = 0
    skipped = 0
    failed = 0

    for raw in requests:
        if executed >= max_requests:
            break
        if not isinstance(raw, Mapping):
            raise FederationExecutorError("FEDERATION_REQUEST_MAPPING_REQUIRED")
        source_class = _canon(raw.get("source_class"))
        domain = _canon(raw.get("domain")).lower()
        query = _canon(raw.get("query"))
        if not source_class or not domain or not query:
            raise FederationExecutorError("FEDERATION_REQUEST_FIELDS_REQUIRED")
        rid = _request_id(raw)
        if rid in consumed:
            skipped += 1
            continue

        executed += 1
        try:
            result = discover_fn(
                query,
                limit=limit_per_request,
                timeout=timeout,
                query_override=query,
            )
            if not isinstance(result, Mapping):
                raise FederationExecutorError("DISCOVERY_RESULT_MAPPING_REQUIRED")
            raw_candidates = result.get("candidates") or []
            if not isinstance(raw_candidates, list):
                raise FederationExecutorError("DISCOVERY_CANDIDATES_LIST_REQUIRED")
            normalized = _normalize_candidates(
                raw_candidates,
                request_id=rid,
                source_class=source_class,
                domain=domain,
                query=query,
            )
            traces = result.get("retrieval_provenance") or []
            backend_errors = result.get("backend_errors") or []
            if not normalized and not traces and backend_errors:
                raise FederationExecutorError("ALL_DISCOVERY_BACKENDS_FAILED")

            status = "QUERIED_CANDIDATE" if normalized else "QUERIED_NO_CANDIDATE"
            newly_consumed.append(rid)
            candidates.extend(normalized)
            cells.append(
                {
                    "request_id": rid,
                    "source_class": source_class,
                    "domain": domain,
                    "query": query,
                    "status": status,
                    "candidate_count": len(normalized),
                    "backend_status": _canon(result.get("status")) or None,
                    "backend_errors": backend_errors,
                    "nonexistence_claim_authorized": False,
                }
            )
        except Exception as exc:
            failed += 1
            cells.append(
                {
                    "request_id": rid,
                    "source_class": source_class,
                    "domain": domain,
                    "query": query,
                    "status": "FAILED_TRANSIENT",
                    "candidate_count": 0,
                    "error_class": type(exc).__name__,
                    "error": str(exc)[:800],
                    "retryable": True,
                    "nonexistence_claim_authorized": False,
                }
            )

    epoch_payload = {
        "prior_consumed": sorted(consumed),
        "newly_consumed": sorted(newly_consumed),
        "cells": sorted(
            [
                {
                    "request_id": row["request_id"],
                    "status": row["status"],
                    "candidate_count": row["candidate_count"],
                }
                for row in cells
            ],
            key=lambda x: x["request_id"],
        ),
        "candidate_urls": sorted(
            {
                str(row.get("url"))
                for row in candidates
                if isinstance(row, Mapping) and row.get("url")
            }
        ),
    }
    epoch_sha256 = hashlib.sha256(
        json.dumps(epoch_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return {
        "schema": SCHEMA,
        "status": "EXECUTED",
        "executed_request_count": executed,
        "skipped_consumed_request_count": skipped,
        "failed_transient_request_count": failed,
        "newly_consumed_request_ids": newly_consumed,
        "consumed_request_ids_after": sorted(consumed | set(newly_consumed)),
        "cells": cells,
        "candidates": candidates,
        "candidate_count": len(candidates),
        "source_epoch_sha256": epoch_sha256,
        "complete": False,
        "nonexistence_claim_authorized": False,
        "acceptance_credit": 0,
        "family_credit": 0,
        "capability_credit": 0,
        "incremental_spend_usd": 0,
        "hard_rules": [
            "ONLY_SUCCESSFULLY_QUERIED_CELLS_ENTER_THE_CONSUMED_SET",
            "TRANSIENT_FAILURE_REMAINS_RETRYABLE_UNKNOWN",
            "EMPTY_RESULT_IS_NOT_NONEXISTENCE",
            "OFF_DOMAIN_RESULTS_DO_NOT_SATISFY_A_SOURCE_CELL",
            "FEDERATED_RESULTS_ARE_CANDIDATE_ONLY",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_EXECUTION_OR_PROMOTION_CREDIT",
        ],
    }
