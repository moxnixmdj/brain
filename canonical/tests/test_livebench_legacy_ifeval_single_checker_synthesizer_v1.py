from canonical.runtime.livebench_legacy_ifeval_single_checker_synthesizer_v1 import (
    ALL_INSTRUCTION_IDS,
    synthesize_single,
)


CASES = {
    "keywords:existence": {"keywords": ["alpha", "beta"]},
    "keywords:frequency": {"keyword": "alpha", "frequency": 3, "relation": "at least"},
    "keywords:forbidden_words": {"forbidden_words": ["alpha", "beta"]},
    "keywords:letter_frequency": {"letter": "q", "let_frequency": 5, "let_relation": "at least"},
    "language:response_language": {"language": "en"},
    "length_constraints:number_sentences": {"num_sentences": 3, "relation": "at least"},
    "length_constraints:number_paragraphs": {"num_paragraphs": 3},
    "length_constraints:number_words": {"num_words": 100, "relation": "less than"},
    "length_constraints:nth_paragraph_first_word": {
        "num_paragraphs": 3,
        "nth_paragraph": 2,
        "first_word": "alpha",
    },
    "detectable_content:number_placeholders": {"num_placeholders": 3},
    "detectable_content:postscript": {"postscript_marker": "P.S."},
    "detectable_format:number_bullet_lists": {"num_bullets": 3},
    "detectable_format:constrained_response": {},
    "detectable_format:number_highlighted_sections": {"num_highlights": 3},
    "detectable_format:multiple_sections": {"section_spliter": "Section", "num_sections": 3},
    "detectable_format:json_format": {},
    "detectable_format:title": {},
    "combination:two_responses": {},
    "combination:repeat_prompt": {"prompt_to_repeat": "Repeat this exact request."},
    "startend:end_checker": {"end_phrase": "Any other questions?"},
    "change_case:capital_word_frequency": {
        "capital_frequency": 3,
        "capital_relation": "at least",
    },
    "change_case:english_capital": {},
    "change_case:english_lowercase": {},
    "punctuation:no_comma": {},
    "startend:quotation": {},
}


def test_registry_surface_is_exactly_25():
    assert len(ALL_INSTRUCTION_IDS) == 25
    assert set(ALL_INSTRUCTION_IDS) == set(CASES)


def test_every_checker_has_a_nonempty_candidate_on_representative_generator_domain():
    for instruction_id in ALL_INSTRUCTION_IDS:
        out = synthesize_single(instruction_id, CASES[instruction_id])
        assert out["status"] == "CANDIDATE_SINGLE_CHECKER_WITNESS", (instruction_id, out)
        assert out["response"].strip()
        assert out["semantic_task_content_required"] is False
        assert out["model_dependency_count"] == 0
        assert out["incremental_spend_usd"] == 0


def test_relational_boundary_constructors_fail_closed_on_unproved_or_impossible_cases():
    impossible = [
        ("keywords:frequency", {"keyword": "alpha", "frequency": 0, "relation": "less than"}),
        ("keywords:letter_frequency", {"letter": "a", "let_frequency": 0, "let_relation": "less than"}),
        ("length_constraints:number_sentences", {"num_sentences": 1, "relation": "less than"}),
        ("length_constraints:number_words", {"num_words": 0, "relation": "less than"}),
        ("change_case:capital_word_frequency", {"capital_frequency": 0, "capital_relation": "less than"}),
    ]
    for instruction_id, kwargs in impossible:
        out = synthesize_single(instruction_id, kwargs)
        assert out["status"] == "FAIL_CLOSED", (instruction_id, out)


def test_parameterized_easy_domains_construct_without_semantic_task_content():
    # These ranges are the public generator domains hard-coded by the pinned
    # legacy IFEval implementation.
    for n in range(1, 4):
        assert synthesize_single(
            "keywords:frequency",
            {"keyword": "alpha", "frequency": n, "relation": "at least"},
        )["status"] == "CANDIDATE_SINGLE_CHECKER_WITNESS"
        assert synthesize_single(
            "keywords:frequency",
            {"keyword": "alpha", "frequency": n, "relation": "less than"},
        )["status"] == "CANDIDATE_SINGLE_CHECKER_WITNESS"

    for n in range(1, 11):
        assert synthesize_single(
            "keywords:letter_frequency",
            {"letter": "q", "let_frequency": n, "let_relation": "at least"},
        )["status"] == "CANDIDATE_SINGLE_CHECKER_WITNESS"
        assert synthesize_single(
            "keywords:letter_frequency",
            {"letter": "q", "let_frequency": n, "let_relation": "less than"},
        )["status"] == "CANDIDATE_SINGLE_CHECKER_WITNESS"

    for n in range(1, 21):
        assert synthesize_single(
            "length_constraints:number_sentences",
            {"num_sentences": n, "relation": "at least"},
        )["status"] == "CANDIDATE_SINGLE_CHECKER_WITNESS"
        if n > 1:
            assert synthesize_single(
                "length_constraints:number_sentences",
                {"num_sentences": n, "relation": "less than"},
            )["status"] == "CANDIDATE_SINGLE_CHECKER_WITNESS"

    for n in range(1, 6):
        assert synthesize_single(
            "length_constraints:number_paragraphs",
            {"num_paragraphs": n},
        )["status"] == "CANDIDATE_SINGLE_CHECKER_WITNESS"
        assert synthesize_single(
            "detectable_format:number_bullet_lists",
            {"num_bullets": n},
        )["status"] == "CANDIDATE_SINGLE_CHECKER_WITNESS"
        assert synthesize_single(
            "detectable_format:multiple_sections",
            {"section_spliter": "Section", "num_sections": n},
        )["status"] == "CANDIDATE_SINGLE_CHECKER_WITNESS"

    for n in range(1, 5):
        assert synthesize_single(
            "detectable_content:number_placeholders",
            {"num_placeholders": n},
        )["status"] == "CANDIDATE_SINGLE_CHECKER_WITNESS"
        assert synthesize_single(
            "detectable_format:number_highlighted_sections",
            {"num_highlights": n},
        )["status"] == "CANDIDATE_SINGLE_CHECKER_WITNESS"

    for total in range(1, 6):
        for nth in range(1, total + 1):
            assert synthesize_single(
                "length_constraints:nth_paragraph_first_word",
                {"num_paragraphs": total, "nth_paragraph": nth, "first_word": "alpha"},
            )["status"] == "CANDIDATE_SINGLE_CHECKER_WITNESS"

    for n in (100, 101, 250, 499, 500):
        for relation in ("less than", "at least"):
            assert synthesize_single(
                "length_constraints:number_words",
                {"num_words": n, "relation": relation},
            )["status"] == "CANDIDATE_SINGLE_CHECKER_WITNESS"

    for n in range(1, 21):
        for relation in ("less than", "at least"):
            assert synthesize_single(
                "change_case:capital_word_frequency",
                {"capital_frequency": n, "capital_relation": relation},
            )["status"] == "CANDIDATE_SINGLE_CHECKER_WITNESS"
