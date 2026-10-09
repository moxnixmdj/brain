from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
V41 = ROOT / "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V41.json"
PTR = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
TERM = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
ENTAIL = ROOT / "canonical/runtime/source_aligned_semantic_entailment_v1.py"
CONTROL = ROOT / "canonical/runtime/semantic_relation_control_v1.py"

EXPECTED_ENTAIL_BLOB = "855f7d6cff2333bdaf19ca01317a164e81b98534"
EXPECTED_CONTROL_BLOB = "e06d9ecc244eae188060762b662a2d41a0157e75"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class Tests(unittest.TestCase):
    def test_v41_scheduler_pointer_terminal_and_runtime_reconcile(self):
        sched = load(V41)
        ptr = load(PTR)
        term = load(TERM)
        sched_blob = git_blob_sha(V41)

        self.assertEqual(
            sched["schema"],
            "PROJECT_BRAIN_ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V41",
        )
        self.assertIn("SOURCE_ALIGNED_ENTAILMENT_CONTROL_BOUND", sched["status"])
        self.assertEqual(
            ptr["scheduler_cut"]["path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V41.json",
        )
        self.assertEqual(ptr["scheduler_cut"]["git_blob_sha"], sched_blob)
        self.assertIn("V41", ptr["status"])

        precedence = term["r2_scheduler_precedence"]
        self.assertEqual(
            precedence["current_scheduler_path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V41.json",
        )
        self.assertEqual(precedence["current_scheduler_git_blob_sha"], sched_blob)
        self.assertEqual(
            term["live_truth"]["current_r2_scheduler_cut"],
            "ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V41",
        )

        self.assertEqual(git_blob_sha(ENTAIL), EXPECTED_ENTAIL_BLOB)
        self.assertEqual(git_blob_sha(CONTROL), EXPECTED_CONTROL_BLOB)

        recon = sched["source_aligned_semantic_entailment_reconciliation"]
        self.assertEqual(recon["runtime_git_blob_sha"], EXPECTED_ENTAIL_BLOB)
        self.assertEqual(
            recon["semantic_relation_control_git_blob_sha"],
            EXPECTED_CONTROL_BLOB,
        )
        self.assertTrue(recon["bounded_source_aligned_directional_entailment_closed"])
        self.assertTrue(
            recon["mutual_checked_direction_scoped_logical_equivalence_closed"]
        )
        self.assertFalse(recon["general_natural_language_entailment_closed"])
        self.assertEqual(recon["new_direct_adequacy_route_credit"], 0)
        self.assertEqual(recon["finance_subregion_count_credit"], 0)
        self.assertEqual(recon["terminal_credit_delta"], 0)

        direct = ptr["direct_adequacy"]
        self.assertEqual(direct["current_route_count"], 28)
        self.assertEqual(direct["bounded_family_count"], 25)

        cell = ptr["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
        self.assertEqual(len(cell["verified_positive_subregions"]), 10)
        self.assertIn(
            "BEYOND_THE_CHECKED_SOURCE_ALIGNED_ENTAILMENT_FRAGMENT",
            ptr["remaining_problem_class"],
        )
        self.assertIn(
            "BEYOND_THE_CHECKED_SOURCE_ALIGNED_ENTAILMENT_FRAGMENT",
            cell["remaining_boundary"],
        )

        terminal_recon = term["r2_v41_source_aligned_entailment_reconciliation"]
        self.assertEqual(terminal_recon["scheduler_cut_git_blob_sha"], sched_blob)
        self.assertEqual(terminal_recon["terminal_credit_delta"], 0)
        self.assertFalse(term["live_truth"]["general_natural_language_entailment_closed"])
        self.assertEqual(term["accounting"]["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
