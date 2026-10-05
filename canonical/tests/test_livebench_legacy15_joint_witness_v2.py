import re

from canonical.runtime.livebench_legacy15_joint_witness_v2 import solve


def _bullet_count(value: str) -> int:
    a = re.findall(r"^\s*\*[^\*].*$", value, flags=re.MULTILINE)
    b = re.findall(r"^\s*-.*$", value, flags=re.MULTILINE)
    return len(a) + len(b)


def test_quotation_plus_bullets_preserves_exact_bullet_count():
    prompt = (
        "Your answer must contain exactly 3 bullet points. Use the markdown bullet points such as:\n"
        "* This is point 1. \n* This is point 2 "
        "Wrap your entire response with double quotation marks."
    )
    out = solve(prompt)
    assert out["status"] == "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS_V2"
    assert out["response"][0] == out["response"][-1] == '"'
    assert _bullet_count(out["response"]) == 3


def test_less_than_one_sentence_fails_closed_instead_of_false_pass():
    prompt = "Your response should contain less than 1 sentences."
    out = solve(prompt)
    assert out["status"] == "FAIL_CLOSED"
    assert "LESS_THAN_ONE_SENTENCE" in out["error"]


def test_less_than_sentences_with_postscript_fails_closed_without_exact_punkt_search():
    prompt = (
        "Your response should contain less than 2 sentences. "
        "At the end of your response, please explicitly add a postscript starting with P.S."
    )
    out = solve(prompt)
    assert out["status"] == "FAIL_CLOSED"
    assert "EXACT_TOKENIZER_SEARCH" in out["error"]


def test_less_than_sentences_with_end_phrase_fails_closed_without_exact_punkt_search():
    prompt = (
        "Your response should contain less than 2 sentences. "
        "Finish your response with this exact phrase Any other questions?. No other words should follow this phrase."
    )
    out = solve(prompt)
    assert out["status"] == "FAIL_CLOSED"
    assert "EXACT_TOKENIZER_SEARCH" in out["error"]


def test_plain_less_than_two_sentence_candidate_stays_one_sentence():
    prompt = "Your response should contain less than 2 sentences."
    out = solve(prompt)
    assert out["status"] == "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS_V2"
    assert not re.search(r"[.!?]", out["response"])
