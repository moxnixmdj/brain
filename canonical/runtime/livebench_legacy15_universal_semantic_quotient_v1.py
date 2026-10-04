#!/usr/bin/env python3
"""Universal semantic-quotient proof object for frozen legacy LiveBench Active15.

This module closes the *scope* side of the pointwise-dominance route without
reading terminal rows.  The key observation is that the public generator's raw
slot cartesian product is not the semantic state space of the exact checkers.

The proof factors the generator into:
  * 928 conflict-compatible structural ID sets;
  * 192 exact reachable checker-relevant lexical signatures;
  * monotone boundary representatives for word/sentence thresholds;
  * finite exact domains for paragraph/bullet/section/nth/postscript/end slots;
  * one opaque repeat-target class, because the solver copies the visible target
    verbatim and repeat_prompt can co-exist only with existence/title in Active15.

The executable object deliberately grants zero acceptance credit by itself.
Independent content-bound verification must bind the pinned generator/checker
bytes and validate the interaction basis before governance may promote the
atomic LiveBench predicate.
"""
from __future__ import annotations

from typing import Any

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as arch
from canonical.runtime import livebench_legacy15_lexical_slot_quotient_v1 as lex

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_UNIVERSAL_SEMANTIC_QUOTIENT_V1"

PINNED = {
    "livebench_commit": "8f8e5c381a16e3f24257776edd53471fe86f8091",
    "instructions_blob": "4997bab885a676d92545fd91a9a20b48d234a2b2",
    "registry_blob": "903ed738398648c7cfac61d5ffa478c22f1f0891",
    "instructions_util_blob": "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b",
    "evaluation_main_blob": "4a341984936c4d609644a3b77f8c030ac5aa7269",
    "historical_generator_commit": "686be1e78a0ba8036d7e355bc406e1a265da5292",
    "historical_generator_blob": "6ff390d6885cf90f88d9d36959735cb327613edc",
}

# Exact build_description default domains in the pinned checker source.
SLOT_DOMAINS = {
    "length_constraints:number_paragraphs.num_paragraphs": tuple(range(1, 6)),
    "length_constraints:number_words.num_words": tuple(range(100, 501)),
    "length_constraints:number_words.relation": ("less than", "at least"),
    "length_constraints:number_sentences.num_sentences": tuple(range(1, 21)),
    "length_constraints:number_sentences.relation": ("less than", "at least"),
    "detectable_content:postscript.postscript_marker": ("P.S.", "P.P.S"),
    "detectable_format:number_bullet_lists.num_bullets": tuple(range(1, 6)),
    "detectable_format:multiple_sections.section_spliter": ("Section", "SECTION"),
    "detectable_format:multiple_sections.num_sections": tuple(range(1, 6)),
    "startend:end_checker.end_phrase": (
        "Any other questions?",
        "Is there anything else I can help with?",
    ),
}


def word_threshold_representative(num_words: int, relation: str) -> tuple[int, str]:
    """Map every public word threshold to the strongest boundary obligation."""
    n = int(num_words)
    r = str(relation)
    if not 100 <= n <= 500 or r not in {"less than", "at least"}:
        raise ValueError("OUTSIDE_PUBLIC_WORD_DOMAIN")
    # If a construction has <100 words, it has <n for every n>=100.
    # If it has >=500 words, it has >=n for every n<=500.
    return (100, "less than") if r == "less than" else (500, "at least")


def sentence_threshold_representative(
    num_sentences: int, relation: str
) -> tuple[int, str]:
    """Map every satisfiable public sentence threshold to its strongest boundary.

    The strict evaluator's nonempty-response gate makes <1 intrinsically
    impossible, so it remains its own exact UNSAT class.
    """
    n = int(num_sentences)
    r = str(relation)
    if not 1 <= n <= 20 or r not in {"less than", "at least"}:
        raise ValueError("OUTSIDE_PUBLIC_SENTENCE_DOMAIN")
    if r == "less than" and n == 1:
        return (1, "less than")
    # <2 is strongest among satisfiable less-than thresholds; >=20 is strongest
    # among at-least thresholds.
    return (2, "less than") if r == "less than" else (20, "at least")


def nth_numeric_domain() -> tuple[tuple[int, int], ...]:
    return tuple((p, k) for p in range(1, 6) for k in range(1, p + 1))


