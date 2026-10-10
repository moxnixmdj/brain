import copy
import unittest
from canonical.runtime import capability_parallel_frontier_post_composition_v2 as p
from canonical.runtime import capability_parallel_frontier_v2 as core

class Tests(unittest.TestCase):
    def test_current_frontier_is_read_only_and_exactly_4_of_24(self):
        out=p.plan_current_post_composition_frontier_v2()
        self.assertEqual(out["parallel_full_execution_work_ids"],[])
        self.assertIn(p.PROF_WORK,out["parallel_read_only_evidence_work_ids"])
        self.assertEqual(out["property_truth_closed_count"],4)
        self.assertEqual(out["open_execution_leaf_count"],8)
        self.assertEqual(out["open_semantic_leaf_count"],12)
        self.assertEqual(out["semantic_identity_carrier_verified_count"],12)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_property_truth_count_drift_fails_closed(self):
        f=copy.deepcopy(core.load_current_frontier())
        row=next(x for x in f["candidates"] if x.get("work_id")==p.PROF_WORK)
        row["read_only_evidence"]["property_truth_closed_count"]=3
        with self.assertRaisesRegex(p.PostCompositionFrontierV2Error,"PROPERTY_TRUTH_COUNT_NOT_4"):
            p._assert_current_phase(f)

    def test_semantic_carrier_overclaim_fails_closed(self):
        f=copy.deepcopy(core.load_current_frontier())
        row=next(x for x in f["candidates"] if x.get("work_id")==p.PROF_WORK)
        row["read_only_evidence"]["semantic_property_truth_closed_count"]=1
        with self.assertRaisesRegex(p.PostCompositionFrontierV2Error,"SEMANTIC_PROPERTY_TRUTH_OVERCLAIM"):
            p._assert_current_phase(f)

    def test_wrong_verified_leaf_set_fails_closed(self):
        f=copy.deepcopy(core.load_current_frontier())
        row=next(x for x in f["candidates"] if x.get("work_id")==p.PROF_WORK)
        row["read_only_evidence"]["verified_property_truth_leaf_ids"]=[]
        with self.assertRaisesRegex(p.PostCompositionFrontierV2Error,"PROPERTY_TRUTH_LEAF_SET_MISMATCH"):
            p._assert_current_phase(f)

if __name__=="__main__":
    unittest.main(verbosity=2)
