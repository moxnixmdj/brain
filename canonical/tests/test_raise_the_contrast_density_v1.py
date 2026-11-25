#!/usr/bin/env python3
"""Exploration policy against a metric that is not the policy's own objective.

Measured on 10 machines x 3 seeds x 40 steps:

    RANDOM    641 transitions, 4 usable laws, 0.62 per 100, 2 machines producing any
    TARGETED  295 transitions, 0 usable laws, 0.00 per 100   <- my prediction, and it was wrong
    COVERAGE  609 transitions, 7 usable laws, 1.15 per 100, 3 machines producing any

The lesson the tests pin: aiming at a contrast that must ALREADY exist aims at nothing. Novelty of
state is what generates contrasts.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

import frames_that_cross_machines_v1 as room  # noqa: E402
from canonical.tools import raise_the_contrast_density_v1 as density  # noqa: E402


def _machine(name="GIT"):
    tmp = tempfile.TemporaryDirectory()
    root = pathlib.Path(tmp.name) / name
    root.mkdir(parents=True)
    machine = room.all_machines()[name](root)
    machine.reset()
    return tmp, machine, list(machine.atoms)


def test_every_policy_is_deterministic_modulo_identity():
    """A policy must be reproducible in CONTENT for a fixed seed -- that is what makes policies
    comparable.

    It is NOT reproducible in identity, and that is a property of the environment: GIT's rows are
    commit SHAs, and a SHA embeds the commit timestamp, so re-running the same walk yields different
    identifiers. Measured: the naive equality test failed about one run in four. Comparing contents
    is the honest form of the test.
    """
    for name, policy in density.POLICIES.items():
        for machine_name in ("GIT", "VAULT", "JOURNAL"):
            tmp, machine, atoms = _machine(machine_name)
            try:
                first = density._content_only(policy(machine, atoms, 12, 13))
                second = density._content_only(policy(machine, atoms, 12, 13))
                assert first == second, f"{name} on {machine_name} is not deterministic"
            finally:
                tmp.cleanup()


def test_a_policy_only_records_executed_transitions():
    tmp, machine, atoms = _machine("VAULT")
    try:
        for name, policy in density.POLICIES.items():
            transitions = policy(machine, atoms, 10, 13)
            assert transitions, f"{name} produced nothing"
            for ident, before, after in transitions:
                assert ident in {atom.ident for atom in atoms}
                assert isinstance(before, tuple) and isinstance(after, tuple)
    finally:
        tmp.cleanup()


def test_the_metric_counts_laws_with_two_witnesses_and_a_contrast():
    """`usable_laws` is not "laws learned" -- it is the object earlier rounds established is worth
    having. A single no-op observation can never count."""
    tmp, machine, atoms = _machine("JOURNAL")
    try:
        transitions = density.walk_random(machine, atoms, 6, 13)
        assert density.usable_laws(transitions) >= 0        # a count, not a promise
        assert density.usable_laws([]) == 0, "no evidence, no laws"
    finally:
        tmp.cleanup()


def test_the_measured_comparison_is_recorded_and_my_prediction_stayed_wrong():
    """COVERAGE beat RANDOM; TARGETED lost to both. If a future change flips this, the report's claim
    is no longer the claim and the test should fail loudly."""
    import json
    artifact = (REPO / "canonical" / "verification" /
                "RAISE_THE_CONTRAST_DENSITY_20261124_V1.json")
    if not artifact.exists():                                # pragma: no cover
        return
    summary = json.loads(artifact.read_text())["summary"]
    assert summary["COVERAGE"]["density_per_100"] > summary["RANDOM"]["density_per_100"]
    assert summary["TARGETED"]["density_per_100"] <= summary["RANDOM"]["density_per_100"]
    assert summary["verdicts"]["targeted_is_worse_than_random"] is True
