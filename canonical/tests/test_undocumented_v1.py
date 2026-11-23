"""Tests for `undocumented_v1` -- learning an interface nobody wrote down.

The mission's hardest case is an environment that documents nothing. These tests are hard on purpose:
they use TWO programs with deliberately different refusal vocabularies, because a mechanism that reads
one program's words is a lookup, not a mechanism.
"""
from __future__ import annotations

import pathlib
import shutil
import tempfile

import pytest

from canonical.runtime import undocumented_v1 as U

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_BIN = _ROOT / "canonical" / "tests" / "programs" / "bin"


def _mystery() -> str:
    """A program whose refusals use the `<NAME>_REQUIRED` vocabulary and whose state is in the environment."""
    body = '''#!/usr/bin/env python3
import json, os, sys
STATE = os.environ.get("MYSTERY_STATE") or (
    os.path.dirname(os.path.abspath(__file__)) + "/.mystery.json")


def load():
    try:
        with open(STATE) as handle:
            return json.load(handle)
    except Exception:
        return {}


def save(data):
    with open(STATE, "w") as handle:
        json.dump(data, handle)


args = sys.argv[1:]
if not args:
    print("mystery: do things")
    sys.exit(0)
if args[0] == "add":
    if len(args) < 2:
        sys.stderr.write("NAME_REQUIRED\\n")
        sys.exit(1)
    state = load()
    state.setdefault("items", []).append(args[1])
    save(state)
    print(json.dumps({"ok": True}))
    sys.exit(0)
if args[0] == "list":
    print(json.dumps(load().get("items", [])))
    sys.exit(0)
sys.stderr.write("UNKNOWN_VERB:" + args[0] + "\\n")
sys.exit(1)
'''
    handle = tempfile.mkdtemp(prefix="mystery_")
    path = pathlib.Path(handle) / "mystery"
    path.write_text(body)
    path.chmod(0o755)
    return handle


@pytest.fixture()
def mystery_world():
    directory = _mystery()
    try:
        yield directory
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_it_learns_a_program_that_documents_nothing(mystery_world: str) -> None:
    """The point of the module: `add` and `list` are discovered from the program's own answers.

    Nothing here reads a manual, because there is no manual. `add` is found because a bare `add` is
    REFUSED FOR WANTING AN ARGUMENT -- a positive membership result -- and `bogus` is rejected because the
    program says so in its own words.
    """
    program = str(pathlib.Path(mystery_world) / "mystery")
    learned = U.learn_interface(program, mystery_world,
                               candidates=["add", "list", "bogus"], env_key="MYSTERY_STATE")

    assert learned["verbs_learned"] == ["add", "list"], learned["probed"]
    assert learned["arity"]["add"] == 1
    assert learned["arity"]["list"] == 0
    assert learned["unknown"] == ["bogus"]
    assert learned["mutating"] == ["add"]


def test_it_generalises_to_a_different_refusal_vocabulary() -> None:
    """THE TEST THAT CAUGHT ME CODING THE FIRST PROGRAM'S WORDS.

    `ticketer` refuses with `MISSING_ARGUMENT` and `INVALID_COMMAND`; `mystery` says `NAME_REQUIRED` and
    `UNKNOWN_VERB:`. A pattern matching one reported the other's real verbs as unreadable. The fix is not
    a bigger pattern -- it is the differential reading: probe a verb that cannot exist, learn what
    "no such verb" sounds like HERE, and treat any refusal that sounds DIFFERENT as evidence the verb is
    real.
    """
    world = tempfile.mkdtemp(prefix="tix_")
    try:
        shutil.copy(_BIN / "ticketer", pathlib.Path(world) / "ticketer")
        program = str(pathlib.Path(world) / "ticketer")
        learned = U.learn_interface(program, world, candidates=["open", "show", "delete"])

        assert learned["verbs_learned"] == ["open", "show"], learned["probed"]
        assert learned["arity"] == {"open": 2, "show": 1}, learned["arity"]
        assert learned["unknown"] == ["delete"], learned["unknown"]
        # and the signature it calibrated on is the program's own words, not mine
        assert "INVALID_COMMAND" in learned["no_such_verb_signature"]["said"]
    finally:
        shutil.rmtree(world, ignore_errors=True)


def test_probing_never_touches_the_world_it_was_given() -> None:
    """A PROBE OF A MUTATING PROGRAM MUTATES. That is why the copy exists, and why it must be EXECUTED.

    Measured 2026-11-23: the program path was resolved from the ORIGINAL tree, so probing ran the real
    binary and every write landed in the world I had promised not to touch -- `.tix.json` appeared in the
    caller's directory while the copy stayed clean. A copy that is never executed is not a sandbox; it is
    a decoration that makes the code READ safe while it is not.
    """
    world = tempfile.mkdtemp(prefix="tix_")
    try:
        shutil.copy(_BIN / "ticketer", pathlib.Path(world) / "ticketer")
        program = str(pathlib.Path(world) / "ticketer")
        learned = U.learn_interface(program, world, candidates=["open", "show"])

        # the probe DID find the mutation
        assert learned["mutating"] == ["open"], learned["mutating"]
        # and it happened in the copy, not here
        assert sorted(p.name for p in pathlib.Path(world).iterdir()) == ["ticketer"]
        copy = pathlib.Path(learned["world_was_copied_to"])
        assert ".tix.json" in sorted(p.name for p in copy.iterdir())
    finally:
        shutil.rmtree(world, ignore_errors=True)


def test_the_learned_interface_is_enough_to_act_and_its_limit_is_stated(mystery_world: str) -> None:
    """It learns SHAPE, never MEANING, and says so in the same breath as its success.

    `act_hint` is a command that will run. Whether `add` is the act the goal wants is a question this
    module cannot answer and does not pretend to -- `not_learnt` states it. A caller who reads
    `verbs_learned` as understanding has been misled by omission, which is why the omission is not allowed.
    """
    program = str(pathlib.Path(mystery_world) / "mystery")
    learned = U.learn_interface(program, mystery_world, candidates=["add", "list"],
                                env_key="MYSTERY_STATE")

    assert learned["enough_to_act"] is True
    assert learned["act_hint"].endswith("add<arg>")
    assert "MEANS" in learned["not_learnt"]


def test_an_unreadable_program_is_reported_not_guessed() -> None:
    """A program that says the same nothing to every input cannot be learnt, and says so.

    This is the honest refusal that keeps the module from becoming the thing Agent-Diff measured: an agent
    that receives null responses and hallucinates completion. `NO_DISCRIMINATION` is the whole point --
    it is the difference between not knowing and not admitting it.
    """
    world = tempfile.mkdtemp(prefix="mute_")
    try:
        path = pathlib.Path(world) / "mute"
        # every input is accepted silently and nothing is ever written
        path.write_text("#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n")
        path.chmod(0o755)
        learned = U.learn_interface(str(path), world, candidates=["anything", "else"])

        assert learned["enough_to_act"] is False
        assert learned["why"] == "VERBS_LEARNED_NONE_CHANGED_THE_WORLD", learned
    finally:
        shutil.rmtree(world, ignore_errors=True)
