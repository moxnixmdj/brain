import pytest

from canonical.runtime.livebench_legacy_single_checker_witness_v1 import (
    WitnessError,
    synthesize,
)


CASES = [
    ("keywords:existence", {"keywords": ["cedar", "river"]}),
    ("keywords:frequency", {"keyword": "cedar", "frequency": 3, "relation": "at least"}),
    ("keywords:forbidden_words", {"forbidden_words": ["cedar", "river"]}),
    ("keywords:letter_frequency", {"letter": "q", "let_frequency": 3, "let_relation": "at least"}),
    ("language:response_language", {"language": "en"}),
    ("length_constraints:number_sentences", {"num_sentences": 3, "relation": "at least"}),
    ("length_constraints:number_paragraphs", {"num_paragraphs": 3}),
    ("length_constraints:number_words", {"num_words": 6, "relation": "at least"}),
    ("length_constraints:nth_paragraph_first_word", {"num_paragraphs": 3, "nth_paragraph": 2, "first_word": "cedar"}),
    ("detectable_content:number_placeholders", {"num_placeholders": 3}),
    ("detectable_content:postscript", {"postscript_marker": "P.S."}),
    ("detectable_format:number_bullet_lists", {"num_bullets": 3}),
    ("detectable_format:constrained_response", {}),
    ("detectable_format:number_highlighted_sections", {"num_highlights": 3}),
    ("detectable_format:multiple_sections", {"num_sections": 3, "section_spliter": "Section"}),
    ("detectable_format:json_format", {}),
    ("detectable_format:title", {}),
    ("combination:two_responses", {}),
    ("combination:repeat_prompt", {"prompt_to_repeat": "Explain cedar trees."}),
    ("startend:end_checker", {"end_phrase": "Any other questions?"}),
    ("change_case:capital_word_frequency", {"capital_frequency": 3, "capital_relation": "at least"}),
    ("change_case:english_capital", {}),
    ("change_case:english_lowercase", {}),
    ("punctuation:no_comma", {}),
    ("startend:quotation", {}),
]


@pytest.mark.parametrize("iid,slots", CASES)
def test_all_25_registered_legacy_families_have_nonempty_candidate(iid, slots):
    out = synthesize(iid, slots)
    assert out["status"] == "CANDIDATE_WITNESS_PENDING_EXACT_CHECKER_VERIFICATION"
    assert out["response"].strip()
    assert out["hidden_kwargs_used"] is False
    assert out["terminal_data_used"] is False


def test_less_than_word_count_uses_n_minus_one():
    out = synthesize("length_constraints:number_words", {"num_words": 4, "relation": "less than"})
    assert len(out["response"].split()) == 3


def test_unsatisfiable_strict_zero_fails_closed():
    with pytest.raises(WitnessError):
        synthesize("keywords:frequency", {"keyword": "x", "frequency": 0, "relation": "less than"})


def test_unknown_family_fails_closed():
    with pytest.raises(WitnessError):
        synthesize("not:a_checker", {})
