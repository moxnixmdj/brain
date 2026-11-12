"""What one lesson actually buys, measured on the shipped learner.

`file.question.taught_words.v1` is the one capability whose acceptance predicate recomputes the
learned program instead of checking that a file was written. This file pins the honest reading of
its result:

  * one lesson adds **one word**, and that word composes with everything already known, so requests
    nobody showed become answerable and are answered correctly;
  * it adds **no operator**. An operation outside the built-in parts is refused however many
    demonstrations are supplied, because a lesson selects among operations rather than inventing
    one.

The second half is the part that matters. It is what makes "give it one try everywhere" a statement
about vocabulary and not about capability.
"""
from __future__ import annotations

import sys
from pathlib import Path

# parents[2] is the repository root. parents[1] pointed the live-state check at
# canonical/canonical/astra_runtime/state, which cannot exist, so "wrote nothing into the tree"
# passed vacuously.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from one_lesson_buys_a_word_not_an_operator_probe_20261112 import (  # noqa: E402
    LIVE_LESSON,
    UNTEACHABLE,
    run,
)

from canonical.runtime import taught_words_v1 as taught  # noqa: E402

_CACHE: dict = {}


def _report() -> dict:
    if "r" not in _CACHE:
        _CACHE["r"] = run()
    return _CACHE["r"]


def test_one_lesson_teaches_exactly_one_word():
    lesson = _report()["lesson"]
    assert lesson["examples_given"] == 2, "a one-example lesson is refused by design"
    assert lesson["words_added_to_the_lexicon"] == 1
    assert lesson["taught_sentence_ok"] is True


def test_the_lesson_generalizes_to_requests_nobody_showed():
    s = _report()["summary"]
    assert s["held_out_unlocked"] == 12
    assert s["held_out_correct"] >= 11


def test_it_never_answers_one_of_them_wrongly():
    """Refusing is allowed. Guessing is not — that is the whole difference from a rubber stamp."""
    s = _report()["summary"]
    assert s["held_out_wrong"] == 0


def test_a_composition_nobody_showed_is_right():
    """`unique` was learned in a different lesson from `records`. They compose anyway."""
    composition = _report()["composition_nobody_showed"]
    assert composition["ok"] is True
    assert composition["value"] == 18
    assert composition["correct"] is True
    assert "record" in composition["meanings"] or "records" in composition["meanings"]


def test_an_operator_the_learner_does_not_have_cannot_be_demonstrated():
    op = _report()["operator_that_cannot_be_taught"]
    assert op["request"] == UNTEACHABLE
    assert op["ok"] is False
    # `median` was this pin until its operator was added in code (the next round); `mode` has no
    # part and no lesson can create one.
    assert op["reason"] == "UNKNOWN_WORD:mode"


def test_the_lesson_adds_no_operator():
    s = _report()["summary"]
    assert s["operators_added_by_the_lesson"] == 0
    assert s["built_in_operator_parts"] == len(taught.PARTS)
    # Report the measured number rather than the prose. The module docstring and the registry
    # limitation both say fifteen; PARTS held fourteen until the median reducer was added as a
    # code change (A_NEW_PART_COSTS_CODE_ONE_LESSON_BUYS_THE_WORD_20261112_V1.md). It now
    # matches the prose the whole time.
    assert len(taught.PARTS) == 15


def test_a_lesson_with_one_example_is_set_aside_not_believed():
    one = _report()["lesson_with_one_example"]
    assert one["lexicon_is_empty"] is True
    assert [row["set_aside"] for row in one["set_aside"]] == ["TWO_EXAMPLE_FILES_NEEDED"]


def test_the_probe_ran_the_shipped_learner_and_wrote_nothing_into_the_tree():
    state = ROOT / "canonical" / "astra_runtime" / "state"
    assert not (state / taught.LIVE_LESSONS_NAME).exists()
    assert not (state / taught.LIVE_LEXICON_NAME).exists()
    assert LIVE_LESSON["sentence"].startswith("how many records")
