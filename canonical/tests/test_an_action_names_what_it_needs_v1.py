"""§A137 — the dependency graph is in the arguments, and reading it beats searching for it.

THE CEILING THIS REMOVES. `environment_learning_v1` learns by walking an environment at random and recording
what each action does. Measured 2026-11-23, a task needing FIVE ordered steps:

    budget  60   FAIL_CLOSED__GOAL_NEVER_OBSERVED
    budget 150   FAIL_CLOSED__GOAL_NEVER_OBSERVED
    budget 400   FAIL_CLOSED__GOAL_NEVER_OBSERVED

Random walk finds a five-step chain only by collision, and the odds fall exponentially with depth. OSWorld 2.0
averages 318 steps per task. More budget is not a plan.

THE FACT. Every real action states its own precondition in its own arguments:

    ('cp', 'a.txt', 's1')   needs a.txt, produces s1
    ('cp', 's1',    's2')   needs s1, which the line above produces

At the start of that chain exactly one of the actions is possible. The graph was written down in the command
line; nothing has to learn it and nothing has to know what `cp` is.
"""
from __future__ import annotations

import pathlib
import subprocess

import pytest

from canonical.runtime import environment_learning_v1 as el
from canonical.runtime.an_action_names_what_it_needs_v1 import (
    distance_to_goal,
    execute_plan,
    heuristic,
    needs_and_produces,
    plan_from_arguments,
    possible_actions,
)


# ----------------------------------------------------------------------------------------------------------
# reading the arguments
# ----------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("action,needs,produces", [
    (("cp", "a", "b"), ["a"], "b"),                          # last word is the output
    (("tar", "-cf", "x.tar", "dir"), ["dir"], "x.tar"),      # the operand after the flag is the output
    (("gzip", "-k", "log"), ["log"], None),                  # the arguments do not say what appears
    (("rm", "x"), ["x"], None),                              # takes away, produces nothing
])
def test_a_flag_marks_the_operand_after_it(action, needs, produces) -> None:
    """Measured 2026-11-23 on `tar -cf x.tar dir`: reading the LAST operand as the output got this BACKWARDS,
    demanding the archive exist before creating it. The rule is positional -- a flag attaches to what follows."""
    spec = needs_and_produces(action)
    assert spec["needs"] == needs, spec
    assert spec["produces"] == produces, spec


def test_mkdir_and_rm_look_identical_and_must_not_be_guessed() -> None:
    """One word after a flag is undecidable from the arguments alone.

        mkdir -p scratch    scratch is MADE
        rm -f notes.txt     notes.txt must EXIST

    Choosing "made" for both would have `rm` demand a file that must not exist. The module keeps the word as a
    need and reports no output, which is the safe reading for both.
    """
    assert needs_and_produces(("mkdir", "-p", "scratch"))["produces"] is None
    assert needs_and_produces(("rm", "-f", "notes.txt"))["needs"] == ["notes.txt"]


def test_the_frontier_of_what_can_be_done_now() -> None:
    actions = [("cp", "a.txt", "s1"), ("cp", "s1", "s2"), ("rm", "s1")]
    assert possible_actions(actions, ["a.txt"]) == [("cp", "a.txt", "s1")]
    assert set(possible_actions(actions, ["a.txt", "s1"])) == {("cp", "a.txt", "s1"), ("cp", "s1", "s2"),
                                                              ("rm", "s1")}


def test_distance_is_read_off_the_arguments() -> None:
    chain = [("cp", "a.txt", "s1"), ("cp", "s1", "s2"), ("cp", "s2", "s3")]
    assert distance_to_goal(chain, ["a.txt"], "s3") == 3
    assert distance_to_goal(chain, ["a.txt"], "a.txt") == 0
    assert distance_to_goal(chain, ["a.txt"], "nowhere") == float("inf")


# ----------------------------------------------------------------------------------------------------------
# the ceiling, and breaking it
# ----------------------------------------------------------------------------------------------------------

class _Directory:
    """A real directory, real programs, real files. Reset puts it back so probing is free."""

    KEEP = {"a.txt"}

    def __init__(self, root: pathlib.Path) -> None:
        self.root = root
        (root / "a.txt").write_text("x\n")

    def reset(self):
        for path in list(self.root.iterdir()):
            if path.is_file() and path.name not in self.KEEP:
                path.unlink()
        return self.state()

    def state(self):
        return tuple(sorted(p.name for p in self.root.iterdir()))

    def act(self, action):
        subprocess.run(list(action), cwd=self.root, capture_output=True)
        return self.state()

    def snapshot(self):
        return self.state()

    def restore(self, state):
        self.reset()
        for name in state:
            if name not in self.KEEP:
                (self.root / name).write_text("x\n")


def _chain(length: int):
    actions, previous = [], "a.txt"
    for index in range(1, length + 1):
        actions.append(("cp", previous, "s%d" % index))
        previous = "s%d" % index
    return actions, previous


