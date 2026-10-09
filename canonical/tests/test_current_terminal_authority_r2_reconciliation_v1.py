from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
TERMINAL = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
MISSION = ROOT / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
CUT = ROOT / "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V52.json"
ACTIVATION = ROOT / "canonical/governance/R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_ACTIVATION_20261009_V28.json"
DISPATCHER = ROOT / "canonical/runtime/r2_direct_route_registry_v1.py"
FIXED_POINT = ROOT / "canonical/runtime/general_adequate_decision_fixed_point_v2.py"

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
            "PROJECT_BRAIN_CURRENT_TERMINAL_AUTHORITY_POINTER_V37",
        )
        self.assertEqual(terminal["pointer_revision"], 91)
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
        self.assertNotEqual(
            terminal["checkpoint_objective"],
            terminal["terminal_objective"],
        )

    def test_current_terminal_pointer_binds_current_r2_and_v52_scheduler(self):
        terminal = self.load(TERMINAL)
        r2 = self.load(R2)
        cut = self.load(CUT)
        bound = terminal["authoritative_sources"]["current_r2_decision_intelligence"]
        self.assertEqual(
            bound["path"],
            "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
        )
        self.assertNotIn("git_blob_sha", bound)
        self.assertTrue(bound["mutable_pointer_blob_is_not_load_bearing"])
        self.assertEqual(
            bound["scheduler_cut"]["path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V52.json",
        )
        self.assertEqual(bound["scheduler_cut"]["git_blob_sha"], blob_sha(CUT))
        self.assertEqual(r2["scheduler_cut"]["git_blob_sha"], blob_sha(CUT))
        self.assertEqual(
            cut["single_live_primitive"]["id"],
            "ESCAPE_POLICY_ADEQUACY",
        )
        self.assertFalse(cut["single_live_primitive"]["general_mechanism_missing"])

    def test_current_r2_default_runtime_projection_is_exactly_37_routes(self):
        terminal = self.load(TERMINAL)
        r2 = self.load(R2)
        direct = r2["direct_adequacy"]
        self.assertEqual(direct["current_route_count"], 37)
        self.assertEqual(direct["exact_cell_count"], 3)
        self.assertEqual(direct["bounded_family_count"], 34)
        self.assertEqual(
            direct["activation_path"],
            "canonical/governance/R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_ACTIVATION_20261009_V28.json",
        )
        self.assertEqual(direct["activation_git_blob_sha"], blob_sha(ACTIVATION))
        self.assertEqual(
            direct["direct_runtime_path"],
            "canonical/runtime/r2_direct_route_registry_v1.py",
        )
        self.assertEqual(direct["direct_runtime_git_blob_sha"], blob_sha(DISPATCHER))
        self.assertEqual(
            r2["controller"]["fixed_point_git_blob_sha"],
            blob_sha(FIXED_POINT),
        )
        truth = terminal["live_truth"]
        self.assertEqual(truth["r2_direct_adequacy_route_count"], 37)
        self.assertEqual(truth["r2_direct_adequacy_exact_cell_count"], 3)
        self.assertEqual(truth["r2_direct_adequacy_bounded_family_count"], 34)
        rec = terminal["r2_v53_default_runtime_stable_dispatch_reconciliation"]
        self.assertEqual(rec["route_count"], 37)
        self.assertEqual(rec["bounded_family_count"], 34)
        self.assertEqual(rec["direct_runtime_git_blob_sha"], blob_sha(DISPATCHER))
        self.assertEqual(rec["fixed_point_controller_git_blob_sha"], blob_sha(FIXED_POINT))
        self.assertFalse(rec["terminal_remains_false"] is False)

    def test_scheduler_counts_and_terminal_nonclaims_match(self):
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
        self.assertEqual(result["direct_route_count"], 37)
        self.assertEqual(result["bounded_family_count"], 34)
        self.assertEqual(
            terminal["live_truth"]["current_r2_scheduler_cut"],
            "ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V52",
        )
        self.assertFalse(terminal["live_truth"]["opus_5_5_is_global_terminal_objective"])
        self.assertTrue(terminal["live_truth"]["opus_5_5_is_frontier_checkpoint"])
        self.assertFalse(
            terminal["r2_v53_default_runtime_stable_dispatch_reconciliation"][
                "terminal_credit_delta"
            ]
            != 0
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
