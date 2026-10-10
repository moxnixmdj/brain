from __future__ import annotations

from hashlib import sha256
import unittest

from canonical.runtime import brain_owned_oewn_decision_relation_edge_authority_v1 as a
from canonical.runtime.certified_document_effect_field_edge_v1 import field_concept_id
from canonical.runtime.oewn_release_sense_universe_v1 import (
    RELEASE_ID, RELEASE_SHA256, SCHEMA as OEWN_SCHEMA,
)
from canonical.runtime.semantic_relation_entailment_dag_v1 import RECEIPT_SCHEMA


def _universe():
    return {
        "schema":OEWN_SCHEMA,
        "pass":True,
        "release_id":RELEASE_ID,
        "archive_sha256":RELEASE_SHA256,
        "candidate_set_complete_relative_to_release":True,
        "open_world_english_sense_completeness_claimed":False,
        "lemma":"margin",
        "requested_part_of_speech":"n",
        "senses":[
            {"sense_id":"margin%1:01:00::","synset_id":"s1","part_of_speech":"n"},
            {"sense_id":"margin%1:02:00::","synset_id":"s2","part_of_speech":"n"},
        ],
    }


def _mention(source,scope,span):
    return "MENTION:"+sha256((source+"\n"+scope+"\n"+span).encode()).hexdigest()


def _evidence(*,terminal2_same=True,observed=False):
    scope="scope"
    effect_id="E.t"
    field="value"
    value="12"
    target=field_concept_id(
        scope_id=scope,effect_id=effect_id,field=field,value=value
    )
    alt=field_concept_id(
        scope_id=scope,effect_id=effect_id,field=field,value="13"
    )
    s1='margin%1:01:00::'
    s2='margin%1:02:00::'
    sig1='{"effect_field_concept_id":"'+target+'"}'
    sig2='{"effect_field_concept_id":"'+(target if terminal2_same else alt)+'"}'
    lines=[
        "Sense terminal "+s1+": "+sig1,
        "Sense terminal "+s2+": "+sig2,
    ]
    if observed:
        lines += [
            'Sense observation context cost 1 for '+s1+': "profit"',
            'Sense observation context cost 1 for '+s2+': "collateral"',
            'Sense observed context: "profit"',
        ]
    raw_source_id="doc"
    span="margin"
    raw={
        "schema":a.SCHEMA,
        "proof_class":a.PROOF_CLASS,
        "scope_id":scope,
        "source_id":_mention(raw_source_id,scope,span),
        "target_id":target,
        "relation":"ENTAILS",
        "oewn_decision_source":{
            "source_id":raw_source_id,
            "raw_span":span,
            "sense_universe":_universe(),
            "decision_source_id":"decision-evidence",
            "decision_source_text":"\n".join(lines),
            "effect_id":effect_id,
            "field":field,
            "value":value,
        },
    }
    return raw


class OewnDecisionRelationEdgeAuthorityV1Tests(unittest.TestCase):
    def test_terminally_equivalent_senses_prove_without_unique_sense(self):
        out=a.verify(_evidence())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["schema"],RECEIPT_SCHEMA)
        self.assertFalse(out["intended_sense_identified"])
        self.assertEqual(len(out["surviving_sense_ids"]),2)
        self.assertEqual(out["relation"],"ENTAILS")

    def test_action_changing_senses_do_not_prove(self):
        out=a.verify(_evidence(terminal2_same=False))
        self.assertFalse(out["pass"],out)
        self.assertIn("OEWN_DECISION_NOT_SUFFICIENT",out["reason"])

    def test_authenticated_observation_can_narrow_to_field_concept(self):
        out=a.verify(_evidence(terminal2_same=False,observed=True))
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["intended_sense_identified"])
        self.assertEqual(out["surviving_sense_ids"],["margin%1:01:00::"])

    def test_wrong_raw_span_lemma_binding_fails(self):
        raw=_evidence()
        raw["oewn_decision_source"]["raw_span"]="buffer"
        raw["source_id"]=_mention("doc","scope","buffer")
        out=a.verify(raw)
        self.assertFalse(out["pass"])
        self.assertIn("RAW_SPAN_DOES_NOT_MATCH_OEWN_LEMMA",out["reason"])

    def test_wrong_target_field_concept_fails(self):
        raw=_evidence()
        raw["target_id"]="EFFECT_FIELD_CONCEPT::"+"0"*64
        out=a.verify(raw)
        self.assertFalse(out["pass"])
        self.assertIn("EDGE_TARGET_ID_DOES_NOT_BIND_EFFECT_FIELD",out["reason"])

    def test_wrong_mention_id_fails(self):
        raw=_evidence()
        raw["source_id"]="MENTION:"+"0"*64
        out=a.verify(raw)
        self.assertFalse(out["pass"])
        self.assertIn("EDGE_SOURCE_ID_DOES_NOT_BIND_RAW_MENTION",out["reason"])

    def test_only_positive_entails_supported(self):
        raw=_evidence()
        raw["relation"]="NOT_ENTAILS"
        out=a.verify(raw)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"ONLY_POSITIVE_ENTAILS_SUPPORTED")

    def test_missing_terminal_evidence_does_not_prove(self):
        raw=_evidence()
        raw["oewn_decision_source"]["decision_source_text"] = (
            raw["oewn_decision_source"]["decision_source_text"].splitlines()[0]
        )
        out=a.verify(raw)
        self.assertFalse(out["pass"])
        self.assertIn("OEWN_DECISION_NOT_SUFFICIENT",out["reason"])


if __name__=="__main__":
    unittest.main()
