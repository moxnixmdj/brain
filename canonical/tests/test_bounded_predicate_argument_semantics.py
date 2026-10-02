import unittest
from canonical.runtime.bounded_predicate_argument_semantics import parse_clause, consensus_proposal
from canonical.runtime.m0a_semantic_graph_consensus import compile_consensus

class Tests(unittest.TestCase):
    def test_active_modal(self):
        text="The worker must write the report."
        r=parse_clause(text)
        self.assertEqual(r["status"],"RESOLVED")
        g=r["semantic_graph"]
        self.assertEqual(g["subject"],"The worker")
        self.assertEqual(g["predicate"],"write")
        self.assertEqual(g["object"],"the report")
        self.assertEqual(g["polarity"],"REQUIRED")

    def test_negative_modal(self):
        r=parse_clause("The worker must not delete the receipt.")
        self.assertEqual(r["status"],"RESOLVED")
        self.assertEqual(r["semantic_graph"]["polarity"],"PROHIBITED")

    def test_passive_modal(self):
        r=parse_clause("The report must be signed by the approver.")
        self.assertEqual(r["status"],"RESOLVED")
        g=r["semantic_graph"]
        self.assertEqual(g["voice"],"PASSIVE")
        self.assertEqual(g["subject"],"the approver")
        self.assertEqual(g["predicate"],"signed")
        self.assertEqual(g["object"],"The report")

    def test_leading_condition(self):
        text="If validation fails, the worker must retry the operation."
        r=parse_clause(text)
        self.assertEqual(r["status"],"RESOLVED")
        self.assertEqual(r["condition"]["relation"],"CONDITION_IF")
        self.assertEqual(r["condition"]["text"],"validation fails")

    def test_coordination_fails_closed(self):
        r=parse_clause("The worker must read and verify the report.")
        self.assertEqual(r["status"],"FAIL_CLOSED")
        self.assertEqual(r["reason"],"COORDINATED_OR_MULTI_CLAUSE_FORM")

    def test_pronoun_argument_unresolved(self):
        r=parse_clause("He must write the report.")
        self.assertEqual(r["status"],"UNRESOLVED")

    def test_outside_grammar_unresolved(self):
        r=parse_clause("Writing the report is desirable.")
        self.assertEqual(r["status"],"UNRESOLVED")

    def test_source_spans_are_exact(self):
        text="The worker must write the report."
        g=parse_clause(text)["semantic_graph"]
        self.assertEqual(text[slice(*g["subject_span"])],"The worker")
        self.assertEqual(text[slice(*g["predicate_span"])],"write")
        self.assertEqual(text[slice(*g["object_span"])],"the report")

    def test_consensus_interface(self):
        text="The worker must write the report."
        p1=consensus_proposal(text)["proposal"]
        g=parse_clause(text)["semantic_graph"]
        p2={
            "route_id":"independent_fixture_route",
            "independence_group":"independent_structural_route",
            "bindings":[],
            "relations":[],
            "obligations":[{
                "subject_span":g["subject_span"],
                "predicate_span":g["predicate_span"],
                "object_span":g["object_span"],
                "modality":"required",
            }],
        }
        out=compile_consensus(text,[p1,p2])
        self.assertEqual(out["status"],"CONSENSUS")
        self.assertEqual(len(out["accepted"]["obligations"]),1)

if __name__=="__main__":
    unittest.main()
