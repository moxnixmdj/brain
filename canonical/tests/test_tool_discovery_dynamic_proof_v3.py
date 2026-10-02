import unittest
from canonical.runtime.tool_discovery_dynamic_candidate_v3 import next_action
from canonical.runtime import tool_discovery_dynamic_proof_v3 as p

class ToolDiscoveryDynamicV3Tests(unittest.TestCase):
    def test_full_population(self):
        out=p.run_batch(20261002,140,next_action)
        self.assertTrue(out["pass"],out["failures"][:12])
        self.assertEqual(set(out["classes"]),set(p.CLASSES))

    def test_dynamic_discovery(self):
        i=p.CLASSES.index("DYNAMIC_DISCOVERY")
        c=p.generate_case(7,i)
        v=p.score_episode(c,next_action)
        self.assertTrue(v["pass"],v)

    def test_generic_constraint(self):
        i=p.CLASSES.index("GENERIC_CONSTRAINT")
        c=p.generate_case(11,i)
        v=p.score_episode(c,next_action)
        self.assertTrue(v["pass"],v)

    def test_baseline_advantage_is_load_bearing(self):
        i=p.CLASSES.index("BASELINE_ADVANTAGE")
        c=p.generate_case(13,i)
        v=p.score_episode(c,next_action)
        self.assertTrue(v["pass"],v)
        self.assertEqual(v["baseline_failed_invocations"],1)

    def test_no_route_exhausts_discovery_before_escalation(self):
        i=p.CLASSES.index("NO_ROUTE")
        c=p.generate_case(17,i)
        v=p.score_episode(c,next_action)
        self.assertTrue(v["pass"],v)

if __name__=="__main__":
    unittest.main()
