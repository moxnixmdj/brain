from canonical.runtime import livebench_legacy15_semantic_factorization_v1 as proof


def test_projection_counts_match_independent_envelope_axes():
    assert proof._projection_counts() == {
        "structural_identity_sets": 928,
        "lexical_collision_signatures": 192,
        "word_threshold_relation_states": 802,
        "sentence_threshold_relation_states": 40,
        "paragraph_bullet_section_states": 250,
        "nth_postscript_end_states": 60,
    }


def test_word_upper_bound_dominates_public_less_than_domain():
    facts = proof._word_bound_facts()
    assert facts["conservative_unpadded_general_word_upper_bound"] == 63
    assert facts["public_minimum_word_threshold"] == 100
    assert facts["strict_margin"] == 37


def test_special_branches_are_numeric_general_isolated():
    facts = proof._verify_special_branch_locality()
    assert facts["compatible_set_count"] == 928
    assert facts["special_numeric_general_cross_count"] == 0
    assert facts["repeat_forbidden_cross_count"] == 0


def test_sentence_kernel_is_finite_and_explicit():
    kernel = proof.sentence_kernel_spec()
    assert kernel["independent_verifier_must_exhaust_all_thresholds"] == 40
    assert len(kernel["postscript_states"]) == 3
    assert len(kernel["end_states"]) == 3
    assert len(kernel["quote_states"]) == 2
    assert len(kernel["carrier_classes"]) == 2
    assert len(kernel["word_padding_states"]) == 2
