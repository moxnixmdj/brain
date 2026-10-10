from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
TERMINAL = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
TB = ROOT / "canonical/governance/CURRENT_TB_SCIENCE_EXECUTION.json"

class TerminalTBScienceCurrentnessTests(unittest.TestCase):
    def test_terminal_authority_uses_mutable_tb_science_path_currentness(self):
        terminal = json.loads(TERMINAL.read_text(encoding="utf-8"))
        live = terminal["tb_science_dynamic_currentness"]
        self.assertEqual(
            live["path"],
            "canonical/governance/CURRENT_TB_SCIENCE_EXECUTION.json",
        )
        self.assertEqual(
            live["binding"],
            "MUTABLE_CURRENT_POINTER_PATH_IDENTITY__LIVE_INVARIANTS_RECHECKED",
        )
        self.assertFalse(live["activation_observed_blob_is_load_bearing"])
        self.assertEqual(
            live["historical_tb_science_snapshots"],
            "PROVENANCE_ONLY__NOT_CURRENTNESS_AUTHORITY",
        )
        self.assertIn(
            "HISTORICAL_TB_SCIENCE_CURRENTNESS_SUPERSEDED",
            terminal["status"],
        )
        self.assertNotIn(
            "RANK19_EXECUTION_FROZEN_PENDING_ZERO_EXPOSURE_PLANNER_REPAIR",
            terminal["status"],
        )

    def test_current_tb_science_zero_credit_invariants_are_rechecked_live(self):
        terminal = json.loads(TERMINAL.read_text(encoding="utf-8"))
        tb = json.loads(TB.read_text(encoding="utf-8"))
        required = terminal["tb_science_dynamic_currentness"]["required_current_invariants"]
        self.assertEqual(tb["terminal_credit_delta"], required["terminal_credit_delta"])
        self.assertEqual(tb["acceptance_credit_delta"], required["acceptance_credit_delta"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
