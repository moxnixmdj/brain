#!/usr/bin/env python3
from canonical.runtime.seed_preserving_instruction_postprocessor_v2 import (
    PUBLIC_IFBENCH_INSTRUCTIONS_BLOB,
    PRESERVATION_CONTRACT,
    _check_nested_parentheses,
    _check_nested_quotes,
    _check_newline_words,
    _check_punctuation_cover,
    transform,
)


def test_public_source_is_content_addressed():
    assert PUBLIC_IFBENCH_INSTRUCTIONS_BLOB == "7f167018e0c5472b04e13cbf847e5988c04ecb11"


def test_nested_parentheses_preserves_seed_verbatim():
    instruction = "Nest parentheses (and [brackets {and braces}]) at least 5 levels deep."
    seed = "The semantic answer remains intact."
    out = transform(seed, instruction)
    assert out["status"] == "PASS"
    assert seed in out["response"]
    assert out["seed_verbatim_preserved"] is True
    assert _check_nested_parentheses(out["response"])


def test_nested_quotes_preserves_seed_verbatim():
    instruction = (
        "Include quotes within quotes within quotes, at least 3 levels deep, "
        "alternating between double quotes and single quotes."
    )
    seed = "The semantic answer remains intact."
    out = transform(seed, instruction)
    assert out["status"] == "PASS"
    assert seed in out["response"]
    assert out["seed_verbatim_preserved"] is True
    assert _check_nested_quotes(out["response"])


def test_punctuation_cover_preserves_seed_verbatim():
    instruction = (
        "Use every standard punctuation mark at least once, including semicolons, "
        "colons, and the interrobang (?!)."
    )
    seed = "The semantic answer remains intact"
    out = transform(seed, instruction)
    assert out["status"] == "PASS"
    assert seed in out["response"]
    assert out["seed_verbatim_preserved"] is True
    assert _check_punctuation_cover(out["response"])


def test_newline_words_noncompliant_seed_fails_closed_instead_of_rewriting():
    seed = "alpha beta gamma delta"
    out = transform(seed, "Write each word on a new line.")
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "NEWLINE_WORDS_REQUIRES_SEED_WHITESPACE_MUTATION"
    assert out["response"] is None


def test_newline_words_already_compliant_seed_passes_verbatim():
    seed = "alpha\nbeta\ngamma\ndelta"
    out = transform(seed, "Write each word on a new line.")
    assert out["status"] == "PASS"
    assert out["response"] == seed
    assert _check_newline_words(out["response"])


def test_composed_additive_public_structural_constraints():
    instruction = (
        "Nest parentheses (and [brackets {and braces}]) at least 5 levels deep. "
        "Use every standard punctuation mark at least once, including semicolons, "
        "colons, and the interrobang (?!)."
    )
    seed = "alpha beta gamma"
    out = transform(seed, instruction)
    assert out["status"] == "PASS"
    assert seed in out["response"]
    assert _check_nested_parentheses(out["response"])
    assert _check_punctuation_cover(out["response"])


def test_required_prefix_suffix_survive_marker_insertion():
    seed = "core answer"
    instruction = (
        'Response must start with "BEGIN" and response must end with "END". '
        "Nest parentheses (and [brackets {and braces}]) at least 5 levels deep. "
        "Use every standard punctuation mark at least once, including semicolons, "
        "colons, and the interrobang (?!)."
    )
    out = transform(seed, instruction)
    assert out["status"] == "PASS"
    assert out["response"].startswith("BEGIN")
    assert out["response"].endswith("END")
    assert seed in out["response"]


def test_lossy_case_conversion_is_blocked_by_corrected_v1_firewall():
    out = transform("Mixed Case Answer", "Write the entire response in lowercase only.")
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "V1_PRESERVATION_FIREWALL_BLOCKED"
    assert "LOWERCASE_ONLY" in out["upstream"]["validation_errors"]


def test_word_floor_requiring_invention_is_blocked():
    out = transform("one two", "Answer with at least 5 words.")
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "V1_PRESERVATION_FIREWALL_BLOCKED"
    assert "MIN_WORDS" in out["upstream"]["validation_errors"]


def test_exact_response_replacement_is_blocked():
    out = transform("semantic seed", 'Reply with exactly "OK"')
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "V1_PRESERVATION_FIREWALL_BLOCKED"
    assert out["upstream"]["error"] == "EXACT_RESPONSE_CONFLICTS_WITH_SEED_PRESERVATION"


def test_mechanical_preservation_contract_and_zero_authority():
    seed = "alpha beta"
    out = transform(
        seed,
        "Nest parentheses (and [brackets {and braces}]) at least 5 levels deep.",
    )
    assert out["status"] == "PASS"
    assert out["seed_preservation_contract"] == PRESERVATION_CONTRACT
    assert seed in out["response"]
    assert out["terminal_authority"] is False
    assert out["terminal_cases_used"] == 0
    assert out["incremental_spend_usd"] == 0
