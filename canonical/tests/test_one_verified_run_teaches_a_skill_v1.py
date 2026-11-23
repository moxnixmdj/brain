"""ONE VERIFIED RUN TEACHES A SKILL, AND THE SKILL IS GENERAL — NOT A REPLAY.

THE HYPOTHESIS UNDER TEST. The mission says the agent should have to do something once and have it
learned permanently. Measured 2026-11-22 that was FALSE in a specific, fixable way, and this file
pins the fix.

WHAT WAS WRONG (A75). A procedure stored WHICH CAPABILITY answered and not WHAT COMMAND made it work.
`shell.command.run` with `['ls','-la']` is a solved task; `shell.command.run` with no argv is not a
task at all. So a request could be taught once, recalled at similarity 1.0, and still be refused --
the recalled candidate had an ARGV slot and nothing to put in it. Worse, `ra.solve` never learned at
all: the store was written only by `grounded_action_v1.act`, which that front door does not call. The
loop was open at both joints.

THE STORED FORM IS A SKILL, NOT A REPLAY. Storing `['ls','-la']` verbatim would work in one directory
and nowhere else -- "saving the exact experience in a dumb way". The split needs no knowledge of any
program:

    token 0             -> the PROGRAM      (which program did this)
    token starting '-'  -> a FLAG           (how the program was told what to do: part of the skill)
    anything else       -> an OPERAND       (a value the SENTENCE supplied, by position)

so `['wc','-l','README.md']` becomes `wc`, flags `['-l']`, and an operand at position 2 — and a new
sentence supplies its own operand there.

THE THREE THINGS THAT MAKE RECALL HONEST, all tested below:

    a) only a VERIFIED run teaches (a failure teaches nothing);
    b) a skill must fit EXACTLY — right program, right number of operands — or it is not offered;
    c) the recalled command is still compiled, bound and executed like any other, so a bad fit costs
       a failed run and never a wrong answer.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from canonical.runtime import procedure_memory_v1 as PM


# --------------------------------------------------------------------------------------------
# THE GENERALISATION ITSELF — no I/O, no memory, just the shape.
# --------------------------------------------------------------------------------------------
def test_the_program_and_the_flags_are_the_skill_and_the_rest_is_an_operand():
    skill = PM.command_skill(["wc", "-l", "README.md"])
    assert skill["program"] == "wc"
    assert skill["template"] == ["wc", "-l", PM._OPERAND]
    assert skill["operand_positions"] == [2]
    # What it was learned FROM is kept for inspection.
    assert skill["learned_from"] == ["wc", "-l", "README.md"]


def test_a_skill_with_no_operand_is_directly_runnable_anywhere():
    skill = PM.command_skill(["ls", "-la"])
    assert skill["template"] == ["ls", "-la"]
    assert PM.apply_command_skill(skill, []) == ["ls", "-la"]


def test_a_skill_applies_to_a_operand_it_was_never_taught():
    """The whole point: `wc -l README.md` teaches a skill that counts a DIFFERENT file."""
    skill = PM.command_skill(["wc", "-l", "README.md"])
    assert PM.apply_command_skill(skill, ["AGENTS.md"]) == ["wc", "-l", "AGENTS.md"]
    assert PM.apply_command_skill(skill, ["src/main.py"]) == ["wc", "-l", "src/main.py"]


@pytest.mark.parametrize("operands", [[], ["a.txt", "b.txt"]])
def test_a_skill_that_does_not_fit_exactly_is_not_offered(operands):
    """One operand too few or too many is a different task, not a loose match."""
    skill = PM.command_skill(["wc", "-l", "README.md"])
    assert PM.apply_command_skill(skill, operands) is None


def test_no_argv_teaches_no_skill():
    assert PM.command_skill([]) == {}
    assert PM.apply_command_skill({}, ["x"]) is None


# --------------------------------------------------------------------------------------------
# ONLY A VERIFIED RECEIPT MAY TEACH.
# --------------------------------------------------------------------------------------------
def test_a_failed_run_teaches_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        store = Path(tmp) / "experience.json"
        taught = PM.learn("use wc on AGENTS.md", "shell.command.run", verified=False,
                          path=store, inputs={"argv": ["wc", "-l", "AGENTS.md"]})
        assert taught["learned"] is False
        assert taught["why"] == "ONLY_A_VERIFIED_RECEIPT_MAY_TEACH_A_PROCEDURE"
        assert PM.recall("use wc on AGENTS.md", path=store) is None


def test_a_verified_run_stores_the_command_it_used():
    with tempfile.TemporaryDirectory() as tmp:
        store = Path(tmp) / "experience.json"
        taught = PM.learn("wc -l README.md", "shell.command.run", verified=True,
                          path=store, inputs={"argv": ["wc", "-l", "README.md"]})
        assert taught["learned"] is True
        entry = PM._procedures(path=store)[taught["signature"]]
        assert entry["command_skill"]["template"] == ["wc", "-l", PM._OPERAND]
        # Persisted: a fresh read of the file sees it.
        on_disk = json.loads(store.read_text())
        assert on_disk["procedures"][taught["signature"]]["command_skill"]["program"] == "wc"


# --------------------------------------------------------------------------------------------
# THE END-TO-END PROOF: teach once, then a NEW FILE answered from memory.
# --------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def store():
    """A private store, so this file never touches the machine's real memory."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp) / "experience.json"


