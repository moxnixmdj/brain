import unittest
from canonical.runtime.bounded_imperative_directive_semantics_v1 import parse_directive

class T(unittest.TestCase):
    def test_simple_include_exact_raw_action(self):
        s="Include metrics A1 and C1, which carry higher risk weightings."
        x=parse_directive(s)
        self.assertEqual(x["status"],"RESOLVED_DIRECTIVE")
        d=x["directive"]
        self.assertEqual(d["predicate"],"include")
        self.assertEqual(d["action_text"],s[:-1])
        self.assertEqual(d["object_text"],"metrics A1 and C1, which carry higher risk weightings")
        self.assertFalse(d["coordination_split"])
        self.assertFalse(d["argument_semantics_resolved"])
        a,b=d["action_span"]; self.assertEqual(s[a:b],s[:-1])
        a,b=d["object_span"]; self.assertEqual(s[a:b],d["object_text"])

    def test_for_context_is_raw_bound_not_interpreted(self):
        s="For each invoice, list the original amount, amortization period, monthly expense, and remaining balance by month."
        x=parse_directive(s)
        self.assertEqual(x["status"],"RESOLVED_DIRECTIVE")
        self.assertEqual(x["directive"]["predicate"],"list")
        self.assertEqual(x["context"]["relation"],"CONTEXT_FOR")
        self.assertEqual(x["context"]["text"],"each invoice")
        a,b=x["context"]["span"]; self.assertEqual(s[a:b],"each invoice")

    def test_if_context(self):
        s="If unavailable, review options with the Vendor of Record."
        x=parse_directive(s)
        self.assertEqual(x["status"],"RESOLVED_DIRECTIVE")
        self.assertEqual(x["directive"]["predicate"],"review")
        self.assertEqual(x["context"]["relation"],"CONTEXT_IF")
        self.assertEqual(x["context"]["semantic_resolution"],"RAW_SOURCE_BOUND_CONTEXT_ONLY")

    def test_please_prefix(self):
        s="Please prepare Bob and Lisa Smith's Individual tax return form 1040."
        x=parse_directive(s)
        self.assertEqual(x["status"],"RESOLVED_DIRECTIVE")
        self.assertEqual(x["directive"]["predicate"],"prepare")
        a,b=x["directive"]["action_span"]
        self.assertEqual(s[a:b],"prepare Bob and Lisa Smith's Individual tax return form 1040")

    def test_ensure_coordination_not_split(self):
        s="Ensure that i) each sample satisfies one criterion, and ii) all criteria are represented."
        x=parse_directive(s)
        self.assertEqual(x["status"],"RESOLVED_DIRECTIVE")
        self.assertEqual(x["directive"]["predicate"],"ensure")
        self.assertFalse(x["directive"]["coordination_split"])
        self.assertIn("and ii)",x["directive"]["object_text"])

    def test_declarative_rejected(self):
        x=parse_directive("The report includes a summary and appendix.")
        self.assertEqual(x["status"],"UNRESOLVED")
        self.assertEqual(x["reason"],"IMPERATIVE_VERB_OUTSIDE_CERTIFIED_LEXICON")

    def test_unknown_imperative_verb_rejected(self):
        x=parse_directive("Foo the report.")
        self.assertEqual(x["status"],"UNRESOLVED")

if __name__=="__main__":
    unittest.main(verbosity=2)
