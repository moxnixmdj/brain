from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def git_blob_sha(rel: str) -> str:
    raw = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class Tests(unittest.TestCase):
    def test_v78_scheduler_pointer_is_exact_v66_blob(self):
        r2 = load("canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json")
        cut = r2["scheduler_cut"]
        self.assertEqual(
            cut["path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261010_V66.json",
        )
        self.assertEqual(cut["git_blob_sha"], git_blob_sha(cut["path"]))
        self.assertIn("V78", r2["status"])

    def test_negative_theorem_is_not_counted_as_positive_coverage(self):
        r2 = load("canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json")
        cell = r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
        positives = [
            x.get("id")
            for x in cell.get("verified_positive_subregions", [])
            if isinstance(x, dict)
        ]
        negatives = [
            x.get("id")
            for x in cell.get("verified_negative_controls", [])
            if isinstance(x, dict)
        ]
        theorem = "REGCAP_FOUR_WAY_SHARED_LOSS_ABSORPTION_NONSEPARATION_GUARD"
        self.assertNotIn(theorem, positives)
        self.assertIn(theorem, negatives)

    def test_residual_remains_open_and_requires_discriminator(self):
        r2 = load("canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json")
        cell = r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
        self.assertEqual(
            cell["state"],
            "INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT",
        )
        self.assertIn(
            "REJECT_DISPOSITION_LOSS_ABSORPTION_ALONE",
            cell["required_action"],
        )
        self.assertIn(
            "ADDITIONAL_AUTHENTICATED_DISCRIMINATOR",
            cell["remaining_boundary"],
        )

    def test_route_and_residual_counts_do_not_inflate(self):
        cut = load("canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261010_V66.json")
        sr = cut["scheduler_result"]
        self.assertEqual(sr["direct_route_count"], 40)
        self.assertEqual(sr["bounded_family_count"], 36)
        self.assertEqual(
            sr["primary_internal_unsolved_pending_acquisition_or_experiment_cell_count"],
            1,
        )
        self.assertEqual(sr["primary_cell"], "FINANCE_SEMANTIC_ADEQUACY_TAIL")

    def test_terminal_projection_matches_v78_v66(self):
        t = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY.json")
        self.assertIn("CURRENT_R2_V78", t["status"])
        src = t["authoritative_sources"]["current_r2_decision_intelligence"]
        self.assertEqual(
            src["scheduler_cut"]["path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261010_V66.json",
        )
        self.assertEqual(
            src["scheduler_cut"]["git_blob_sha"],
            git_blob_sha(src["scheduler_cut"]["path"]),
        )
        self.assertEqual(
            t["r2_scheduler_precedence"]["current_scheduler_git_blob_sha"],
            git_blob_sha(src["scheduler_cut"]["path"]),
        )
        self.assertFalse(t["live_truth"].get("terminal", False))
        self.assertEqual(t["live_truth"]["r2_primary_internal_unsolved_count"], 1)

    def test_reconciliation_binds_exact_successor_blobs(self):
        rec = load(
            "canonical/governance/"
            "R2_V78_FOUR_WAY_LOSS_ABSORPTION_NONSEPARATION_RECONCILIATION_20261010_V1.json"
        )
        self.assertEqual(
            rec["successor"]["current_r2_git_blob_sha"],
            git_blob_sha("canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"),
        )
        self.assertEqual(
            rec["successor"]["root2_git_blob_sha"],
            git_blob_sha("canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261010_V66.json"),
        )
        self.assertEqual(
            rec["successor"]["terminal_git_blob_sha"],
            git_blob_sha("canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"),
        )
        self.assertEqual(rec["semantic_delta"]["verified_positive_subregion_count_delta"], 0)
        self.assertEqual(rec["semantic_delta"]["verified_negative_control_count_delta"], 1)
        self.assertFalse(rec["semantic_delta"]["finance_tail_closed"])
        self.assertEqual(rec["accounting"]["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
