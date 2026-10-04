#!/usr/bin/env python3
"""Exact four-regime factorization of the LiveBench union25 hard extension.

Upstream reduces the 156 extra10 signatures to 20 hard kernels over six
families.  The frozen conflict graph makes those 20 kernels an exact union of
four tiny parametric regimes:

  COUNT_ONLY:
      any subset of keyword_frequency, letter_frequency, capital_word_frequency
      -> 2^3 = 8 kernels

  LANGUAGE:
      response_language plus any subset of
      letter_frequency, capital_word_frequency
      -> 2^2 = 4 kernels

  ENGLISH_CAPITAL:
      english_capital plus any subset of keyword_frequency, letter_frequency
      -> 2^2 = 4 kernels

  ENGLISH_LOWERCASE:
      english_lowercase plus any subset of keyword_frequency, letter_frequency
      -> 2^2 = 4 kernels

Thus the 20 apparently distinct composition problems require four constructor
regimes, not twenty handwritten solvers.  This is a structural scheduling
theorem only; it grants zero benchmark or capability credit.
"""
from __future__ import annotations

from itertools import chain, combinations
from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_union25_archetypes_v1 as u
from canonical.runtime import livebench_union25_extension_kernel_v1 as k

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_FOUR_REGIME_CUT_V1"

COUNT_AXES = frozenset({
    u.KEYWORD_FREQUENCY,
    u.LETTER_FREQUENCY,
    u.CAPITAL_FREQUENCY,
})
GLOBAL_MODES = frozenset({
    u.LANGUAGE,
    u.ENGLISH_CAPITAL,
    u.ENGLISH_LOWERCASE,
})

REGIME_AXES = {
    "COUNT_ONLY": (
        frozenset(),
        frozenset({
            u.KEYWORD_FREQUENCY,
            u.LETTER_FREQUENCY,
            u.CAPITAL_FREQUENCY,
        }),
    ),
    "LANGUAGE": (
        frozenset({u.LANGUAGE}),
        frozenset({
            u.LETTER_FREQUENCY,
            u.CAPITAL_FREQUENCY,
        }),
    ),
    "ENGLISH_CAPITAL": (
        frozenset({u.ENGLISH_CAPITAL}),
        frozenset({
            u.KEYWORD_FREQUENCY,
            u.LETTER_FREQUENCY,
        }),
    ),
    "ENGLISH_LOWERCASE": (
        frozenset({u.ENGLISH_LOWERCASE}),
        frozenset({
            u.KEYWORD_FREQUENCY,
            u.LETTER_FREQUENCY,
        }),
    ),
}

EXPECTED_REGIME_SIZES = {
    "COUNT_ONLY": 8,
    "LANGUAGE": 4,
    "ENGLISH_CAPITAL": 4,
    "ENGLISH_LOWERCASE": 4,
}


def _powerset(values: Sequence[str] | frozenset[str]) -> tuple[frozenset[str], ...]:
    seq = tuple(values)
    return tuple(
        frozenset(c)
        for n in range(len(seq) + 1)
        for c in combinations(seq, n)
    )


def _ordered(values: frozenset[str] | set[str]) -> tuple[str, ...]:
    s = set(values)
    return tuple(iid for iid in u.ALL_IDS if iid in s)


def regime_kernel_sets() -> dict[str, frozenset[tuple[str, ...]]]:
    out: dict[str, frozenset[tuple[str, ...]]] = {}
    for name, (required, optional) in REGIME_AXES.items():
        kernels = {
            _ordered(set(required) | set(extra))
            for extra in _powerset(optional)
        }
        out[name] = frozenset(kernels)
    return out


def classify(hard_signature: Sequence[str]) -> dict[str, Any]:
    sig = frozenset(hard_signature)
    if not sig <= k.HARD_EXTRA:
        raise ValueError("OUTSIDE_HARD_EXTRA")
    modes = sig & GLOBAL_MODES
    if len(modes) > 1:
        raise ValueError("MULTIPLE_GLOBAL_MODES_CONFLICT")
    if not modes:
        name = "COUNT_ONLY"
    elif u.LANGUAGE in modes:
        name = "LANGUAGE"
    elif u.ENGLISH_CAPITAL in modes:
        name = "ENGLISH_CAPITAL"
    else:
        name = "ENGLISH_LOWERCASE"

    required, optional = REGIME_AXES[name]
    if not required <= sig:
        raise ValueError("REGIME_REQUIRED_MODE_MISSING")
    residual = sig - required
    if not residual <= optional:
        raise ValueError("REGIME_FORBIDDEN_AXIS_PRESENT")
    return {
        "regime": name,
        "required": list(_ordered(required)),
        "active_optional_axes": list(_ordered(residual)),
    }


