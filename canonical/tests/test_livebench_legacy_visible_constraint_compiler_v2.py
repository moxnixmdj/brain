from canonical.runtime.livebench_legacy_visible_constraint_compiler_v2 import (
    compile_visible_constraints,
    source_surface,
)


def test_repeated_word_count_bounds_are_preserved_not_rejected():
    prompt = (
        "Answer with at least 600 words. "
        "Answer with less than 701 words."
    )
    out = compile_visible_constraints(prompt)
    assert out["status"] == "PASS"
    assert out["recognized_type_count"] == 1
    assert out["recognized_instance_count"] == 2
    assert out["repeated_instruction_ids"] == ["length_constraints:number_words"]
    assert out["repeated_instruction_instance_counts"] == {
        "length_constraints:number_words": 2
    }
    slots = [x["slots"] for x in out["constraints"]]
    assert slots == [
        {"relation": "at least", "num_words": 600},
        {"relation": "less than", "num_words": 701},
    ]


def test_repeated_sentence_range_survives_with_another_checker():
    prompt = (
        "In your entire response, refrain from the use of any commas. "
        "Your response should contain less than 31 sentences. "
        "Your response should contain at least 30 sentences."
    )
    out = compile_visible_constraints(prompt)
    assert out["status"] == "PASS"
    assert out["recognized_type_count"] == 2
    assert out["recognized_instance_count"] == 3
    assert out["repeated_instruction_ids"] == ["length_constraints:number_sentences"]


def test_duplicate_static_checker_is_idempotent_visible_constraint_not_ambiguity():
    prompt = (
        "Wrap your entire response with double quotation marks. "
        "Answer with at least 10 words. "
        "Wrap your entire response with double quotation marks."
    )
    out = compile_visible_constraints(prompt)
    assert out["status"] == "PASS"
    assert out["recognized_instance_count"] == 3
    assert out["repeated_instruction_instance_counts"] == {
        "startend:quotation": 2
    }


def test_nonrepeated_behavior_remains_pass():
    out = compile_visible_constraints(
        "Include keywords ['alpha', 'beta'] in the response. "
        "In your entire response, refrain from the use of any commas."
    )
    assert out["status"] == "PASS"
    assert out["repeated_instruction_ids"] == []
    assert out["recognized_instance_count"] == 2


def test_surface_keeps_all_25_and_declares_repetition_support():
    out = source_surface()
    assert out["recognized_public_type_count"] == 25
    assert out["registered_legacy_type_count"] == 25
    assert out["all_registered_types_covered_by_recognizers"]
    assert out["repeated_same_family_instances_supported"]
