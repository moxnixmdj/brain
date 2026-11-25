#!/usr/bin/env python3
"""Tests for budgeted exploration and for the one rule that makes a probe evidence.

Two things here were learned by running the instrument, not by designing it:

  * `explore(depth)` is exhaustive, so nothing is ever unknown and acquisition has nothing to ask.
    Measured: every second-witness candidate was a HELD-OUT state, which is banned. Acquisition only
    becomes meaningful under a step budget, which is also the only regime a real environment offers.
  * A probe that runs the atom and records whatever happened always "confirms" its own prediction.
    A question is only evidence when the answer could have gone the other way.
"""
from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

import frames_that_cross_machines_v1 as room  # noqa: E402
import tempfile  # noqa: E402

from canonical.tools import acquire_the_second_witness_v1 as acquire  # noqa: E402
from canonical.swe_kernel import safe_action_model_v1 as sam  # noqa: E402


def _machine(name):
    tmp = tempfile.TemporaryDirectory()
    root = pathlib.Path(tmp.name) / name
    root.mkdir(parents=True, exist_ok=True)
    machine = room.all_machines()[name](root)
    machine.reset()
    return tmp, machine


def test_a_budgeted_walk_is_deterministic_for_a_seed():
    """State order used to depend on Python's per-process string hashing, so the same seed produced a
    different split on every invocation. A budgeted walk must be reproducible or no number in this
    module means anything."""
    tmp, machine = _machine("VAULT")
    try:
        atoms = list(machine.atoms)
        first = acquire.budgeted_walk(machine, atoms, 20, 13)
        second = acquire.budgeted_walk(machine, atoms, 20, 13)
        assert first == second
        other = acquire.budgeted_walk(machine, atoms, 20, 7)
        assert first != other, "a different seed must explore something different"
    finally:
        tmp.cleanup()


def test_a_budgeted_walk_leaves_states_unobserved():
    """The reason acquisition has anything to do: after a budget, some reachable states were never
    seen. Exhaustive `explore` cannot offer this, and that is why the earlier arms probed nothing."""
    tmp, machine = _machine("GIT")
    try:
        atoms = list(machine.atoms)
        walked = acquire.budgeted_walk(machine, atoms, 12, 13)
        seen = {before for _ident, before, _after in walked}
        assert 0 < len(seen) < len(atoms) ** 3, "a short walk must not have seen everything"
    finally:
        tmp.cleanup()


def test_a_walk_records_only_executed_transitions():
    tmp, machine = _machine("SQLITE")
    try:
        atoms = list(machine.atoms)
        walked = acquire.budgeted_walk(machine, atoms, 10, 13)
        assert walked, "a walk of 10 steps must produce at least one transition"
        for ident, before, after in walked:
            assert ident in {atom.ident for atom in atoms}
            assert isinstance(before, tuple) and isinstance(after, tuple)
    finally:
        tmp.cleanup()


def test_a_law_confirmed_by_a_probe_still_states_the_projected_effect():
    """One rule, and it is the reason a probe can falsify: the recorded law carries the effect the
    probe actually measured (compare `run`'s arm C, which drops the law when the effect differs),
    never the effect that was hypothesised. `sam.Observation.effect` is the only source."""
    one = (("0", "alpha"),)
    observation = sam.Observation.of("TOUCH", one, one, [("CARD", "WHOLE", None, "count_is", 1)])
    assert observation.effect == (frozenset(), frozenset()), (
        "an unchanged state is a no-op effect, and that is what a confirmed law must predict")
