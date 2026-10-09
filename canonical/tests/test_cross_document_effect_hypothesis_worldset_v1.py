from __future__ import annotations
import unittest

from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as w
from canonical.runtime import cross_document_effect_hypothesis_worldset_verify_v1 as verify

def _e(eid,target,cls,value,*,cond=None,start=None,sup=None):
    return {
        "effect_id":eid,
        "target_id":target,
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

def _problem(*,small=True,add_irrelevant=False):
    docs=[
        {"document_id":"A","effect_slots":[
            _slot("A.effect",_e("A.t","threshold","DEFINE","10")),
        ]},
        {"document_id":"B","effect_slots":[
            _slot(
                "B.effect",
                _e("B.t","threshold","REPLACE","12",start="2026-07-01",sup=["A.t"]),
                _e("B.t","threshold","REPLACE","13",start="2026-07-01",sup=["A.t"]),
            ),
        ]},
        {"document_id":"C","effect_slots":[
            _slot(
                "C.effect",
                _e(
                    "C.t","threshold","EXCEPTION","8",
                    cond={"small":True},
                    start="2026-07-01",
                    sup=["B.t"],
                ),
            ),
        ]},
    ]
    if add_irrelevant:
        docs.append({
            "document_id":"X",
            "effect_slots":[
                _slot(
                    "X.effect",
                    _e("X.t","other","DEFINE","alpha"),
                    _e("X.t","other","DEFINE","beta"),
                )
            ],
        })
    return {
        "schema":w.SCHEMA,
        "case_id":"worldset",
        "hypothesis_set_complete":True,
        "documents":docs,
        "query":{
            "target_id":"threshold",
            "as_of":"2026-08-01",
            "context":{"small":small},
        },
    }

class CrossDocumentEffectHypothesisWorldsetV1Tests(unittest.TestCase):
    def test_ambiguous_amendment_is_irrelevant_under_later_exception(self):
        out=w.evaluate(_problem(small=True))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["effective_value"],"8")
        self.assertEqual(out["world_count"],2)
        self.assertEqual(out["minimum_discriminator_slots"],[])
        self.assertTrue(out["does_not_require_unique_effect_interpretation"])
        self.assertTrue(verify.verify(_problem(small=True),out)["verified"])

    def test_same_ambiguity_reopens_when_exception_not_applicable(self):
        out=w.evaluate(_problem(small=False))
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["status"],"OPEN__TERMINALLY_RELEVANT_EFFECT_AMBIGUITY")
        self.assertEqual(set(out["possible_outcomes"]),{"12","13"})
        self.assertEqual(out["minimum_discriminator_slots"],["B.effect"])
        self.assertTrue(verify.verify(_problem(small=False),out)["verified"])

    def test_irrelevant_second_ambiguity_is_excluded_from_minimum_discriminator(self):
        out=w.evaluate(_problem(small=False,add_irrelevant=True))
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["world_count"],4)
        self.assertEqual(out["minimum_discriminator_slots"],["B.effect"])

    def test_incomplete_global_hypothesis_set_fails_closed(self):
        problem=_problem()
        problem["hypothesis_set_complete"]=False
        out=w.evaluate(problem)
        self.assertFalse(out["pass"])
        self.assertIn("HYPOTHESIS_SET_NOT_DECLARED_COMPLETE",out["reason"])

    def test_incomplete_slot_hypothesis_set_fails_closed(self):
        problem=_problem()
        problem["documents"][1]["effect_slots"][0]["hypothesis_set_complete"]=False
        out=w.evaluate(problem)
        self.assertFalse(out["pass"])
        self.assertIn("SLOT_HYPOTHESIS_SET_NOT_COMPLETE",out["reason"])

    def test_invalid_declared_world_is_not_silently_dropped(self):
        problem=_problem()
        problem["documents"][1]["effect_slots"][0]["hypotheses"][1]["effect"]["target_id"]="other"
        out=w.evaluate(problem)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED__INVALID_DECLARED_HYPOTHESIS_WORLD")
        self.assertIn("CROSS_TARGET_SUPERSESSION",out["reason"])

    def test_semantically_duplicate_hypotheses_fail_closed(self):
        problem=_problem()
        slot=problem["documents"][1]["effect_slots"][0]
        slot["hypotheses"][1]["effect"]=dict(slot["hypotheses"][0]["effect"])
        out=w.evaluate(problem)
        self.assertFalse(out["pass"])
        self.assertIn("SEMANTICALLY_DUPLICATE_HYPOTHESIS",out["reason"])

    def test_world_bound_fails_closed(self):
        problem=_problem()
        extras=[]
        for i in range(12):
            extras.append({
                "document_id":f"Z{i}",
                "effect_slots":[_slot(
                    f"Z{i}.effect",
                    _e(f"Z{i}.a",f"other{i}","DEFINE","a"),
                    _e(f"Z{i}.b",f"other{i}","DEFINE","b"),
                )],
            })
        problem["documents"].extend(extras)
        out=w.evaluate(problem)
        self.assertFalse(out["pass"])
        self.assertIn("WORLD_BOUND_EXCEEDED",out["reason"])

if __name__=="__main__":
    unittest.main()
