from canonical.runtime.livebench_legacy15_joint_router_v2 import solve


def _env(s: str) -> str:
    return (
        "The following are the beginning sentences of a news article from the Guardian.\n"
        "-------\n"
        "Public article body.\n"
        "-------\n"
        "Please summarize based on the sentences provided. "
        + s
    )


def test_nth_paragraph_strict_sentence_upper_bound_with_postscript_and_end():
    prompt = (
        "There should be 3 paragraphs. Paragraphs and only paragraphs are separated with each other by two "
        "new lines as if it was '\\n\\n' in python. Paragraph 2 must start with word anchor. "
        "Your response should contain less than 2 sentences. "
        "At the end of your response, please explicitly add a postscript starting with P.S. "
        "Finish your response with this exact phrase Any other questions?. No other words should follow this phrase."
    )
    out = solve(_env(prompt))
    assert out["status"] == "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS"
    response = out["response"]
    paragraphs = response.split("\n\n")
    assert len(paragraphs) == 3
    assert paragraphs[1].split()[0].lower() == "anchor"
    assert "P.S.Any other questions?" in response
    assert response.rstrip().endswith("Any other questions?")


def test_plain_strict_sentence_upper_bound_fuses_postscript_and_end():
    prompt = (
        "Your response should contain less than 2 sentences. "
        "At the end of your response, please explicitly add a postscript starting with P.P.S "
        "Finish your response with this exact phrase Is there anything else I can help with?. "
        "No other words should follow this phrase."
    )
    out = solve(_env(prompt))
    assert out["status"] == "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS"
    response = out["response"]
    assert "P.P.SIs there anything else I can help with?" in response
    assert response.rstrip().endswith("Is there anything else I can help with?")
