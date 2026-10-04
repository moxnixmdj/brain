from canonical.runtime.livebench_legacy_joint_witness_v1 import solve


def envelope(suffix: str) -> str:
    return "Public synthetic source text\n-------\n" + suffix


def assert_pass(prompt: str) -> str:
    out = solve(prompt)
    assert out["status"] == "PASS_CANDIDATE_EXACT_POSTVALIDATION_REQUIRED", out
    assert out["response"]
    return out["response"]


def test_keyword_word_quote_active15():
    prompt = envelope(
        "Include keywords ['alpha', 'beta'] in the response. "
        "Answer with at least 30 words. "
        "Wrap your entire response with double quotation marks."
    )
    response = assert_pass(prompt)
    assert response.startswith('"') and response.endswith('"')
    assert "alpha" in response.lower() and "beta" in response.lower()


def test_two_response_title_forbidden_active15():
    prompt = envelope(
        "Give two different responses. Responses and only responses should be separated by 6 asterisk symbols: ******. "
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>. "
        "Do not include the word forbidden."
    )
    response = assert_pass(prompt)
    assert response.count("******") == 1
    assert "<<verified result>>" in response
    assert "forbidden" not in response.lower()


def test_repeat_prompt_recovers_historical_visible_prefix():
    marker = (
        "First repeat the request word for word without change,"
        " then give your answer (1. do not say any words or characters"
        " before repeating the request; 2. the request you need to repeat"
        " does not include this sentence)"
    )
    suffix = "Please summarize this clean source text " + marker + " Include keywords ['alpha'] in the response."
    wrapped = envelope(suffix)
    response = assert_pass(wrapped)
    expected_prefix = wrapped.split(marker, 1)[0].strip()
    assert response.lower().startswith(expected_prefix.lower())
    assert "alpha" in response.lower()


def test_number_paragraphs_and_bullets_active15():
    prompt = envelope(
        "There should be 3 paragraphs. Paragraphs are separated with the markdown divider: *** "
        "Your answer must contain exactly 2 bullet points. Use the markdown bullet points such as:\n"
        "* This is point 1. \n* This is point 2"
    )
    response = assert_pass(prompt)
    assert response.count("***") == 2
    assert sum(1 for line in response.splitlines() if line.strip().startswith("*")) == 2


def test_nth_paragraph_first_word_and_words_active15():
    prompt = envelope(
        "There should be 3 paragraphs. Paragraphs and only paragraphs are separated with each other by two "
        "new lines as if it was '\\n\\n' in python. Paragraph 2 must start with word river. "
        "Answer with at least 20 words."
    )
    response = assert_pass(prompt)
    paragraphs = response.split("\n\n")
    assert len(paragraphs) == 3
    assert paragraphs[1].lower().startswith("river")


def test_json_and_keyword_active15():
    prompt = envelope(
        "Output should be in JSON format. "
        "Include keywords ['alpha', 'beta'] in the response."
    )
    response = assert_pass(prompt)
    assert "alpha" in response.lower() and "beta" in response.lower()


def test_outside_exact_active15_fails_closed():
    prompt = envelope("In your entire response, refrain from the use of any commas.")
    out = solve(prompt)
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "OUTSIDE_RECOVERED_HISTORICAL_GENERATOR_SURFACE"
