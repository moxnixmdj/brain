#!/usr/bin/env python3
"""Exact factorization of the LiveBench union25 delta10 extension kernel.

The previously verified union25 structural quotient exposes 156 distinct
signatures over the ten families outside the closed Active15 core.  This module
proves that those 156 signatures are not 156 independent composition problems.

After removing the structurally isolated constrained-response family, the
remaining nine extra families factor exactly into:

  * four graph-free commuting modifiers, compatible with every other extra
    family: letter frequency, placeholders, highlights, and no-comma; and
  * five semantic-axis families whose entire compatible state space has only
    ten states, nine non-empty:
        keyword frequency
        response language
        capital-word frequency
        English all-caps
        English all-lowercase
    with only four compatible two-axis combinations and no compatible triple.

Thus every one of the 155 non-constrained delta10 signatures has a unique
product representation (semantic_axis_state, commuting_modifier_subset).
This is a graph theorem only.  It deliberately grants no pointwise or
acceptance credit until the semantic composition lemmas are independently
verified against the exact checker bytes.
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime import livebench_union25_archetypes_v1 as u

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_EXTENSION_KERNEL_FACTORIZATION_V1"

KEYWORD_FREQUENCY = u.KEYWORD_FREQUENCY
LETTER_FREQUENCY = u.LETTER_FREQUENCY
LANGUAGE = u.LANGUAGE
PLACEHOLDERS = u.PLACEHOLDERS
CONSTRAINED = u.CONSTRAINED
HIGHLIGHTS = u.HIGHLIGHTS
CAPITAL_FREQUENCY = u.CAPITAL_FREQUENCY
ENGLISH_CAPITAL = u.ENGLISH_CAPITAL
ENGLISH_LOWERCASE = u.ENGLISH_LOWERCASE
NO_COMMA = u.NO_COMMA

COMMUTING4 = (
    LETTER_FREQUENCY,
    PLACEHOLDERS,
    HIGHLIGHTS,
    NO_COMMA,
)

SEMANTIC_AXIS5 = (
    KEYWORD_FREQUENCY,
    LANGUAGE,
    CAPITAL_FREQUENCY,
    ENGLISH_CAPITAL,
    ENGLISH_LOWERCASE,
)

EXPECTED_AXIS_STATES = (
    (),
    (KEYWORD_FREQUENCY,),
    (LANGUAGE,),
    (CAPITAL_FREQUENCY,),
    (ENGLISH_CAPITAL,),
    (ENGLISH_LOWERCASE,),
    (KEYWORD_FREQUENCY, CAPITAL_FREQUENCY),
    (KEYWORD_FREQUENCY, ENGLISH_CAPITAL),
    (KEYWORD_FREQUENCY, ENGLISH_LOWERCASE),
    (LANGUAGE, CAPITAL_FREQUENCY),
)

# The Active15 symbolic reduction proved 48 words is the global maximum before
# word-lower-bound padding for any compatible active15 case containing a
# "words < N" constraint.  Numeric placeholder/highlight carriers need at most
# four RegexpTokenizer words each and introduce no alphabetic characters.
ACTIVE15_LESS_THAN_WORD_GLOBAL_BOUND = 48
MAX_PUBLIC_PLACEHOLDERS = 4
MAX_PUBLIC_HIGHLIGHTS = 4
MIN_PUBLIC_LESS_THAN_WORD_THRESHOLD = 100
NEUTRAL_NUMERIC_CARRIER_BOUND = (
    ACTIVE15_LESS_THAN_WORD_GLOBAL_BOUND
    + MAX_PUBLIC_PLACEHOLDERS
    + MAX_PUBLIC_HIGHLIGHTS
)


class FactorizationError(RuntimeError):
    pass


def _subsets(values: Sequence[str]) -> tuple[tuple[str, ...], ...]:
    out: list[tuple[str, ...]] = []
    for n in range(len(values) + 1):
        out.extend(combinations(values, n))
    return tuple(out)


def _axis_states_from_graph() -> tuple[tuple[str, ...], ...]:
    out: list[tuple[str, ...]] = []
    for ids in _subsets(SEMANTIC_AXIS5):
        if u.compatible(ids):
            out.append(ids)
    return tuple(out)


def factor_signature(signature: Sequence[str]) -> dict[str, tuple[str, ...]]:
    sig = tuple(signature)
    if not sig:
        raise FactorizationError("EMPTY_EXTRA_SIGNATURE")
    if len(sig) != len(set(sig)):
        raise FactorizationError("DUPLICATE_EXTRA_ID")
    if any(iid not in u.EXTRA10 for iid in sig):
        raise FactorizationError("NON_EXTRA10_ID")
    if not u.compatible(sig):
        raise FactorizationError("INCOMPATIBLE_EXTRA_SIGNATURE")

    if CONSTRAINED in sig:
        if sig != (CONSTRAINED,):
            # ConstrainedResponse conflicts with every registry family.
            raise FactorizationError("CONSTRAINED_MUST_BE_SINGLETON")
        return {
            "semantic_axis": (),
            "commuting_modifiers": (),
            "isolated": (CONSTRAINED,),
        }

    present = set(sig)
    axis = tuple(iid for iid in SEMANTIC_AXIS5 if iid in present)
    modifiers = tuple(iid for iid in COMMUTING4 if iid in present)
    if set(axis) | set(modifiers) != present:
        raise FactorizationError("FACTORIZATION_PARTITION_DRIFT")
    return {
        "semantic_axis": axis,
        "commuting_modifiers": modifiers,
        "isolated": (),
    }


def _all_extra_signatures() -> tuple[tuple[str, ...], ...]:
    seen: set[tuple[str, ...]] = set()
    for ids in u.enumerate_compatible_sets():
        sig = u.extra_signature(ids)
        if sig:
            seen.add(sig)
    # Preserve the canonical registry order from union25 archetypes.
    order = {iid: i for i, iid in enumerate(u.ALL_IDS)}
    return tuple(sorted(seen, key=lambda s: (len(s), tuple(order[x] for x in s))))


def verify() -> dict[str, Any]:
    axis_states = _axis_states_from_graph()
    if axis_states != EXPECTED_AXIS_STATES:
        raise FactorizationError("SEMANTIC_AXIS_STATE_DRIFT")

    # Every commuting modifier must have zero conflict edges to every other
    # extra family except its self edge.  This is stronger than merely checking
    # pairwise compatibility for observed signatures.
    for modifier in COMMUTING4:
        extra_conflicts = (u.CONFLICTS[modifier] & set(u.EXTRA10)) - {modifier}
        if extra_conflicts:
            raise FactorizationError(
                "COMMUTING_MODIFIER_CONFLICT_DRIFT:"
                + modifier
                + ":"
                + ",".join(sorted(extra_conflicts))
            )

    signatures = _all_extra_signatures()
    if len(signatures) != u.EXPECTED_DISTINCT_EXTRA_SIGNATURES:
        raise FactorizationError("EXTRA_SIGNATURE_COUNT_DRIFT")

    isolated = 0
    product_pairs: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    axis_hist = Counter()
    modifier_hist = Counter()

    for sig in signatures:
        factored = factor_signature(sig)
        if factored["isolated"]:
            isolated += 1
            continue
        axis = factored["semantic_axis"]
        modifiers = factored["commuting_modifiers"]
        product_pairs.add((axis, modifiers))
        axis_hist[axis] += 1
        modifier_hist[len(modifiers)] += 1

    if isolated != 1:
        raise FactorizationError("ISOLATED_CONSTRAINED_COUNT_DRIFT")
    if len(product_pairs) != 155:
        raise FactorizationError("PRODUCT_SIGNATURE_COUNT_DRIFT")

    # Closed-form count:
    # axis size 0: 1 state * (2^4 - 1 non-empty modifier subsets) = 15
    # axis size 1: 5 states * 2^4 modifier subsets = 80
    # axis size 2: 4 states * sum(C(4,j), j=0..3) due max-5 IDs = 60
    # constrained singleton = 1
    axis_size_counts = Counter(map(len, axis_states))
    if axis_size_counts != Counter({0: 1, 1: 5, 2: 4}):
        raise FactorizationError("AXIS_SIZE_HISTOGRAM_DRIFT")
    closed_form_nonconstrained = 15 + 80 + 60
    if closed_form_nonconstrained != len(product_pairs):
        raise FactorizationError("CLOSED_FORM_COUNT_MISMATCH")
    if closed_form_nonconstrained + isolated != 156:
        raise FactorizationError("TOTAL_CLOSED_FORM_COUNT_MISMATCH")

    if NEUTRAL_NUMERIC_CARRIER_BOUND != 56:
        raise FactorizationError("NUMERIC_CARRIER_BOUND_DRIFT")
    if not NEUTRAL_NUMERIC_CARRIER_BOUND < MIN_PUBLIC_LESS_THAN_WORD_THRESHOLD:
        raise FactorizationError("NUMERIC_CARRIER_WORD_MARGIN_LOST")

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__156_DELTA10_SIGNATURES_FACTORED_TO_"
            "1_ISOLATED_PLUS_9_NONEMPTY_AXIS_STATES_PLUS_4_COMMUTING_MODIFIERS"
        ),
        "raw_extra_signatures": len(signatures),
        "isolated_constrained_response_signatures": isolated,
        "nonconstrained_product_signatures": len(product_pairs),
        "semantic_axis_family_count": len(SEMANTIC_AXIS5),
        "semantic_axis_state_count_including_empty": len(axis_states),
        "semantic_axis_nonempty_state_count": len(axis_states) - 1,
        "semantic_axis_states": [list(x) for x in axis_states],
        "commuting_modifier_families": list(COMMUTING4),
        "closed_form_signature_count": {
            "empty_axis_nonempty_modifiers": 15,
            "one_axis_any_modifiers": 80,
            "two_axis_up_to_three_modifiers": 60,
            "isolated_constrained_response": 1,
            "total": 156,
        },
        "numeric_format_carrier_word_budget": {
            "active15_less_than_global_bound": ACTIVE15_LESS_THAN_WORD_GLOBAL_BOUND,
            "max_placeholder_carrier_words": MAX_PUBLIC_PLACEHOLDERS,
            "max_highlight_carrier_words": MAX_PUBLIC_HIGHLIGHTS,
            "combined_bound": NEUTRAL_NUMERIC_CARRIER_BOUND,
            "minimum_public_less_than_threshold": MIN_PUBLIC_LESS_THAN_WORD_THRESHOLD,
            "remaining_margin": (
                MIN_PUBLIC_LESS_THAN_WORD_THRESHOLD
                - NEUTRAL_NUMERIC_CARRIER_BOUND
            ),
            "consequence": (
                "NUMERIC_PLACEHOLDER_AND_HIGHLIGHT_CARRIERS_CANNOT_BY_WORD_COUNT_"
                "ALONE_BREAK_ANY_PUBLIC_ACTIVE15_LESS_THAN_WORD_CONSTRAINT"
            ),
        },
        "next_load_bearing_semantic_obligations": [
            "PROVE_THE_9_NONEMPTY_SEMANTIC_AXIS_STATES_OVER_ACTIVE15_CONTEXT",
            "PROVE_LETTER_FREQUENCY_AS_A_SCALAR_COUNT_MODIFIER_WITH_EXACT_COLLISION_MINCUTS",
            "PROVE_NO_COMMA_AUTOMATIC_OFF_REPEAT_AND_VISIBLE_PREFIX_MINCUT_ON_REPEAT",
            "PROVE_NUMERIC_PLACEHOLDER_AND_HIGHLIGHT_INSERTION_PRESERVES_ALL_COMPATIBLE_EXACT_CHECKERS",
        ],
        "terminal_rows_used": False,
        "hidden_kwargs_used": False,
        "target_scores_used": False,
        "acceptance_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
