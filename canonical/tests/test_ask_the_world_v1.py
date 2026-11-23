"""Refusing to know is honest; asking and knowing is better -- provided the answer carries its moment.

§A119 ended on a boundary: every real-world program in the sample (config files, environment variables, stdin,
HTTP) came back `THIS_WALK_COULD_NOT_DECIDE`, because the values come from the world and a literal walk has
nothing to hold. Honest, and useless for deciding whether to run the program.

TWO PAPERS NAMED BOTH THE FAILURE AND THE REMEDY, and §A120 implements the pair:

  * EnvTrustBench (arXiv 2605.08828) -- the defect is treating an observed environment-facing claim as
    sufficient ground for action "without resolving it against available current evidence";
  * EnvProbe (arXiv 2606.31422) -- the remedy is to query the one belief field before acting and pay one step.

So the rules pinned here are: ask rather than refuse; never let a probe change the world it is measuring; and
never let a probed answer be confused with a constant, because evidence has a moment.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

from canonical.runtime import ask_the_world_v1 as A
from canonical.runtime import evaluate_literals_v1 as E


def _world() -> str:
    return tempfile.mkdtemp(prefix="probe_")


def test_a_read_is_answered_with_a_value_and_its_provenance() -> None:
    """A probe answers, and the answer says WHERE and WHEN it came from -- not just what it was."""
    world = _world()
    (pathlib.Path(world) / "present.txt").write_text("hello\n")

    record = A.probe("1 + 1", world=world)
    assert record["answered"] is True and record["value"] == 2 and record["literal"] is True
    assert isinstance(record["taken_at"], float) and record["world"] == world

    # a value from the WORLD, resolved against the directory the program will run in
    exists = A.probe("__import__('os').path.exists('present.txt')", world=world)
    assert exists["answered"] is False, "a probe may not call __import__"
    assert exists["why"].startswith("CALL_MAY_HAVE_AN_EFFECT")


def test_a_probe_may_not_change_the_world_it_is_measuring() -> None:
    """§A112 in miniature. `open('x','w')` under the name of a question is an ACTION.

    This is the one refusal that protects everything else: a probe that writes leaves the next measurement in a
    world the previous probe chose, which is exactly the error that invalidated five probes in §A111.
    """
    world = pathlib.Path(_world())
    before = sorted(p.name for p in world.iterdir())

    for dangerous in ('open("written-by-probe.txt", "w")', '__import__("os").system("echo hi")',
                      'input()', 'eval("1+1")', 'exec("x=1")'):
        record = A.probe(dangerous, world=str(world))
        assert record["answered"] is False, dangerous
        assert "EFFECT" in record["why"] or "WORLD" in record["why"], record

    assert sorted(p.name for p in world.iterdir()) == before, "the probe wrote into the world it was measuring"


def test_a_raised_exception_is_the_answer_not_a_failure() -> None:
    """`os.environ['NOPE']` raises when asked. That is the most useful answer available: the program dies here."""
    world = _world()
    record = A.probe("os.environ['A_NAME_THAT_CANNOT_EXIST_ZZ']", world=world, imports=["import os"])
    assert record["answered"] is True
    assert record["raised"] is True
    assert "KeyError" in (record.get("said") or "")


def test_asking_turns_an_unknowable_expression_into_a_decided_fault() -> None:
    """THE POINT OF THE WHOLE MODULE: the §A119 boundary, closed by evidence instead of refusal.

    Measured both ways in one test, so the difference cannot be mistaken for the module having changed its mind.
    """
    world = _world()
    source = "import os\nprint(os.environ['A_NAME_THAT_CANNOT_EXIST_ZZ'])"

    static = E.evaluate(source)
    assert static["verdict"] == "THIS_WALK_COULD_NOT_DECIDE"
    assert static["certain"] == []

    def prober(expression: str) -> dict:
        return A.probe(expression, world=world, imports=["import os"])

    probed = E.evaluate(source, prober=prober)
    assert [fault["class"] for fault in probed["certain"]] == ["key_not_found"]
    assert probed["verdict"] == "DECIDED_FROM_PROBED_EVIDENCE"
    # and the evidence travels with the verdict, so a caller can see what it rested on
    assert any(probe["expression"] == "os.environ['A_NAME_THAT_CANNOT_EXIST_ZZ']"
               for probe in probed["probes"])


def test_a_probe_that_proves_nothing_does_not_become_a_clean_verdict() -> None:
    """A verdict resting on evidence is not the same as a program being safe, and must not read as one."""
    world = _world()

    def prober(expression: str) -> dict:
        return A.probe(expression, world=world, imports=["import os"])

    result = E.evaluate("import os\nprint(os.sep)", prober=prober)
    assert result["certain"] == []
    assert result["verdict"] == "EVIDENCE_PROBED_NOTHING_PROVED"


def test_evidence_can_be_re_asked_and_is_reported_as_changing() -> None:
    """FRESHNESS IS THE PAPER'S WHOLE SUBJECT, and the cheapest honest answer is to be able to re-ask.

    A probe result is the freshest thing this system has and is still only a claim about a moment. `still_true`
    re-asks and compares. The comparison is deliberately literal equality: anything cleverer would need a notion
    of "same" this module does not have.
    """
    world = pathlib.Path(_world())
    # a permitted, read-only observable: whether a file is there
    question = A.probe("os.path.exists('flag.txt')", world=str(world), imports=["import os"])
    assert question["answered"] is True and question["value"] is False

    # NOTHING CHANGED: the same question gets the same answer, and that is reported as unchanged
    unchanged = A.still_true(question, world=str(world), imports=["import os"])
    assert unchanged["changed"] is False and unchanged["before"] == unchanged["after"] is False

    # THE WORLD CHANGES: the file appears, and re-asking catches it
    (world / "flag.txt").write_text("one\n")
    changed = A.still_true(question, world=str(world), imports=["import os"])
    assert changed["changed"] is True and changed["after"] is True

    # a constant is not evidence of a moment, and stays constant
    stable = A.probe("2 ** 8", world=str(world))
    again = A.still_true(stable, world=str(world))
    assert again["changed"] is False and again["before"] == again["after"] == 256
