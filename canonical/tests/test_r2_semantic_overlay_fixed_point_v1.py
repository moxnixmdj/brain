from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.tests import test_r2_domain_mapping_dynamic_admission_v1 as prior
from canonical.runtime import r2_cross_document_semantic_registry_v3_lattice_direct_adequacy_v1 as direct
from canonical.runtime import r2_direct_live_admission_v2 as live2
from canonical.runtime import general_adequate_decision_fixed_point_v2 as fixed


def valid_overlay(root:Path):
    good=deepcopy(prior.case(model_only=False)["source_documents"][0]["claims"][0])
    good["claim_id"]="edge.value.domain.overlay"
    raw=(root/"canonical/tmp/case.json").read_bytes()
    return {
        "schema":"PROJECT_BRAIN_R2_SEMANTIC_CLAIM_OVERLAY_V1",
        "input_sha256":sha256(raw).hexdigest(),
        "claims_by_document":{"A":[good]},
    }


def dynamic_row():
    row=prior.dyn_row()
    row["runtime_path"]="canonical/runtime/r2_cross_document_semantic_registry_v3_lattice_direct_adequacy_v1.py"
    return row


class OverlayRouteTests(unittest.TestCase):
    def test_open_route_exposes_hash_bound_overlay_contract(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); prior.write_case(root,prior.case(model_only=True))
            out=direct.preflight({"task_id":"x","goal":prior.goal()},repo_root=root)
            self.assertTrue(out["direct_route_semantic_open"],out)
            contract=out["semantic_claim_overlay_contract"]
            self.assertEqual(contract["request_patch_field"],"semantic_claim_overlay")
            self.assertEqual(contract["input_sha256"],sha256(
                (root/"canonical/tmp/case.json").read_bytes()
            ).hexdigest())
            self.assertFalse(contract["candidate_claims_authority"])

    def test_valid_overlay_closes_route_without_mutating_source(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); prior.write_case(root,prior.case(model_only=True))
            source=root/"canonical/tmp/case.json"; before=source.read_bytes()
            request={
                "task_id":"x","goal":prior.goal(),
                "semantic_claim_overlay":valid_overlay(root),
            }
            pf=direct.preflight(request,repo_root=root)
            self.assertTrue(pf["matched"],pf)
            out=direct.run(request,repo_root=root)
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["effective_value"],"CCOB")
            self.assertEqual(source.read_bytes(),before)
            self.assertTrue(out["source_immutability_verified"])
            self.assertFalse(out["overlay_candidate_claims_were_authority"])

    def test_wrong_hash_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); prior.write_case(root,prior.case(model_only=True))
            ov=valid_overlay(root); ov["input_sha256"]="0"*64
            out=direct.preflight({
                "task_id":"x","goal":prior.goal(),"semantic_claim_overlay":ov
            },repo_root=root)
            self.assertEqual(out["status"],"FAIL_CLOSED")
            self.assertIn("INPUT_SHA256_MISMATCH",out["reason"])

    def test_claim_id_collision_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); prior.write_case(root,prior.case(model_only=True))
            ov=valid_overlay(root)
            ov["claims_by_document"]["A"][0]["claim_id"]="edge.value.domain"
            out=direct.preflight({
                "task_id":"x","goal":prior.goal(),"semantic_claim_overlay":ov
            },repo_root=root)
            self.assertEqual(out["status"],"FAIL_CLOSED")
            self.assertIn("CLAIM_ID_COLLISION",out["reason"])


class AdmissionAndFixedPointTests(unittest.TestCase):
    def test_unique_dynamic_open_is_exposed_when_legacy_idle(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); prior.write_case(root,prior.case(model_only=True))
            with patch.object(live2.v1,"_dynamic_rows",return_value=[dynamic_row()]), \
                 patch.object(live2.v1.legacy,"preflight",return_value={"matched":False,"status":"NO"}):
                out=live2.preflight({"task_id":"x","goal":prior.goal()},repo_root=root)
            self.assertTrue(out["direct_route_semantic_open"],out)
            self.assertEqual(out["semantic_open_precedence_authority"],
                             "UNIQUE_DYNAMIC_OPEN_AND_LEGACY_IDLE")

    def test_dynamic_open_plus_legacy_engagement_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); prior.write_case(root,prior.case(model_only=True))
            with patch.object(live2.v1,"_dynamic_rows",return_value=[dynamic_row()]), \
                 patch.object(live2.v1.legacy,"preflight",return_value={
                     "matched":True,"route_id":"LEGACY","status":"MATCH"
                 }):
                out=live2.preflight({"task_id":"x","goal":prior.goal()},repo_root=root)
            self.assertEqual(out["status"],"FAIL_CLOSED__DIRECT_ROUTE_COLLISION")

    def test_fixed_point_accepts_overlay_then_reenters_direct_route(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); prior.write_case(root,prior.case(model_only=True))
            ov=valid_overlay(root)
            seen={}
            def provider(packet,index,prior_candidates):
                seen["hint"]=packet.get("direct_preflight_hint")
                return {"request_patch":{"semantic_claim_overlay":ov}}
            unresolved={
                "pass":False,"status":"OPEN__SEMANTIC_PROOF_REQUIRED",
                "next_required_edge":"SEMANTIC_PROOF",
                "goal_sha256":"g",
            }
            with patch.object(live2.v1,"_dynamic_rows",return_value=[dynamic_row()]), \
                 patch.object(live2.v1.legacy,"preflight",return_value={"matched":False,"status":"NO"}), \
                 patch.object(fixed,"run_controller",return_value=unresolved):
                out=fixed.run(
                    {"task_id":"x","goal":prior.goal()},
                    repo_root=root,proposal_provider=provider,
                    max_fixed_point_steps=2,provider_max_candidates=1,
                )
            self.assertTrue(out["pass"],out)
            self.assertEqual(out["fixed_point_status"],
                             "PASS__R2_DIRECT_END_TO_END_ADEQUACY_CLOSED_AFTER_REPAIR")
            self.assertEqual(out["effective_value"],"CCOB")
            self.assertEqual(
                seen["hint"]["semantic_claim_overlay_contract"]["request_patch_field"],
                "semantic_claim_overlay",
            )

    def test_overlay_merge_is_additive_and_conflicts_fail(self):
        one={
            "schema":fixed.SEMANTIC_OVERLAY_SCHEMA,"input_sha256":"a"*64,
            "claims_by_document":{"A":[{"claim_id":"c1","kind":"X"}]},
        }
        two={
            "schema":fixed.SEMANTIC_OVERLAY_SCHEMA,"input_sha256":"a"*64,
            "claims_by_document":{"A":[{"claim_id":"c2","kind":"Y"}]},
        }
        merged,error=fixed._merge_candidate(
            {"task_id":"x","goal":"g","semantic_claim_overlay":one},
            {"request_patch":{"semantic_claim_overlay":two}},
        )
        self.assertIsNone(error)
        self.assertEqual(
            [x["claim_id"] for x in merged["semantic_claim_overlay"]["claims_by_document"]["A"]],
            ["c1","c2"],
        )
        bad=deepcopy(two); bad["claims_by_document"]["A"][0]["claim_id"]="c1"
        _,error=fixed._merge_candidate(
            {"task_id":"x","goal":"g","semantic_claim_overlay":one},
            {"request_patch":{"semantic_claim_overlay":bad}},
        )
        self.assertIn("MUTATION_FORBIDDEN",error)


if __name__=="__main__":
    unittest.main(verbosity=2)
