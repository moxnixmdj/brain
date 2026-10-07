import unittest

from canonical.runtime.certified_scope_fragment_v1 import parse_scope


class CertifiedScopeFragmentTests(unittest.TestCase):
    def test_unless_scope(self):
        out = parse_scope("Apply the rule unless the exception holds.", source="s")
        self.assertEqual(out["status"], "PARSED")
        self.assertEqual(out["parse"]["relation"], "UNLESS")
        self.assertEqual(out["parse"]["left_role"], "ORDINARY_BRANCH")
        self.assertEqual(out["parse"]["right_role"], "EXCEPTION_BRANCH")

    def test_prefix_if_controlled_form(self):
        out = parse_scope("If exposure exceeds the limit, escalate.", source="s")
        self.assertEqual(out["status"], "PARSED")
        self.assertEqual(out["parse"]["left_role"], "ANTECEDENT")
        self.assertEqual(out["parse"]["right_role"], "CONSEQUENT")

    def test_postfix_if_controlled_form(self):
        out = parse_scope("Escalate if exposure exceeds the limit.", source="s")
        self.assertEqual(out["status"], "PARSED")
        self.assertEqual(out["parse"]["left_role"], "CONSEQUENT")
        self.assertEqual(out["parse"]["right_role"], "ANTECEDENT")

    def test_before_scope(self):
        out = parse_scope("Validate the exception before execution.", source="s")
        self.assertEqual(out["status"], "PARSED")
        self.assertEqual(out["parse"]["relation"], "BEFORE")

    def test_multiple_conditionals_are_unresolved(self):
        out = parse_scope("Proceed if A, unless B.", source="s")
        self.assertEqual(out["status"], "UNRESOLVED")

    def test_prefix_if_without_controlled_comma_is_unresolved(self):
        out = parse_scope("If A then B.", source="s")
        self.assertEqual(out["status"], "UNRESOLVED")

    def test_no_scope_operator_is_unresolved(self):
        out = parse_scope("The transaction qualifies.", source="s")
        self.assertEqual(out["status"], "UNRESOLVED")


if __name__ == "__main__":
    unittest.main()
