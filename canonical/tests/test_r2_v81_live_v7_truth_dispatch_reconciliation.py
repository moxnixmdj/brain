from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
TA = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
CERT5 = ROOT / "canonical/runtime/regcap_loss_cushion_truth_certificate_v5.py"
GROUND7 = ROOT / "canonical/runtime/loss_absorbing_cushion_regcap_grounding_v7.py"
DISPATCH = ROOT / "canonical/runtime/semantic_truth_dispatch_v1.py"
CERT4 = ROOT / "canonical/runtime/regcap_loss_cushion_truth_certificate_v4.py"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


class Tests(unittest.TestCase):
    def test_r2_v81_binds_exact_live_truth_path(self):
        r2 = load(R2)
        live = r2["regcap_loss_cushion_truth_v5_live_binding"]
        self.assertIn("__V81__", r2["status"])
        self.assertEqual(live["truth_certificate_git_blob_sha"], blob(CERT5))
        self.assertEqual(live["grounding_git_blob_sha"], blob(GROUND7))
        self.assertEqual(live["dispatcher_git_blob_sha"], blob(DISPATCH))
        self.assertTrue(live["historical_v4_preserved"])
        self.assertTrue(CERT4.exists())
        self.assertFalse(live["global_identity_authority"])
        self.assertFalse(live["finance_tail_closed"])
        self.assertEqual(live["direct_route_count_delta"], 0)
        self.assertEqual(live["terminal_credit_delta"], 0)

    def test_terminal_authority_projects_v81_without_false_closure(self):
        r2 = load(R2)
        ta = load(TA)
        rec = ta["r2_v81_live_v7_truth_dispatch_reconciliation"]
        self.assertIn("CURRENT_R2_V81", ta["status"])
        self.assertEqual(
            ta["authoritative_sources"]["current_r2_decision_intelligence"]["status"],
            r2["status"],
        )
        self.assertEqual(rec["current_r2_expected_git_blob_sha"], blob(R2))
        self.assertEqual(rec["truth_certificate_git_blob_sha"], blob(CERT5))
        self.assertEqual(rec["dispatcher_git_blob_sha"], blob(DISPATCH))
        self.assertEqual(rec["grounding_git_blob_sha"], blob(GROUND7))
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
