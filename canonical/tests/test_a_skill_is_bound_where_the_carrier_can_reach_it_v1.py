"""A learned skill is only real if the carrier can reach what it names.

THE DEFECT THIS PINS (measured 2026-11-09)
------------------------------------------
Teach a skill once, then ask it to run. Held-out qualification failed with
`FAIL_CLOSED__CARRIER_DID_NOT_ESTABLISH_CONFINEMENT`, which reads like a confinement
problem and is not one. Confinement held the whole time (`confined: True`,
`live_workspace_untouched: True`). The exit code was 2: THE COMMAND COULD NOT FIND ITS FILE.

The carrier stages a workspace directory and runs the argv with that directory as cwd. So:

    ["sort","-u","data.txt"]                              -> exit 0, works
    ["sort","-u","canonical/astra_runtime/tmp/x/data.txt"] -> exit 2, NOT FOUND

A skill compiled from a goal that named a repo-relative path therefore stores an argv the
carrier can never satisfy. The skill is correct, the store is correct, the carrier is
correct -- and the learned capability is still dead, because nothing checked that the two
agree about what a path means.

This is the most expensive kind of defect in the tree: it does not fail loudly, it fails as
a SAFETY refusal, so it looks like the system being careful rather than the system being
unable to run what it taught itself.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from canonical.runtime import brokered_workspace_execution_v1 as broker
from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import recall_and_execute_workflow

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_BASE = _ROOT / "canonical" / "astra_runtime" / "tmp"


@pytest.fixture()
def work():
    d = pathlib.Path(tempfile.mkdtemp(prefix="reach_", dir=str(_BASE)))
    (d / "data.txt").write_text("a\nb\na\n", encoding="utf-8")
    yield d


def test_a_bare_filename_is_reachable_from_the_carrier(work):
    out = broker.run_staged_confined_command(str(work), ["sort", "-u", "data.txt"],
                                             timeout=20, task_id="t", goal="t")
    assert out.get("confined") is True
    assert out.get("live_workspace_untouched") is True
    assert out.get("exit") == 0, out.get("status")


def test_a_repo_relative_path_is_NOT_reachable(work):
    """The nearest world: same file, same program, different path shape."""
    rel = str((work / "data.txt").relative_to(_ROOT))
    out = broker.run_staged_confined_command(str(work), ["sort", "-u", rel],
                                             timeout=20, task_id="t", goal="t")
    assert out.get("exit") == 2, "if this ever passes, the carrier gained path translation"


def test_the_learned_skill_answers_when_bound_where_the_carrier_looks(work):
    """The shipped skill taught as 'how many unique lines in ?' actually works."""
    hit = recall_and_execute_workflow("how many unique lines in data.txt", cwd=str(work))
    assert hit is not None
    assert hit.get("answer") == 2


@pytest.mark.parametrize("synonym", ["distinct", "different"])
def test_and_it_survives_paraphrase_there(work, synonym):
    hit = recall_and_execute_workflow(f"how many {synonym} lines in data.txt", cwd=str(work))
    assert hit is not None, f"a taught skill did not survive {synonym!r}"


def test_and_refuses_a_different_intent_there(work):
    assert recall_and_execute_workflow("how many words in data.txt", cwd=str(work)) is None
