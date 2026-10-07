import unittest

from canonical.runtime.certified_deontic_rule_fragment_v1 import parse_deontic_rule
from canonical.runtime.source_aligned_semantic_proof_v3 import verify_proof


class CertifiedDeonticRuleFragmentTests(unittest.TestCase):
    def _claim(self, parsed):
        scope = parsed.get("scope")
        return {
            "claim_id": "d",
            "kind": "DEONTIC_RULE",
            "rule_id": parsed["rule_id"],
            "relation": parsed["relation"],
            "subject_span": parsed["subject_span"],
            "action_span": parsed["action_span"],
            "scope_id": scope.get("scope_id") if scope else None,
            "scope_relation": scope.get("relation") if scope else None,
            "condition_span": scope.get("condition_span") if scope else None,
        }

    def test_simple_required(self):
        text = "The operator must archive the record."
        p = parse_deontic_rule(text, source="s")
        self.assertEqual(p["status"], "PARSED")
        self.assertEqual(p["relation"], "REQUIRED")
        out = verify_proof(text, source_id="s", claims=[self._claim(p)])
        self.assertEqual(out["status"], "PROOF_CHECKED")
        self.assertEqual(len(out["proved_constraints"]), 1)

    def test_simple_prohibition(self):
        text = "The operator must not publish the draft."
        p = parse_deontic_rule(text, source="s")
        self.assertEqual(p["status"], "PARSED")
        self.assertEqual(p["relation"], "PROHIBITED")

    def test_prefix_if_scope(self):
        text = "If the input is complete, The operator must archive the record."
        p = parse_deontic_rule(text, source="s")
        self.assertEqual(p["status"], "PARSED")
        self.assertEqual(p["relation"], "REQUIRED")
        self.assertEqual(p["scope"]["relation"], "IF_THEN")
        self.assertEqual(p["scope"]["deontic_role"], "CONSEQUENT")

    def test_unless_scope(self):
        text = "The operator must archive the record unless the exception applies."
        p = parse_deontic_rule(text, source="s")
        self.assertEqual(p["status"], "PARSED")
        self.assertEqual(p["scope"]["relation"], "UNLESS")
        self.assertEqual(p["scope"]["deontic_role"], "ORDINARY_BRANCH")

    def test_scope_cannot_be_stripped(self):
        text = "If the input is complete, The operator must archive the record."
        p = parse_deontic_rule(text, source="s")
        claim = self._claim(p)
        claim["scope_id"] = None
        claim["scope_relation"] = None
        claim["condition_span"] = None
        out = verify_proof(text, source_id="s", claims=[claim])
        self.assertEqual(out["status"], "PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["proved_constraints"], [])

    def test_coordinated_action_fails_closed(self):
        p = parse_deontic_rule("The operator must archive the record and notify the reviewer.", source="s")
        self.assertEqual(p["status"], "UNRESOLVED")

    def test_implicit_meaning_fails_closed(self):
        p = parse_deontic_rule("The operator is responsible for the record.", source="s")
        self.assertEqual(p["status"], "UNRESOLVED")

    def test_multi_scope_fails_closed(self):
        p = parse_deontic_rule("If A, The operator must archive the record unless B.", source="s")
        self.assertEqual(p["status"], "UNRESOLVED")

    def test_wrong_relation_claim_rejected(self):
        text = "The operator shall not publish the draft."
        p = parse_deontic_rule(text, source="s")
        claim = self._claim(p)
        claim["relation"] = "REQUIRED"
        out = verify_proof(text, source_id="s", claims=[claim])
        self.assertEqual(out["proved_constraints"], [])


if __name__ == "__main__":
    unittest.main()
