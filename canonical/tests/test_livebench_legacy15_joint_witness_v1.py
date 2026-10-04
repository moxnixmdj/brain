import re

from canonical.runtime.livebench_legacy15_joint_witness_v1 import solve


def _env(s: str) -> str:
    return "Historical task request.\n-------\nPublic article body.\n-------\n" + s

def test_json_exists_forbidden_composition():
    prompt = (
        "Include keywords ['alpha', 'cat'] in the response. "
        "Do not include keywords ['cat', 'dog'] in the response. "
        "Entire output should be wrapped in JSON format. You can use markdown ticks such as code fences."
    )
    out = solve(_env(prompt))
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
    prefix = "Please summarize the article. Include keywords ['alpha'] in the response."
    prompt = prefix + " " + marker + " Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>."
    out = solve(_env(prompt))
    assert out["status"] == "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS"
    assert out["route"] == "REPEAT_PROMPT"
    assert out["response"].startswith(_env(prefix).strip())
    assert "<<x>>" in out["response"]
    assert "alpha" in out["response"]

def test_two_responses_with_keyword_title_forbidden():
    prompt = (
        "Include keywords ['alpha'] in the response. "
        "Do not include keywords ['dog'] in the response. "
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>. "
        "Give two different responses. Responses and only responses should be separated by 6 asterisk symbols: ******."
    )
    out = solve(_env(prompt))
    assert out["status"] == "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS"
    assert out["route"] == "TWO_RESPONSES"
    assert out["response"].count("******") == 1
    assert "dog" not in out["response"].lower()

def test_general_sections_bullets_words_end():
    prompt = (
        "Your answer must contain exactly 3 bullet points. Use the markdown bullet points such as:\n"
        "* This is point 1. \n* This is point 2 "
        "Your response must have 2 sections. Mark the beginning of each section with SECTION X, such as:\n"
        "SECTION 1\n[content of section 1]\nSECTION 2\n[content of section 2] "
        "Answer with at least 40 words. "
        "Finish your response with this exact phrase Any other questions?. No other words should follow this phrase."
    )
    out = solve(_env(prompt))
    assert out["status"] == "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS"
    assert out["route"] == "GENERAL"
    assert out["response"].rstrip().lower().endswith("any other questions?")
    assert sum(1 for line in out["response"].splitlines() if line.lstrip().startswith("* ")) == 3

def test_quotation_and_end_compose():
    prompt = (
        "Finish your response with this exact phrase Any other questions?. No other words should follow this phrase. "
        "Wrap your entire response with double quotation marks."
    )
    out = solve(_env(prompt))
    assert out["status"] == "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS"
    assert out["response"][0] == out["response"][-1] == '"'
    assert out["response"].strip('"').rstrip().lower().endswith("any other questions?")

def test_nth_paragraph_first_word():
    prompt = (
        "There should be 3 paragraphs. Paragraphs and only paragraphs are separated with each other by two "
        "new lines as if it was '\\n\\n' in python. Paragraph 2 must start with word anchor."
    )
    out = solve(_env(prompt))
    assert out["status"] == "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS"
    ps = out["response"].split("\n\n")
    assert len(ps) == 3
    assert ps[1].split()[0].lower() == "anchor"


def test_quotation_preserves_exact_bullet_count():
    prompt = (
        "Your answer must contain exactly 5 bullet points. Use the markdown bullet points such as:\n"
        "* This is point 1. \n* This is point 2 "
        "Wrap your entire response with double quotation marks."
    )
    out = solve(_env(prompt))
    assert out["status"] == "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS"
    response = out["response"]
    assert response[0] == response[-1] == '"'
    bullets = re.findall(r"^\\s*\\*[^\\*].*$", response, flags=re.MULTILINE)
    assert len(bullets) == 5


def test_quotation_bullets_and_end_all_compose():
    prompt = (
        "Your answer must contain exactly 2 bullet points. Use the markdown bullet points such as:\n"
        "* This is point 1. \n* This is point 2 "
        "Finish your response with this exact phrase Any other questions?. No other words should follow this phrase. "
        "Wrap your entire response with double quotation marks."
    )
    out = solve(_env(prompt))
    assert out["status"] == "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS"
    response = out["response"]
    assert len(re.findall(r"^\\s*\\*[^\\*].*$", response, flags=re.MULTILINE)) == 2
    assert response.strip().strip('"').lower().endswith("any other questions?")


def test_existence_forbidden_overlap_uses_boundary_safe_carrier():
    prompt = (
        "Include keywords ['ta'] in the response. "
        "Do not include keywords ['ta', 'tax'] in the response."
    )
    out = solve(_env(prompt))
    assert out["status"] == "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS"
    response = out["response"].lower()
    assert "ta" in response
    assert re.search(r"\\bta\\b", response) is None
    assert re.search(r"\\btax\\b", response) is None
