from __future__ import annotations
import json, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

class StructuredMethodTerminalBindingTests(unittest.TestCase):
    def setUp(self):
        self.input=load("canonical/governance/STRUCTURED_METHOD_SCOPE_EQUIVALENT_PROOF_GATE_V2_INPUT.json")
        self.verdict=load("canonical/governance/STRUCTURED_METHOD_SCOPE_EQUIVALENT_PROOF_GATE_V2_VERDICT.json")
        self.binding=load("canonical/governance/STRUCTURED_METHOD_TERMINAL_BINDING_V1.json")

    def test_gate_verdict_is_exactly_admissible_for_frozen_input(self):
        self.assertTrue(self.verdict["admissible"])
        self.assertEqual(self.verdict["errors"],[])
        self.assertEqual(self.verdict["proof_mode"],self.input["proof_mode"])
        self.assertEqual(self.verdict["required_interaction_count"],len(self.input["required_interaction_ids"]))
        self.assertEqual(self.verdict["covered_interaction_count"],len(self.input["candidate_interaction_ids"]))
        self.assertEqual(self.verdict["required_inference_ids"],self.input["required_inference_ids"])

    def test_binding_preserves_scope_and_hidden_oracle_boundary(self):
        pop=self.binding["frozen_population"]
        self.assertEqual(pop["interaction_ids"],self.input["required_interaction_ids"])
        self.assertEqual(pop["inference_ids"],self.input["required_inference_ids"])
        self.assertEqual(pop["anti_shortcut_mutations"],self.input["anti_shortcut_mutation_ids"])
        self.assertEqual(pop["hidden_oracle_ids"],self.input["hidden_oracle_ids"])
        self.assertEqual(pop["candidate_visible_derived_or_oracle_ids"],[])
        self.assertIs(self.binding["information_boundary"]["reference_solution_visible"],False)
        self.assertIs(self.binding["information_boundary"]["hidden_oracle_visible"],False)

    def test_verification_receipts_exist(self):
        for rel in self.binding["verification"]:
            self.assertTrue((ROOT/rel).is_file(),rel)
        for rel in self.binding["candidate"].values():
            self.assertTrue((ROOT/rel).is_file(),rel)

    def test_fail_closed_acceptance_is_frozen(self):
        a=self.binding["acceptance"]
        for key in (
            "all_required_interactions_present",
            "zero_unresolved_required_dimensions",
            "zero_load_bearing_oracle_leak",
            "all_declared_type_dimension_lineage_invariant_and_required_output_mutations_detected",
            "cycle_or_unresolved_dependency_fails_closed",
            "candidate_must_not_receive_reference_solution",
            "candidate_must_not_receive_hidden_oracle_payload",
            "any_case_failure_blocks_route",
            "scorer_or_population_mutation_after_freeze_forbidden",
        ):
            self.assertIs(a[key],True)

    def test_no_terminal_credit_or_authority(self):
        self.assertEqual(self.binding["terminal_results_observed"],0)
        self.assertEqual(self.binding["fresh_terminal_evidence_consumed"],0)
        self.assertIs(self.binding["execution_authority"],False)
        self.assertEqual(self.binding["capability_credit_delta"],0)
        self.assertEqual(self.binding["family_credit_delta"],0)

if __name__=="__main__":
    unittest.main()
