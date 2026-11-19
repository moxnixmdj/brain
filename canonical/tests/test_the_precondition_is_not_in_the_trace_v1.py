"""The round's own tests: the oracle, the sensor, and the two arithmetic facts the arms rest on.

These are real `git` processes against a repository made with `git init`, so nothing here is a stub.
The three things that could silently fake the round's result are each pinned:

  * the oracle — a failure whose stderr names an infrastructure problem is not evidence about a
    precondition, and must be classified AMBIGUOUS rather than counted as "does not apply";
  * the sensor — a fact that cannot be observed cannot refute a requirement, so `sense` must report
    only what it actually reads, and must report it for a state where it is false as well as true;
  * the arm-A mechanism — the intersection of successes SHRINKS as successes are added, which is why
    more demonstrations make the rule broader rather than more correct.
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

import the_precondition_is_not_in_the_trace_v1 as pre  # noqa: E402


def _git(repo: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com",
                           *args], cwd=str(repo), capture_output=True, text=True, check=False)


@pytest.fixture()
def repo(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "machine"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    (root / "README.rst").write_text("readme\n", encoding="utf-8")
    _git(root, "add", "README.rst")
    _git(root, "commit", "-q", "-m", "first")
    return root


def test_every_action_states_what_it_turns_on() -> None:
    """An action with no stated precondition cannot be checked, so the table must be total."""
    assert {a.name for a in pre.ACTIONS} == set(pre.INTENDED)


def test_the_sensor_sees_a_stash_the_moment_it_exists(repo: pathlib.Path) -> None:
    assert "stash.absent" in pre.sense(repo)
    (repo / "README.rst").write_text("edited\n", encoding="utf-8")
    _git(repo, "add", "README.rst")
    _git(repo, "stash", "push", "-q")
    facts = pre.sense(repo)
    assert "stash.present" in facts
    assert "stash.absent" not in facts


def test_the_oracle_reads_the_program_and_not_my_opinion(repo: pathlib.Path) -> None:
    """`git stash pop` says it applies only when a stash exists. The action list does not decide."""
    state = pre.State(name="s", path=repo, facts=pre.sense(repo))
    pop = next(a for a in pre.ACTIONS if a.name == "git_stash_pop")
    outcome, _note = pre.verdict(state, pop, repo.parent)
    assert outcome == pre.DOES_NOT, outcome

    (repo / "README.rst").write_text("edited\n", encoding="utf-8")
    _git(repo, "add", "README.rst")
    _git(repo, "stash", "push", "-q")
    state = pre.State(name="s", path=repo, facts=pre.sense(repo))
    outcome, _note = pre.verdict(state, pop, repo.parent)
    assert outcome == pre.APPLIES, outcome


def test_an_infrastructure_failure_is_not_evidence_about_a_condition(repo: pathlib.Path) -> None:
    state = pre.State(name="s", path=repo, facts=pre.sense(repo))
    infrafail = pre.Action("infra", ("sh", "-c", "echo 'permission denied' >&2; exit 1"),
                           "a failure that says nothing about applicability")
    outcome, _note = pre.verdict(state, infrafail, repo.parent)
    assert outcome == pre.AMBIGUOUS


def test_the_oracle_runs_in_a_copy_and_leaves_the_state_alone(repo: pathlib.Path) -> None:
    """An observation that destroys the state it measured cannot be repeated, so it is not usable."""
    state = pre.State(name="s", path=repo, facts=pre.sense(repo))
    marker = repo / "survives.txt"
    marker.write_text("still here\n", encoding="utf-8")
    remover = pre.Action("rm", ("rm", "-f", "survives.txt"), "a mutation")
    assert pre.verdict(state, remover, repo.parent)[0] == pre.APPLIES
    assert marker.exists(), "the trial mutated the state instead of a copy of it"


def test_intersection_shrinks_as_successes_are_added() -> None:
    """More demonstrations of one action make the licensed rule BROADER, never more correct."""
    one = pre.intersection([{"a", "b", "c"}])
    two = pre.intersection([{"a", "b", "c"}, {"a", "b"}])
    assert one == frozenset({"a", "b", "c"})
    assert two == frozenset({"a", "b"})
    assert two < one


def test_the_exact_precondition_is_found_when_the_vocabulary_contains_it() -> None:
    table = [(frozenset({"stash.present", "clean"}), True),
             (frozenset({"stash.present", "dirty"}), True),
             (frozenset({"stash.absent", "clean"}), False),
             (frozenset({"stash.absent", "dirty"}), False)]
    assert pre.exact_precondition(table, ("stash.present", "stash.absent", "clean", "dirty")) == (
        "stash.present",)


def test_no_rule_is_invented_when_the_vocabulary_cannot_separate_the_classes() -> None:
    """Two states with the SAME facts and different outcomes: no requirement over them explains both."""
    table = [(frozenset({"file.present"}), True), (frozenset({"file.present"}), False)]
    assert pre.exact_precondition(table, ("file.present",)) is None


def test_a_class_with_no_states_licenses_nothing() -> None:
    assert pre.exact_precondition([(frozenset({"a"}), True)], ("a",)) is None


def test_accuracy_reports_the_base_rate_rule_honestly() -> None:
    rows = [(frozenset({"x"}), True), (frozenset({"y"}), False)]
    always = pre.accuracy(lambda facts: True, rows)
    assert always == {"accuracy": 0.5, "precision": 0.5, "recall": 1.0, "n": 2}
    never = pre.accuracy(lambda facts: False, rows)
    assert never["accuracy"] == 0.5 and never["recall"] == 0.0
