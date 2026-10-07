from __future__ import annotations

from typing import Sequence, Tuple

Point = Tuple[float, ...]


def geq(a: Point, b: Point) -> bool:
    if len(a) != len(b):
        raise ValueError("DIMENSION_MISMATCH")
    return all(x >= y for x, y in zip(a, b))


def strict_geq(a: Point, b: Point) -> bool:
    return geq(a, b) and a != b


def pareto_frontier(points: Sequence[Point]) -> tuple[Point, ...]:
    out: list[Point] = []
    for i, p in enumerate(points):
        if not any(i != j and strict_geq(q, p) for j, q in enumerate(points)):
            out.append(p)
    return tuple(out)


def owned_frontier_simulates(opus: Sequence[Point], brain: Sequence[Point]) -> bool:
    of = pareto_frontier(opus)
    bf = pareto_frontier(brain)
    return all(any(geq(b, o) for b in bf) for o in of)


def punctuation_case() -> dict[str, object]:
    return {
        "raw_trace_differs": "4." != "4",
        "outcome_equivalent": (1.0, 1.0, 1.0) == (1.0, 1.0, 1.0),
        "simulation_passes": owned_frontier_simulates(((1.0, 1.0, 1.0),), ((1.0, 1.0, 1.0),)),
    }


def tradeoff_case() -> dict[str, object]:
    opus = ((2.0, 1.0), (1.0, 2.0))
    brain = ((2.0, 1.0),)
    return {"simulation_passes": owned_frontier_simulates(opus, brain)}


def hidden_capability_case() -> dict[str, object]:
    opus = ((1.0, 1.0), (3.0, 0.5))
    brain = ((1.0, 1.0),)
    return {"simulation_passes": owned_frontier_simulates(opus, brain)}


def better_case() -> dict[str, object]:
    return {"simulation_passes": owned_frontier_simulates(((1.0, 1.0),), ((1.1, 1.2),))}


def compile_kernel() -> dict[str, object]:
    p = punctuation_case()
    t = tradeoff_case()
    h = hidden_capability_case()
    b = better_case()
    if not (p["raw_trace_differs"] and p["outcome_equivalent"] and p["simulation_passes"]):
        return {"status": "FAIL_CLOSED", "error": "EQUIVALENCE_CASE"}
    if t["simulation_passes"] is not False:
        return {"status": "FAIL_CLOSED", "error": "TRADEOFF_COLLAPSE"}
    if h["simulation_passes"] is not False:
        return {"status": "FAIL_CLOSED", "error": "HIDDEN_CAPABILITY_ESCAPE"}
    if b["simulation_passes"] is not True:
        return {"status": "FAIL_CLOSED", "error": "BETTER_CASE"}
    return {
        "status": "PASS__FINITE_FRONTIER_SIMULATION_KERNEL",
        "terminal_credit": False,
        "classification": "TRUTH_REPAIR_CANDIDATE",
    }
