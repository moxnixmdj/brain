from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
CLASSIFIER = ROOT / "canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json"

MUTABLE_CURRENT_PATHS = {
    "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
    "canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json",
    "canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json",
    "canonical/governance/CURRENT_COVERAGE_COMPLETENESS_ROOT_CERTIFICATES.json",
    "canonical/governance/CURRENT_DEFAULT_RUNTIME_INTEGRATION.json",
    "canonical/governance/CURRENT_ONE_SHOT_REALITY_CLOSURE.json",
    "canonical/governance/CURRENT_TB_SCIENCE_EXECUTION.json",
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
}

class ResidualReuseCurrentnessTests(unittest.TestCase):
    def load(self):
        return json.loads(CLASSIFIER.read_text(encoding="utf-8"))

    def test_mutable_current_sources_are_path_bound_not_blob_frozen(self):
        doc = self.load()
        by_path = {row["path"]: row for row in doc["sources"]}
        for path in MUTABLE_CURRENT_PATHS:
            self.assertIn(path, by_path)
            row = by_path[path]
            self.assertEqual(
                row["binding"],
                "MUTABLE_CURRENT_POINTER_PATH_IDENTITY__LIVE_INVARIANTS_RECHECKED",
            )
            self.assertFalse(row["observed_blob_is_load_bearing"])
            self.assertNotIn("git_blob_sha", row)
        self.assertNotIn(
            "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json",
            by_path,
        )

    def test_mutable_derived_summaries_are_explicitly_nonauthoritative(self):
        doc = self.load()
        law = doc["classification_currentness_law"]
        self.assertIn("RECOMPUTE_FROM_SOURCE_CURRENT_PATH", law["mutable_source_derived_summaries"])
        self.assertIn("CURRENT_SOURCE_WINS", law["fail_closed_rule"])
        by_id = {row["residual_id"]: row for row in doc["classifications"]}
        for residual_id in (
            "R2_PRIMARY_FINANCE_SEMANTIC_TAIL",
            "ASSURANCE_CLOSURE_COMPILER_NOT_LIVE_DEFAULT",
            "PROFESSIONAL_QUALITY_BROAD_EXECUTION",
            "TB_SCIENCE_RANK19",
            "OPUS_FRONTIER_CHECKPOINT_OPEN_FAMILIES",
        ):
            self.assertFalse(by_id[residual_id]["observed_summary_is_load_bearing"])

    def test_escape_successor_audit_is_current_v2_not_historical_v1(self):
        doc = self.load()
        by_id = {row["residual_id"]: row for row in doc["classifications"]}
        for rid in (
            "ESCAPE_GAP_A_ACQUISITION_TOTALITY",
            "ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS",
        ):
            row = by_id[rid]
            self.assertEqual(
                row["executable_audit"],
                "canonical/runtime/escape_progress_shared_gap_audit_v2.py",
            )
            self.assertEqual(
                row["audit_verification"],
                "canonical/verification/ESCAPE_PROGRESS_SHARED_GAP_EXECUTABLE_AUDIT_VERIFY_20261010_V4.json",
            )
            self.assertIn("SUCCESSOR_AUDIT_V2_VERIFIED", row["current_gate_status"])
            self.assertNotIn("NOT_YET_LIVE", row["current_gate_status"])

    def test_completed_escape_audit_is_not_left_in_next_execution_cut(self):
        doc = self.load()
        cut = doc["next_shared_execution_cut"]
        self.assertFalse(any(
            x.startswith("IMPLEMENT_AND_INDEPENDENTLY_VERIFY_COUNT_GENERIC_ESCAPE_SUCCESSOR_AUDIT")
            for x in cut
        ))
        self.assertNotIn(
            "NO_CLAIM_SUCCESSOR_ESCAPE_AUDIT_IS_EXECUTABLE_OR_VERIFIED_YET",
            doc["hard_nonclaims"],
        )

if __name__ == "__main__":
    unittest.main(verbosity=2)
