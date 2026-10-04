from canonical.runtime.livebench_legacy_joint_witness_v1 import solve


def envelope(suffix: str) -> str:
    return "Public synthetic source text\n-------\n" + suffix


def assert_pass(envelope(prompt)):
    out = solve(envelope(prompt))
    assert out["status"] == "PASS_CANDIDATE_EXACT_POSTVALIDATION_REQUIRED", out
    assert out["response"]
    return out["response"]


def test_general_joint_keyword_word_no_comma_quote():
    prompt = (
        "Include keywords ['alpha', 'beta'] in the response. "
        "Answer with at least 30 words. "
        "In your entire response, refrain from the use of any commas. "
        "Wrap your entire response with double quotation marks."
    )
    response = assert_pass(envelope(prompt))
    assert response.startswith('"') and response.endswith('"')
    assert "," not in response
    assert "alpha" in response.lower() and "beta" in response.lower()


def test_two_response_route_with_title_and_no_comma():
    prompt = (
        "Give two different responses. Responses and only responses should be separated by 6 asterisk symbols: ******. "
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>. "
        "In your entire response, refrain from the use of any commas."
    )
    response = assert_pass(envelope(prompt))
    assert response.count("******") == 1
    assert "<<verified result>>" in response
    assert "," not in response


def test_repeat_prompt_recovers_visible_prefix():
    prefix = "Please summarize this clean source text"
    marker = (
        "First repeat the request word for word without change,"
        " then give your answer (1. do not say any words or characters"
        " before repeating the request; 2. the request you need to repeat"
        " does not include this sentence)"
    )
    prompt = prefix + " " + marker + " Include keywords ['alpha'] in the response."
    wrapped = envelope(prompt)
    response = assert_pass(wrapped)
    expected_prefix = wrapped.split(marker, 1)[0].strip()
    assert response.lower().startswith(expected_prefix.lower())
    assert "alpha" in response.lower()


def test_markdown_paragraph_and_bullets_compose():
    prompt = (
        "There should be 3 paragraphs. Paragraphs are separated with the markdown divider: *** "
        "Your answer must contain exactly 2 bullet points. Use the markdown bullet points such as:\n"
        "* This is point 1. \n* This is point 2 "
        "The response must contain at least 2 placeholders represented by square brackets, such as [address]."
    )
    response = assert_pass(envelope(prompt))
    assert response.count("***") == 2
    assert "[slot1]" in response and "[slot2]" in response


def test_nth_paragraph_first_word_compose():
    prompt = (
        "There should be 3 paragraphs. Paragraphs and only paragraphs are separated with each other by two "
        "new lines as if it was '\\n\\n' in python. Paragraph 2 must start with word river. "
        "Answer with at least 20 words."
    )
    response = assert_pass(envelope(prompt))
    paragraphs = response.split("\n\n")
    assert len(paragraphs) == 3
    assert paragraphs[1].lower().startswith("river")


def test_visible_less_than_contradiction_fails_closed():
    prompt = (
        "Include keywords ['alpha'] in the response. "
        "In your response, the letter a should appear less than 1 times."
    )
    out = solve(envelope(prompt))
    assert out["status"] == "FAIL_CLOSED"
    assert "LETTER" in out["error"]


def test_language_family_is_outside_recovered_generator_surface():
    prompt = "Your ENTIRE response should be in English language, no other language is allowed."
    out = solve(envelope(prompt))
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "OUTSIDE_RECOVERED_HISTORICAL_GENERATOR_SURFACE"
