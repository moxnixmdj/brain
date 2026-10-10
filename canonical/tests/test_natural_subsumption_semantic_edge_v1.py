from __future__ import annotations
from hashlib import sha256
import unittest

from canonical.runtime.certified_natural_semantic_subsumption_source_v1 import parse
from canonical.runtime.brain_owned_natural_subsumption_closure_edge_authority_v1 import (
    SCHEMA, PROOF_CLASS, verify,
)
from canonical.runtime.brain_owned_semantic_relation_edge_registry_v5 import (
    supported_proof_classes, can_prove, verify as registry_verify,
)
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    RECEIPT_SCHEMA, EVIDENCE_SCHEMA, evidence_sha256,
)
from canonical.runtime.certified_document_effect_field_edge_v1 import (
    field_concept_id,
)
from canonical.runtime.source_aligned_semantic_proof_v15_registry_base import (
    verify_proof,
)


def evidence(*,source="A",target="C",scope="s",text=None,relation="ENTAILS"):
    text=text or (
        "In scope s, every A is a B.\n"
        "In scope s, every B is a C."
    )
    return {
        "schema":SCHEMA,
        "proof_class":PROOF_CLASS,
        "scope_id":scope,
        "source_id":source,
        "target_id":target,
        "relation":relation,
        "natural_subsumption_source":{
            "source_id":"doc",
            "source_text":text,
        },
    }


class NaturalSourceTests(unittest.TestCase):
    def test_exact_natural_subsumption_parses(self):
        out=parse("In scope s, every A is a B.",source_id="doc")
        self.assertEqual(out["status"],"PARSED",out)
        self.assertEqual(len(out["edges"]),1)
        self.assertEqual(out["edges"][0]["source_id"],"A")
        self.assertEqual(out["edges"][0]["target_id"],"B")
        self.assertEqual(out["edges"][0]["semantic_relation"],"SUBSET_ENTAILS")

    def test_unrecognized_language_grants_no_edge(self):
        out=parse("A probably resembles B.",source_id="doc")
        self.assertEqual(out["status"],"PARSED")
        self.assertEqual(out["edges"],[])

    def test_duplicate_and_self_declarations_fail_closed(self):
        dup=(
            "In scope s, every A is a B.\n"
            "In scope s, every A is a B."
        )
        self.assertEqual(parse(dup)["status"],"FAIL_CLOSED")
        self.assertEqual(
            parse("In scope s, every A is a A.")["status"],
            "FAIL_CLOSED",
        )


class NaturalClosureAuthorityTests(unittest.TestCase):
    def test_two_step_nonexplicit_entailment_proved(self):
        out=verify(evidence())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["schema"],RECEIPT_SCHEMA)
        self.assertEqual(out["relation"],"ENTAILS")
        self.assertEqual(out["nonexplicit_entailment_path"],["A","B","C"])
        self.assertEqual(len(out["path_edge_receipts"]),2)

    def test_direct_relation_rejected_as_not_nonexplicit(self):
        out=verify(evidence(
            source="A",target="B",
            text="In scope s, every A is a B.",
        ))
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"REQUESTED_RELATION_IS_EXPLICIT_NOT_NONEXPLICIT")

    def test_wrong_scope_or_negative_relation_not_proved(self):
        wrong=verify(evidence(scope="other"))
        self.assertFalse(wrong["pass"])
        self.assertEqual(wrong["reason"],"NONEXPLICIT_ENTAILMENT_PATH_NOT_PROVED")
        neg=verify(evidence(relation="NOT_ENTAILS"))
        self.assertFalse(neg["pass"])
        self.assertEqual(neg["reason"],"ONLY_POSITIVE_ENTAILS_SUPPORTED")

    def test_registry_v5_recomputes_natural_proof(self):
        raw=evidence()
        self.assertIn("NATURAL_SUBSUMPTION_CLOSURE",supported_proof_classes())
        self.assertTrue(can_prove(raw))
        out=registry_verify(raw)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["proof_class"],"NATURAL_SUBSUMPTION_CLOSURE")


class V15FieldEdgeIntegrationTests(unittest.TestCase):
    def test_natural_nonexplicit_entailment_closes_field_without_callback(self):
        source_text="capital requirement"
        source_id="effect-doc"
        scope="finance"
        effect_id="E1"
        field="value"
        value="12"

        mention="MENTION:"+sha256(
            (source_id+"\n"+scope+"\n"+source_text).encode("utf-8")
        ).hexdigest()
        concept=field_concept_id(
            scope_id=scope,effect_id=effect_id,field=field,value=value
        )
        middle="canonical_threshold_value"
        natural_source=(
            f"In scope {scope}, every {mention} is a {middle}.\n"
            f"In scope {scope}, every {middle} is a {concept}."
        )
        receipt_evidence={
            "schema":SCHEMA,
            "proof_class":PROOF_CLASS,
            "scope_id":scope,
            "source_id":mention,
            "target_id":concept,
            "relation":"ENTAILS",
            "natural_subsumption_source":{
                "source_id":"relation-doc",
                "source_text":natural_source,
            },
        }
        dag={
            "schema":EVIDENCE_SCHEMA,
            "scope_id":scope,
            "left_id":mention,
            "right_id":concept,
            "entailment_receipts":[receipt_evidence],
            "counterexample_receipts":[],
        }
        claim={
            "claim_id":"field-edge",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD_EDGE",
            "scope_id":scope,
            "effect_id":effect_id,
            "field":field,
            "value":value,
            "source_span_chars":[0,len(source_text)],
            "dag_evidence":dag,
            "expected_dag_sha256":evidence_sha256(dag),
        }
        out=verify_proof(
            source_text,
            source_id=source_id,
            claims=[claim],
        )
        self.assertEqual(out["status"],"PROOF_CHECKED",out)
        rows=[
            x for x in out["accepted_claims"]
            if x.get("kind")=="CERTIFIED_DOCUMENT_EFFECT_FIELD"
        ]
        self.assertEqual(len(rows),1,out)
        self.assertEqual(rows[0]["effect_id"],effect_id)
        self.assertEqual(rows[0]["field"],field)
        self.assertEqual(rows[0]["value"],value)
        self.assertEqual(
            rows[0]["proof_primitive"],
            "SEMANTIC_ENTAILMENT_DAG_FIELD_EDGE_V1",
        )


if __name__=="__main__":
    unittest.main()
