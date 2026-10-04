#!/usr/bin/env python3
"""Exact minimum checker-type cut for the public IFBench 1/2-instruction population.

The solver is distribution-only. It never reads response text or terminal
LiveBench prompt content. Given rows containing only instruction_id_list, it
finds the minimum number of instruction types that, under a conservative
type-universal success model, force a requested threshold under the frozen
LiveBench IF scoring rule:

    prompt_score = 0.5 * all_instructions_followed
                 + 0.5 * mean(individual_instruction_followed)

Scores are represented as integers scaled by four, so no floating point
participates in the threshold proof.
"""
from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from typing import Any, Iterable

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_IF_MINIMUM_CHECKER_SURFACE_CUT_V1"


class SurfaceCutError(ValueError):
    pass


def _normalize_rows(rows: Iterable[dict[str, Any]]) -> list[tuple[str, ...]]:
    out: list[tuple[str, ...]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise SurfaceCutError(f"ROW_NOT_OBJECT:{index}")
        raw = row.get("instruction_id_list")
        if not isinstance(raw, list):
            raise SurfaceCutError(f"INSTRUCTION_ID_LIST_REQUIRED:{index}")
        ids = tuple(str(x).strip() for x in raw)
        if len(ids) not in (1, 2):
            raise SurfaceCutError(f"UNSUPPORTED_INSTRUCTION_ARITY:{index}:{len(ids)}")
        if any(not x for x in ids):
            raise SurfaceCutError(f"EMPTY_INSTRUCTION_ID:{index}")
        if len(set(ids)) != len(ids):
            raise SurfaceCutError(f"DUPLICATE_INSTRUCTION_ID:{index}")
        out.append(ids)
    if not out:
        raise SurfaceCutError("ROWS_REQUIRED")
    return out


def _prefer(candidate, current):
    if current is None:
        return candidate
    c_score, c_sel = candidate
    score, sel = current
    if c_score != score:
        return candidate if c_score > score else current
    return candidate if c_sel < sel else current


def _score_components(normalized, selected_names):
    counts = {
        "single_pass": 0,
        "single_fail": 0,
        "pair_both": 0,
        "pair_one": 0,
        "pair_none": 0,
    }
    for ids in normalized:
        passed = sum(1 for x in ids if x in selected_names)
        if len(ids) == 1:
            counts["single_pass" if passed else "single_fail"] += 1
        elif passed == 2:
            counts["pair_both"] += 1
        elif passed == 1:
            counts["pair_one"] += 1
        else:
            counts["pair_none"] += 1
    return counts


def _score4_from_components(c):
    return 4 * c["single_pass"] + 4 * c["pair_both"] + c["pair_one"]


def solve(rows: Iterable[dict[str, Any]], threshold_percent="65.7") -> dict[str, Any]:
    normalized = _normalize_rows(rows)
    try:
        threshold = Fraction(str(threshold_percent))
    except Exception as exc:
        raise SurfaceCutError("INVALID_THRESHOLD") from exc
    if threshold < 0 or threshold > 100:
        raise SurfaceCutError("THRESHOLD_OUT_OF_RANGE")

    names = sorted({x for ids in normalized for x in ids})
    index = {name: i for i, name in enumerate(names)}
    singleton = [0] * len(names)
    edges = defaultdict(int)
    adjacency = [set() for _ in names]

    for ids in normalized:
        if len(ids) == 1:
            singleton[index[ids[0]]] += 1
            continue
        a, b = sorted((index[ids[0]], index[ids[1]]))
        edges[(a, b)] += 1
        adjacency[a].add(b)
        adjacency[b].add(a)

    components = []
    seen = set()
    for start in range(len(names)):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        comp = []
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in sorted(adjacency[u], reverse=True):
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        components.append(tuple(sorted(comp)))

    component_options = []
    for comp in components:
        local = set(comp)
        local_edges = [
            (a, b, weight)
            for (a, b), weight in edges.items()
            if a in local and b in local
        ]
        by_k = [None] * (len(comp) + 1)
        for mask in range(1 << len(comp)):
            selected = tuple(comp[j] for j in range(len(comp)) if (mask >> j) & 1)
            selected_set = set(selected)
            score4 = 4 * sum(singleton[v] for v in selected)
            for a, b, weight in local_edges:
                count = int(a in selected_set) + int(b in selected_set)
                if count == 2:
                    score4 += 4 * weight
                elif count == 1:
                    score4 += weight
            k = len(selected)
            by_k[k] = _prefer((score4, selected), by_k[k])
        component_options.append(by_k)

    dp = [(0, tuple())]
    for options in component_options:
        nxt = [None] * (len(dp) + len(options) - 1)
        for k0, state in enumerate(dp):
            if state is None:
                continue
            base_score, base_sel = state
            for kc, option in enumerate(options):
                if option is None:
                    continue
                score, sel = option
                k = k0 + kc
                merged = tuple(sorted(base_sel + sel))
                nxt[k] = _prefer((base_score + score, merged), nxt[k])
        dp = nxt

    n = len(normalized)

    def meets(score4):
        return Fraction(25 * score4, n) >= threshold

    minimum_k = next(
        (k for k, state in enumerate(dp) if state is not None and meets(state[0])),
        None,
    )
    if minimum_k is None:
        raise SurfaceCutError("THRESHOLD_UNREACHABLE")

    best_score4, best_ids = dp[minimum_k]
    best_names = [names[i] for i in best_ids]
    components_best = _score_components(normalized, set(best_names))
    if _score4_from_components(components_best) != best_score4:
        raise SurfaceCutError("INTERNAL_SCORE_MISMATCH")

    previous = None
    if minimum_k > 0 and dp[minimum_k - 1] is not None:
        p_score4, p_ids = dp[minimum_k - 1]
        p_names = [names[i] for i in p_ids]
        p_components = _score_components(normalized, set(p_names))
        previous = {
            "checker_type_count": minimum_k - 1,
            "score4": p_score4,
            "score_percent_fraction": str(Fraction(25 * p_score4, n)),
            "score_percent": float(Fraction(25 * p_score4, n)),
            "score_components": p_components,
            "checker_types": p_names,
        }

    arity = defaultdict(int)
    for ids in normalized:
        arity[len(ids)] += 1

    return {
        "schema": SCHEMA,
        "row_count": n,
        "instruction_type_count": len(names),
        "row_arity_distribution": {str(k): arity[k] for k in sorted(arity)},
        "threshold_percent_fraction": str(threshold),
        "threshold_percent": float(threshold),
        "minimum_checker_type_count": minimum_k,
        "best_score4": best_score4,
        "best_score_percent_fraction": str(Fraction(25 * best_score4, n)),
        "best_score_percent": float(Fraction(25 * best_score4, n)),
        "score_components": components_best,
        "checker_types": best_names,
        "best_with_one_fewer": previous,
        "proof_method": (
            "EXACT_COMPONENT_SUBSET_ENUMERATION_PLUS_CARDINALITY_DP__"
            "INTEGER_SCORE_X4__NO_FLOATING_POINT_IN_THRESHOLD_DECISION"
        ),
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return solve(args.get("rows") or [], args.get("threshold_percent", "65.7"))
