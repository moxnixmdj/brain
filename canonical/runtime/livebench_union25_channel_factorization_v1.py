#!/usr/bin/env python3
"""Exact channel factorization of the LiveBench union25 hard extension modes.

The verified union25 structural theorem exposes ten families outside Active15.
Three are passive decorators for hard-mode purposes:
  number_placeholders, number_highlighted_sections, punctuation:no_comma.

The remaining seven look like 21 separate hard signatures if enumerated flat.
They are not independent.  Every hard signature factors uniquely into:

GLOBAL CHASSIS (exactly one):
  NEUTRAL
  ENGLISH_UPPER
  ENGLISH_LOWER
  RESPONSE_LANGUAGE
  CONSTRAINED_SINGLETON

COUNT OVERLAYS (subset of three):
  KEYWORD_FREQUENCY
  LETTER_FREQUENCY
  CAPITAL_WORD_FREQUENCY

The pinned conflict graph gives the exact overlay mask per chassis:
  NEUTRAL          -> K, L, C   => 8 subsets
  ENGLISH_UPPER    -> K, L      => 4 subsets
  ENGLISH_LOWER    -> K, L      => 4 subsets
  RESPONSE_LANGUAGE-> L, C      => 4 subsets
  CONSTRAINED      -> none      => 1 subset
Total = 8 + 4 + 4 + 4 + 1 = 21.

This turns "build 21 unrelated constructors" into "build five chassis and
three reusable count adapters".  No terminal rows, hidden kwargs, responses,
frequencies, or target scores are used.
"""
from __future__ import annotations

from collections import Counter
from itertools import chain, combinations
from typing import Any, Iterable, Sequence

from canonical.runtime import livebench_union25_archetypes_v1 as u

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_CHANNEL_FACTORIZATION_V1"

K = u.KEYWORD_FREQUENCY
L = u.LETTER_FREQUENCY
C = u.CAPITAL_FREQUENCY
U = u.ENGLISH_CAPITAL
D = u.ENGLISH_LOWERCASE
G = u.LANGUAGE
R = u.CONSTRAINED

COUNT_OVERLAYS = (K, L, C)
PASSIVE = frozenset({u.PLACEHOLDERS, u.HIGHLIGHTS, u.NO_COMMA})
HARD7 = frozenset({K, L, C, U, D, G, R})

CHASSIS_ALLOWED_OVERLAYS = {
    "NEUTRAL": frozenset({K, L, C}),
    "ENGLISH_UPPER": frozenset({K, L}),
    "ENGLISH_LOWER": frozenset({K, L}),
    "RESPONSE_LANGUAGE": frozenset({L, C}),
    "CONSTRAINED_SINGLETON": frozenset(),
}

EXPECTED_SIGNATURES_PER_CHASSIS = {
    "NEUTRAL": 8,
    "ENGLISH_UPPER": 4,
    "ENGLISH_LOWER": 4,
    "RESPONSE_LANGUAGE": 4,
    "CONSTRAINED_SINGLETON": 1,
}


def powerset(values: Iterable[str]) -> tuple[frozenset[str], ...]:
    xs = tuple(values)
    return tuple(
        frozenset(part)
        for n in range(len(xs) + 1)
        for part in combinations(xs, n)
    )


def hard_signature(ids: Sequence[str]) -> frozenset[str]:
    return frozenset(set(u.extra_signature(ids)) - PASSIVE)


def factor_signature(sig: Iterable[str]) -> tuple[str, frozenset[str]]:
    s = frozenset(sig)
    if not s <= HARD7:
        raise ValueError("UNKNOWN_HARD_SIGNATURE")

    if R in s:
        if s != {R}:
            raise ValueError("CONSTRAINED_MUST_BE_SINGLETON")
        return "CONSTRAINED_SINGLETON", frozenset()

    global_bits = s & {U, D, G}
    if len(global_bits) > 1:
        raise ValueError("MULTIPLE_GLOBAL_CHASSIS")

    if U in global_bits:
        chassis = "ENGLISH_UPPER"
    elif D in global_bits:
        chassis = "ENGLISH_LOWER"
    elif G in global_bits:
        chassis = "RESPONSE_LANGUAGE"
    else:
        chassis = "NEUTRAL"

    overlays = s & set(COUNT_OVERLAYS)
    if not overlays <= CHASSIS_ALLOWED_OVERLAYS[chassis]:
        raise ValueError("OVERLAY_CONFLICT_WITH_CHASSIS")
    return chassis, frozenset(overlays)


def reconstruct(chassis: str, overlays: Iterable[str]) -> frozenset[str]:
    overlays = frozenset(overlays)
    if chassis not in CHASSIS_ALLOWED_OVERLAYS:
        raise ValueError("UNKNOWN_CHASSIS")
    if not overlays <= CHASSIS_ALLOWED_OVERLAYS[chassis]:
        raise ValueError("ILLEGAL_OVERLAY_FOR_CHASSIS")
    base = {
        "NEUTRAL": frozenset(),
        "ENGLISH_UPPER": frozenset({U}),
        "ENGLISH_LOWER": frozenset({D}),
        "RESPONSE_LANGUAGE": frozenset({G}),
        "CONSTRAINED_SINGLETON": frozenset({R}),
    }[chassis]
    if chassis == "CONSTRAINED_SINGLETON" and overlays:
        raise ValueError("CONSTRAINED_OVERLAY_FORBIDDEN")
    return base | overlays


