from __future__ import annotations
from hashlib import sha256
import json
import unittest

from canonical.runtime.source_aligned_semantic_proof_v11 import verify_proof
from canonical.runtime.certified_document_effect_field_edge_v1 import (
    field_concept_id,
)
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA,
    RECEIPT_SCHEMA,
    evidence_sha256,
)


def mention(source,scope,raw):
    return "MENTION:"+sha256(
        (source+"\n"+scope+"\n"+raw).encode("utf-8")
    ).hexdigest()


def dag(scope,left,right):
    return {
        "schema":EVIDENCE_SCHEMA,
        "scope_id":scope,
        "left_id":left,
        "right_id":right,
        "entailment_receipts":[{"kind":"edge"}],
        "counterexample_receipts":[],
    }


def verifier(scope,left,right):
    def verify(_raw):
        return {
            "pass":True,
            "schema":RECEIPT_SCHEMA,
            "scope_id":scope,
            "source_id":left,
            "target_id":right,
            "relation":"ENTAILS",
            "source_semantics_authenticated":True,
            "target_semantics_authenticated":True,
            "relation_semantics_authenticated":True,
            "verification_authority_mutated":False,
            "evidence_sha256":"a"*64,
            "receipt_sha256":"b"*64,
        }
    return verify


def edge_claim(source_text,*,value="10",span=None):
    scope="crossdoc:v11"
    source="A"
    span=span or [0,len(source_text)]
    raw=source_text[span[0]:span[1]]
    concept=field_concept_id(
        scope_id=scope,effect_id="A.t",field="value",value=value
    )
    ev=dag(scope,mention(source,scope,raw),concept)
    return {
        "claim_id":"edge",
        "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD_EDGE",
        "scope_id":scope,
        "effect_id":"A.t",
        "field":"value",
        "value":value,
        "source_span_chars":span,
        "dag_evidence":ev,
        "expected_dag_sha256":evidence_sha256(ev),
    },verifier(scope,mention(source,scope,raw),concept)


class SourceAlignedSemanticProofV11Tests(unittest.TestCase):
    def test_authenticated_edge_normalizes_to_field_proof(self):
        raw="Threshold is ten."
        claim,rel= edge_claim(raw)
        out=verify_proof(
            raw,source_id="A",claims=[claim],relation_verifier=rel
        )
        self.assertEqual(out["status"],"PROOF_CHECKED",out)
        row=out["accepted_claims"][0]
        self.assertEqual(row["kind"],"CERTIFIED_DOCUMENT_EFFECT_FIELD")
        self.assertEqual(row["effect_id"],"A.t")
        self.assertEqual(row["field"],"value")
        self.assertEqual(row["value"],"10")
        self.assertEqual(
            row["proof_primitive"],
            "SEMANTIC_ENTAILMENT_DAG_FIELD_EDGE_V1",
        )

    def test_missing_relation_verifier_keeps_edge_rejected(self):
        raw="Threshold is ten."
        claim,_=edge_claim(raw)
        out=verify_proof(
            raw,source_id="A",claims=[claim],relation_verifier=None
        )
        self.assertEqual(out["status"],"PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["accepted_claims"],[])
        self.assertIn(
            "RELATION_VERIFIER_REQUIRED",
            out["rejected_claims"][0]["reason"],
        )

    def test_wrong_source_span_cannot_borrow_edge(self):
        raw="Alpha. Threshold is ten."
        start=raw.index("Threshold")
        claim,rel=edge_claim(raw,span=[0,len("Alpha.")])
        # Replace the claim's evidence with an edge for the other span.
        other=raw[start:]
        concept=field_concept_id(
            scope_id="crossdoc:v11",
            effect_id="A.t",field="value",value="10",
        )
        ev=dag(
            "crossdoc:v11",
            mention("A","crossdoc:v11",other),
            concept,
        )
        claim["dag_evidence"]=ev
        claim["expected_dag_sha256"]=evidence_sha256(ev)
        rel=verifier(
            "crossdoc:v11",
            mention("A","crossdoc:v11",other),
            concept,
        )
        out=verify_proof(
            raw,source_id="A",claims=[claim],relation_verifier=rel
        )
        self.assertEqual(out["status"],"PROOF_CHECKED_WITH_REJECTIONS")
        self.assertEqual(out["accepted_claims"],[])
        self.assertIn(
            "LEFT_SOURCE_MENTION_ID",
            out["rejected_claims"][0]["reason"],
        )

    def test_tampered_dag_is_fail_closed(self):
        raw="Threshold is ten."
        claim,rel=edge_claim(raw)
        claim["expected_dag_sha256"]="0"*64
        out=verify_proof(
            raw,source_id="A",claims=[claim],relation_verifier=rel
        )
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn(
            "DOCUMENT_EFFECT_FIELD_EDGE_FAIL_CLOSED",
            out["errors"][0],
        )

    def test_redundant_direct_and_edge_same_value_do_not_duplicate(self):
        payload={"effect_id":"A.t","field":"value","value":"10"}
        line="Effect field: "+json.dumps(
            payload,sort_keys=True,separators=(",",":")
        )
        raw=line
        claim,rel=edge_claim(raw)
        direct={
            "claim_id":"direct",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
            **payload,
        }
        out=verify_proof(
            raw,source_id="A",
            claims=[direct,claim],
            relation_verifier=rel,
        )
        self.assertEqual(out["status"],"PROOF_CHECKED",out)
        rows=[
            x for x in out["accepted_claims"]
            if x.get("kind")=="CERTIFIED_DOCUMENT_EFFECT_FIELD"
        ]
        self.assertEqual(len(rows),1)
        self.assertEqual(
            out["edge_field_receipts"][0]["status"],
            "REDUNDANT_WITH_EXISTING_FIELD_PROOF",
        )

    def test_direct_and_edge_conflict_fails_closed(self):
        payload={"effect_id":"A.t","field":"value","value":"10"}
        raw="Effect field: "+json.dumps(
            payload,sort_keys=True,separators=(",",":")
        )
        edge,rel=edge_claim(raw,value="99")
        direct={
            "claim_id":"direct",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
            **payload,
        }
        out=verify_proof(
            raw,source_id="A",
            claims=[direct,edge],
            relation_verifier=rel,
        )
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("DIRECT_AND_EDGE_FIELD_CONFLICT",out["errors"][0])


if __name__=="__main__":
    unittest.main()
