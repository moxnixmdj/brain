import json
import unittest
from copy import deepcopy

from canonical.runtime import capability_parallel_frontier_post_composition_v1 as p
from canonical.runtime import capability_parallel_frontier_v2 as core
from canonical.runtime.professional_quality_whole_leaf_residual_compiler_v1 import compile_whole_leaf_residuals


class Tests(unittest.TestCase):
    def test_current(self):
        frontier = core.load_current_frontier()
        row = p._professional_row(frontier)
        out = p.plan_current_post_composition_frontier()
        self.assertEqual(out["parallel_full_execution_work_ids"], [])
        self.assertIn(row["work_id"], out["parallel_read_only_evidence_work_ids"])
        self.assertFalse(out["execution_authority"])

    def test_stale_property_count_fails(self):
        frontier = deepcopy(core.load_current_frontier())
        row = p._professional_row(frontier)
        row["read_only_evidence"]["property_truth_closed_count"] += 1
        with self.assertRaises(p.PostCompositionFrontierError):
            p._assert_post_composition(frontier)

    def test_current_whole_leaf_residual_replay(self):
        ledger = json.loads(
            (
                core.ROOT
                / "canonical/governance/PROFESSIONAL_QUALITY_WHOLE_LEAF_RESIDUAL_LEDGER_20261010_V1.json"
            ).read_text()
        )
        registry = json.loads(
            (core.ROOT / ledger["subject"]["scoped_registry_path"]).read_text()
        )
        expected = [row["leaf_id"] for row in ledger["leaves"]]
        out = compile_whole_leaf_residuals(registry["entries"], expected)
        self.assertEqual(out["expected_leaf_count"], 24)
        self.assertEqual(out["closed_leaf_count"], 0)
        self.assertEqual(out["open_leaf_count"], 24)

    def test_requires_professional_lane(self):
        frontier = deepcopy(core.load_current_frontier())
        frontier["candidates"] = [
            row
            for row in frontier["candidates"]
            if row.get("source") != p.PROFESSIONAL_SOURCE_REL
        ]
        with self.assertRaises(p.PostCompositionFrontierError):
            p._assert_post_composition(frontier)


if __name__ == "__main__":
    unittest.main()
