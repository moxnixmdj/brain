from __future__ import annotations

from hashlib import sha256
import json
import unittest

from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as w
from canonical.runtime import cross_document_source_residual_frontier_v1 as c
from canonical.runtime import cross_document_source_residual_frontier_verify_v1 as cv


def _canon(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)

def _sha(raw:bytes):
    return sha256(raw).hexdigest()

def _e(eid,target,value):
    return {
        "effect_id":eid,
        "target_id":target,
        "effect_class":"DEFINE",
        "value":value,
        "conditions":{},
        "valid_from":None,
        "valid_until":None,
        "supersedes":[],
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

def _worldset(*,ambiguous=False,include_other=False):
    a_effects=[_e("A.t","threshold","10")]
    if ambiguous:
        a_effects.append(_e("A.t","threshold","11"))
    docs=[
        {"document_id":"A","effect_slots":[_slot("A.effect",*a_effects)]},
    ]
    if include_other:
        docs.append({
            "document_id":"X",
            "effect_slots":[_slot("X.effect",_e("X.o","other","alpha"))],
        })
    return {
        "schema":w.SCHEMA,
        "case_id":"combined",
        "hypothesis_set_complete":True,
        "compatibility_constraints_complete":True,
        "incompatible_hypothesis_sets":[],
        "documents":docs,
        "query":{"target_id":"threshold","as_of":"2026-10-09","context":{}},
    }

def _doc_rows(problem,*,tails=None,claims=None):
    tails=tails or {}
    claims=claims or {}
    byte_docs=[]
    residual_docs=[]
    for doc in problem["documents"]:
        did=doc["document_id"]
        slot=doc["effect_slots"][0]
        base=_canon(slot)
        source=base
        regions=[{
            "region_id":did+".slot",
            "start":0,
            "end":len(base.encode()),
            "text_sha256":_sha(base.encode()),
            "mode":"CANONICAL_EFFECT_SLOT_JSON",
            "slot_id":slot["slot_id"],
        }]
        tail=tails.get(did,"")
        if tail:
            start=len(source.encode())
            source+=tail
            regions.append({
                "region_id":did+".unknown",
                "start":start,
                "end":len(source.encode()),
                "text_sha256":_sha(tail.encode()),
                "mode":"OPEN_UNKNOWN_EFFECT",
                "slot_id":None,
            })
        raw=source.encode()
        byte_docs.append({
            "document_id":did,
            "source_text":source,
            "source_sha256":_sha(raw),
            "coverage_regions":regions,
        })
        spec=claims.get(did,{})
        residual_docs.append({
            "document_id":did,
            "source_id":"src:"+did,
            "source_text":source,
            "scope_claim":spec.get("scope_claim"),
            "inventory_claims":spec.get("inventory_claims",[]),
        })
    return byte_docs,residual_docs

def _problem(*,ambiguous=False,include_other=False,tails=None,claims=None):
    ws=_worldset(ambiguous=ambiguous,include_other=include_other)
    byte_docs,residual_docs=_doc_rows(ws,tails=tails,claims=claims)
    return {
        "schema":c.SCHEMA,
        "case_id":"combined",
        "byte_coverage_documents":byte_docs,
        "residual_source_documents":residual_docs,
        "worldset_problem":ws,
    }


class CrossDocumentSourceResidualFrontierV1Tests(unittest.TestCase):
    def test_exact_byte_semantics_discharge_unproved_residual_top(self):
        problem=_problem()
        out=c.evaluate(problem)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"10")
        self.assertEqual(
            out["documents_discharged_by_exact_byte_semantics"],["A"]
        )
        self.assertEqual(
            out["residual_states"]["A"],"TOP_EFFECT_MAY_AFFECT_QUERY"
        )
        self.assertTrue(out["query_relative_source_completeness_proved"])
        self.assertTrue(cv.verify(problem,out)["verified"])

    def test_query_relevant_unknown_prose_blocks(self):
        problem=_problem(tails={"A":" arbitrary prose"})
        out=c.evaluate(problem)
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["status"],"OPEN__QUERY_RELEVANT_SOURCE_TOP_REMAINS")
        self.assertEqual(out["blocking_document_ids"],["A"])
        self.assertEqual(
            out["blocking_unknown_regions"][0]["region_id"],"A.unknown"
        )
        self.assertFalse(out["query_relative_source_completeness_proved"])
        self.assertTrue(cv.verify(problem,out)["verified"])

    def test_effect_id_inventory_alone_does_not_discharge_unknown_prose(self):
        tail="\nEffect IDs only for threshold: A.t."
        claims={
            "A":{
                "inventory_claims":[{
                    "claim_id":"inv.A",
                    "kind":"CERTIFIED_EFFECT_ID_INVENTORY",
                    "target_id":"threshold",
                    "effect_ids":["A.t"],
                }]
            }
        }
        problem=_problem(tails={"A":tail},claims=claims)
        out=c.evaluate(problem)
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["residual_states"]["A"],
            "PROVED_QUERY_EFFECT_ID_INVENTORY_EXHAUSTIVE",
        )
        obligation=out["next_proof_obligations"][0]
        self.assertIn("inventory_warning",obligation)
        self.assertEqual(out["blocking_document_ids"],["A"])
        self.assertTrue(cv.verify(problem,out)["verified"])

    def test_query_target_exclusion_discharges_unknown_other_document(self):
        tail="\nEffect targets only: other."
        claims={
            "X":{
                "scope_claim":{
                    "claim_id":"scope.X",
                    "kind":"CERTIFIED_EFFECT_TARGET_SCOPE",
                    "target_ids":["other"],
                }
            }
        }
        problem=_problem(
            include_other=True,
            tails={"X":tail},
            claims=claims,
        )
        out=c.evaluate(problem)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"10")
        self.assertEqual(
            out["documents_discharged_by_query_target_exclusion"],["X"]
        )
        self.assertEqual(out["residual_states"]["X"],"PROVED_QUERY_IRRELEVANT")
        self.assertTrue(cv.verify(problem,out)["verified"])

    def test_finite_effect_ambiguity_remains_open_after_source_top_closed(self):
        problem=_problem(ambiguous=True)
        out=c.evaluate(problem)
        self.assertFalse(out["pass"],out)
        self.assertEqual(
            out["status"],
            "OPEN__SOURCE_TOP_CLOSED__FINITE_EFFECT_WORLDS_NOT_CLOSED",
        )
        self.assertEqual(set(out["possible_outcomes"]),{"10","11"})
        self.assertEqual(out["minimum_discriminator_slots"],["A.effect"])
        self.assertTrue(out["query_relative_source_completeness_proved"])
        self.assertTrue(cv.verify(problem,out)["verified"])

    def test_byte_and_residual_source_text_must_be_identical(self):
        problem=_problem()
        problem["residual_source_documents"][0]["source_text"]+="x"
        out=c.evaluate(problem)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("BYTE_RESIDUAL_SOURCE_TEXT_MISMATCH",out["reason"])

    def test_scope_proof_inconsistent_with_modeled_effect_fails_closed(self):
        tail="\nEffect targets only: other."
        claims={
            "A":{
                "scope_claim":{
                    "claim_id":"scope.A",
                    "kind":"CERTIFIED_EFFECT_TARGET_SCOPE",
                    "target_ids":["other"],
                }
            }
        }
        problem=_problem(tails={"A":tail},claims=claims)
        out=c.evaluate(problem)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED__RESIDUAL_FRONTIER")
        self.assertTrue(cv.verify(problem,out)["verified"])


if __name__=="__main__":
    unittest.main()
