"""Goal-directed vs learn-everything: measured 12 trials vs 36 (3.0x).

These tests pin the three behaviours that make the saving real rather than an accounting trick:

  1. probing STOPS once every needed effect has been witnessed (FILESYSTEM: 2 trials of 10);
  2. an environment that cannot produce a needed effect SAYS SO (TARBALL has no REPLACE);
  3. the goal is read off the requests themselves -- no stored taxonomy of what a goal "means".
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import goal_directed_beats_learn_everything_v1 as GD


def _atom(name, effect):
    return {"atom": name, "effect": effect}


def test_probing_stops_when_the_goal_is_satisfied():
    atoms = [_atom("A1", "PERSIST"), _atom("A2", "INERT"), _atom("A3", "REMOVE"),
             _atom("A4", "REPLACE")]
    got = GD.goal_directed(atoms, ["PERSIST", "REMOVE"])
    assert got["trials"] == 3, "it must stop after A3 satisfies the last needed effect"
    assert got["state"] == "SOLVABLE"
    assert got["satisfied"] == {"PERSIST": "A1", "REMOVE": "A3"}


def test_an_unreachable_effect_is_reported_not_faked():
    atoms = [_atom("A1", "PERSIST"), _atom("A2", "REMOVE")]
    got = GD.goal_directed(atoms, ["PERSIST", "REPLACE"])
    assert got["unsatisfiable"] == ["REPLACE"]
    assert got["state"] == "IMPOSSIBLE-HERE"


def test_inert_atoms_never_satisfy_anything():
    atoms = [_atom("A1", "INERT"), _atom("A2", "INERT"), _atom("A3", "PERSIST")]
    got = GD.goal_directed(atoms, ["PERSIST"])
    assert got["trials"] == 3 and got["satisfied"] == {"PERSIST": "A3"}


def test_goal_directed_is_never_more_expensive_than_learning_everything():
    atoms = [_atom("A1", "INERT"), _atom("A2", "PERSIST"), _atom("A3", "REPLACE")]
    for needed in ([], ["PERSIST"], ["PERSIST", "REPLACE"], ["REMOVE"]):
        gd = GD.goal_directed(atoms, needed)["trials"]
        le = GD.learn_everything(atoms)["trials"]
        assert gd <= le


def test_the_goal_is_read_off_the_requests():
    requests = [{"effect": "PERSIST"}, {"effect": "PERSIST"}, {"effect": "REMOVE"}]
    assert GD.needed_effects_from_requests(requests) == ["PERSIST", "REMOVE"]


def test_duplicate_needs_do_not_inflate_the_goal():
    atoms = [_atom("A1", "PERSIST")]
    assert GD.goal_directed(atoms, ["PERSIST", "PERSIST"])["trials"] == 1


def test_append_is_a_first_class_goal():
    """`tar -rf` on an existing name produces APPEND: a copy in, the original kept."""
    atoms = [_atom("A1", "APPEND")]
    got = GD.goal_directed(atoms, ["APPEND"])
    assert got["state"] == "SOLVABLE" and got["satisfied"] == {"APPEND": "A1"}
