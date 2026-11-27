from __future__ import annotations

import math
import unittest

from canonical.runtime import mysterymechanism_adaptive_planner_v3 as v3


class MysteryMechanismAdaptivePlannerV3Tests(unittest.TestCase):
    def test_generic_disagreement_core_is_strictly_bounded(self):
        bounds={"x":[0.1,10.0],"z":[0.2,20.0]}
        rows=[
            {"x":0.1,"z":0.2},{"x":10.0,"z":0.2},
            {"x":0.1,"z":20.0},{"x":1.0,"z":2.0},{"x":3.0,"z":5.0},
        ]
        predictors=[
            lambda p:2+p["x"]+p["z"],
            lambda p:2+p["x"]*p["z"],
            lambda p:2+math.sqrt(p["x"])*p["z"]**(1/3),
        ]
        out=v3.choose_from_predictors(rows,bounds=bounds,predictors=predictors)
        self.assertEqual(out["status"],"ADAPTIVE_CANDIDATE_DISAGREEMENT",out)
        self.assertGreater(out["normalized_disagreement"],0.0)
        for name,(lo,hi) in v3._bounds(bounds).items():
            self.assertGreaterEqual(out["point"][name],lo)
            self.assertLessEqual(out["point"][name],hi)

    def test_exact_observed_point_is_not_reprobed(self):
        bounds={"x":[0.0,1.0],"z":[0.0,1.0]}
        rows=[
            {"x":0.0,"z":0.0},{"x":1.0,"z":0.0},{"x":0.0,"z":1.0},
            {"x":0.5,"z":0.5},{"x":0.25,"z":0.75},
        ]
        out=v3.choose_from_predictors(
            rows,bounds=bounds,
            predictors=[lambda p:p["x"]+p["z"],lambda p:p["x"]*p["z"]],
            grid_levels=5,
        )
        point=tuple(out["point"][k] for k in sorted(bounds))
        observed={tuple(r[k] for k in sorted(bounds)) for r in rows}
        self.assertNotIn(point,observed)

    def test_first_three_active_probes_seed_then_replan(self):
        bounds={"x":[0.1,10.0],"z":[0.2,20.0]}
        rows=[{"x":0.7,"z":1.1,"out":2.3},{"x":2.0,"z":4.0,"out":5.2}]
        for used in range(3):
            out=v3.next_experiment(
                rows,bounds=bounds,active_experiments_used=used,target="out"
            )
            self.assertEqual(out["status"],"SPACE_FILLING_MAXIMIN",out)
            p=out["point"]
            rows.append({"x":p["x"],"z":p["z"],"out":1.0+p["x"]*p["z"]})
            self.assertTrue(out["replan_required_after_observation"])
        self.assertEqual(len(rows),5)
        out=v3.next_experiment(
            rows,bounds=bounds,active_experiments_used=3,target="out"
        )
        self.assertIn(
            out["status"],
            {"ADAPTIVE_CANDIDATE_DISAGREEMENT","SPACE_FILLING_MAXIMIN"},
            out,
        )
        self.assertEqual(out["remaining_active_experiments_after_this"],1)
        for name,(lo,hi) in v3._bounds(bounds).items():
            self.assertTrue(lo <= out["point"][name] <= hi)

    def test_budget_exhausts_exactly_at_2d_plus_1(self):
        out=v3.next_experiment(
            [{"x":0.2,"z":0.3,"out":1.0},{"x":0.8,"z":0.7,"out":2.0}],
            bounds={"x":[0,1],"z":[0,1]},
            active_experiments_used=5,
        )
        self.assertEqual(out["status"],"ACTIVE_BUDGET_EXHAUSTED")
        self.assertIsNone(out["point"])
        self.assertEqual(out["active_budget"],5)

    def test_public_viscosity_dev_example_finalizer_preserves_zero_credit(self):
        rows=[
            {"x1":0.5944,"x2":1.9188,"out":12.2245},
            {"x1":0.5044,"x2":0.2068,"out":10.3732},
            {"x1":0.05,"x2":0.05,"out":4.3715},
            {"x1":0.70,"x2":0.05,"out":30.6686},
            {"x1":0.05,"x2":30.0,"out":2.3912},
            {"x1":0.70,"x2":30.0,"out":16.3743},
            {"x1":0.375,"x2":1.225,"out":5.7241},
        ]
        out=v3.finalize(
            rows,bounds={"x1":[0.05,0.70],"x2":[0.05,30.0]},
            target="out",fit_threshold=0.05,
        )
        self.assertEqual(
            out["status"],
            "CANDIDATE_READY__UNVERIFIED_ON_PRIVATE_STRUCTURAL_PROBES",
            out,
        )
        self.assertLess(out["conservative_nrmse"],0.05,out)
        self.assertFalse(out["private_score_claimed"])
        self.assertEqual(out["acceptance_credit_delta"],0)
        self.assertEqual(out["capability_credit_delta"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
