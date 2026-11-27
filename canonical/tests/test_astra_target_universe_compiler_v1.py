from __future__ import annotations
import copy
import unittest
from canonical.runtime.astra_target_universe_compiler_v1 import load_registry, verify

class AstraTargetUniverseCompilerV1Tests(unittest.TestCase):
    def setUp(self):
        self.r = load_registry()

    def test_live_candidate_is_structurally_valid(self):
        out = verify(self.r)
        self.assertTrue(out["valid"], out)
        self.assertGreater(out["target_behavior_count"], 0)
        self.assertTrue(out["target_comparator_separated"])
        self.assertFalse(out["activation_authority"])

    def test_benchmark_as_target_is_rejected(self):
        r = copy.deepcopy(self.r)
        r["target_rule"] = "PASS_ALL_BENCHMARKS"
        self.assertFalse(verify(r)["valid"])

    def test_unsourced_target_is_rejected(self):
        r = copy.deepcopy(self.r)
        r["target_behaviors"][0]["source_ids"] = []
        self.assertFalse(verify(r)["valid"])

    def test_unknown_source_reference_is_rejected(self):
        r = copy.deepcopy(self.r)
        r["target_behaviors"][0]["source_ids"] = ["NOT_A_SOURCE"]
        self.assertFalse(verify(r)["valid"])

    def test_opaque_astra_cannot_count_as_owned(self):
        r = copy.deepcopy(self.r)
        r["ownership_rule"]["opaque_astra_runtime_counts_as_owned"] = True
        self.assertFalse(verify(r)["valid"])

    def test_nonzero_incremental_spend_is_rejected(self):
        r = copy.deepcopy(self.r)
        r["ownership_rule"]["incremental_spend_usd"] = 0.01
        self.assertFalse(verify(r)["valid"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
