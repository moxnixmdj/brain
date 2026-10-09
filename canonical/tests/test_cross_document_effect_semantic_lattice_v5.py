from __future__ import annotations
from hashlib import sha256
import json
import unittest

from canonical.runtime import cross_document_effect_semantic_lattice_v5 as l
from canonical.runtime import cross_document_effect_semantic_lattice_verify_v5 as lv
from canonical.runtime.certified_document_effect_field_edge_v1 import field_concept_id
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA,
    evidence_sha256,
)
from canonical.runtime.brain_owned_bounded_semantic_relation_edge_authority_v1 import (
    SCHEMA as EDGE_SCHEMA,
    PROOF_CLASS,
)


def field_line(eid,field,value):
    return "Effect field: "+json.dumps(
        {"effect_id":eid,"field":field,"value":value},
        sort_keys=True,separators=(",",":"),ensure_ascii=False,
    )


def mention(source,scope,raw):
    return "MENTION:"+sha256(
        (source+"\n"+scope+"\n"+raw).encode()
    ).hexdigest()


def canon(v):
    return json.dumps(
        v,sort_keys=True,separators=(",",":"),
        ensure_ascii=False,allow_nan=False,
    )


def bounded_edge(source_text,*,span,value="10",reverse=False):
    scope="crossdoc:v5"
    raw=source_text[span[0]:span[1]]
    concept=field_concept_id(
        scope_id=scope,effect_id="A.t",field="value",value=value
    )
    left=mention("A",scope,raw)
    if reverse:
        left_members=["a","b"]; right_members=["a"]
    else:
        left_members=["a"]; right_members=["a","b"]
    declaration="\n".join([
        "Semantic universe: "+canon({
            "members":["a","b"],"scope_id":scope,
        }),
        "Semantic extension: "+canon({
            "concept_id":left,"members":left_members,"scope_id":scope,
        }),
        "Semantic extension: "+canon({
            "concept_id":concept,"members":right_members,"scope_id":scope,
        }),
    ])
    edge={
        "schema":EDGE_SCHEMA,
        "proof_class":PROOF_CLASS,
        "scope_id":scope,
        "source_id":left,
        "target_id":concept,
        "relation":"ENTAILS",
        "bounded_extension_source":{
            "source_id":"decl","scope_id":scope,"source_text":declaration,
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
    return {
        "claim_id":"edge.value",
        "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD_EDGE",
        "scope_id":scope,
        "effect_id":"A.t",
        "field":"value",
        "value":value,
        "source_span_chars":span,
        "dag_evidence":dag,
        "expected_dag_sha256":evidence_sha256(dag),
    }


def source_without_value():
    return "\n".join([
        "Effect IDs only for threshold: A.t.",
        field_line("A.t","effect_class","DEFINE"),
        field_line("A.t","conditions",{}),
        field_line("A.t","valid_from",None),
        field_line("A.t","valid_until",None),
        field_line("A.t","supersedes",[]),
        "Threshold is ten.",
    ])


def problem(source,claims):
    return {
        "schema":l.SCHEMA,
        "case_id":"registry-lattice",
        "source_documents":[{
            "document_id":"A","source_id":"A",
            "source_text":source,"claims":list(claims),
        }],
        "query":{
            "target_id":"threshold",
            "as_of":"2026-10-09",
            "context":{},
        },
    }


class Tests(unittest.TestCase):
    def test_registry_bounded_edge_closes_missing_field_without_callback(self):
        source=source_without_value()
        raw="Threshold is ten."
        start=source.index(raw)
        claim=bounded_edge(
            source,span=[start,start+len(raw)],value="10"
        )
        p=problem(source,[claim])
        out=l.evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"10")
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_source_disproved_registry_edge_fails_closed(self):
        source=source_without_value()
        raw="Threshold is ten."
        start=source.index(raw)
        claim=bounded_edge(
            source,span=[start,start+len(raw)],value="10",reverse=True
        )
        p=problem(source,[claim])
        out=l.evaluate(p)
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("DOCUMENT_EFFECT_FIELD_EDGE_FAIL_CLOSED",out["reason"])

    def test_unsupported_internal_edge_class_leaves_value_top(self):
        source=source_without_value()
        raw="Threshold is ten."
        start=source.index(raw)
        claim=bounded_edge(
            source,span=[start,start+len(raw)],value="10"
        )
        claim["dag_evidence"]["entailment_receipts"][0]["proof_class"]="MODEL_GUESS"
        claim["expected_dag_sha256"]=evidence_sha256(claim["dag_evidence"])
        p=problem(source,[claim])
        out=l.evaluate(p)
        self.assertFalse(out["pass"],out)
        atoms=[
            x for x in out["open_lattice_atoms"]
            if x.get("dimension")=="DOCUMENT_EFFECT_FIELD"
        ]
        self.assertEqual(len(atoms),1)
        self.assertEqual(atoms[0]["field"],"value")
        self.assertTrue(lv.verify(p,out)["verified"])


if __name__=="__main__":
    unittest.main()
