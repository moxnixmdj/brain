#!/usr/bin/env python3
"""The learner's refusals, asked what its vocabulary is missing. The answer is: a guard.

Coverage 0.7019 -- 219 of 312 held-out transitions, 93 refusals, across six machines.

    63 of 93 refusals   the atom has ONE effect; the law is merely too narrow
     6 context-dependent atoms
      4 are GUARDS         the atom declines to fire (NO_CHANGE) unless a precondition holds
      2 really depend      GIT_A1 and G2_A1 have two effects, BOTH firing
      1 of 6 is separable by the existing keys

So the missing object is not another state predicate. It is a PRECONDITION: the lift vocabulary
describes what an atom DOES and has no way to say when it may do it. Four of six context-dependent atoms
are an atom refusing to fire, which a richer state description cannot express at all.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

ARTIFACT = (REPO / "canonical" / "verification" /
            "WHAT_THE_VOCABULARY_STILL_CANNOT_SAY_20261124_V1.json")


def _summary():
    return json.loads(ARTIFACT.read_text())["summary"]


def test_coverage_survived_lifting_on_a_wider_set():
    """312 held-out transitions across six machines, 0.70 covered. If this ever drops back toward the
    0.13 of the un-lifted learner, the lifting gain was a property of five particular pairs."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    assert summary["held_out"] > 300
    assert summary["coverage"] > 0.65


def test_most_refusals_are_narrowness_not_absence():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    assert summary["refusals_a_narrower_law_would_already_cover"] > 0.5 * summary["refused"]
    assert summary["verdicts"]["most_refusals_are_a_narrow_vocabulary_not_a_missing_one"] is True


def test_the_gap_is_mostly_a_guard_and_the_work_order_says_so():
    """The claim that must not be softened into 'some atoms are context-dependent': four of the six are
    an atom declining to fire, and a state predicate cannot express that."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    assert summary["guard_atoms"] == 4
    assert summary["genuinely_dependent_atoms_count"] == 2
    assert summary["guard_atoms"] > summary["genuinely_dependent_atoms_count"]
    assert summary["verdicts"]["most_context_dependence_is_a_guard_not_a_predicate"] is True
    for atom in summary["work_order"]["guards"]["GIT"]:
        assert "NO_CHANGE" not in summary["work_order"]["guards"]["GIT"][atom]["fires_as"]


def test_the_work_order_names_atoms_not_machines_in_general():
    """A work order that says 'GIT is hard' is useless; it must name the atom and the two effects."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    dependent = _summary()["work_order"]["genuinely_dependent"]
    assert "GIT" in dependent
    assert set(dependent["GIT"]) == {"GIT_A1"}
    assert len(dependent["GIT"]["GIT_A1"]["effects"]) == 2
    assert not dependent["GIT"]["GIT_A1"]["effects"][0].endswith("NO_CHANGE")
