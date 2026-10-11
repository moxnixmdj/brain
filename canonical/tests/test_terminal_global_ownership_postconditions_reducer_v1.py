from __future__ import annotations
import unittest
from canonical.runtime.terminal_global_ownership_postconditions_reducer_v1 import evaluate_documents, TERMINAL_SHA

class OwnershipPostconditionsTests(unittest.TestCase):
    def fixture(self):
        terminal={
            "status":"ONE_SHOT_TERMINAL_WAVE_PASS__IMMUTABLE_PUBLIC_RUNNER_RECEIPT__NO_REPLAY_AUTHORIZED",
            "terminal_results_observed":1,
            "fresh_terminal_evidence_consumed":3352,
            "artifact":{"full_result_sha256":TERMINAL_SHA},
            "direct_terminal_population":{"total_cases":2770,"total_passes":2770,"total_failures":0},
            "parent_terminal_population":{"parent_reduction_status":"PASS","multiplex_behavior_failures":0},
            "result_guards":{"no_case_replacement":True,"no_tuning_replay":True,"result_to_runtime_feedback_during_wave":False},
        }
        reduction={
            "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__12_OF_12_TERMINAL_CONTRACTS_PASS__19_OF_19_PROVISIONAL_FAMILY_ROWS_PASS__GLOBAL_OWNERSHIP_POSTCONDITIONS_REMAIN",
            "source_full_result_sha256":TERMINAL_SHA,
            "contract_verdict":{"valid":True,"contract_count":12,"contract_pass_count":12,"failed_contracts":[]},
            "family_verdict":{"valid":True,"family_count":19,"family_pass_count":19,"failed_families":[]},
        }
        dependency={
            "prewave_conclusion":{"exact_runtime_dependencies_frozen":True,"no_known_opaque_target_capability_provider":True,"known_dependency_identity_complete_for_declared_operative_route":True},
            "dependency_policy":{"paid_or_hosted_target_capability_provider":"FORBIDDEN","opaque_external_target_capability_provider":"NONE_DECLARED_IN_OPERATIVE_ROUTE"},
        }
        cleanliness={"prewave_predicates":{
            "brain_route_and_dependency_manifest_frozen":True,
            "no_known_opaque_target_capability_provider_in_operative_brain_route":True,
            "no_known_unresolved_controller_composition_defect_before_wave":True,
        }}
        composition={"status":"INDEPENDENT_PASS","conclusions":["CURRENT_CONTROLLER_COMPOSITION_REGRESSION_SUITE_PASSES_ON_INDEPENDENT_PUBLIC_RUNNER"]}
        mutation={"status":"INDEPENDENT_PASS","verified_property":"KNOWN_GOOD_ACCEPTED_AND_EVERY_PREDECLARED_SYNTHETIC_MUTATION_REJECTED"}
        donor={
            "status":"INDEPENDENT_PUBLIC_RUNNER_PASS__DONOR_DENIED_IDENTICAL_FROZEN_QUALIFICATION__BEHAVIOR_PRESERVED",
            "behavior_preserved":True,"byte_identical_terminal_result":True,"undeclared_dependency_count":0,
            "donor_deletion_protocol":"canonical/governance/DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_V2.json",
            "external_contribution_census_complete":True,
            "full_runtime_dependency_inventory_complete":True,
            "runtime_cognition_dependency_class":"MODEL_INDEPENDENT",
            "model_dependency_count":0,
            "external_model_runtime_dependency_count":0,
            "online_teacher_call_count":0,
            "teacher_fallback_path_count":0,
            "copied_or_rehosted_teacher_present":False,
            "brain_owned_operative_artifact":True,
            "operative_solver_role":"BRAIN_OWNED_NATIVE_MECHANISM",
            "predeletion_result":{"full_result_sha256":TERMINAL_SHA},
            "postdeletion_result":{"full_result_sha256":TERMINAL_SHA},
        }
        closure={
            "verified_closed_family_count":19,"open_family_count":0,
            "counters":{"uncontracted_required_behaviors":0,"unproved_required_behaviors":0,"contaminated_promotion_evidence":0,"resource_or_authority_violations":0},
            "terminal_predicates":{"all_frozen_opus_acceptance_predicates_pass":True},
        }
        return terminal,reduction,dependency,cleanliness,composition,mutation,donor,closure

    def test_pass(self):
        out=evaluate_documents(*self.fixture())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["counters"]["donor_dependent_required_behaviors"],0)
        self.assertEqual(out["counters"]["unresolved_verifier_mutations"],0)
        self.assertEqual(out["counters"]["unresolved_composition_failures"],0)

    def test_donor_result_drift_fails_closed(self):
        args=list(self.fixture())
        args[6]["postdeletion_result"]["full_result_sha256"]="bad"
        out=evaluate_documents(*args)
        self.assertFalse(out["pass"])
        self.assertIn("DONOR_CLEANROOM_RESULT_SHA_MISMATCH",out["errors"])

    def test_unresolved_composition_preflight_fails_closed(self):
        args=list(self.fixture())
        args[4]["conclusions"]=[]
        out=evaluate_documents(*args)
        self.assertFalse(out["pass"])
        self.assertIn("CONTROLLER_COMPOSITION_NOT_CURRENT_PASS",out["errors"])

    def test_mutation_preflight_missing_fails_closed(self):
        args=list(self.fixture())
        args[5]["verified_property"]="KNOWN_GOOD_ACCEPTED"
        out=evaluate_documents(*args)
        self.assertFalse(out["pass"])
        self.assertIn("VERIFIER_MUTATION_PREFLIGHT_INCOMPLETE",out["errors"])

    def test_legacy_offline_only_donor_receipt_no_longer_closes_ownership(self):
        args=list(self.fixture())
        donor=args[6]
        for key in (
            "donor_deletion_protocol","external_contribution_census_complete",
            "full_runtime_dependency_inventory_complete","runtime_cognition_dependency_class",
            "model_dependency_count","external_model_runtime_dependency_count",
            "online_teacher_call_count","teacher_fallback_path_count",
            "copied_or_rehosted_teacher_present","brain_owned_operative_artifact",
            "operative_solver_role",
        ):
            donor.pop(key,None)
        out=evaluate_documents(*args)
        self.assertFalse(out["pass"])
        self.assertIn("DONOR_CLEANROOM_PROTOCOL_V2_NOT_BOUND",out["errors"])
        self.assertIn("DONOR_CLEANROOM_RUNTIME_DEPENDENCY_INVENTORY_INCOMPLETE",out["errors"])

    def test_local_rehosted_teacher_donor_receipt_fails(self):
        args=list(self.fixture())
        donor=args[6]
        donor["model_dependency_count"]=1
        donor["external_model_runtime_dependency_count"]=1
        donor["runtime_cognition_dependency_class"]="MODEL_DEPENDENT"
        donor["copied_or_rehosted_teacher_present"]=True
        out=evaluate_documents(*args)
        self.assertFalse(out["pass"])
        self.assertIn("DONOR_CLEANROOM_MODEL_DEPENDENCY_COUNT_NOT_ZERO",out["errors"])
        self.assertIn("DONOR_CLEANROOM_COPIED_OR_REHOSTED_TEACHER_NOT_EXPLICITLY_FALSE",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