# Dependency closure for *cross-family checker truth under the current
# constructor*.  Families omitted from a dependency set are syntactically
# noninterfering under the pinned checkers and construction.
DEPENDENCIES = {
    "keywords:existence": frozenset({"keywords:forbidden_words"}),
    "keywords:forbidden_words": frozenset({
        "keywords:existence",
        "length_constraints:nth_paragraph_first_word",
        "detectable_format:multiple_sections",
        "startend:end_checker",
    }),
    "length_constraints:number_paragraphs": frozenset({
        "detectable_format:number_bullet_lists",
        "detectable_format:multiple_sections",
        "startend:quotation",
    }),
    "length_constraints:number_words": frozenset(arch.ACTIVE_IDS),
    "length_constraints:number_sentences": frozenset({
        "detectable_content:postscript",
        "startend:end_checker",
        "startend:quotation",
    }),
    "length_constraints:nth_paragraph_first_word": frozenset({
        "keywords:forbidden_words",
        "length_constraints:number_words",
        "length_constraints:number_sentences",
        "detectable_content:postscript",
        "startend:end_checker",
        "startend:quotation",
    }),
    "detectable_content:postscript": frozenset({
        "length_constraints:number_sentences",
        "startend:end_checker",
    }),
    "detectable_format:number_bullet_lists": frozenset({
        "length_constraints:number_paragraphs",
        "length_constraints:number_words",
        "startend:quotation",
    }),
    "detectable_format:title": frozenset({
        "combination:repeat_prompt",
        "combination:two_responses",
    }),
    "detectable_format:multiple_sections": frozenset({
        "keywords:forbidden_words",
        "length_constraints:number_paragraphs",
        "length_constraints:number_words",
        "length_constraints:number_sentences",
    }),
    "detectable_format:json_format": frozenset({
        "keywords:existence",
        "keywords:forbidden_words",
    }),
    "combination:repeat_prompt": frozenset({
        "keywords:existence",
        "detectable_format:title",
    }),
    "combination:two_responses": frozenset({
        "keywords:existence",
        "keywords:forbidden_words",
        "detectable_format:title",
    }),
    "startend:end_checker": frozenset({
        "keywords:forbidden_words",
        "length_constraints:number_sentences",
        "detectable_content:postscript",
        "startend:quotation",
    }),
    "startend:quotation": frozenset({
        "length_constraints:number_paragraphs",
        "length_constraints:number_words",
        "length_constraints:number_sentences",
        "length_constraints:nth_paragraph_first_word",
        "detectable_format:number_bullet_lists",
        "startend:end_checker",
    }),
}


def verify_repeat_target_quotient() -> dict[str, Any]:
    # Generator sets prompt_to_repeat to the visible prefix before the repeat
    # directive. Solver strips and copies that exact visible target first.
    # Pinned checker strips/lowercases and tests startswith(target.strip().lower()).
    # Therefore target *content* has one semantic class for RepeatPrompt itself.
    repeat_cohabitants = {
        iid
        for iid in arch.ACTIVE_IDS
        if iid != "combination:repeat_prompt"
        and arch.compatible(("combination:repeat_prompt", iid))
    }
    expected = {"keywords:existence", "detectable_format:title"}
    if repeat_cohabitants != expected:
        raise RuntimeError("REPEAT_COHABITANT_SCOPE_DRIFT")
    return {
        "opaque_repeat_target_classes": 1,
        "active15_repeat_cohabitants": sorted(repeat_cohabitants),
        "content_independence_reason": (
            "SOLVER_COPIES_VISIBLE_TARGET_VERBATIM_FIRST__PINNED_CHECKER_TESTS_"
            "CASE_INSENSITIVE_STRIPPED_STARTSWITH__ONLY_EXISTENCE_AND_TITLE_COHABIT"
        ),
    }


def verify_dependency_graph() -> None:
    active = set(arch.ACTIVE_IDS)
    if set(DEPENDENCIES) != active:
        raise RuntimeError("DEPENDENCY_KEY_SCOPE_DRIFT")
    for iid, deps in DEPENDENCIES.items():
        if not set(deps) <= active:
            raise RuntimeError("DEPENDENCY_OUTSIDE_ACTIVE15:" + iid)


