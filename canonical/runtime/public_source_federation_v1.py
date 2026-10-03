#!/usr/bin/env python3
"""Compile orthogonal public-source federation queries for residual retrieval.

This module does not fetch or rank evidence. It transforms a query lattice into
source-specific candidate queries so open-web discovery is not silently reduced
to one host or one metadata surface.

All outputs are candidate-discovery requests only. Empty results remain UNKNOWN.
"""
from __future__ import annotations

import unicodedata
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_PUBLIC_SOURCE_FEDERATION_V1"

SOURCE_GROUPS = (
    ("CODE_HOST", "github.com"),
    ("CODE_HOST", "gitlab.com"),
    ("CODE_HOST", "gitee.com"),
    ("CODE_HOST", "codeberg.org"),
    ("MODEL_DATA", "huggingface.co"),
    ("PACKAGE", "pypi.org"),
    ("PACKAGE", "npmjs.com"),
    ("PACKAGE", "crates.io"),
    ("PACKAGE", "pkg.go.dev"),
    ("PACKAGE", "central.sonatype.com"),
    ("SCHOLARLY", "arxiv.org"),
    ("SCHOLARLY", "paperswithcode.com"),
    ("TECHNICAL_DISCUSSION", "stackoverflow.com"),
    ("TECHNICAL_DISCUSSION", "reddit.com"),
)


def _canon(value: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).strip().split())


def compile_federation(
    queries: Sequence[str] | Sequence[Mapping[str, Any]],
    *,
    max_queries_per_source: int = 8,
) -> dict[str, Any]:
    max_queries_per_source = max(1, min(int(max_queries_per_source), 32))
    base: list[str] = []
    for row in queries:
        q = _canon(row.get("text")) if isinstance(row, Mapping) else _canon(row)
        if q and q.casefold() not in {x.casefold() for x in base}:
            base.append(q)
    if not base:
        raise ValueError("AT_LEAST_ONE_QUERY_REQUIRED")

    requests: list[dict[str, Any]] = []
    for source_class, domain in SOURCE_GROUPS:
        for rank, query in enumerate(base[:max_queries_per_source]):
            requests.append({
                "source_class": source_class,
                "domain": domain,
                "query": f"site:{domain} {query}",
                "base_query": query,
                "base_rank": rank,
                "transport": "OPEN_WEB",
                "authority": "CANDIDATE_ONLY",
                "complete": False,
            })

    return {
        "schema": SCHEMA,
        "status": "COMPILED",
        "source_group_count": len(SOURCE_GROUPS),
        "base_query_count": len(base),
        "request_count": len(requests),
        "requests": requests,
        "complete": False,
        "incremental_spend_usd": 0,
        "hard_rules": [
            "FEDERATED_WEB_SEARCH_IS_NOT_SOURCE_COMPLETENESS",
            "EMPTY_SOURCE_RESULT_IS_UNKNOWN_NOT_NONEXISTENCE",
            "DISCUSSION_AND_METADATA_RESULTS_ARE_CANDIDATE_ONLY",
            "WITNESS_ACCEPTANCE_REQUIRES_INDEPENDENT_CONTENT_ADDRESSED_VERIFICATION",
            "SOURCE_GROUP_DIVERSITY_MUST_NOT_BE_COLLAPSED_TO_POPULARITY_RANKING",
        ],
    }
