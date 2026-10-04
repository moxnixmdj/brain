from fractions import Fraction

from canonical.runtime.livebench_generator_support_threshold_route_falsifier_v2 import (
    COUNTEREXAMPLE_IDS,
    REACHABLE_COLLISION_WORD,
    TARGET_PREDICATE_FLOOR,
    verify,
)


def test_generator_support_universal_threshold_route_is_falsified():
    out = verify()
    assert out["status"] == "PASS__GENERATOR_SUPPORT_UNIVERSAL_THRESHOLD_ROUTE_FALSIFIED"
    assert tuple(out["counterexample_instruction_ids"]) == COUNTEREXAMPLE_IDS
    assert out["counterexample_word"] == REACHABLE_COLLISION_WORD == "rock"
    assert out["counterexample_hard_unsat_reason"] == "NTH_FIRST_WORD_IS_FORBIDDEN_WORD"
    assert out["maximum_counterexample_score"] == "1/4"
    assert TARGET_PREDICATE_FLOOR == Fraction(657, 1000)
    assert Fraction(1, 4) < TARGET_PREDICATE_FLOOR


def test_counterexample_is_bound_to_public_generator_support_not_illustrative_alpha():
    out = verify()
    reach = out["public_support_reachability"]
    assert reach["word_is_in_pinned_word_list"] is True
    assert reach["lexical_slots_share_generate_keywords_word_list"] is True
    assert reach["instruction_pair_is_conflict_compatible"] is True
    repair = out["truth_repair"]
    assert repair["prior_illustrative_word"] == "alpha"
    assert repair["prior_illustrative_word_is_in_pinned_word_list"] is False
    assert repair["replacement_generator_reachable_word"] == "rock"


def test_acceptance_consequence_is_population_specific_not_support_universal():
    out = verify()
    assert "A_UNIVERSAL_PER_ROW_GENERATOR_SUPPORT_FLOOR_CANNOT_PROVE_LIVEBENCH_IF_GE_65_7" in out["deduction"]
    assert len(out["corrected_acceptance_routes"]) == 2
    assert out["terminal_row_content_read"] is False
    assert out["terminal_row_metadata_read"] is False
    assert out["terminal_case_frequency_inferred"] is False
    assert out["acceptance_credit"] is False
