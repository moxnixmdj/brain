from __future__ import annotations
from hashlib import sha256
import json
import unittest

from canonical.runtime import cross_document_effect_semantic_lattice_v4 as l
from canonical.runtime import cross_document_effect_semantic_lattice_verify_v4 as lv
from canonical.runtime.certified_document_effect_field_edge_v1 import (
    field_concept_id,
)
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA,
    RECEIPT_SCHEMA,
    evidence_sha256,
)


def field_line(eid,field,value):
    return "Effect field: "+json.dumps(
        {"effect_id":eid,"field":field,"value":value},
        sort_keys=True,separators=(",",":"),ensure_ascii=False,
    )


def mention(source,scope,raw):
    return "MENTION:"+sha256(
        (source+"\n"+scope+"\n"+raw).encode("utf-8")
    ).hexdigest()


def edge_claim(source_text,*,span,value="10"):
    scope="crossdoc:v4"
    raw=source_text[span[0]:span[1]]
    concept=field_concept_id(
        scope_id=scope,effect_id="A.t",field="value",value=value
    )
    left=mention("A",scope,raw)
    ev={
        "schema":EVIDENCE_SCHEMA,
        "scope_id":scope,
        "left_id":left,
        "right_id":concept,
        "entailment_receipts":[{"kind":"edge"}],
        "counterexample_receipts":[],
    }
    claim={
        "claim_id":"edge.value",
        "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD_EDGE",
        "scope_id":scope,
        "effect_id":"A.t",
        "field":"value",
        "value":value,
        "source_span_chars":span,
        "dag_evidence":ev,
        "expected_dag_sha256":evidence_sha256(ev),
    }
    def verifier(_raw):
        return {
            "pass":True,
            "schema":RECEIPT_SCHEMA,
            "scope_id":scope,
            "source_id":left,
            "target_id":concept,
            "relation":"ENTAILS",
            "source_semantics_authenticated":True,
            "target_semantics_authenticated":True,
            "relation_semantics_authenticated":True,
            "verification_authority_mutated":False,
            "evidence_sha256":"a"*64,
            "receipt_sha256":"b"*64,
        }
    return claim,verifier


def source_without_value():
    lines=[
        "Effect IDs only for threshold: A.t.",
        field_line("A.t","effect_class","DEFINE"),
        field_line("A.t","conditions",{}),
        field_line("A.t","valid_from",None),
        field_line("A.t","valid_until",None),
        field_line("A.t","supersedes",[]),
        "Threshold is ten.",
    ]
    return "\n".join(lines)


def problem(source,claims):
    return {
        "schema":l.SCHEMA,
        "case_id":"edge-lattice",
        "source_documents":[{
            "document_id":"A",
            "source_id":"A",
            "source_text":source,
            "claims":list(claims),
        }],
        "query":{
            "target_id":"threshold",
            "as_of":"2026-10-09",
            "context":{},
        },
    }


class CrossDocumentEffectSemanticLatticeV4Tests(unittest.TestCase):
    def test_authenticated_edge_closes_only_missing_value_field(self):
        source=source_without_value()
        raw="Threshold is ten."
        start=source.index(raw)
        claim,rel=edge_claim(
            source,span=[start,start+len(raw)],value="10"
        )
        p=problem(source,[claim])
        out=l.evaluate(p,relation_verifier=rel)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"10")
        state=out["lattice_documents"][0]["effect_states"]["A.t"]
        self.assertEqual(state["kind"],"EXACT_FIELDS")
        value_state=state["components"]["value"]
        self.assertEqual(value_state["kind"],"EXACT")
        self.assertEqual(value_state["value"],"10")
        self.assertTrue(
            lv.verify(p,out,relation_verifier=rel)["verified"]
        )

    def test_missing_relation_verifier_leaves_value_top(self):
        source=source_without_value()
        raw="Threshold is ten."
        start=source.index(raw)
        claim,_=edge_claim(
            source,span=[start,start+len(raw)],value="10"
        )
        p=problem(source,[claim])
        out=l.evaluate(p)
        self.assertFalse(out["pass"],out)
        atoms=[
            x for x in out["open_lattice_atoms"]
            if x.get("dimension")=="DOCUMENT_EFFECT_FIELD"
        ]
        self.assertEqual(len(atoms),1)
        self.assertEqual(atoms[0]["field"],"value")
        self.assertFalse(out["query_relative_effect_semantics_finite"])
        self.assertTrue(lv.verify(p,out)["verified"])

    def test_edge_bound_to_other_span_cannot_close_value(self):
        source=source_without_value()
        raw="Threshold is ten."
        start=source.index(raw)
        claim,rel=edge_claim(source,span=[0,10],value="10")
        # Replace DAG with one bound to the actual threshold sentence while
        # keeping the claim's declared source span at [0,10].
        concept=field_concept_id(
            scope_id="crossdoc:v4",
            effect_id="A.t",field="value",value="10",
        )
        left=mention("A","crossdoc:v4",raw)
        ev={
            "schema":EVIDENCE_SCHEMA,
            "scope_id":"crossdoc:v4",
            "left_id":left,
            "right_id":concept,
            "entailment_receipts":[{"kind":"edge"}],
            "counterexample_receipts":[],
        }
        claim["dag_evidence"]=ev
        claim["expected_dag_sha256"]=evidence_sha256(ev)
        def wrong_rel(_raw):
            return {
                "pass":True,"schema":RECEIPT_SCHEMA,
                "scope_id":"crossdoc:v4",
                "source_id":left,"target_id":concept,
                "relation":"ENTAILS",
                "source_semantics_authenticated":True,
                "target_semantics_authenticated":True,
                "relation_semantics_authenticated":True,
                "verification_authority_mutated":False,
                "evidence_sha256":"a"*64,"receipt_sha256":"b"*64,
            }
        p=problem(source,[claim])
        out=l.evaluate(p,relation_verifier=wrong_rel)
        self.assertFalse(out["pass"],out)
        atoms=[
            x for x in out["open_lattice_atoms"]
            if x.get("dimension")=="DOCUMENT_EFFECT_FIELD"
        ]
        self.assertEqual(atoms[0]["field"],"value")

    def test_direct_field_and_edge_same_value_are_compatible(self):
        base=source_without_value()
        explicit=field_line("A.t","value","10")
        source=base+"\n"+explicit
        raw="Threshold is ten."
        start=source.index(raw)
        claim,rel=edge_claim(
            source,span=[start,start+len(raw)],value="10"
        )
        p=problem(source,[claim])
        out=l.evaluate(p,relation_verifier=rel)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"10")
        self.assertTrue(
            lv.verify(p,out,relation_verifier=rel)["verified"]
        )

    def test_direct_field_and_edge_conflict_fail_closed(self):
        base=source_without_value()
        explicit=field_line("A.t","value","10")
        source=base+"\n"+explicit
        raw="Threshold is ten."
        start=source.index(raw)
        claim,rel=edge_claim(
            source,span=[start,start+len(raw)],value="99"
        )
        p=problem(source,[claim])
        out=l.evaluate(p,relation_verifier=rel)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("DIRECT_AND_EDGE_FIELD_CONFLICT",out["reason"])


if __name__=="__main__":
    unittest.main()
