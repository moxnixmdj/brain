from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
TERM = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
REC = ROOT / "canonical/governance/R2_REGCAP_CONTEXT_ATOM_V2_CURRENTNESS_RECONCILIATION_20261010_V1.json"

V65 = "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261010_V65.json"
V65_SHA = "a3284796a11c1c69ede669e68deb6d0052b1e5be"
CERT = "canonical/runtime/regcap_context_atom_truth_certificate_v2.py"
CERT_SHA = "22490d1d61807aafdb94a6617ee64c4912ecc46f"
DISPATCH_SHA = "364eae40fbb38fc0b053bfa0f7aa4950863fa41a"
COMPILER_SHA = "128142cafd915c2fc206534fd2bdf557e6d2f1ea"
REC_SHA = "aa8b0fab84aebdbcbfb9a7d61b65761e0b62adf2"
VERIFY_SHA = "301ac6c9a36067fe2a97d8e3a3436ab5f522427f"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class Tests(unittest.TestCase):
    def test_current_r2_rebinds_only_live_context_atom_binding(self):
        d = load(R2)
        self.assertIn("V77", d["status"])
        self.assertEqual(d["scheduler_cut"]["path"], V65)
        self.assertEqual(d["scheduler_cut"]["git_blob_sha"], V65_SHA)

        row = d["regcap_context_atom_truth_dispatch"]
        self.assertEqual(row["truth_certificate_path"], CERT)
        self.assertEqual(row["truth_certificate_git_blob_sha"], CERT_SHA)
        self.assertEqual(row["semantic_dispatch_git_blob_sha"], DISPATCH_SHA)
        self.assertEqual(row["canonical_context_compiler_git_blob_sha"], COMPILER_SHA)
        self.assertEqual(row["reconciliation_git_blob_sha"], REC_SHA)
        self.assertEqual(row["verification_git_blob_sha"], VERIFY_SHA)
        self.assertFalse(row["negative_truth_from_absence_authorized"])
        self.assertFalse(row["concept_identity_authority"])
        self.assertFalse(row["policy_adequacy_authority"])
        self.assertFalse(row["finance_semantic_tail_closed"])
        self.assertEqual(row["terminal_credit_delta"], 0)

        historical = d["r2_v59_regcap_entry_surface_admission"]
        self.assertEqual(
            historical["context_atom_truth_certificate_blob"],
            "3e35f67ee88f7337569774835890efc54cdc734d",
        )

        rec = d["regcap_context_atom_v2_currentness_reconciliation"]
        self.assertEqual(rec["git_blob_sha"], REC_SHA)
        self.assertEqual(rec["direct_route_count_delta"], 0)
        self.assertEqual(rec["bounded_family_count_delta"], 0)
        self.assertEqual(rec["primary_unsolved_count_delta"], 0)
        self.assertEqual(rec["terminal_credit_delta"], 0)

    def test_terminal_pointer_projects_same_v77_v65_truth_and_stays_false(self):
        d = load(TERM)
        self.assertEqual(d["pointer_revision"], 133)
        self.assertFalse(d["live_truth"]["terminal"])

        current = d["authoritative_sources"]["current_r2_decision_intelligence"]
        self.assertIn("V77", current["status"])
        self.assertEqual(current["scheduler_cut"]["path"], V65)
        self.assertEqual(current["scheduler_cut"]["git_blob_sha"], V65_SHA)

        row = d["authoritative_sources"][
            "r2_v58_regcap_context_entry_surfaces_20261009_v1"
        ]["explicit_context_atom_truth"]
        self.assertEqual(row["runtime_path"], CERT)
        self.assertEqual(row["runtime_git_blob_sha"], CERT_SHA)
        self.assertEqual(row["dispatcher_git_blob_sha"], DISPATCH_SHA)
        self.assertEqual(row["canonical_context_compiler_git_blob_sha"], COMPILER_SHA)
        self.assertEqual(row["reconciliation_git_blob_sha"], REC_SHA)
        self.assertEqual(row["verification_git_blob_sha"], VERIFY_SHA)

        rec = d["r2_regcap_context_atom_v2_currentness_20261010_v1"]
        self.assertEqual(rec["reconciliation_git_blob_sha"], REC_SHA)
        self.assertEqual(rec["direct_route_count_delta"], 0)
        self.assertEqual(rec["bounded_family_count_delta"], 0)
        self.assertEqual(rec["acceptance_credit_delta"], 0)
        self.assertEqual(rec["terminal_credit_delta"], 0)

    def test_reconciliation_is_soundness_rebind_not_frontier_credit(self):
        d = load(REC)
        self.assertIn("V77_V65_SCHEDULER_UNCHANGED", d["status"])
        self.assertFalse(d["semantic_delta"]["authority_expanded"])
        self.assertTrue(
            d["semantic_delta"][
                "truth_surface_narrowed_to_canonical_verified_contextual_observations"
            ]
        )
        for value in d["scheduler_delta"].values():
            self.assertEqual(value, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
