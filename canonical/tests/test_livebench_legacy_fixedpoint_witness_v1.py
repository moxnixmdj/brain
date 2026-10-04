import pytest

pytest.importorskip("langdetect")
pytest.importorskip("immutabledict")
nltk = pytest.importorskip("nltk")

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    pytest.skip("pinned legacy checker test requires NLTK punkt", allow_module_level=True)

from canonical.runtime.livebench_legacy_fixedpoint_witness_v1 import (
    HISTORICAL_GENERATOR_INSTRUCTION_IDS,
    synthesize_visible_witness,
)


def _assert_pass(prompt: str):
    out = synthesize_visible_witness(prompt)
    assert out["status"] == "PASS", out
    assert out["exact_checker_pass_count"] == out["checker_count"]
    assert not out["failing_instruction_ids"]
    assert out["visible_prompt_only"] is True
    assert out["hidden_instruction_ids_used"] is False
    assert out["hidden_kwargs_used"] is False
    return out


def test_historical_generator_universe_is_24_not_registry_25():
    assert len(HISTORICAL_GENERATOR_INSTRUCTION_IDS) == 24
    assert "language:response_language" not in HISTORICAL_GENERATOR_INSTRUCTION_IDS


def test_joint_lexical_word_count_quote_and_no_comma():
    _assert_pass(
        "Explain deterministic verification. "
        "Include keywords ['alpha', 'omega'] in the response. "
        "Do not include keywords ['danger', 'failure'] in the response. "
        "Answer with at least 20 words. "
        "In your entire response, refrain from the use of any commas. "
        'Wrap your entire response with double quotation marks.'
    )


def test_joint_bullets_highlights_placeholder_end_and_no_comma():
    _assert_pass(
        "Explain a small system. "
        "Your answer must contain exactly 3 bullet points. "
        "Use the markdown bullet points such as:\n"
        "* This is point 1. \n"
        "* This is point 2 "
        "Highlight at least 2 sections in your answer with markdown, i.e. *highlighted section*. "
        "The response must contain at least 2 placeholders represented by square brackets, such as [address]. "
        "Finish your response with this exact phrase Any other questions?. "
        "No other words should follow this phrase. "
        "In your entire response, refrain from the use of any commas."
    )


def test_joint_paragraph_keyword_frequency_letter_frequency_and_quote():
    _assert_pass(
        "Explain a process. "
        "There should be 3 paragraphs. Paragraphs are separated with the markdown divider: *** "
        "In your response, the word orbit should appear at least 2 times. "
        "In your response, the letter q should appear at least 3 times. "
        "Answer with at least 30 words. "
        'Wrap your entire response with double quotation marks.'
    )


def test_nth_paragraph_title_end_and_no_comma():
    _assert_pass(
        "Explain a process. "
        "There should be 3 paragraphs. Paragraphs and only paragraphs are separated with each other by two "
        "new lines as if it was '\\n\\n' in python. Paragraph 2 must start with word anchor. "
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>. "
        "Finish your response with this exact phrase Any other questions?. No other words should follow this phrase. "
        "In your entire response, refrain from the use of any commas."
    )


def test_json_can_compose_with_existence_and_forbidden():
    _assert_pass(
        "Explain a process. "
        "Entire output should be wrapped in JSON format. You can use markdown ticks such as \`\`\`. "
        "Include keywords ['alpha', 'omega'] in the response. "
        "Do not include keywords ['danger', 'failure'] in the response."
    )


def test_two_response_allowed_surface_composes():
    _assert_pass(
        "Explain a process. "
        "Give two different responses. Responses and only responses should be separated by 6 asterisk symbols: ******. "
        "Include keywords ['alpha'] in the response. "
        "Do not include keywords ['danger'] in the response. "
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>. "
        "In your entire response, refrain from the use of any commas."
    )


def test_repeat_prompt_allowed_surface_composes_when_prefix_is_comma_free():
    prompt = (
        "Explain why proof matters. "
        "Include keywords ['alpha'] in the response. "
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>. "
        "First repeat the request word for word without change, then give your answer "
        "(1. do not say any words or characters before repeating the request; "
        "2. the request you need to repeat does not include this sentence) "
        "In your entire response, refrain from the use of any commas."
    )
    _assert_pass(prompt)


def test_registry_language_checker_is_rejected_as_outside_generator_lineage():
    out = synthesize_visible_witness(
        "Explain a process. "
        "Your ENTIRE response should be in French language, no other language is allowed."
    )
    assert out["status"] == "BLOCKED"
    assert out["reason"] == "OUTSIDE_RECOVERED_HISTORICAL_GENERATOR_UNIVERSE"
    assert out["outside_instruction_ids"] == ["language:response_language"]


def test_known_repeat_plus_comma_ceiling_fails_closed_not_fabricated():
    prompt = (
        "Explain this request, using the visible prefix. "
        "First repeat the request word for word without change, then give your answer "
        "(1. do not say any words or characters before repeating the request; "
        "2. the request you need to repeat does not include this sentence) "
        "In your entire response, refrain from the use of any commas."
    )
    out = synthesize_visible_witness(prompt)
    assert out["status"] == "BLOCKED"
    assert out["reason"] == "NO_ALL_CHECKER_FIXED_POINT_FOUND"
    assert "punctuation:no_comma" in out["best_failing_instruction_ids"] or (
        "combination:repeat_prompt" in out["best_failing_instruction_ids"]
    )
