#!/usr/bin/env python3
"""Choose the next experience so it actually teaches something.

THE MEASURED PROBLEM. After the applicability learner was wired into the live executor, three real
successes of the same chain still produced `UNDETERMINED__NO_CONTRASTING_OUTCOME` with zero
survivors. Repeating a job in the state it already worked in adds rows and no information. This is
why "let it experience the action once and it knows it permanently" fails: the first experience is
a point, and further identical points are the same point.

THE FIX IS CHOOSING, NOT MORE. A state `s` splits the surviving requirements into those that admit
`s` and those that refuse it. Whichever way the world answers, one side dies. The state whose split
is most even therefore guarantees the most progress, and a state where every survivor agrees has
exactly zero value however many times it is run. `what_a_success_teaches_20261112.py` measured the
consequence: chosen contrasts identify 25/25 requirements in a mean of 2.76 demonstrations, while
one success identifies 0 of 200.

REUSED, NOT REBUILT. Ranking uses `exact_information_gain`, which compares information gain with
exact rationals and no floating-point logarithms. A zero-gain test is recognised exactly (its log
term dict is empty), not by an epsilon on a float.

THE FAILURE MODE THIS REFUSES. Expected-information-gain selection is known to go wrong when it
proposes queries outside the region the system can actually realise -- "Wild Guesses and Mild
Guesses in Active Concept Learning" (arXiv 2602.06818) reports EIG inducing datasets outside the
generator's reliable support, and the crowd-RL line (arXiv 2508.19132) restricts queries to states
encountered in actual trajectories for the same reason. So the candidate pool here is ONLY states
that have actually been observed, plus the state the caller is in right now. This module never
invents a world, never proposes deleting a file to manufacture a failure, and never touches
anything. When no reachable state splits the survivors it says so, and names the facts that would
have to differ -- which is a request an operator or a scheduler can satisfy, not a guess.

Authority NONE. A pure function of evidence and a candidate pool. It executes nothing and changes
nothing. Zero model dependency, $0.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Iterable, Sequence

from canonical.runtime import applicability_v1 as APP
from canonical.runtime.exact_information_gain import (
    information_gain_log_terms,
    rank_tests_by_information_gain,
)

SCHEMA = "PROJECT_BRAIN_CONTRAST_SELECTION_V1"

NO_SPACE = "NO_REQUIREMENT_SPACE__NOTHING_TO_DISAMBIGUATE"
ALREADY_SETTLED = "ALREADY_IDENTIFIED__NO_CONTRAST_NEEDED"
NO_POOL = "NO_CANDIDATE_STATES_SUPPLIED"
NO_INFORMATIVE_STATE = "NO_REACHABLE_STATE_SPLITS_THE_SURVIVORS"
SELECTED = "SELECTED__A_REACHABLE_STATE_SPLITS_THE_SURVIVORS"

#: Likelihoods are deterministic: a requirement either admits a state or it does not. Expressing
#: them as exact integers keeps the whole computation in Fraction arithmetic.
_YES = "applicable"
_NO = "not_applicable"


@dataclass(frozen=True)
class Contrast:
    """What to try next, what it is guaranteed to teach, or why nothing can be taught yet."""

    schema: str
    status: str
    #: The recommended state, only when status is SELECTED.
    state: tuple[str, ...] | None
    survivors_before: int
    #: Largest number of survivors that can remain after this query, over both answers.
    worst_case_survivors_after: int | None
    #: Facts on which the survivors disagree. These are what a contrast has to vary.
    discriminating_facts: tuple[str, ...]
    #: Exact information gain as {rational base: rational coefficient}, natural-log units.
    gain_log_terms: dict[str, str]
    reason: str

    @property
    def informative(self) -> bool:
        return self.status == SELECTED

    def guaranteed_elimination(self) -> int:
        if self.worst_case_survivors_after is None:
            return 0
        return max(0, self.survivors_before - self.worst_case_survivors_after)

    def as_row(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "status": self.status,
            "state": None if self.state is None else list(self.state),
            "survivors_before": self.survivors_before,
            "worst_case_survivors_after": self.worst_case_survivors_after,
            "guaranteed_elimination": self.guaranteed_elimination(),
            "discriminating_facts": list(self.discriminating_facts),
            "gain_log_terms": dict(self.gain_log_terms),
            "reason": self.reason,
        }


def _split(requirements: Sequence[frozenset[str]], state: frozenset[str]) -> tuple[int, int]:
    yes = sum(1 for need in requirements if need <= state)
    return yes, len(requirements) - yes


def discriminating_facts(requirements: Sequence[frozenset[str]]) -> tuple[str, ...]:
    """Facts present in some survivors and absent from others.

    A fact every survivor requires, or none does, cannot be what separates them, so varying it
    teaches nothing. This is the difference between "try something different" and "try a run where
    THIS differs".
    """
    if not requirements:
        return ()
    union: frozenset[str] = frozenset().union(*requirements)
    intersection = frozenset(requirements[0])
    for need in requirements[1:]:
        intersection = intersection & need
    return tuple(sorted(union - intersection))


def _likelihoods(requirements: Sequence[frozenset[str]], state: frozenset[str]) -> dict:
    row = {}
    for need in requirements:
        key = "&".join(sorted(need)) or APP.EMPTY_KEY
        admits = need <= state
        row[key] = {_YES: 1 if admits else 0, _NO: 0 if admits else 1}
    return row


def select_contrast(
    evidence: Sequence[tuple[Iterable[str], bool]],
    candidate_states: Iterable[Iterable[str]] = (),
) -> Contrast:
    """Pick the reachable state that teaches the most, or explain why none can.

    `candidate_states` must be states the caller can actually realise. Observed states and the
    current state always qualify; an invented one does not, and this function has no way to check,
    so the caller owns that contract and this module keeps the pool small by default.
    """
    boundary = APP.learn(evidence)
    # Use the surviving SPACE, not the licensed boundary. After successes alone `learn` correctly
    # reports UNDETERMINED with no survivors -- but the successes still constrain which
    # requirements are possible, and that is precisely what makes a first contrast choosable.
    requirements = [frozenset(s) for s in APP.candidate_requirements(evidence)]

    def _stop(status: str, reason: str) -> Contrast:
        return Contrast(
            schema=SCHEMA, status=status, state=None,
            survivors_before=len(requirements), worst_case_survivors_after=None,
            discriminating_facts=discriminating_facts(requirements),
            gain_log_terms={}, reason=reason,
        )

    if not requirements:
        return _stop(NO_SPACE, boundary.status)
    if len(requirements) == 1 and boundary.identified:
        return _stop(ALREADY_SETTLED, "ONE_REQUIREMENT_ALREADY_EXPLAINS_EVERY_OUTCOME")

    pool = sorted({APP.normalise_state(s) for s in (candidate_states or ())}, key=lambda s: (len(s), sorted(s)))
    if not pool:
        return _stop(NO_POOL, "CALLER_SUPPLIED_NO_REACHABLE_STATE")

    # Uniform exact prior: the reused ranker requires probabilities summing to exactly 1, and
    # rejects floats outright. 1/n as a Fraction keeps the whole comparison exact.
    weight = Fraction(1, len(requirements))
    prior = {"&".join(sorted(need)) or APP.EMPTY_KEY: weight for need in requirements}
    tests = {index: _likelihoods(requirements, state) for index, state in enumerate(pool)}
    ranked = rank_tests_by_information_gain(prior, tests)

    best_index = ranked[0]
    terms = information_gain_log_terms(prior, tests[best_index])
    if not terms:
        # Exact zero, not a float below an epsilon: every survivor gives the same answer in every
        # reachable state, so no amount of repetition in this pool can teach anything.
        return _stop(NO_INFORMATIVE_STATE, "EVERY_REACHABLE_STATE_GIVES_THE_SAME_ANSWER_FOR_ALL_SURVIVORS")

    state = pool[best_index]
    yes, no = _split(requirements, state)
    return Contrast(
        schema=SCHEMA,
        status=SELECTED,
        state=tuple(sorted(state)),
        survivors_before=len(requirements),
        worst_case_survivors_after=max(yes, no),
        discriminating_facts=discriminating_facts(requirements),
        gain_log_terms={str(base): str(coeff) for base, coeff in terms.items()},
        reason="MOST_EVEN_SPLIT_OF_THE_SURVIVING_REQUIREMENTS",
    )


def observed_states(evidence: Sequence[tuple[Iterable[str], bool]]) -> list[frozenset[str]]:
    """The states already seen. Reachable by construction, because they happened."""
    seen = {APP.normalise_state(state) for state, _ in (evidence or ())}
    return sorted(seen, key=lambda s: (len(s), sorted(s)))