def _remember(goal, store):
    """`world_binding_v1._remembered_argv`, with the store redirected."""
    from canonical.runtime import world_binding_v1 as WB
    original = PM._procedures

    def _from_store(path=None):
        return original(path=store)

    PM._procedures = _from_store
    try:
        return WB._remembered_argv(goal)
    finally:
        PM._procedures = original


def test_nothing_is_offered_before_anything_was_taught(store):
    assert _remember("use wc on AGENTS.md", store) is None


def test_one_verified_run_is_enough_to_answer_a_new_file(store):
    PM.learn("wc -l README.md", "shell.command.run", verified=True,
             path=store, inputs={"argv": ["wc", "-l", "README.md"]})
    # Never taught, different file, different wording.
    assert _remember("use wc on AGENTS.md", store) == ["wc", "-l", "AGENTS.md"]


def test_memory_does_not_override_a_command_the_sentence_states(store):
    """A stated command wins: `extract_argv` is consulted before memory everywhere it matters."""
    from canonical.runtime.composer_route_v1 import extract_argv
    assert extract_argv("wc -l AGENTS.md") == ["wc", "-l", "AGENTS.md"]
    # And the remembered skill is only reached when the sentence states no command.
    assert extract_argv("use wc on AGENTS.md") is None


def test_teach_once_then_a_new_file_is_answered_from_memory():
    """THE PROOF, through the real front door, with the machine's own memory.

    `use wc on AGENTS.md` is refused BEFORE anything is taught; `wc -l README.md` is done once; and
    the same request, never taught and naming a different file, then passes with the count of that
    file. That sequence is the mission's hypothesis, tested rather than asserted.
    """
    from canonical.runtime import live_brain_route_admission_v1 as ra
    from canonical.runtime import procedure_memory_v1 as memory

    target = ROOT / "AGENTS.md"
    if not target.is_file():
        pytest.skip("AGENTS.md is not present in this checkout")
    expected = len(target.read_text(errors="replace").splitlines())

    saved = json.dumps(memory._procedures())
    try:
        # A TEST MUST NOT DEPEND ON WHAT AN EARLIER RUN LEFT BEHIND.
        #
        # Measured 2026-11-22: this assertion passed vacuously because a previous run had taught the
        # wc skill into the machine's real store, so "before teaching" was already after teaching.
        # The store is cleared to its saved baseline here, and restored in `finally`.
        from canonical.runtime import experience_v1 as _EXP
        _fresh = _EXP._load()
        _fresh["procedures"] = {}
        _EXP._save(_fresh)

        # 0. Nothing taught yet: the request is refused.
        before = ra.solve({"task_id": "pre", "goal": "use wc on AGENTS.md"})
        assert not before.get("pass"), "the request passed with nothing in memory"

        # 1. Do it once, on a different file.
        taught = ra.solve({"task_id": "teach", "goal": "wc -l README.md"})
        assert taught.get("pass") is True, taught.get("status")

        # 2. The same request now answers, for a file it was never taught.
        after = ra.solve({"task_id": "post", "goal": "use wc on AGENTS.md"})
        assert after.get("pass") is True, after.get("status")
        execution = after["execution"]
        step = execution[0] if isinstance(execution, list) else execution
        assert step["argv"] == ["wc", "-l", "AGENTS.md"]
        assert int(step["stdout"].split()[0]) == expected
    finally:
        # Leave the machine's memory exactly as it was found.
        from canonical.runtime import experience_v1 as _EXP
        state = _EXP._load()
        state["procedures"] = json.loads(saved)
        _EXP._save(state)


