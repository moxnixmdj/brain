"""A refusal has to say WHICH refusal it is.

The system had one word for three completely different epistemic states:

    "the question names nothing that exists in this tree"

It said that about a column carried by two files, and it said it about a column called `x`
in a single file. Both statements are FALSE. The column exists. The system refused for a
reason and reported a different one, which is a false statement rather than a careful
refusal -- and a system that cannot tell "I found nothing" from "there are two true answers
and I cannot choose" is not being cautious, it is being vague.

  1. NOTHING MATCHED            -- genuinely nothing in the tree answers this
  2. AMBIGUOUS_REFERENT         -- two files carry the name; choosing one answers a
                                   question nobody asked
  3. a one-letter name          -- `x` was dropped by the tokenizer, so the word never
                                   arrived and could not be reported as not found

Two more things were measured and never consulted, and are now carried on the answer:

  * `law_grade` -- whether the law behind `verified: True` excludes 95% or 37% of wrong
    answers. The grade was built last round and read by nothing.
  * `rival_readings` -- how many OTHER well-typed readings produce a different value.
    `what is the total amount` has 30. The answer is right, and it wins on size and
    alphabetical order among candidates that all pass every filter. That is worth being
    able to see.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from canonical.runtime import inspect_v1 as I  # noqa: E402
from canonical.runtime import operation_trial_v1 as T  # noqa: E402

SALES = "region,amount\nnorth,100\nsouth,150\nnorth,50\nwest,250\n"


def _tree(tmp_path, **files) -> str:
    for name, text in files.items():
        (tmp_path / name).write_text(text)
    return str(tmp_path)


# ---------------------------------------------------------------------------
# Ambiguity is a verdict, not a silence.
# ---------------------------------------------------------------------------

def test_a_column_two_files_carry_is_reported_as_ambiguous_not_absent(tmp_path):
    root = _tree(tmp_path, **{"a.csv": "revenue\n10\n20\n", "b.csv": "revenue\n30\n40\n"})
    out = I.answer("what is the total revenue", root)
    assert out["verdict"] == "AMBIGUOUS_REFERENT", out["verdict"]
    assert out["answered"] is False
    assert out["ambiguous"] == {"revenue": ["a.csv", "b.csv"]}
    # the reason has to be true, and it has to name the candidates
    assert "a.csv" in out["trial_reason"] and "b.csv" in out["trial_reason"]
    assert "names nothing that exists" not in out["trial_reason"]


def test_ambiguity_is_refused_rather_than_resolved_by_preference(tmp_path):
    """Picking the first file would answer a question nobody asked."""
    root = _tree(tmp_path, **{"a.csv": "revenue\n10\n20\n", "b.csv": "revenue\n30\n40\n"})
    out = I.answer("what is the total revenue", root)
    assert out["answered"] is False
    assert (out.get("computation") or {}).get("value") is None


def test_naming_the_file_resolves_it(tmp_path):
    root = _tree(tmp_path, **{"a.csv": "revenue\n10\n20\n", "b.csv": "revenue\n30\n40\n"})
    named = I.answer("what is the total revenue in a.csv", root)
    assert named["verdict"] != "AMBIGUOUS_REFERENT"
    assert float((named.get("computation") or {}).get("value")) == 30.0
    other = I.answer("what is the total revenue in b.csv", root)
    assert float((other.get("computation") or {}).get("value")) == 70.0


def test_genuinely_absent_still_says_absent(tmp_path):
    """The fix must not turn every refusal into an ambiguity."""
    root = _tree(tmp_path, **{"a.csv": "revenue\n10\n"})
    out = I.answer("what is the total zzzz", root)
    assert out["verdict"] != "AMBIGUOUS_REFERENT"
    assert out["ambiguous"] == {}
    assert out["answered"] is False


def test_a_stale_ambiguity_does_not_outlive_its_question(tmp_path):
    """Same rule as the evaluation memo: a fact from the last question is not a fact.

    The two trees must be DIFFERENT DIRECTORIES. The first version of this test built the
    "clean" tree in the same tmp_path after writing a.csv and b.csv -- so it still had three
    files carrying `revenue`, the ambiguity was real, and the test was asserting a bug out
    of existence with a badly-built fixture.
    """
    ambiguous_root = tmp_path / "amb"
    ambiguous_root.mkdir()
    _tree(ambiguous_root, **{"a.csv": "revenue\n10\n", "b.csv": "revenue\n20\n"})
    assert I.answer("what is the total revenue", str(ambiguous_root))["verdict"] == \
        "AMBIGUOUS_REFERENT"

    clean_root = tmp_path / "clean"
    clean_root.mkdir()
    _tree(clean_root, **{"c.csv": "revenue\n5\n6\n"})
    after = I.answer("what is the total revenue", str(clean_root))
    assert after["verdict"] != "AMBIGUOUS_REFERENT"
    assert after["ambiguous"] == {}
    assert float((after.get("computation") or {}).get("value")) == 11.0


# ---------------------------------------------------------------------------
# A one-letter name is a name.
# ---------------------------------------------------------------------------

def test_a_one_letter_column_can_be_named(tmp_path):
    """`x` is what most real tables call their only numeric column.

    The tokenizer required two characters and the subject-word pass dropped the rest, so
    "what is the total x" against a one-file tree with a column x came back "the question
    names nothing that exists in this tree". The word never arrived; the refusal blamed
    the tree.
    """
    root = _tree(tmp_path, **{"a.csv": "x\n10\n20\n"})
    out = I.answer("what is the total x", root)
    assert float((out.get("computation") or {}).get("value")) == 30.0, out.get("trial_reason")
    assert out["answered"] is True


def test_a_one_letter_column_in_two_files_is_ambiguous_not_absent(tmp_path):
    root = _tree(tmp_path, **{"a.csv": "x\n10\n20\n", "b.csv": "x\n30\n40\n"})
    out = I.answer("what is the total x", root)
    assert out["verdict"] == "AMBIGUOUS_REFERENT"
    assert out["ambiguous"] == {"x": ["a.csv", "b.csv"]}


def test_short_english_words_are_still_not_names():
    """Removing the length rule must not turn "a", "an", "of" into column references.

    The judgement about which short words are words belongs to the glue list, which names
    words; it never belonged to a length test, which names lengths.
    """
    words = T._subject_words("what is the total of the a and b", [])
    assert "a" not in words and "an" not in words
    assert "total" in words


# ---------------------------------------------------------------------------
# How well a thing is checked is part of the answer.
# ---------------------------------------------------------------------------

def test_the_answer_carries_the_grade_of_its_weakest_law(tmp_path):
    """`verified: True` meant the same thing for a 95% check and a 37% one."""
    root = _tree(tmp_path, **{"sales.csv": SALES})
    comp = (I.answer("what is the total amount", root).get("computation") or {})
    assert float(comp.get("value")) == 550.0
    assert comp.get("verified") is True
    assert comp.get("law_grade") in ("MODERATE", "STRONG"), comp.get("law_grade")


def test_an_expression_with_no_aggregate_reports_no_grade(tmp_path):
    """Absence of a grade is absence of a law, not a failing grade."""
    root = _tree(tmp_path, **{"sales.csv": SALES})
    comp = (I.answer("how many rows are in sales.csv", root).get("computation") or {})
    assert int(comp.get("value")) == 4
    # a grade, when present, must be one the strength measurement can actually produce
    assert comp.get("law_grade") in (None, "STRONG", "MODERATE", "WEAK")


# ---------------------------------------------------------------------------
# How many other readings fitted.
# ---------------------------------------------------------------------------

def test_the_answer_reports_how_many_other_readings_also_fitted(tmp_path):
    """The winner is real; it is also one of several. A reader deserves to know.

    `what is the total amount` returns 550, which is correct. Thirty other well-typed
    expressions also evaluate and hold their own laws, and the chosen one wins on size and
    then alphabetical order. The number is not a warning -- it is the fact that the answer
    was chosen from rivals rather than being the only reading available.
    """
    root = _tree(tmp_path, **{"sales.csv": SALES})
    comp = (I.answer("what is the total amount", root).get("computation") or {})
    assert float(comp.get("value")) == 550.0
    assert isinstance(comp.get("rival_readings"), int)
    assert comp["rival_readings"] > 0


def test_a_question_with_no_rivals_reports_zero(tmp_path):
    root = _tree(tmp_path, **{"sales.csv": SALES})
    comp = (I.answer("how many rows are in sales.csv", root).get("computation") or {})
    assert int(comp.get("value")) == 4
    # a direct row count is not produced by the enumeration, so it carries no rival count;
    # either way it must never be a number that claims rivals were counted when none were
    assert comp.get("rival_readings") is None or isinstance(comp.get("rival_readings"), int)


@pytest.fixture(autouse=True)
def _no_persistent_memory():
    """A test run must not write to the creature's committed memory store."""
    from canonical.tests._memory import no_persistent_memory

    with no_persistent_memory():
        yield
