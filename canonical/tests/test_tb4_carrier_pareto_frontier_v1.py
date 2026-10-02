from __future__ import annotations

import copy
import unittest

from canonical.runtime import tb4_carrier_pareto_frontier_v1 as v


class TB4CarrierParetoFrontierTests(unittest.TestCase):
    def docs(self):
        return v._load(v.SOURCE), v._load(v.CANDIDATE)

    def test_live_frontier_is_exact_and_fail_closed(self):
        source, candidate = self.docs()
        out = v.evaluate(source, candidate, source_blob=v._blob(v.SOURCE))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["subset_count"], 495)
        self.assertEqual(
            out["pareto_frontier"],
            [
                {"env": [8, 16384, 30720, 1], "subset_count": 9},
                {"env": [8, 16384, 51200, 0], "subset_count": 1},
                {"env": [16, 16384, 20480, 0], "subset_count": 1},
            ],
        )
        self.assertEqual(out["joint_floor_counterexamples"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_declared_frontier_tamper_fails(self):
        source, candidate = self.docs()
        candidate = copy.deepcopy(candidate)
        candidate["single_carrier_pareto_frontier"][1]["envelope"]["free_storage_mb_at_least"] = 20480
        out = v.evaluate(source, candidate, source_blob=v.EXPECTED_SOURCE_BLOB)
        self.assertFalse(out["pass"])
        self.assertIn("PARETO_FRONTIER_MISMATCH", out["errors"])

    def test_source_blob_drift_fails_even_when_metadata_is_same(self):
        source, candidate = self.docs()
        out = v.evaluate(source, candidate, source_blob="0" * 40)
        self.assertFalse(out["pass"])
        self.assertIn("SOURCE_BLOB_DRIFT", out["errors"])

    def test_resource_mutation_changes_frontier_and_fails_candidate(self):
        source, candidate = self.docs()
        source = copy.deepcopy(source)
        row = next(x for x in source["resource_exceed_tasks"] if x["task"].endswith("takens-embedding-lean"))
        row["storage_mb"] = 20480
        out = v.evaluate(source, candidate, source_blob=v.EXPECTED_SOURCE_BLOB)
        self.assertFalse(out["pass"])
        self.assertTrue(
            "PARETO_FRONTIER_MISMATCH" in out["errors"]
            or "PARETO_FRONTIER_NOT_EXACT_EXPECTED_THREE" in out["errors"]
        )

    def test_joint_floor_is_exhaustive_not_single_representative(self):
        source, _ = self.docs()
        compiled = v.compile_frontier(source)
        self.assertEqual(compiled["subset_count"], 495)
        self.assertEqual(compiled["joint_floor_violation_count"], 0)
        self.assertEqual(compiled["tasks_not_jointly_requiring_8cpu_16384mb"], 7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
