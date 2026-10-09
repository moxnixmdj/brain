from __future__ import annotations
import unittest
from hashlib import sha256

from canonical.runtime.certified_document_effect_field_edge_v1 import (
    field_concept_id,
    prove_field,
)
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA,
    RECEIPT_SCHEMA,
    evidence_sha256,
)


def evidence(scope, left, right, *, rows=None, counters=None):
    return {
        "schema":EVIDENCE_SCHEMA,
        "scope_id":scope,
        "left_id":left,
        "right_id":right,
        "entailment_receipts":list(rows if rows is not None else [{"kind":"entails"}]),
        "counterexample_receipts":list(counters or []),
    }


def verifier_for(scope, source, target):
    def verify(raw):
        relation="NOT_ENTAILS" if raw.get("kind")=="counter" else "ENTAILS"
        return {
            "pass":True,
            "schema":RECEIPT_SCHEMA,
            "scope_id":scope,
            "source_id":source,
            "target_id":target,
            "relation":relation,
            "source_semantics_authenticated":True,
            "target_semantics_authenticated":True,
            "relation_semantics_authenticated":True,
            "verification_authority_mutated":False,
            "evidence_sha256":"a"*64,
            "receipt_sha256":"b"*64,
        }
    return verify


class CertifiedDocumentEffectFieldEdgeV1Tests(unittest.TestCase):
    def setUp(self):
        self.scope="crossdoc:test"
        self.source="doc:A"
        self.raw="Threshold is ten."
        self.left="MENTION:"+sha256(
            (self.source+"\n"+self.scope+"\n"+self.raw).encode("utf-8")
        ).hexdigest()
        self.concept=field_concept_id(
            scope_id=self.scope,
            effect_id="A.t",
            field="value",
            value="10",
        )

    def test_recomputed_entailment_proves_exact_field(self):
        ev=evidence(self.scope,self.left,self.concept)
        out=prove_field(
            source_id=self.source,
            raw_span=self.raw,
            scope_id=self.scope,
            effect_id="A.t",
            field="value",
            value="10",
            dag_evidence=ev,
            expected_dag_sha256=evidence_sha256(ev),
            relation_verifier=verifier_for(
                self.scope,self.left,self.concept
            ),
        )
        self.assertTrue(out["pass"],out)
        receipt=out["field_receipt"]
        self.assertEqual(receipt["effect_id"],"A.t")
        self.assertEqual(receipt["field"],"value")
        self.assertEqual(receipt["value"],"10")
        self.assertEqual(receipt["field_concept_id"],self.concept)
        self.assertTrue(receipt["relation_semantics_recomputed"])
        self.assertFalse(receipt["execution_authority"])
        self.assertFalse(receipt["terminal_authority"])

    def test_missing_relation_verifier_cannot_prove_field(self):
        ev=evidence(self.scope,self.left,self.concept)
        out=prove_field(
            source_id=self.source,
            raw_span=self.raw,
            scope_id=self.scope,effect_id="A.t",field="value",value="10",
            dag_evidence=ev,
            expected_dag_sha256=evidence_sha256(ev),
            relation_verifier=None,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"OPEN__RELATION_VERIFIER_REQUIRED")

    def test_wrong_terminal_concept_does_not_narrow_field(self):
        wrong="EFFECT_FIELD_CONCEPT::"+"0"*64
        ev=evidence(self.scope,self.left,wrong)
        out=prove_field(
            source_id=self.source,
            raw_span=self.raw,
            scope_id=self.scope,effect_id="A.t",field="value",value="10",
            dag_evidence=ev,
            expected_dag_sha256=evidence_sha256(ev),
            relation_verifier=verifier_for(self.scope,self.left,wrong),
        )
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["status"],"OPEN__FIELD_ENTAILMENT_NOT_PROVED")
        self.assertIn("RIGHT_FIELD_CONCEPT_ID",out["reason"])

    def test_other_source_mention_cannot_be_borrowed(self):
        other_left="MENTION:"+sha256(
            ("doc:B"+"\n"+self.scope+"\n"+"Other source.").encode("utf-8")
        ).hexdigest()
        ev=evidence(self.scope,other_left,self.concept)
        out=prove_field(
            source_id=self.source,
            raw_span=self.raw,
            scope_id=self.scope,
            effect_id="A.t",
            field="value",
            value="10",
            dag_evidence=ev,
            expected_dag_sha256=evidence_sha256(ev),
            relation_verifier=verifier_for(
                self.scope,other_left,self.concept
            ),
        )
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["status"],"OPEN__FIELD_ENTAILMENT_NOT_PROVED")
        self.assertIn("LEFT_SOURCE_MENTION_ID",out["reason"])

    def test_tampered_evidence_hash_fails_closed(self):
        ev=evidence(self.scope,self.left,self.concept)
        out=prove_field(
            source_id=self.source,
            raw_span=self.raw,
            scope_id=self.scope,effect_id="A.t",field="value",value="10",
            dag_evidence=ev,
            expected_dag_sha256="0"*64,
            relation_verifier=verifier_for(
                self.scope,self.left,self.concept
            ),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("EVIDENCE_CONTENT_ADDRESS_MISMATCH",out["reason"])

    def test_invalid_relation_receipt_fails_closed(self):
        ev=evidence(self.scope,self.left,self.concept)
        bad=verifier_for("wrong-scope",self.left,self.concept)
        out=prove_field(
            source_id=self.source,
            raw_span=self.raw,
            scope_id=self.scope,effect_id="A.t",field="value",value="10",
            dag_evidence=ev,
            expected_dag_sha256=evidence_sha256(ev),
            relation_verifier=bad,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("ENTAILMENT_RECEIPT_INVALID",out["reason"])

    def test_contradictory_entailment_and_counterexample_fails_closed(self):
        ev=evidence(
            self.scope,self.left,self.concept,
            rows=[{"kind":"entails"}],
            counters=[{"kind":"counter"}],
        )
        out=prove_field(
            source_id=self.source,
            raw_span=self.raw,
            scope_id=self.scope,effect_id="A.t",field="value",value="10",
            dag_evidence=ev,
            expected_dag_sha256=evidence_sha256(ev),
            relation_verifier=verifier_for(
                self.scope,self.left,self.concept
            ),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn(
            "CONTRADICTORY_ENTAILMENT_AND_COUNTEREXAMPLE_EVIDENCE",
            out["reason"],
        )

    def test_invalid_field_value_fails_closed(self):
        ev=evidence(self.scope,self.left,self.concept)
        out=prove_field(
            source_id=self.source,
            raw_span=self.raw,
            scope_id=self.scope,
            effect_id="A.t",
            field="effect_class",
            value="replace",
            dag_evidence=ev,
            expected_dag_sha256=evidence_sha256(ev),
            relation_verifier=verifier_for(
                self.scope,self.left,self.concept
            ),
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("EFFECT_CLASS_NOT_CANONICAL",out["reason"])


if __name__=="__main__":
    unittest.main()
