import unittest
from canonical.runtime.certified_deontic_rule_fragment_v1 import parse_deontic_rule
from canonical.runtime.source_aligned_deontic_extension_v1 import verify_proof

class TestDeonticFragment(unittest.TestCase):
    def claim(self, p):
        s=p.get("scope")
        return {"claim_id":"d","kind":"DEONTIC_RULE","rule_id":p["rule_id"],"relation":p["relation"],
                "subject_span":p["subject_span"],"action_span":p["action_span"],
                "scope_id":s.get("scope_id") if s else None,
                "scope_relation":s.get("relation") if s else None,
                "condition_span":s.get("condition_span") if s else None}
    def test_required(self):
        t="The operator must archive the record.";p=parse_deontic_rule(t,source="s")
        self.assertEqual(p["relation"],"REQUIRED")
    def test_prohibited(self):
        self.assertEqual(parse_deontic_rule("The operator must not publish the draft.",source="s")["relation"],"PROHIBITED")
    def test_if(self):
        self.assertEqual(parse_deontic_rule("If the input is complete, The operator must archive the record.",source="s")["scope"]["relation"],"IF_THEN")
    def test_unless(self):
        self.assertEqual(parse_deontic_rule("The operator must archive the record unless the exception applies.",source="s")["scope"]["relation"],"UNLESS")
    def test_coord_rejected(self):
        self.assertEqual(parse_deontic_rule("The operator must archive the record and notify the reviewer.",source="s")["status"],"UNRESOLVED")
    def test_implicit_rejected(self):
        self.assertEqual(parse_deontic_rule("The operator is responsible for the record.",source="s")["status"],"UNRESOLVED")
    def test_multi_scope_rejected(self):
        self.assertEqual(parse_deontic_rule("If A, The operator must archive the record unless B.",source="s")["status"],"UNRESOLVED")