def verify() -> dict[str, Any]:
    a = arch.verify()
    l = lex.verify()
    verify_dependency_graph()
    repeat = verify_repeat_target_quotient()

    if a["compatible_set_count"] != 928:
        raise RuntimeError("STRUCTURAL_QUOTIENT_DRIFT")
    if l["exact_reachable_signature_count"] != 192:
        raise RuntimeError("LEXICAL_QUOTIENT_DRIFT")
    if len(nth_numeric_domain()) != 15:
        raise RuntimeError("NTH_NUMERIC_DOMAIN_DRIFT")

    # Exhaustively validate the monotone maps over their exact public domains.
    word_reps = {
        word_threshold_representative(n, r)
        for r in ("less than", "at least")
        for n in range(100, 501)
    }
    sentence_reps = {
        sentence_threshold_representative(n, r)
        for r in ("less than", "at least")
        for n in range(1, 21)
    }
    if word_reps != {(100, "less than"), (500, "at least")}:
        raise RuntimeError("WORD_MONOTONE_REDUCTION_DRIFT")
    if sentence_reps != {
        (1, "less than"),
        (2, "less than"),
        (20, "at least"),
    }:
        raise RuntimeError("SENTENCE_MONOTONE_REDUCTION_DRIFT")

    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_UNIVERSAL_SCOPE_PROOF__INDEPENDENT_CONTENT_BOUND_VERIFICATION_REQUIRED",
        "pinned": PINNED,
        "structural_id_set_count": 928,
        "lexical_signature_count": 192,
        "word_threshold_raw_states": 802,
        "word_threshold_semantic_boundaries": [
            {"num_words": 100, "relation": "less than"},
            {"num_words": 500, "relation": "at least"},
        ],
        "sentence_threshold_raw_states": 40,
        "sentence_threshold_semantic_boundaries": [
            {"num_sentences": 1, "relation": "less than", "class": "PROVED_UNSAT"},
            {"num_sentences": 2, "relation": "less than", "class": "STRONGEST_SAT_BOUNDARY"},
            {"num_sentences": 20, "relation": "at least", "class": "STRONGEST_LOWER_BOUND"},
        ],
        "nth_numeric_state_count": 15,
        "paragraph_values": list(range(1, 6)),
        "bullet_values": list(range(1, 6)),
        "section_values": {
            "splitters": ["Section", "SECTION"],
            "counts": list(range(1, 6)),
        },
        "postscript_values": ["P.S.", "P.P.S"],
        "end_phrase_values": list(SLOT_DOMAINS["startend:end_checker.end_phrase"]),
        "repeat_target_reduction": repeat,
        "dependency_graph_closed_over_active15": True,
        "universal_proof_shape": [
            "EVERY_GENERATOR_OUTPUT_ACTIVE15_ID_SET_IS_UNIQUE_SIZE_LE_5_AND_CONFLICT_COMPATIBLE__THEREFORE_IN_928_SET_SUPERSET",
            "EVERY_KEYWORD_IDENTITY_INTERACTION_FACTORS_THROUGH_EXACT_192_REACHABLE_LEXICAL_SIGNATURES",
            "WORD_THRESHOLDS_COLLAPSE_BY_MONOTONICITY_TO_LT100_AND_GE500",
            "SENTENCE_THRESHOLDS_COLLAPSE_BY_MONOTONICITY_TO_LT2_AND_GE20_PLUS_EXACT_LT1_UNSAT",
            "ALL_REMAINING_GENERATED_ACTIVE15_SLOTS_HAVE_EXPLICIT_FINITE_DOMAINS",
            "REPEAT_TARGET_TEXT_IS_AN_OPAQUE_VISIBLE_PREFIX_COPIED_VERBATIM_AND_HAS_ONE_REPEAT_CHECKER_SEMANTIC_CLASS",
            "DEPENDENCY_CLOSED_INTERACTION_BASIS_IS_SUFFICIENT_TO_LIFT_EXACT_CHECKER_RESULTS_TO_ALL_GENERATOR_ADMITTED_ACTIVE15_TUPLES",
        ],
        "terminal_rows_used": False,
        "terminal_kwargs_used": False,
        "terminal_instruction_ids_used": False,
        "target_scores_used": False,
        "model_dependency_count": 0,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
        "next_required": (
            "INDEPENDENTLY_BIND_PINNED_GENERATOR_AND_CHECKER_BYTES_AND_VERIFY_"
            "EVERY_DEPENDENCY_CLOSED_EXTREMAL_INTERACTION_BASIS_CASE_WITH_EXACT_CHECKERS"
        ),
    }


def run(args=None, root=None):
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
