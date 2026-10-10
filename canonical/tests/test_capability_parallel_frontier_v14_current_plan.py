from __future__ import annotations

import unittest

from canonical.runtime.capability_parallel_frontier_post_composition_v1 import (
    plan_current_post_composition_frontier,
)


class CapabilityParallelFrontierV14CurrentPlanTests(unittest.TestCase):
    def test_current_plan_uses_four_safe_evidence_lanes_and_parks_tb(self):
        out=plan_current_post_composition_frontier()
        self.assertEqual(
            set(out["parallel_read_only_evidence_work_ids"]),
            {
                "PROFESSIONAL_QUALITY_V7_WHOLE_LEAF_DOMAIN_EVIDENCE",
                "BYTES_EXACT_SYMBOLIC_V24_NEXT_PHYSICAL_CUT",
                "ESCAPE_GAP_A_AUTHENTICATED_ROW_PROOFS",
                "ESCAPE_GAP_B_STRICT_PROGRESS_ROW_PROOFS",
            },
        )
        self.assertIn(
            "TB_SCIENCE_RANK20_V3_RETIRED_PARKED",
            out["nonprimary_candidate_ids"],
        )
        self.assertNotIn(
            "TB_SCIENCE_RANK20_V3_RETIRED_PARKED",
            out["parallel_read_only_evidence_work_ids"],
        )
        self.assertIn(
            "R2_FINANCE_SEMANTIC_ADEQUACY_TAIL",
            out["nonprimary_candidate_ids"],
        )
        self.assertIn(
            "ASSURANCE_UVCK_V2_PROMOTION_GATES",
            out["nonprimary_candidate_ids"],
        )

    def test_no_full_execution_authority_is_created(self):
        out=plan_current_post_composition_frontier()
        self.assertEqual(out["parallel_full_execution_work_ids"], [])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["terminal_credit_delta"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
