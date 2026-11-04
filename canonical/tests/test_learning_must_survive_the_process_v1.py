"""THE ACCEPTANCE TEST FOR "SENTIENT-LIKE, NOT STATIC".

Every previous round was measured by asking "does it catch a wrong answer". That is a test
of a DETECTOR, and a creature can pass it forever while never learning anything. The test
that actually distinguishes a learning system from static code is:

    ask something it cannot do, ask again, is it better?

Before this round the answer was no, and the reason was not that learning was missing. The
repository can already INDUCE an operator from worked examples -- narrowing a generated
family of composed primitives down to the one function that reproduces what it was shown,
refusing when the examples leave more than one standing. What was missing is that the
result lived in a module-level dict, so:

    acquire_from_examples("spreadish")     acquired: True
    same process                           aggregate_names() contains "spreadish"
    FRESH PROCESS                          does not

The creature learned and forgot. These tests are written against that specific failure.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest

from canonical.runtime import acquired_operator_memory_v1 as M
from canonical.runtime import inspect_v1 as I
from canonical.runtime import operator_acquisition_v1 as A
from canonical.runtime import value_algebra_v1 as V
from canonical.tests._memory import no_persistent_memory

REPO = str(__import__("pathlib").Path(__file__).resolve().parents[2])

#: Two worked examples that pin exactly ONE candidate out of the generated family.
#: `sum-max` reproduces both; nothing else does. Deliberately arithmetic nobody typed in.
SPREAD = [([1, 2, 3], 3), ([10, 20, 30], 30)]


@pytest.fixture(autouse=True)
def _clean():
    """Undo the vocabulary a test taught.

    `value_algebra_v1._AGGREGATES` is module-global, so an operator declared by one test is
    declared for every later test in the same process. Measured: the second test's `teach`
    came back `already_declared`, wrote nothing, and the test failed on a missing file --
    a leak that looked like a broken feature.
    """
    aggregates = dict(V._AGGREGATES)
    words = {k: set(v) for k, v in V._AGG_WORDS.items()}
    with no_persistent_memory():
        V._AGGREGATES.clear()
        V._AGGREGATES.update(aggregates)
        V._AGG_WORDS.clear()
        V._AGG_WORDS.update(words)
        yield
        V._AGGREGATES.clear()
        V._AGGREGATES.update(aggregates)
        V._AGG_WORDS.clear()
        V._AGG_WORDS.update(words)


def _fresh(script: str, *args) -> str:
    """Run in a NEW interpreter -- the only place a memory can be proved to persist."""
    body = textwrap.dedent(f"""
        import sys
        sys.path.insert(0, {REPO!r})
        {script}
    """)
    out = subprocess.run([sys.executable, "-c", body, *args],
                         capture_output=True, text=True, timeout=180)
    assert out.returncode == 0, out.stdout + out.stderr
    return out.stdout


# ---------------------------------------------------------------------------
# THE DEMONSTRATION IS STORED, NOT THE FUNCTION.
# ---------------------------------------------------------------------------

def test_an_induced_operator_survives_a_fresh_process(tmp_path):
    """The whole point. Induced in one process, present in the next."""
    store = tmp_path / "ops.json"
    taught = M.teach("spreadv", {"spreadv"}, SPREAD, path=store)
    assert taught["acquired"] is True
    assert taught["arithmetic"] == "sum(v)-max(v)"

    seen = _fresh("""
        from canonical.runtime import acquired_operator_memory_v1 as M
        from canonical.runtime import value_algebra_v1 as V
        store = sys.argv[1]
        print("BEFORE", "spreadv" in V.aggregate_names())
        M.restore(path=store)
        print("AFTER", "spreadv" in V.aggregate_names())
    """, str(store))
    assert "BEFORE False" in seen
    assert "AFTER True" in seen


def test_the_stored_operator_is_re_derived_not_replayed(tmp_path):
    """What is stored is the DEMONSTRATION. Nothing executable is written to disk.

    Persisting the candidate's `fn` would be arbitrary code from a JSON file. It is also
    unnecessary: at the moment of acquisition the examples already pin one function, so
    storing the examples stores everything needed -- and re-deriving runs the gates again.
    """
    store = tmp_path / "ops.json"
    M.teach("spreadv", {"spreadv"}, SPREAD, path=store)

    import json
    blob = store.read_text()
    assert "lambda" not in blob and "def " not in blob
    stored = json.loads(blob)["taught"]["spreadv"]
    assert stored["examples"] == [[[1.0, 2.0, 3.0], 3.0], [[10.0, 20.0, 30.0], 30.0]]
    # the arithmetic is recorded as an identity, not as a callable
    assert stored["arithmetic"] == "sum(v)-max(v)"


def test_a_refused_acquisition_is_not_remembered(tmp_path):
    """A refusal has no operator behind it. Storing the attempt would be a cache that lies."""
    store = tmp_path / "ops.json"
    # `2` for both [1,2,3] and [10,20,30] leaves three candidates standing
    refused = M.teach("medianv", {"medianv"}, [([1, 2, 3], 2), ([10, 20, 30], 20)], path=store)
    assert refused["acquired"] is False
    assert refused["reason"] == "ambiguous"
    assert M.recall(path=store) == []


def test_a_taught_operator_that_stops_deriving_is_reported_not_trusted(tmp_path):
    """An operator whose evidence no longer identifies a function must not load anyway."""
    store = tmp_path / "ops.json"
    M.teach("weakv", {"weakv"}, SPREAD, path=store)
    state = M._load(store)
    # corrupt the demonstration: these examples leave many candidates standing
    state["taught"]["weakv"]["examples"] = [[[1.0, 2.0, 3.0], 6.0]]
    M._save(state, store)

    # be a FRESH process for this vocabulary: the operator must genuinely be absent, or
    # restore short-circuits on `already_declared` and never examines the evidence at all
    V._AGGREGATES.pop("weakv", None)
    V._AGG_WORDS.pop("weakv", None)
    assert "weakv" not in V.aggregate_names()

    out = M.restore(path=store)
    assert "weakv" not in out["restored"]
    assert any(f["kind"] == "weakv" for f in out["failed"]), out


# ---------------------------------------------------------------------------
# THE FALSIFIABLE ACCEPTANCE CRITERION.
# ---------------------------------------------------------------------------

def test_the_same_question_asked_twice_does_not_fail_the_same_way(tmp_path):
    """ASK, TEACH, ASK AGAIN. The second attempt must be better than the first.

    This is the measurement that no amount of detector work could ever move. It is the
    difference between code that can check answers and a system that can acquire a way to
    give one.
    """
    store = tmp_path / "ops.json"
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "sales.csv").write_text("region,amount\nnorth,100\nsouth,150\nnorth,50\nwest,250\n")

    first = I.answer("what is the spreadv amount", str(tree))
    assert first["answered"] is False
    assert "spreadv" in first["unresolved_terms"]

    M.teach("spreadv", {"spreadv"}, SPREAD, path=store)
    M.restore(path=store)

    second = I.answer("what is the spreadv amount", str(tree))
    assert second["answered"] is True
    assert second["unresolved_terms"] == []
    assert second["computation"]["value"] == "300"


def test_the_door_restores_taught_vocabulary_by_itself(tmp_path, monkeypatch):
    """The door must not need a caller to remember what the creature learned."""
    store = tmp_path / "ops.json"
    M.teach("spreadv", {"spreadv"}, SPREAD, path=store)
    monkeypatch.setattr(M, "DEFAULT_STATE", str(store))
    M._STATE_CACHE.clear()
    I._RESTORED = False  # simulate a process that has not restored yet
    V._AGGREGATES.pop("spreadv", None)
    V._AGG_WORDS.pop("spreadv", None)
    assert "spreadv" not in V.aggregate_names()

    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "sales.csv").write_text("region,amount\nnorth,100\nsouth,150\nnorth,50\nwest,250\n")
    out = I.answer("what is the spreadv amount", str(tree))
    assert out["computation"]["value"] == "300"


# ---------------------------------------------------------------------------
# THE RULE THAT KEEPS THIS FROM BECOMING A WORD TABLE.
# ---------------------------------------------------------------------------

def test_a_word_alone_still_acquires_nothing():
    """A hand-typed word table was rejected three times, and this does not smuggle it back."""
    out = A.acquire("spreadv", {"spreadv"})
    assert out["acquired"] is False
    assert out["reason"] == "no_example"
    assert V._AGGREGATES.get("spreadv") is None


def test_learning_a_new_name_for_an_old_function_is_refused():
    """`sum` is already declared; teaching it under a new name is not a new capability."""
    out = A.acquire_from_examples("brandnew", {"brandnew"}, [([1, 2, 3], 6), ([10, 20, 30], 60)])
    assert out["acquired"] is False
    assert out["reason"] == "already_declared"
