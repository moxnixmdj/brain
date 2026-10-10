import json
import unittest
from copy import deepcopy
from canonical.runtime import capability_parallel_frontier_post_composition_v1 as p
from canonical.runtime import capability_parallel_frontier_v2 as core
from canonical.runtime.professional_quality_whole_leaf_residual_compiler_v1 import compile_whole_leaf_residuals

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

    def test_current_whole_leaf_residual_replay(self):
        ledger=json.loads((core.ROOT / p.WHOLE_LEAF_LEDGER_REL).read_text())
        registry=json.loads((core.ROOT / ledger["subject"]["scoped_registry_path"]).read_text())
        expected=[row["leaf_id"] for row in ledger["leaves"]]
        out=compile_whole_leaf_residuals(registry["entries"],expected)
        self.assertEqual(out["expected_leaf_count"],24)
        self.assertEqual(out["closed_leaf_count"],0)
        self.assertEqual(out["open_leaf_count"],24)

    def test_requires_professional_lane(self):
        f=deepcopy(core.load_current_frontier())
        f["candidates"]=[x for x in f["candidates"] if x.get("work_id")!=p.PROF_WORK]
        with self.assertRaises(p.PostCompositionFrontierError):
            p._assert_post_composition(f)

if __name__=="__main__":
    unittest.main()
