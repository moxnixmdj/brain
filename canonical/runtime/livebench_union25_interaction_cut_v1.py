#!/usr/bin/env python3
"""Exact structural interaction cut for the full pinned LiveBench registry25.

The verified public-scope theorem expanded the load-bearing proof target from
Active15 to the full 25-family pinned registry.  This module removes the false
impression that 14,559 structural identity sets require 14,559 unrelated proofs.

Every compatible registry25 set factors uniquely into:
    (new10 subset, inherited Active15 residual)

The new10 subset has only 157 reachable signatures.  The residual is itself an
Active15-compatible set and can therefore reuse the already verified Active15
constructor/pointwise machinery.  New reasoning can be organized by the 157
extension signatures rather than by the raw 14,559 identity sets.

No terminal rows, hidden kwargs, target scores, or comparator responses are
read.  This is a structural theorem only; it grants zero acceptance credit.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from typing import Any, Iterable

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_INTERACTION_CUT_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"

REGISTRY25 = (
    "keywords:existence",
    "keywords:frequency",
    "keywords:forbidden_words",
    "keywords:letter_frequency",
    "language:response_language",
    "length_constraints:number_sentences",
    "length_constraints:number_paragraphs",
    "length_constraints:number_words",
    "length_constraints:nth_paragraph_first_word",
    "detectable_content:number_placeholders",
    "detectable_content:postscript",
    "detectable_format:number_bullet_lists",
    "detectable_format:constrained_response",
    "detectable_format:number_highlighted_sections",
    "detectable_format:multiple_sections",
    "detectable_format:json_format",
    "detectable_format:title",
    "combination:two_responses",
    "combination:repeat_prompt",
    "startend:end_checker",
    "change_case:capital_word_frequency",
    "change_case:english_capital",
    "change_case:english_lowercase",
    "punctuation:no_comma",
    "startend:quotation",
)

ACTIVE15 = (
    "keywords:existence",
    "keywords:forbidden_words",
    "length_constraints:number_paragraphs",
    "length_constraints:number_words",
    "length_constraints:number_sentences",
    "length_constraints:nth_paragraph_first_word",
    "detectable_content:postscript",
    "detectable_format:number_bullet_lists",
    "detectable_format:title",
    "detectable_format:multiple_sections",
    "detectable_format:json_format",
    "combination:repeat_prompt",
    "combination:two_responses",
    "startend:end_checker",
    "startend:quotation",
)

NEW10 = tuple(x for x in REGISTRY25 if x not in set(ACTIVE15))
EXPECTED_NEW10 = (
    "keywords:frequency",
    "keywords:letter_frequency",
    "language:response_language",
    "detectable_content:number_placeholders",
    "detectable_format:constrained_response",
    "detectable_format:number_highlighted_sections",
    "change_case:capital_word_frequency",
    "change_case:english_capital",
    "change_case:english_lowercase",
    "punctuation:no_comma",
)

EXPECTED_CARDINALITY_COUNTS = {1: 25, 2: 203, 3: 1055, 4: 3750, 5: 9526}
EXPECTED_TOTAL = 14559
EXPECTED_ACTIVE15_ONLY = 928
EXPECTED_NEW_SIGNATURES = 157
EXPECTED_BY_NEW_COUNT = {0: 928, 1: 4317, 2: 5892, 3: 2906, 4: 495, 5: 21}
EXPECTED_PER_NEW_FAMILY = {
    "keywords:frequency": 3690,
    "keywords:letter_frequency": 3938,
    "language:response_language": 809,
    "detectable_content:number_placeholders": 3938,
    "detectable_format:constrained_response": 1,
    "detectable_format:number_highlighted_sections": 2858,
    "change_case:capital_word_frequency": 2738,
    "change_case:english_capital": 2490,
    "change_case:english_lowercase": 2490,
    "punctuation:no_comma": 3952,
}


def _raw_conflicts() -> dict[str, set[str]]:
    """Literal transcription of the pinned registry's conflict expressions."""
    all_ids = set(REGISTRY25)
    c = {x: {x} for x in REGISTRY25}

    c["language:response_language"].update({
        "language:response_language",
        "detectable_format:multiple_sections",
        "keywords:existence",
        "keywords:frequency",
        "keywords:forbidden_words",
        "startend:end_checker",
        "change_case:english_capital",
        "change_case:english_lowercase",
    })
    c["length_constraints:number_paragraphs"].update({
        "length_constraints:number_paragraphs",
        "length_constraints:nth_paragraph_first_word",
        "length_constraints:number_sentences",
    })
    c["length_constraints:nth_paragraph_first_word"].update({
        "length_constraints:nth_paragraph_first_word",
        "length_constraints:number_paragraphs",
        "detectable_format:number_bullet_lists",
        "detectable_format:number_highlighted_sections",
        "detectable_format:multiple_sections",
    })
    c["detectable_format:number_bullet_lists"].update({
        "detectable_format:number_bullet_lists",
        "length_constraints:nth_paragraph_first_word",
    })
    c["detectable_format:constrained_response"] = set(all_ids)
    c["detectable_format:number_highlighted_sections"].update({
        "detectable_format:number_highlighted_sections",
        "length_constraints:nth_paragraph_first_word",
    })
    c["detectable_format:multiple_sections"].update({
        "detectable_format:multiple_sections",
        "language:response_language",
        "detectable_format:number_highlighted_sections",
        "length_constraints:nth_paragraph_first_word",
    })
    c["detectable_format:json_format"] = all_ids.difference({
        "keywords:forbidden_words",
        "keywords:existence",
    })
    c["combination:two_responses"] = all_ids.difference({
        "keywords:forbidden_words",
        "keywords:existence",
        "language:response_language",
        "detectable_format:title",
        "punctuation:no_comma",
    })
    c["combination:repeat_prompt"] = all_ids.difference({
        "keywords:existence",
        "detectable_format:title",
        "punctuation:no_comma",
    })
    c["change_case:capital_word_frequency"].update({
        "change_case:capital_word_frequency",
        "change_case:english_lowercase",
        "change_case:english_capital",
    })
    c["change_case:english_lowercase"].update({
        "change_case:english_lowercase",
        "change_case:english_capital",
    })
    c["startend:quotation"].update({
        "startend:quotation",
        "detectable_format:title",
    })
    return c


