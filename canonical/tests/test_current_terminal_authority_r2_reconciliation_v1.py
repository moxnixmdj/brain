from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
TERMINAL = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
MISSION = ROOT / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
CUT = ROOT / "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261008_V5.json"

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

    def test_current_terminal_pointer_binds_real_mission_and_checkpoint_role(self):
        terminal = self.load(TERMINAL)
        mission = self.load(MISSION)

        self.assertEqual(
            terminal["schema"],
            "PROJECT_BRAIN_CURRENT_TERMINAL_AUTHORITY_POINTER_V34",
        )
        self.assertEqual(terminal["pointer_revision"], 35)
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

    def test_current_terminal_pointer_binds_current_r2_and_v5_scheduler(self):
        terminal = self.load(TERMINAL)
        r2 = self.load(R2)
        cut = self.load(CUT)

        bound = terminal["authoritative_sources"]["current_r2_decision_intelligence"]
        self.assertEqual(
            bound["path"],
            "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
        )
        self.assertEqual(bound["git_blob_sha"], blob_sha(R2))
        self.assertEqual(
            bound["scheduler_cut"]["path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261008_V5.json",
        )
        self.assertEqual(bound["scheduler_cut"]["git_blob_sha"], blob_sha(CUT))
        self.assertEqual(r2["scheduler_cut"]["git_blob_sha"], blob_sha(CUT))
        self.assertEqual(
            cut["single_live_primitive"]["id"],
            "ESCAPE_POLICY_ADEQUACY",
        )
        self.assertFalse(cut["single_live_primitive"]["general_mechanism_missing"])

    def test_gdpval_owner_layer_is_sleeping_not_awake(self):
        terminal = self.load(TERMINAL)
        cut = self.load(CUT)
        truth = terminal["live_truth"]
        self.assertIs(
            truth["gdpval_owner_layer_target_relative_route_currently_awake"],
            False,
        )
        self.assertEqual(
            truth["gdpval_owner_layer_target_relative_route_state"],
            "EXTERNAL_REQUIRED_SLEEP",
        )
        self.assertEqual(
            cut["current_cell_classifications"]["GDPVAL_AA_OWNER_LAYER"]["state"],
            "EXTERNAL_REQUIRED_SLEEP",
        )
        self.assertFalse(
            terminal["r2_scheduler_precedence"][
                "historical_root2_scheduler_fields_authoritative_for_current_r2"
            ]
        )
        self.assertFalse(
            truth["historical_root2_scheduler_fields_currently_authoritative"]
        )

    def test_current_r2_scheduler_counts_and_terminal_nonclaim_match(self):
        terminal = self.load(TERMINAL)
        cut = self.load(CUT)
        precedence = terminal["r2_scheduler_precedence"]
        result = cut["scheduler_result"]
        self.assertEqual(
            precedence["enumerated_active_zero_reality_cell_count"],
            result["active_zero_reality_cell_count"],
        )
        self.assertEqual(
            precedence["enumerated_external_required_sleep_cell_count"],
            result["external_required_sleep_cell_count"],
        )
        self.assertFalse(terminal["live_truth"]["opus_5_5_is_global_terminal_objective"])
        self.assertTrue(terminal["live_truth"]["opus_5_5_is_frontier_checkpoint"])
        self.assertFalse(terminal["live_truth"]["current_escape_policy_adequacy_closed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