# --------------------------------------------------------------------------------------------
# A PROGRAM THE SENTENCE NAMES AS AN INSTRUMENT, WHEN THAT PROGRAM NEEDS NO ARGUMENT.
#
# This is the SYNTHESIS half: not everything has to be taught. "list the files using ls" says which
# program, and bare `ls` is a complete command. It is also the DANGEROUS half -- answering "what does
# ls do" by running `ls` answers a question nobody asked -- so the guard is measured, not guessed.
# --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("sentence,program", [
    ("list the files using ls", "ls"),
    ("use date to tell the time", "date"),
])
def test_a_program_named_as_an_instrument_is_derived_when_it_needs_no_argument(sentence, program):
    from canonical.runtime import machine_purpose_index_v1 as machine
    derived = machine.derive_argv(sentence)
    assert derived.get("ok") is True, derived.get("reason")
    assert derived["argv"] == [program]
    assert derived["authority"] == "THE_PROGRAM_ANSWERED_WITH_NO_ARGUMENT"


@pytest.mark.parametrize("sentence", [
    "what does ls do",
    "explain how ls works",
    "is ls dangerous",
    "tell me about ls",
    "what is wc",
    "how does git work",
])
def test_a_sentence_ABOUT_a_program_is_never_answered_by_running_it(sentence):
    """Measured 2026-11-22: 7 of 11 program-naming probes were sentences ABOUT the program."""
    from canonical.runtime import machine_purpose_index_v1 as machine
    assert machine.derive_argv(sentence).get("ok") is False


def test_a_bare_command_never_stands_in_for_a_path_the_sentence_named():
    """THE DEFECT THIS RULE WAS WRITTEN FOR, kept as a test.

    With nothing in memory, "use wc on AGENTS.md" derived bare `['wc']`. That is a complete command --
    it reads stdin and exits 0 -- so the request PASSED and answered "0 0 0" about no file at all. The
    sentence said which file; the command could not see it. A pass whose answer is about something
    else is worse than a refusal.
    """
    from canonical.runtime import machine_purpose_index_v1 as machine
    assert machine._a_path_the_bare_command_would_ignore("use wc on AGENTS.md") is True
    assert machine.derive_argv("use wc on AGENTS.md").get("ok") is False
    # A sentence that names no path is still derivable.
    assert machine._a_path_the_bare_command_would_ignore("list the files using ls") is False


def test_a_taught_skill_outranks_a_derivation():
    """`wc` with no file reads stdin; the learned `wc -l <file>` must not be shadowed by bare `wc`."""
    from canonical.runtime import live_brain_route_admission_v1 as ra
    from canonical.runtime import experience_v1 as _EXP
    target = ROOT / "AGENTS.md"
    if not target.is_file():
        pytest.skip("AGENTS.md is not present in this checkout")
    saved = json.dumps(_EXP._load().get("procedures") or {})
    try:
        state = _EXP._load()
        state["procedures"] = {}
        _EXP._save(state)
        assert ra.solve({"task_id": "teach", "goal": "wc -l README.md"}).get("pass") is True
        after = ra.solve({"task_id": "post", "goal": "use wc on AGENTS.md"})
        assert after.get("pass") is True, after.get("status")
        execution = after["execution"]
        step = execution[0] if isinstance(execution, list) else execution
        # The skill, not the derivation: the operand is back, and the count is real.
        assert step["argv"] == ["wc", "-l", "AGENTS.md"]
        assert int(step["stdout"].split()[0]) == len(target.read_text(errors="replace").splitlines())
    finally:
        state = _EXP._load()
        state["procedures"] = json.loads(saved)
        _EXP._save(state)
