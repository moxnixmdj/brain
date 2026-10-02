#!/usr/bin/env python3
"""Finite complete-verifier search bypass for Project Brain.

This mechanism replaces learned proposal generation only when:
1) the candidate universe is explicit and finite,
2) the verifier is deterministic for the frozen acceptance contract, and
3) exhaustive enumeration is within the declared bound.

It never claims semantic completeness of the candidate universe. If the universe
is incomplete, that is an upstream S0/G0 specification/model-acquisition hole.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Iterable, Sequence, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class SearchVerdict(Generic[T]):
    status: str
    passing: tuple[T, ...]
    examined: int
    complete_over_declared_universe: bool


def exhaustive_acceptance_search(
    candidates: Sequence[T],
    verifier: Callable[[T], bool],
    *,
    max_candidates: int = 100000,
) -> SearchVerdict[T]:
    if max_candidates < 0:
        raise ValueError("max_candidates must be nonnegative")
    if len(candidates) > max_candidates:
        return SearchVerdict(
            status="BOUND_EXCEEDED",
            passing=(),
            examined=0,
            complete_over_declared_universe=False,
        )

    passing: list[T] = []
    for candidate in candidates:
        result = verifier(candidate)
        if type(result) is not bool:
            raise TypeError("verifier must return bool")
        if result:
            passing.append(candidate)

    if not passing:
        status = "NO_ACCEPTED_CANDIDATE_IN_DECLARED_UNIVERSE"
    elif len(passing) == 1:
        status = "UNIQUE_ACCEPTED_CANDIDATE"
    else:
        status = "MULTIPLE_ACCEPTED_CANDIDATES__AMBIGUITY_PRESERVED"

    return SearchVerdict(
        status=status,
        passing=tuple(passing),
        examined=len(candidates),
        complete_over_declared_universe=True,
    )


def self_test() -> None:
    r = exhaustive_acceptance_search([1, 2, 3], lambda x: x == 2)
    assert r.status == "UNIQUE_ACCEPTED_CANDIDATE"
    assert r.passing == (2,)
    assert r.examined == 3
    assert r.complete_over_declared_universe is True

    r2 = exhaustive_acceptance_search([1, 2, 3, 4], lambda x: x % 2 == 0)
    assert r2.status == "MULTIPLE_ACCEPTED_CANDIDATES__AMBIGUITY_PRESERVED"
    assert r2.passing == (2, 4)

    r3 = exhaustive_acceptance_search([1, 2], lambda x: False)
    assert r3.status == "NO_ACCEPTED_CANDIDATE_IN_DECLARED_UNIVERSE"

    r4 = exhaustive_acceptance_search([1, 2], lambda x: True, max_candidates=1)
    assert r4.status == "BOUND_EXCEEDED"
    assert r4.examined == 0


if __name__ == "__main__":
    self_test()
    print("SELF_TEST_PASS")
