import json
import unittest
from pathlib import Path

from canonical.runtime.scope_equivalent_proof_gate_v2 import evaluate

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "canonical/governance/SA_CCR_SCOPE_EQUIVALENT_PROOF_GATE_V2_INPUT.json"
ROUTE = ROOT / "canonical/governance/SA_CCR_INFORMATION_SAFE_TERMINAL_ROUTE_V1.json"
SCOPE = ROOT / "canonical/governance/SA_CCR_ACTIVE_CONTRACT_SCOPE_CLOSURE_V1.json"
RECEIPT = ROOT / "canonical/verification/SA_CCR_INFORMATION_SAFE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class SaccrScopeEquivalentGateV2Tests(unittest.TestCase):
    def setUp(self):
        self.gate = load(GATE)
        self.route = load(ROUTE)
        self.scope = load(SCOPE)
        self.receipt = load(RECEIPT)

    def test_declared_behavior_matches_hidden_oracle(self):
        required = set(self.gate["required_behavior_ids"])
        self.assertEqual(required, set(self.route["information_boundary"]["hidden_oracle"]))
        self.assertEqual(required, set(self.gate["candidate_behavior_ids"]))
        self.assertEqual(required, set(self.gate["required_inference_ids"]))
        self.assertEqual(required, set(self.gate["hidden_oracle_ids"]))

    def test_declared_interactions_match_population_scope(self):
        required = set(self.gate["required_interaction_ids"])
        self.assertEqual(required, set(self.route["population"]["covers"]))
        self.assertEqual(required, set(self.gate["candidate_interaction_ids"]))

    def test_scope_closure_excludes_out_of_contract_surfaces(self):
        deduction = self.scope["contract_schema_deduction"]
        self.assertIn("WHOLE_NETTING_SET_RC", deduction["excluded_absent_outputs"])
        self.assertIn("EAD", deduction["excluded_absent_outputs"])
        self.assertIn("RWA", deduction["excluded_absent_outputs"])
        self.assertIn("OPTION_STYLE_STRIKE_UNDERLYING_PRICE_VOLATILITY_OR_OPTION_DELTA_INPUTS", deduction["excluded_absent_inputs"])
        self.assertIn("CDO_TRANCHE_ATTACHMENT_DETACHMENT_OR_TRANCHE_DELTA_INPUTS", deduction["excluded_absent_inputs"])

    def test_information_boundary_and_independence_are_bound(self):
        self.assertFalse(self.route["information_boundary"]["candidate_receives_reference_solution"])
        self.assertFalse(self.route["information_boundary"]["candidate_receives_hidden_oracle"])
        self.assertTrue(self.route["oracle"]["independent_implementation"])
        self.assertTrue(self.route["oracle"]["checks_every_intermediate_and_final_credit_addon"])
        self.assertTrue(self.receipt["status"].startswith("INDEPENDENT_PREWAVE_PASS"))
        self.assertEqual(self.receipt["workflow_conclusion"], "success")

    def test_gate_v2_admits_scope_substitution(self):
        out = evaluate(self.gate)
        self.assertTrue(out["admissible"], out)
        self.assertEqual(out["errors"], [])
        self.assertEqual(out["status"], "ADMISSIBLE_SUBSTITUTION")

    def test_terminal_credit_remains_blocked(self):
        self.assertFalse(self.gate["terminal_result_observed"])
        self.assertEqual(self.gate["capability_credit_delta"], 0)
        self.assertEqual(self.gate["family_credit_delta"], 0)
        self.assertIn("POST_FREEZE_TERMINAL_POPULATION_BINDING", self.route["remaining_before_terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
