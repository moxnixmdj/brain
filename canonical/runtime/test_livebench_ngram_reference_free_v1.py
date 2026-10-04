#!/usr/bin/env python3
from canonical.runtime.livebench_ngram_reference_free_v1 import (
    _contract_holds_for_audit,
    construct,
    score_with_reference_for_audit,
)


def _assert_hits(base: str, reference: str, target: float):
    ok, c1, c2 = _contract_holds_for_audit(base, reference)
    assert ok and c1 and c2
    out = construct(base, target)
    assert out["status"] == "PASS_UNDER_CONTRACT"
    assert out["reference_text_read"] is False
    actual = score_with_reference_for_audit(out["response"], reference)
    assert target - 2 <= actual <= target + 2
    assert abs(actual - out["certified_percent"]) < 1e-12


def test_newline_flattening_72():
    _assert_hits(
        "Use induction to prove this claim. Consider a simple graph with vertices and edges.",
        "Use induction to prove this claim.\nConsider a simple graph with vertices and edges.",
        72,
    )


def test_high_overlap_93_without_raw_reference():
    _assert_hits(
        "Transformational Leadership improves engagement through autonomy.",
        "Transformational Leadership improves engagement\nthrough autonomy.",
        93,
    )


def test_low_overlap_6_without_raw_reference():
    _assert_hits(
        "For her art installation critics praised the inventive exhibit.",
        "For her art installation critics praised\nthe inventive exhibit.",
        6,
    )


def test_extra_visible_nonwhitespace_character_does_not_break_sufficient_contract():
    # C2 is one-way: the visible base may contain an extra character that the
    # reference does not. Exact equality would be unnecessarily strong.
    base = "prove it step by step.\u200b"
    reference = "prove it step by step."
    ok, c1, c2 = _contract_holds_for_audit(base, reference)
    assert ok and c1 and c2
    out = construct(base, 74)
    assert out["status"] == "PASS_UNDER_CONTRACT"
    actual = score_with_reference_for_audit(out["response"], reference)
    assert 72 <= actual <= 76


def test_contract_fails_if_reference_has_hidden_nonwhitespace_character():
    ok, c1, c2 = _contract_holds_for_audit("alpha beta", "alpha Ω beta")
    assert not ok
    assert not c2


def test_empty_base_fails_closed():
    out = construct("", 50)
    assert out["status"] == "FAIL_CLOSED"
    assert out["error"] == "BASE_TEXT_REQUIRED"
