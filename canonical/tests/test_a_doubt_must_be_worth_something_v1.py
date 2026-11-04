"""THE CIRCUIT BETWEEN NOTICING A DOUBT AND DOING SOMETHING ABOUT IT.

The system had every piece of a learning creature and no wires between them:

    ignorance_ledger_v1   82 persisted, expected-value-ranked gaps -- and the answer path
                          had never written to it
    operator_acquisition  can induce an operator AND name the example that would settle it
    acquired_operator_..  remembers a demonstration across processes

Measured before this: `what is the skew of amount` asked three times returned
PARTIALLY_GROUNDED three times and left the ledger byte-for-byte identical. Every doubt was
re-derived from nothing on the next call. The ledger had 82 gaps, 0 resolved, 3 ever helped
in 29 trials -- which is why its own docstring says rank() without feedback "is a guess
dressed up as a calculation". It was.

These tests are written against that, and they are deliberately about OUTCOMES, because a
ledger that cannot be told whether closing a gap helped is decoration with a formula.
"""

from __future__ import annotations

import pytest

from canonical.runtime import acquired_operator_memory_v1 as M
from canonical.runtime import ignorance_ledger_v1 as L
from canonical.runtime import ignorance_loop_v1 as C
from canonical.runtime import inspect_v1 as I
from canonical.runtime import value_algebra_v1 as V
from canonical.tests._memory import no_persistent_memory

SALES = "region,amount\nnorth,100\nsouth,150\nnorth,50\nwest,250\n"


@pytest.fixture(autouse=True)
def _clean(tmp_path, monkeypatch):
    """Every test gets its own ledger and its own vocabulary.

    Both are module-global / on-disk in production, so without this a test would be
    measuring whatever the previous test left behind -- which is the same defect this
    module exists to fix, one layer up.
    """
    aggregates = dict(V._AGGREGATES)
    words = {k: set(v) for k, v in V._AGG_WORDS.items()}
    ledger = str(tmp_path / "ledger.json")
    monkeypatch.setattr(L, "DEFAULT_STATE", ledger)
    monkeypatch.setattr(I, "_PENDING_GAPS", {})
    with no_persistent_memory():
        yield
        V._AGGREGATES.clear()
        V._AGGREGATES.update(aggregates)
        V._AGG_WORDS.clear()
        V._AGG_WORDS.update(words)
        I._PENDING_GAPS.clear()


def _tree(tmp_path):
    tree = tmp_path / "tree"
    tree.mkdir(exist_ok=True)
    (tree / "sales.csv").write_text(SALES)
    return str(tree)


# ---------------------------------------------------------------------------
# THE ANSWER PATH WRITES TO ITS OWN LEDGER.
# ---------------------------------------------------------------------------

def test_an_unanswerable_question_is_recorded_as_a_doubt(tmp_path):
    """Before this, asking and failing changed the ledger by nothing at all."""
    root = _tree(tmp_path)
    before = L.stats()
    out = I.answer("what is the skewv of amount", root)
    assert out["verdict"] == "PARTIALLY_GROUNDED"
    after = L.stats()
    assert after["gaps"] == before["gaps"] + 1, (before, after)


def test_asking_the_same_unanswerable_question_does_not_mint_new_gaps(tmp_path):
    """A doubt that keeps coming back is ONE doubt seen repeatedly, not many doubts."""
    root = _tree(tmp_path)
    I.answer("what is the skewv of amount", root)
    once = L.stats()["gaps"]
    for _ in range(3):
        I.answer("what is the skewv of amount", root)
    assert L.stats()["gaps"] == once


def test_a_question_that_answers_records_no_doubt(tmp_path):
    root = _tree(tmp_path)
    before = L.stats()["gaps"]
    out = I.answer("what is the total amount", root)
    assert out["answered"] is True
    assert L.stats()["gaps"] == before


# ---------------------------------------------------------------------------
# AND THE DOUBT CAN BE CLOSED, BY ACTUAL EVIDENCE.
# ---------------------------------------------------------------------------

def test_the_loop_closes_a_doubt_when_the_question_is_really_answered(tmp_path):
    """THE MEASUREMENT THAT WAS IMPOSSIBLE BEFORE THIS ROUND.

    ask -> it fails and records a gap -> teach -> ask again -> answered -> gap closes and
    the ledger is told it HELPED. That last part is the only thing that teaches a ledger
    which kinds of ignorance matter.
    """
    root = _tree(tmp_path)
    store = tmp_path / "ops.json"

    I.answer("what is the skewv of amount", root)
    assert L.stats()["resolved"] == 0

    M.teach("skewv", {"skewv"}, [([1, 2, 3], 3), ([10, 20, 30], 30)], path=store)
    M.restore(path=store)

    out = I.answer("what is the skewv of amount", root)
    assert out["answered"] is True
    assert out["computation"]["value"] == "300"

    stats = L.stats()
    assert stats["resolved"] == 1, stats
    assert stats["ever_helped"] == 1, stats


def test_a_failed_attempt_lowers_the_value_but_does_not_close_the_gap(tmp_path):
    """A FAILED ATTEMPT IS NOT A CURE.

    Nearly shipped the opposite: `resolve` only sets `resolved` when `helped`, which looks
    like a bug and is exactly right. If closing a gap did not help, the doubt is STILL
    THERE -- all that changed is that we have learned this gap is worth less. Recording it as
    resolved would empty the ledger of precisely the gaps it should be chasing.

    The existing `test_failed_attempt_leaves_it_open` caught the change; this test pins the
    reasoning so it cannot come back.
    """
    out = C.credit_if_answered("PARTIALLY_GROUNDED", "PARTIALLY_GROUNDED", "zork")
    assert out["helped"] is False
    stats = L.stats()
    assert stats["resolved"] == 0, "a failed attempt must not resolve the gap"
    assert stats["ever_helped"] == 0
    assert stats["tried"] == 1, "but it IS evidence, and evidence must be recorded"

    # and the evidence moved the ranking, which is the whole point of recording it
    gap = [g for g in L.rank(limit=20, include_resolved=True) if g["what"] == "zork"][0]
    untried = 0.5  # the ledger's prior for a gap nobody has tried
    assert L.value(gap) < untried / (1.0 + float(gap.get("cost") or 0.0)) + 1e-9


def test_helping_is_credited_only_from_a_real_answer(tmp_path):
    out = C.credit_if_answered("PARTIALLY_GROUNDED", "COMPUTED", "zork")
    assert out["helped"] is True
    assert L.stats()["ever_helped"] == 1


# ---------------------------------------------------------------------------
# THE LEDGER STAYS A LEDGER.
# ---------------------------------------------------------------------------

def test_noticing_the_same_gap_twice_does_not_inflate_the_target(tmp_path):
    C.notice_unanswered("zork", root="/r")
    C.notice_unanswered("zork", root="/r")
    assert L.stats()["gaps"] == 1


def test_an_unresolvable_word_records_nothing_to_rank(tmp_path):
    """Recording a doubt nobody can act on only makes the ranking noisier."""
    assert C.notice_unanswered("   ") is None
    assert L.stats()["gaps"] == 0


def test_one_root_does_not_shadow_another(tmp_path):
    """The ledger keys on (what x why); two roots are two different gaps."""
    C.notice_unanswered("zork", root="/a")
    C.notice_unanswered("zork", root="/b")
    assert L.stats()["gaps"] == 2
