from canonical.runtime.livebench_legacy_repeat_prompt_self_detector_v1 import (
    detect_and_recover_legacy_repeat_prompt,
)
from canonical.runtime.livebench_legacy_visible_constraint_compiler_v2 import (
    compile_visible_constraints,
)


def test_canonical_suffix_shape():
    base = "Write a funny haiku about moms."
    prompt = (
        base
        + "\nFirst repeat the request word for word without change, then give your answer "
        "(1. do not say any words or characters before repeating the request; "
        "2. the request you need to repeat does not include this sentence)"
    )
    got = detect_and_recover_legacy_repeat_prompt(prompt)
    assert got["status"] == "PASS"
    assert got["prompt_to_repeat"] == base
    assert got["target_side"] == "TARGET_PREFIX"


def test_prefix_meta_shape():
    base = "Write a good name for a black dog."
    prompt = (
        "First repeat the request below word for word without change, then give your answer.\n"
        "Do not say any words or characters before repeating the request.\n\n"
        + base
    )
    got = detect_and_recover_legacy_repeat_prompt(prompt)
    assert got["status"] == "PASS"
    assert got["prompt_to_repeat"] == base
    assert got["target_side"] == "TARGET_SUFFIX"


def test_base_may_itself_mention_repeated_request():
    base = (
        'TLDR the article "How to dress like a football manager". '
        "Your entire response (including the repeated request) should have 45 or less words."
    )
    prompt = (
        base
        + "\n\nFirst repeat the request above without changing a single letter, "
        "then give your answer."
    )
    got = detect_and_recover_legacy_repeat_prompt(prompt)
    assert got["status"] == "PASS"
    assert got["prompt_to_repeat"] == base


def test_multiline_repeat_meta_does_not_leak_into_target():
    base = "Write a plot for a story about two people who swap fingerprints."
    prompt = (
        base
        + "\n\nFirst, repeat the request above word for word without change.\n"
        "Do not say any words or characters before repeating the request above.\n"
        "After you repeated the request, you can give your response next."
    )
    got = detect_and_recover_legacy_repeat_prompt(prompt)
    assert got["status"] == "PASS"
    assert got["prompt_to_repeat"] == base


def test_unrelated_prompt_is_not_invented_as_repeat_family():
    got = detect_and_recover_legacy_repeat_prompt(
        "Explain why repeated measurements improve confidence in an experiment."
    )
    assert got["status"] == "NO_MATCH"


def test_visible_compiler_discovers_noncanonical_repeat_family_and_fills_hidden_parameter():
    base = "Write a resume for a junior hardware engineer."
    prompt = (
        "Before you answer the following request, repeat it at the very beginning of your reply. "
        "Repeat the request as it is. Please do not change it.\n\n"
        + base
    )
    got = compile_visible_constraints(prompt)
    repeat = [x for x in got["constraints"] if x["instruction_id"] == "combination:repeat_prompt"]
    assert got["status"] == "PASS"
    assert len(repeat) == 1
    assert repeat[0]["parameter_complete"] is True
    assert repeat[0]["unresolved_parameters"] == []
    assert repeat[0]["slots"]["prompt_to_repeat"] == base


def test_visible_compiler_enriches_canonical_repeat_family_instead_of_duplicating_it():
    base = "Write a funny haiku about moms."
    prompt = (
        base
        + "\nFirst repeat the request word for word without change, then give your answer "
        "(1. do not say any words or characters before repeating the request; "
        "2. the request you need to repeat does not include this sentence)"
    )
    got = compile_visible_constraints(prompt)
    repeat = [x for x in got["constraints"] if x["instruction_id"] == "combination:repeat_prompt"]
    assert len(repeat) == 1
    assert repeat[0]["parameter_complete"] is True
    assert repeat[0]["slots"]["prompt_to_repeat"] == base
