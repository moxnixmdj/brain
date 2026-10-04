import pytest

from canonical.runtime.legacy_repeat_prompt_visible_recovery_v1 import (
    RepeatPromptRecoveryBlocked,
    construct_checker_witness,
    recover_prompt_to_repeat,
)


def test_request_prefix_directive_suffix():
    request = "Write a short poem about cedar trees."
    prompt = (
        request
        + "\nFirst repeat the request word for word without change, then give your answer "
          "(1. do not say any words or characters before repeating the request; "
          "2. the request you need to repeat does not include this sentence)"
    )
    out = recover_prompt_to_repeat(prompt)
    assert out["prompt_to_repeat"] == request
    assert out["orientation"] == "REQUEST_PREFIX_DIRECTIVE_SUFFIX"


def test_directive_prefix_request_suffix():
    request = "Explain why leaves change color in autumn."
    prompt = (
        "First repeat the request below word for word without change, then give your answer. "
        "Do not say any words or characters before repeating the request.\n\n"
        + request
    )
    out = recover_prompt_to_repeat(prompt)
    assert out["prompt_to_repeat"] == request
    assert out["orientation"] == "DIRECTIVE_PREFIX_REQUEST_SUFFIX"


def test_witness_satisfies_exact_legacy_startswith_condition():
    request = "Summarize the water cycle."
    prompt = request + "\nBefore you answer it, just repeat the request above exactly."
    out = construct_checker_witness(prompt)
    assert out["checker_condition_proved"] is True
    assert out["answer"].strip().lower().startswith(request.lower())
    assert out["hidden_kwargs_used"] is False


def test_no_boundary_fails_closed():
    with pytest.raises(RepeatPromptRecoveryBlocked):
        recover_prompt_to_repeat("Explain photosynthesis clearly.")


def test_ambiguous_repeat_like_halves_fail_closed():
    prompt = (
        "Repeat the request exactly and answer the request.\n"
        "Repeat the prompt exactly and answer the prompt."
    )
    with pytest.raises(RepeatPromptRecoveryBlocked):
        recover_prompt_to_repeat(prompt)
