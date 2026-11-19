"""The round's own tests: the switch that stops a trial, and the accounting that makes it a price.

The load-bearing object here is `decisive`. The first version of this round used `boundary.identified` as
the switch, and since a real sensor vocabulary always carries facts no reachable state can change, the
requirement is never uniquely named: the loop trialled 160 of 160 decisions and the "learning" claim looked
false for the wrong reason. The right switch is per STATE -- do all surviving requirements agree here? --
and these tests pin it, because a wrong switch produces a number that reads exactly like a finding.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
if str(TOOLS.parents[1]) not in sys.path:
    sys.path.insert(0, str(TOOLS.parents[1]))

import what_a_decision_costs_v1 as cost  # noqa: E402
from canonical.runtime import applicability_v1 as APP  # noqa: E402


class _Boundary:
    def __init__(self, survivors):
        self.survivors = tuple(tuple(sorted(s)) for s in survivors)
        self.survivor_count = len(self.survivors)
        self.identified = self.survivor_count == 1
        self.required = self.survivors[0] if self.identified else None


def test_no_failure_licenses_nothing_so_the_switch_is_open() -> None:
    assert cost.decisive(_Boundary([]), ["stash.present"]) is None
    assert cost.decisive(APP.learn([({"stash.present"}, True)]), ["stash.present"]) is None


def test_the_switch_closes_when_every_survivor_agrees_here() -> None:
    boundary = _Boundary([{"a"}, {"a", "b"}])
    assert cost.decisive(boundary, ["a", "b"]) is True      # both requirements are satisfied
    assert cost.decisive(boundary, ["c"]) is False          # neither is


def test_the_switch_stays_open_when_survivors_disagree_here() -> None:
    boundary = _Boundary([{"a"}, {"a", "b"}])
    assert cost.decisive(boundary, ["a"]) is None


def test_the_switch_is_per_state_not_per_condition() -> None:
    """A thousand survivors can still decide -- that is the whole reason a trial can stop."""
    boundary = _Boundary([{"a"}, {"a", "b"}, {"a", "c"}])
    assert not boundary.identified
    assert cost.decisive(boundary, ["a", "b", "c"]) is True


def test_the_stream_alternates_so_no_policy_wins_by_ordering() -> None:
    rows = [("p0", None, "APPLIES", ""), ("p1", None, "APPLIES", ""),
            ("n0", None, "DOES_NOT_APPLY", ""), ("n1", None, "DOES_NOT_APPLY", "")]
    out = cost._interleave(rows)
    outcomes = [row[2] for row in out]
    assert outcomes == ["APPLIES", "DOES_NOT_APPLY", "APPLIES", "DOES_NOT_APPLY"]
    assert {row[0] for row in out} == {"p0", "p1", "n0", "n1"}


def _git(repo: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                          cwd=str(repo), capture_output=True, text=True, check=False)


@pytest.fixture()
def machine(tmp_path: pathlib.Path):
    """A tiny real machine: one action with a genuinely varied applicability, real git, no network."""
    root = tmp_path
    base = root / "base"
    base.mkdir()
    _git(base, "init", "-q", "-b", "main")
    (base / "README.rst").write_text("readme\n", encoding="utf-8")
    _git(base, "add", "README.rst")
    _git(base, "commit", "-q", "-m", "first")
    states = []
    for index in range(8):
        path = root / f"s{index}"
        subprocess.run(["cp", "-a", str(base), str(path)], check=True)
        if index % 2:
            _git(path, "rm", "--cached", "-q", "README.rst")
        if index % 4 == 0:
            (path / "scratch.txt").write_text("x\n", encoding="utf-8")
        states.append(cost.MACHINE.State(name=f"s{index}", path=path, facts=cost.MACHINE.sense(path)))
    action = next(a for a in cost.MACHINE.ACTIONS if a.name == "git_rm_cached_tracked")
    return action, states, root


def test_trials_stop_and_the_price_drops_below_trial_always(machine) -> None:
    """End to end on real git: deciding by trial every time costs one execution per decision; keeping
    the lesson costs fewer, and the decisions it stops trialling are still correct."""
    action, states, root = machine
    row = cost.measure_action(action, states, root, copy_seconds=0.001)
    assert row["stage"] == "MEASURED", row
    assert row["trial_always"]["executions"] == len(states)
    assert row["trial_then_know"]["executions"] < len(states)
    assert row["trial_then_know"]["accuracy"] >= row["demonstration"]["accuracy"]
    assert row["trial_always"]["accuracy"] == 1.0
    assert row["exchange_rate"]["saved"] >= 0
