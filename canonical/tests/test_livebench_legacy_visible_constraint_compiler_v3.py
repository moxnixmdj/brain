from canonical.runtime.livebench_legacy_visible_constraint_compiler_v3 import (
    compile_visible_constraints,
    source_surface,
)


REPEAT = (
    "First repeat the request word for word without change,"
    " then give your answer (1. do not say any words or characters"
    " before repeating the request; 2. the request you need to repeat"
    " does not include this sentence)"
)


def test_repeated_word_count_bounds_are_conjunctive_not_ambiguous():
    out = compile_visible_constraints(
        "Answer with at least 600 words. Answer with less than 701 words."
    )
    assert out["status"] == "PASS"
    assert out["recognized_type_count"] == 1
    assert out["recognized_instance_count"] == 2
    assert out["repeated_instruction_instance_counts"] == {
        "length_constraints:number_words": 2
    }
    assert out["duplicate_instruction_ids"] == []
    assert out["v2_duplicate_instruction_ids_observed"] == [
        "length_constraints:number_words"
    ]
    assert [c["slots"] for c in out["constraints"]] == [
        {"relation": "at least", "num_words": 600},
        {"relation": "less than", "num_words": 701},
    ]


def test_repeated_sentence_bounds_survive_with_another_checker():
    out = compile_visible_constraints(
        "In your entire response, refrain from the use of any commas. "
        "Your response should contain less than 31 sentences. "
        "Your response should contain at least 30 sentences."
    )
    assert out["status"] == "PASS"
    assert out["recognized_type_count"] == 2
    assert out["recognized_instance_count"] == 3
    assert out["repeated_instruction_ids"] == [
        "length_constraints:number_sentences"
    ]


def test_repeated_static_checker_is_idempotent_visible_constraint():
    out = compile_visible_constraints(
        "Wrap your entire response with double quotation marks. "
        "Answer with at least 10 words. "
        "Wrap your entire response with double quotation marks."
    )
    assert out["status"] == "PASS"
    assert out["recognized_instance_count"] == 3
    assert out["repeated_instruction_instance_counts"] == {
        "startend:quotation": 2
    }


def test_v2_repeat_parameter_closure_is_preserved():
    prefix = "Summarize the supplied article. Include keywords ['alpha'] in the response."
    out = compile_visible_constraints(prefix + " " + REPEAT)
    repeats = [
        c for c in out["constraints"]
        if c["instruction_id"] == "combination:repeat_prompt"
    ]
    assert len(repeats) == 1
    assert repeats[0]["parameter_complete"] is True
    assert repeats[0]["slots"]["prompt_to_repeat"] == prefix
    assert out["all_recognized_parameters_complete"] is True


def test_source_surface_keeps_v2_parameter_closure_and_adds_repetition_support():
    out = source_surface()
    assert out["recognized_public_type_count"] == 25
    assert out["fully_visible_parameter_type_count_under_historical_generator"] == 25
    assert out["repeated_same_family_instances_supported"] is True
