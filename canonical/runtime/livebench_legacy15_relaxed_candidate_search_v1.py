#!/usr/bin/env python3
"""Bounded subset-relaxation candidate search for frozen LiveBench legacy15.

Pointwise optimality is only useful if an unsatisfiable full conjunction still
has candidate responses that maximize the number of satisfiable checkers. The
existing joint candidate generator targets a supplied conjunction and can
correctly return no candidates when that conjunction is UNSAT.

The frozen historical generator has at most five checker contracts per case.
Therefore every non-empty relaxation is bounded by 2^5 - 1 = 31 subsets. This
module runs the existing visible-only generator on those subsets, deduplicates
responses, adds a tiny content-free baseline set, and emits candidates for exact
full-case postvalidation.

No terminal row, hidden kwargs, case id, comparator response, score, or target
frequency is consumed.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any, Iterable

from canonical.runtime import livebench_legacy15_joint_candidate_generator_v1 as base
from canonical.runtime import livebench_legacy15_composition_partition_v1 as partition

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_RELAXED_CANDIDATE_SEARCH_V1"
MAX_CHECKERS = 5
MAX_RELAXATIONS = (1 << MAX_CHECKERS) - 1
DEFAULT_MAX_PER_SUBSET = 16
DEFAULT_MAX_TOTAL = 512

_BASELINES = ("", "0", '""', "{}", "0******1")


def _normalize(constraints: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = [dict(c) for c in constraints]
    if not rows:
        raise ValueError("CONSTRAINTS_REQUIRED")
    if len(rows) > MAX_CHECKERS:
        raise ValueError("CHECKER_COUNT_EXCEEDS_FROZEN_BOUND")
    ids = [str(c.get("instruction_id") or "") for c in rows]
    if any(not x for x in ids):
        raise ValueError("INSTRUCTION_ID_REQUIRED")
    if len(ids) != len(set(ids)):
        raise ValueError("DUPLICATE_INSTRUCTION_ID")
    if any(c.get("parameter_complete") is not True for c in rows):
        raise ValueError("PARAMETER_INCOMPLETE")
    classification = partition.classify(ids)
    if classification.get("status") != "PASS":
        raise ValueError("ACTIVE15_CONFLICT_GRAPH_REJECTED")
    return rows


def generate_relaxed(
    constraints: Iterable[dict[str, Any]],
    *,
    max_per_subset: int = DEFAULT_MAX_PER_SUBSET,
    max_total: int = DEFAULT_MAX_TOTAL,
) -> dict[str, Any]:
    rows = _normalize(constraints)
    if max_per_subset < 1:
        raise ValueError("MAX_PER_SUBSET_MUST_BE_POSITIVE")
    if max_total < 1:
        raise ValueError("MAX_TOTAL_MUST_BE_POSITIVE")

    k = len(rows)
    seen: dict[str, dict[str, Any]] = {}
    subset_attempts = 0
    subset_generator_passes = 0

    def add(response: str, provenance: dict[str, Any]) -> None:
        if response in seen:
            seen[response]["provenance"].append(provenance)
            return
        if len(seen) >= max_total:
            return
        seen[response] = {
            "response": response,
            "provenance": [provenance],
        }

    # Baselines matter for constraints such as forbidden words or strict upper
    # bounds, where an empty/minimal response can already score checkers.
    for candidate in _BASELINES:
        add(candidate, {"kind": "BASELINE"})

    # Larger relaxations first. If max_total is reached, the pool therefore
    # preferentially retains candidates constructed to satisfy more checkers.
    for size in range(k, 0, -1):
        for subset in combinations(range(k), size):
            subset_attempts += 1
            subrows = [rows[i] for i in subset]
            out = base.generate(subrows, max_candidates=max_per_subset)
            if out.get("status") != "PASS_CANDIDATES":
                continue
            subset_generator_passes += 1
            provenance = {
                "kind": "RELAXED_SUBSET",
                "subset_indices": list(subset),
                "instruction_ids": [str(rows[i]["instruction_id"]) for i in subset],
                "mode": out.get("mode"),
            }
            for response in out.get("candidates") or []:
                add(str(response), provenance)
                if len(seen) >= max_total:
                    break
            if len(seen) >= max_total:
                break
        if len(seen) >= max_total:
            break

    candidates = list(seen.values())
    return {
        "schema": SCHEMA,
        "status": "PASS_CANDIDATE_POOL" if candidates else "FAIL_CLOSED_NO_CANDIDATES",
        "checker_count": k,
        "theoretical_nonempty_relaxation_count": (1 << k) - 1,
        "subset_attempt_count": subset_attempts,
        "subset_generator_pass_count": subset_generator_passes,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "requires_exact_full_case_checker_postvalidation": True,
        "pointwise_optimality_not_claimed_by_candidate_generation": True,
        "terminal_data_used": False,
        "hidden_kwargs_used": False,
        "terminal_case_id_used": False,
        "comparator_response_used": False,
        "acceptance_credit": False,
    }


def run(args: dict[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = args or {}
    return generate_relaxed(
        args.get("constraints") or [],
        max_per_subset=int(args.get("max_per_subset") or DEFAULT_MAX_PER_SUBSET),
        max_total=int(args.get("max_total") or DEFAULT_MAX_TOTAL),
    )


if __name__ == "__main__":
    import json
    import sys

    payload = json.load(sys.stdin)
    print(json.dumps(run(payload), ensure_ascii=False, indent=2, sort_keys=True))
