from canonical.runtime.livebench_legacy_ifeval_certified_composer_v1 import compose


def _cert(prompt: str):
    out = compose(prompt, max_candidates=768, max_rounds=18)
    assert out["status"] == "CERTIFIED_FULL_WITNESS", out
    assert out["oracle"]["follow_all_instructions"] is True
    assert out["oracle"]["row_score"] == 1.0
    assert out["model_dependency_count"] == 0
    assert out["network_used"] is False
    assert out["hidden_kwargs_used"] is False
    return out


def test_keyword_existence_title_and_no_comma():
    _cert(
        "Include keywords ['alpha', 'beta'] in the response. "
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>. "
        "In your entire response, refrain from the use of any commas."
    )


def test_repeated_keyword_frequency_instances_compose():
    _cert(
        "In your response, the word war should appear at least 3 times. "
        "In your response, the word peace should appear at least 4 times. "
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>."
    )


def test_placeholders_word_floor_and_end_phrase():
    _cert(
        "The response must contain at least 3 placeholders represented by square brackets, such as [address]. "
        "Answer with at least 25 words. "
        "Finish your response with this exact phrase Any other questions?. No other words should follow this phrase."
    )


def test_exact_bullets_plus_highlights():
    _cert(
        "Your answer must contain exactly 3 bullet points. Use the markdown bullet points such as:\n"
        "* This is point 1. \n"
        "* This is point 2 "
        "Highlight at least 2 sections in your answer with markdown, i.e. *highlighted section*. "
        "In your entire response, refrain from the use of any commas."
    )


def test_multiple_sections_plus_title():
    _cert(
        "Your response must have 3 sections. Mark the beginning of each section with Section X, such as:\n"
        "Section 1\n[content of section 1]\nSection 2\n[content of section 2] "
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>."
    )


def test_two_responses_with_existence_title_and_no_comma():
    _cert(
        "Give two different responses. Responses and only responses should be separated by 6 asterisk symbols: ******. "
        "Include keywords ['alpha', 'beta'] in the response. "
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>. "
        "In your entire response, refrain from the use of any commas."
    )


def test_repeat_prompt_with_existence_and_title():
    _cert(
        "Write a tiny harmless answer. "
        "Include keywords ['alpha'] in the response. "
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>. "
        "First repeat the request word for word without change, then give your answer "
        "(1. do not say any words or characters before repeating the request; "
        "2. the request you need to repeat does not include this sentence)"
    )


def test_lowercase_plus_word_floor_and_no_comma():
    _cert(
        "Your entire response should be in English, and in all lowercase letters. No capital letters are allowed. "
        "Answer with at least 20 words. "
        "In your entire response, refrain from the use of any commas."
    )


def test_sentence_band_via_repeated_same_family_constraints():
    _cert(
        "Your response should contain at least 3 sentences. "
        "Your response should contain less than 6 sentences. "
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>."
    )


def test_fail_closed_if_no_legacy_constraint_recognized():
    out = compose("Just answer normally.")
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "NO_RECOGNIZED_LEGACY_CONSTRAINTS"
