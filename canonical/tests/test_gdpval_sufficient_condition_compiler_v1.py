import unittest
from canonical.runtime.gdpval_sufficient_condition_compiler_v1 import compile_criterion,evaluate


class Tests(unittest.TestCase):
    def test_top_heading(self):
        c=compile_criterion('The report includes a top-level section titled "Findings". (case/punctuation variations acceptable).')
        self.assertEqual(c["status"],"COMPILED_SUFFICIENT_CONDITION")
        out=evaluate(c["program"],[{"kind":"HEADING","level":1,"text":"Findings:"}])
        self.assertEqual(out["status"],"PASS")

    def test_wrong_heading_level_does_not_pass(self):
        c=compile_criterion('The report includes a top-level section titled "Findings". (case/punctuation variations acceptable).')
        self.assertEqual(evaluate(c["program"],[{"kind":"HEADING","level":2,"text":"Findings"}])["status"],"NOT_PROVED")

    def test_sheet_name(self):
        c=compile_criterion("Workbook (deliverable) contains a worksheet named exactly 'Controls' (case-insensitive).")
        self.assertEqual(c["status"],"COMPILED_SUFFICIENT_CONDITION")
        self.assertEqual(evaluate(c["program"],[{"kind":"SHEET","name":" controls "}])["status"],"PASS")

    def test_form_line_numeric_is_anchored(self):
        c=compile_criterion("Form 1120 line 11 is $45,000")
        self.assertEqual(c["status"],"COMPILED_SUFFICIENT_CONDITION")
        units=[{"kind":"TEXT_BLOCK","text":"Form 1120, line 11 is $45,000."}]
        self.assertEqual(evaluate(c["program"],units)["status"],"PASS")
        self.assertEqual(evaluate(c["program"],[{"kind":"TEXT_BLOCK","text":"Unrelated total is $45,000."}])["status"],"NOT_PROVED")

    def test_rate_range(self):
        c=compile_criterion("States the 2025 annual rate increase for USPS as a number between 7% and 8%")
        self.assertEqual(c["status"],"COMPILED_SUFFICIENT_CONDITION")
        units=[{"kind":"TEXT_BLOCK","text":"USPS 2025 annual rate increase: 7.5%"}]
        self.assertEqual(evaluate(c["program"],units)["status"],"PASS")

    def test_scenario_rent(self):
        c=compile_criterion("Scenario 2 default base rent equals $4.25 per SF per month.")
        self.assertEqual(c["status"],"COMPILED_SUFFICIENT_CONDITION")
        units=[{"kind":"TEXT_BLOCK","text":"Scenario 2 base rent $4.25 per SF per month"}]
        self.assertEqual(evaluate(c["program"],units)["status"],"PASS")

    def test_unknown_fails_closed(self):
        c=compile_criterion("The memo is clear and professional.")
        self.assertEqual(c["status"],"UNRESOLVED")


if __name__=="__main__":
    unittest.main()
