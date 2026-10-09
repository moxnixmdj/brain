from __future__ import annotations
import unittest

from canonical.runtime.source_semantic_claim_autofill_v4 import synthesize_missing_claims
from canonical.runtime.source_aligned_semantic_proof_v13 import verify_proof
from canonical.runtime import cross_document_effect_semantic_lattice_v6 as lattice
from canonical.runtime import cross_document_effect_semantic_lattice_verify_v6 as lattice_verify

TEXT=(
    "The complete effect B.t on threshold defines it as 12, "
    "is unconditional, has no start date, has no end date, "
    "and supersedes nothing."
)

def problem(text=TEXT):
    return {
        "schema":lattice.SCHEMA,
        "case_id":"comp",
        "source_documents":[{
            "document_id":"B",
            "source_id":"B",
            "source_text":text,
            "claims":[],
        }],
        "query":{"target_id":"threshold","as_of":"2026-10-09","context":{}},
    }

class ProofAndLattice(unittest.TestCase):
    def test_autofill_inventory_and_fields(self):
        out=synthesize_missing_claims(TEXT,source_id="B",existing_claims=[])
        self.assertTrue(out["pass"],out)
        generated=out["synthesized_claims"]
        self.assertEqual(
            sum(x["kind"]=="CERTIFIED_EFFECT_ID_INVENTORY" for x in generated),1
        )
        self.assertEqual(
            sum(x["kind"]=="CERTIFIED_DOCUMENT_EFFECT_FIELD" for x in generated),7
        )

    def test_v13_independently_reparses(self):
        auto=synthesize_missing_claims(TEXT,source_id="B",existing_claims=[])
        out=verify_proof(TEXT,source_id="B",claims=auto["synthesized_claims"])
        self.assertEqual(out["status"],"PROOF_CHECKED",out)
        self.assertEqual(out["rejected_claims"],[])
        rows=[
            x for x in out["accepted_claims"]
            if x.get("proof_primitive")=="COMPOSITIONAL_NATURAL_EFFECT_CLAUSE_V1"
        ]
        self.assertEqual(len(rows),8)

    def test_caller_conflict_not_replaced(self):
        existing=[{
            "claim_id":"caller",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
            "effect_id":"B.t",
            "field":"value",
            "value":99,
        }]
        auto=synthesize_missing_claims(TEXT,source_id="B",existing_claims=existing)
        self.assertTrue(auto["pass"],auto)
        self.assertFalse(any(
            x.get("kind")=="CERTIFIED_DOCUMENT_EFFECT_FIELD"
            and x.get("effect_id")=="B.t"
            and x.get("field")=="value"
            for x in auto["synthesized_claims"]
        ))
        proof=verify_proof(
            TEXT,source_id="B",
            claims=existing+auto["synthesized_claims"],
        )
        self.assertEqual(proof["status"],"PROOF_CHECKED_WITH_REJECTIONS")

    def test_v6_lattice_closes_one_sentence(self):
        p=problem()
        out=lattice.evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],12)
        self.assertTrue(lattice_verify.verify(p,out)["verified"])

    def test_unrecognized_prose_stays_top(self):
        p=problem("The threshold becomes 12 next July.")
        out=lattice.evaluate(p)
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["open_lattice_atoms"][0]["dimension"],"EFFECT_ID_INVENTORY")
        self.assertTrue(lattice_verify.verify(p,out)["verified"])

if __name__=="__main__":
    unittest.main()
