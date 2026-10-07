import unittest
from canonical.runtime.bounded_imperative_directive_semantics_v2 import parse_directive, segment_task_text

class TestImperativeV2(unittest.TestCase):
    def test_simple(self):
        x=parse_directive("Include metrics A1 and C1, which carry higher risk weightings.")
        self.assertEqual(x["status"],"RESOLVED_DIRECTIVE")
        self.assertEqual(x["directive"]["predicate"],"include")
    def test_context(self):
        x=parse_directive("For each invoice, list the original amount, amortization period, monthly expense, and remaining balance by month.")
        self.assertEqual(x["status"],"RESOLVED_DIRECTIVE")
        self.assertEqual(x["context"]["relation"],"CONTEXT_FOR")
    def test_filename_not_split(self):
        t="Refer to Wholesale Price.pdf for costs. Use Reimbursement.pdf for reimbursement values."
        parts=segment_task_text(t)
        self.assertEqual(parts,["Refer to Wholesale Price.pdf for costs.","Use Reimbursement.pdf for reimbursement values."])
        x=parse_directive(parts[1])
        self.assertEqual(x["directive"]["action_text"],"Use Reimbursement.pdf for reimbursement values")
    def test_decimal_not_split(self):
        self.assertEqual(segment_task_text("Use 0.4 mg daily. Create a PDF report."),["Use 0.4 mg daily.","Create a PDF report."])
    def test_reference_declarative_rejected(self):
        x=parse_directive('Reference materials are attached, including "Targets.pdf".')
        self.assertEqual(x["status"],"UNRESOLVED")
        self.assertEqual(x["reason"],"NOUN_HEADED_DECLARATIVE_AMBIGUITY")
    def test_reference_heading_rejected(self):
        x=parse_directive("Reference Material:")
        self.assertEqual(x["status"],"UNRESOLVED")
    def test_slash_label_rejected(self):
        x=parse_directive("Develop/Integrate Tooling")
        self.assertEqual(x["status"],"UNRESOLVED")
    def test_real_develop_survives(self):
        self.assertEqual(parse_directive("Develop a comprehensive option pricing framework.")["status"],"RESOLVED_DIRECTIVE")
    def test_declarative_rejected(self):
        self.assertEqual(parse_directive("The report includes a summary.")["status"],"UNRESOLVED")
    def test_no_whole_task_claim(self):
        x=parse_directive("Ensure that all criteria are represented.")
        self.assertFalse(x["directive"]["argument_semantics_resolved"])
        self.assertFalse(x["terminal_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
