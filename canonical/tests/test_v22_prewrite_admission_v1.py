import unittest
from execution_guard.v22_prewrite_admission import ACTIVE_POINTER_PATH, admission_errors, referenced_receipt_paths

POINTER={"exact_state":{"accepted_families":5,"open_families":14,"proved_atomic":14,"unresolved_atomic":24,"root1_positive_gap_count":0,"root2_touching_count":18,"root3_touching_count":9,"meta_envelope_open_count":8,"total_open_truth_obligations":32,"terminal":False},"current_shared_causal_interfaces":["EXTERNAL_RESULT_OR_ACCESS","UNIVERSAL_SCOPE_AND_COMPOSITION","BEHAVIORAL_QUOTIENT_AND_TRANSFER"],"dormant_wake_only":["HLE_GRADER_RELATION"],"meta_dormant_wake_only":["CREATIVE_DIAGRAM_SURFACE_NONINFERIOR"]}
PTR="1"*40; COUNTER="2"*40; WAKE="3"*40; PROVISION="4"*40; EXHAUST="5"*40

def external_benchmark():
    a=base()
    a["interface"]="EXTERNAL_RESULT_OR_ACCESS"
    a["target_truth_obligations"]=["MYSTERYMECHANISM_GE_49_55"]
    a["proof_state_reachability"]="OPTIONAL_EXTERNAL_WITNESS_FOR_CURRENT_BENCHMARK_DERIVED_PREDICATE"
    a["benchmark_information_equivalence"]={
        "law_path":"canonical/laws/BENCHMARK_OUTPUT_INFORMATION_EQUIVALENCE_LAW_V1.md",
        "witness_synthesis_path":"canonical/governance/BENCHMARK_WITNESS_ELIMINATION_SYNTHESIS_20261006_V1.json",
        "target_predicates":["MYSTERYMECHANISM_GE_49_55"],
        "current_minimum_information_cut_member":True,
        "route_nondominated_proved":True,
        "internal_certificate_search_state":"NONZERO_INFORMATION_GAIN",
        "external_wait_on_critical_path":False,
        "self_service_access_claimed":False,
    }
    return a
def base():
    return {"active_pointer_path":ACTIVE_POINTER_PATH,"active_pointer_git_blob_sha":PTR,"mode":"ACTIVE_INTERFACE","interface":"UNIVERSAL_SCOPE_AND_COMPOSITION","target_truth_obligations":["COMPOSITION_COMPONENT_SCOPED_PROOFS"],"proof_state_reachability":"ATTACKS_CURRENT_ROOT3_SCOPE_PREMISE","fresh_reality_authority":False,"terminal_credit_delta":0,"currentness":dict(POINTER["exact_state"]),"tournament":{"proposal_id":"P_TEST","falsifier_id":"F_TEST","decisive_question":"CAN_THIS_PROPOSAL_BE_KILLED?","known_counterexamples_checked":True,"counterexample_receipts":[{"path":"canonical/verification/counter.json","git_blob_sha":COUNTER}]}}
