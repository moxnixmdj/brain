from __future__ import annotations

from fractions import Fraction
from functools import cmp_to_key
from math import gcd
from typing import Hashable, Mapping, TypeVar

H = TypeVar("H", bound=Hashable)
O = TypeVar("O", bound=Hashable)
T = TypeVar("T", bound=Hashable)

ExactProbability = Fraction | int | str | tuple[int, int]


def _fraction(value: ExactProbability) -> Fraction:
    """Convert an exact probability literal to Fraction. Floats are rejected."""
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
    raise TypeError(
        "probabilities must be exact: Fraction, int, 'a/b' string, or (a, b) tuple"
    )


def _lcm(a: int, b: int) -> int:
    if not a or not b:
        return 0
    return abs(a // gcd(a, b) * b)


def _normalize_prior(prior: Mapping[H, ExactProbability]) -> dict[H, Fraction]:
    if not prior:
        raise ValueError("prior must be non-empty")
    out = {h: _fraction(p) for h, p in prior.items()}
    if any(p < 0 for p in out.values()):
        raise ValueError("prior probabilities must be non-negative")
    if sum(out.values(), Fraction(0, 1)) != 1:
        raise ValueError("prior probabilities must sum exactly to 1")
    if all(p == 0 for p in out.values()):
        raise ValueError("prior must have positive mass")
    return out


def _normalize_likelihoods(
    prior: Mapping[H, Fraction],
    likelihoods: Mapping[H, Mapping[O, ExactProbability]],
) -> dict[H, dict[O, Fraction]]:
    if set(likelihoods) != set(prior):
        raise ValueError("likelihood rows must exist for exactly the prior hypotheses")
    out: dict[H, dict[O, Fraction]] = {}
    for h, row in likelihoods.items():
        if not row:
            raise ValueError(f"likelihood row for {h!r} must be non-empty")
        exact = {o: _fraction(p) for o, p in row.items()}
        if any(p < 0 for p in exact.values()):
            raise ValueError("likelihood probabilities must be non-negative")
        if sum(exact.values(), Fraction(0, 1)) != 1:
            raise ValueError(f"likelihood row for {h!r} must sum exactly to 1")
        out[h] = exact
    return out


def information_gain_log_terms(
    prior: Mapping[H, ExactProbability],
    likelihoods: Mapping[H, Mapping[O, ExactProbability]],
) -> dict[Fraction, Fraction]:
    """
    Return an exact symbolic representation of I(H;O) in natural-log units.

    The result maps each positive rational base r to its rational coefficient c,
    meaning I(H;O) = sum(c * ln(r)). No floating-point logarithms are used.
    """
    p_h = _normalize_prior(prior)
    cond = _normalize_likelihoods(p_h, likelihoods)
    observations = set()
    for row in cond.values():
        observations.update(row)

    p_o: dict[O, Fraction] = {}
    for o in observations:
        p_o[o] = sum(
            (p_h[h] * cond[h].get(o, Fraction(0, 1)) for h in p_h),
            Fraction(0, 1),
        )

    terms: dict[Fraction, Fraction] = {}
    for h, ph in p_h.items():
        if ph == 0:
            continue
        for o in observations:
            p_given_h = cond[h].get(o, Fraction(0, 1))
            joint = ph * p_given_h
            if joint == 0:
                continue
            po = p_o[o]
            if po <= 0:
                raise AssertionError("positive joint probability implies positive observation mass")
            base = joint / (ph * po)
            terms[base] = terms.get(base, Fraction(0, 1)) + joint

    return {base: coeff for base, coeff in terms.items() if coeff and base != 1}


def compare_information_gain(
    prior: Mapping[H, ExactProbability],
    likelihoods_a: Mapping[H, Mapping[O, ExactProbability]],
    likelihoods_b: Mapping[H, Mapping[O, ExactProbability]],
) -> int:
    """
    Compare two tests' expected information gain exactly.

    Returns 1 if A > B, 0 if equal, and -1 if A < B. For rational priors and
    likelihoods this comparison is exact despite logarithms: after clearing
    rational coefficients' denominators, sign(I_A-I_B) equals sign(ln(R))
    for one exactly computed positive rational R, hence equals sign(R-1).
    """
    a = information_gain_log_terms(prior, likelihoods_a)
    b = information_gain_log_terms(prior, likelihoods_b)
    diff: dict[Fraction, Fraction] = dict(a)
    for base, coeff in b.items():
        diff[base] = diff.get(base, Fraction(0, 1)) - coeff
    diff = {base: coeff for base, coeff in diff.items() if coeff}
    if not diff:
        return 0

    scale = 1
    for coeff in diff.values():
        scale = _lcm(scale, coeff.denominator)

    ratio = Fraction(1, 1)
    for base, coeff in diff.items():
        exponent = coeff.numerator * (scale // coeff.denominator)
        if exponent > 0:
            ratio *= base ** exponent
        elif exponent < 0:
            ratio /= base ** (-exponent)

    return (ratio > 1) - (ratio < 1)


def comparison_certificate(
    prior: Mapping[H, ExactProbability],
    likelihoods_a: Mapping[H, Mapping[O, ExactProbability]],
    likelihoods_b: Mapping[H, Mapping[O, ExactProbability]],
) -> dict[str, int | str]:
    """Emit a machine-checkable rational witness for an exact A-vs-B comparison."""
    a = information_gain_log_terms(prior, likelihoods_a)
    b = information_gain_log_terms(prior, likelihoods_b)
    diff: dict[Fraction, Fraction] = dict(a)
    for base, coeff in b.items():
        diff[base] = diff.get(base, Fraction(0, 1)) - coeff
    diff = {base: coeff for base, coeff in diff.items() if coeff}

    scale = 1
    for coeff in diff.values():
        scale = _lcm(scale, coeff.denominator)

    ratio = Fraction(1, 1)
    for base, coeff in diff.items():
        exponent = coeff.numerator * (scale // coeff.denominator)
        if exponent > 0:
            ratio *= base ** exponent
        elif exponent < 0:
            ratio /= base ** (-exponent)

    relation = "GT" if ratio > 1 else "LT" if ratio < 1 else "EQ"
    return {
        "coefficient_denominator_scale": scale,
        "rational_ratio_numerator": ratio.numerator,
        "rational_ratio_denominator": ratio.denominator,
        "relation": relation,
    }


def rank_tests_by_information_gain(
    prior: Mapping[H, ExactProbability],
    tests: Mapping[T, Mapping[H, Mapping[O, ExactProbability]]],
) -> list[T]:
    """Return test IDs from highest to lowest exact information gain."""
    ids = list(tests)

    def _cmp(a: T, b: T) -> int:
        return -compare_information_gain(prior, tests[a], tests[b])

    return sorted(ids, key=cmp_to_key(_cmp))
