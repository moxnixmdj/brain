#!/usr/bin/env python3
"""Exact finite composition partition for the frozen active legacy-15 LiveBench surface.

This is a source/commitment-derived structural reducer only. It uses:
- the exact 15 active instruction identities opened from the pre-existing frozen
  terminal-set commitment; and
- the pinned legacy IFEval INSTRUCTION_CONFLICTS semantics.

It reads no terminal prompt, kwargs, response, case id, frequency, combination,
or score. The theorem is finite: every conflict-valid subset of the 15 active
identities is contained in at least one of nine maximal independent sets.
"""
from __future__ import annotations

from itertools import combinations
from typing import Iterable

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_COMPOSITION_PARTITION_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
ACTIVE_SET_COMMITMENT = "af4eeddebf27394eb689d2049f2f8104ae081ebafe237258bdc1a992e96f598d"

ACTIVE_IDS = frozenset({
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
})

# Symmetric conflict edges induced by the pinned public registry, projected onto
# the exact active-15 identity set. Self-conflicts are irrelevant for set-valued
# composition because one identity occurs at most once in the recovered legacy
# generator family; multiplicity handling is a separate verifier concern.
_CONFLICT_PAIRS = {
    frozenset(("length_constraints:number_paragraphs", "length_constraints:nth_paragraph_first_word")),
    frozenset(("length_constraints:number_paragraphs", "length_constraints:number_sentences")),
    frozenset(("length_constraints:nth_paragraph_first_word", "detectable_format:number_bullet_lists")),
    frozenset(("length_constraints:nth_paragraph_first_word", "detectable_format:multiple_sections")),
    frozenset(("detectable_format:title", "startend:quotation")),
}

# Registry-wide exclusions for three special operators.
for _iid in ACTIVE_IDS - {
    "detectable_format:json_format",
    "keywords:existence",
    "keywords:forbidden_words",
}:
    _CONFLICT_PAIRS.add(frozenset(("detectable_format:json_format", _iid)))

for _iid in ACTIVE_IDS - {
    "combination:two_responses",
    "keywords:existence",
    "keywords:forbidden_words",
    "detectable_format:title",
}:
    _CONFLICT_PAIRS.add(frozenset(("combination:two_responses", _iid)))

for _iid in ACTIVE_IDS - {
    "combination:repeat_prompt",
    "keywords:existence",
    "detectable_format:title",
}:
    _CONFLICT_PAIRS.add(frozenset(("combination:repeat_prompt", _iid)))

MAXIMAL_MODES = (
    frozenset({
        "detectable_format:json_format",
        "keywords:existence",
        "keywords:forbidden_words",
    }),
    frozenset({
        "combination:repeat_prompt",
        "detectable_format:title",
        "keywords:existence",
    }),
    frozenset({
        "combination:two_responses",
        "detectable_format:title",
        "keywords:existence",
        "keywords:forbidden_words",
    }),
    frozenset({
        "detectable_content:postscript",
        "detectable_format:title",
        "keywords:existence",
        "keywords:forbidden_words",
        "length_constraints:nth_paragraph_first_word",
        "length_constraints:number_sentences",
        "length_constraints:number_words",
        "startend:end_checker",
    }),
    frozenset({
        "detectable_content:postscript",
        "keywords:existence",
        "keywords:forbidden_words",
        "length_constraints:nth_paragraph_first_word",
        "length_constraints:number_sentences",
        "length_constraints:number_words",
        "startend:end_checker",
        "startend:quotation",
    }),
    frozenset({
        "detectable_content:postscript",
        "detectable_format:multiple_sections",
        "detectable_format:number_bullet_lists",
        "detectable_format:title",
        "keywords:existence",
        "keywords:forbidden_words",
        "length_constraints:number_paragraphs",
        "length_constraints:number_words",
        "startend:end_checker",
    }),
    frozenset({
        "detectable_content:postscript",
        "detectable_format:multiple_sections",
        "detectable_format:number_bullet_lists",
        "keywords:existence",
        "keywords:forbidden_words",
        "length_constraints:number_paragraphs",
        "length_constraints:number_words",
        "startend:end_checker",
        "startend:quotation",
    }),
    frozenset({
        "detectable_content:postscript",
        "detectable_format:multiple_sections",
        "detectable_format:number_bullet_lists",
        "detectable_format:title",
        "keywords:existence",
        "keywords:forbidden_words",
        "length_constraints:number_sentences",
        "length_constraints:number_words",
        "startend:end_checker",
    }),
    frozenset({
        "detectable_content:postscript",
        "detectable_format:multiple_sections",
        "detectable_format:number_bullet_lists",
        "keywords:existence",
        "keywords:forbidden_words",
        "length_constraints:number_sentences",
        "length_constraints:number_words",
        "startend:end_checker",
        "startend:quotation",
    }),
)


