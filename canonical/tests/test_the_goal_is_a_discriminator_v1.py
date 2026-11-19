"""The goal is a discriminator: the tests pin the four things that would make the claim fake.

If one judgment already identified the goal, ambiguity would be a story. If asking well could cost
more than asking in order, the active step would be decoration. If the agent acted while its survivors
disagreed, a false accept would be one step away. If no discriminator came back for a real pool, the
grammar would not contain the answer.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "tools"))
sys.path.insert(0, str(ROOT))

import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_goal_is_a_discriminator_v1 as goal_tool  # noqa: E402

State = tuple[tuple[str, str], ...]


def _filesystem(tmp_path, name="fs"):
    machine = env.build_filesystem(tmp_path / name)
    machine.root.mkdir(parents=True, exist_ok=True)
    machine.reset()
    return machine


def _args(machine):
    holder = next(ident for ident, content in machine.read() if content == env.PROBE_OLD)
    return {"content": env.PROBE_OLD, "old": env.PROBE_OLD, "name": holder, "target": "moved_seed"}


def test_the_grammar_instantiates_only_literals_the_machine_produced():
    """A term exists because a real execution made it true somewhere, not because it was written."""
    states = [(("seed", "alpha"), ("seed2", "beta"))]
    texts = {term.text for term in goal_tool.terms_from(states)}
    assert "card==2" in texts and "count[alpha]==1" in texts
    assert "has[seed]=alpha" in texts
    assert not any("gamma" in text for text in texts)  # a literal nobody produced is not a term


def test_one_judgment_leaves_more_than_one_discriminator():
    """Identifiability, measured: after a single judgment the answer is a set, not a term."""
    terms = goal_tool.terms_from([(("a", "x"),), (("a", "y"),)])
    goal_tool.TERMS_BY_TEXT.clear()
    goal_tool.TERMS_BY_TEXT.update({term.text: term for term in terms})
    accepted = [(("a", "x"),)]
    rejected = [(("a", "y"),)]
    survivors = goal_tool.minimal_discriminators(terms, accepted, rejected)
    assert len(survivors) > 1, survivors
    assert all(d.holds(accepted[0]) and not d.holds(rejected[0]) for d in survivors)


def test_the_mechanism_prefers_the_smallest_conjunction_that_separates():
    terms = [goal_tool.Term("card==1", lambda s: len(s) == 1),
             goal_tool.Term("has[a]=x", lambda s: ("a", "x") in s),
             goal_tool.Term("has[b]=y", lambda s: ("b", "y") in s)]
    goal_tool.TERMS_BY_TEXT.clear()
    goal_tool.TERMS_BY_TEXT.update({term.text: term for term in terms})
    survivors = goal_tool.minimal_discriminators(terms, [(("a", "x"),)], [(("a", "y"),)])
    assert survivors and all(len(d.terms) == 1 for d in survivors), survivors


def test_asking_well_never_costs_more_than_asking_in_order(tmp_path):
    machine = _filesystem(tmp_path)
    args = _args(machine)
    machine_spec = goal_tool.Goal("FILESYSTEM", "the seed content under a new name", args,
                                  lambda s: ("moved_seed", env.PROBE_OLD) in s)
    pool = goal_tool.pool_for(machine, args)
    active = goal_tool.learn(machine_spec, pool, "active")
    in_order = goal_tool.learn(machine_spec, pool, "pool")
    assert active["judgments"] <= in_order["judgments"]
    assert active["behaviour"]["behaviourally_identified"] is True


def test_no_action_is_taken_while_the_survivors_disagree(tmp_path):
    """Ambiguity is not permission. If no reachable state satisfies every survivor, refuse."""
    machine = _filesystem(tmp_path)
    goal_tool.TERMS_BY_TEXT.clear()
    goal_tool.TERMS_BY_TEXT.update({
        "card==2": goal_tool.Term("card==2", lambda s: len(s) == 2),
        "card==3": goal_tool.Term("card==3", lambda s: len(s) == 3)})
    survivors = [goal_tool.Discriminator(("card==2",)), goal_tool.Discriminator(("card==3",))]
    goal = goal_tool.Goal("FILESYSTEM", "contradictory", _args(machine), lambda s: True)
    outcome = goal_tool.plan_under(goal, machine, survivors)
    assert outcome["planned"] is False
    assert outcome["false_accept"] is False
    assert outcome["why"] == "NO_ACTION_REACHES_A_STATE_ALL_SURVIVORS_ACCEPT"
