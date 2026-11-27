from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "canonical/governance/MYSTERYMECHANISM_PROPOSITION_FIRST_MINIMUM_PROOF_FRONTIER_20261011_V1.json"


class MysteryMechanismPropositionFirstFrontierV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(PATH.read_text(encoding="utf-8"))

    def test_b_c_o_are_separate_and_typed(self):
        p = self.doc["propositions"]
        self.assertEqual(p["B"]["type"], "EXACT_BENCHMARK_STATISTIC")
        self.assertEqual(p["C"]["type"], "CAPABILITY_RELATION")
        self.assertEqual(p["O"]["type"], "OWNERSHIP_PREDICATE")
        self.assertEqual(len({p["B"]["id"], p["C"]["id"], p["O"]["id"]}), 3)

    def test_branded_receipt_is_wake_gated_not_c_critical_path(self):
        b = self.doc["propositions"]["B"]
        self.assertIn("WAKE_GATED", b["scheduler_state"])
        self.assertFalse(b["critical_for_C"])
        self.assertFalse(self.doc["scheduler_decision"]["vals_authorization_on_current_C_critical_path"])

    def test_selected_next_action_is_immediate_scope_entailment_work(self):
        decision = self.doc["scheduler_decision"]
        self.assertEqual(decision["selected_route"], "PROVE_OR_FALSIFY_SCOPE_BOUND_CAPABILITY_ENTAILMENT")
        route = next(r for r in self.doc["route_frontier"] if r["id"] == decision["selected_route"])
        self.assertTrue(route["runnable_now"])
        self.assertFalse(route["waits_for_external_event"])
        self.assertEqual(route["incremental_spend_usd"], 0)
        self.assertEqual(route["external_runtime_cognition"], 0)
        self.assertFalse(route["reconstructs_private_answers_or_hidden_task_identity"])

    def test_v4_is_capability_asset_not_score_receipt(self):
        a = self.doc["brain_capability_asset"]
        self.assertEqual(a["runtime_v4"], "canonical/runtime/mysterymechanism_adaptive_planner_v4.py")
        self.assertEqual(a["tests_v4"], "canonical/tests/test_mysterymechanism_adaptive_planner_v4.py")
        self.assertEqual(a["benchmark_credit"], 0)
        self.assertEqual(a["external_runtime_cognition"], 0)

    def test_same_information_retry_is_rejected(self):
        route = next(r for r in self.doc["route_frontier"] if r["id"] == "REPEAT_UNCHANGED_PUBLIC_SCOPE_SEARCH")
        self.assertEqual(route["state"], "REJECTED")
        self.assertFalse(route["runnable_now"])
        self.assertFalse(self.doc["scheduler_decision"]["same_information_public_search_retry_authorized"])

    def test_custom_eval_equivalence_is_not_assumed(self):
        nonclaims = set(self.doc["hard_nonclaims"])
        self.assertIn(
            "NO_CLAIM_A_LOCALLY_GENERATED_HIDDEN_OR_ADVERSARIAL_EVALUATION_IS_EQUIVALENT_WITHOUT_A_PROVED_SCOPE_RELATION",
            nonclaims,
        )
        self.assertIn("NO_CLAIM_BRAIN_CURRENTLY_SCORES_109_OF_222_OR_HIGHER", nonclaims)

    def test_zero_credit_and_zero_spend(self):
        a = self.doc["accounting"]
        self.assertEqual(a["incremental_spend_usd"], 0)
        self.assertEqual(a["private_mysterymechanism_cases_consumed"], 0)
        for key in (
            "benchmark_score_credit_delta",
            "capability_credit_delta",
            "ownership_credit_delta",
            "terminal_credit_delta",
        ):
            self.assertEqual(a[key], 0)

    def test_v2_measurement_law_is_authority(self):
        self.assertEqual(
            self.doc["authority"]["measurement_law"],
            "canonical/laws/BENCHMARK_MEASUREMENT_VS_CAPABILITY_PROOF_LAW_V2.md",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
