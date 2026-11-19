"""The vocabulary is the artifact: the tests are the counter-examples, not the prose.

Each test here can fail for a reason that would matter. If `mv` shows a multiset change, the fixed
vocabulary was never blind and the whole round is wrong. If `sort` shows one, the same. If the
goal-directed vocabulary cannot solve the rename the fixed one cannot even state, the mechanism does
not buy a request.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "tools"))
sys.path.insert(0, str(ROOT))

import instant_learning_in_a_new_environment_v1 as env  # noqa: E402
import the_vocabulary_is_the_artifact_v1 as vocab  # noqa: E402


def _probe_one(machine: env.Machine, args: dict[str, str]) -> dict[str, dict[str, list[str]]]:
    machine.reset()
    before = machine.read()
    out = {}
    for atom in machine.atoms:
        machine.reset()
        state = machine.read()
        env.execute(atom, machine, args)
        after = machine.read()
        out[atom.ident] = {"fixed": vocab.effect(state, after, vocab.FIXED_VOCABULARY),
                           "full": vocab.effect(state, after, vocab.FULL_VOCABULARY)}
    machine.reset()
    return out


def test_a_rename_is_invisible_to_the_fixed_vocabulary(tmp_path):
    """`mv` keeps every content and every count. A vocabulary of cardinality plus multiset calls it
    inert -- and it is the only atom on that machine that can move a name."""
    machine = env.build_filesystem(tmp_path / "fs")
    machine.root.mkdir(parents=True, exist_ok=True)
    machine.reset()
    state = machine.read()
    holder = next(ident for ident, content in state if content == env.PROBE_OLD)
    effects = _probe_one(machine, {"content": env.PROBE_OLD, "old": env.PROBE_OLD,
                                   "name": holder, "target": "moved_seed"})
    assert effects["FS_A3"]["fixed"] == [], effects["FS_A3"]
    assert set(effects["FS_A3"]["full"]) >= {"PAIRING", "IDENT"}, effects["FS_A3"]


def test_a_sort_moves_nothing_in_the_multiset_and_everything_in_the_order(tmp_path):
    machine = vocab.build_sort(tmp_path / "sort")
    machine.root.mkdir(parents=True, exist_ok=True)
    machine.reset()
    before = machine.read()
    env.execute(next(atom for atom in machine.atoms if atom.ident == "SRT_A1"), machine, {})
    after = machine.read()
    assert vocab.relation_value("MULTISET", before) == vocab.relation_value("MULTISET", after)
    assert vocab.relation_value("ORDER", before) != vocab.relation_value("ORDER", after)
    assert vocab.effect(before, after, vocab.FIXED_VOCABULARY) == []
    assert "ORDER" in vocab.effect(before, after, vocab.FULL_VOCABULARY)


@pytest.mark.parametrize("machine_name", ["FILESYSTEM"])
def test_the_goal_the_fixed_vocabulary_cannot_state_is_solved_by_one_that_can(tmp_path, machine_name):
    """The claim is not a success rate, it is a door: unstateable in the vocabulary, unsolvable; the
    relation the user's goal is about, and the same request is solved and stable on a second read."""
    machines = {machine_name: vocab.MACHINES[machine_name](tmp_path / machine_name.lower())}
    machine = machines[machine_name]
    machine.root.mkdir(parents=True, exist_ok=True)
    machine.reset()
    adaptation = vocab.adapt(machine)
    request = next(r for r in vocab.requests_for(machines) if r.goal == "CONTENT_MOVED_TO_NEW_NAME")
    fixed = vocab.solve(machine, request, vocab.FIXED_VOCABULARY, adaptation)
    directed = vocab.solve(machine, request, (request.relation, "MULTISET"), adaptation)
    assert fixed["stateable"] is False and fixed["solved"] is False, fixed
    assert directed["solved"] is True and directed["stable_on_a_second_read"] is True, directed
    assert directed["atom"] in {atom.ident for atom in machine.atoms}


def test_the_second_pass_reproduces_every_inert_verdict(tmp_path):
    """An inert atom is a claim about every cell. One run is not a fact, so the tool re-probes."""
    machine = env.build_filesystem(tmp_path / "fs")
    machine.root.mkdir(parents=True, exist_ok=True)
    adaptation = vocab.adapt(machine)
    assert all(adaptation["reproduced_by_a_second_pass"].values()), adaptation["reproduced_by_a_second_pass"]
    assert any(not effects for effects in adaptation["union_fixed"].values())
