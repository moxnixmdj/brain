from __future__ import annotations

from collections import deque
from typing import Iterable, Mapping, Sequence

EPS = 1e-10


class PosetLiftError(ValueError):
    pass


def _normalize(dist: Mapping[str, float], outcomes: Sequence[str]) -> dict[str, float]:
    if not isinstance(dist, Mapping):
        raise PosetLiftError("DISTRIBUTION_REQUIRED")
    allowed = set(outcomes)
    if any(k not in allowed for k in dist):
        raise PosetLiftError("OUTCOME_OUTSIDE_DOMAIN")
    out = {x: float(dist.get(x, 0.0)) for x in outcomes}
    if any(p < -EPS for p in out.values()):
        raise PosetLiftError("NEGATIVE_PROBABILITY")
    total = sum(out.values())
    if abs(total - 1.0) > 1e-9:
        raise PosetLiftError("PROBABILITIES_MUST_SUM_TO_ONE")
    return {k: (0.0 if abs(v) <= EPS else v) for k, v in out.items()}


def validate_poset(
    outcomes: Sequence[str],
    geq_pairs: Iterable[tuple[str, str]],
) -> frozenset[tuple[str, str]]:
    xs = tuple(outcomes)
    if not xs or len(set(xs)) != len(xs):
        raise PosetLiftError("OUTCOME_DOMAIN_INVALID")
    domain = set(xs)
    rel = frozenset((str(a), str(b)) for a, b in geq_pairs)
    if any(a not in domain or b not in domain for a, b in rel):
        raise PosetLiftError("RELATION_OUTSIDE_DOMAIN")
    for x in xs:
        if (x, x) not in rel:
            raise PosetLiftError("RELATION_NOT_REFLEXIVE")
    for a in xs:
        for b in xs:
            if a != b and (a, b) in rel and (b, a) in rel:
                raise PosetLiftError("RELATION_NOT_ANTISYMMETRIC")
    for a in xs:
        for b in xs:
            if (a, b) not in rel:
                continue
            for c in xs:
                if (b, c) in rel and (a, c) not in rel:
                    raise PosetLiftError("RELATION_NOT_TRANSITIVE")
    return rel


def _add_edge(
    cap: dict[str, dict[str, float]],
    adj: dict[str, list[str]],
    u: str,
    v: str,
    capacity: float,
) -> None:
    cap.setdefault(u, {})
    cap.setdefault(v, {})
    adj.setdefault(u, [])
    adj.setdefault(v, [])
    if v not in adj[u]:
        adj[u].append(v)
    if u not in adj[v]:
        adj[v].append(u)
    cap[u][v] = cap[u].get(v, 0.0) + capacity
    cap[v].setdefault(u, 0.0)


def _max_flow(
    cap: dict[str, dict[str, float]],
    adj: dict[str, list[str]],
    source: str,
    sink: str,
) -> float:
    flow = 0.0
    while True:
        parent: dict[str, str | None] = {source: None}
        q = deque([source])
        while q and sink not in parent:
            u = q.popleft()
            for v in adj.get(u, []):
                if v not in parent and cap[u].get(v, 0.0) > EPS:
                    parent[v] = u
                    q.append(v)
        if sink not in parent:
            return flow
        aug = float("inf")
        v = sink
        while parent[v] is not None:
            u = parent[v]
            aug = min(aug, cap[u][v])
            v = u
        v = sink
        while parent[v] is not None:
            u = parent[v]
            cap[u][v] -= aug
            cap[v][u] = cap[v].get(u, 0.0) + aug
            v = u
        flow += aug


