from __future__ import annotations

import math
import unittest

from canonical.runtime import mysterymechanism_active_controller_v1 as c


class MysteryMechanismActiveControllerTests(unittest.TestCase):
    def test_2d_budget_is_exact_and_sequential(self):
        bounds={"x1":[1.0,1000.0],"x2":[0.2,10.0]}
        def law(x1,x2):
            return (
                2.3
                + 4.7
                * x1**0.5
                * (1+(x1/940.0)**0.625)**0.8
                * x2**(1.0/3.0)
                / (1+(0.4/x2)**(2.0/3.0))**0.25
            )

        observations=[
            {"x1":7.0,"x2":0.7,"out":law(7.0,0.7)},
            {"x1":120.0,"x2":3.0,"out":law(120.0,3.0)},
        ]
        seen={(7.0,0.7),(120.0,3.0)}
        strategies=[]
        for used in range(5):
            nxt=c.next_experiment(
                bounds=bounds,
                observations=observations,
                target="out",
                active_experiments_used=used,
            )
            self.assertEqual(nxt["status"],"EXPERIMENT_REQUIRED")
            point=nxt["point"]
            key=(round(point["x1"],12),round(point["x2"],12))
            self.assertNotIn(key,seen)
            seen.add(key)
            observations.append({
                "x1":point["x1"],
                "x2":point["x2"],
                "out":law(point["x1"],point["x2"]),
            })
            strategies.append(nxt["strategy"])

        self.assertEqual(len(observations),7)
        self.assertIn("MAXIMIZE_SURVIVING_CANDIDATE_DISAGREEMENT",strategies)
        exhausted=c.next_experiment(
            bounds=bounds,
            observations=observations,
            target="out",
            active_experiments_used=5,
        )
        self.assertEqual(exhausted["status"],"ACTIVE_BUDGET_EXHAUSTED")
        self.assertIsNone(exhausted["point"])

        final=c.finalize(
            bounds=bounds,
            observations=observations,
            target="out",
            active_experiments_used=5,
            fit_threshold=0.03,
            loo_threshold=0.08,
        )
        self.assertEqual(final["status"],"EXECUTABLE_CANDIDATE_READY__UNVERIFIED")
        self.assertTrue(final["expression"])
        self.assertEqual(final["acceptance_credit_delta"],0)
        self.assertFalse(final["fresh_reality_authority"])

    def test_first_phase_maximizes_geometric_coverage(self):
        bounds={"a":[0.1,100.0],"b":[0.01,1.0]}
        observations=[
            {"a":1.0,"b":0.1,"y":2.0},
            {"a":2.0,"b":0.2,"y":3.0},
        ]
        nxt=c.next_experiment(
            bounds=bounds,
            observations=observations,
            target="y",
            active_experiments_used=0,
        )
        self.assertEqual(nxt["strategy"],"MAXIMIN_IDENTIFIABILITY_COVERAGE")
        self.assertEqual(nxt["candidate_count"],0)
        self.assertEqual(nxt["remaining_active_experiments_after_this"],4)

    def test_insufficient_evidence_fails_closed(self):
        out=c.finalize(
            bounds={"x":[1.0,10.0]},
            observations=[
                {"x":1.0,"y":1.0},
                {"x":2.0,"y":4.0},
            ],
            target="y",
            active_experiments_used=0,
        )
        self.assertEqual(out["status"],"INSUFFICIENT_VISIBLE_EVIDENCE__FAIL_CLOSED")
        self.assertIsNone(out["expression"])
        self.assertEqual(out["acceptance_credit_delta"],0)

    def test_budget_overrun_is_rejected(self):
        with self.assertRaises(Exception):
            c.next_experiment(
                bounds={"x":[1.0,10.0]},
                observations=[
                    {"x":1.0,"y":1.0},
                    {"x":2.0,"y":4.0},
                ],
                target="y",
                active_experiments_used=4,
                budget=3,
            )


if __name__=="__main__":
    unittest.main(verbosity=2)
