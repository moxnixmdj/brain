"""Twelve demonstrations buy nothing; sixteen lines of code buy the capability.

Round 8 showed one lesson teaches a word and `median` is refused forever. This pins the price of
that claim: the same twelve lessons are offered to the shipped learner and set aside one by one with
`NO_OPERATION_I_CAN_PERFORM_GIVES_THESE_ANSWERS`, and adding one reducer — `median` — makes every
one of them readable.

Two properties are load-bearing and are tested first, because the whole comparison collapses without
them:

  * none of the fourteen shipped parts can produce any lesson's stated answer, so "the learner
    cannot read these lessons" is about the algebra and not about a malformed lesson;
  * the shipped module is untouched — `median` is not in `taught_words_v1.PARTS` — so the receipt
    that binds its adapter hash still binds.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from twelve_lessons_buy_nothing_one_part_buys_it_probe_20261112 import (  # noqa: E402
    MEDIAN,
    NotPerformable,
    TEXTS,
    _lessons,
    median_of,
    run,
    run_extended,
)

from canonical.runtime import taught_words_v1 as taught  # noqa: E402

_CACHE: dict = {}


def _report() -> dict:
    if "r" not in _CACHE:
        _CACHE["r"] = run()
    return _CACHE["r"]


def test_the_shipped_algebra_is_untouched():
    assert MEDIAN not in taught.PARTS
    assert len(taught.PARTS) == 14


def test_no_shipped_operation_produces_any_lesson_answer():
    """Without this the comparison is about arithmetic coincidences, not about the operator space."""
    assert _report()["without_the_part"]["no_operation_fits_the_stated_answers"] is True
    for sentence, examples in _lessons():
        assert taught.candidates(sentence, examples) == [], sentence


def test_twelve_lessons_teach_no_word_at_all():
    a = _report()["without_the_part"]
    assert a["lessons_set_aside"] == 12
    assert a["reasons"] == ["NO_OPERATION_I_CAN_PERFORM_GIVES_THESE_ANSWERS"]
    assert a["lexicon_words"] == 0
    assert a["ok"] is False


def test_the_refusal_names_the_one_word_it_is_missing():
    """Not `what`, not `numbers` — those are known. `median` is the gap."""
    assert _report()["without_the_part"]["reason"] == "UNKNOWN_WORD:median"


def test_one_part_makes_every_lesson_readable():
    b = _report()["with_the_part"]
    assert b["lessons_with_exactly_one_reading"] == 12
    assert all(b["lessons"])


def test_the_part_agrees_with_an_independent_recomputation():
    b = _report()["with_the_part"]
    assert b["all_agree"] is True
    for name, text in TEXTS.items():
        assert b["answers"][name] == median_of(text) == int(sorted(
            int(t) for t in text.split()
        )[len(text.split()) // 2])


def test_the_part_refuses_what_it_cannot_do():
    """It is a part, not a licence: median of text, or of lines, is refused rather than approximated."""
    for parts in ({MEDIAN}, {MEDIAN, "lines"}, {MEDIAN, "numbers", "unique"}):
        try:
            run_extended(parts, TEXTS["n1"])
        except NotPerformable:
            continue
        raise AssertionError("the part answered outside its domain: %r" % (sorted(parts),))


def test_the_price_is_a_handful_of_lines():
    s = _report()["summary"]
    assert s["capability_bought_by_lessons"] is False
    assert s["capability_bought_by_code"] is True
    assert 0 < s["code_lines"] <= 25