def monotone_coupling_exists(
    brain: Mapping[str, float],
    target: Mapping[str, float],
    *,
    outcomes: Sequence[str],
    geq_pairs: Iterable[tuple[str, str]],
) -> bool:
    """Finite stochastic order by constructive monotone transport.

    Returns True iff there exists a joint law gamma(B, O) with the supplied
    marginals and gamma(b, o) > 0 only when b >= o in the task outcome poset.
    """
    rel = validate_poset(outcomes, geq_pairs)
    bdist = _normalize(brain, outcomes)
    odist = _normalize(target, outcomes)

    source, sink = "__SOURCE__", "__SINK__"
    cap: dict[str, dict[str, float]] = {}
    adj: dict[str, list[str]] = {}

    for o in outcomes:
        _add_edge(cap, adj, source, "O:" + o, odist[o])
    for b in outcomes:
        _add_edge(cap, adj, "B:" + b, sink, bdist[b])
    for o in outcomes:
        for b in outcomes:
            if (b, o) in rel:
                _add_edge(cap, adj, "O:" + o, "B:" + b, 1.0)

    return _max_flow(cap, adj, source, sink) >= 1.0 - 1e-9


def _upward_closed(
    subset: frozenset[str],
    outcomes: Sequence[str],
    rel: frozenset[tuple[str, str]],
) -> bool:
    for x in subset:
        for y in outcomes:
            if (y, x) in rel and y not in subset:
                return False
    return True


def upper_set_dominates(
    brain: Mapping[str, float],
    target: Mapping[str, float],
    *,
    outcomes: Sequence[str],
    geq_pairs: Iterable[tuple[str, str]],
) -> bool:
    """Brute-force finite upper-set characterization, for verification only."""
    rel = validate_poset(outcomes, geq_pairs)
    if len(outcomes) > 16:
        raise PosetLiftError("UPPER_SET_VERIFIER_DOMAIN_TOO_LARGE")
    bdist = _normalize(brain, outcomes)
    odist = _normalize(target, outcomes)
    n = len(outcomes)
    for mask in range(1 << n):
        subset = frozenset(outcomes[i] for i in range(n) if mask & (1 << i))
        if not _upward_closed(subset, outcomes, rel):
            continue
        bp = sum(bdist[x] for x in subset)
        op = sum(odist[x] for x in subset)
        if bp + EPS < op:
            return False
    return True


def compile_finite_falsifier() -> dict[str, object]:
    binary = ("failure", "success")
    binary_rel = {
        ("failure", "failure"),
        ("success", "success"),
        ("success", "failure"),
    }
    reliability = monotone_coupling_exists(
        {"failure": 0.49, "success": 0.51},
        {"failure": 0.01, "success": 0.99},
        outcomes=binary,
        geq_pairs=binary_rel,
    )

    ordered = ("low", "middle", "high")
    ordered_rel = {
        ("low", "low"),
        ("middle", "middle"),
        ("high", "high"),
        ("middle", "low"),
        ("high", "middle"),
        ("high", "low"),
    }
    brain_mid = {"middle": 1.0}
    target_tail = {"low": 0.5, "high": 0.5}
    brain_over_tail = monotone_coupling_exists(
        brain_mid, target_tail, outcomes=ordered, geq_pairs=ordered_rel
    )
    tail_over_brain = monotone_coupling_exists(
        target_tail, brain_mid, outcomes=ordered, geq_pairs=ordered_rel
    )

    incomparable = ("a", "b")
    incomparable_rel = {("a", "a"), ("b", "b")}
    tradeoff = monotone_coupling_exists(
        {"b": 1.0},
        {"a": 1.0},
        outcomes=incomparable,
        geq_pairs=incomparable_rel,
    )

    perfect = monotone_coupling_exists(
        {"success": 1.0},
        {"failure": 0.01, "success": 0.99},
        outcomes=binary,
        geq_pairs=binary_rel,
    )

    return {
        "status": "PASS__FINITE_POSET_STOCHASTIC_LIFT_FALSIFIERS"
        if (not reliability and not brain_over_tail and not tail_over_brain and not tradeoff and perfect)
        else "FAIL_CLOSED",
        "reliability_gap_rejected": not reliability,
        "equal_mean_tail_crossing_incomparable": not brain_over_tail and not tail_over_brain,
        "unordered_tradeoff_rejected": not tradeoff,
        "strictly_better_distribution_accepted": perfect,
        "terminal_credit": False,
    }
