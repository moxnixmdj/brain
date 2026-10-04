from canonical.runtime.livebench_legacy_repeat_prompt_self_detector_v1 import (
    detect_and_recover_legacy_repeat_prompt,
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
