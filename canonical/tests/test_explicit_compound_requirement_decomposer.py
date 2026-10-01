import unittest

from canonical.runtime.explicit_compound_requirement_decomposer import decompose_explicit_compound


class ExplicitCompoundRequirementDecomposerTests(unittest.TestCase):
    def test_explicit_bullet_list(self):
        out = decompose_explicit_compound("- Preserve formulas\n- Preserve formatting\n- Save the workbook")
        self.assertEqual(out["status"], "DECOMPOSED")
        self.assertEqual(out["count"], 3)
        self.assertEqual(out["route"], "EXPLICIT_LIST")

    def test_flat_shared_modal_and(self):
        out = decompose_explicit_compound("The artifact must preserve formulas and preserve formatting")
        self.assertEqual(out["status"], "DECOMPOSED")
        self.assertEqual(out["count"], 2)
        self.assertIn("must preserve formulas", out["obligations"][0])
        self.assertIn("must preserve formatting", out["obligations"][1])

    def test_or_fails_closed(self):
        out = decompose_explicit_compound("The artifact must preserve formulas or preserve formatting")
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_exception_fails_closed(self):
        out = decompose_explicit_compound("The artifact must preserve formulas and formatting unless explicitly removed")
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_pronoun_reference_fails_closed(self):
        out = decompose_explicit_compound("- Preserve the table\n- Move it below the chart")
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_multiple_modals_fail_closed(self):
        out = decompose_explicit_compound("The file must preserve formulas and shall preserve formatting")
        self.assertEqual(out["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
