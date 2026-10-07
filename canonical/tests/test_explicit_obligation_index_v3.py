import unittest

from canonical.runtime.explicit_obligation_index_v3 import build_index


class TestExplicitObligationIndexV3(unittest.TestCase):
    def test_filename_period_is_not_sentence_boundary(self):
        text = "Refer to Sample.pdf for details. Use Notes.pdf for values."
        out = build_index(text, source_id="gdpval-test")
        self.assertEqual(out["directive_obligation_count"], 1, out)
        row = out["directive_obligations"][0]
        self.assertEqual(row["action"], "use")
        self.assertEqual(row["object_text"], "Notes.pdf for values")
        s, e = row["action_span"]
        self.assertEqual(text[s:e], "Use Notes.pdf for values")

    def test_decimal_period_is_not_sentence_boundary(self):
        text = "Use 0.4 units daily. Create a PDF report."
        out = build_index(text, source_id="gdpval-test")
        self.assertEqual(out["directive_obligation_count"], 2, out)
        self.assertEqual(
            [x["action"] for x in out["directive_obligations"]],
            ["use", "create"],
        )
        for row in out["directive_obligations"]:
            s, e = row["action_span"]
            self.assertEqual(text[s:e], row["action_text"])

    def test_declarative_reference_materials_is_not_promoted(self):
        text = 'Reference materials are attached, including "Sample.pdf".'
        out = build_index(text, source_id="gdpval-test")
        self.assertEqual(out["directive_obligation_count"], 0, out)
        self.assertTrue(out["unresolved_segments"])

    def test_short_reference_heading_is_not_promoted(self):
        out = build_index("Reference Material:", source_id="gdpval-test")
        self.assertEqual(out["directive_obligation_count"], 0, out)
        self.assertTrue(out["unresolved_segments"])

    def test_slash_heading_is_not_promoted(self):
        out = build_index("Develop/Integrate Tooling", source_id="gdpval-test")
        self.assertEqual(out["directive_obligation_count"], 0, out)
        self.assertTrue(out["unresolved_segments"])

    def test_context_span_and_action_span_are_exact(self):
        text = "For each item, list the original value, duration, monthly value, and remaining value by month."
        out = build_index(text, source_id="gdpval-test")
        self.assertEqual(out["directive_obligation_count"], 1, out)
        row = out["directive_obligations"][0]
        self.assertEqual(row["action"], "list")
        s, e = row["action_span"]
        self.assertEqual(
            text[s:e],
            "list the original value, duration, monthly value, and remaining value by month",
        )
        cs, ce = row["context"]["span"]
        self.assertEqual(text[cs:ce], "each item")

    def test_modal_path_is_preserved(self):
        text = "The report must include metric A and metric B."
        out = build_index(text, source_id="gdpval-test")
        self.assertEqual(out["modal_obligation_count"], 1, out)
        self.assertEqual(out["directive_obligation_count"], 0, out)

    def test_absence_does_not_prove_no_obligation(self):
        out = build_index("Background information for the task.", source_id="gdpval-test")
        self.assertFalse(out["absence_of_indexed_obligation_proves_no_obligation"])
        self.assertFalse(out["semantic_completeness_claim"])
        self.assertFalse(out["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
