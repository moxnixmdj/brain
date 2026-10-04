#!/usr/bin/env python3
"""End-to-end exact pointwise solver for the frozen LiveBench legacy15 surface.

Composition:
visible contracts
  -> bounded relaxed candidate search (<=31 non-empty subsets for k<=5)
  -> exact pinned LiveBench checker vector
  -> semantic next-cardinality UNSAT certificates
  -> pointwise score-optimality certificate

The public LiveBench checkout is supplied locally and must match the pinned
checker source blobs before any checker executes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_legacy15_exact_contract_checker_v1 as exact
from canonical.runtime import livebench_legacy15_pointwise_search_v1 as search

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_EXACT_POINTWISE_SOLVER_V1"


def solve(
    contracts: Sequence[Mapping[str, Any]],
    livebench_root: str | Path,
    *,
    max_per_subset: int = 16,
    max_total: int = 512,
) -> dict[str, Any]:
    rows = [dict(x) for x in contracts]
    source = exact.verify_pinned_source(livebench_root)
    checker = exact.checker_for_root(livebench_root)
    result = search.solve_with_checker(
        rows,
        checker,
        max_per_subset=max_per_subset,
        max_total=max_total,
    )
    result["schema"] = SCHEMA
    result["pinned_checker_source"] = source
    result["exact_checker_adapter_schema"] = exact.SCHEMA
    result["exact_checker_source_required"] = True
    result["terminal_data_used"] = False
    result["hidden_kwargs_used"] = False
    result["network_used"] = False
    result["acceptance_credit"] = False
    return result


def run(args: dict[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = args or {}
    livebench_root = args.get("livebench_root")
    if not livebench_root:
        raise ValueError("LIVEBENCH_ROOT_REQUIRED")
    return solve(
        args.get("contracts") or [],
        livebench_root,
        max_per_subset=int(args.get("max_per_subset") or 16),
        max_total=int(args.get("max_total") or 512),
    )


if __name__ == "__main__":
    import json
    import sys
    payload = json.load(sys.stdin)
    print(json.dumps(run(payload), ensure_ascii=False, indent=2, sort_keys=True))
