import unittest
from execution_guard.v22_prewrite_admission import ACTIVE_POINTER_PATH, admission_errors

POINTER={
    "exact_state":{
        "accepted_families":5,"open_families":14,"proved_atomic":14,"unresolved_atomic":24,
        "root1_positive_gap_count":0,"root2_touching_count":18,"root3_touching_count":9,
        "meta_envelope_open_count":8,"total_open_truth_obligations":32,"terminal":False
    },
    "current_shared_causal_interfaces":[
        "EXTERNAL_RESULT_OR_ACCESS","UNIVERSAL_SCOPE_AND_COMPOSITION","BEHAVIORAL_QUOTIENT_AND_TRANSFER"
    ],
    "dormant_wake_only":["HLE_GRADER_RELATION"],
    "meta_dormant_wake_only":["CREATIVE_DIAGRAM_SURFACE_NONINFERIOR"]
}
PTR="1"*40; COUNTER="2"*40; WAKE="3"*40

def base():
    targets=["COMPOSITION_COMPONENT_SCOPED_PROOFS"]
    return {
        "active_pointer_path":ACTIVE_POINTER_PATH,
        "active_pointer_git_blob_sha":PTR,
        "mode":"ACTIVE_INTERFACE",
        "interface":"UNIVERSAL_SCOPE_AND_COMPOSITION",
        "target_truth_obligations":targets,
        "proof_state_reachability":"ATTACKS_CURRENT_ROOT3_SCOPE_PREMISE",
        "fresh_reality_authority":False,
        "terminal_credit_delta":0,
        "claimed_progress_credit":0,
        "work_class":"PROGRESS_CANDIDATE",
        "postchange_evidence_required":True,
        "expected_progress":{
            "effect_kind":"PROOF_NODE_CONTRACTION",
            "target_truth_obligations":targets,
            "success_condition":"CURRENT_ACTIVE_CAUSAL_CLAIM_IS_PROVED_AND_REMOVED_FROM_OPEN_CONTROL_LOOP"
        },
        "currentness":dict(POINTER["exact_state"]),
        "tournament":{
            "proposal_id":"P_TEST",
            "falsifier_id":"F_TEST",
            "decisive_question":"CAN_THIS_PROPOSAL_BE_KILLED?",
            "known_counterexamples_checked":True,
            "counterexample_receipts":[{"path":"canonical/verification/counter.json","git_blob_sha":COUNTER}]
        }
    }

def run(a, action_kind="RECONCILE_FRONTIER", extra=None):
    blobs={"canonical/verification/counter.json":COUNTER}
    blobs.update(extra or {})
    return admission_errors(a,POINTER,pointer_blob_sha=PTR,action_kind=action_kind,receipt_blobs=blobs)

class Tests(unittest.TestCase):
    def test_pass_progress_candidate(self):
        self.assertEqual(run(base()),[])

    def test_stale(self):
        a=base(); a["active_pointer_git_blob_sha"]="f"*40
        self.assertIn("V22_ACTIVE_POINTER_BLOB_STALE_OR_MISMATCH",run(a))

    def test_off_frontier(self):
        a=base(); a["interface"]="H100_SYNTHETIC_REGISTRY"
        self.assertIn("V22_INTERFACE_NOT_CURRENTLY_ACTIVE",run(a))

    def test_wake(self):
        a=base()
        a.update(mode="DORMANT_WAKE",dormant_work_id="HLE_GRADER_RELATION",
                 wake_receipt_path="canonical/verification/wake.json",wake_receipt_git_blob_sha=WAKE)
        a.pop("interface")
        self.assertEqual(run(a,extra={"canonical/verification/wake.json":WAKE}),[])
        self.assertIn("V22_WAKE_RECEIPT_BLOB_STALE_OR_MISMATCH",run(a))

    def test_control_plane(self):
        a=base()
        a.update(
            mode="CONTROL_PLANE_PREREQUISITE",
            control_plane_gap="V22_SCHEDULER_ENFORCEMENT_GAP",
            minimum_prerequisite_for=list(POINTER["current_shared_causal_interfaces"]),
            work_class="CONTROL_PLANE",
            claimed_progress_credit=0,
        )
        a.pop("interface")
        a.pop("expected_progress")
        a.pop("postchange_evidence_required")
        self.assertEqual(run(a,action_kind="GOVERNANCE_GUARD"),[])
        self.assertIn("V22_CONTROL_PLANE_MODE_REQUIRES_GOVERNANCE_ACTION",run(a,action_kind="RECONCILE_FRONTIER"))

    def test_currentness(self):
        a=base(); a["currentness"]["unresolved_atomic"]=23
        self.assertIn("V22_CURRENTNESS_MISMATCH:unresolved_atomic",run(a))

    def test_tournament_required(self):
        a=base(); a.pop("tournament")
        self.assertIn("V22_TOURNAMENT_BINDING_MISSING",admission_errors(a,POINTER,pointer_blob_sha=PTR,action_kind="RECONCILE_FRONTIER"))

    def test_work_class_required(self):
        a=base(); a.pop("work_class")
        self.assertIn("V22_WORK_CLASS_INVALID",run(a))

    def test_control_plane_class_cannot_escape_control_plane_mode(self):
        a=base(); a["work_class"]="CONTROL_PLANE"; a.pop("expected_progress"); a.pop("postchange_evidence_required")
        self.assertIn("V22_CONTROL_PLANE_WORK_CLASS_OUTSIDE_CONTROL_PLANE_MODE",run(a))

    def test_progress_target_mismatch_rejected(self):
        a=base(); a["expected_progress"]["target_truth_obligations"]=["OTHER"]
        self.assertIn("V22_EXPECTED_PROGRESS_TARGET_MISMATCH",run(a))

    def test_progress_effect_kind_must_be_real_contraction(self):
        a=base(); a["expected_progress"]["effect_kind"]="ADD_MORE_CONTRACTS"
        self.assertIn("V22_EXPECTED_PROGRESS_EFFECT_INVALID",run(a))

    def test_progress_requires_postchange_evidence(self):
        a=base(); a["postchange_evidence_required"]=False
        self.assertIn("V22_PROGRESS_POSTCHANGE_EVIDENCE_NOT_REQUIRED",run(a))

    def test_truth_repair_requires_actual_countermodel_receipt(self):
        a=base()
        a["work_class"]="TRUTH_REPAIR"
        a.pop("expected_progress")
        a["tournament"]["counterexample_receipts"]=[]
        a["tournament"]["no_known_counterexample_reason"]="SEARCH_PENDING"
        errors=run(a)
        self.assertIn("V22_TRUTH_REPAIR_COUNTERMODEL_RECEIPT_REQUIRED",errors)

    def test_falsification_probe_is_zero_progress_class(self):
        a=base()
        a["work_class"]="FALSIFICATION_PROBE"
        a.pop("expected_progress")
        a.pop("postchange_evidence_required")
        a["claimed_progress_credit"]=0
        self.assertEqual(run(a),[])

    def test_nonzero_prewrite_progress_credit_rejected(self):
        a=base(); a["claimed_progress_credit"]=1
        self.assertIn("V22_PREWRITE_PROGRESS_CREDIT_NONZERO",run(a))

if __name__=="__main__":
    unittest.main(verbosity=2)
