from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
TA = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
RUNTIME = ROOT / "canonical/runtime/loss_absorbing_cushion_regcap_grounding_v7.py"
TESTS = ROOT / "canonical/tests/test_loss_absorbing_cushion_regcap_grounding_v7.py"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


class Tests(unittest.TestCase):
    def test_r2_v80_binds_exact_v7_runtime_and_keeps_scope_narrow(self):
        r2 = load(R2)
        cap = r2["loss_cushion_all_pairs_mrel_context_lift"]
        self.assertIn("__V80__", r2["status"])
        self.assertEqual(cap["runtime_git_blob_sha"], blob(RUNTIME))
        self.assertEqual(cap["tests_git_blob_sha"], blob(TESTS))
        self.assertEqual(
            cap["bound_inventory"],
            ["REGCAP::CCOB", "REGCAP::CCYB", "REGCAP::TLAC", "REGCAP::MREL"],
        )
        self.assertEqual(
            cap["exact_pair_scopes"],
            ["CCOB_MREL", "CCYB_MREL", "TLAC_MREL"],
        )
        self.assertTrue(cap["relative_selection_only"])
        self.assertFalse(cap["global_identity_authority"])
        self.assertFalse(cap["finance_tail_closed"])
        self.assertEqual(cap["mixed_selection"], "FAIL_CLOSED")
        self.assertEqual(cap["terminal_credit_delta"], 0)

    def test_terminal_projection_preserves_finance_and_global_openness(self):
        r2 = load(R2)
        ta = load(TA)
        rec = ta["r2_v80_all_pairs_mrel_context_reconciliation"]
        self.assertIn("CURRENT_R2_V80", ta["status"])
        self.assertEqual(
            ta["authoritative_sources"]["current_r2_decision_intelligence"]["status"],
            r2["status"],
        )
        self.assertEqual(rec["current_r2_expected_git_blob_sha"], blob(R2))
        self.assertEqual(rec["runtime_git_blob_sha"], blob(RUNTIME))
        self.assertTrue(rec["relative_selection_only"])
        self.assertFalse(rec["finance_tail_closed"])
        self.assertFalse(rec["global_mission_completion"])
        self.assertEqual(rec["direct_route_count_delta"], 0)
        self.assertEqual(rec["terminal_credit_delta"], 0)
        self.assertFalse(ta["terminal_architecture_override"]["terminal"])
        self.assertIn(
            "ONE_FINANCE_RESIDUAL_REMAINS",
            ta["live_truth"]["current_r2_semantic_revision"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
