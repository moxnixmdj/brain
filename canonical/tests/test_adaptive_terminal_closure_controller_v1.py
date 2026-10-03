from __future__ import annotations

import copy
import importlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "canonical/runtime/adaptive_terminal_closure_controller_v1.py"


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def live_docs():
    return [
        load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
        load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
        load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
        load("canonical/governance/CURRENT_27_INFORMATION_DOMINANCE_V1.json"),
        load("canonical/verification/CURRENT_27_INFORMATION_DOMINANCE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"),
        load("canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json"),
        load("canonical/verification/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_EXECUTION_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json"),
        load("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"),
        load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
    ]


class AdaptiveTerminalClosureControllerV1Tests(unittest.TestCase):
    def test_controller_module_exists(self):
        self.assertTrue(MODULE_PATH.exists(), "adaptive controller runtime is missing")

    def _module(self):
        self.assertTrue(MODULE_PATH.exists(), "adaptive controller runtime is missing")
        return importlib.import_module("canonical.runtime.adaptive_terminal_closure_controller_v1")

    def test_live_frontier_compiles_exact_refinement(self):
        m = self._module()
        out = m.evaluate_repository(ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["live_world"]["unresolved_predicates"], 27)
        self.assertEqual(out["live_world"]["nondominated_certificates"], 16)
        self.assertEqual(out["live_world"]["verified_zero_reality_requirements"], 19)
        self.assertEqual(out["live_world"]["matched_live_targets"], 8)
        self.assertEqual(out["live_world"]["matched_primitive_child_facts"], 16)
        self.assertEqual(out["live_world"]["matched_shared_residual_groups"], 0)
        self.assertEqual(out["action_refinement"]["direct_nonmatched_work_units"], 17)
        self.assertEqual(out["action_refinement"]["primitive_acceptance_work_units"], 33)
        self.assertEqual(len(out["first_resource_priority_work_unit_ids"]), 16)

    def test_matched_parent_flags_are_not_actionable_substitutes(self):
        m = self._module()
        out = m.evaluate_repository(ROOT)
        ids = {x["work_unit_id"] for x in out["acceptance_work_units"]}
        self.assertNotIn("MATCHED_BRAIN_WITNESS_TARGET_ATOM_METRIC_BINDINGS_INDEPENDENT_PASS", ids)
        self.assertNotIn("MATCHED_BRAIN_WITNESS_SCOPE_RELATIONS_INDEPENDENT_PASS", ids)
        matched = [x for x in out["acceptance_work_units"] if x["lane"] == "MATCHED_TARGET_PROOF"]
        self.assertEqual(len(matched), 16)
        self.assertTrue(all(len(x["target_predicates"]) == 1 for x in matched))
        self.assertTrue(all(x["first_resource_priority"] is True for x in matched))

    def test_already_accepted_unowned_families_get_parallel_ownership_reconciliation(self):
        m = self._module()
        out = m.evaluate_repository(ROOT)
        families = {x["family"] for x in out["ownership_reconciliation_work_units"]}
        self.assertEqual(
            families,
            {"SUBAGENT_DELEGATION_AND_COORDINATION", "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"},
        )

    def test_unknown_probability_is_not_invented(self):
        m = self._module()
        out = m.evaluate_repository(ROOT)
        self.assertEqual(out["probability_policy"]["empirically_scored_work_unit_count"], 0)
        self.assertTrue(all(x["empirical_posterior"] is None for x in out["acceptance_work_units"]))
        self.assertFalse(out["probability_policy"]["unknown_success_probability_may_be_invented"])

    def test_empirical_history_enables_scheduling_posterior_but_never_promotion(self):
        m = self._module()
        docs = live_docs()
        probe = m.evaluate(*docs)
        unit_id = probe["acceptance_work_units"][0]["work_unit_id"]
        out = m.evaluate(
            *docs,
            attempt_history={
                unit_id: {
                    "verified_successes": 3,
                    "verified_failures": 1,
                    "total_wall_seconds": 40,
                }
            },
        )
        row = next(x for x in out["acceptance_work_units"] if x["work_unit_id"] == unit_id)
        posterior = row["empirical_posterior"]
        self.assertEqual((posterior["alpha"], posterior["beta"]), (4, 2))
        self.assertAlmostEqual(posterior["posterior_mean_verified_discharge_probability"], 4 / 6)
        self.assertEqual(posterior["mean_wall_seconds"], 10.0)
        self.assertTrue(posterior["promotion_use_forbidden"])
        self.assertFalse(out["promotion_authority"])

    def test_tool_discovery_is_mechanically_kept_behind_v2_gate(self):
        m = self._module()
        out = m.evaluate_repository(ROOT)
        rows = [
            x for x in out["acceptance_work_units"]
            if "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR" in x["target_predicates"]
        ]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertTrue(row["mandatory_tool_discovery_v2_gate"])
        self.assertEqual(row["source_hints"][0], "MANDATORY_TOOL_DISCOVERY_V2_RETRIEVAL_GATE")
        self.assertIn("NEW_ORTHOGONAL_SOURCE_EPOCH_ONLY", row["source_hints"])

    def test_verified_frontier_count_mutation_fails_closed(self):
        m = self._module()
        docs = copy.deepcopy(live_docs())
        docs[4]["verified"]["unique_zero_reality_requirements"] = 18
        out = m.evaluate(*docs)
        self.assertFalse(out["pass"])
        self.assertIn("DOMINANCE_VERIFIED_COUNTS_MISMATCH", out["errors"])

    def test_recomputed_future_world_requires_no_controller_code_change(self):
        m = self._module()
        docs = copy.deepcopy(live_docs())
        pid = "COMPOSITION_COMPONENT_SCOPED_PROOFS"
        claim = next(x for x in docs[1]["claims"] if x.get("predicate_id") == pid)
        claim["state"] = "PROVED"
        claim["scope_complete"] = True
        docs[3]["live_world"]["proved_predicates"] = 12
        docs[3]["live_world"]["unresolved_predicates"] = 26
        docs[4]["verified"]["proved_predicates"] = 12
        docs[4]["verified"]["unresolved_predicates"] = 26
        out = m.evaluate(*docs)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["live_world"]["proved_predicates"], 12)
        self.assertEqual(out["live_world"]["unresolved_predicates"], 26)

    def test_controller_never_grants_credit_or_reality_authority(self):
        m = self._module()
        out = m.evaluate_repository(ROOT)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["fresh_reality_authority"])
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertEqual(out["ownership_credit_delta"], 0)
        self.assertEqual(out["incremental_spend_usd"], 0)
        self.assertEqual(out["new_reality_units_consumed"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
