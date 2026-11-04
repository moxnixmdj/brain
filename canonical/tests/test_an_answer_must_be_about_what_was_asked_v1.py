"""An answer that ignores the thing it was asked about is not an answer.

Every check in this system answered one question: IS THIS EXPRESSION SOUND? `holds()` asks
whether the value agrees with the expression's own law. The law grade asks how much of the
wrong-answer space that law excludes. Both can say yes while the expression answers a
different question than the one asked.

Measured on the door before this existed:

    what is the total amount times region
      terms      = ['total', 'amount', 'times', 'region']
      expression = double(count(sum(amount) by region))
      value      = 6        verified: True

Both data words present and accounted for. The expression counts the three region groups
and doubles the count. It never multiplies anything and never reads a single amount. It
passed every check because `double(3)` really is 6 and nothing asked what it was 6 OF.

`what is the total amount divided by how many regions` is the same shape -- `half(count)`
= 1.5 -- and so is the 1.5 that two rounds of cross-answer work were built on. It was
never a division.

THE DERIVED TEST, AND WHY THE OBVIOUS ONE WAS REJECTED. `times` and `divided` are binary
in English and were filed into the UNARY operator lexicon. Deleting them there makes the
door refuse instead of fabricate -- better, and still me typing a list of which words are
binary. Two rounds of this work have already been spent removing exactly that reflex.

So the check does not ask what a word means. It asks whether the answer DEPENDS on the
thing the question names: change every value in that column, and an answer about that
column must move.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from canonical.runtime import answer_ledger_v1 as L  # noqa: E402
from canonical.runtime import inspect_v1 as I  # noqa: E402
from canonical.runtime import referent_dependence_v1 as D  # noqa: E402

SALES = "region,amount\nnorth,100\nsouth,150\nnorth,50\nwest,250\n"


def _tree(tmp_path, **files) -> str:
    for name, text in files.items():
        (tmp_path / name).write_text(text)
    return str(tmp_path)


def _ask(question):
    def go(root):
        inner = I.answer(question, root).get("computation") or {}
        value = inner.get("value")
        return None if value is None else str(value)
    return go


@pytest.fixture(autouse=True)
def _clean():
    """A TEST RUN MUST NOT MUTATE THE COMMITTED EXPERIENCE STORE.

    Measured before this fixture existed: running the suite wrote 61 lines into
    canonical/runtime/state/experience_v1.json, so a CI run and a laptop run disagreed
    depending on what had already been recorded. Memory is a product behaviour; a test of
    the law must not change the product's memory to observe it.
    """
    from canonical.tests._memory import no_persistent_memory
    with no_persistent_memory():
        L.reset()
        yield
        L.reset()


# ---------------------------------------------------------------------------
# The defect itself.
# ---------------------------------------------------------------------------

def test_an_answer_that_never_reads_the_column_it_names_is_caught(tmp_path):
    """`double(count(sum(amount) by region))` = 6, and no amount affects it."""
    root = _tree(tmp_path, **{"sales.csv": SALES})
    out = I.answer("what is the total amount times region", root)
    assert out["depends_on_referent"]["verdict"] == "ignores", out["depends_on_referent"]
    assert out["depends_on_referent"]["column"] == "amount"


def test_the_same_half_a_count_is_caught(tmp_path):
    """The 1.5 that two rounds of ledger work were built on was `half(count(...))`."""
    root = _tree(tmp_path, **{"sales.csv": SALES})
    out = I.answer("what is the total amount divided by how many regions", root)
    assert out["depends_on_referent"]["verdict"] == "ignores"


def test_a_doubled_count_is_caught(tmp_path):
    """`what is the amount doubled` returned 8 -- double the ROW COUNT, not the total."""
    root = _tree(tmp_path, **{"sales.csv": SALES})
    out = I.answer("what is the amount doubled", root)
    assert out["depends_on_referent"]["verdict"] == "ignores"


# ---------------------------------------------------------------------------
# It must not fire on correct answers. Every case below was a real false positive
# at some point while this was being built.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("question", [
    "what is the total amount",
    "what is the average amount",
    "what is the largest amount",
    "what is the smallest amount",
    "what is the total amount in west",
    "what is the total amount per region",
])
def test_a_correct_answer_depends_on_the_column_it_names(tmp_path, question):
    root = _tree(tmp_path, **{"sales.csv": SALES})
    out = I.answer(question, root)
    assert out["depends_on_referent"]["verdict"] == "depends", \
        (question, out["depends_on_referent"])


@pytest.mark.parametrize("csv", [
    "region,amount\nnorth,7\nsouth,7\nnorth,7\nwest,7\n",      # the old fixed probe's value
    "region,amount\nnorth,0\nsouth,0\nnorth,0\nwest,0\n",
    "region,amount\nnorth,5\nsouth,5\nnorth,5\nwest,5\n",
])
def test_a_constant_column_still_depends(tmp_path, csv):
    """THE FALSE POSITIVE THAT SHIPPED INSIDE THE FIRST DRAFT.

    The probe was the constant 7. On a tree where every amount was already 7, replacing
    the column with 7 changed nothing, and THREE CORRECT ANSWERS were accused of ignoring
    the column they were entirely made of. The probe is now derived from the data so the
    perturbation is always real.
    """
    root = _tree(tmp_path, **{"sales.csv": csv})
    for question in ("what is the total amount", "what is the average amount"):
        out = I.answer(question, root)
        assert out["depends_on_referent"]["verdict"] == "depends", \
            (csv, question, out["depends_on_referent"])


def test_a_question_about_a_different_column_is_not_accused(tmp_path):
    """`how many regions` ignores `amount` -- correctly, because it never named amount."""
    root = _tree(tmp_path, **{"sales.csv": SALES})
    out = I.answer("how many regions", root)
    assert out["depends_on_referent"]["verdict"] == "uncheckable", out["depends_on_referent"]


def test_the_referent_comes_from_the_question_not_from_the_caller(tmp_path):
    """The check only applies when the question picks out exactly one numeric column."""
    root = _tree(tmp_path, **{"sales.csv": SALES})
    assert D.numeric_referent("what is the total amount", root) == "amount"
    # plural resolves to the header, as the door itself resolves it
    assert D.numeric_referent("how many amounts are there", root) == "amount"
    # a question naming no numeric column picks out nothing
    assert D.numeric_referent("how many regions", root) is None
    # and a question naming two is genuinely ambiguous, which is not this check's verdict
    # A question naming two numeric columns is genuinely ambiguous. This check must
    # not pick one and hold the answer to it -- a wrong pick would accuse a correct
    # answer of ignoring a column it was never asked about.
    two_dir = tmp_path / "two"
    two_dir.mkdir()
    two = _tree(two_dir, **{"t.csv": "amount,region_count\n10,1\n20,2\n"})
    assert D.numeric_referent("what is the total amount and region_count", two) is None


# ---------------------------------------------------------------------------
# The probe must not contaminate the memory it is protecting.
# ---------------------------------------------------------------------------

def test_a_probe_is_not_an_answer(tmp_path):
    """One question used to log THREE ledger entries, including the perturbed 7004.

    The ledger then reported a contradiction between a real answer and its own
    experiment. A probe is an experiment, not a claim.
    """
    root = _tree(tmp_path, **{"sales.csv": SALES})
    I.answer("what is the total amount", root)
    assert len(L.entries()) == 1, [e["value"] for e in L.entries()]


def test_the_probe_does_not_recurse(tmp_path):
    """The first version called answer() from inside answer() and never returned."""
    root = _tree(tmp_path, **{"sales.csv": SALES})
    out = I.answer("what is the total amount", root)
    assert out["depends_on_referent"]["verdict"] == "depends"


def test_the_check_is_skipped_when_nothing_was_computed(tmp_path):
    root = _tree(tmp_path, **{"sales.csv": SALES})
    out = I.answer("what is the total revenue", root)
    assert out["computation"] is None
    assert out["depends_on_referent"]["verdict"] == "not_applicable"


# ---------------------------------------------------------------------------
# The honest limit.
# ---------------------------------------------------------------------------

def test_a_non_numeric_referent_is_uncheckable_not_passing(tmp_path):
    """A text column cannot be perturbed into a different numeric answer.

    `how many regions` names a text column. Reporting it as `depends` would be a claim
    this check cannot support, and reporting it as `ignores` would be a false accusation.
    It says `uncheckable`, which is a third thing and the true one.
    """
    root = _tree(tmp_path, **{"sales.csv": SALES})
    out = I.answer("how many regions", root)
    assert out["depends_on_referent"]["verdict"] == "uncheckable"
    assert "not a numeric column" in out["depends_on_referent"]["why"] or \
           "exactly one numeric column" in out["depends_on_referent"]["why"]


def test_the_check_does_not_prove_the_answer_is_right():
    """It proves the answer is ABOUT what was asked, which is a different claim.

    A deliberately wrong constant that happens to move is not caught by this check --
    that is what `holds()` and the law grade are for. Stated as a test so nobody
    over-reads this one.
    """
    verdict = D.depends_on_column(
        "/nonexistent", "amount", lambda root: "1")
    assert verdict["verdict"] == "uncheckable"


# ---------------------------------------------------------------------------
# A MEASURED CONCLUSION OUTLIVES THE PROCESS THAT MEASURED IT.
#
# Before this, every measurement was in-process: `_CACHE` in decomposition_law_v1 was a
# dict that died with the interpreter, so a fresh process reported `cache: 0` and
# rediscovered `sum -> sum` and `mean -> nothing` forever. `answer()` is a pure function
# of (question, tree), so nothing it learned could change what it did next -- which is as
# static as code gets, and is why six rounds of checks were six rounds of the same check.
#
# The creature already had a persistent experience store with an e-process gate on it.
# Nothing on the answer path read it (zero references in inspect_v1, decomposition_law_v1,
# answer_ledger_v1, referent_dependence_v1). These tests prove the join works.
# ---------------------------------------------------------------------------

from canonical.runtime import answer_memory_v1 as M  # noqa: E402
from canonical.runtime import experience_v1 as E  # noqa: E402


def _store(tmp_path):
    return tmp_path / "experience.json"


def test_a_discovery_is_not_reused_on_thin_evidence(tmp_path):
    """Six observations is not enough. A shortcut has to be earned."""
    p = _store(tmp_path)
    for _ in range(6):
        M.remember_decomposition("sum", "sum", path=p)
    assert M.recall_decomposition("sum", path=p) == (False, None)


def test_a_discovery_is_reused_once_the_evidence_clears_the_gate(tmp_path):
    p = _store(tmp_path)
    for _ in range(10):
        M.remember_decomposition("sum", "sum", path=p)
    assert M.recall_decomposition("sum", path=p) == (True, "sum")


def test_a_non_decomposition_is_remembered_as_such_not_as_unknown(tmp_path):
    """`mean` does not decompose. That is a fact, and it must not be stored as 'no idea'."""
    p = _store(tmp_path)
    for _ in range(10):
        M.remember_decomposition("mean", None, path=p)
    assert M.recall_decomposition("mean", path=p) == (True, None)


def test_an_operator_never_measured_is_not_guessed(tmp_path):
    p = _store(tmp_path)
    for _ in range(10):
        M.remember_decomposition("sum", "sum", path=p)
    assert M.recall_decomposition("median", path=p) == (False, None)


def test_memory_survives_a_fresh_process(tmp_path):
    """The whole point. Written by one interpreter, read by another."""
    import subprocess
    import textwrap

    p = _store(tmp_path)
    for _ in range(10):
        M.remember_decomposition("median", None, path=p)

    script = textwrap.dedent(f"""
        import sys
        sys.path.insert(0, {str(pathlib.Path(__file__).resolve().parents[1])!r})
        from canonical.runtime import answer_memory_v1 as M
        print(M.recall_decomposition("median", path={str(p)!r}))
    """)
    out = subprocess.run([sys.executable, "-c", script],
                         capture_output=True, text=True, timeout=120)
    assert "(True, None)" in out.stdout, out.stdout + out.stderr


def test_the_store_is_not_written_by_a_test_run():
    """conftest.py turns persistence off. A test must not mutate product state.

    Measured before the fixture existed: the suite wrote dozens of lines into
    canonical/runtime/state/experience_v1.json, so CI and a laptop disagreed depending on
    what had already been recorded.
    """
    from canonical.runtime import decomposition_law_v1 as D
    assert D.REMEMBER is False


# ---------------------------------------------------------------------------
# AN ANSWER THAT IGNORES ITS REFERENT IS NOT ANSWERED.
#
# Last round shipped `depends_on_referent` and nothing read it: the fabricated answer came
# back verified=True, answered=True, COMPUTED -- identical in every field a caller looks
# at to a correct one. A distinction that changes no behaviour is a comment with a dict
# around it.
# ---------------------------------------------------------------------------

def test_ignoring_the_referent_changes_the_answer_not_just_a_field(tmp_path):
    root = _tree(tmp_path, **{"sales.csv": SALES})
    good = I.answer("what is the total amount", root)
    bad = I.answer("what is the total amount times region", root)

    assert good["answered"] is True and good["verdict"] == "COMPUTED"
    assert bad["answered"] is False
    assert bad["verdict"] == "REFERENT_NOT_READ", bad["verdict"]
    # the fabricated value is still reported -- it was computed -- but it is not an answer
    assert bad["computation"]["value"] == "6"


def test_uncheckable_does_not_block_the_answer(tmp_path):
    """"I could not test this" is not evidence against it."""
    root = _tree(tmp_path, **{"sales.csv": SALES})
    out = I.answer("how many regions", root)
    assert out["depends_on_referent"]["verdict"] == "uncheckable"
    assert out["answered"] is True


# ---------------------------------------------------------------------------
# Four false positives found while building this, each now a test.
# ---------------------------------------------------------------------------

def test_a_comparison_is_not_accused_of_ignoring_its_operand(tmp_path):
    """`yes`/`no` is ordinal; it cannot move gradually. It is still about `units`."""
    root = _tree(tmp_path, **{
        "inventory.csv": "item,units\nbolt,5\nnut,15\nbolt,7\n",
        "returns.csv": "item,units\nbolt,1\nnut,1\n",
    })
    out = I.answer("is the total units in returns.csv less than the total units "
                   "in inventory.csv", root)
    assert out["computation"]["value"] == "yes"
    assert out["depends_on_referent"]["verdict"] == "depends"


def test_a_selection_is_not_accused_of_ignoring_its_operand(tmp_path):
    """`north` is a LABEL. A uniform probe ties every row and leaves the argmin fixed."""
    root = _tree(tmp_path, **{"sales.csv": SALES})
    out = I.answer("which region has the smallest amount in sales.csv", root)
    assert out["computation"]["value"] == "north"
    assert out["depends_on_referent"]["verdict"] == "depends"


def test_the_referent_is_scoped_to_the_file_the_question_names(tmp_path):
    """Both files carry `units`; perturbing the wrong one accused a correct answer."""
    root = _tree(tmp_path, **{
        "inventory.csv": "item,units\nbolt,5\nnut,15\nbolt,7\n",
        "returns.csv": "item,units\nbolt,1\nnut,1\n",
    })
    for q in ("what is the total units in returns.csv",
              "what is the total units in inventory.csv"):
        out = I.answer(q, root)
        assert out["depends_on_referent"]["verdict"] == "depends", (q, out["depends_on_referent"])


def test_a_listing_is_uncheckable_not_accused(tmp_path):
    """`what is amount in sales.csv` answers `3 line(s)`; that is not a quantity."""
    root = _tree(tmp_path, **{"sales.csv": "region,amount\nnorth,100\nsouth,250\n"})
    out = I.answer("what is amount in sales.csv", root)
    assert out["answered"] is True
    assert out["depends_on_referent"]["verdict"] == "uncheckable"
