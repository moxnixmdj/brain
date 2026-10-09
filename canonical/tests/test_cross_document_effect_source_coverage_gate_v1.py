from __future__ import annotations

from hashlib import sha256
import json
import unittest

from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as w
from canonical.runtime import cross_document_effect_source_coverage_gate_v1 as g
from canonical.runtime import cross_document_effect_source_coverage_gate_verify_v1 as gv
from canonical.runtime import certified_raw_effect_sentence_v1 as rawc


def _canon(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _sha(raw:bytes):
    return sha256(raw).hexdigest()


def _e(eid,cls,value,*,cond=None,start=None,sup=None):
    return {
        "effect_id":eid,
        "target_id":"threshold",
        "effect_class":cls,
        "value":value,
        "conditions":cond or {},
        "valid_from":start,
        "valid_until":None,
        "supersedes":sup or [],
        "source_locator":"section:"+eid,
    }


def _slot(slot_id,*effects):
    return {
        "slot_id":slot_id,
        "hypothesis_set_complete":True,
        "hypotheses":[
            {"hypothesis_id":f"{slot_id}.h{i+1}","effect":effect}
            for i,effect in enumerate(effects)
        ],
    }


def _problem(*,small=True,ambiguous_b=False):
    b_effects=[
        _e("B.t","REPLACE","12",start="2026-07-01",sup=["A.t"])
    ]
    if ambiguous_b:
        b_effects.append(
            _e("B.t","REPLACE","13",start="2026-07-01",sup=["A.t"])
        )
    return {
        "schema":w.SCHEMA,
        "case_id":"coverage",
        "hypothesis_set_complete":True,
        "compatibility_constraints_complete":True,
        "incompatible_hypothesis_sets":[],
        "documents":[
            {"document_id":"A","effect_slots":[
                _slot("A.effect",_e("A.t","DEFINE","10"))
            ]},
            {"document_id":"B","effect_slots":[
                _slot("B.effect",*b_effects)
            ]},
            {"document_id":"C","effect_slots":[
                _slot(
                    "C.effect",
                    _e("C.t","EXCEPTION","8",cond={"small":True},
                       start="2026-07-01",sup=["B.t"]),
                )
            ]},
        ],
        "query":{
            "target_id":"threshold",
            "as_of":"2026-08-01",
            "context":{"small":small},
        },
    }


def _capsule(problem,*,open_tail=False):
    docs=[]
    for doc in problem["documents"]:
        slot=doc["effect_slots"][0]
        slot_text=_canon(slot)
        source_text=slot_text
        regions=[{
            "region_id":doc["document_id"]+".slot",
            "start":0,
            "end":len(slot_text.encode("utf-8")),
            "text_sha256":_sha(slot_text.encode("utf-8")),
            "mode":"CANONICAL_EFFECT_SLOT_JSON",
            "slot_id":slot["slot_id"],
        }]
        if open_tail and doc["document_id"]=="C":
            tail=" arbitrary prose"
            start=len(source_text.encode("utf-8"))
            source_text+=tail
            end=len(source_text.encode("utf-8"))
            regions.append({
                "region_id":"C.unknown",
                "start":start,
                "end":end,
                "text_sha256":_sha(tail.encode("utf-8")),
                "mode":"OPEN_UNKNOWN_EFFECT",
                "slot_id":None,
            })
        raw=source_text.encode("utf-8")
        docs.append({
            "document_id":doc["document_id"],
            "source_text":source_text,
            "source_sha256":_sha(raw),
            "coverage_regions":regions,
        })
    return {
        "schema":g.SCHEMA,
        "case_id":"coverage",
        "documents":docs,
        "worldset_problem":problem,
    }


def _raw_sentence_capsule():
    sentences={
        "A":"Effect A.t defines threshold as 10.",
        "B":"Effect B.t replaces A.t on threshold with 12 effective 2026-07-01.",
        "C":"Effect C.t excepts B.t on threshold with 8 when small = true effective 2026-07-01.",
    }
    slots={}
    docs=[]
    for did in ("A","B","C"):
        sid=did+".effect"
        compiled=rawc.compile_sentence(
            sentences[did],
            document_id=did,
            slot_id=sid,
        )
        assert compiled["pass"], compiled
        slots[did]=compiled["slot"]
        raw=sentences[did].encode("utf-8")
        docs.append({
            "document_id":did,
            "source_text":sentences[did],
            "source_sha256":_sha(raw),
            "coverage_regions":[{
                "region_id":did+".sentence",
                "start":0,
                "end":len(raw),
                "text_sha256":_sha(raw),
                "mode":"CERTIFIED_EFFECT_SENTENCE",
                "slot_id":sid,
            }],
        })
    problem={
        "schema":w.SCHEMA,
        "case_id":"raw-sentences",
        "hypothesis_set_complete":True,
        "compatibility_constraints_complete":True,
        "incompatible_hypothesis_sets":[],
        "documents":[
            {"document_id":did,"effect_slots":[slots[did]]}
            for did in ("A","B","C")
        ],
        "query":{
            "target_id":"threshold",
            "as_of":"2026-08-01",
            "context":{"small":True},
        },
    }
    return {
        "schema":g.SCHEMA,
        "case_id":"raw-sentences",
        "documents":docs,
        "worldset_problem":problem,
    }


class CrossDocumentEffectSourceCoverageGateV1Tests(unittest.TestCase):

    def test_certified_effect_sentences_close_three_document_chain(self):
        cap=_raw_sentence_capsule()
        out=g.evaluate(cap)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],8)
        self.assertEqual(out["world_count"],1)
        self.assertTrue(out["source_byte_coverage_complete"])
        self.assertTrue(out["finite_effect_hypothesis_completeness_proved"])
        self.assertTrue(gv.verify(cap,out)["verified"])

    def test_certified_effect_sentence_worldset_mismatch_fails_closed(self):
        cap=_raw_sentence_capsule()
        effect=cap["worldset_problem"]["documents"][1]["effect_slots"][0]["hypotheses"][0]["effect"]
        effect["value"]=13
        out=g.evaluate(cap)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("CERTIFIED_EFFECT_SENTENCE_WORLDSET_MISMATCH",out["reason"])

    def test_unrecognized_text_cannot_be_mislabeled_certified_sentence(self):
        cap=_raw_sentence_capsule()
        doc=cap["documents"][1]
        text="The threshold changes to twelve."
        raw=text.encode("utf-8")
        doc["source_text"]=text
        doc["source_sha256"]=_sha(raw)
        region=doc["coverage_regions"][0]
        region["end"]=len(raw)
        region["text_sha256"]=_sha(raw)
        out=g.evaluate(cap)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("CERTIFIED_EFFECT_SENTENCE_NOT_PROVED",out["reason"])

    def test_fully_source_closed_worldset_returns_verified_value(self):
        problem=_problem(small=True)
        out=g.evaluate(_capsule(problem))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"8")
        self.assertTrue(out["source_byte_coverage_complete"])
        self.assertTrue(out["finite_effect_hypothesis_completeness_proved"])
        self.assertTrue(gv.verify(_capsule(problem),out)["verified"])

    def test_unknown_source_region_blocks_even_when_finite_worldset_agrees(self):
        problem=_problem(small=True)
        out=g.evaluate(_capsule(problem,open_tail=True))
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["status"],"OPEN__SOURCE_EFFECT_COVERAGE_INCOMPLETE")
        self.assertEqual(out["open_unknown_region_count"],1)
        self.assertTrue(out["source_byte_coverage_complete"])
        self.assertFalse(out["finite_effect_hypothesis_completeness_proved"])
        self.assertTrue(gv.verify(_capsule(problem,open_tail=True),out)["verified"])

    def test_closed_source_but_outcome_changing_effect_ambiguity_remains_open(self):
        problem=_problem(small=False,ambiguous_b=True)
        out=g.evaluate(_capsule(problem))
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["status"],"OPEN__TERMINALLY_RELEVANT_EFFECT_AMBIGUITY")
        self.assertTrue(out["finite_effect_hypothesis_completeness_proved"])
        self.assertEqual(
            out["worldset_result"]["minimum_discriminator_slots"],
            ["B.effect"],
        )
        self.assertTrue(gv.verify(_capsule(problem),out)["verified"])

    def test_unbound_worldset_slot_fails_closed(self):
        problem=_problem()
        cap=_capsule(problem)
        cap["documents"][1]["coverage_regions"][0]["mode"]="OPEN_UNKNOWN_EFFECT"
        cap["documents"][1]["coverage_regions"][0]["slot_id"]=None
        out=g.evaluate(cap)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("WORLDSET_SLOTS_LACK_SOURCE_CLOSURE",out["reason"])

    def test_source_hash_drift_fails_closed(self):
        problem=_problem()
        cap=_capsule(problem)
        cap["documents"][0]["source_sha256"]="0"*64
        out=g.evaluate(cap)
        self.assertFalse(out["pass"])
        self.assertIn("SOURCE_SHA256_MISMATCH",out["reason"])

    def test_source_region_gap_fails_closed(self):
        problem=_problem()
        cap=_capsule(problem)
        cap["documents"][0]["coverage_regions"][0]["start"]=1
        out=g.evaluate(cap)
        self.assertFalse(out["pass"])
        self.assertIn("REGION_PARTITION_INVALID",out["reason"])

    def test_source_slot_worldset_mismatch_fails_closed(self):
        problem=_problem()
        cap=_capsule(problem)
        problem["documents"][0]["effect_slots"][0]["hypotheses"][0]["effect"]["value"]="99"
        out=g.evaluate(cap)
        self.assertFalse(out["pass"])
        self.assertIn("SOURCE_SLOT_WORLDSET_MISMATCH",out["reason"])

    def test_noncanonical_structured_region_fails_closed(self):
        problem=_problem()
        cap=_capsule(problem)
        doc=cap["documents"][0]
        parsed=json.loads(doc["source_text"])
        noncanonical=json.dumps(parsed,indent=2)
        raw=noncanonical.encode("utf-8")
        doc["source_text"]=noncanonical
        doc["source_sha256"]=_sha(raw)
        doc["coverage_regions"][0]["end"]=len(raw)
        doc["coverage_regions"][0]["text_sha256"]=_sha(raw)
        out=g.evaluate(cap)
        self.assertFalse(out["pass"])
        self.assertIn("CANONICAL_EFFECT_SLOT_JSON_NOT_CANONICAL",out["reason"])

    def test_whitespace_region_is_independently_accepted(self):
        problem=_problem()
        cap=_capsule(problem)
        doc=cap["documents"][0]
        space="\n  "
        base=doc["source_text"].encode("utf-8")
        doc["source_text"]+=space
        raw=doc["source_text"].encode("utf-8")
        doc["source_sha256"]=_sha(raw)
        doc["coverage_regions"].append({
            "region_id":"A.ws",
            "start":len(base),
            "end":len(raw),
            "text_sha256":_sha(space.encode("utf-8")),
            "mode":"WHITESPACE_NO_EFFECT",
            "slot_id":None,
        })
        out=g.evaluate(cap)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"8")


if __name__=="__main__":
    unittest.main()