def expected_factorized_signatures() -> frozenset[frozenset[str]]:
    out = []
    for chassis, allowed in CHASSIS_ALLOWED_OVERLAYS.items():
        for overlays in powerset(allowed):
            out.append(reconstruct(chassis, overlays))
    return frozenset(out)


def verify() -> dict[str, Any]:
    structural = u.verify()
    all_sets = u.enumerate_compatible_sets()
    extra_sets = [ids for ids in all_sets if set(ids) & set(u.EXTRA10)]

    observed = frozenset(hard_signature(ids) for ids in extra_sets)
    expected = expected_factorized_signatures()

    if observed != expected:
        raise AssertionError(
            "CHANNEL_FACTORIZATION_SIGNATURE_MISMATCH:"
            + repr(sorted(observed ^ expected, key=lambda x: (len(x), sorted(x))))
        )
    if len(observed) != 21:
        raise AssertionError("HARD_SIGNATURE_COUNT_DRIFT")

    roundtrip_failures = []
    factor_hist = Counter()
    for sig in observed:
        chassis, overlays = factor_signature(sig)
        rebuilt = reconstruct(chassis, overlays)
        if rebuilt != sig:
            roundtrip_failures.append((sig, chassis, overlays, rebuilt))
        factor_hist[chassis] += 1

    if roundtrip_failures:
        raise AssertionError("FACTORIZATION_NOT_BIJECTIVE:" + repr(roundtrip_failures))
    if dict(factor_hist) != EXPECTED_SIGNATURES_PER_CHASSIS:
        raise AssertionError("CHASSIS_SIGNATURE_HISTOGRAM_DRIFT:" + repr(dict(factor_hist)))

    # Structural independence facts that delete whole classes of pairwise work.
    if K in CHASSIS_ALLOWED_OVERLAYS["RESPONSE_LANGUAGE"]:
        raise AssertionError("LANGUAGE_KEYWORD_CONFLICT_LOST")
    if C in CHASSIS_ALLOWED_OVERLAYS["ENGLISH_UPPER"]:
        raise AssertionError("UPPER_CAPITAL_CONFLICT_LOST")
    if C in CHASSIS_ALLOWED_OVERLAYS["ENGLISH_LOWER"]:
        raise AssertionError("LOWER_CAPITAL_CONFLICT_LOST")

    return {
        "schema": SCHEMA,
        "status": "PASS__21_HARD_SIGNATURES_FACTOR_EXACTLY_INTO_5_CHASSIS_PLUS_3_COUNT_OVERLAYS",
        "pinned_registry_blob": u.PINNED_REGISTRY_BLOB,
        "upstream_union25_status": structural["status"],
        "union25_compatible_set_count": structural["compatible_total"],
        "extra_bearing_set_count": structural["extra_bearing_total"],
        "hard_signature_count": len(observed),
        "global_chassis_count": len(CHASSIS_ALLOWED_OVERLAYS),
        "count_overlay_count": len(COUNT_OVERLAYS),
        "signatures_per_chassis": dict(sorted(factor_hist.items())),
        "allowed_overlays": {
            chassis: sorted(values)
            for chassis, values in CHASSIS_ALLOWED_OVERLAYS.items()
        },
        "exact_factorization_identity": "21 = 8 + 4 + 4 + 4 + 1",
        "constructor_consequence": {
            "old_surface": "21_FLAT_HARD_EXTENSION_SIGNATURES",
            "new_surface": "5_GLOBAL_CHASSIS_PLUS_3_REUSABLE_COUNT_OVERLAYS",
            "global_chassis": [
                "NEUTRAL",
                "ENGLISH_UPPER",
                "ENGLISH_LOWER",
                "RESPONSE_LANGUAGE",
                "CONSTRAINED_SINGLETON",
            ],
            "count_overlays": [
                K,
                L,
                C,
            ],
            "deleted_cross_channels": [
                "RESPONSE_LANGUAGE_X_KEYWORD_FREQUENCY__REGISTRY_CONFLICT",
                "ENGLISH_UPPER_X_CAPITAL_WORD_FREQUENCY__REGISTRY_CONFLICT",
                "ENGLISH_LOWER_X_CAPITAL_WORD_FREQUENCY__REGISTRY_CONFLICT",
            ],
        },
        "next_load_bearing_problem": (
            "PROVE_FIVE_CHASSIS_CONSTRUCTORS_AND_THREE_REUSABLE_COUNT_ADAPTERS__"
            "THEN_BIND_THEIR_SMALL_REMAINING_COUNT_COUPLINGS_TO_ACTIVE15_FORCED_LITERALS"
        ),
        "terminal_rows_read": 0,
        "hidden_kwargs_read": 0,
        "terminal_instruction_id_lists_read": 0,
        "target_scores_read": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
    }


def run(args=None, root=None):
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
