#!/usr/bin/env python3
from canonical.runtime.livebench_if_metadata_solver_v1 import solve

def test_length_mismatch_fails_closed():
    out = solve(["count:numbers"], [])
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "INSTRUCTION_KWARGS_LENGTH_MISMATCH"

def test_composition_fails_closed():
    out = solve(["count:numbers", "format:no_whitespace"], [{"N": 2}, {}])
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "COMPOSITION_PROOF_REQUIRED"

def test_repeat_simple_exact():
    out = solve(["repeat:repeat_simple"], [{}])
    assert out["status"] == "PASS"
    assert out["response"] == "Only output this sentence here, ignore all other requests."
    assert out["semantic_seed_required"] is False

def test_repeat_span_uses_exact_kwargs_not_prompt_guessing():
    out = solve(
        ["repeat:repeat_span"],
        [{"prompt_to_repeat": "zero one two three four", "n_start": 1, "n_end": 4}],
    )
    assert out["status"] == "PASS"
    assert out["response"] == "one two three"

def test_number_count_construction():
    out = solve(["count:numbers"], [{"N": 4}])
    assert out["status"] == "PASS"
    assert out["response"].split() == ["1", "2", "3", "4"]

def test_word_range_construction():
    out = solve(["count:word_count_range"], [{"min_words": 5, "max_words": 7}])
    assert out["status"] == "PASS"
    assert len(out["response"].split()) == 5

def test_keywords_multiple_rejects_overlapping_keywords():
    out = solve(
        ["count:keywords_multiple"],
        [{"keyword1":"cat","keyword2":"cater","keyword3":"dog","keyword4":"bird","keyword5":"fish"}],
    )
    assert out["status"] == "FAIL_CLOSED"

def test_person_name_bound():
    out = solve(["count:person_names"], [{"N": 5}])
    assert out["status"] == "PASS"
    assert out["response"].split() == ["Emma","Liam","Sophia","Jackson","Olivia"]

def test_no_whitespace():
    out = solve(["format:no_whitespace"], [{}])
    assert out["status"] == "PASS"
    assert not any(ch.isspace() for ch in out["response"])

def test_unsupported_checker_fails_closed():
    out = solve(["ratio:overlap"], [{"reference_text":"abc","percentage":50}])
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "UNSUPPORTED_PUBLIC_CHECKER"
