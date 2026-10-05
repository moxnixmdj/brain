import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "governance" / "OPUS55_SCORE_TARGET_TUPLE_BINDINGS_20261005_V1.json"
EXPECTED = {
    "CODING_TB4_GE_66_4",
    "CHARTOGRAPHY_TOOLS_GE_89",
    "HLE_TOOLS_GE_67_7",
    "OSWORLD_2_1_PARTIAL_GE_81_8",
    "FINANCE_AGENT_V2_GE_58_59",
    "CODING_FRONTIERCODE_GE_54_4",
    "PROWORK_GDPVAL_GE_1846",
    "PROWORK_AA_BRIEFCASE_GE_1822",
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
    "AUTOMATIONBENCH_GE_40",
    "MYSTERYMECHANISM_GE_49_55",
    "FINANCE_ACCOUNTING_INDEX_GE_61",
    "CODING_CURSORBENCH_GE_57_8",
    "TB_SCIENCE_GE_58_7",
}
TUPLE_FIELDS = (
    "benchmark", "benchmark_version", "model", "effort", "evaluator",
    "harness", "fallback_policy", "score", "unit", "source_url", "source_snapshot"
)

class ScoreTargetTupleBindingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PATH.read_text())
        cls.bindings = cls.doc["bindings"]

    def test_exact_14_predicates_bound(self):
        ids = [b["predicate_id"] for b in self.bindings]
        self.assertEqual(len(ids), 14)
        self.assertEqual(set(ids), EXPECTED)
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_binding_has_exact_tuple_and_bound_source(self):
        for b in self.bindings:
            for key in TUPLE_FIELDS:
                self.assertIn(key, b, (b["predicate_id"], key))
                self.assertNotEqual(b[key], "", (b["predicate_id"], key))
            self.assertTrue(b["source_url"].startswith("https://"))

    def test_unique_tuple_count_is_13_with_only_expected_shared_pair(self):
        keys = {}
        for b in self.bindings:
            k = tuple(str(b[x]) for x in (
                "benchmark", "benchmark_version", "model", "effort", "evaluator",
                "harness", "fallback_policy", "score", "unit"
            ))
            keys.setdefault(k, []).append(b["predicate_id"])
        self.assertEqual(len(keys), 13)
        shared = [v for v in keys.values() if len(v) > 1]
        self.assertEqual(shared, [["PROWORK_AA_BRIEFCASE_GE_1822", "ARTIFACT_AA_BRIEFCASE_GE_1822"]])

    def test_zero_acceptance_or_ownership_credit(self):
        a = self.doc["accounting"]
        self.assertEqual(a["acceptance_credit_delta"], 0)
        self.assertEqual(a["family_credit_delta"], 0)
        self.assertEqual(a["capability_credit_delta"], 0)
        self.assertEqual(a["ownership_credit_delta"], 0)

if __name__ == "__main__":
    unittest.main(verbosity=2)
