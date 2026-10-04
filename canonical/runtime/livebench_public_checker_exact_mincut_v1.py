#!/usr/bin/env python3
"""Exact minimum checker-family cut for the public IFBench 1/2-checker population.

Under the idealized family-perfect abstraction used by the public scheduling
frontier, selecting a checker family means that checker is guaranteed true on
every row containing it; unselected families are false.

For one-checker rows, a selected family contributes full score 1.
For two-checker rows, the frozen IFBench score is:
  none selected -> 0
  one selected  -> 1/4
  both selected -> 1

Multiplying score mass by four makes the objective integer:
  node weight = 4 * singleton_rows + pair_incidence
  edge bonus  = 2 * pair_row_multiplicity

The pair graph in the pinned public population is sparse. The global exact
maximum for every cardinality is therefore obtained by exhaustive enumeration
inside each connected component followed by dynamic programming across
components. This proves the minimum family cardinality without heuristic search.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import ceil
from typing import Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_PUBLIC_CHECKER_EXACT_MINCUT_V1"


class ExactCutError(ValueError):
    pass


@dataclass(frozen=True)
class CutPoint:
    family_count: int
    score4: int
    selected_families: tuple[str, ...]

    @property
    def score_mass(self) -> Fraction:
        return Fraction(self.score4, 4)


def _ids(row: Mapping[str, object]) -> tuple[str, ...]:
    raw = row.get("instruction_id_list")
    if not isinstance(raw, (list, tuple)):
        raise ExactCutError("INSTRUCTION_ID_LIST_REQUIRED")
    ids = tuple(str(x) for x in raw)
    if len(ids) not in (1, 2):
        raise ExactCutError("ONLY_ONE_OR_TWO_CHECKER_ROWS_SUPPORTED")
    if len(set(ids)) != len(ids):
        raise ExactCutError("DUPLICATE_CHECKER_IN_ROW")
    return ids


def build_integer_objective(rows: Iterable[Mapping[str, object]]):
    parsed = tuple(_ids(row) for row in rows)
    if not parsed:
        raise ExactCutError("ROWS_REQUIRED")

    families = tuple(sorted({x for ids in parsed for x in ids}))
    index = {name: i for i, name in enumerate(families)}
    n = len(families)
    node = [0] * n
    edge = [dict() for _ in range(n)]

    for ids in parsed:
        if len(ids) == 1:
            node[index[ids[0]]] += 4
            continue
        a, b = index[ids[0]], index[ids[1]]
        node[a] += 1
        node[b] += 1
        edge[a][b] = edge[a].get(b, 0) + 2
        edge[b][a] = edge[b].get(a, 0) + 2

    return parsed, families, tuple(node), tuple(edge)


def _components(edge: Sequence[Mapping[int, int]]) -> tuple[tuple[int, ...], ...]:
    seen = [False] * len(edge)
    out: list[tuple[int, ...]] = []
    for start in range(len(edge)):
        if seen[start]:
            continue
        stack = [start]
        seen[start] = True
        comp: list[int] = []
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in edge[u]:
                if not seen[v]:
                    seen[v] = True
                    stack.append(v)
        out.append(tuple(comp))
    return tuple(out)


def _component_options(
    comp: Sequence[int],
    node: Sequence[int],
    edge: Sequence[Mapping[int, int]],
    *,
    max_component_size: int,
):
    m = len(comp)
    if m > max_component_size:
        raise ExactCutError(f"COMPONENT_TOO_LARGE_FOR_EXACT_ENUMERATION:{m}")
    best: list[tuple[int, tuple[int, ...]] | None] = [None] * (m + 1)

    for mask in range(1 << m):
        selected = tuple(comp[j] for j in range(m) if (mask >> j) & 1)
        k = len(selected)
        score4 = sum(node[u] for u in selected)
        for a in range(len(selected)):
            for b in range(a + 1, len(selected)):
                score4 += edge[selected[a]].get(selected[b], 0)
        prior = best[k]
        if prior is None or score4 > prior[0]:
            best[k] = (score4, selected)
    return tuple(best)


def exact_frontier(
    rows: Iterable[Mapping[str, object]],
    *,
    max_component_size: int = 20,
) -> dict:
    parsed, families, node, edge = build_integer_objective(rows)
    components = _components(edge)
    options = [
        _component_options(
            comp,
            node,
            edge,
            max_component_size=max_component_size,
        )
        for comp in components
    ]

    dp: list[tuple[int, tuple[int, ...]] | None] = [(0, tuple())]
    for opt in options:
        nxt: list[tuple[int, tuple[int, ...]] | None] = [None] * (
            len(dp) + len(opt) - 1
        )
        for a, left in enumerate(dp):
            if left is None:
                continue
            for b, right in enumerate(opt):
                if right is None:
                    continue
                score4 = left[0] + right[0]
                k = a + b
                candidate = (score4, left[1] + right[1])
                if nxt[k] is None or score4 > nxt[k][0]:
                    nxt[k] = candidate
        dp = nxt

    points = []
    for k, value in enumerate(dp):
        if value is None:
            continue
        score4, selected = value
        points.append(
            CutPoint(
                family_count=k,
                score4=score4,
                selected_families=tuple(sorted(families[i] for i in selected)),
            )
        )

    return {
        "schema": SCHEMA,
        "row_count": len(parsed),
        "family_count": len(families),
        "component_sizes": tuple(sorted((len(c) for c in components), reverse=True)),
        "frontier": tuple(points),
    }


def minimum_cut(
    rows: Iterable[Mapping[str, object]],
    threshold_percent: Fraction,
    *,
    max_component_size: int = 20,
) -> dict:
    if not 0 <= threshold_percent <= 100:
        raise ExactCutError("THRESHOLD_PERCENT_OUT_OF_RANGE")

    solved = exact_frontier(rows, max_component_size=max_component_size)
    row_count = int(solved["row_count"])
    threshold4 = ceil(Fraction(row_count * 4, 1) * threshold_percent / 100)

    crossing: CutPoint | None = None
    for point in solved["frontier"]:
        if point.score4 >= threshold4:
            crossing = point
            break
    if crossing is None:
        raise ExactCutError("THRESHOLD_UNREACHABLE")

    previous = None
    if crossing.family_count:
        previous = solved["frontier"][crossing.family_count - 1]

    return {
        "schema": SCHEMA,
        "row_count": row_count,
        "family_count": solved["family_count"],
        "component_sizes": solved["component_sizes"],
        "threshold_percent": str(threshold_percent),
        "threshold_score4": threshold4,
        "minimum_family_count": crossing.family_count,
        "crossing_score4": crossing.score4,
        "crossing_score_mass": str(crossing.score_mass),
        "crossing_percent": str(crossing.score_mass * 100 / row_count),
        "selected_families": crossing.selected_families,
        "lower_neighbor_score4": previous.score4 if previous else None,
        "lower_neighbor_score_mass": str(previous.score_mass) if previous else None,
        "lower_neighbor_percent": (
            str(previous.score_mass * 100 / row_count) if previous else None
        ),
        "proof_method": (
            "EXHAUSTIVE_SUBSET_ENUMERATION_WITHIN_EACH_PAIR_GRAPH_CONNECTED_COMPONENT"
            "__EXACT_CARDINALITY_DYNAMIC_PROGRAMMING_ACROSS_COMPONENTS"
        ),
    }
