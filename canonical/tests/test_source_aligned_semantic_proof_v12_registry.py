from __future__ import annotations

from hashlib import sha256
import json
import unittest

from canonical.runtime.source_aligned_semantic_proof_v12 import verify_proof
from canonical.runtime.certified_document_effect_field_edge_v1 import field_concept_id
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA,
    evidence_sha256,
)
from canonical.runtime.brain_owned_bounded_semantic_relation_edge_authority_v1 import (
    SCHEMA as EDGE_SCHEMA,
    PROOF_CLASS,
)


def mention_id(source_id,scope_id,raw_span):
    return "MENTION:"+sha256(
        (source_id+"\n"+scope_id+"\n"+raw_span).encode()
    ).hexdigest()


def canon(value):
    return json.dumps(
        value,sort_keys=True,separators=(",",":"),
        ensure_ascii=False,allow_nan=False,
    )


def declaration_source(scope,left,right):
    return "\n".join([
        "Semantic universe: "+canon({
            "members":["a","b"],
            "scope_id":scope,
        }),
        "Semantic extension: "+canon({
            "concept_id":left,
            "members":["a"],
            "scope_id":scope,
        }),
        "Semantic extension: "+canon({
            "concept_id":right,
            "members":["a","b"],
            "scope_id":scope,
        }),
    ])


class Tests(unittest.TestCase):
    def test_bounded_extension_edge_closes_field_without_external_verifier(self):
        source_id="doc"
        scope="scope:test"
        raw="Threshold amount"
        source_text=raw
        concept=field_concept_id(
            scope_id=scope,
            effect_id="A.t",
            field="value",
            value="10",
        )
        left=mention_id(source_id,scope,raw)
        edge={
            "schema":EDGE_SCHEMA,
            "proof_class":PROOF_CLASS,
            "scope_id":scope,
            "source_id":left,
            "target_id":concept,
            "relation":"ENTAILS",
            "bounded_extension_source":{
                "source_id":"decl",
                "scope_id":scope,
                "source_text":declaration_source(scope,left,concept),
            },
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

    def test_source_disproved_bounded_entailment_fails_closed(self):
        source_id="doc"
        scope="scope:test"
        raw="Threshold amount"
        concept=field_concept_id(
            scope_id=scope,effect_id="A.t",field="value",value="10"
        )
        left=mention_id(source_id,scope,raw)
        text="\n".join([
            "Semantic universe: "+canon({"members":["a","b"],"scope_id":scope}),
            "Semantic extension: "+canon({"concept_id":left,"members":["a","b"],"scope_id":scope}),
            "Semantic extension: "+canon({"concept_id":concept,"members":["a"],"scope_id":scope}),
        ])
        edge={
            "schema":EDGE_SCHEMA,
            "proof_class":PROOF_CLASS,
            "scope_id":scope,
            "source_id":left,
            "target_id":concept,
            "relation":"ENTAILS",
            "bounded_extension_source":{
                "source_id":"decl","scope_id":scope,"source_text":text,
            },
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
            "claim_id":"edge","kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD_EDGE",
            "scope_id":scope,"effect_id":"A.t","field":"value","value":"10",
            "source_span_chars":[0,len(raw)],
            "dag_evidence":dag,
            "expected_dag_sha256":evidence_sha256(dag),
        }
        out=verify_proof(raw,source_id=source_id,claims=[claim])
        self.assertEqual(out["status"],"FAIL_CLOSED",out)
        self.assertTrue(any(
            "DOCUMENT_EFFECT_FIELD_EDGE_FAIL_CLOSED" in item
            for item in out["errors"]
        ))

    def test_unsupported_registry_class_remains_rejected(self):
        source_id="doc"; scope="scope:test"; raw="Threshold amount"
        concept=field_concept_id(
            scope_id=scope,effect_id="A.t",field="value",value="10"
        )
        left=mention_id(source_id,scope,raw)
        edge={
            "schema":EDGE_SCHEMA,
            "proof_class":"MODEL_GUESS",
            "scope_id":scope,
            "source_id":left,
            "target_id":concept,
            "relation":"ENTAILS",
            "bounded_extension_source":{
                "source_id":"decl","scope_id":scope,
                "source_text":declaration_source(scope,left,concept),
            },
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
            "claim_id":"edge","kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD_EDGE",
            "scope_id":scope,"effect_id":"A.t","field":"value","value":"10",
            "source_span_chars":[0,len(raw)],
            "dag_evidence":dag,
            "expected_dag_sha256":evidence_sha256(dag),
        }
        out=verify_proof(raw,source_id=source_id,claims=[claim])
        self.assertEqual(out["status"],"PROOF_CHECKED_WITH_REJECTIONS",out)
        self.assertEqual(out["accepted_claims"],[])


if __name__=="__main__":
    unittest.main()
