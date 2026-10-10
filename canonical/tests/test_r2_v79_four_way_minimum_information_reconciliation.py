from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
TA = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
DISCOVERY = ROOT / "canonical/runtime/regcap_mrel_property_candidate_discovery_v1.py"
CONTROL = ROOT / "canonical/runtime/regcap_candidate_ambiguity_control_v1.py"
VERIFY = ROOT / "canonical/verification/R2_FOUR_WAY_REGCAP_MREL_MINIMUM_INFORMATION_VERIFY_20261010_V1.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


class Tests(unittest.TestCase):
    def test_r2_v79_binds_exact_four_way_minimum_information_runtime(self):
        r2 = load(R2)
        cap = r2["regcap_mrel_four_way_minimum_information"]
        self.assertIn("__V79__", r2["status"])
        self.assertEqual(cap["candidate_discovery_git_blob_sha"], blob(DISCOVERY))
        self.assertEqual(cap["ambiguity_control_git_blob_sha"], blob(CONTROL))
        self.assertEqual(
            cap["verification_path"],
            str(VERIFY.relative_to(ROOT)).replace("\\", "/"),
        )
        self.assertEqual(
            cap["bound_candidate_ids"],
            ["REGCAP::CCOB", "REGCAP::CCYB", "REGCAP::TLAC", "REGCAP::MREL"],
        )
        self.assertFalse(cap["bare_shared_property_identity_authority"])
        self.assertTrue(cap["incomplete_observation_model_routes_minimum_information"])
        self.assertFalse(cap["finance_tail_closed"])
        self.assertEqual(cap["terminal_credit_delta"], 0)

    def test_terminal_authority_projects_v79_without_inflating_closure(self):
        r2 = load(R2)
        ta = load(TA)
        rec = ta["r2_v79_four_way_minimum_information_reconciliation"]
        self.assertIn("CURRENT_R2_V79", ta["status"])
        self.assertEqual(
            ta["authoritative_sources"]["current_r2_decision_intelligence"]["status"],
            r2["status"],
        )
        self.assertEqual(rec["current_r2_expected_git_blob_sha"], blob(R2))
        self.assertEqual(rec["bound_candidate_count"], 4)
        self.assertEqual(rec["direct_route_count_delta"], 0)
        self.assertFalse(rec["finance_tail_closed"])
        self.assertEqual(rec["terminal_credit_delta"], 0)
        self.assertFalse(ta["terminal_architecture_override"]["terminal"])
        self.assertIn(
            "ONE_FINANCE_RESIDUAL_REMAINS",
            ta["live_truth"]["current_r2_semantic_revision"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
