from canonical.runtime.livebench_legacy15_joint_witness_v1 import solve


FENCE = chr(96) * 3


def envelope(suffix: str, article: str = "Ordinary article text with no generated constraints.") -> str:
    return (
        "The following are the beginning sentences of a news article from the Guardian.\n"
        "-------\n"
        + article
        + "\n-------\n"
        + suffix
    )


def test_v4_contract_accepts_complete_visible_suffix():
    out = solve(envelope("Include keywords ['alpha'] in the response."))
    assert out["status"] == "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS"
    assert "alpha" in out["response"]


def test_article_region_is_not_misparsed_as_constraint():
    article = "Include keywords ['article_trap'] in the response."
    out = solve(envelope("Include keywords ['real_suffix'] in the response.", article=article))
    assert out["status"] == "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS"
    assert "real_suffix" in out["response"]
    assert "article_trap" not in out["response"]


def test_missing_historical_envelope_fails_closed():
    out = solve("Include keywords ['alpha'] in the response.")
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "VISIBLE_COMPILER_NOT_COMPLETE"


def test_json_exists_forbidden_composition():
    suffix = (
        "Include keywords ['alpha', 'cat'] in the response. "
        "Do not include keywords ['cat', 'dog'] in the response. "
        f"Entire output should be wrapped in JSON format. You can use markdown ticks such as {FENCE}."
    )
    out = solve(envelope(suffix))
    assert out["status"] == "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS"
    assert out["route"] == "JSON"
    assert "alpha" in out["response"]
    assert "cat" in out["response"].lower()
    assert " cat " not in (" " + out["response"].lower() + " ")


def test_repeat_prompt_plus_title_and_existence():
    marker = (
        "First repeat the request word for word without change, then give your answer "
        "(1. do not say any words or characters before repeating the request; "
        "2. the request you need to repeat does not include this sentence)"
    )
    before = "Please summarize based on the sentences provided. Include keywords ['alpha'] in the response."
    suffix = (
        before + " " + marker + " "
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>."
    )
    prompt = envelope(suffix)
    recovered_target = prompt.split(marker, 1)[0].strip()
    out = solve(prompt)
    assert out["status"] == "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS"
    assert out["route"] == "REPEAT_PROMPT"
    assert out["response"].startswith(recovered_target)
    assert "<<x>>" in out["response"]
    assert "alpha" in out["response"]


def test_two_responses_with_keyword_title_forbidden():
    suffix = (
        "Include keywords ['alpha'] in the response. "
        "Do not include keywords ['dog'] in the response. "
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>. "
        "Give two different responses. Responses and only responses should be separated by 6 asterisk symbols: ******."
    )
    out = solve(envelope(suffix))
    assert out["status"] == "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS"
    assert out["route"] == "TWO_RESPONSES"
    assert out["response"].count("******") == 1
    assert "dog" not in out["response"].lower()


def test_general_sections_bullets_words_end():
    suffix = (
        "Your answer must contain exactly 3 bullet points. "
        "Your response must have 2 sections. Mark the beginning of each section with SECTION X, such as: "
        "Answer with at least 40 words. "
        "Finish your response with this exact phrase Any other questions?. No other words should follow this phrase."
    )
    out = solve(envelope(suffix))
    assert out["status"] == "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS"
    assert out["route"] == "GENERAL"
    assert out["response"].rstrip().lower().endswith("any other questions?")
    assert sum(1 for line in out["response"].splitlines() if line.lstrip().startswith("* ")) == 3


def test_quotation_and_end_compose():
    suffix = (
        "Finish your response with this exact phrase Any other questions?. No other words should follow this phrase. "
        "Wrap your entire response with double quotation marks."
    )
    out = solve(envelope(suffix))
    assert out["status"] == "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS"
    assert out["response"][0] == out["response"][-1] == '"'
    assert out["response"].strip('"').rstrip().lower().endswith("any other questions?")


def test_nth_paragraph_first_word():
    suffix = (
        "There should be 3 paragraphs. Paragraphs and only paragraphs are separated with each other by two "
        "new lines as if it was '\\n\\n' in python. Paragraph 2 must start with word anchor."
    )
    out = solve(envelope(suffix))
    assert out["status"] == "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS"
    ps = out["response"].split("\n\n")
    assert len(ps) == 3
    assert ps[1].split()[0].lower() == "anchor"
