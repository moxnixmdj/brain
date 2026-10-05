import unittest
from canonical.runtime import h100_verified_capability_registry_v1 as r
from canonical.runtime import h100_zero_learned_transfer_v1 as t

class H100VerifiedCapabilityRegistryTests(unittest.TestCase):
    def test_registry_contains_only_prior_verified_transfer_families(self):
        snap=r.registry_snapshot()
        self.assertEqual(snap["entry_count"],3)
        self.assertEqual(snap["persistent_learned_bytes"],0)
        self.assertEqual({x["family"] for x in snap["entries"]},{"linear_trend_sinusoid","exp_abs","threshold_step"})
        for row in snap["entries"]:
            self.assertIn("H100_ZERO_LEARNED_TRANSFER_PUBLIC_RUNNER_VERIFICATION",row["prior_verification"])

    def test_frozen_transfer_tasks_hit_library_before_raw_search(self):
        cases=[
            ("SIN_B","CAP_LINEAR_TREND_SINUSOID_V1"),
            ("EXP_B","CAP_EXP_ABS_V1"),
            ("STEP_B","CAP_THRESHOLD_STEP_V1"),
        ]
        xs=[-4,-3,-2,-1,0,1,2,3,4]
        for task,cap in cases:
            rows=t._rows(task,xs)
            out=r.resolve_verified_capability(rows,target="y",input_name="x")
            self.assertEqual(out["status"],"LIBRARY_HIT__VERIFY_BEFORE_USE",out)
            self.assertEqual(out["match"]["capability_id"],cap)
            self.assertEqual(out["raw_synthesis_attempts_before_hit"],0)

    def test_predictions_remain_exact_on_distinct_points(self):
        rows=t._rows("EXP_B",[-4,-3,-2,-1,0,1,2,3,4])
        out=r.resolve_verified_capability(rows,target="y",input_name="x")
        for x in (-3.7,-0.7,0.6,2.8):
            got=r.predict(out,{"x":x})
            want=t._truth("EXP_B",x)
            self.assertAlmostEqual(got,want,places=9)

    def test_out_of_family_cubic_fails_closed_to_raw_synthesis(self):
        rows=[{"x":float(x),"y":float(x**3+0.123*x)} for x in range(-5,6)]
        out=r.resolve_verified_capability(rows,target="y",input_name="x")
        self.assertEqual(out["status"],"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED")
        self.assertIsNone(out["match"])

    def test_predict_rejects_library_miss(self):
        with self.assertRaises(r.CapabilityRegistryError):
            r.predict({"status":"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED"},{"x":1.0})

if __name__=="__main__":
    unittest.main(verbosity=2)
