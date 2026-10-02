from __future__ import annotations

import unittest
from pathlib import Path

from canonical.runtime.opus55_acceptance_receipt_saturator_v1 import evaluate


ROOT = Path(__file__).resolve().parents[2]


class AcceptanceReceiptSaturatorV1Tests(unittest.TestCase):
    def test_current_snapshot_saturates_without_new_reality(self):
        out = evaluate(ROOT)
        self.assertEqual(out["status"], "COMPLETE__ZERO_NEW_REALITY__3_ATOMIC_PREDICATES_PROVED")
        self.assertEqual(out["scanned_json_files"], 768)
        self.assertEqual(out["fresh_acceptance_cases_consumed"], 0)
        self.assertFalse(out["terminal_replay"])
        self.assertEqual(
            {c["predicate_id"] for c in out["claims"]},
            {
                "SYNTHESIS_ZERO_UNSUPPORTED_MATERIAL_CLAIMS",
                "TOOL_LEARNING_SECOND_TASK_TRANSFER",
                "TOOL_LEARNING_NO_UNSUPPORTED_PROMOTION",
            },
        )
        self.assertTrue(all(c["scope_complete"] for c in out["claims"]))
        self.assertTrue(all(c["independent_or_objective"] for c in out["claims"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
