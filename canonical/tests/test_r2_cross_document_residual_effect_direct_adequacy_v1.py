from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as w
from canonical.runtime import cross_document_residual_effect_frontier_v1 as f
from canonical.runtime import r2_cross_document_residual_effect_direct_adequacy_v1 as d
from canonical.runtime import r2_direct_end_to_end_adequacy_v11 as v11


def _effect(value):
    return {
        "effect_id":"A.t",
        "target_id":"reporting.threshold",
        "effect_class":"DEFINE",
        "value":value,
        "conditions":{},
        "valid_from":None,
        "valid_until":None,
        "supersedes":[],
        "source_locator":"section:A.t",
    }


def _problem(*,values=("10",),proved_inventory=True):
    hypotheses=[
        {"hypothesis_id":f"A.effect.h{i+1}","effect":_effect(v)}
        for i,v in enumerate(values)
    ]
    ws={
        "schema":w.SCHEMA,
        "case_id":"source-backed",
        "hypothesis_set_complete":True,
        "compatibility_constraints_complete":True,
        "incompatible_hypothesis_sets":[],
        "documents":[{
            "document_id":"A",
            "effect_slots":[{
                "slot_id":"A.effect",
                "hypothesis_set_complete":True,
                "hypotheses":hypotheses,
            }],
        }],
        "query":{
            "target_id":"reporting.threshold",
            "as_of":"2026-10-09",
            "context":{},
        },
    }
    if proved_inventory:
        text="Effect IDs only for reporting.threshold: A.t."
        claims=[{
            "claim_id":"inventory",
            "kind":"CERTIFIED_EFFECT_ID_INVENTORY",
            "target_id":"reporting.threshold",
            "effect_ids":["A.t"],
        }]
    else:
        text="The threshold is ten."
        claims=[]
    return {
        "schema":f.SCHEMA,
        "case_id":"source-backed-frontier",
        "source_documents":[{
            "document_id":"A",
            "source_id":"source-A",
            "source_text":text,
            "scope_claim":None,
            "inventory_claims":claims,
        }],
        "worldset_problem":ws,
    }


def _goal():
    return (
        "Using the source-backed cross-document effect case at canonical/tmp/source.json, "
        "compute and independently verify the effective value and save it to "
        "canonical/tmp/out.json."
    )


def _write(root:Path,problem):
    p=root/"canonical/tmp"
    p.mkdir(parents=True,exist_ok=True)
    (p/"source.json").write_text(json.dumps(problem),encoding="utf-8")


class R2CrossDocumentResidualEffectDirectAdequacyV1Tests(unittest.TestCase):
    def test_source_inventory_closed_case_matches_and_runs(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,_problem())
            pf=d.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            self.assertEqual(pf["effective_value"],"10")
            out=d.run({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],"10")
            self.assertTrue(out["source_immutability_verified"])

    def test_unproved_raw_source_remains_unmatched_with_proof_obligation(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,_problem(proved_inventory=False))
            pf=d.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertTrue(pf["direct_route_semantic_open"])
            self.assertEqual(pf["blocking_residual_document_ids"],["A"])
            self.assertEqual(
                pf["next_proof_obligations"][0]["kind"],
                "PROVE_EFFECT_TARGET_SCOPE_OR_QUERY_EFFECT_ID_INVENTORY",
            )

    def test_value_ambiguity_remains_unmatched_after_residual_is_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,_problem(values=("10","11")))
            pf=d.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(pf["matched"],pf)
            self.assertTrue(pf["direct_route_semantic_open"])
            self.assertEqual(pf["blocking_residual_document_ids"],[])
            self.assertEqual(pf["minimum_discriminator_slots"],["A.effect"])
            self.assertEqual(set(pf["possible_outcomes"]),{"10","11"})

    def test_postwrite_verifier_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,_problem())
            op=root/"canonical/tmp/out.json"
            op.write_text('{"old":true}\n',encoding="utf-8")
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


class R2DirectEndToEndAdequacyV11Tests(unittest.TestCase):
    def test_v11_selects_source_backed_route_before_v10(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,_problem())
            with patch.object(v11.v10,"preflight") as prior:
                pf=v11.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertTrue(pf["matched"],pf)
            self.assertEqual(pf["route_id"],d.ROUTE_ID)
            prior.assert_not_called()

    def test_v11_preserves_residual_top_open_without_v10_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,_problem(proved_inventory=False))
            with patch.object(v11.v10,"preflight") as prior:
                pf=v11.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(pf["matched"])
            self.assertTrue(pf["direct_route_semantic_open"])
            self.assertEqual(pf["blocking_residual_document_ids"],["A"])
            prior.assert_not_called()

    def test_v11_preserves_value_ambiguity_without_v10_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); _write(root,_problem(values=("10","11")))
            with patch.object(v11.v10,"preflight") as prior:
                pf=v11.preflight({"task_id":"x","goal":_goal()},repo_root=root)
            self.assertFalse(pf["matched"])
            self.assertEqual(pf["minimum_discriminator_slots"],["A.effect"])
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
