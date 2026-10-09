from __future__ import annotations
from hashlib import sha256
import unittest

from canonical.runtime.source_aligned_semantic_proof_v11 import verify_proof
from canonical.runtime.certified_document_effect_field_edge_v1 import (
    field_concept_id,
)
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA,
    evidence_sha256,
)
from canonical.runtime.brain_owned_semantic_relation_edge_authority_v1 import (
    SCHEMA as EDGE_SCHEMA,
    PROOF_CLASS,
)


def mention_id(source_id,scope_id,raw_span):
    return "MENTION:"+sha256(
        (source_id+"\n"+scope_id+"\n"+raw_span).encode()
    ).hexdigest()


class Tests(unittest.TestCase):
    def test_explicit_definition_edge_closes_without_external_verifier(self):
        source_id="doc"
        scope="scope:test"
        raw="Threshold amount"
        target_surface="A.t value 10"
        source_text=raw+" means "+target_surface+"."
        concept=field_concept_id(
            scope_id=scope,effect_id="A.t",field="value",value="10"
        )
        left=mention_id(source_id,scope,raw)
        edge={
            "schema":EDGE_SCHEMA,
            "proof_class":PROOF_CLASS,
            "scope_id":scope,
            "source_id":left,
            "target_id":concept,
            "source_surface":raw,
            "target_surface":target_surface,
            "relation":"ENTAILS",
            "explicit_definition_sources":[{
                "source_id":"definition:doc",
                "scope_id":scope,
                "source_text":source_text,
            }],
        }
        dag={
            "schema":EVIDENCE_SCHEMA,
            "scope_id":scope,
            "left_id":left,
            "right_id":concept,
            "entailment_receipts":[edge],
            "counterexample_receipts":[],
        }
        claim={
            "claim_id":"edge",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD_EDGE",
            "scope_id":scope,
            "effect_id":"A.t",
            "field":"value",
            "value":"10",
            "source_span_chars":[0,len(raw)],
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
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["field"],"value")
        self.assertEqual(rows[0]["value"],"10")
        self.assertEqual(
            rows[0]["proof_primitive"],
            "SEMANTIC_ENTAILMENT_DAG_FIELD_EDGE_V1",
        )

    def test_unsupported_edge_without_external_verifier_remains_rejected(self):
        source_text="Threshold is ten."
        scope="scope:test"
        raw=source_text
        concept=field_concept_id(
            scope_id=scope,effect_id="A.t",field="value",value="10"
        )
        left=mention_id("doc",scope,raw)
        dag={
            "schema":EVIDENCE_SCHEMA,
            "scope_id":scope,
            "left_id":left,
            "right_id":concept,
            "entailment_receipts":[{"kind":"legacy-edge"}],
            "counterexample_receipts":[],
        }
        claim={
            "claim_id":"edge",
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD_EDGE",
            "scope_id":scope,
            "effect_id":"A.t",
            "field":"value",
            "value":"10",
            "source_span_chars":[0,len(raw)],
            "dag_evidence":dag,
            "expected_dag_sha256":evidence_sha256(dag),
        }
        out=verify_proof(
            source_text,
            source_id="doc",
            claims=[claim],
        )
        self.assertEqual(out["status"],"PROOF_CHECKED_WITH_REJECTIONS",out)
        self.assertEqual(out["accepted_claims"],[])
        self.assertIn(
            "RELATION_VERIFIER_REQUIRED",
            out["rejected_claims"][0]["reason"],
        )


if __name__=="__main__":
    unittest.main()
