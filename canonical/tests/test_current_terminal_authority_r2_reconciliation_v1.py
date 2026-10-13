from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
TERMINAL = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
MISSION = ROOT / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
REGCAP_ACTIVATION = ROOT / "canonical/governance/R2_REGCAP_CANDIDATE_AMBIGUITY_CONTROL_ACTIVATION_20261009_V1.json"

REAL_OBJECTIVE = (
    "BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_"
    "PROBLEM_SOLVING_SYSTEM_POSSIBLE"
)


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class CurrentTerminalAuthorityR2ReconciliationV1Tests(unittest.TestCase):
    def load(self, path: Path):
        value = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return value

    def scheduler_path(self, r2):
        rel = r2["scheduler_cut"]["path"]
        path = ROOT / rel
        self.assertTrue(path.is_file(), rel)
        return path

    def test_current_terminal_pointer_binds_real_mission_and_checkpoint_role(self):
        terminal = self.load(TERMINAL)
        mission = self.load(MISSION)

        self.assertTrue(
            terminal["schema"].startswith("PROJECT_BRAIN_CURRENT_TERMINAL_AUTHORITY_POINTER_V")
        )
        self.assertGreaterEqual(terminal["pointer_revision"], 93)
        self.assertEqual(terminal["terminal_objective"], REAL_OBJECTIVE)
        self.assertEqual(
            terminal["objective_precedence"]["authoritative_path"],
            "canonical/governance/CURRENT_MISSION_OBJECTIVE.json",
        )
        self.assertEqual(
            terminal["objective_precedence"]["authoritative_git_blob_sha"],
            blob_sha(MISSION),
        )
        self.assertEqual(mission["real_objective"], REAL_OBJECTIVE)
        self.assertEqual(
            mission["opus_5_5_role"],
            "FIRST_FRONTIER_CHECKPOINT_NOT_TERMINAL_OBJECTIVE",
        )
        self.assertEqual(
            terminal["objective_precedence"]["opus_5_5_role"],
            mission["opus_5_5_role"],
        )
        self.assertNotEqual(
            terminal["checkpoint_objective"],
            terminal["terminal_objective"],
        )

    def test_current_terminal_pointer_binds_mutable_current_r2_and_exact_scheduler(self):
        terminal = self.load(TERMINAL)
        r2 = self.load(R2)
        cut_path = self.scheduler_path(r2)
        cut = self.load(cut_path)

        bound = terminal["authoritative_sources"]["current_r2_decision_intelligence"]
        self.assertEqual(
            bound["path"],
            "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
        )
        self.assertNotIn("git_blob_sha", bound)
        self.assertTrue(bound["mutable_pointer_blob_is_not_load_bearing"])
        self.assertEqual(bound["status"], r2["status"])
        self.assertEqual(bound["scheduler_cut"]["path"], r2["scheduler_cut"]["path"])
        self.assertEqual(bound["scheduler_cut"]["git_blob_sha"], blob_sha(cut_path))
        self.assertEqual(r2["scheduler_cut"]["git_blob_sha"], blob_sha(cut_path))
        self.assertEqual(
            terminal["r2_scheduler_precedence"]["current_scheduler_path"],
            r2["scheduler_cut"]["path"],
        )
        self.assertEqual(
            terminal["r2_scheduler_precedence"]["current_scheduler_git_blob_sha"],
            blob_sha(cut_path),
        )
        self.assertEqual(cut["single_live_primitive"]["id"], "ESCAPE_POLICY_ADEQUACY")
        self.assertFalse(cut["single_live_primitive"]["general_mechanism_missing"])

    def test_gdpval_projection_matches_current_r2_dormant_cell(self):
        terminal = self.load(TERMINAL)
        r2 = self.load(R2)
        truth = terminal["live_truth"]
        cell = r2["current_cell_classifications"]["GDPVAL_AA_OWNER_LAYER"]

        self.assertFalse(truth["gdpval_owner_layer_target_relative_route_currently_awake"])
        self.assertEqual(
            truth["gdpval_owner_layer_target_relative_route_state"],
            cell["state"],
        )
        self.assertTrue(cell["state"].startswith("DORMANT_ALTERNATIVE_"))
        self.assertTrue(terminal["r2_scheduler_precedence"]["current_authority_pointer_mutable"])
        self.assertTrue(
            terminal["r2_scheduler_precedence"]["current_authority_pointer_blob_is_not_load_bearing"]
        )
        self.assertNotIn(
            "current_authority_git_blob_sha",
            terminal["r2_scheduler_precedence"],
        )
        self.assertFalse(
            terminal["r2_scheduler_precedence"][
                "historical_root2_scheduler_fields_authoritative_for_current_r2"
            ]
        )
        self.assertFalse(
            truth["historical_root2_scheduler_fields_currently_authoritative"]
        )

    def test_current_r2_scheduler_projection_counts_are_coherent(self):
        terminal = self.load(TERMINAL)
        r2 = self.load(R2)
        precedence = terminal["r2_scheduler_precedence"]
        result = r2["scheduler_result"]

        self.assertEqual(
            precedence["enumerated_active_zero_reality_cell_count"],
            result["active_zero_reality_cell_count"],
        )
        self.assertEqual(
            precedence["enumerated_external_required_sleep_cell_count"],
            result["external_required_sleep_cell_count"],
        )
        self.assertEqual(
            precedence["primary_internal_unsolved_pending_acquisition_or_experiment_cell_count"],
            result["primary_internal_unsolved_pending_acquisition_or_experiment_cell_count"],
        )
        self.assertEqual(
            precedence["dormant_alternative_route_count"],
            result["dormant_alternative_route_cell_count"],
        )
        self.assertEqual(result["task_specific_external_observation_frontier_cell_count"], 1)
        self.assertEqual(
            result["task_specific_external_observation_frontier_cell"],
            "FINANCE_SEMANTIC_ADEQUACY_TAIL",
        )
        self.assertEqual(result["direct_route_count"], 40)
        self.assertEqual(result["bounded_family_count"], 36)
        self.assertFalse(terminal["live_truth"]["opus_5_5_is_global_terminal_objective"])
        self.assertTrue(terminal["live_truth"]["opus_5_5_is_frontier_checkpoint"])
        self.assertFalse(terminal["live_truth"]["current_escape_policy_adequacy_closed"])

    def test_r2_v53_regcap_routing_precedence_and_nonclaims(self):
        terminal = self.load(TERMINAL)
        r2 = self.load(R2)
        activation = self.load(REGCAP_ACTIVATION)

        self.assertIn("__V91__", r2["status"])
        rec = r2["r2_v53_regcap_semantic_routing_reconciliation"]
        self.assertEqual(
            rec["precedence"][:3],
            [
                "EXACT_AUTHENTICATED_SOURCE_BOUND_IDENTITY_WHEN_SOURCE_CONTRACT_MATCHES",
                "EXACT_AUTHENTICATED_LOCAL_APPOSITIVE_IDENTITY_WHEN_SOURCE_SPAN_CONTRACT_MATCHES",
                "VERIFIED_PROPERTY_CANDIDATE_DISCOVERY_PLUS_MINIMUM_INFORMATION_AMBIGUITY_CONTROL",
            ],
        )
        self.assertFalse(rec["finance_semantic_tail_closed"])
        self.assertEqual(rec["primary_internal_unsolved_count_before"], 1)
        self.assertEqual(rec["primary_internal_unsolved_count_after"], 1)
        self.assertFalse(
            r2["regcap_loss_cushion_source_bound_identity"]["global_phrase_identity_authority"]
        )
        self.assertFalse(
            r2["regcap_local_appositive_identity"]["global_alias_authority"]
        )
        self.assertFalse(
            r2["regcap_candidate_ambiguity_minimum_information_control"][
                "external_impossibility_claimed"
            ]
        )
        self.assertEqual(
            r2["regcap_candidate_ambiguity_minimum_information_control"][
                "activation_git_blob_sha"
            ],
            blob_sha(REGCAP_ACTIVATION),
        )
        self.assertEqual(
            activation["r2_truth_delta"]["primary_internal_unsolved_count_delta"],
            0,
        )

        truth = terminal["live_truth"]
        self.assertTrue(truth["r2_regcap_nyfed_loss_cushion_ccob_identity_bound"])
        self.assertTrue(truth["r2_regcap_local_appositive_identity_bound"])
        self.assertTrue(truth["r2_regcap_candidate_ambiguity_minimum_information_control_bound"])
        self.assertFalse(truth["r2_regcap_global_loss_cushion_identity_closed"])
        self.assertFalse(truth["r2_regcap_open_world_ontology_closed"])
        self.assertFalse(truth["r2_regcap_missing_context_is_external_impossibility"])
        self.assertEqual(truth["r2_primary_internal_unsolved_count"], 0)
        self.assertIsNone(truth["r2_primary_internal_unsolved_cell"])
        self.assertEqual(
            truth["r2_task_specific_external_observation_frontier"],
            "FINANCE_SEMANTIC_ADEQUACY_TAIL",
        )
        self.assertIn(
            "__V91__",
            terminal["authoritative_sources"]["current_r2_decision_intelligence"]["status"],
        )
        self.assertIn("TERMINAL_FALSE", terminal["status"])
        self.assertEqual(
            terminal["r2_v53_regcap_semantic_routing_reconciliation_20261009_v1"][
                "terminal_credit_delta"
            ],
            0,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