def verify() -> dict[str, Any]:
    upstream = k.verify()
    actual = {
        tuple(row["ids"])
        for row in upstream["hard_signatures"]
    }
    generated = regime_kernel_sets()

    union = set().union(*generated.values())
    if union != actual:
        missing = sorted(actual - union)
        invented = sorted(union - actual)
        raise AssertionError(
            f"FOUR_REGIME_NOT_EXACT:missing={missing}:invented={invented}"
        )

    seen: set[tuple[str, ...]] = set()
    for name, kernels in generated.items():
        if len(kernels) != EXPECTED_REGIME_SIZES[name]:
            raise AssertionError("REGIME_SIZE_DRIFT:" + name)
        overlap = seen & set(kernels)
        if overlap:
            raise AssertionError("REGIMES_NOT_DISJOINT:" + name)
        seen |= set(kernels)

    # The exact conflict graph is what permits the four factor products.
    # Count-only axes are mutually compatible.
    for a, b in combinations(COUNT_AXES, 2):
        if not u.compatible((a, b)):
            raise AssertionError(f"COUNT_AXIS_CONFLICT_DRIFT:{a}:{b}")

    # Language admits exactly LFREQ and CAPF among the three count axes.
    if u.compatible((u.LANGUAGE, u.KEYWORD_FREQUENCY)):
        raise AssertionError("LANGUAGE_KEYWORD_FREQUENCY_CONFLICT_DRIFT")
    for allowed in (u.LETTER_FREQUENCY, u.CAPITAL_FREQUENCY):
        if not u.compatible((u.LANGUAGE, allowed)):
            raise AssertionError("LANGUAGE_ALLOWED_AXIS_DRIFT:" + allowed)

    # Global English case modes admit exactly KFREQ and LFREQ among count axes.
    for mode in (u.ENGLISH_CAPITAL, u.ENGLISH_LOWERCASE):
        if u.compatible((mode, u.CAPITAL_FREQUENCY)):
            raise AssertionError("CASE_CAPITAL_FREQUENCY_CONFLICT_DRIFT:" + mode)
        for allowed in (u.KEYWORD_FREQUENCY, u.LETTER_FREQUENCY):
            if not u.compatible((mode, allowed)):
                raise AssertionError("CASE_ALLOWED_AXIS_DRIFT:" + mode + ":" + allowed)

    if u.compatible((u.ENGLISH_CAPITAL, u.ENGLISH_LOWERCASE)):
        raise AssertionError("UPPER_LOWER_CONFLICT_DRIFT")

    regime_rows = []
    for name in ("COUNT_ONLY", "LANGUAGE", "ENGLISH_CAPITAL", "ENGLISH_LOWERCASE"):
        required, optional = REGIME_AXES[name]
        regime_rows.append({
            "name": name,
            "required": list(_ordered(required)),
            "optional_count_axes": list(_ordered(optional)),
            "kernel_count": len(generated[name]),
        })

    return {
        "schema": SCHEMA,
        "status": "PASS__20_HARD_KERNELS_FACTOR_EXACTLY_TO_4_PARAMETRIC_SOLVER_REGIMES",
        "upstream_hard_kernel_count": len(actual),
        "solver_regime_count": len(generated),
        "structural_solver_path_reduction_factor": len(actual) / len(generated),
        "regimes": regime_rows,
        "regime_kernel_counts": EXPECTED_REGIME_SIZES,
        "exact_cover": True,
        "pairwise_disjoint": True,
        "maximum_regime_optional_axis_count": 3,
        "constructor_consequence": {
            "COUNT_ONLY": (
                "ONE_CALIBRATED_COUNT_CONSTRUCTOR_FOR_KFREQ_LFREQ_CAPF_SUBSETS"
            ),
            "LANGUAGE": (
                "ONE_LANGUAGE_SEED_CONSTRUCTOR_WITH_OPTIONAL_LFREQ_CAPF_CALIBRATION"
            ),
            "ENGLISH_CAPITAL": (
                "ONE_GLOBAL_UPPERCASE_CONSTRUCTOR_WITH_OPTIONAL_KFREQ_LFREQ_CALIBRATION"
            ),
            "ENGLISH_LOWERCASE": (
                "ONE_GLOBAL_LOWERCASE_CONSTRUCTOR_WITH_OPTIONAL_KFREQ_LFREQ_CALIBRATION"
            ),
        },
        "next_load_bearing_problem": (
            "IMPLEMENT_AND_EXACT_POSTVALIDATE_THE_4_PARAMETRIC_REGIME_CONSTRUCTORS_"
            "THEN_LIFT_THE_THREE_SYNTAX_OVERLAYS_AND_ACTIVE15_CONTEXT"
        ),
        "terminal_rows_used": False,
        "hidden_kwargs_used": False,
        "target_scores_used": False,
        "model_dependency_count": 0,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
