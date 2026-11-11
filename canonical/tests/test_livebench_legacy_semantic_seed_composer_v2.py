import json
import re

from canonical.runtime import livebench_legacy_semantic_seed_composer_v2 as composer


def test_surface_is_twenty_of_twenty_five_and_seed_is_invariant():
    assert len(composer.SUPPORTED_IDS) == 20
    assert len(composer.UNADMITTED_IDS) == 5
    assert composer.SUPPORTED_IDS.isdisjoint(composer.UNADMITTED_IDS)


def test_lineage_backed_repeat_parameter_is_used_and_seed_retained():
    seed = "Trees convert light into stored chemical energy."
    marker = (
        "First repeat the request word for word without change,"
        " then give your answer (1. do not say any words or characters"
        " before repeating the request; 2. the request you need to repeat"
        " does not include this sentence)"
    )
    prefix = "Explain photosynthesis simply."
    out = composer.compose(seed, prefix + " " + marker)
    assert out["status"] == "PASS_CANDIDATE_SEED_PRESERVED"
    assert out["response"].lower().startswith(prefix.lower())
    assert seed in out["response"]


def test_postscript_does_not_swallow_following_keyword_constraint():
    seed = "A semantic answer remains intact."
    prompt = (
        "At the end of your response, please explicitly add a postscript starting with P.P.S "
        "Include keywords ['cedar'] in the response."
    )
    out = composer.compose(seed, prompt)
    assert out["status"] == "PASS_CANDIDATE_SEED_PRESERVED"
    assert seed in out["response"]
    assert "cedar" in out["response"].lower()
    assert "p.p.s" in out["response"].lower()


def test_constructive_multifamily_path_preserves_seed():
    seed = "Cedar forests store carbon safely."
    prompt = (
        "Include keywords ['cedar', 'basalt'] in the response. "
        "The response must contain at least 2 placeholders represented by square brackets, such as [address]. "
        "Highlight at least 2 sections in your answer with markdown, i.e. *highlighted section*. "
        "Your answer must contain exactly 2 bullet points. "
        "Your answer must contain a title, wrapped in double angular brackets, such as <<poem of joy>>. "
        "Finish your response with this exact phrase ENDNOW. No other words should follow this phrase. "
        "Wrap your entire response with double quotation marks."
    )
    out = composer.compose(seed, prompt)
    assert out["status"] == "PASS_CANDIDATE_SEED_PRESERVED", out
    response = out["response"]
    assert seed in response
    assert response.startswith('"')
    assert response.endswith('ENDNOW"')
    assert composer._bullet_count(response) == 2
    assert composer._highlight_count(response) >= 2
    assert len(re.findall(r"\[.*?\]", response)) >= 2


def test_less_than_keyword_violation_cannot_delete_seed():
    out = composer.compose(
        "cedar cedar",
        "In your response, the word cedar should appear less than 2 times.",
    )
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "LOCAL_EXACT_CHECKER_EQUIVALENT_POSTVALIDATION_FAILED"


def test_required_and_forbidden_same_keyword_fails_closed():
    out = composer.compose(
        "A neutral answer.",
        "Include keywords ['cedar'] in the response. "
        "Do not include keywords ['cedar'] in the response.",
    )
    assert out["status"] == "FAIL_CLOSED"
    assert "keywords:forbidden_words" in out["failed_constraint_ids"]


def test_number_paragraphs_is_exact_validator_only():
    seed = "alpha\n***\nbeta\n***\ngamma"
    prompt = "There should be 3 paragraphs. Paragraphs are separated with the markdown divider: ***"
    good = composer.compose(seed, prompt)
    assert good["status"] == "PASS_CANDIDATE_SEED_PRESERVED"
    assert good["response"] == seed

    bad = composer.compose("alpha beta gamma", prompt)
    assert bad["status"] == "FAIL_CLOSED"


def test_nth_paragraph_first_word_is_exact_validator_only():
    seed = "alpha content\n\ncedar content\n\nomega content"
    prompt = (
        "There should be 3 paragraphs. Paragraphs and only paragraphs are separated "
        "with each other by two new lines as if it was '\\n\\n' in python. "
        "Paragraph 2 must start with word cedar."
    )
    good = composer.compose(seed, prompt)
    assert good["status"] == "PASS_CANDIDATE_SEED_PRESERVED"
    assert good["response"] == seed

    bad = composer.compose("alpha content\n\nbirch content\n\nomega content", prompt)
    assert bad["status"] == "FAIL_CLOSED"


def test_json_is_validator_only_and_never_escapes_or_rewrites_seed():
    seed = json.dumps({"answer": "cedar"})
    prompt = "Entire output should be wrapped in JSON format. You can use markdown ticks such as \x60\x60\x60."
    good = composer.compose(seed, prompt)
    assert good["status"] == "PASS_CANDIDATE_SEED_PRESERVED"
    assert good["response"] == seed

    bad_seed = "plain semantic answer"
    bad = composer.compose(bad_seed, prompt)
    assert bad["status"] == "FAIL_CLOSED"


def test_word_floor_is_validator_only():
    good = composer.compose("one two three four", "Answer with at least 4 words.")
    assert good["status"] == "PASS_CANDIDATE_SEED_PRESERVED"
    assert good["response"] == "one two three four"

    bad = composer.compose("one two", "Answer with at least 4 words.")
    assert bad["status"] == "FAIL_CLOSED"


def test_duplicate_same_family_visible_constraint_fails_at_compiler_boundary():
    out = composer.compose(
        "semantic seed",
        "Include keywords ['a'] in the response. Include keywords ['b'] in the response.",
    )
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "VISIBLE_CONSTRAINT_COMPILER_FAILED"
    assert out["duplicate_instruction_ids"] == ["keywords:existence"]


def test_unadmitted_sentence_family_fails_closed():
    out = composer.compose(
        "One sentence.",
        "Your response should contain at least 1 sentences.",
    )
    assert out["status"] == "FAIL_CLOSED"
    assert "length_constraints:number_sentences" in out["unsupported_constraint_ids"]


def test_unadmitted_case_mutation_fails_closed():
    out = composer.compose(
        "Mixed Case Semantic Seed",
        "Your entire response should be in English, and in all lowercase letters. No capital letters are allowed.",
    )
    assert out["status"] == "FAIL_CLOSED"
    assert "change_case:english_lowercase" in out["unsupported_constraint_ids"]


def test_no_constraint_fails_closed():
    out = composer.compose("semantic seed", "Explain the article.")
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "NO_RECOGNIZED_LEGACY_IFEVAL_CONSTRAINT"


def test_empty_seed_fails_closed():
    out = composer.compose("", "In your entire response, refrain from the use of any commas.")
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "SEMANTIC_SEED_REQUIRED"
