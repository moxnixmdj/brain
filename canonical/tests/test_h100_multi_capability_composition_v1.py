import json, unittest
from canonical.runtime import h100_multi_capability_composition_v1 as c

class H100MultiCapabilityCompositionTests(unittest.TestCase):
    def test_precommit_plan_is_eighteen_bits_and_frozen(self):
        d=json.loads(c.PRE.read_text())
        self.assertEqual(d["composition_plan"]["total_plan_bits"],18)
        self.assertEqual(len(d["tasks"]),4)

    def test_three_positive_tasks_compose_without_raw_synthesis(self):
        pre=json.loads(c.PRE.read_text()); tpre=json.loads(c.TRANSFER_PRE.read_text())
        for task in pre["tasks"][:3]:
            out=c.execute_task(task,tpre)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["status"],"COMPOSED_VERIFIED_CAPABILITY")
            self.assertEqual(out["raw_synthesis_attempts_before_hit"],0)
            self.assertEqual(out["raw_synthesis_attempts_executed"],0)
            self.assertLessEqual(out["holdout_nrmse"],1e-7)

    def test_cubic_control_fails_closed_to_raw_stage_without_executing_it(self):
        pre=json.loads(c.PRE.read_text()); tpre=json.loads(c.TRANSFER_PRE.read_text())
        out=c.execute_task(pre["tasks"][3],tpre)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["status"],"LIBRARY_MISS__RAW_SYNTHESIS_REQUIRED")
        self.assertTrue(out["raw_synthesis_required"])
        self.assertEqual(out["raw_synthesis_attempts_executed"],0)

    def test_full_measurement_zero_learned(self):
        out=c.run()
        self.assertEqual(out["positive_tasks_passed"],3)
        self.assertTrue(out["negative_control_fail_closed"])
        self.assertEqual(out["persistent_learned_bytes"],0)
        self.assertEqual(out["summary"]["raw_synthesis_attempts_executed"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
