from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as w
from canonical.runtime import cross_document_source_residual_frontier_v1 as c
from canonical.runtime import r2_cross_document_source_residual_direct_adequacy_v1 as d
from canonical.runtime import r2_direct_end_to_end_adequacy_v12 as v12

def _canon(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)

def _sha(raw:bytes):
    return sha256(raw).hexdigest()

def _e(eid,target,value):
    return {
        "effect_id":eid,"target_id":target,"effect_class":"DEFINE","value":value,
        "conditions":{},"valid_from":None,"valid_until":None,"supersedes":[],
        "source_locator":"section:"+eid,
    }

def _slot(slot_id,*effects):
    return {
        "slot_id":slot_id,"hypothesis_set_complete":True,
        "hypotheses":[
            {"hypothesis_id":f"{slot_id}.h{i+1}","effect":effect}
            for i,effect in enumerate(effects)
        ],
    }

def _worldset(*,ambiguous=False,include_other=False):
    effects=[_e("A.t","threshold","10")]
    if ambiguous:
        effects.append(_e("A.t","threshold","11"))
    docs=[{"document_id":"A","effect_slots":[_slot("A.effect",*effects)]}]
    if include_other:
        docs.append({"document_id":"X","effect_slots":[
            _slot("X.effect",_e("X.o","other","alpha"))
        ]})
    return {
        "schema":w.SCHEMA,"case_id":"direct-combined",
        "hypothesis_set_complete":True,
        "compatibility_constraints_complete":True,
        "incompatible_hypothesis_sets":[],
        "documents":docs,
        "query":{"target_id":"threshold","as_of":"2026-10-09","context":{}},
    }

def _case(*,ambiguous=False,include_other=False,tails=None,claims=None):
    tails=tails or {}; claims=claims or {}
    ws=_worldset(ambiguous=ambiguous,include_other=include_other)
    bdocs=[]; rdocs=[]
    for doc in ws["documents"]:
        did=doc["document_id"]; slot=doc["effect_slots"][0]
        base=_canon(slot); source=base
        regions=[{
            "region_id":did+".slot","start":0,"end":len(base.encode()),
            "text_sha256":_sha(base.encode()),
            "mode":"CANONICAL_EFFECT_SLOT_JSON","slot_id":slot["slot_id"],
        }]
        tail=tails.get(did,"")
        if tail:
            start=len(source.encode()); source+=tail
            regions.append({
                "region_id":did+".unknown","start":start,"end":len(source.encode()),
                "text_sha256":_sha(tail.encode()),
                "mode":"OPEN_UNKNOWN_EFFECT","slot_id":None,
            })
        raw=source.encode()
        bdocs.append({
            "document_id":did,"source_text":source,"source_sha256":_sha(raw),
            "coverage_regions":regions,
        })
        spec=claims.get(did,{})
        rdocs.append({
            "document_id":did,"source_id":"src:"+did,"source_text":source,
            "scope_claim":spec.get("scope_claim"),
            "inventory_claims":spec.get("inventory_claims",[]),
        })
    return {
        "schema":c.SCHEMA,"case_id":"direct-combined",
        "byte_coverage_documents":bdocs,
        "residual_source_documents":rdocs,
        "worldset_problem":ws,
    }

def _goal():
    return (
        "Using the source-and-byte-covered cross-document effect case at "
        "canonical/tmp/case.json, compute and independently verify the effective "
        "value and save it to canonical/tmp/out.json."
    )

def _write(root:Path,**kwargs):
    p=root/"canonical/tmp"; p.mkdir(parents=True,exist_ok=True)
    (p/"case.json").write_text(json.dumps(_case(**kwargs)),encoding="utf-8")

class R2CrossDocumentSourceResidualDirectAdequacyV1Tests(unittest.TestCase):
    def test_exact_byte_closed_case_matches_and_runs(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root)
            pf=d.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            self.assertTrue(pf["query_relative_source_completeness_proved"])
            out=d.run({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],"10")
            self.assertTrue(out["source_immutability_verified"])

    def test_query_relevant_unknown_bytes_are_exactly_localized(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,tails={"A":" arbitrary prose"})
            pf=d.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertTrue(pf["direct_route_semantic_open"])
            self.assertEqual(pf["blocking_document_ids"],["A"])
            self.assertEqual(pf["blocking_unknown_regions"][0]["region_id"],"A.unknown")
            self.assertFalse(pf["query_relative_source_completeness_proved"])

    def test_inventory_only_does_not_hide_unknown_bytes(self):
        tail="\nEffect IDs only for threshold: A.t."
        claims={"A":{"inventory_claims":[{
            "claim_id":"inv.A","kind":"CERTIFIED_EFFECT_ID_INVENTORY",
            "target_id":"threshold","effect_ids":["A.t"],
        }]}}
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,tails={"A":tail},claims=claims)
            pf=d.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertIn("inventory_warning",pf["next_proof_obligations"][0])

    def test_target_exclusion_can_close_unknown_other_document(self):
        tail="\nEffect targets only: other."
        claims={"X":{"scope_claim":{
            "claim_id":"scope.X","kind":"CERTIFIED_EFFECT_TARGET_SCOPE",
            "target_ids":["other"],
        }}}
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,include_other=True,tails={"X":tail},claims=claims)
            out=d.run({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],"10")

    def test_finite_ambiguity_remains_unmatched(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,ambiguous=True)
            pf=d.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertEqual(pf["minimum_discriminator_slots"],["A.effect"])
            self.assertEqual(set(pf["possible_outcomes"]),{"10","11"})
            self.assertTrue(pf["query_relative_source_completeness_proved"])

    def test_postwrite_verifier_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root)
            op=root/"canonical/tmp/out.json"; op.write_text('{"old":true}\n')
            old=op.read_bytes()
            original=d.verifier.verify; calls={"n":0}
            def injected(problem,result):
                calls["n"]+=1
                if calls["n"]>=3:
                    return {"verified":False,"errors":["forced"]}
                return original(problem,result)
            with patch.object(d.verifier,"verify",side_effect=injected):
                out=d.run({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(out["pass"],out)
            self.assertTrue(out["rollback_complete"])
            self.assertEqual(op.read_bytes(),old)

class R2DirectEndToEndAdequacyV12Tests(unittest.TestCase):
    def test_v12_selects_combined_route_before_v11(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root)
            with patch.object(v12.v11,"preflight") as prior:
                pf=v12.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            self.assertEqual(pf["route_id"],d.ROUTE_ID)
            prior.assert_not_called()

    def test_v12_preserves_combined_open_state_without_v11_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,tails={"A":" unknown"})
            with patch.object(v12.v11,"preflight") as prior:
                pf=v12.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(pf["matched"])
            self.assertTrue(pf["direct_route_semantic_open"])
            self.assertEqual(pf["blocking_unknown_regions"][0]["region_id"],"A.unknown")
            prior.assert_not_called()

    def test_v12_delegates_unrelated_request_to_v11(self):
        request={"task_id":"x","goal":"Do something unrelated."}
        expected={"matched":False,"pass":False,"status":"V11_FALLBACK"}
        with patch.object(v12.v11,"preflight",return_value=expected) as prior:
            out=v12.preflight(request)
        self.assertEqual(out,expected)
        prior.assert_called_once()

if __name__=="__main__":
    unittest.main()
