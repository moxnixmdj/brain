from fractions import Fraction

from canonical.runtime.livebench_generator_support_threshold_route_falsifier_v2 import (
    COLLISION_WORD,
    COUNTEREXAMPLE_IDS,
    MANDATORY_END_PHRASE,
    REACHABLE_FORBIDDEN_WORDS,
    TARGET_PREDICATE_FLOOR,
    verify,
)


def test_generator_support_universal_threshold_route_is_falsified():
    out = verify()
    assert out["status"] == "PASS__GENERATOR_SUPPORT_UNIVERSAL_THRESHOLD_ROUTE_FALSIFIED"
    assert tuple(out["counterexample_instruction_ids"]) == COUNTEREXAMPLE_IDS
    assert out["collision_word"] == COLLISION_WORD == "help"
    assert out["mandatory_end_phrase"] == MANDATORY_END_PHRASE
    assert tuple(out["counterexample_forbidden_words"]) == REACHABLE_FORBIDDEN_WORDS
    assert out["counterexample_forbidden_word_count"] == 5
    assert len(REACHABLE_FORBIDDEN_WORDS) == len(set(REACHABLE_FORBIDDEN_WORDS)) == 5
    assert "help" in REACHABLE_FORBIDDEN_WORDS
    assert out["counterexample_hard_unsat_reason"] == (
        "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:help"
    )
    assert out["maximum_counterexample_score"] == "1/4"
    assert TARGET_PREDICATE_FLOOR == Fraction(657, 1000)
    assert Fraction(1, 4) < TARGET_PREDICATE_FLOOR


def test_counterexample_is_generator_admitted_and_minimal():
    out = verify()
    reach = out["public_support_reachability"]
    assert reach["all_counterexample_forbidden_words_are_in_pinned_word_list"] is True
    assert reach["forbidden_default_keyword_count"] == 5
    assert reach["mandatory_end_phrase_is_in_pinned_ending_options"] is True
    assert reach["instruction_pair_is_conflict_compatible"] is True
    reduction = out["proof_reduction"]
    assert reduction["superseded_nth_paragraph_witness"] is True
    assert reduction["reason"] == "END_FORBIDDEN_REQUIRES_FEWER_GENERATOR_SLOT_PREMISES"


def test_acceptance_consequence_is_population_specific_not_support_universal():
    out = verify()
    assert "A_UNIVERSAL_PER_ROW_GENERATOR_SUPPORT_FLOOR_CANNOT_PROVE_LIVEBENCH_IF_GE_65_7" in out["deduction"]
    assert len(out["corrected_acceptance_routes"]) == 2
    assert out["terminal_row_content_read"] is False
    assert out["terminal_row_metadata_read"] is False
    assert out["terminal_case_frequency_inferred"] is False
    assert out["acceptance_credit"] is False
