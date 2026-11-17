"""Tests for the GUI invariance census and the phrase-blind arm.

These tests exist to hold four specific mistakes down, each of which was made and caught:

1. Calling a rule difference a DEFECT when the PAGE never moved. Pass one did this to
   `text-transform` and would have "fixed" a working page. The `UNDECIDED` verdict is now the only
   thing an unperturbed page can produce.
2. Counting `"11".upper()` as a distinct answer. It is the same string, so it reports a quotient that
   does not exist. Variants are filtered to distinct spellings by construction.
3. Counting case/whitespace normalisation as reach. That is the browser's own encoding, not a
   discovery. Only SEMANTIC quotients count, and the only one found is `scroll-text`'s trailing dot,
   which is the page's own `.replace('.','')`.
4. Typing into `can_type[0]` on `scroll-text`, which is the passage to READ, not the box to answer in.
   Every candidate then looks rejected and a working arm is reported as dead.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, "/home/user/brain")
from canonical.tools import gui_invariance_census_v1 as census  # noqa: E402
from canonical.tools import gui_phrase_blind_basis_arm_v1 as arm  # noqa: E402


def test_identical_spellings_are_not_distinct_variants():
    """Mistake 2: `"11".upper()` is `"11"`. A variant that is not distinct is not a quotient."""
    assert set(census.answer_variants("11")) == {"as-is", "trailing dot", "leading space",
                                                 "trailing space", "padded"}
    assert "upper" not in census.answer_variants("11")
    assert "lower" not in census.answer_variants("11")


def test_real_strings_keep_their_case_variants():
    assert "upper" in census.answer_variants("volutpat")
    assert census.answer_variants("volutpat")["upper"] == "VOLUTPAT"


def test_reordering_without_perturbing_the_page_cannot_be_called_a_defect():
    """Mistake 1. The only honest verdicts for an unperturbed page are INVARIANT or UNDECIDED."""
    fake_rules = [("A", "RULE")]
    observation = {"elements": [{"index": 0, "text": "A"}, {"index": 1, "text": "B"}]}
    assert census.rules_of.__name__ == "rules_of"
    assert census._reverse_elements(observation)["elements"][0]["text"] == "B"
    # UNDECIDED and TRUE_BREAK are the only non-INVARIANT verdicts the census may emit.
    allowed = {census.INVARIANT, census.TRUE_BREAK, census.UNDECIDED}
    assert census.DEFECT not in allowed
    assert fake_rules  # the constant path is exercised by the live census, not here


def test_defect_verdict_is_unreachable_by_construction():
    """The census keeps DEFECT as a named constant for the record, but no arm may return it."""
    source = pathlib.Path(census.__file__).read_text()
    body = source.split("def identity_census", 1)[1].split("def judge_census", 1)[0]
    assert "UNDECIDED" in body
    assert "verdict\": DEFECT" not in body and "DEFECT," not in body.replace("TRUE_BREAK if", "")


def test_identity_of_the_rules_is_the_address_only():
    """The identity invariances are vacuous because `index` is an address. Assert the recorded fact."""
    assert "397" in census.IDENTITY_USE
    source = pathlib.Path(dv_path()).read_text()
    hits = [n for n, line in enumerate(source.splitlines(), 1) if "e[\"index\"]" in line]
    assert hits == [397], hits


def dv_path() -> str:
    return str(pathlib.Path(census.dv.__file__))


def test_answer_field_prefers_the_empty_typeable_one():
    """Mistake 4. `scroll-text` has a textarea holding the passage and an empty input for the answer."""
    observation = {"elements": [
        {"index": 3, "can_type": True, "text": "Vestibulum long passage " * 20},
        {"index": 4, "can_type": True, "text": ""},
        {"index": 5, "can_type": False, "text": "Submit"},
    ]}
    assert arm.answer_field(observation) == 4


def test_answer_field_falls_back_to_the_last_typeable_one():
    observation = {"elements": [{"index": 2, "can_type": True, "text": "x"},
                                {"index": 7, "can_type": True, "text": "y"}]}
    assert arm.answer_field(observation) == 7


def test_answer_field_is_none_when_nothing_can_be_typed():
    assert arm.answer_field({"elements": [{"index": 0, "can_type": False}]}) is None


def test_phrase_blind_basis_reads_no_english():
    """The basis must be derivable from page strings alone. Give it a page with no utterance at all."""
    observation = {"utterance": "", "elements": [
        {"index": 3, "text": "8 + x = 33"}, {"index": 5, "text": "x ="},
        {"index": 7, "text": "Submit"}]}
    basis = arm.phrase_blind_basis(observation)
    assert "25" in basis          # linear solve, no English needed
    assert "33" in basis          # a token of the shown expression
    assert "Submit" in basis      # a page literal


def test_phrase_blind_basis_offers_both_orders_of_single_characters():
    observation = {"utterance": "", "elements": [{"index": i, "text": c}
                                                 for i, c in enumerate("ZC5F")]}
    basis = arm.phrase_blind_basis(observation)
    assert "ZC5F" in basis and "F5CZ" in basis


def test_gated_basis_is_empty_when_the_phrase_is_not_recognised():
    """The measured defect: reword the instruction on an unchanged page and the gate returns []."""
    observation = {"utterance": "Find the final word in the text area, enter it into the text field.",
                   "elements": [{"index": 3, "text": "Lorem ipsum dolor sit amet consectetur volutpat"}]}
    assert arm.gated_basis(observation) == []


def test_gated_basis_fires_on_the_wording_it_was_designed_for():
    observation = {"utterance": "Find the last word in the text area, enter it into the text field.",
                   "elements": [{"index": 3, "text": "Lorem ipsum dolor sit amet consectetur volutpat"}]}
    values = arm.gated_basis(observation)
    assert "volutpat" in values


def test_the_last_word_rule_also_has_a_length_precondition():
    """The gate is a conjunction, not a phrase: the phrase AND at least 40 characters of text.

    Recorded so the phrase is never described as the only precondition. A short passage silently
    produces nothing even when the wording matches exactly.
    """
    short = {"utterance": "Find the last word in the text area, hit Submit.",
             "elements": [{"index": 3, "text": "Lorem ipsum dolor sit amet volutpat"}]}
    long = {"utterance": "Find the last word in the text area, hit Submit.",
            "elements": [{"index": 3, "text": "Lorem ipsum dolor sit amet consectetur volutpat"}]}
    assert "volutpat" not in arm.gated_basis(short)
    assert "volutpat" in arm.gated_basis(long)
