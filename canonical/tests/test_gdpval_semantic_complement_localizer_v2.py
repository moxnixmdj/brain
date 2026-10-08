from __future__ import annotations

import unittest

from canonical.runtime.gdpval_semantic_complement_localizer_v2 import (
    _compound_candidate,
    localize_rows,
)


class GDPvalSemanticComplementLocalizerV2Tests(unittest.TestCase):
    def test_flat_compound_candidate_is_diagnostic_not_credit(self):
        x = _compound_candidate("The report must include revenue and include expenses.")
        self.assertEqual(x["status"], "BOUNDED_COMPOUND_CANDIDATE")
        self.assertEqual(x["part_count"], 2)

    def test_ambiguous_compound_stays_unresolved(self):
        x = _compound_candidate("The report must include revenue or expenses.")
        self.assertNotEqual(x["status"], "BOUNDED_COMPOUND_CANDIDATE")

    def test_complete_population_guard_fails_closed(self):
        out = localize_rows([])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertFalse(out["terminal_authority"])

    def test_synthetic_220_never_mints_terminal_or_scope_credit(self):
        rows = []
        for i in range(220):
            rows.append({
                "row_idx": i,
                "row": {
                    "task_id": f"task-{i:03d}",
                    "sector": "S",
                    "occupation": "O",
                    "prompt": "The report must include revenue and include expenses.",
                    "reference_files": [],
                    "deliverable_files": [],
                    "rubric_json": "[]",
                },
            })
        out = localize_rows(rows)
        self.assertTrue(out["status"].startswith("PASS__"))
        self.assertEqual(out["population"]["task_count"], 220)
        self.assertEqual(out["inference"]["fresh_target_model_queries"], 0)
        self.assertFalse(out["soundness"]["candidate_is_credit"])
        self.assertFalse(out["soundness"]["gdpval_scope_closed"])
        self.assertFalse(out["soundness"]["u_deletion_authority"])
        self.assertFalse(out["soundness"]["terminal_authority"])
        self.assertGreater(
            out["compound_candidate_counts"].get("BOUNDED_COMPOUND_CANDIDATE", 0),
            0,
        )


if __name__ == "__main__":
    unittest.main()
