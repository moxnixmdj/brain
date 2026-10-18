#!/usr/bin/env python3
"""The machine must refuse to call a route 'fastest' on incomplete data.

This is the owner's central requirement, stated in their own words:

    "After it gets the data, the data must be complete. If it just makes the
    prediction on just some data, it will extrapolate: 'this is the fastest way
    based only on the data that it has.' There are a lot of better and faster
    ways that it doesn't know anything about...  It must know literally all the
    data...  Its extrapolations must be global all the time."

    Their worked example: one paper on the internet says the fastest way to a
    million dollars is YouTube videos. If that is the only thing the machine
    has read, it concludes YouTube -- "and this is a huge mistake, because the
    world is very wide and very big, literally huge."

So these tests do not measure whether the chase improves a number. They measure
whether the chase REFUSES to act when the option set cannot support the claim
it is about to make. A machine that says "I don't have the data" is behaving
correctly; a machine that confidently acts on one source is not.
"""

from __future__ import annotations

import unittest
from typing import Any

from execution_guard import goal_chase_v1 as gc
from execution_guard import target_chase_driver_v1 as chase

GOAL = "make me a million dollars"


def _one_source_option() -> dict[str, Any]:
    """The owner's exact scenario: a single source, and it is only a lead."""
    return {
        "kind": "QUERY",
        "query": "fastest way to make a million dollars",
        "source_id": "web_paper_1",
        "candidate_authority": "CANDIDATE_ONLY",
    }


def _three_channels_one_verified() -> list[dict[str, Any]]:
    """Three genuinely independent channels, one independently verified."""
    return [
        {"kind": "QUERY", "query": "q1", "source_id": "web",
         "candidate_authority": "CANDIDATE_ONLY"},
        {"kind": "QUERY", "query": "q2", "source_id": "registry",
         "candidate_authority": "CANDIDATE_ONLY"},
        {"kind": "QUERY", "query": "q3", "source_id": "market_data",
         "candidate_authority": "VERIFIED", "independently_verified_by": "oracle.money.v1"},
    ]


class CompletenessGateTests(unittest.TestCase):
    def test_one_source_is_not_complete(self):
        """One paper saying 'YouTube' must not license a conclusion."""
        gate = gc.completeness_gate_for(GOAL)
        verdict = gate({"known_options": [_one_source_option()]})
        self.assertFalse(verdict["complete"])
        self.assertIn("CHANNEL", verdict["reason"])

    def test_ten_rows_from_one_source_are_still_one_source(self):
        """Correlated channels are discounted: ten copies of one claim is one claim."""
        gate = gc.completeness_gate_for(GOAL)
        rows = [dict(_one_source_option(), query=f"q{i}") for i in range(10)]
        verdict = gate({"known_options": rows})
        self.assertFalse(verdict["complete"])

    def test_candidates_alone_are_never_complete(self):
        """Candidates are leads about where to look, not data.

        However many there are, a set of pure candidates cannot back a claim
        about the fastest way. This is the one that stops the machine from
        acting on a wide-looking set that has never been checked.
        """
        gate = gc.completeness_gate_for(GOAL)
        rows = [
            {"source_id": f"chan{i}", "candidate_authority": "CANDIDATE_ONLY"}
            for i in range(6)
        ]
        verdict = gate({"known_options": rows})
        self.assertFalse(verdict["complete"])
        self.assertIn("CANDIDATE_ONLY", verdict["reason"])

    def test_nonexistence_claim_from_partial_search_is_refused(self):
        gate = gc.completeness_gate_for(GOAL)
        verdict = gate({"known_options": _three_channels_one_verified()
                        + [{"source_id": "x", "nonexistence_claim_authorized": True}]})
        self.assertFalse(verdict["complete"])
        self.assertIn("NONEXISTENCE", verdict["reason"])

    def test_gate_fails_closed_on_error(self):
        """An exception must block, never permit."""
        gate = gc.completeness_gate_for(GOAL)
        self.assertFalse(gate({"known_options": [object()]})["complete"])
        self.assertFalse(gate({})["complete"])

    def test_independent_verified_evidence_passes(self):
        gate = gc.completeness_gate_for(GOAL)
        verdict = gate({"known_options": _three_channels_one_verified()})
        self.assertTrue(verdict["complete"])
        self.assertEqual(verdict["channels"], 3)


class ChaseRefusesToActOnIncompleteData(unittest.TestCase):
    """End-to-end: the chase must not act, and must say why."""

    def _run(self, options: list[dict[str, Any]]) -> tuple[dict[str, Any], int]:
        acted = {"n": 0}

        def measure() -> float:
            return 0.0

        def act(ctx: dict[str, Any]) -> dict[str, Any]:
            acted["n"] += 1
            return {"did": "commit to a route"}

        result = chase.run(
            goal=GOAL,
            target=1_000_000.0,
            direction="maximize",
            unit="USD",
            measure=measure,
            act=act,
            max_rounds=6,
            patience=2,
            # no options_provider: nothing can widen the set, so if the gate
            # blocks, the chase has to admit it rather than quietly proceed
            completeness_gate=gc.completeness_gate_for(GOAL),
            context={"options": list(options)},
        )
        return result, acted["n"]

    def test_chase_does_not_act_on_one_source(self):
        """The owner's scenario. Acting here would be the 'YouTube' mistake."""
        result, acted = self._run([_one_source_option()])
        self.assertEqual(acted, 0, "the chase acted on a single unverified source")
        self.assertEqual(result["status"], chase.INCOMPLETE_DATA)
        self.assertFalse(result["pass"])

    def test_incomplete_data_is_not_reported_as_stuck(self):
        """'I can't move the number' and 'I lack the data' are different.

        Collapsing them is how the machine hides the one failure the owner most
        wants reported.
        """
        result, _ = self._run([_one_source_option()])
        self.assertNotEqual(result["status"], chase.STUCK)
        self.assertNotEqual(result["status"], chase.BOUND)
        self.assertIn("INCOMPLETE", result["status"])

    def test_chase_acts_when_evidence_is_independent_and_verified(self):
        result, acted = self._run(_three_channels_one_verified())
        self.assertGreater(acted, 0, "gate blocked a complete, verified option set")


if __name__ == "__main__":
    unittest.main()
