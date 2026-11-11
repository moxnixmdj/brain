"""A skill taught with one word must survive its synonyms.

THE DEFECT THIS PINS (measured 2026-11-09)
------------------------------------------
The only compiled skill in the permanent store was taught as "how many unique lines in ?".
Recall HIT on "unique" and MISSED on "distinct" and "different" -- the same intent in three
sentences, all of which the tree's own `computer_env_v1.query_kind` calls `uniquelines`.

The store was a paraphrase-intolerant SPECIALIST, which is the failure PolySkill (ICLR 2026)
measures across web agents: specialist skills reuse at <4-31% across sites because the
concrete surface is encoded and the abstract goal is not. The abstraction already existed in
this tree; the store simply did not read it.

FOUR SEPARATE GATES each dropped the paraphrase, and each was found by measuring rather than
reading:
  1. `_candidate_skills_for_words` indexes by raw WORD, so the skill never became a
     candidate. (An intent check downstream was therefore unreachable.)
  2. a second copy of the skeleton test inside `recall_and_execute_workflow` dropped the
     candidate that gate 1 had been fixed to admit.
  3. `bind_goal_parameters` matched a regex with the literal adjective frozen into it.
  4. the intent was built from a SORTED BAG OF WORDS ("different how lines many ..."),
     which `query_kind` reads as plain `lines` -- so "different" was still dropped after
     gates 1-3 were fixed, while "distinct" worked by luck of alphabetical order.

The lesson recorded: a filter that cannot be reached is not a filter, and a gate duplicated
in two places will be patched in one of them.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sqlite3
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as C

_REAL_STORE = pathlib.Path(__file__).resolve().parents[1] / "astra_runtime" / "tmp" / "compiled_workflows_v1.sqlite"


_BASE = pathlib.Path(__file__).resolve().parents[2] / "canonical" / "astra_runtime" / "tmp"


@pytest.fixture()
def store():
    """A scratch COPY of the shipped skill store.

    Copying the database FILE rather than re-inserting its row is deliberate: a
    hand-reconstructed row failed while the identical row in its original file worked,
    which means something outside the row (a pragma, a companion table) carries part of
    the contract. Copying the file copies the contract.
    """
    if not _REAL_STORE.exists():
        pytest.skip("the shipped skill store is not present")
    work = pathlib.Path(tempfile.mkdtemp(prefix="syn_", dir=str(_BASE)))
    db = work / "skills.sqlite"
    C._WORKFLOW_MEM_CACHE.clear()
    C._WORKFLOW_INDEX_CACHE.clear()
    shutil.copyfile(_REAL_STORE, db)
    yield db, work
    C._WORKFLOW_MEM_CACHE.clear()
    C._WORKFLOW_INDEX_CACHE.clear()
    shutil.rmtree(work, ignore_errors=True)


def _data(work):
    """Scratch file, named by its REPO-RELATIVE path.

    Absolute paths fail here for the same reason the fixture first failed: the door is
    rooted at the repository and its carrier stages work relative to that root. A test that
    asserts on an absolute path is testing a path shape the door does not use.
    """
    p = work / "data.txt"
    p.write_text("a\nb\na\n", encoding="utf-8")
    return str(p.relative_to(pathlib.Path(__file__).resolve().parents[2]))


def test_the_taught_word_still_matches(store):
    db, work = store
    assert C.recall_and_execute_workflow(
        f"how many unique lines in {_data(work)}", db_path=db) is not None


@pytest.mark.parametrize("synonym", ["distinct", "different"])
def test_a_synonym_of_the_same_intent_reaches_the_skill(store, synonym):
    """query_kind calls all of unique/distinct/different `uniquelines`, so all must reach."""
    db, work = store
    hit = C.recall_and_execute_workflow(
        f"how many {synonym} lines in {_data(work)}", db_path=db)
    assert hit is not None, f"a taught skill did not survive the synonym {synonym!r}"


@pytest.mark.parametrize("other", ["words", "bytes"])
def test_a_different_intent_is_never_reached(store, other):
    """The nearest world in which the widened match must NOT fire.

    Widening a skill's recognition until it answers the wrong question would be worse than
    the miss it fixes: an unanswerable question is a refusal, an answered wrong question is
    a false pass.
    """
    db, work = store
    assert C.recall_and_execute_workflow(
        f"how many {other} in {_data(work)}", db_path=db) is None


def test_the_intent_is_read_from_the_sentence_not_a_sorted_bag(store):
    _ = store
    """Regression for gate 4: sorting destroys word order, which `query_kind` reads."""
    target = " ".join(["different", "how", "lines", "many", "pd", "txt"])
    assert C._intent_of(target) == "lines"        # the bug's signature
    assert C._intent_of("how many different lines in pd.txt") == "uniquelines"
