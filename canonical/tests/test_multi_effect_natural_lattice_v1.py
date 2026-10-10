from __future__ import annotations
import unittest

from canonical.runtime.certified_multi_effect_natural_clause_v1 import parse_multi_effect_clauses
from canonical.runtime.source_aligned_semantic_proof_v16 import verify_proof
from canonical.runtime.source_semantic_claim_autofill_v5 import synthesize_missing_claims
from canonical.runtime import cross_document_effect_semantic_lattice_v9 as lattice
from canonical.runtime import cross_document_effect_semantic_lattice_verify_v9 as lattice_verify


def source():
    return "\n".join([
        "The complete effects on threshold are A.t, B.t, and C.t.",
        "Effect A.t on threshold defines it as \"10\", is unconditional, has no start date, has no end date, and supersedes nothing.",
        "Effect B.t on threshold replaces it with \"12\", is unconditional, is valid from 2026-07-01, has no end date, and supersedes A.t.",
        "Effect C.t on threshold creates an exception for it with value \"8\", applies when {\"small\":true}, is valid from 2026-07-01, has no end date, and supersedes B.t.",
    ])


class MultiEffectParserTests(unittest.TestCase):
    def test_complete_same_target_chain_parses(self):
        out=parse_multi_effect_clauses(source(),source="D")
        self.assertEqual(out["status"],"PARSED",out)
        self.assertEqual(len(out["groups"]),1)
        group=out["groups"][0]
        self.assertEqual(group["inventory"]["effect_ids"],["A.t","B.t","C.t"])
        self.assertEqual([x["effect"]["effect_class"] for x in group["effects"]],["DEFINE","REPLACE","EXCEPTION"])

    def test_missing_declared_body_is_unresolved(self):
        bad="\n".join(source().splitlines()[:-1])
        out=parse_multi_effect_clauses(bad,source="D")
        self.assertEqual(out["status"],"UNRESOLVED")
        self.assertIn("COMPLETE_EFFECT_BODY_SET_MISMATCH",out["reason"])

    def test_undeclared_extra_body_is_unresolved(self):
        extra=source()+"\nEffect X.t on threshold defines it as \"99\", is unconditional, has no start date, has no end date, and supersedes nothing."
        out=parse_multi_effect_clauses(extra,source="D")
        self.assertEqual(out["status"],"UNRESOLVED")
        self.assertIn("COMPLETE_EFFECT_BODY_SET_MISMATCH",out["reason"])

    def test_orphan_body_is_unresolved(self):
        text="Effect A.t on threshold defines it as \"10\", is unconditional, has no start date, has no end date, and supersedes nothing."
        out=parse_multi_effect_clauses(text,source="D")
        self.assertEqual(out["status"],"UNRESOLVED")
        self.assertIn("EFFECT_BODY_WITHOUT_COMPLETE_HEADER",out["reason"])


class MultiEffectProofAutofillLatticeTests(unittest.TestCase):
    def test_autofill_and_v16_independent_reparse_close_fields(self):
        auto=synthesize_missing_claims(source(),source_id="D",existing_claims=[])
        self.assertTrue(auto["pass"],auto)
        claims=auto["synthesized_claims"]
        proof=verify_proof(source(),source_id="D",claims=claims)
        self.assertEqual(proof["status"],"PROOF_CHECKED",proof)
        accepted=[x for x in proof["accepted_claims"] if x.get("proof_primitive")=="MULTI_EFFECT_NATURAL_CLAUSE_V1"]
        self.assertGreaterEqual(len(accepted),22)

    def test_query_context_selects_exception_value(self):
        problem={
            "schema":lattice.SCHEMA,
            "case_id":"multi",
            "source_documents":[{
                "document_id":"D","source_id":"D",
                "source_text":source(),"claims":[],
            }],
            "query":{
                "target_id":"threshold",
                "as_of":"2026-08-01",
                "context":{"small":True},
            },
        }
        out=lattice.evaluate(problem)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"8")
        self.assertTrue(lattice_verify.verify(problem,out)["verified"])

    def test_nonexception_context_uses_replacement(self):
        problem={
            "schema":lattice.SCHEMA,
            "case_id":"multi2",
            "source_documents":[{
                "document_id":"D","source_id":"D",
                "source_text":source(),"claims":[],
            }],
            "query":{
                "target_id":"threshold",
                "as_of":"2026-08-01",
                "context":{"small":False},
            },
        }
        out=lattice.evaluate(problem)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"12")
        self.assertTrue(lattice_verify.verify(problem,out)["verified"])

    def test_conflicting_caller_inventory_is_not_overwritten(self):
        problem={
            "schema":lattice.SCHEMA,
            "case_id":"conflict",
            "source_documents":[{
                "document_id":"D","source_id":"D",
                "source_text":source(),
                "claims":[{
                    "claim_id":"caller",
                    "kind":"CERTIFIED_EFFECT_ID_INVENTORY",
                    "target_id":"threshold",
                    "effect_ids":["A.t"],
                }],
            }],
            "query":{"target_id":"threshold","as_of":"2026-08-01","context":{"small":True}},
        }
        out=lattice.evaluate(problem)
        self.assertFalse(out["pass"],out)

if __name__=="__main__":
    unittest.main()
