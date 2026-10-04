#!/usr/bin/env python3
"""Finite full-slot factorization candidate for frozen LiveBench legacy15.

This module attacks the remaining proof gap after the independently verified
12,489-case pointwise envelope: prove that the public-generator-admitted visible
slot domain factors through a finite checker-semantic basis instead of requiring
a raw Cartesian product.

It deliberately grants zero acceptance credit.  The result is a proof candidate
and reduced-basis compiler that must be replayed against the exact pinned
checkers by an independent runner.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import prod
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
from canonical.runtime import livebench_legacy15_contract_composer_v2 as composer
from canonical.runtime import livebench_legacy15_lexical_slot_quotient_v1 as lexical

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_FULL_SLOT_FACTORIZATION_V1"

PINNED_GENERATOR_COMMIT = "686be1e78a0ba8036d7e355bc406e1a265da5292"
PINNED_GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"
PINNED_CHECKER_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
PINNED_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"

EXPECTED_STRUCTURAL_SET_COUNT = 928
EXPECTED_LEXICAL_SIGNATURE_COUNT = 192
EXPECTED_REDUCED_BASIS_COUNT = 60495

# The public generator/checker domains.  Infinite/arbitrary text is absent here:
# repeat_prompt is separately proved to be one success-equivalence class.
PARAGRAPH_VALUES = tuple(range(1, 6))
WORD_CLASSES = (
    ("LT_BOUNDARY", 100, "less than"),
    ("GE_STRESS", 500, "at least"),
)
SENTENCE_CLASSES = (
    ("LT1_UNSAT", 1, "less than"),
    ("LT2_BOUNDARY", 2, "less than"),
    ("GE_STRESS", 20, "at least"),
)
NTH_LOCATIONS = tuple((p, k) for p in range(1, 6) for k in range(1, p + 1))
POSTSCRIPT_VALUES = ("P.S.", "P.P.S")
BULLET_VALUES = tuple(range(1, 6))
SECTION_VALUES = tuple(
    (splitter, n)
    for splitter in ("Section", "SECTION")
    for n in range(1, 6)
)
END_VALUES = (
    "Any other questions?",
    "Is there anything else I can help with?",
)

# Representative lexical values are public-generator members already bound by
# the exact lexical quotient.  They are deliberately disjoint.
EXISTENCE_REP = lexical.EXISTENCE_REPRESENTATIVE
FORBIDDEN_REP = lexical.GENERIC_FORBIDDEN_FILLERS

# Number of reduced representatives per active instruction when lexical identity
# is factored into the separate 192-state quotient.
REPRESENTATIVE_COUNTS = {
    composer.EXIST: 1,
    composer.FORBIDDEN: 1,
    composer.PARAGRAPHS: len(PARAGRAPH_VALUES),
    composer.WORDS: len(WORD_CLASSES),
    composer.SENTENCES: len(SENTENCE_CLASSES),
    composer.NTH: len(NTH_LOCATIONS),
    composer.POSTSCRIPT: len(POSTSCRIPT_VALUES),
    composer.BULLETS: len(BULLET_VALUES),
    composer.TITLE: 1,
    composer.SECTIONS: len(SECTION_VALUES),
    composer.JSON_ID: 1,
    composer.REPEAT: 1,
    composer.TWO: 1,
    composer.END: len(END_VALUES),
    composer.QUOTE: 1,
}

# Conservative maximum word-token contribution of each co-constraint to an
# unpadded WORDS construction.  The values intentionally overcount shared
# baseline tokens.  JSON/REPEAT/TWO are absent because the frozen conflict graph
# forbids them from coexisting with WORDS.
WORD_CONTRIBUTION_UPPER = {
    composer.EXIST: 1,       # five required words packed into one \w+ carrier
    composer.FORBIDDEN: 0,   # constraint only
    composer.PARAGRAPHS: 5,  # baseline plus at most four extra safe paragraphs
    composer.SENTENCES: 20,  # public maximum explicit sentence carriers
    composer.NTH: 6,         # target first word + baseline + four other paragraphs
    composer.POSTSCRIPT: 3,  # P.P.S
    composer.BULLETS: 5,
    composer.TITLE: 1,
    composer.SECTIONS: 15,   # three \w+ tokens per section, max five
    composer.END: 8,         # longer of the two frozen ending phrases
    composer.QUOTE: 0,
}


@dataclass(frozen=True)
class BasisChoice:
    instruction_id: str
    label: str
    slots: tuple[tuple[str, Any], ...]

    def contract(self) -> dict[str, Any]:
        return {
            "instruction_id": self.instruction_id,
            "slots": dict(self.slots),
        }


def _choice(iid: str, label: str, **slots: Any) -> BasisChoice:
    return BasisChoice(iid, label, tuple(sorted(slots.items())))


def choices_for(iid: str) -> tuple[BasisChoice, ...]:
    """Return the reduced nonlexical representative domain for one active ID."""
    if iid == composer.EXIST:
        return (_choice(iid, "LEXICAL_REP", keywords=list(EXISTENCE_REP)),)
    if iid == composer.FORBIDDEN:
        return (_choice(iid, "LEXICAL_REP", forbidden_words=list(FORBIDDEN_REP)),)
    if iid == composer.PARAGRAPHS:
        return tuple(_choice(iid, f"P{n}", num_paragraphs=n) for n in PARAGRAPH_VALUES)
    if iid == composer.WORDS:
        return tuple(
            _choice(iid, label, num_words=n, relation=relation)
            for label, n, relation in WORD_CLASSES
        )
    if iid == composer.SENTENCES:
        return tuple(
            _choice(iid, label, num_sentences=n, relation=relation)
            for label, n, relation in SENTENCE_CLASSES
        )
    if iid == composer.NTH:
        return tuple(
            _choice(
                iid,
                f"P{p}_K{k}",
                num_paragraphs=p,
                nth_paragraph=k,
                first_word=lexical.GENERIC_NTH_WORD,
            )
            for p, k in NTH_LOCATIONS
        )
    if iid == composer.POSTSCRIPT:
        return tuple(_choice(iid, marker, postscript_marker=marker) for marker in POSTSCRIPT_VALUES)
    if iid == composer.BULLETS:
        return tuple(_choice(iid, f"B{n}", num_bullets=n) for n in BULLET_VALUES)
    if iid == composer.TITLE:
        return (_choice(iid, "STATIC"),)
    if iid == composer.SECTIONS:
        return tuple(
            _choice(iid, f"{splitter}_{n}", section_spliter=splitter, num_sections=n)
            for splitter, n in SECTION_VALUES
        )
    if iid == composer.JSON_ID:
        return (_choice(iid, "STATIC"),)
    if iid == composer.REPEAT:
        return (_choice(iid, "TEXT_EQUIVALENCE_CLASS", prompt_to_repeat="Visible public request."),)
    if iid == composer.TWO:
        return (_choice(iid, "STATIC"),)
    if iid == composer.END:
        return tuple(_choice(iid, f"END_{i}", end_phrase=p) for i, p in enumerate(END_VALUES))
    if iid == composer.QUOTE:
        return (_choice(iid, "STATIC"),)
    raise ValueError("UNKNOWN_ACTIVE_ID:" + str(iid))


def reduced_basis_count() -> int:
    total = 0
    for ids in arch.enumerate_compatible_sets():
        total += prod(REPRESENTATIVE_COUNTS[iid] for iid in ids)
    return total


def iter_reduced_basis() -> Iterable[tuple[dict[str, Any], ...]]:
    """Enumerate the 60,495 structural/numeric/categorical representatives."""
    for ids in arch.enumerate_compatible_sets():
        domains = [choices_for(iid) for iid in ids]
        for row in product(*domains):
            yield tuple(choice.contract() for choice in row)


def word_less_than_global_upper_bound() -> dict[str, Any]:
    """Prove every unpadded compatible WORDS construction is below 100 words.

    The generator emits at most five active instructions.  For each compatible
    identity set containing WORDS, sum conservative per-checker contribution
    bounds.  This deliberately ignores cancellation and therefore remains an
    upper bound.  The maximum is still less than the public minimum threshold
    100, so every less-than threshold 100..500 belongs to one semantic class.
    """
    maxima: list[tuple[int, tuple[str, ...]]] = []
    forbidden_with_words = {
        composer.JSON_ID,
        composer.REPEAT,
        composer.TWO,
    }
    for ids in arch.enumerate_compatible_sets():
        if composer.WORDS not in ids:
            continue
        if any(iid in ids for iid in forbidden_with_words):
            raise RuntimeError("CONFLICT_GRAPH_WORD_ROUTE_DRIFT")
        bound = sum(WORD_CONTRIBUTION_UPPER.get(iid, 0) for iid in ids if iid != composer.WORDS)
        if bound == 0:
            bound = 1
        maxima.append((bound, ids))
    upper, witness_ids = max(maxima)
    if upper != 48:
        raise RuntimeError(f"WORD_UPPER_BOUND_DRIFT:{upper}:{witness_ids}")
    if upper >= 100:
        raise RuntimeError("WORD_LT_BOUNDARY_NOT_PROVED")
    return {
        "conservative_global_unpadded_word_upper_bound": upper,
        "public_minimum_less_than_threshold": 100,
        "margin": 100 - upper,
        "maximizing_compatible_id_set": list(witness_ids),
        "consequence": "ALL_LESS_THAN_THRESHOLDS_100_TO_500_COLLAPSE_TO_ONE_PASS_CLASS",
    }


def repeat_prompt_equivalence() -> dict[str, Any]:
    """Prove arbitrary repeat text is not a Cartesian proof dimension.

    In the frozen conflict graph, repeat_prompt can coexist only with existence
    and title from active15.  Composer V2 emits the stripped visible base as the
    first response bytes, then optional title/required-keyword material.  Hence
    every nonempty public generator prefix satisfies RepeatPromptThenAnswer and
    its textual identity cannot hurt any coexisting active checker.
    """
    repeat_sets = tuple(
        ids for ids in arch.enumerate_compatible_sets()
        if composer.REPEAT in ids
    )
    allowed = {composer.REPEAT, composer.EXIST, composer.TITLE}
    for ids in repeat_sets:
        if not set(ids) <= allowed:
            raise RuntimeError("REPEAT_CONFLICT_SCOPE_DRIFT:" + ",".join(ids))

    probes = (
        "Visible public request.",
        "Mixed CASE, punctuation?!\nSecond line.",
        "  Leading and trailing whitespace survive only semantically.  ",
    )
    checked = 0
    for ids in repeat_sets:
        for prompt in probes:
            contracts = []
            for iid in ids:
                if iid == composer.REPEAT:
                    contracts.append({
                        "instruction_id": iid,
                        "slots": {"prompt_to_repeat": prompt},
                    })
                elif iid == composer.EXIST:
                    contracts.append({
                        "instruction_id": iid,
                        "slots": {"keywords": list(EXISTENCE_REP)},
                    })
                elif iid == composer.TITLE:
                    contracts.append({"instruction_id": iid, "slots": {}})
                else:
                    raise RuntimeError("UNREACHABLE_REPEAT_COID")
            out = composer.compose_contracts(contracts)
            if out.get("status") != "CANDIDATE_WITNESS":
                raise RuntimeError("REPEAT_EQUIVALENCE_CONSTRUCTION_FAILURE:" + str(out))
            response = str(out["response"])
            base = prompt.strip()
            if not response.strip().casefold().startswith(base.casefold()):
                raise RuntimeError("REPEAT_PREFIX_INVARIANT_FAILURE")
            checked += 1
    return {
        "compatible_repeat_identity_sets": len(repeat_sets),
        "adversarial_text_probes": len(probes),
        "constructor_prefix_checks": checked,
        "coexisting_active_ids": sorted(allowed - {composer.REPEAT}),
        "consequence": "NONEMPTY_PROMPT_TO_REPEAT_TEXT_COLLAPSES_TO_ONE_SUCCESS_EQUIVALENCE_CLASS",
    }


def sentence_threshold_factorization() -> dict[str, Any]:
    """State the exact threshold quotient induced by Composer V2.

    less-than 1 is independently proved UNSAT under the strict nonempty gate.
    For n>=2 the constructor branch is byte-identical with respect to n, so n=2
    is the strongest threshold.  For at-least n the constructor emits n explicit
    sentence carriers; n ranges over the finite public 1..20 domain.

    Exact Punkt noninterference across wrapper variants remains an independent
    runner obligation; this function does not silently promote that obligation.
    """
    return {
        "public_thresholds": [1, 20],
        "less_than_classes": {
            "1": "INTRINSICALLY_UNSAT",
            "2_to_20": "SAME_CONSTRUCTOR_BRANCH__BOUNDARY_REPRESENTATIVE_2",
        },
        "at_least_class": "MONOTONE_EXPLICIT_N_SENTENCE_CONSTRUCTION__FINITE_N_1_TO_20",
        "independent_runner_obligation": (
            "BIND_LT2_AND_GE_N_NONINTERFERENCE_TO_EXACT_PINNED_PUNKT_ACROSS_"
            "POSTSCRIPT_END_QUOTE_AND_COMPATIBLE_STRUCTURAL_WRAPPERS"
        ),
    }


def verify() -> dict[str, Any]:
    structural = arch.verify()
    if structural["compatible_set_count"] != EXPECTED_STRUCTURAL_SET_COUNT:
        raise RuntimeError("STRUCTURAL_SET_COUNT_DRIFT")

    lex = lexical.verify()
    if lex["exact_reachable_signature_count"] != EXPECTED_LEXICAL_SIGNATURE_COUNT:
        raise RuntimeError("LEXICAL_SIGNATURE_COUNT_DRIFT")

    basis_count = reduced_basis_count()
    if basis_count != EXPECTED_REDUCED_BASIS_COUNT:
        raise RuntimeError("REDUCED_BASIS_COUNT_DRIFT:" + str(basis_count))

    for iid in arch.ACTIVE_IDS:
        got = len(choices_for(iid))
        expected = REPRESENTATIVE_COUNTS[iid]
        if got != expected:
            raise RuntimeError(f"REPRESENTATIVE_COUNT_DRIFT:{iid}:{got}:{expected}")

    word_bound = word_less_than_global_upper_bound()
    repeat = repeat_prompt_equivalence()
    sentence = sentence_threshold_factorization()

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__FULL_SLOT_FACTORIZATION_CANDIDATE__"
            "60495_REDUCED_NONLEXICAL_BASIS__192_EXACT_LEXICAL_SIGNATURES__"
            "INDEPENDENT_EXACT_CHECKER_REPLAY_REQUIRED"
        ),
        "source_binding": {
            "historical_generator_commit": PINNED_GENERATOR_COMMIT,
            "historical_generator_blob": PINNED_GENERATOR_BLOB,
            "checker_commit": PINNED_CHECKER_COMMIT,
            "instructions_blob": PINNED_INSTRUCTIONS_BLOB,
            "registry_blob": PINNED_REGISTRY_BLOB,
            "instructions_util_blob": PINNED_UTIL_BLOB,
        },
        "structural_identity_sets": EXPECTED_STRUCTURAL_SET_COUNT,
        "lexical_signature_count": EXPECTED_LEXICAL_SIGNATURE_COUNT,
        "reduced_structural_numeric_categorical_basis_count": basis_count,
        "representative_counts": dict(sorted(REPRESENTATIVE_COUNTS.items())),
        "word_threshold_factorization": {
            "less_than": word_bound,
            "at_least": {
                "public_threshold_domain": [100, 500],
                "constructor_rule": (
                    "PAD_WITH_FORBIDDEN_SAFE_ALPHANUMERIC_TOKENS_UNTIL_THRESHOLD_"
                    "THEN_APPLY_ONLY_MONOTONE_OR_WORD_NEUTRAL_WRAPPERS_AND_FINAL_EXACT_GUARD"
                ),
            },
        },
        "sentence_threshold_factorization": sentence,
        "repeat_prompt_text_factorization": repeat,
        "lexical_factorization": {
            "exact_reachable_signatures": EXPECTED_LEXICAL_SIGNATURE_COUNT,
            "forced_literal_collision_dimensions": [
                "NTH_FIRST_WORD_IN_FORBIDDEN_SET",
                "END_PHRASE_WHOLE_WORDS_IN_FORBIDDEN_SET",
            ],
            "existence_identity_removed_by_word_character_shield": True,
            "section_literal_boundary_destroyed_by_numeric_prefix": True,
            "postscript_p_or_s_word_list_collision": False,
        },
        "remaining_independent_obligations": [
            "EXACTLY_POSTVALIDATE_THE_REDUCED_BASIS_OR_AN_EQUIVALENT_SMALLER_CERTIFICATE_AGAINST_PINNED_CHECKERS",
            "VERIFY_THE_192_LEXICAL_SIGNATURES_COMPOSE_WITH_THE_REDUCED_NONLEXICAL_BASIS_WITHOUT_A_NEW_INTERACTION_CLASS",
            "BIND_SENTENCE_THRESHOLD_NONINTERFERENCE_TO_EXACT_PINNED_PUNKT_WRAPPER_SEMANTICS",
            "BIND_ACCEPTED_LIVEBENCH_PREDICATE_SCOPE_TO_THE_FROZEN_ACTIVE15_SCORER_SURFACE",
        ],
        "terminal_rows_used": False,
        "terminal_kwargs_used": False,
        "terminal_frequencies_used": False,
        "target_scores_used": False,
        "fresh_reality_used": False,
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
