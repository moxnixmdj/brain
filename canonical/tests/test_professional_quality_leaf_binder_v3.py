from __future__ import annotations

from copy import deepcopy
import unittest
from unittest.mock import patch

from canonical.runtime import professional_quality_leaf_binder_v3 as v3


SEMANTIC = "PQ::R10_ANALYSIS_DECISION::SEMANTIC"
EXECUTION = "PQ::R10_ANALYSIS_DECISION::EXECUTION"


def base_output():
    semantic = [f"PQ::R{i}_ROOT::SEMANTIC" for i in range(1, 13)]
    semantic[9] = SEMANTIC
    execution = [f"PQ::R{i}_ROOT::EXECUTION" for i in range(1, 13)]
    execution[9] = EXECUTION
    verified_exec = execution[:11]
    open_exec = execution[11:]
    return {
        "schema": "PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_BINDER_V2",
        "status": "OPEN__LEAF_RECEIPTS_OR_EVIDENCE_REMAIN",
        "pass": False,
        "structural_errors": [],
        "verified_semantic_leaf_ids": [],
        "verified_execution_leaf_ids": verified_exec,
        "open_semantic_leaf_ids": semantic,
        "open_execution_leaf_ids": open_exec,
        "verified_leaf_count": 11,
        "open_leaf_count": 13,
        "receipt_results": [
            {
                "leaf_id": leaf,
                "root_id": "R",
                "kind": "EXECUTION",
                "path": f"canonical/verification/{n}.json",
                "admitted": True,
                "errors": [],
            }
            for n, leaf in enumerate(verified_exec)
        ],
        "rejected_receipt_count": 0,
        "existing_evidence_current": True,
        "manifest_status_has_promotion_authority": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


class ProfessionalQualityLeafBinderV3Tests(unittest.TestCase):
    def test_no_semantic_receipts_preserves_v2_execution_state_exactly(self):
        b = base_output()
        out = v3.harden_base_output(b)
        self.assertEqual(
            set(out["verified_execution_leaf_ids"]),
            set(b["verified_execution_leaf_ids"]),
        )
        self.assertEqual(out["verified_semantic_leaf_ids"], [])
        self.assertEqual(out["verified_leaf_count"], 11)
        self.assertEqual(out["open_leaf_count"], 13)
        self.assertEqual(
            out["semantic_property_truth_gate"]["semantic_receipts_checked"], 0
        )
        self.assertFalse(out["promotion_ready"])

    def test_v2_admitted_semantic_receipt_is_demoted_when_v3_gate_rejects(self):
        b = base_output()
        b["open_semantic_leaf_ids"].remove(SEMANTIC)
        b["verified_semantic_leaf_ids"] = [SEMANTIC]
        b["verified_leaf_count"] = 12
        b["open_leaf_count"] = 12
        b["receipt_results"].append({
            "leaf_id": SEMANTIC,
            "root_id": "R10_ANALYSIS_DECISION",
            "kind": "SEMANTIC",
            "path": "canonical/verification/legacy-r10-semantic.json",
            "admitted": True,
            "errors": [],
        })
        rejected = {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "SEMANTIC_TOTALITY_CLAIM_ID_MISMATCH",
            "leaf_property_truth_admissible": False,
        }
        with patch.object(v3, "_semantic_candidate_verdict", return_value=rejected):
            out = v3.harden_base_output(b)
        self.assertNotIn(SEMANTIC, out["verified_semantic_leaf_ids"])
        self.assertIn(SEMANTIC, out["open_semantic_leaf_ids"])
        row = next(x for x in out["receipt_results"] if x["leaf_id"] == SEMANTIC)
        self.assertFalse(row["admitted"])
        self.assertIn("SEMANTIC_PROPERTY_TRUTH_ADMISSION_FAILED", row["errors"])
        self.assertEqual(
            out["semantic_property_truth_gate"]["semantic_receipts_rejected"], 1
        )

    def test_gate_admitted_semantic_receipt_remains_admitted(self):
        b = base_output()
        b["open_semantic_leaf_ids"].remove(SEMANTIC)
        b["verified_semantic_leaf_ids"] = [SEMANTIC]
        b["verified_leaf_count"] = 12
        b["open_leaf_count"] = 12
        b["receipt_results"].append({
            "leaf_id": SEMANTIC,
            "root_id": "R10_ANALYSIS_DECISION",
            "kind": "SEMANTIC",
            "path": "canonical/verification/current-r10-semantic.json",
            "admitted": True,
            "errors": [],
        })
        accepted = {
            "pass": True,
            "status": "PASS__TEST",
            "leaf_property_truth_admissible": True,
        }
        with patch.object(v3, "_semantic_candidate_verdict", return_value=accepted):
            out = v3.harden_base_output(b)
        self.assertIn(SEMANTIC, out["verified_semantic_leaf_ids"])
        self.assertNotIn(SEMANTIC, out["open_semantic_leaf_ids"])
        self.assertEqual(
            out["semantic_property_truth_gate"]["semantic_receipts_admitted"], 1
        )

    def test_execution_receipts_never_require_semantic_gate(self):
        b = base_output()
        with patch.object(
            v3,
            "_semantic_candidate_verdict",
            side_effect=AssertionError("semantic gate must not run for execution receipts"),
        ):
            out = v3.harden_base_output(b)
        self.assertEqual(out["verified_leaf_count"], 11)

    def test_rejected_semantic_receipt_blocks_promotion_even_if_other_counts_are_full(self):
        b = base_output()
        all_sem = list(b["open_semantic_leaf_ids"])
        all_exec = list(b["verified_execution_leaf_ids"]) + list(b["open_execution_leaf_ids"])
        b["verified_execution_leaf_ids"] = all_exec
        b["open_execution_leaf_ids"] = []
        b["verified_semantic_leaf_ids"] = all_sem
        b["open_semantic_leaf_ids"] = []
        b["verified_leaf_count"] = 24
        b["open_leaf_count"] = 0
        b["receipt_results"].append({
            "leaf_id": SEMANTIC,
            "root_id": "R10_ANALYSIS_DECISION",
            "kind": "SEMANTIC",
            "path": "canonical/verification/bad-semantic.json",
            "admitted": True,
            "errors": [],
        })
        rejected = {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "SAFE_ABSTENTION_DOES_NOT_IMPLY_UNIVERSAL_POSITIVE_PROPERTY",
            "leaf_property_truth_admissible": False,
        }
        with patch.object(v3, "_semantic_candidate_verdict", return_value=rejected):
            out = v3.harden_base_output(b)
        self.assertFalse(out["promotion_ready"])
        self.assertFalse(out["pass"])
        self.assertGreaterEqual(out["rejected_receipt_count"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
