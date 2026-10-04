from canonical.runtime import livebench_public_scope_union_v1 as s


def _historical_generator_source():
    return """
def add_instructions_to_registry(no_of_instructions_to_add, max_instructions=5):
    length_constraints=[
        "length_constraints:number_sentences",
        "length_constraints:number_paragraphs",
        "length_constraints:number_words",
        "length_constraints:nth_paragraph_first_word",
    ]
    keyword_constraints=[
        "keywords:existence",
        "keywords:frequency",
        "keywords:forbidden_words",
        "keywords:letter_frequency",
    ]
    content_constraints=[
        "detectable_content:number_placeholders",
        "detectable_content:postscript",
    ]
    format_constraints=[
        "detectable_format:number_bullet_lists",
        "detectable_format:constrained_response",
        "detectable_format:number_highlighted_sections",
        "detectable_format:multiple_sections",
        "detectable_format:json_format",
        "detectable_format:title",
    ]
    combinations_constraints=[
        "combination:two_responses",
        "combination:repeat_prompt",
    ]
    startend_constraints=[
        "startend:end_checker",
        "startend:quotation",
    ]
    changecase_constraints=[
        "change_case:capital_word_frequency",
        "change_case:english_capital",
        "change_case:english_lowercase",
    ]
    punctuation_constraints=["punctuation:no_comma"]

    all_constraints = (
        length_constraints
        + keyword_constraints
        + content_constraints
        + format_constraints
        + combinations_constraints
        + startend_constraints
        + changecase_constraints
        + punctuation_constraints
    )
    return all_constraints
"""


def test_extracts_exact_historical_24_family_generator_universe():
    got = s.extract_constraint_universe(_historical_generator_source())
    assert len(got) == 24
    assert len(set(got)) == 24
    assert set(got) == set(s.HISTORICAL_GENERATOR_24)


def test_scope_lattice_is_15_strict_subset_24_strict_subset_25():
    out = s.analyze_source(_historical_generator_source())
    assert out["status"] == "PASS__PUBLIC_SCOPE_LATTICE_15_LT_24_LT_25"
    assert out["active15_count"] == 15
    assert out["historical_generator_count"] == 24
    assert out["public_union_count"] == 25
    assert out["active15_strict_subset_of_generator24"] is True
    assert out["generator24_strict_subset_of_public_union25"] is True
    assert out["public_union25_minus_generator24"] == ["language:response_language"]


def test_active15_omits_exactly_nine_historical_generator_families():
    out = s.analyze_source(_historical_generator_source())
    assert out["generator24_minus_active15"] == [
        "change_case:capital_word_frequency",
        "change_case:english_capital",
        "change_case:english_lowercase",
        "detectable_content:number_placeholders",
        "detectable_format:constrained_response",
        "detectable_format:number_highlighted_sections",
        "keywords:frequency",
        "keywords:letter_frequency",
        "punctuation:no_comma",
    ]


def test_public_union_is_ambiguity_free_scope_superset():
    out = s.analyze_source(_historical_generator_source())
    assert out["ambiguity_free_proof_target"] == "PUBLIC_TABLE4_UNION_25"
    assert out["subsumption_theorem"] == (
        "POINTWISE_OPTIMALITY_OVER_PUBLIC_UNION25_IMPLIES_POINTWISE_OPTIMALITY_"
        "OVER_ACTIVE15_AND_OVER_EVERY_SUBSET_OF_TABLE4_25_AND_OVER_EVERY_"
        "HISTORICAL_GENERATOR24_OUTPUT"
    )
    assert out["terminal_data_used"] is False
    assert out["acceptance_credit"] is False
