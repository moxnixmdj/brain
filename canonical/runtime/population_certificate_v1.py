"""Certify a population of verified fates -- once, not repeatedly.

WHY THIS EXISTS, AND WHAT IT IS NOT
-----------------------------------

An earlier proposal in this series was to run the front door twenty times per goal and
stop on an anytime-valid lower bound. That proposal was **wrong, and it was measured
wrong**: `live_brain_route_admission_v1.solve` is deterministic. Two runs of the same
goal, diffed key by key, differ in exactly one field -- `elapsed_ns`. The verdict is
identical. Twenty identical runs of a deterministic function are **one sample repeated**,
so a confidence bound computed over them would be statistics theatre with a
respectable-looking number attached.

So this module does the opposite. It refuses to treat repetition as evidence:

    repeated identical trials are rejected, loudly, rather than averaged.

What survives is the regime where the rule is genuinely correct. Because the door is
deterministic, `solve(goal)` on a fixed corpus is not sampling -- it is a **census**.
Every goal is either verified or not, and the result does not vary. The open question
is not "what is the probability this goal passes" but:

    **is this corpus large enough for the claim I want to make about it?**

`h100_anytime_proposal_confidence_v1` answers exactly that, and its answer is
uncomfortable and useful. At 17 goals the interval is decisive only at the extremes:

    17/17  lower 0.575  DECIDED          (the corpus certifies unanimity)
    16/17  lower 0.483  UNDECIDED
    13/17  lower 0.294  UNDECIDED
     1/17  upper 0.517  UNDECIDED
     0/17  upper 0.425  DECIDED          (the corpus certifies universal failure)

and to certify a middling rate you need a much larger corpus (at n=200, 60/200 is
decisive at 0.471, 120/200 is still undecided).

**A corpus of 17 cannot certify "most goals pass". It can only certify "all" or "none".**
That is the fact this module exists to state out loud, instead of quoting "13 of 17"
as though the number meant something a reader could rely on.

AVOIDING THE ONE REAL STATISTICAL TRAP
--------------------------------------

The door is deterministic *given its inputs*. It is not deterministic across **seed**.
A capability that samples (mutation testing draws from a random basis; any search over
a random basis does) will vary run to run even though the goal is identical. For those,
repetition IS evidence, and `refuses_repetition_as_evidence` must be cleared with an
explicit `stochastic=True` that names the source of the randomness. Silence is not
consent: the default rejects.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime.h100_anytime_proposal_confidence_v1 import (
    lower_bound,
    upper_bound,
)

SCHEMA = "PROJECT_BRAIN_POPULATION_CERTIFICATE_V1"


class PopulationCertificateError(ValueError):
    """Malformed or inadmissible input. Never downgraded to a soft verdict."""


@dataclass(frozen=True)
class Certificate:
    """The interval a corpus actually supports, and whether it decided anything."""

    trials: int
    successes: int
    lower: float
    upper: float
    rate: float
    decided: bool
    verdict: str                      # "CERTIFIED_MAJORITY" | "CERTIFIED_MINORITY" | "UNDECIDED"
    claim: str                        # the sentence a paper is allowed to print

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "trials": self.trials,
            "successes": self.successes,
            "rate": round(self.rate, 6),
            "lower_bound": round(self.lower, 6),
            "upper_bound": round(self.upper, 6),
            "decided": self.decided,
            "verdict": self.verdict,
            "claim": self.claim,
        }


def refuses_repetition_as_evidence(
    fates: Sequence[str], *, stochastic: bool, source: str = ""
) -> bool:
    """True when the input is repetition of a deterministic fate and must not be certified.

    A census of one deterministic goal is one observation, however many times it is run.
    """
    if stochastic:
        if not source.strip():
            raise PopulationCertificateError(
                "STOCHASTIC_CLAIM_REQUIRES_NAMED_SOURCE_OF_RANDOMNESS"
            )
        return False
    return len(set(fates)) == 1 and len(fates) > 1


def certify(
    fates: Iterable[str],
    *,
    goals: Sequence[str] | None = None,
    stochastic: bool = False,
    source: str = "",
) -> Certificate:
    """Certificate over a population of goal fates ("pass" / anything else = not pass).

    `goals` must be supplied whenever the fates are unanimous (all pass or all fail).
    Unanimity is the one case where a census and a repeated single measurement look
    identical, so the caller has to name the distinct goals it measured. Distinct goal
    texts make unanimous fates a census; identical or missing goals make it repetition,
    and repetition is refused.
    """
    values = [str(f) for f in fates]
    if not values:
        raise PopulationCertificateError("EMPTY_POPULATION")

    if len(set(values)) == 1 and len(values) > 1 and not stochastic:
        distinct = {str(g) for g in (goals or ())}
        if len(distinct) != len(values):
            raise PopulationCertificateError(
                "UNANIMOUS_FATES_REQUIRE_DISTINCT_GOAL_IDENTITIES__"
                "pass `goals=` naming each goal measured; without it unanimity is "
                "indistinguishable from re-running one deterministic goal"
            )
    if stochastic and not source.strip():
        raise PopulationCertificateError(
            "STOCHASTIC_CLAIM_REQUIRES_NAMED_SOURCE_OF_RANDOMNESS"
        )

    successes = sum(1 for v in values if v == "pass")
    n = len(values)
    lb, ub = lower_bound(successes, n), upper_bound(successes, n)
    rate = successes / n

    if lb > 0.5:
        verdict, decided = "CERTIFIED_MAJORITY", True
        claim = (f"at least {lb:.1%} of goals in this corpus were verified "
                 f"({successes} of {n}), and the certified majority is excluded only "
                 f"by a rate below one half")
    elif ub < 0.5:
        verdict, decided = "CERTIFIED_MINORITY", True
        claim = (f"at most {ub:.1%} of goals in this corpus were verified "
                 f"({successes} of {n})")
    else:
        verdict, decided = "UNDECIDED", False
        claim = (f"{successes} of {n} goals were verified, but a corpus of {n} "
                 f"cannot certify a rate near one half: the interval is "
                 f"[{lb:.3f}, {ub:.3f}]. Report the counts, not a percentage.")

    return Certificate(n, successes, lb, ub, rate, decided, verdict, claim)


def corpus_needed_for(*, target_rate: float, tolerance: float = 0.5) -> int:
    """Smallest corpus on which a corpus at `target_rate` certifies against `tolerance`.

    Answers "how many goals do I need before the claim is real?" -- the question a
    corpus of 17 silently refuses to answer.

    The bound tightens monotonically in n for a fixed rate, so this binary-searches
    instead of scanning. The first version of this function scanned linearly and took
    **397 seconds** to answer four questions -- a fair demonstration that "insanely
    fast" has to be applied to the tools that measure speed, not only to the hot path.
    """
    if not 0.0 < target_rate <= 1.0:
        raise PopulationCertificateError("TARGET_RATE_OUT_OF_RANGE")

    def decides(n: int) -> bool:
        k = int(round(target_rate * n))
        if not 0 <= k <= n:
            return False
        try:
            return lower_bound(k, n) > tolerance or upper_bound(k, n) < tolerance
        except Exception:  # counts out of range at very small n
            return False

    lo, hi = 1, 8192
    if not decides(hi):
        return -1
    while lo < hi:
        mid = (lo + hi) // 2
        if decides(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo
