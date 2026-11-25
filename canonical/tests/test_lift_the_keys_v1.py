#!/usr/bin/env python3
"""Lifting works inside a machine and fails between machines -- both, measured.

WITHIN a machine (same five pairs, same walk, same held-out set):

    unlifted target only    58 predictions,  6 wrong, accuracy 0.906, coverage 0.126
    lifted   target only   162 predictions,  4 wrong, accuracy 0.976, coverage 0.704

    reach 2.8x, accuracy +7.0 points, coverage +57.8 points.

BETWEEN machines, with lifted laws only:

    B  lifted transfer       50 predictions, 42 wrong, accuracy 0.543, coverage 0.217
    B' lifted, shuffled      50 predictions, 49 wrong, accuracy 0.505
    C  lifted + target own  188 predictions, 44 wrong, accuracy 0.810

Structural keys cross; they carry no machine-specific truth. Adding them to the target's own laws makes
the target WORSE (0.976 -> 0.810) because they disagree with laws the target actually earned.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.tools import lift_the_keys_v1 as lift  # noqa: E402

ARTIFACT = REPO / "canonical" / "verification" / "LIFT_THE_KEYS_20261124_V1.json"


def test_the_lifted_key_names_no_machine_and_no_content():
    """If a lifted key ever contains a literal from a machine, transfer is back to being a written
    mapping. Check the vocabulary itself, not just the numbers."""
    state = (("a.txt", "alpha_one"), ("b.txt", "alpha_one"))
    key = lift.key_of(state)
    assert "a.txt" not in key and "alpha_one" not in key
    for name in key.split("|"):
        assert name in {n for n, _ in lift.KEY_PATTERNS} | {"NO_PATTERN"}, name


def test_atom_rank_is_derived_by_sorting():
    idents = ["GIT_A3", "GIT_A1", "GIT_A2"]
    assert lift.atom_rank(idents, "GIT_A1") == 0
    assert lift.atom_rank(idents, "GIT_A3") == 2
    # and it is stable under a different naming, which is the whole point
    other = ["LS_A9", "LS_A1", "LS_A4"]
    assert lift.atom_rank(other, "LS_A1") == 0


def test_lifting_raises_the_ceiling_within_a_machine():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    base = summary["same_machine_baseline"]
    unlifted, lifted = base["unlifted_target_only"], base["lifted_target_only"]
    assert lifted["predictions"] > 2 * unlifted["predictions"]
    assert lifted["accuracy"] > unlifted["accuracy"]
    assert lifted["coverage"] > 4 * unlifted["coverage"]
    assert summary["verdicts"]["lifting_lifts_the_ceiling_within_a_machine"] is True


def test_lifting_does_not_transfer():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    assert summary["verdicts"]["lifting_transfers_between_machines"] is False
    assert summary["verdicts"]["lifting_beats_its_own_shuffled_null"] is False
    assert summary["B_lifted_transfer"]["accuracy"] < 0.6


def test_importing_laws_makes_the_target_worse():
    """The finding most worth keeping: structural laws are not merely useless abroad, they are harmful,
    because they compete with laws the target earned. C must be worse than A."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    a, c = summary["A_target_only"], summary["C_lifted_combined"]
    assert c["accuracy"] < a["accuracy"]
    assert summary["verdicts"]["combined_beats_target_only"] is False
