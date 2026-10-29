#!/usr/bin/env python3
"""A declared knob is the machine's business, and a declared kind is what parses a value.

Three defects, all of the same shape: **the declaration existed and no binder read it.**

1. `input_role_lexicon_v1.ROLE_ALIASES` carries the words a sentence uses for 38 declared roles --
   "timeout", "interpreter", "branch called", "kill ratio", "repeats" -- and
   `goal_front_compiler_v1` imported it (`_ROLE_LEXICON_ALIASES`) without ever consulting it.  Every
   key with no entry in the compiler's own `_KEY_ALIASES` therefore had no prose form at all.
2. `input_role_lexicon_v1.SLOT_KIND` declares `timeout_s`, `python_executable`, `repeats`,
   `min_coverage_ratio`, `max_mutants`, `min_kill_ratio`, `tolerance`, `budget` and `ref` as
   `KIND_TUNING`, with the reason written beside them: "every adapter writes
   ``args.get("<knob>") or <default>``, so these are the adapter's business, not the caller's".
   The binder raised on them instead, so `timeout_s` alone made 15 capabilities unaskable: the
   sentence could not state a timeout, the compiler refused `named_but_inputs_not_stated`, and no
   adapter ever ran.
3. `_parse_typed_value` keeps its own four-key numeric sets, so a value the lexicon declares a
   NUMBER could not be parsed -- "with a timeout of 30 seconds" bound nothing.

Measured on sentences that name a capability, before and after: 2 more capabilities reachable by
name and 0 lost (a worktree at `580fa4d` against this tree, identical sentences).  The numbers are
small because the sentence has to name the capability to hit these paths; the point of the pins is
that the three laws hold and that nothing is ever silently dropped or invented.

The last law is the one that matters most: **a stated value that vanishes is the same defect as a
stated revision silently replaced by HEAD.**  A knob the sentence states must be bound or refused --
never dropped on the floor.
"""
from __future__ import annotations

import pathlib

import pytest

from canonical.runtime import goal_compiler as gc
from canonical.runtime import goal_front_compiler_v1 as front
from canonical.runtime import input_role_lexicon_v1 as lexicon

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIFF = ("diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a\n+b\n")


@pytest.fixture(scope="module")
def registry():
    from canonical.runtime.live_integrated_brain_v1 import load_verified_registry
    return gc._platform_admissible_registry(dict(load_verified_registry()))


@pytest.fixture()
def world(tmp_path):
    (tmp_path / "work").mkdir()
    (tmp_path / "work" / "change.diff").write_text(DIFF, encoding="utf-8")
    (tmp_path / "reports").mkdir()
    return tmp_path


def _goal(world, extra: str = "") -> str:
    return ("Run the python review diff static triage capability on the diff work/change.diff"
            + extra + " and report it to reports/result.json.")


def _bind(world, registry, extra: str = "") -> dict:
    front._DEFAULTED_INPUTS.set(())
    return front.bind_all_inputs(_goal(world, extra), registry["python.review.diff_static_triage.v1"],
                                 world)


# ------------------------------------------------------------------ the vocabulary, wired up


@pytest.mark.parametrize("key,phrase", [
    ("timeout_s", "timeout"),
    ("python_executable", "interpreter"),
    ("branch_name", "branch"),
    ("min_kill_ratio", "kill ratio"),
    ("repeats", "repeats"),
])
def test_the_lexicon_the_machine_already_declared_is_read_by_the_binder(key, phrase):
    assert phrase in lexicon.ROLE_ALIASES[key]
    assert phrase in front._role_phrases(key)


def test_a_key_the_compiler_never_had_a_form_for_now_has_one():
    """"timeout s 30" is not a sentence anybody says, and the binder was right to refuse it."""
    assert "timeout_s" not in front._KEY_ALIASES
    assert front._role_phrases("timeout_s") != ["timeout_s"]


# ---------------------------------------------------------------- the knob is not the caller's


def test_a_knob_the_sentence_never_states_is_defaulted_and_the_answer_says_so(world, registry):
    bound = _bind(world, registry)
    assert bound["diff_path"] == "work/change.diff"
    # the adapter owns these; the caller never mentioned them
    assert "timeout_s" not in bound and "python_executable" not in bound
    assert set(front._DEFAULTED_INPUTS.get()) == {"timeout_s", "python_executable"}


def test_a_knob_the_sentence_states_is_bound_not_discarded(world, registry):
    bound = _bind(world, registry, " with a timeout of 30 seconds")
    assert bound["timeout_s"] == 30
    assert front._DEFAULTED_INPUTS.get() == ("python_executable",)


def test_a_stated_interpreter_is_a_path_and_the_word_python_is_not(world, registry):
    stated = _bind(world, registry, " using the interpreter /usr/bin/python3")
    assert stated["python_executable"] == "/usr/bin/python3"
    assert "python_executable" not in front._DEFAULTED_INPUTS.get()
    # every Python sentence contains the word "python"; none of them states an interpreter
    hinted = _bind(world, registry, " for the python code")
    assert "python_executable" not in hinted
    assert "python_executable" in front._DEFAULTED_INPUTS.get()


def test_a_stated_knob_that_cannot_be_read_is_refused_never_dropped(world, registry):
    front._DEFAULTED_INPUTS.set(())
    with pytest.raises(gc.GoalCompilationFailure) as refused:
        front.bind_all_inputs(
            _goal(world, " with a timeout of soonish"),
            registry["python.review.diff_static_triage.v1"], world)
    assert "stated_but_unbound" in str(refused.value.detail)


# ------------------------------------------------------------- the anti-fabrication rule still holds


def test_the_anti_fabrication_check_is_not_weakened_for_a_slot_that_is_not_a_knob():
    """A defaulted knob is declared tuning.  An invented path is not, and is still reported."""
    front._DEFAULTED_INPUTS.set(())
    front._DEFAULTED_INPUTS.set(("diff_path", "timeout_s"))
    unstated = front._inputs_not_stated_by("a sentence that states nothing",
                                          {"diff_path": "invented.diff", "timeout_s": 30})
    assert unstated == ["diff_path"]
