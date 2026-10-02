"""Exact one-sided lower confidence bound for finite binary benchmark populations.

Use case
--------
A benchmark release contains N fixed tasks and the terminal predicate is a strict
binary pass-rate threshold. Running all N tasks may be unnecessarily expensive.
If n tasks are sampled uniformly without replacement *before seeing outcomes*,
this module inverts the exact hypergeometric tail to obtain a conservative lower
confidence bound on the number of successes in the entire fixed population.

No iid or infinite-population approximation is used.

Important: this proves only the frozen population metric represented by the sampled
tasks. It does not repair harness mismatch, contamination, inaccessible/private
tasks, or a non-binary/model-judge metric.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from math import comb
from typing import Any


@dataclass(frozen=True)
class FinitePopulationVerdict:
    population_size: int
    sample_size: int
    sample_successes: int
    alpha: float
    lower_success_count: int
    lower_rate: float
    threshold_rate: float
    threshold_success_count: int
    pass_lower_bound: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _hypergeom_upper_tail(N: int, K: int, n: int, x: int) -> float:
    """P[X >= x] for X~Hypergeom(N,K,n), computed exactly with integer sums."""
    if not (0 <= K <= N and 0 <= n <= N and 0 <= x <= n):
        raise ValueError("invalid hypergeometric parameters")
    lo = max(x, 0, n - (N - K))
    hi = min(n, K)
    if lo > hi:
        return 0.0
    denominator = comb(N, n)
    numerator = sum(comb(K, k) * comb(N - K, n - k) for k in range(lo, hi + 1))
    return numerator / denominator


def exact_lower_success_count(N: int, n: int, x: int, alpha: float = 0.05) -> int:
    """Return a 1-alpha exact one-sided lower confidence bound on total successes K.

    This inverts tests H0: K <= K0.  Values K0 whose probability of observing at
    least x sample successes is < alpha are rejected.  The first non-rejected K is
    the lower confidence bound.
    """
    if not isinstance(N, int) or not isinstance(n, int) or not isinstance(x, int):
        raise TypeError("N, n, x must be integers")
    if N <= 0 or not (0 <= n <= N) or not (0 <= x <= n):
        raise ValueError("require N>0 and 0<=x<=n<=N")
    if not isinstance(alpha, (int, float)) or not (0 < float(alpha) < 1):
        raise ValueError("alpha must be in (0,1)")
    alpha = float(alpha)

    # K cannot be smaller than x because the sample already contains x successes.
    for K in range(x, N + 1):
        if _hypergeom_upper_tail(N, K, n, x) >= alpha:
            return K
    return N  # defensive; K=N always has tail 1 when x<=n


def threshold_success_count(N: int, threshold_rate: float) -> int:
    """Minimum integer K whose population rate is at least threshold_rate."""
    if N <= 0:
        raise ValueError("N must be positive")
    if not isinstance(threshold_rate, (int, float)) or not (0 <= float(threshold_rate) <= 1):
        raise ValueError("threshold_rate must be in [0,1]")
    # ceil(N*t) without floating-point edge surprises.
    t = float(threshold_rate)
    k = int(N * t)
    if k / N + 1e-15 < t:
        k += 1
    return min(N, k)


def evaluate_binary_population(
    *,
    population_size: int,
    sample_size: int,
    sample_successes: int,
    threshold_rate: float,
    alpha: float = 0.05,
) -> dict[str, Any]:
    lower = exact_lower_success_count(
        population_size, sample_size, sample_successes, alpha
    )
    needed = threshold_success_count(population_size, threshold_rate)
    verdict = FinitePopulationVerdict(
        population_size=population_size,
        sample_size=sample_size,
        sample_successes=sample_successes,
        alpha=float(alpha),
        lower_success_count=lower,
        lower_rate=lower / population_size,
        threshold_rate=float(threshold_rate),
        threshold_success_count=needed,
        pass_lower_bound=lower >= needed,
    )
    return {
        "schema": "BRAIN_FINITE_BINARY_POPULATION_LOWER_BOUND_V1",
        "status": "PASS" if verdict.pass_lower_bound else "INSUFFICIENT_EVIDENCE",
        **verdict.to_dict(),
        "assumptions": [
            "FROZEN_FINITE_POPULATION",
            "UNIFORM_SAMPLE_WITHOUT_REPLACEMENT_PRECOMMITTED_BEFORE_OUTCOMES",
            "BINARY_PER_CASE_SCORING",
            "NO_CASE_REPLAY_OR_ADAPTIVE_CASE_SELECTION",
            "HARNESS_AND_SCORER_IDENTITY_FROZEN",
        ],
    }


def minimum_sample_size_for_all_successes(
    *, population_size: int, threshold_rate: float, alpha: float = 0.05
) -> int | None:
    """Smallest n such that n/n observed successes would prove the threshold."""
    N = population_size
    for n in range(1, N + 1):
        out = evaluate_binary_population(
            population_size=N,
            sample_size=n,
            sample_successes=n,
            threshold_rate=threshold_rate,
            alpha=alpha,
        )
        if out["pass_lower_bound"]:
            return n
    return None
