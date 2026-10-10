from __future__ import annotations
import unittest

from canonical.runtime.certified_bounded_natural_effect_clause_v1 import parse_natural_effect_clauses
from canonical.runtime.source_aligned_semantic_proof_v10 import verify_proof
from canonical.runtime.source_semantic_claim_autofill_v3 import synthesize_missing_claims
from canonical.runtime import cross_document_effect_semantic_lattice_v3 as l
from canonical.runtime import cross_document_effect_semantic_lattice_verify_v3 as lv


def define_source(eid="A.t",value="10",target="threshold"):
    return "\n".join([
        f"The only effects on {target} are {eid}.",
        f"Effect {eid} defines {target} as {value}.",
        f"Effect {eid} is unconditional.",
        f"Effect {eid} has no start date.",
        f"Effect {eid} has no end date.",
        f"Effect {eid} supersedes nothing.",
    ])


def replace_source(eid="B.t",value="12",sup="A.t",target="threshold"):
    return "\n".join([
        f"The only effects on {target} are {eid}.",
        f"Effect {eid} replaces {target} with {value}.",
        f"Effect {eid} is unconditional.",
        f"Effect {eid} has no start date.",
        f"Effect {eid} has no end date.",
        f"Effect {eid} supersedes {sup}.",
    ])

def exception_source(eid="C.t",value="8",sup="B.t",target="threshold"):
    return "\n".join([
        f"The only effects on {target} are {eid}.",
        f"Effect {eid} creates an exception for {target} with value {value}.",
        f'Effect {eid} applies when {{"small":true}}.',
        f"Effect {eid} has no start date.",
        f"Effect {eid} has no end date.",
        f"Effect {eid} supersedes {sup}.",
    ])


def doc(did,text,claims=None):
    return {
        "document_id":did,
        "source_id":did,
        "source_text":text,
        "claims":list(claims or []),
    }


def problem(*docs,context=None):
    return {
        "schema":l.SCHEMA,
        "case_id":"natural",
        "source_documents":list(docs),
        "query":{
            "target_id":"threshold",
            "as_of":"2026-10-09",
            "context":dict(context or {}),
        },
    }


class BoundedNaturalEffectClauseV1Tests(unittest.TestCase):
    def test_define_sentence_yields_three_fields(self):
        out=parse_natural_effect_clauses(
            "Effect A.t defines threshold as 10.",
            source="A",
        )
        self.assertEqual(out["status"],"PARSED",out)
        fields=[x for x in out["clauses"] if x["kind"]=="FIELD"]
        self.assertEqual(
            {(x["field"],x["value"]) for x in fields},
            {("target_id","threshold"),("effect_class","DEFINE"),("value",10)},
        )

    def test_replace_and_supersession_are_separate_proofs(self):
        text="\n".join([
            "Effect B.t replaces threshold with 12.",
            "Effect B.t supersedes A.t.",
        ])
        out=parse_natural_effect_clauses(text,source="B")
        self.assertEqual(out["status"],"PARSED",out)
        by={(x.get("field"),str(x.get("value"))):x for x in out["clauses"]}
        self.assertIn(("effect_class","REPLACE"),by)
        self.assertIn(("supersedes","['A.t']"),by)

    def test_unrecognized_prose_is_not_certified(self):
        out=parse_natural_effect_clauses(
            "The threshold is probably twelve now.",
            source="A",
        )
        self.assertEqual(out["status"],"PARSED")
        self.assertEqual(out["clauses"],[])

    def test_noncanonical_json_value_is_unresolved(self):
        out=parse_natural_effect_clauses(
            "Effect A.t defines threshold as {'x': 1}.",
            source="A",
        )
        self.assertEqual(out["status"],"UNRESOLVED")


class NaturalSourceProofV10Tests(unittest.TestCase):
    def test_natural_field_claim_is_source_proved(self):
        text="Effect A.t defines threshold as 10."
        claim={
            "claim_id":"c",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
            "effect_id":"A.t",
            "field":"effect_class",
            "value":"DEFINE",
        }
        out=verify_proof(text,source_id="A",claims=[claim])
        self.assertEqual(out["status"],"PROOF_CHECKED",out)
        row=out["accepted_claims"][0]
        self.assertEqual(row["proof_primitive"],"BOUNDED_NATURAL_EFFECT_CLAUSE_V1")

    def test_wrong_natural_field_claim_remains_rejected(self):
        text="Effect A.t defines threshold as 10."
        claim={
            "claim_id":"c",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
            "effect_id":"A.t",
            "field":"effect_class",
            "value":"REPLACE",
        }
        out=verify_proof(text,source_id="A",claims=[claim])
        self.assertEqual(out["status"],"PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(len(out["accepted_claims"]),0)

    def test_autofill_synthesizes_complete_define_claim_set(self):
        text=define_source()
        out=synthesize_missing_claims(text,source_id="A",existing_claims=[])
        self.assertTrue(out["pass"],out)
        claims=out["synthesized_claims"]
        inv=[x for x in claims if x["kind"]=="CERTIFIED_EFFECT_ID_INVENTORY"]
        fields=[x for x in claims if x["kind"]=="CERTIFIED_DOCUMENT_EFFECT_FIELD"]
        self.assertEqual(len(inv),1)
        self.assertEqual(
            {x["field"] for x in fields},
            {"target_id","effect_class","value","conditions","valid_from","valid_until","supersedes"},
        )

    def test_wrong_caller_field_blocks_natural_autofill_for_that_slot(self):
        text=define_source()
        wrong={
            "claim_id":"wrong",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
            "effect_id":"A.t",
            "field":"value",
            "value":99,
        }
        out=synthesize_missing_claims(text,source_id="A",existing_claims=[wrong])
        values=[
            x for x in out["synthesized_claims"]
            if x.get("kind")=="CERTIFIED_DOCUMENT_EFFECT_FIELD"
            and x.get("effect_id")=="A.t"
            and x.get("field")=="value"
        ]
        self.assertEqual(values,[])


class NaturalEffectLatticeV3Tests(unittest.TestCase):
    def test_natural_define_closes_without_manual_claims(self):
        p=problem(doc("A",define_source()))
        out=l.evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],10)
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_natural_define_replace_composes(self):
        p=problem(
            doc("A",define_source()),
            doc("B",replace_source()),
        )
        out=l.evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],12)
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_natural_define_replace_exception_composes_when_condition_true(self):
        p=problem(
            doc("A",define_source()),
            doc("B",replace_source()),
            doc("C",exception_source()),
            context={"small":True},
        )
        out=l.evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],8)
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_conditional_exception_falls_back_to_replacement_when_false(self):
        p=problem(
            doc("A",define_source()),
            doc("B",replace_source()),
            doc("C",exception_source()),
            context={"small":False},
        )
        out=l.evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],12)
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_missing_natural_coordinate_stays_top(self):
        lines=define_source().splitlines()
        text="\n".join(x for x in lines if "no end date" not in x)
        p=problem(doc("A",text))
        out=l.evaluate(p)
        self.assertFalse(out["pass"],out)
        atoms=out["open_lattice_atoms"]
        self.assertEqual(len(atoms),1)
        self.assertEqual(atoms[0]["field"],"valid_until")
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_ambiguous_unrecognized_sentence_does_not_narrow(self):
        p=problem(doc("A","The threshold changed somehow."))
        out=l.evaluate(p)
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["open_lattice_atoms"][0]["dimension"],"EFFECT_ID_INVENTORY")
        self.assertTrue(lv.verify(p,out)["verified"])


if __name__=="__main__":
    unittest.main()
