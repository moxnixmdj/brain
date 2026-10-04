from canonical.runtime.livebench_legacy15_rowblind_self_validating_composer_v1 import solve

SEP = "\n-------\n"

def prompt(*constraints: str, body: str = "Public article text.") -> str:
    return "The following are the beginning sentences of a news article from the Guardian." + SEP + body + SEP + "Please summarize based on the sentences provided. " + " ".join(constraints)

def assert_pass(p: str, expected: str):
    out = solve(p)
    assert out["status"] == "PASS_CANDIDATE_ROWBLIND", out
    assert out["archetype"] == expected
    assert out["visible_self_validation_pass"] is True
    assert out["hidden_instruction_ids_used"] is False
    assert out["hidden_kwargs_used"] is False
    assert out["terminal_case_metadata_used"] is False
    assert out["terminal_case_content_used"] is False
    assert out["prior_score_used"] is False

def test_json_archetype():
    assert_pass(prompt(
        "Entire output should be wrapped in JSON format. You can use markdown ticks such as ```.",
        "Include keywords ['western'] in the response.",
        "Do not include keywords ['western'] in the response.",
    ), "JSON")

def test_two_responses_archetype():
    assert_pass(prompt(
        "Give two different responses. Responses and only responses should be separated by 6 asterisk symbols: ******.",
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>.",
        "Include keywords ['signal'] in the response.",
        "Do not include keywords ['signal'] in the response.",
    ), "TWO_RESPONSES")

def test_repeat_prompt_archetype():
    assert_pass(prompt(
        "Include keywords ['signal'] in the response.",
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>.",
        "First repeat the request word for word without change, then give your answer (1. do not say any words or characters before repeating the request; 2. the request you need to repeat does not include this sentence)",
    ), "REPEAT_PROMPT")

def test_nth_paragraph_archetype():
    assert_pass(prompt(
        "There should be 3 paragraphs. Paragraphs and only paragraphs are separated with each other by two new lines as if it was '\\\\n\\\\n' in python. Paragraph 2 must start with word western.",
        "Answer with at least 110 words.",
        "Include keywords ['signal'] in the response.",
        "Do not include keywords ['signal'] in the response.",
    ), "NTH_PARAGRAPH")

def test_star_paragraph_archetype():
    assert_pass(prompt(
        "There should be 3 paragraphs. Paragraphs are separated with the markdown divider: ***",
        "Answer with at least 110 words.",
        "Your response must have 2 sections. Mark the beginning of each section with Section X, such as:",
        "Your answer must contain exactly 2 bullet points. Use the markdown bullet points such as:",
    ), "STAR_PARAGRAPH")

def test_sentence_archetype():
    assert_pass(prompt(
        "Your response should contain at least 4 sentences.",
        "Answer with at least 110 words.",
        "Finish your response with this exact phrase Any other questions?. No other words should follow this phrase.",
        "Wrap your entire response with double quotation marks.",
    ), "SENTENCE")

def test_plain_archetype():
    assert_pass(prompt(
        "Include keywords ['brain'] in the response.",
        "Do not include keywords ['brain'] in the response.",
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>.",
        "At the end of your response, please explicitly add a postscript starting with P.S.",
    ), "PLAIN")
