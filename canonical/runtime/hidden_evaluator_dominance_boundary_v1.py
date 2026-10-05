from __future__ import annotations

from fractions import Fraction
from typing import Hashable, Mapping, TypeVar

Y = TypeVar("Y", bound=Hashable)
ExactProbability = Fraction | int | str | tuple[int, int]


def _fraction(value: ExactProbability) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, bool):
        raise TypeError("bool is not an exact probability literal")
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, str):
        return Fraction(value)
    if isinstance(value, tuple) and len(value) == 2:
        return Fraction(value[0], value[1])
    raise TypeError("probabilities must be exact rational literals")


def _distribution(values: Mapping[Y, ExactProbability]) -> dict[Y, Fraction]:
    out = {y: _fraction(p) for y, p in values.items()}
    if any(p < 0 for p in out.values()):
        raise ValueError("negative probability")
    if sum(out.values(), Fraction(0, 1)) != 1:
        raise ValueError("distribution must sum exactly to 1")
    return out


def hidden_evaluator_universal_noninferiority(
    target: Mapping[Y, ExactProbability],
    brain: Mapping[Y, ExactProbability],
) -> bool:
    """
    Decide whether Brain weakly dominates Target for every hidden utility u:Y->[0,1].

    Finite-output theorem:
      E_brain[u] >= E_target[u] for every bounded hidden u
      iff brain == target as distributions.

    Indicator utilities u_y(z)=1[z=y] force brain(y)>=target(y) for every y.
    Since both distributions sum to one, all inequalities can hold only at equality.
    """
    p = _distribution(target)
    q = _distribution(brain)
    support = set(p) | set(q)
    return all(q.get(y, Fraction(0, 1)) >= p.get(y, Fraction(0, 1)) for y in support)


def distinguishing_hidden_utility(
    target: Mapping[Y, ExactProbability],
    brain: Mapping[Y, ExactProbability],
) -> Y | None:
    """
    Return an output y whose indicator utility proves Brain inferior, if distributions differ.
    """
    p = _distribution(target)
    q = _distribution(brain)
    for y in sorted(set(p) | set(q), key=repr):
        if q.get(y, Fraction(0, 1)) < p.get(y, Fraction(0, 1)):
            return y
    return None
