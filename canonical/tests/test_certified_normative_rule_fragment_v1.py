import unittest
from canonical.runtime.certified_normative_rule_fragment_v1 import parse_rule,decide

class T(unittest.TestCase):
    def test_obligation(self):
        x=decide("Broker must file report",source_id="r1",subject_applies=True)
        self.assertEqual(x["status"],"DECIDED")
        self.assertEqual(x["normative_kind"],"OBLIGATION")
        self.assertEqual(x["disposition"],"REQUIRED")
        self.assertEqual(x["action"]["text"],"file report")

    def test_prohibition(self):
        x=decide("Broker must not disclose secret",source_id="r2",subject_applies=True)
        self.assertEqual(x["normative_kind"],"PROHIBITION")
        self.assertEqual(x["disposition"],"PROHIBITED")
        self.assertEqual(x["action"]["text"],"disclose secret")

    def test_unless_branch(self):
        text="Broker must file report unless exemption applies"
        a=decide(text,source_id="r3",subject_applies=True,exception_holds=False)
        b=decide(text,source_id="r3",subject_applies=True,exception_holds=True)
        self.assertEqual(a["disposition"],"REQUIRED")
        self.assertEqual(b["disposition"],"EXCEPTION_APPLIES")
        self.assertEqual(b["exception"]["text"],"exemption applies")

    def test_inapplicable_subject(self):
        x=decide("Broker shall file report",source_id="r4",subject_applies=False)
        self.assertEqual(x["disposition"],"NOT_APPLICABLE")

    def test_missing_exception_fact_fails_closed(self):
        x=decide("Broker must file report unless exemption applies",source_id="r5",subject_applies=True)
        self.assertEqual(x["status"],"FAIL_CLOSED")
        self.assertEqual(x["reason"],"EXCEPTION_HOLDS_NOT_BOOLEAN")

    def test_undeclared_exception_fact_fails_closed(self):
        x=decide("Broker must file report",source_id="r6",subject_applies=True,exception_holds=False)
        self.assertEqual(x["status"],"FAIL_CLOSED")
        self.assertEqual(x["reason"],"UNDECLARED_EXCEPTION_FACT")

    def test_nested_semantics_rejected(self):
        for text in (
            "Broker must file report before execution",
            "Broker must file report if threshold holds",
            "Broker must file report unless exemption applies unless waiver applies",
        ):
            x=parse_rule(text,source_id="nested")
            self.assertEqual(x["status"],"UNRESOLVED")

    def test_source_mutation_changes_binding(self):
        a=parse_rule("Broker must file report",source_id="r7")
        b=parse_rule("Broker must file notice",source_id="r7")
        self.assertNotEqual(a["source_sha256"],b["source_sha256"])
        self.assertNotEqual(a["action"]["sha256"],b["action"]["sha256"])

    def test_zero_dependencies(self):
        x=decide("Broker shall not disclose secret",source_id="r8",subject_applies=True)
        self.assertEqual(x["model_dependency_count"],0)
        self.assertFalse(x["external_capability_dependency"])

if __name__=="__main__":
    unittest.main(verbosity=2)
