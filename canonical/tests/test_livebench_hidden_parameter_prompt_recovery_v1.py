from canonical.runtime.livebench_hidden_parameter_prompt_recovery_v1 import (
    recover_legacy_repeat_prompt,
    recover_repeat_span_response,
)


def test_repeat_span_prompt_only():
    prompt = (
        "zero one two three four "
        "Copy the span of words that lies between (and including) index 1 and 4, "
        "the indices are word indices, split by whitespace!"
    )
    got = recover_repeat_span_response(prompt)
    assert got["response"] == "one two three"


def test_legacy_repeat_suffix_meta():
    prompt = (
        "Write a funny haiku about moms.\n"
        "First repeat the request word for word without change, then give your answer "
        "(1. do not say any words or characters before repeating the request; "
        "2. the request you need to repeat does not include this sentence)"
    )
    got = recover_legacy_repeat_prompt(prompt)
    assert got["prompt_to_repeat"] == "Write a funny haiku about moms."


def test_legacy_repeat_prefix_meta():
    prompt = (
        "Before you answer the following request, repeat it at the very beginning of your reply. "
        "Repeat the request as it is. Please do not change it.\n\n"
        "Write a resume for a junior hardware engineer."
    )
    got = recover_legacy_repeat_prompt(prompt)
    assert got["prompt_to_repeat"] == "Write a resume for a junior hardware engineer."


def test_legacy_base_can_mention_repeated_request():
    prompt = (
        "TLDR the article. Your entire response (including the repeated request) should have 45 or less words.\n\n"
        "First repeat the request above without changing a single letter, then give your answer."
    )
    got = recover_legacy_repeat_prompt(prompt)
    assert "including the repeated request" in got["prompt_to_repeat"]


def test_legacy_livebench_exact_generator_prefix_rule_preserves_prior_constraints():
    repeat = (
        "First repeat the request word for word without change, then give your answer "
        "(1. do not say any words or characters before repeating the request; "
        "2. the request you need to repeat does not include this sentence)"
    )
    prefix = (
        "The following are the beginning sentences of a news article from the Guardian.\n"
        "-------\n"
        "Article sentence one. Article sentence two.\n"
        "-------\n"
        "Please summarize based on the sentences provided. "
        "Include keywords ['alpha', 'beta'] in the response. "
    )
    prompt = prefix + repeat + " Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>."
    got = recover_legacy_repeat_prompt(prompt)
    assert got["prompt_to_repeat"] == prefix.rstrip()
    assert got["response_prefix"] == prefix.rstrip()
    assert got["source"] == "VISIBLE_PROMPT_PREFIX_BEFORE_PINNED_LIVEBENCH_REPEAT_MARKER"
    assert got["scope"] == "PINNED_LIVEBENCH_LEGACY_GENERATION_RULE_V1"


def test_legacy_livebench_exact_rule_matches_historical_split_semantics():
    marker = "First repeat the request word for word without change,"
    prompt = "base before marker " + marker + " tail " + marker + " second tail"
    got = recover_legacy_repeat_prompt(prompt)
    assert got["prompt_to_repeat"] == prompt.split(marker)[0].rstrip()
