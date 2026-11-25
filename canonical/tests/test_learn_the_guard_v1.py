#!/usr/bin/env python3
"""The guard was the named work order. It covers nothing, and it is harmful when it speaks.

Six machines, 293 held-out transitions, guards learned from a NON-deduplicated walk because
`budgeted_walk`'s dedup discards exactly the repeated observations that are negative witnesses:

    blocked witnesses in the walk      386
    guard keys learned                  50
    guard keys with two witnesses       37

    A  no guards                 227 predictions, 42 wrong, accuracy 0.844, coverage 0.699
    B  guards override           227 predictions, 65 wrong, accuracy 0.777
    C  guards, two witnesses     227 predictions, 46 wrong, accuracy 0.832
    D  guards, fallback only     227 predictions, 42 wrong, accuracy 0.844  <- bit-identical to A

D predicts exactly what A predicts, on every machine. **Guards cover zero refusals**: a refusal is a
held-out state whose (atom, key) pair the walk never visited, so there is no witness of either kind, and
a guard learned from observed keys cannot speak about an unobserved one. Guard support is the same
evidence requirement as law support, so guards add nothing where coverage is missing.

B and C are worse than A because a blocked witness at a key is perfectly compatible with a positive
witness at the same key: the key does not determine firing, so a guard that overrides a law destroys it.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.tools import learn_the_guard_v1 as guard  # noqa: E402
from canonical.tools import lift_the_keys_v1 as lift  # noqa: E402

ARTIFACT = REPO / "canonical" / "verification" / "LEARN_THE_GUARD_20261124_V1.json"


def test_a_no_op_is_recorded_as_a_guard():
    idents = ["A1", "A2"]
    state = (("r1", "c1"), ("r2", "c2"))
    walked = [("A1", state, state), ("A1", state, state)]
    guards = guard.learn_guards(walked, idents)
    assert guards, "a repeated no-op must produce a guard"
    assert all(count >= 2 for count in guards.values())


def test_the_guard_and_a_law_can_share_a_key_so_override_is_wrong():
    """The unit-level statement of why arm B loses: with both a blocking witness and a firing witness at
    one key, neither claim is entitled to override the other."""
    idents = ["A1"]
    state = (("r1", "c1"),)
    other = (("r1", "c9"),)
    guard_map = guard.learn_guards([("A1", state, state)], idents)
    laws = lift.lift([("A1", state, other)], idents)
    overriding = guard.predict_with_guards(laws, guard_map, 0, state, fallback_only=False)
    falling_back = guard.predict_with_guards(laws, guard_map, 0, state, fallback_only=True)
    assert overriding["effect"] == "NO_CHANGE"
    assert falling_back["status"] == "PREDICTS" and falling_back["effect"] != "NO_CHANGE"


def test_guards_cover_no_refusals_at_all():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    a, d = summary["A_no_guards"], summary["D_guards_fallback_only"]
    assert a == d, "fallback-only guards must be literally inactive, not merely unhelpful"
    assert summary["verdicts"]["guards_used_only_as_a_fallback_cover_refusals"] is False


def test_guards_are_harmful_when_they_speak():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    assert summary["B_guards"]["accuracy"] < summary["A_no_guards"]["accuracy"]
    assert summary["C_guards_strict"]["accuracy"] < summary["A_no_guards"]["accuracy"]
    assert summary["verdicts"]["the_guard_and_the_law_cannot_share_a_key"] is True


def test_the_blocked_evidence_exists_and_is_therefore_not_the_problem():
    """The round's premise was right -- 386 blocked witnesses were sitting in the walk unused. The
    conclusion is that having the evidence is not the same as having the coverage."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = json.loads(ARTIFACT.read_text())["summary"]
    assert summary["blocked_witnesses"] > 300
    assert summary["guards_learned"] > 40
    assert summary["verdicts"]["the_walk_contains_blocked_witnesses"] is True
