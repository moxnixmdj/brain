import unittest
from copy import deepcopy
from canonical.runtime import capability_parallel_frontier_post_composition_v1 as p
from canonical.runtime import capability_parallel_frontier_v2 as core

class Tests(unittest.TestCase):
    def test_current(self):
        out=p.plan_current_post_composition_frontier()
        self.assertEqual(out["parallel_full_execution_work_ids"],[])
        self.assertIn(p.PROF_WORK,out["parallel_read_only_evidence_work_ids"])
        self.assertFalse(out["execution_authority"])

    def test_requires_composed_state(self):
        f=deepcopy(core.load_current_frontier())
        row=next(x for x in f["candidates"] if x.get("work_id")==p.PROF_WORK)
        row["read_only_evidence"]["composition_admissible"]=False
        with self.assertRaises(p.PostCompositionFrontierError):
            p._assert_post_composition(f)

    def test_requires_professional_lane(self):
        f=deepcopy(core.load_current_frontier())
        f["candidates"]=[x for x in f["candidates"] if x.get("work_id")!=p.PROF_WORK]
        with self.assertRaises(p.PostCompositionFrontierError):
            p._assert_post_composition(f)

if __name__=="__main__":
    unittest.main()