def is_valid(ids: Iterable[str]) -> bool:
    s = frozenset(ids)
    if not s <= ACTIVE_IDS:
        return False
    return not any(pair <= s for pair in _CONFLICT_PAIRS)


def covering_modes(ids: Iterable[str]) -> tuple[int, ...]:
    s = frozenset(ids)
    if not is_valid(s):
        return ()
    return tuple(i for i, mode in enumerate(MAXIMAL_MODES) if s <= mode)


def classify(ids: Iterable[str]) -> dict:
    s = frozenset(ids)
    covers = covering_modes(s)
    return {
        "schema": SCHEMA,
        "status": "PASS" if covers else "FAIL_CLOSED",
        "instruction_ids": sorted(s),
        "covering_mode_indices": list(covers),
        "minimum_covering_mode_index": covers[0] if covers else None,
        "active_identity_count": len(ACTIVE_IDS),
        "maximal_mode_count": len(MAXIMAL_MODES),
        "maximum_simultaneous_family_count": max(map(len, MAXIMAL_MODES)),
        "terminal_data_used": False,
        "model_dependency_count": 0,
    }


def prove_exhaustive_partition() -> dict:
    ordered = sorted(ACTIVE_IDS)
    valid = invalid = uncovered = 0
    max_valid_size = 0
    for r in range(len(ordered) + 1):
        for subset in combinations(ordered, r):
            if is_valid(subset):
                valid += 1
                max_valid_size = max(max_valid_size, r)
                if not covering_modes(subset):
                    uncovered += 1
            else:
                invalid += 1
    if uncovered:
        raise RuntimeError(f"UNcovered_valid_subsets:{uncovered}")
    if len(MAXIMAL_MODES) != 9:
        raise RuntimeError("MAXIMAL_MODE_COUNT_DRIFT")
    if max_valid_size != 9:
        raise RuntimeError("MAX_VALID_SIZE_DRIFT")
    # Maximality: no mode is a strict subset of another valid mode and every
    # one-element extension by an active id is conflict-invalid.
    for i, mode in enumerate(MAXIMAL_MODES):
        if not is_valid(mode):
            raise RuntimeError(f"MODE_{i}_INVALID")
        for j, other in enumerate(MAXIMAL_MODES):
            if i != j and mode < other:
                raise RuntimeError(f"MODE_{i}_NOT_MAXIMAL")
        for iid in ACTIVE_IDS - mode:
            if is_valid(mode | {iid}):
                raise RuntimeError(f"MODE_{i}_EXTENDABLE_BY:{iid}")
    return {
        "schema": SCHEMA,
        "status": "PASS__EXHAUSTIVE_32768_SUBSET_PARTITION",
        "active_identity_count": len(ACTIVE_IDS),
        "all_subsets": 2 ** len(ACTIVE_IDS),
        "valid_subsets": valid,
        "invalid_subsets": invalid,
        "uncovered_valid_subsets": uncovered,
        "maximal_mode_count": len(MAXIMAL_MODES),
        "maximum_simultaneous_family_count": max_valid_size,
        "terminal_data_used": False,
        "terminal_case_frequency_inferred": False,
        "terminal_case_combination_inferred": False,
        "acceptance_credit": False,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(prove_exhaustive_partition(), indent=2, sort_keys=True))