class Tests(unittest.TestCase):
    def test_pass(self):
        self.assertEqual(admission_errors(base(),POINTER,pointer_blob_sha=PTR,action_kind="RECONCILE_FRONTIER",receipt_blobs={"canonical/verification/counter.json":COUNTER}),[])
    def test_stale(self):
        a=base(); a["active_pointer_git_blob_sha"]="f"*40
        self.assertIn("V22_ACTIVE_POINTER_BLOB_STALE_OR_MISMATCH",admission_errors(a,POINTER,pointer_blob_sha=PTR,action_kind="RECONCILE_FRONTIER",receipt_blobs={"canonical/verification/counter.json":COUNTER}))
    def test_off_frontier(self):
        a=base(); a["interface"]="H100_SYNTHETIC_REGISTRY"
        self.assertIn("V22_INTERFACE_NOT_CURRENTLY_ACTIVE",admission_errors(a,POINTER,pointer_blob_sha=PTR,action_kind="RECONCILE_FRONTIER",receipt_blobs={"canonical/verification/counter.json":COUNTER}))
    def test_wake(self):
        a=base(); a.update(mode="DORMANT_WAKE",dormant_work_id="HLE_GRADER_RELATION",wake_receipt_path="canonical/verification/wake.json",wake_receipt_git_blob_sha=WAKE); a.pop("interface")
        self.assertEqual(admission_errors(a,POINTER,pointer_blob_sha=PTR,action_kind="RECONCILE_FRONTIER",receipt_blobs={"canonical/verification/counter.json":COUNTER,"canonical/verification/wake.json":WAKE}),[])
        self.assertIn("V22_WAKE_RECEIPT_BLOB_STALE_OR_MISMATCH",admission_errors(a,POINTER,pointer_blob_sha=PTR,action_kind="RECONCILE_FRONTIER",receipt_blobs={"canonical/verification/counter.json":COUNTER}))
    def test_control_plane(self):
        a=base(); a.update(mode="CONTROL_PLANE_PREREQUISITE",control_plane_gap="V22_SCHEDULER_ENFORCEMENT_GAP",minimum_prerequisite_for=list(POINTER["current_shared_causal_interfaces"])); a.pop("interface")
        self.assertEqual(admission_errors(a,POINTER,pointer_blob_sha=PTR,action_kind="GOVERNANCE_GUARD",receipt_blobs={"canonical/verification/counter.json":COUNTER}),[])
        self.assertIn("V22_CONTROL_PLANE_MODE_REQUIRES_GOVERNANCE_ACTION",admission_errors(a,POINTER,pointer_blob_sha=PTR,action_kind="RECONCILE_FRONTIER",receipt_blobs={"canonical/verification/counter.json":COUNTER}))
    def test_currentness(self):
        a=base(); a["currentness"]["unresolved_atomic"]=23
        self.assertIn("V22_CURRENTNESS_MISMATCH:unresolved_atomic",admission_errors(a,POINTER,pointer_blob_sha=PTR,action_kind="RECONCILE_FRONTIER",receipt_blobs={"canonical/verification/counter.json":COUNTER}))
    def test_tournament_required(self):
        a=base(); a.pop("tournament")
        self.assertIn("V22_TOURNAMENT_BINDING_MISSING",admission_errors(a,POINTER,pointer_blob_sha=PTR,action_kind="RECONCILE_FRONTIER"))
    def test_nonbenchmark_active_interface_is_unchanged(self):
        a=base()
        self.assertEqual(
            admission_errors(
                a,POINTER,pointer_blob_sha=PTR,action_kind="RECONCILE_FRONTIER",
                receipt_blobs={"canonical/verification/counter.json":COUNTER},
            ),
            [],
        )

    def test_benchmark_external_route_requires_information_equivalence_binding(self):
        a=external_benchmark(); a.pop("benchmark_information_equivalence")
        self.assertIn(
            "V22_BENCHMARK_INFORMATION_EQUIVALENCE_MISSING",
            admission_errors(
                a,POINTER,pointer_blob_sha=PTR,action_kind="RECONCILE_FRONTIER",
                receipt_blobs={"canonical/verification/counter.json":COUNTER},
            ),
        )

    def test_provider_wait_cannot_block_critical_path_while_internal_certificate_has_gain(self):
        a=external_benchmark()
        a["benchmark_information_equivalence"]["external_wait_on_critical_path"]=True
        self.assertIn(
            "V22_PROVIDER_WAIT_FORBIDDEN_WHILE_INTERNAL_CERTIFICATE_HAS_INFORMATION_GAIN",
            admission_errors(
                a,POINTER,pointer_blob_sha=PTR,action_kind="RECONCILE_FRONTIER",
                receipt_blobs={"canonical/verification/counter.json":COUNTER},
            ),
        )

    def test_nonblocking_external_witness_is_admitted_when_minimal_and_nondominated(self):
        a=external_benchmark()
        self.assertEqual(
            admission_errors(
                a,POINTER,pointer_blob_sha=PTR,action_kind="RECONCILE_FRONTIER",
                receipt_blobs={"canonical/verification/counter.json":COUNTER},
            ),
            [],
        )

    def test_signup_capable_ui_does_not_prove_self_service_provisioning(self):
        a=external_benchmark()
        info=a["benchmark_information_equivalence"]
        info["self_service_access_claimed"]=True
        info["self_service_provisioning_verified"]=False
        info["existing_authorized_credential_verified"]=False
        self.assertIn(
            "V22_PROVIDER_UI_IS_NOT_SELF_SERVICE_PROVISIONING_EVIDENCE",
            admission_errors(
                a,POINTER,pointer_blob_sha=PTR,action_kind="RECONCILE_FRONTIER",
                receipt_blobs={"canonical/verification/counter.json":COUNTER},
            ),
        )

    def test_verified_self_service_provisioning_requires_content_addressed_receipt(self):
        a=external_benchmark()
        info=a["benchmark_information_equivalence"]
        info["self_service_access_claimed"]=True
        info["self_service_provisioning_verified"]=True
        info["self_service_provisioning_receipt"]={
            "path":"canonical/verification/provider-provision.json",
            "git_blob_sha":PROVISION,
        }
        blobs={
            "canonical/verification/counter.json":COUNTER,
            "canonical/verification/provider-provision.json":PROVISION,
        }
        self.assertEqual(
            admission_errors(a,POINTER,pointer_blob_sha=PTR,action_kind="RECONCILE_FRONTIER",receipt_blobs=blobs),
            [],
        )

    def test_exhausted_internal_certificate_search_requires_bound_receipt(self):
        a=external_benchmark()
        info=a["benchmark_information_equivalence"]
        info["internal_certificate_search_state"]="EXHAUSTED_OR_FALSIFIED"
        info["certificate_exhaustion_receipt"]={
            "path":"canonical/verification/exhaustion.json",
            "git_blob_sha":EXHAUST,
        }
        errors=admission_errors(
            a,POINTER,pointer_blob_sha=PTR,action_kind="RECONCILE_FRONTIER",
            receipt_blobs={"canonical/verification/counter.json":COUNTER},
        )
        self.assertIn("V22_BENCHMARK_CERTIFICATE_EXHAUSTION_RECEIPT_BLOB_STALE_OR_MISMATCH",errors)
        self.assertEqual(
            admission_errors(
                a,POINTER,pointer_blob_sha=PTR,action_kind="RECONCILE_FRONTIER",
                receipt_blobs={
                    "canonical/verification/counter.json":COUNTER,
                    "canonical/verification/exhaustion.json":EXHAUST,
                },
            ),
            [],
        )

    def test_benchmark_target_binding_must_match_actual_obligation(self):
        a=external_benchmark()
        a["benchmark_information_equivalence"]["target_predicates"]=["AUTOMATIONBENCH_GE_40"]
        self.assertIn(
            "V22_BENCHMARK_TARGET_PREDICATE_BINDING_MISMATCH",
            admission_errors(
                a,POINTER,pointer_blob_sha=PTR,action_kind="RECONCILE_FRONTIER",
                receipt_blobs={"canonical/verification/counter.json":COUNTER},
            ),
        )

    def test_receipt_discovery_includes_benchmark_receipts(self):
        a=external_benchmark()
        info=a["benchmark_information_equivalence"]
        info["internal_certificate_search_state"]="EXHAUSTED_OR_FALSIFIED"
        info["certificate_exhaustion_receipt"]={"path":"canonical/verification/exhaustion.json","git_blob_sha":EXHAUST}
        info["self_service_access_claimed"]=True
        info["self_service_provisioning_verified"]=True
        info["self_service_provisioning_receipt"]={"path":"canonical/verification/provider-provision.json","git_blob_sha":PROVISION}
        self.assertEqual(
            referenced_receipt_paths(a),
            [
                "canonical/verification/counter.json",
                "canonical/verification/exhaustion.json",
                "canonical/verification/provider-provision.json",
            ],
        )

if __name__=="__main__": unittest.main(verbosity=2)
