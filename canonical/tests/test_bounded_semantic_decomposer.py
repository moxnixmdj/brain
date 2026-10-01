import unittest

from canonical.runtime.bounded_semantic_decomposer import decompose


class BoundedSemanticDecomposerTests(unittest.TestCase):
    def test_simple_behavior_passes(self):
        out = decompose("Return JSON.")
        self.assertEqual(out["status"], "CONSENSUS")
        self.assertEqual(out["unit_count"], 1)
        self.assertEqual(out["units"][0]["semantic_class"], "BEHAVIOR")

    def test_multiple_simple_units_pass(self):
        out = decompose("Return JSON.\nVerify acceptance.")
        self.assertEqual(out["status"], "CONSENSUS")
        self.assertEqual([u["semantic_class"] for u in out["units"]], ["BEHAVIOR", "EVALUATION"])

    def test_compound_operative_fails_closed(self):
        out = decompose("Return JSON and preserve order.")
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(any(x.startswith("COMPOUND_OPERATIVE_SPAN") for x in out["errors"]))

    def test_multiclass_fails_closed(self):
        out = decompose("Verify the output file.")
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(any(x.startswith("SEMANTIC_CLASS_AMBIGUOUS") for x in out["errors"]))

    def test_informative_text_preserved(self):
        out = decompose("Background context.")
        self.assertEqual(out["status"], "CONSENSUS")
        self.assertEqual(out["units"][0]["semantic_class"], "INFORMATIVE")

    def test_empty_fails_closed(self):
        out = decompose("   ")
        self.assertEqual(out["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
