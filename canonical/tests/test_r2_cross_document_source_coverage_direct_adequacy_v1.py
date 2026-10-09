from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as w
from canonical.runtime import r2_cross_document_source_coverage_direct_adequacy_v1 as d
from canonical.runtime import r2_direct_end_to_end_adequacy_v11 as v11

def _canon(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)

def _sha(raw:bytes):
    return sha256(raw).hexdigest()

def _e(eid,cls,value,*,cond=None,start=None,sup=None):
    return {
        "effect_id":eid,"target_id":"threshold","effect_class":cls,"value":value,
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

def _worldset(*,small=True,ambiguous=False):
    be=[_e("B.t","REPLACE","12",start="2026-07-01",sup=["A.t"])]
    if ambiguous:
        be.append(_e("B.t","REPLACE","13",start="2026-07-01",sup=["A.t"]))
    return {
        "schema":w.SCHEMA,
        "case_id":"source-direct",
        "hypothesis_set_complete":True,
        "compatibility_constraints_complete":True,
        "incompatible_hypothesis_sets":[],
        "documents":[
            {"document_id":"A","effect_slots":[_slot("A.effect",_e("A.t","DEFINE","10"))]},
            {"document_id":"B","effect_slots":[_slot("B.effect",*be)]},
            {"document_id":"C","effect_slots":[_slot(
                "C.effect",
                _e("C.t","EXCEPTION","8",cond={"small":True},start="2026-07-01",sup=["B.t"]),
            )]},
        ],
        "query":{"target_id":"threshold","as_of":"2026-08-01","context":{"small":small}},
    }

def _capsule(*,small=True,ambiguous=False,unknown=False):
    problem=_worldset(small=small,ambiguous=ambiguous)
    docs=[]
    for doc in problem["documents"]:
        slot=doc["effect_slots"][0]
        slot_text=_canon(slot)
        source=slot_text
        regions=[{
            "region_id":doc["document_id"]+".slot",
            "start":0,
            "end":len(slot_text.encode()),
            "text_sha256":_sha(slot_text.encode()),
            "mode":"CANONICAL_EFFECT_SLOT_JSON",
            "slot_id":slot["slot_id"],
        }]
        if unknown and doc["document_id"]=="C":
            tail=" unresolved prose"
            start=len(source.encode())
            source+=tail
            regions.append({
                "region_id":"C.unknown",
                "start":start,
                "end":len(source.encode()),
                "text_sha256":_sha(tail.encode()),
                "mode":"OPEN_UNKNOWN_EFFECT",
                "slot_id":None,
            })
        raw=source.encode()
        docs.append({
            "document_id":doc["document_id"],
            "source_text":source,
            "source_sha256":_sha(raw),
            "coverage_regions":regions,
        })
    return {
        "schema":"PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_SOURCE_COVERAGE_GATE_V1",
        "case_id":"source-direct",
        "documents":docs,
        "worldset_problem":problem,
    }

def _goal():
    return (
        "Using the cross-document source coverage case at canonical/tmp/source.json, "
        "compute and independently verify the effective value and save it to "
        "canonical/tmp/out.json."
    )

def _write(root:Path,**kwargs):
    p=root/"canonical/tmp"; p.mkdir(parents=True,exist_ok=True)
    (p/"source.json").write_text(json.dumps(_capsule(**kwargs)),encoding="utf-8")

class R2CrossDocumentSourceCoverageDirectAdequacyV1Tests(unittest.TestCase):
    def test_source_closed_case_matches_and_runs(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,small=True)
            pf=d.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            self.assertTrue(pf["source_byte_coverage_complete"])
            self.assertTrue(pf["finite_effect_hypothesis_completeness_proved"])
            out=d.run({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],"8")
            self.assertTrue(out["source_immutability_verified"])

    def test_unknown_source_bytes_are_unmatched_and_exactly_localized(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,small=True,unknown=True)
            pf=d.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertTrue(pf["direct_route_semantic_open"])
            self.assertEqual(len(pf["open_unknown_regions"]),1)
            self.assertEqual(pf["open_unknown_regions"][0]["region_id"],"C.unknown")
            self.assertTrue(pf["source_byte_coverage_complete"])
            self.assertFalse(pf["finite_effect_hypothesis_completeness_proved"])

    def test_closed_source_effect_ambiguity_returns_minimum_slot(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,small=False,ambiguous=True)
            pf=d.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertEqual(pf["minimum_discriminator_slots"],["B.effect"])
            self.assertEqual(set(pf["possible_outcomes"]),{"12","13"})
            self.assertTrue(pf["finite_effect_hypothesis_completeness_proved"])

    def test_postwrite_verifier_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,small=True)
            op=root/"canonical/tmp/out.json"; op.write_text('{"old":true}\n')
            old=op.read_bytes()
            original=d.verifier.verify
            calls={"n":0}
            def injected(capsule,result):
                calls["n"]+=1
                if calls["n"]>=3:
                    return {"verified":False,"errors":["forced"]}
                return original(capsule,result)
            with patch.object(d.verifier,"verify",side_effect=injected):
                out=d.run({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["rollback_complete"])
            self.assertEqual(op.read_bytes(),old)

class R2DirectEndToEndAdequacyV11Tests(unittest.TestCase):
    def test_v11_selects_source_coverage_before_v10(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,small=True)
            with patch.object(v11.v10,"preflight") as prior:
                pf=v11.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            self.assertEqual(pf["route_id"],d.ROUTE_ID)
            prior.assert_not_called()

    def test_v11_preserves_open_source_region_without_v10_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,small=True,unknown=True)
            with patch.object(v11.v10,"preflight") as prior:
                pf=v11.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(pf["matched"])
            self.assertTrue(pf["direct_route_semantic_open"])
            self.assertEqual(pf["open_unknown_regions"][0]["region_id"],"C.unknown")
            prior.assert_not_called()

    def test_v11_delegates_unrelated_request_to_v10(self):
        request={"task_id":"x","goal":"Do something unrelated."}
        expected={"matched":False,"pass":False,"status":"V10_FALLBACK"}
        with patch.object(v11.v10,"preflight",return_value=expected) as prior:
            out=v11.preflight(request)
        self.assertEqual(out,expected)
        prior.assert_called_once()

if __name__=="__main__":
    unittest.main()
