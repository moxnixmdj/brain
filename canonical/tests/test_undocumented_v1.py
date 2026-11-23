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


# ----------------------------------------------------------------------------------------------------
# The join: a goal in ordinary words drives a program nobody documented.
# ----------------------------------------------------------------------------------------------------

def _ticketer_world() -> tuple[str, str]:
    world = tempfile.mkdtemp(prefix="tix_")
    shutil.copy(_BIN / "ticketer", pathlib.Path(world) / "ticketer")
    return world, str(pathlib.Path(world) / "ticketer")


def test_the_join_runs_end_to_end_with_no_documentation() -> None:
    """Learn, act, read back -- all three from the program's own answers.

    This is the whole point of the module assembled: the interface is measured, the command comes from the
    goal's own words, and the effect is confirmed by a read verb that was also learned. At no step was any
    documentation consulted, and at no step was a model called.
    """
    from canonical.runtime import mechanism_act_v1 as M
    from canonical.runtime import solve_v1 as S

    world, program = _ticketer_world()
    try:
        learned = U.learn_interface(program, world, candidates=["open", "show", "delete"])
        join = U.act_for_goal('open a ticket "T-1" describing "printer jammed"', learned)
        assert join["why"] == "JOINED_FROM_THE_MEASURED_INTERFACE", join
        assert join["act"][1:] == ["open", "T-1", "printer jammed"], join["act"]

        result = S.act(world, M._as_program(join["act"], world))
        assert result.get("exit") == 0, result

        # the READ was learned too -- no documentation says which verb reads
        read = U.act_for_goal('show ticket "T-1"', learned)
        assert read["act"][1:] == ["show", "T-1"], read["act"]
        back = S.act(world, M._as_program(read["act"], world))
        assert "printer jammed" in (back.get("out") or ""), back
    finally:
        shutil.rmtree(world, ignore_errors=True)


def test_the_join_refuses_a_goal_that_names_no_verb_of_the_program() -> None:
    """THE LINE THE JOIN DOES NOT CROSS, and the reason it is not a synonym table.

    `create a ticket ...` names nothing `ticketer` has. Making `create` mean `open` requires knowing that
    those words are synonyms -- knowledge about English, not about the program. A module with no such
    knowledge must refuse, because the alternative is a synonym list I invent, which would work on the
    three goals I thought of and fail silently on the fourth.
    """
    world, program = _ticketer_world()
    try:
        learned = U.learn_interface(program, world, candidates=["open", "show"])
        join = U.act_for_goal('create a ticket titled "T-9" with body "wifi down"', learned)
        assert join["act"] is None, join
        assert join["why"] == "THE_PROGRAM_STATES_NO_SUCH_VERB", join
        assert "open" in join["the_program_has"]
        assert "synonym" in join["detail"]
    finally:
        shutil.rmtree(world, ignore_errors=True)


def test_a_goal_with_too_few_values_is_refused_not_padded() -> None:
    """A positional argument cannot be filled from nothing, so a short goal is refused with the count."""
    world, program = _ticketer_world()
    try:
        learned = U.learn_interface(program, world, candidates=["open"])
        join = U.act_for_goal('open a ticket "T-1"', learned)
        assert join["act"] is None, join
        assert join["why"] == "THE_GOAL_STATES_TOO_FEW_VALUES", join
        assert join["wanted"] == 2 and join["stated"] == ["T-1"]
    finally:
        shutil.rmtree(world, ignore_errors=True)


def test_the_learned_interface_points_at_a_file_that_still_exists() -> None:
    """The probe runs a COPY, and the copy is deleted. Reporting the copy's path made the learned interface
    unusable: `act_hint` named `/tmp/brain_probe_.../world/bin/ticketer`, which was gone by the time anyone
    tried to run it. The interface a caller gets back must be one they can act on."""
    world, program = _ticketer_world()
    try:
        learned = U.learn_interface(program, world, candidates=["open"])
        assert pathlib.Path(learned["program"]).is_file(), learned["program"]
        assert "brain_probe_" not in learned["program"]
        assert pathlib.Path(learned["act_hint"].split()[0]).is_file()
    finally:
        shutil.rmtree(world, ignore_errors=True)


# ----------------------------------------------------------------------------------------------------
# Nobody supplies the vocabulary either.
# ----------------------------------------------------------------------------------------------------

def test_the_caller_supplies_no_vocabulary_at_all() -> None:
    """The probe needs verbs to try, and a self-documenting program will not volunteer them: `ticketer`
    refuses `help`, `--help` and `commands`.

    So the hypotheses come from the program's own dispatch -- the string literals it COMPARES against --
    and the probe still decides which are real. Measured on `ticketer`: the compared literals are exactly
    `open`, `show`, `shutdown`, its three verbs and nothing else. The caller names a program and a world,
    and that is all.
    """
    world, program = _ticketer_world()
    try:
        learned = U.learn_interface(program, world)  # no candidates=

        assert learned["candidates_from"] == "THE_PROGRAM_STATES_THESE_IN_ITS_OWN_DISPATCH"
        assert learned["verbs_learned"] == ["open", "show", "shutdown"], learned["probed"]
        assert learned["arity"] == {"open": 2, "show": 1, "shutdown": 0}
        assert learned["unknown"] == [], learned["unknown"]
    finally:
        shutil.rmtree(world, ignore_errors=True)


def test_a_literal_in_a_comparison_is_a_claim_and_the_probe_is_the_truth() -> None:
    """A compared literal is a HYPOTHESIS, not a fact -- flags appear in comparisons too.

    A program that compares its argument against a flag as well as its verbs must have the flag rejected.
    If reading the source were treated as authoritative, `--force` would enter the interface as a verb and
    the first command built from it would fail in the world, which is the expensive way to learn a fact one
    probe could have established.
    """
    world = tempfile.mkdtemp(prefix="flaggy_")
    try:
        path = pathlib.Path(world) / "flaggy"
        path.write_text('''#!/usr/bin/env python3
import sys, os
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".flaggy.json")
args = sys.argv[1:]
if not args:
    sys.stderr.write("usage: flaggy <command>\\n")
    sys.exit(2)
if args[0] == "--force":
    sys.stderr.write("INVALID_COMMAND\\n")
    sys.exit(2)
if args[0] == "mark":
    if len(args) < 2:
        sys.stderr.write("MISSING_ARGUMENT\\n")
        sys.exit(2)
    open(STATE, "w").write(args[1])
    print("marked")
    sys.exit(0)
if args[0] == "peek":
    try:
        print(open(STATE).read())
    except Exception:
        print("nothing")
    sys.exit(0)
sys.stderr.write("INVALID_COMMAND\\n")
sys.exit(2)
''')
        path.chmod(0o755)
        learned = U.learn_interface(str(path), world)

        # the flag was offered as a candidate, because it IS a compared literal
        offered = [row["verb"] for row in learned["probed"]]
        assert "--force" not in offered, offered          # flags are skipped before probing
        assert learned["verbs_learned"] == ["mark", "peek"], learned["probed"]
        assert learned["mutating"] == ["mark"], learned["mutating"]
    finally:
        shutil.rmtree(world, ignore_errors=True)
