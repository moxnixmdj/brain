import json, unittest
from canonical.runtime import h100_non_synthetic_verifier_cost_v1 as v

class NonSyntheticVerifierCostTests(unittest.TestCase):
    def test_module_mapping(self):
        self.assertEqual(
            v.module_from_test_path("canonical/tests/test_x.py"),
            "canonical.tests.test_x"
        )
    def test_precommit_exact_cohort(self):
        d=json.loads(v.PRE.read_text())
        self.assertEqual(d["measurement"]["repetitions"],7)
        self.assertEqual([x["id"] for x in d["cohort"]],[
            "OEWN_REAL_LEXICAL","LEXICAL_SOURCE_FALLBACK",
            "COMPOSITIONAL_LANGUAGE","TOOL_TRACE_NORMALIZER"
        ])
    def test_full_measurement_passes_all_exact_subjects(self):
        out=v.run()
        self.assertEqual(len(out["subjects"]),4)
        self.assertEqual(out["persistent_learned_bytes"],0)
        for row in out["subjects"]:
            self.assertGreater(row["median_verifier_seconds"],0)
            self.assertIsNotNone(row["test_count"])

if __name__=="__main__":
    unittest.main(verbosity=2)
