from __future__ import annotations
import unittest
from unittest.mock import Mock,patch
from canonical.runtime import one_shot_verified_closure_v1 as closure

class OneShotR2CoverageBridgeTests(unittest.TestCase):
    def _snap(self,digest,residuals):
        r2={"path":"canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
            "current_r2_sha256":"r2-"+digest,"status":"ACTIVE",
            "scheduler_cut":{"path":"cut-"+digest},"internal_residuals":residuals,
            "residual_digest":"res-"+digest}
        return {"schema":closure.SCHEMA,"digest":digest,"state_sha256":"state-"+digest,
                "payload":{"state_file":{"path":"state","sha256":"state-"+digest,"bytes":1},
                           "files":[],"pending":[],"stats":{},"r2_authority":r2}}

    def _residual(self,boundary="semantic-tail"):
        return [{"cell_id":"FINANCE_SEMANTIC_ADEQUACY_TAIL",
                 "state":"INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT",
                 "required_action":"ACQUIRE_MINIMUM_BINDING","remaining_boundary":boundary,
                 "wake_on":["NEW_BINDING"],"verified_positive_subregion_ids":["A"]}]

    def _drain(self):
        return {"status":"IMPROVEMENT_QUEUE_STABLE","pass":True,"progress_count":0,"actions":[]}

    def test_empty_r3_queue_with_r2_residual_is_not_closed(self):
        snaps=[self._snap("a",self._residual()) for _ in range(3)]
        with patch.object(closure,"frontier_snapshot",side_effect=snaps),patch.object(closure.r3,"drain",return_value=self._drain()):
            out=closure.run(repo_root=".",state_path="state.json")
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"OPEN__R2_INTERNAL_UNSOLVED_GAP_REMAINS")
        self.assertTrue(out["residual"]["internally_solvable_gap_remaining"])

    def test_provider_pass_claim_without_authority_change_gets_no_credit(self):
        snaps=[self._snap("a",self._residual()) for _ in range(4)]
        provider=Mock(return_value={"pass":True,"status":"DONE"})
        with patch.object(closure,"frontier_snapshot",side_effect=snaps),patch.object(closure.r3,"drain",return_value=self._drain()):
            out=closure.run(repo_root=".",state_path="state.json",r2_coverage_provider=provider)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"OPEN__R2_COVERAGE_PROVIDER_DID_NOT_ADVANCE_CANONICAL_RESIDUAL")
        self.assertEqual(provider.call_count,1)
        self.assertFalse(out["transcript"][-1]["authority_changed"])
        self.assertFalse(out["transcript"][-1]["residual_changed"])

    def test_authority_and_residual_change_advances_then_rechecks(self):
        snaps=[
            self._snap("a",self._residual("old")),
            self._snap("a",self._residual("old")),
            self._snap("a",self._residual("old")),
            self._snap("b",[]),
            self._snap("b",[]),
            self._snap("b",[]),
        ]
        provider=Mock(return_value={"pass":True,"status":"CANDIDATE_ONLY"})
        with patch.object(closure,"frontier_snapshot",side_effect=snaps),patch.object(closure.r3,"drain",return_value=self._drain()):
            out=closure.run(repo_root=".",state_path="state.json",r2_coverage_provider=provider)
        self.assertTrue(out["pass"])
        self.assertEqual(out["status"],"VERIFIED_INTERNAL_FIXED_POINT__IMPROVEMENT_QUEUE_EMPTY")
        self.assertEqual(out["r2_internal_residual_count"],0)
        self.assertEqual(provider.call_count,1)
        r2_actions=[x for x in out["transcript"] if x.get("action")=="R2_COVERAGE_PROVIDER"]
        self.assertEqual(len(r2_actions),1)
        self.assertTrue(r2_actions[0]["authority_changed"])
        self.assertTrue(r2_actions[0]["residual_changed"])

    def test_real_current_v35_snapshot_exposes_finance_residual(self):
        snap=closure.frontier_snapshot(
            repo_root="/home/sprite/brain",
            state_path="/home/sprite/brain/canonical/runtime/SELF_IMPROVEMENT_STATE_V1.json",
        )
        rows=snap["payload"]["r2_authority"]["internal_residuals"]
        self.assertTrue(any(r["cell_id"]=="FINANCE_SEMANTIC_ADEQUACY_TAIL" for r in rows))

if __name__=="__main__":
    unittest.main()
