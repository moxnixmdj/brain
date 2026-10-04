from canonical.runtime.livebench_legacy_ifeval_prompt_inverter_v1 import recognize


def _repeat_slot(prompt: str):
    matches = [m for m in recognize(prompt) if m["instruction_id"] == "combination:repeat_prompt"]
    assert len(matches) == 1
    return matches[0]["slots"]["prompt_to_repeat"]


def test_repeat_prompt_canonical_suffix():
    base = "Write a funny haiku about moms."
    prompt = (
        base
        + "\nFirst repeat the request word for word without change, then give your answer "
        "(1. do not say any words or characters before repeating the request; "
        "2. the request you need to repeat does not include this sentence)"
    )
    assert _repeat_slot(prompt) == base


def test_repeat_prompt_public_prefix_meta():
    base = "Write an acoustic song about the Korean peninsula without using any commas."
    prompt = (
        "In this task, repeat the exact request below first, then give your response. "
        "Do not say any word before repeating the exact request.\n\n"
        + base
    )
    assert _repeat_slot(prompt) == base


def test_repeat_prompt_public_below_variant():
    base = (
        "Write a story about a man who is trying to get his life together. "
        "Put the name of the story in double angular brackets, i.e. <<story of xyz>>."
    )
    prompt = (
        "First repeat the request below, word for word without change, then give your answer. "
        "Do not say any words or characters before repeating the request below.\n\n"
        + base
    )
    assert _repeat_slot(prompt) == base


def test_repeat_prompt_public_multiline_suffix():
    base = (
        "Write a plot for a story about two people who swap fingerprints. "
        "Include a title wrapped in double angular brackets, i.e. <<title>>. "
        "In your response please avoid using commas."
    )
    prompt = (
        base
        + "\n\nFirst, repeat the request above word for word without change.\n"
        "Do not say any words or characters before repeating the request above.\n"
        "After you repeated the request, you can give your response next."
    )
    assert _repeat_slot(prompt) == base


def test_repeat_word_in_base_is_not_false_positive():
    prompt = (
        "TLDR the article. Your entire response including the repeated request "
        "should have 45 or less words."
    )
    assert not [
        m for m in recognize(prompt)
        if m["instruction_id"] == "combination:repeat_prompt"
    ]
