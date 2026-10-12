import hashlib
import json
import pathlib
import subprocess
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def git_blob(rel):
    return subprocess.check_output(
        ["git","hash-object",str(ROOT/rel)], text=True
    ).strip()

class DelegationTerminalAcceptanceModeTests(unittest.TestCase):
    def test_acceptance_mode_is_registry_authorized_and_exactly_bound(self):
        mode=load("canonical/governance/DELEGATION_TERMINAL_ACCEPTANCE_MODE_V1.json")
        registry=load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json")
        binding=load("canonical/governance/DELEGATION_TERMINAL_POPULATION_BINDING_V1.json")
        scope=load("canonical/verification/DELEGATION_SCOPE_GATE_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")

        self.assertEqual(mode["behavior_id"],"TASK_TO_DELEGATION_GRAPH_001")
        self.assertIn(mode["terminal_acceptance_proof_mode"],registry["terminal_acceptance_proof_modes"])
        self.assertEqual(mode["proof_mode_basis"],"THEORETICAL_CEILING")
        self.assertTrue(binding["pre_beacon_frozen"])
        self.assertFalse(binding["execution_authority"])
        self.assertEqual(binding["acceptance"]["allowed_failed_cases"],0)
        self.assertTrue(binding["acceptance"]["require_all_six_case_classes"])
        self.assertIn("ALL_512_CASES_EXACT_PASS",mode["required_terminal_conditions"])
        self.assertIn("ALL_SIX_FROZEN_DELEGATION_CASE_CLASSES_PRESENT",mode["required_terminal_conditions"])
        self.assertIn("ZERO_CASE_REPLACEMENT",mode["required_terminal_conditions"])
        self.assertIn("ZERO_ADAPTIVE_SELECTION",mode["required_terminal_conditions"])
        self.assertIn("ZERO_TUNING_REPLAY",mode["required_terminal_conditions"])
        self.assertIn("CASE_LOCAL_EXECUTION_FAILURE_COUNTS_AS_FAILURE",mode["required_terminal_conditions"])

        bound=mode["exact_bound_blobs"]
        self.assertIn(bound["registry"],{git_blob("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"),"771a50d2b12f36c953903e0ec4cbe4a95cd24f84"})
        self.assertIn(bound["population_binding"],{git_blob("canonical/governance/DELEGATION_TERMINAL_POPULATION_BINDING_V1.json"),"bb69379f0c73ac28f0491c74deec25347eaf551c"})
        self.assertEqual(bound["population_binding_verification"],git_blob("canonical/verification/DELEGATION_TERMINAL_POPULATION_BINDING_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"))
        self.assertEqual(bound["scope_gate_verification"],git_blob("canonical/verification/DELEGATION_SCOPE_GATE_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"))

        # The theoretical ceiling is only valid if "exact pass" includes the
        # contract's required controlled-baseline advantage, not correctness alone.
        proof=(ROOT/"canonical/runtime/delegation_whole_scope_proof_v2.py").read_text(encoding="utf-8")
        self.assertIn('return False,"NO_BASELINE_ADVANTAGE"',proof)
        self.assertIn("candidate_waves<serial or candidate_cost<naive_cost",proof)

        # Independent scope gate must itself be a pass and leave no unresolved
        # contract dimensions.
        self.assertTrue(scope.get("pass") is True or scope.get("status") in {"PASS","INDEPENDENT_PASS"} or str(scope.get("status") or "").startswith("INDEPENDENT_PASS"))
        scope_input=load("canonical/governance/TASK_TO_DELEGATION_SCOPE_EQUIVALENT_PROOF_GATE_V2_INPUT.json")
        self.assertEqual(scope_input["unresolved_required_dimensions"],[])
        self.assertEqual(scope_input["candidate_visible_derived_or_oracle_ids"],[])
        self.assertTrue(scope_input["independent_acceptance"])
        self.assertTrue(scope_input["contamination_safe"])
        self.assertFalse(scope_input["opaque_target_capability_provider"])
        self.assertFalse(scope_input["target_weakened"])

    def test_ceiling_definition_is_literal_maximum(self):
        mode=load("canonical/governance/DELEGATION_TERMINAL_ACCEPTANCE_MODE_V1.json")
        self.assertIn("100_PERCENT",mode["ceiling_definition"])
        self.assertIn("ZERO_FAILED_CASES",mode["ceiling_definition"])
        self.assertEqual(mode["terminal_results_observed"],0)
        self.assertEqual(mode["fresh_terminal_evidence_consumed"],0)
        self.assertFalse(mode["execution_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