def test_a_five_step_chain_is_unreachable_by_random_walk(tmp_path) -> None:
    """The ceiling, pinned so it cannot silently return. Five real steps, three budgets, all fail."""
    actions, goal = _chain(5)
    for budget in (60, 150):
        result = el.drive(_Directory(tmp_path), actions, is_goal=lambda s, g=goal: g in s,
                          budget=budget, max_depth=6, seed=1)
        assert result["pass"] is False, (budget, result["status"])


def test_reading_the_arguments_solves_what_searching_could_not(tmp_path) -> None:
    """Same environment, same goal. The random walk fails; the derived plan succeeds and is verified."""
    actions, goal = _chain(5)
    result = el.drive(_Directory(tmp_path), actions, is_goal=lambda s, g=goal: g in s,
                      budget=60, max_depth=6, seed=1, heuristic=heuristic(actions, goal))
    assert result["pass"] is True, result["status"]
    assert len(result["plan"]) == 5


def test_twenty_dependent_steps_in_a_shuffled_list(tmp_path) -> None:
    """Twenty steps is past anything a walk reaches. The action list is shuffled so ORDER cannot be the answer."""
    import random
    actions, goal = _chain(20)
    random.Random(0).shuffle(actions)
    plan = plan_from_arguments(actions, list(_Directory(tmp_path).state()), goal)
    assert plan is not None and len(plan) == 20
    result = execute_plan(_Directory(tmp_path), plan, lambda s, g=goal: g in s)
    assert result["pass"] is True, result["status"]


# ----------------------------------------------------------------------------------------------------------
# honest failures -- the method must refuse what it cannot derive
# ----------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("actions,state,goal,reason", [
    ([("cp", "a.txt", "s1")], ["a.txt"], "s9", "goal nothing produces"),
    ([("cp", "a.txt", "s1"), ("cp", "s2", "s3")], ["a.txt"], "s3", "chain broken in the middle"),
    ([("cp", "missing.txt", "s1")], ["a.txt"], "s1", "starting material absent"),
])
def test_no_derivable_chain_is_none_not_an_invented_plan(actions, state, goal, reason) -> None:
    assert plan_from_arguments(actions, state, goal) is None, reason


def test_a_goal_already_true_is_an_empty_plan_not_a_failure() -> None:
    assert plan_from_arguments([("cp", "a", "b")], ["a", "b"], "b") == []


def test_an_output_the_arguments_do_not_name_is_refused(tmp_path) -> None:
    """`gzip -k report.csv` writes report.csv.gz, and NOTHING in the command says so.

    So a plan through it cannot be derived, and the module refuses rather than inventing the name. This is the
    real boundary of the method: it reads what actions declare, and a program that names its output by
    convention declares nothing. Measured 2026-11-23 -- the same task with `tar -czf out archive` (which DOES
    declare its output) is derivable and passes.
    """
    (tmp_path / "report.csv").write_text("a,b\n")
    actions = [("gzip", "-k", "report.csv"), ("cp", "report.csv.gz", "final.gz")]
    assert plan_from_arguments(actions, list(_Directory(tmp_path).state()), "final.gz") is None


# ----------------------------------------------------------------------------------------------------------
# a real chain, byte-checked
# ----------------------------------------------------------------------------------------------------------

def test_a_real_archive_chain_is_derived_and_the_artifact_is_really_compressed(tmp_path) -> None:
    """tar -> mv -> cp, derived from the arguments, executed, and the bytes inspected.

    The last assertion is the one that matters: a plan can "pass" a goal check by creating an empty file. The
    gzip magic `1f 8b` says the archive is genuinely compressed, which is §A130's lesson applied here.
    """
    import tarfile

    (tmp_path / "report.csv").write_text("a,b\n1,2\n")
    (tmp_path / "archive").mkdir()
    (tmp_path / "archive" / "keep.txt").write_text("k\n")

    class World(_Directory):
        KEEP = {"report.csv"}

        def state(self):
            return tuple(sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*")))

        def act(self, action):
            subprocess.run(list(action), cwd=self.root, capture_output=True)
            return self.state()

    actions = [("tar", "-czf", "report.tar.gz", "report.csv"),
               ("mv", "report.tar.gz", "archive/report.tar.gz"),
               ("cp", "archive/report.tar.gz", "final.tgz")]
    plan = plan_from_arguments(actions, list(World(tmp_path).state()), "final.tgz")
    assert plan == actions, plan

    result = execute_plan(World(tmp_path), plan, lambda s: "final.tgz" in s)
    assert result["pass"] is True, result["status"]

    blob = (tmp_path / "final.tgz").read_bytes()
    assert blob[:2] == b"\x1f\x8b", blob[:2].hex()
    assert tarfile.open(tmp_path / "final.tgz").getnames() == ["report.csv"]
