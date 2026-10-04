from canonical.runtime.livebench_legacy_visible_contract_core_v2 import (
    full_score_quotient_theorem,
    quotient_exact_predicates,
    recover_repeat_prompt_target,
)


def test_same_family_distinct_predicates_are_preserved():
    out = quotient_exact_predicates([
        {
            "instruction_id": "length_constraints:number_sentences",
            "kwargs": {"relation": "at least", "num_sentences": 20},
        },
        {
            "instruction_id": "length_constraints:number_sentences",
            "kwargs": {"relation": "less than", "num_sentences": 26},
        },
    ])
    assert out["instance_count"] == 2
    assert out["unique_predicate_count"] == 2
    assert out["duplicate_family_ids"] == ["length_constraints:number_sentences"]
    assert out["exact_duplicate_group_count"] == 0


def test_exact_duplicate_predicate_is_quotiented_only_for_full_score_reasoning():
    out = quotient_exact_predicates([
        {"instruction_id": "startend:quotation", "kwargs": {}},
        {"instruction_id": "startend:quotation", "kwargs": {}},
    ])
    assert out["instance_count"] == 2
    assert out["unique_predicate_count"] == 1
    assert out["exact_duplicate_group_count"] == 1
    assert out["exact_duplicate_extra_instances"] == 1


def test_full_score_is_invariant_to_exact_duplicate_multiplicity():
    a = full_score_quotient_theorem([True], [1])
    b = full_score_quotient_theorem([True], [2])
    c = full_score_quotient_theorem([True, True], [9, 3])
    assert a["score"] == b["score"] == c["score"] == 1.0
    assert a["full_score"] and b["full_score"] and c["full_score"]


def test_prefix_repeat_target_recovery():
    target = "Write a poem about Jupiter. Do not use commas."
    prompt = target + "\nFirst repeat the request word for word without change, then give your answer."
    out = recover_repeat_prompt_target(prompt)
    assert out["status"] == "RECOVERED"
    assert out["prompt_to_repeat"] == target


def test_suffix_repeat_target_recovery():
    target = "Write a song about a corgi named Chester who loves to play fetch."
    prompt = (
        "Before you answer it, just repeat the request below. "
        "You need to repeat it exactly as it is. Do not change any word.\n\n"
        + target
    )
    out = recover_repeat_prompt_target(prompt)
    assert out["status"] == "RECOVERED"
    assert out["prompt_to_repeat"] == target


def test_typo_repleat_public_style_is_recoverable():
    target = "Rewrite the following sentence in a more formal way."
    prompt = (
        target
        + "\n\nPlease repleat the entire first line above, then give your rewrite. "
          "Do not add any word before that."
    )
    out = recover_repeat_prompt_target(prompt)
    assert out["status"] == "RECOVERED"
    assert out["prompt_to_repeat"] == target


def test_non_repeat_prompt_abstains():
    out = recover_repeat_prompt_target("Write a normal paragraph about a tree.")
    assert out["status"].startswith("ABSTAIN")
    assert out["prompt_to_repeat"] is None
