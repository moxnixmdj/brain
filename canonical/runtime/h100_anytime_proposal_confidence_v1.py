"""Anytime-valid Bernoulli confidence sequence for H100 proposal viability.

Uses exact Clopper-Pearson bounds with summable alpha spending.  For two-sided
confidence level 1-alpha, each side receives alpha/2 and time t receives
alpha_side/(t*(t+1)). Since sum_{t>=1} 1/(t(t+1)) = 1, a union bound gives
simultaneous coverage over every stopping time without optional-stopping leakage.

This is intentionally conservative and dependency-free. It is an operational
stopping instrument, not open-world evidence and not capability credit.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_H100_ANYTIME_PROPOSAL_SEQUENCE_V1"
ALPHA = 0.05


class AnytimeProposalError(ValueError):
    pass


def _log_binomial_term(n: int, k: int, p: float) -> float:
    if p <= 0.0:
        return 0.0 if k == 0 else -math.inf
    if p >= 1.0:
        return 0.0 if k == n else -math.inf
    return (
        math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
        + k * math.log(p) + (n - k) * math.log1p(-p)
    )


def _tail(n: int, k: int, p: float) -> float:
    """P[X >= k] for X~Binomial(n,p)."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    logs = [_log_binomial_term(n, j, p) for j in range(k, n + 1)]
    m = max(logs)
    if m == -math.inf:
        return 0.0
    return math.exp(m) * sum(math.exp(x - m) for x in logs)


def _cdf(n: int, k: int, p: float) -> float:
    """P[X <= k] for X~Binomial(n,p)."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    logs = [_log_binomial_term(n, j, p) for j in range(0, k + 1)]
    m = max(logs)
    if m == -math.inf:
        return 0.0
    return math.exp(m) * sum(math.exp(x - m) for x in logs)


def _validate_counts(successes: int, trials: int) -> None:
    if not isinstance(successes, int) or isinstance(successes, bool):
        raise AnytimeProposalError("SUCCESSES_INVALID")
    if not isinstance(trials, int) or isinstance(trials, bool) or trials <= 0:
        raise AnytimeProposalError("TRIALS_INVALID")
    if successes < 0 or successes > trials:
        raise AnytimeProposalError("SUCCESSES_OUT_OF_RANGE")


def _spend(alpha: float, trials: int) -> float:
    if not isinstance(alpha, (int, float)) or isinstance(alpha, bool) or not 0.0 < float(alpha) < 1.0:
        raise AnytimeProposalError("ALPHA_INVALID")
    return (float(alpha) / 2.0) / (trials * (trials + 1))


def lower_bound(successes: int, trials: int, alpha: float = ALPHA) -> float:
    _validate_counts(successes, trials)
    a = _spend(alpha, trials)
    if successes == 0:
        return 0.0
    if successes == trials:
        return a ** (1.0 / trials)
    lo, hi = 0.0, successes / trials
    for _ in range(90):
        mid = (lo + hi) / 2.0
        if _tail(trials, successes, mid) < a:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def upper_bound(successes: int, trials: int, alpha: float = ALPHA) -> float:
    _validate_counts(successes, trials)
    a = _spend(alpha, trials)
    if successes == trials:
        return 1.0
    if successes == 0:
        return 1.0 - a ** (1.0 / trials)
    lo, hi = successes / trials, 1.0
    for _ in range(90):
        mid = (lo + hi) / 2.0
        if _cdf(trials, successes, mid) < a:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0


def n95_from_p(p: float) -> int | None:
    if not isinstance(p, (int, float)) or isinstance(p, bool):
        raise AnytimeProposalError("P_INVALID")
    p = float(p)
    if p <= 0.0:
        return None
    if p >= 1.0:
        return 1
    return int(math.ceil(math.log(0.05) / math.log1p(-p)))


def sequence(outcomes: Sequence[bool], *, viability_p: float, alpha: float = ALPHA) -> dict[str, Any]:
    if not isinstance(outcomes, Sequence) or isinstance(outcomes, (str, bytes)) or not outcomes:
        raise AnytimeProposalError("OUTCOMES_INVALID")
    if not isinstance(viability_p, (int, float)) or isinstance(viability_p, bool) or not 0.0 < float(viability_p) < 1.0:
        raise AnytimeProposalError("VIABILITY_P_INVALID")
    viability_p = float(viability_p)

    successes = 0
    trace = []
    decision = "CONTINUE"
    stopping_time = None
    for t, value in enumerate(outcomes, start=1):
        if not isinstance(value, bool):
            raise AnytimeProposalError(f"OUTCOME_NOT_BOOL:{t}")
        successes += int(value)
        lo = lower_bound(successes, t, alpha)
        hi = upper_bound(successes, t, alpha)
        if decision == "CONTINUE":
            if lo >= viability_p:
                decision = "VIABLE"
                stopping_time = t
            elif hi < viability_p:
                decision = "FUTILITY"
                stopping_time = t
        trace.append({
            "t": t,
            "successes": successes,
            "p_mle": successes / t,
            "p_lower_anytime": lo,
            "p_upper_anytime": hi,
            "alpha_side_spent_at_t": _spend(alpha, t),
            "n95_from_lower": n95_from_p(lo),
            "decision_if_first_crossing": decision if stopping_time == t else "NONE",
        })

    final = trace[-1]
    return {
        "schema": SCHEMA,
        "status": decision,
        "stopping_time": stopping_time,
        "trials_observed": len(outcomes),
        "successes_observed": successes,
        "viability_p": viability_p,
        "alpha": float(alpha),
        "p_lower_anytime": final["p_lower_anytime"],
        "p_upper_anytime": final["p_upper_anytime"],
        "n95_from_lower": final["n95_from_lower"],
        "trace": trace,
        "coverage_rule": "TWO_SIDED_ALPHA_SPENDING__ALPHA_OVER_2_T_TPLUS1_PER_SIDE__UNION_BOUND_ANYTIME_VALID",
        "hard_nonclaims": [
            "FINITE_PREEXPOSED_SEQUENCE_IS_NOT_OPEN_WORLD_PROOF",
            "STOPPING_DECISION_CREATES_NO_ACCEPTANCE_OR_CAPABILITY_CREDIT",
            "NO_H100_TERMINAL_CREDIT",
        ],
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
