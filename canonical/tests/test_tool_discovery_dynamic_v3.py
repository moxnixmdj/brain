import unittest
from canonical.runtime import tool_discovery_dynamic_candidate_v3 as c
from canonical.runtime import tool_discovery_dynamic_proof_v3 as p

class ToolDiscoveryDynamicV3Tests(unittest.TestCase):
    def test_1200_cross_class_grid(self):
        out=p.run_batch(20261002,1200,c.next_action)
        self.assertTrue(out["pass"],out["failures"][:5])
        self.assertEqual(set(out["classes"]),set(p.CLASSES))
        self.assertEqual(out["failed"],0)

    def test_dynamic_discovery_is_required(self):
        case=p.generate_case(77,0)
        verdict=p.score_episode(case,c.next_action)
        self.assertTrue(verdict["pass"],verdict)
        self.assertGreaterEqual(verdict["baseline_failed_invocations"],1)

    def test_generic_constraint_tree_changes_selection(self):
        case=p.generate_case(88,1)
        verdict=p.score_episode(case,c.next_action)
        self.assertTrue(verdict["pass"],verdict)
        self.assertEqual(case["case_class"],"GENERIC_CONSTRAINT")

    def test_multi_source_and_no_route(self):
        multi=p.score_episode(p.generate_case(99,2),c.next_action)
        none=p.score_episode(p.generate_case(100,5),c.next_action)
        self.assertTrue(multi["pass"],multi)
        self.assertTrue(none["pass"],none)

    def test_transfer_and_version_invalidation(self):
        transfer=p.score_episode(p.generate_case(101,3),c.next_action)
        changed=p.score_episode(p.generate_case(102,4),c.next_action)
        self.assertTrue(transfer["pass"],transfer)
        self.assertTrue(changed["pass"],changed)

if __name__=="__main__":
    unittest.main(verbosity=2)
