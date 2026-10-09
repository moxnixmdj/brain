from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as w
from canonical.runtime import r2_cross_document_effect_worldset_direct_adequacy_v1 as d
from canonical.runtime import r2_direct_end_to_end_adequacy_v10 as v10

def _e(eid,target,cls,value,*,cond=None,start=None,sup=None):
    return {
        "effect_id":eid,"target_id":target,"effect_class":cls,"value":value,
        "conditions":cond or {},"valid_from":start,"valid_until":None,
        "supersedes":sup or [],"source_locator":"section:"+eid,
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

def _case(*,small=True):
    return {
        "schema":w.SCHEMA,
        "case_id":"worldset-direct",
        "hypothesis_set_complete":True,
        "documents":[
            {"document_id":"A","effect_slots":[
                _slot("A.effect",_e("A.t","threshold","DEFINE","10"))
            ]},
            {"document_id":"B","effect_slots":[
                _slot(
                    "B.effect",
                    _e("B.t","threshold","REPLACE","12",start="2026-07-01",sup=["A.t"]),
                    _e("B.t","threshold","REPLACE","13",start="2026-07-01",sup=["A.t"]),
                )
            ]},
            {"document_id":"C","effect_slots":[
                _slot(
                    "C.effect",
                    _e("C.t","threshold","EXCEPTION","8",
                       cond={"small":True},start="2026-07-01",sup=["B.t"]),
                )
            ]},
        ],
        "query":{
            "target_id":"threshold",
            "as_of":"2026-08-01",
            "context":{"small":small},
        },
    }

def _goal():
    return (
        "Using the cross-document effect hypothesis case at canonical/tmp/worlds.json, "
        "compute and independently verify the effective value and save it to "
        "canonical/tmp/out.json."
    )

def _write(root:Path,*,small=True):
    p=root/"canonical/tmp"; p.mkdir(parents=True,exist_ok=True)
    (p/"worlds.json").write_text(json.dumps(_case(small=small)),encoding="utf-8")

class R2CrossDocumentEffectWorldsetDirectAdequacyV1Tests(unittest.TestCase):
    def test_invariant_worldset_matches_and_runs(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,small=True)
            pf=d.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            self.assertEqual(pf["world_count"],2)
            out=d.run({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],"8")
            self.assertEqual(out["world_count"],2)
            self.assertTrue(out["source_immutability_verified"])

    def test_outcome_changing_ambiguity_is_unmatched_with_minimum_discriminator(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,small=False)
            pf=d.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertTrue(pf["direct_route_semantic_open"])
            self.assertEqual(pf["minimum_discriminator_slots"],["B.effect"])
            self.assertEqual(set(pf["possible_outcomes"]),{"12","13"})

    def test_postwrite_verifier_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,small=True)
            op=root/"canonical/tmp/out.json"; op.write_text('{"old":true}\n')
            old=op.read_bytes()
            original=d.verifier.verify
            calls={"n":0}
            def injected(case,result):
                calls["n"]+=1
                if calls["n"]>=3:
                    return {"verified":False,"errors":["forced"]}
                return original(case,result)
            with patch.object(d.verifier,"verify",side_effect=injected):
                out=d.run({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["rollback_complete"])
            self.assertEqual(op.read_bytes(),old)

    def test_nonmatching_goal_has_no_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            out=d.preflight({"task_id":"x","goal":"Analyze these files."},repo_root=root)
            self.assertFalse(out["matched"])
            self.assertEqual(out["status"],"NOT_APPLICABLE")

class R2DirectEndToEndAdequacyV10Tests(unittest.TestCase):
    def test_v10_selects_worldset_before_v9_for_closed_case(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,small=True)
            with patch.object(v10.v9,"preflight") as prior:
                pf=v10.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            self.assertEqual(pf["route_id"],d.ROUTE_ID)
            prior.assert_not_called()

    def test_v10_preserves_open_worldset_discriminator_without_v9_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,small=False)
            with patch.object(v10.v9,"preflight") as prior:
                pf=v10.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(pf["matched"])
            self.assertTrue(pf["direct_route_semantic_open"])
            self.assertEqual(pf["minimum_discriminator_slots"],["B.effect"])
            prior.assert_not_called()

    def test_v10_delegates_unrelated_request_to_v9(self):
        request={"task_id":"x","goal":"Do something unrelated."}
        expected={"matched":False,"pass":False,"status":"V9_FALLBACK"}
        with patch.object(v10.v9,"preflight",return_value=expected) as prior:
            out=v10.preflight(request)
        self.assertEqual(out,expected)
        prior.assert_called_once()

if __name__=="__main__":
    unittest.main()
