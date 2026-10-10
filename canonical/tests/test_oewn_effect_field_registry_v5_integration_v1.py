from __future__ import annotations

from hashlib import sha256
import json
import unittest

from canonical.runtime import brain_owned_semantic_relation_edge_registry_v4 as registry_v4
from canonical.runtime import brain_owned_semantic_relation_edge_registry_v5 as registry_v5
from canonical.runtime.certified_document_effect_field_edge_v1 import field_concept_id
from canonical.runtime.cross_document_effect_semantic_lattice_v8 import evaluate as evaluate_v8
from canonical.runtime.cross_document_effect_semantic_lattice_v9 import evaluate as evaluate_v9
from canonical.runtime.cross_document_effect_semantic_lattice_verify_v9 import verify as verify_v9
from canonical.runtime.oewn_release_sense_universe_v1 import (
    RELEASE_ID, RELEASE_SHA256, SCHEMA as OEWN_SCHEMA,
)
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    EVIDENCE_SCHEMA, evidence_sha256,
)


def _universe():
    return {
        "schema":OEWN_SCHEMA,
        "pass":True,
        "release_id":RELEASE_ID,
        "archive_sha256":RELEASE_SHA256,
        "candidate_set_complete_relative_to_release":True,
        "open_world_english_sense_completeness_claimed":False,
        "lemma":"define",
        "requested_part_of_speech":"v",
        "senses":[
            {"sense_id":"define%2:01:00::","synset_id":"s1","part_of_speech":"v"},
            {"sense_id":"define%2:02:00::","synset_id":"s2","part_of_speech":"v"},
        ],
    }


def _mention(source,scope,span):
    return "MENTION:"+sha256((source+"\n"+scope+"\n"+span).encode()).hexdigest()


def _field_line(effect_id,field,value):
    payload={"effect_id":effect_id,"field":field,"value":value}
    return "Effect field: "+json.dumps(
        payload,sort_keys=True,separators=(",",":"),ensure_ascii=False
    )


def _problem(*,terminally_equivalent=True,schema="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_SEMANTIC_LATTICE_V9"):
    source_id="doc"
    scope="scope"
    effect_id="E.t"
    target="threshold"
    lines=[
        "Effect IDs only for threshold: E.t.",
        _field_line(effect_id,"value","10"),
        _field_line(effect_id,"conditions",{}),
        _field_line(effect_id,"valid_from",None),
        _field_line(effect_id,"valid_until",None),
        _field_line(effect_id,"supersedes",[]),
        "define",
    ]
    source_text="\n".join(lines)
    span_start=source_text.rindex("define")
    span_end=span_start+len("define")
    concept=field_concept_id(
        scope_id=scope,
        effect_id=effect_id,
        field="effect_class",
        value="DEFINE",
    )
    alt=field_concept_id(
        scope_id=scope,
        effect_id=effect_id,
        field="effect_class",
        value="OVERRIDE",
    )
    s1="define%2:01:00::"
    s2="define%2:02:00::"
    decision_lines=[
        'Sense terminal '+s1+': {"effect_field_concept_id":"'+concept+'"}',
        'Sense terminal '+s2+': {"effect_field_concept_id":"'
        +(concept if terminally_equivalent else alt)+'"}',
    ]
    raw_receipt={
        "schema":"PROJECT_BRAIN_SEMANTIC_RELATION_EDGE_EVIDENCE_V1",
        "proof_class":"OEWN_DECISION_RELATION",
        "scope_id":scope,
        "source_id":_mention(source_id,scope,"define"),
        "target_id":concept,
        "relation":"ENTAILS",
        "oewn_decision_source":{
            "source_id":source_id,
            "raw_span":"define",
            "sense_universe":_universe(),
            "decision_source_id":"lexical-decision",
            "decision_source_text":"\n".join(decision_lines),
            "effect_id":effect_id,
            "field":"effect_class",
            "value":"DEFINE",
        },
    }
    dag={
        "schema":EVIDENCE_SCHEMA,
        "scope_id":scope,
        "left_id":_mention(source_id,scope,"define"),
        "right_id":concept,
        "entailment_receipts":[raw_receipt],
        "counterexample_receipts":[],
    }

    claims=[
        {
            "claim_id":"inventory",
            "kind":"CERTIFIED_EFFECT_ID_INVENTORY",
            "target_id":"threshold",
            "effect_ids":["E.t"],
        },
    ]
    for field,value in (
        ("value","10"),
        ("conditions",{}),
        ("valid_from",None),
        ("valid_until",None),
        ("supersedes",[]),
    ):
        claims.append({
            "claim_id":"field."+field,
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
            "effect_id":effect_id,
            "field":field,
            "value":value,
        })
    claims.append({
        "claim_id":"field.effect_class.lexical",
        "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD_EDGE",
        "scope_id":scope,
        "effect_id":effect_id,
        "field":"effect_class",
        "value":"DEFINE",
        "source_span_chars":[span_start,span_end],
        "dag_evidence":dag,
        "expected_dag_sha256":evidence_sha256(dag),
    })

    return {
        "schema":schema,
        "case_id":"oewn-field",
        "source_documents":[{
            "document_id":"D",
            "source_id":source_id,
            "source_text":source_text,
            "claims":claims,
        }],
        "query":{"target_id":target,"as_of":"2026-10-10","context":{}},
    }


class OewnEffectFieldRegistryV5IntegrationTests(unittest.TestCase):
    def test_registry_v5_adds_oewn_without_losing_v4_classes(self):
        old=set(registry_v4.supported_proof_classes())
        new=set(registry_v5.supported_proof_classes())
        self.assertTrue(old.issubset(new))
        self.assertEqual(new-old,{"OEWN_DECISION_RELATION"})

    def test_registry_v4_leaves_lexical_field_top(self):
        problem=_problem(schema="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_SEMANTIC_LATTICE_V8")
        out=evaluate_v8(problem)
        self.assertFalse(out["pass"],out)
        atoms=[
            x for x in out["open_lattice_atoms"]
            if x.get("effect_id")=="E.t" and x.get("field")=="effect_class"
        ]
        self.assertEqual(len(atoms),1)

    def test_registry_v5_closes_lexical_effect_class(self):
        problem=_problem()
        out=evaluate_v9(problem)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"10")
        check=verify_v9(problem,out)
        self.assertTrue(check["verified"],check)

    def test_action_changing_lexical_senses_remain_top(self):
        problem=_problem(terminally_equivalent=False)
        out=evaluate(problem,relation_verifier=registry_v5.verify)
        self.assertFalse(out["pass"],out)
        atoms=[
            x for x in out["open_lattice_atoms"]
            if x.get("effect_id")=="E.t" and x.get("field")=="effect_class"
        ]
        self.assertEqual(len(atoms),1)
        self.assertEqual(atoms[0]["state"],"TOP")

    def test_producer_and_independent_verifier_agree_on_open_case(self):
        problem=_problem(terminally_equivalent=False)
        out=evaluate(problem,relation_verifier=registry_v5.verify)
        check=verify(
            problem,out,relation_verifier=registry_v5.verify
        )
        self.assertTrue(check["verified"],check)


if __name__=="__main__":
    unittest.main()
