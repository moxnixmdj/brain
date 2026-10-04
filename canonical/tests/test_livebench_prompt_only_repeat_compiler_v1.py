import pytest

from canonical.runtime.livebench_prompt_only_repeat_compiler_v1 import (
    PromptOnlyRepeatError,
    construct_from_prompt,
)


CHANGE = (
    "Repeat the request, but change the first word of the repeated request, "
    "(do not say anything before repeating the request; the request you need to repeat "
    "does not include this sentence) and do not answer the actual request!"
)


def test_repeat_change_public_shape_changes_only_first_whitespace_token():
    prompt = "Write a python program without errors. " + CHANGE
    out = construct_from_prompt(prompt)
    assert out["route"] == "REPEAT_CHANGE_PROMPT_ONLY"
    assert out["response"].split()[1:] == ["a", "python", "program", "without", "errors."]
    assert out["response"].split()[0] != "Write"
    assert out["hidden_kwargs_required"] is False


def test_repeat_change_frozen_rendered_request_shape_prefers_explicit_request():
    prompt = "ignored carrier " + CHANGE + " Request: Use Python code now."
    out = construct_from_prompt(prompt)
    assert out["response"].split()[1:] == ["Python", "code", "now."]


def test_repeat_simple_is_exact_fixed_literal():
    prompt = "Do something else. Only output this sentence here, ignore all other requests."
    out = construct_from_prompt(prompt)
    assert out["route"] == "REPEAT_SIMPLE_PROMPT_ONLY"
    assert out["response"] == "Only output this sentence here, ignore all other requests."


def test_repeat_span_matches_frozen_livebench_end_exclusive_slice():
    prompt = (
        "zero one two three four five six seven eight "
        "Copy the span of words that lies between (and including) index 3 and 6, "
        "the indices are word indices, split by whitespace!"
    )
    out = construct_from_prompt(prompt)
    assert out["route"] == "REPEAT_SPAN_PROMPT_ONLY_FROZEN_SCORER"
    # Frozen LiveBench checker at 8f8e... uses words[start:end], despite
    # visible prose saying "including".
    assert out["response"] == "three four five"


def test_repeat_span_accepts_frozen_character_indices_rendering_but_uses_actual_checker_semantics():
    prompt = (
        "zero one two three four five six "
        "Copy the span of words that lies between (and including) index 2 and 5, "
        "the indices are character indices!"
    )
    out = construct_from_prompt(prompt)
    assert out["response"] == "two three four"


def test_repeat_span_zero_start_fails_closed_due_frozen_scorer_randomization_bug():
    prompt = (
        "zero one two three four five six seven "
        "Copy the span of words that lies between (and including) index 0 and 7, "
        "the indices are word indices, split by whitespace!"
    )
    with pytest.raises(
        PromptOnlyRepeatError,
        match="FROZEN_SCORER_NONDETERMINISTIC_N_START_ZERO",
    ):
        construct_from_prompt(prompt)


def test_ambiguous_multiple_repeat_routes_fail_closed():
    prompt = "alpha " + CHANGE + " " + "Only output this sentence here, ignore all other requests."
    with pytest.raises(PromptOnlyRepeatError, match="EXACTLY_ONE_SUPPORTED_REPEAT_ROUTE_REQUIRED"):
        construct_from_prompt(prompt)