def conflict_graph() -> dict[str, frozenset[str]]:
    """Apply the pinned registry conflict_make symmetrization exactly."""
    c = _raw_conflicts()
    for key in tuple(REGISTRY25):
        for other in tuple(c[key]):
            c[other].add(key)
        c[key].add(key)
    return {k: frozenset(v) for k, v in c.items()}


def compatible(ids: Iterable[str]) -> bool:
    xs = tuple(ids)
    if len(set(xs)) != len(xs):
        return False
    graph = conflict_graph()
    for i, a in enumerate(xs):
        if a not in graph:
            return False
        for b in xs[i + 1:]:
            if b in graph[a]:
                return False
    return True


def enumerate_compatible_sets() -> tuple[tuple[str, ...], ...]:
    out: list[tuple[str, ...]] = []
    for k in range(1, 6):
        for row in combinations(REGISTRY25, k):
            if compatible(row):
                out.append(row)
    return tuple(out)


def factor(row: Iterable[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return (new10 signature, inherited Active15 residual)."""
    xs = tuple(row)
    new = tuple(x for x in xs if x in set(NEW10))
    old = tuple(x for x in xs if x in set(ACTIVE15))
    if len(new) + len(old) != len(xs):
        raise AssertionError("UNPARTITIONED_REGISTRY_ID")
    return new, old


def signature_census() -> dict[tuple[str, ...], int]:
    counts: Counter[tuple[str, ...]] = Counter()
    for row in enumerate_compatible_sets():
        new, _ = factor(row)
        counts[new] += 1
    return dict(counts)


def allowed_active15_residuals_by_signature() -> dict[tuple[str, ...], tuple[tuple[str, ...], ...]]:
    out: dict[tuple[str, ...], list[tuple[str, ...]]] = defaultdict(list)
    for row in enumerate_compatible_sets():
        new, old = factor(row)
        out[new].append(old)
    return {k: tuple(v) for k, v in out.items()}


def verify() -> dict[str, Any]:
    if NEW10 != EXPECTED_NEW10:
        raise AssertionError("NEW10_IDENTITY_DRIFT:" + repr(NEW10))
    if set(ACTIVE15) & set(NEW10):
        raise AssertionError("ACTIVE15_NEW10_OVERLAP")
    if set(ACTIVE15) | set(NEW10) != set(REGISTRY25):
        raise AssertionError("REGISTRY25_PARTITION_FAILURE")

    rows = enumerate_compatible_sets()
    by_card = Counter(map(len, rows))
    if dict(sorted(by_card.items())) != EXPECTED_CARDINALITY_COUNTS:
        raise AssertionError("REGISTRY25_CARDINALITY_DRIFT:" + repr(by_card))
    if len(rows) != EXPECTED_TOTAL:
        raise AssertionError("REGISTRY25_TOTAL_DRIFT:" + str(len(rows)))

    sig_counts = signature_census()
    if len(sig_counts) != EXPECTED_NEW_SIGNATURES:
        raise AssertionError("NEW10_SIGNATURE_COUNT_DRIFT:" + str(len(sig_counts)))

    by_new_count = Counter()
    per_new_family = Counter()
    active15_only = 0
    max_new = 0

    for row in rows:
        new, old = factor(row)
        if not compatible(old):
            raise AssertionError("INHERITED_ACTIVE15_RESIDUAL_NOT_COMPATIBLE:" + repr(row))
        by_new_count[len(new)] += 1
        max_new = max(max_new, len(new))
        if not new:
            active15_only += 1
        for iid in new:
            per_new_family[iid] += 1

    if active15_only != EXPECTED_ACTIVE15_ONLY:
        raise AssertionError("ACTIVE15_ONLY_COUNT_DRIFT:" + str(active15_only))
    if dict(sorted(by_new_count.items())) != EXPECTED_BY_NEW_COUNT:
        raise AssertionError("NEW_FAMILY_CARDINALITY_DRIFT:" + repr(by_new_count))
    if dict(per_new_family) != EXPECTED_PER_NEW_FAMILY:
        raise AssertionError("PER_NEW_FAMILY_COUNT_DRIFT:" + repr(per_new_family))
    if max_new != 5:
        raise AssertionError("MAX_NEW_FAMILY_CARDINALITY_DRIFT:" + str(max_new))

    constrained = "detectable_format:constrained_response"
    constrained_rows = [row for row in rows if constrained in row]
    if constrained_rows != [(constrained,)]:
        raise AssertionError("CONSTRAINED_RESPONSE_NOT_STRUCTURALLY_ISOLATED")

    # The quotient is lossless at structural identity level: every raw row maps
    # to exactly one signature and one inherited residual, and concatenating the
    # two in registry order reconstructs the original set.
    reconstructed = 0
    order = {iid: i for i, iid in enumerate(REGISTRY25)}
    for row in rows:
        new, old = factor(row)
        rebuilt = tuple(sorted((*new, *old), key=order.__getitem__))
        if rebuilt != row:
            raise AssertionError("FACTORIZATION_NOT_LOSSLESS:" + repr((row, rebuilt)))
        reconstructed += 1
    if reconstructed != EXPECTED_TOTAL:
        raise AssertionError("FACTORIZATION_TOTALITY_FAILURE")

    top_signatures = sorted(
        (
            {
                "new10_signature": list(sig),
                "raw_structural_sets": count,
            }
            for sig, count in sig_counts.items()
        ),
        key=lambda x: (-x["raw_structural_sets"], x["new10_signature"]),
    )[:20]

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__REGISTRY25_14559_STRUCTURAL_SETS_FACTOR_LOSSLESSLY__"
            "157_NEW10_INTERACTION_SIGNATURES__928_ACTIVE15_ONLY__"
            "CONSTRAINED_RESPONSE_SINGLETON"
        ),
        "pinned_source": {
            "livebench_commit": PINNED_LIVEBENCH_COMMIT,
            "registry_blob": PINNED_REGISTRY_BLOB,
        },
        "registry25_family_count": len(REGISTRY25),
        "active15_family_count": len(ACTIVE15),
        "new10_family_count": len(NEW10),
        "new10_families": list(NEW10),
        "compatible_structural_sets_by_cardinality": dict(sorted(by_card.items())),
        "compatible_structural_set_total": len(rows),
        "active15_only_structural_sets": active15_only,
        "union25_extension_structural_sets": len(rows) - active15_only,
        "new10_reachable_interaction_signature_count": len(sig_counts),
        "raw_to_signature_compression_ratio": len(rows) / len(sig_counts),
        "raw_extension_to_signature_compression_ratio": (
            (len(rows) - active15_only) / (len(sig_counts) - 1)
        ),
        "sets_by_new_family_count": dict(sorted(by_new_count.items())),
        "per_new_family_structural_set_count": {
            iid: per_new_family[iid] for iid in NEW10
        },
        "max_simultaneously_reachable_new_families": max_new,
        "constrained_response": {
            "structural_set_count": len(constrained_rows),
            "only_reachable_set": list(constrained_rows[0]),
            "consequence": (
                "THIS_FAMILY_CAN_BE_PROVED_AND_CONSTRUCTED_IN_ISOLATION_AND_"
                "REMOVED_FROM_MULTI_CHECKER_INTERACTION_REASONING"
            ),
        },
        "factorization_theorem": (
            "EVERY_REGISTRY25_COMPATIBLE_SET_EQUALS_ONE_OF_157_REACHABLE_NEW10_"
            "SIGNATURES_PLUS_AN_INHERITED_ACTIVE15_COMPATIBLE_RESIDUAL"
        ),
        "top_signatures": top_signatures,
        "critical_path_consequence": (
            "STOP_TREATING_14559_IDENTITY_SETS_AS_INDEPENDENT_PROOF_BRANCHES__"
            "EXTEND_THE_VERIFIED_ACTIVE15_CONSTRUCTOR_BY_NEW10_SIGNATURE__"
            "BEGIN_WITH_STRUCTURALLY_ISOLATED_CONSTRAINED_RESPONSE"
        ),
        "terminal_rows_read": 0,
        "hidden_kwargs_read": 0,
        "target_scores_read": 0,
        "comparator_responses_read": 0,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
        "hard_nonclaims": [
            "THE_157_SIGNATURES_ARE_A_STRUCTURAL_NOT_YET_SEMANTIC_QUOTIENT",
            "UNION25_POINTWISE_OPTIMALITY_IS_NOT_YET_PROVED",
            "NO_LIVEBENCH_ACCEPTANCE_CREDIT_FROM_THIS_THEOREM_ALONE",
            "THE_TERMINAL_GOAL_REMAINS_UNPROVED",
        ],
    }


def run(args=None, root=None) -> dict[str, Any]:
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
