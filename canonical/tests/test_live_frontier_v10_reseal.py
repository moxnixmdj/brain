from __future__ import annotations

import json
from pathlib import Path
import unittest

from canonical.runtime import capability_parallel_frontier_v2 as p

ROOT=Path(__file__).resolve().parents[2]
FRONTIER=ROOT/"canonical/governance/CURRENT_LIVE_WORK_FRONTIER.json"

class LiveFrontierV10ResealTests(unittest.TestCase):
    def _frontier(self):
        return json.loads(FRONTIER.read_text(encoding="utf-8"))

    def test_exact_current_reseal_and_zero_full_execution(self):
        out=p.plan_current_parallel_frontier()
        self.assertEqual(out["frontier_id"],"LIVE_WORK_FRONTIER_20261010_045B16EA_V10")
        self.assertTrue(out["frontier_currentness"]["currentness_verified"])
        self.assertEqual(out["parallel_full_execution_work_ids"],[])
        self.assertEqual(out["vector_complete_candidate_ids"],[])
        self.assertEqual(
            set(out["parallel_read_only_evidence_work_ids"]),
            {
                "BYTES_EXACT_SYMBOLIC_V24_NEXT_PHYSICAL_CUT",
                "ESCAPE_GAP_A_AUTHENTICATED_ROW_PROOFS",
                "ESCAPE_GAP_B_STRICT_PROGRESS_ROW_PROOFS",
                "PROFESSIONAL_QUALITY_V7_R12_META_COMPOSITION_CLOSURE_BINDING",
                "REPOSITORY_PROMOTION_ENFORCEMENT",
                "TB_SCIENCE_RANK20_V3_ACTIVATION_PRESTART_EVIDENCE",
            },
        )

    def test_tb_and_r2_are_rederived_not_stale_v8_semantics(self):
        f=self._frontier()
        by_id={row["work_id"]:row for row in f["candidates"]}
        tb=by_id["TB_SCIENCE_RANK20_V3_ACTIVATION_PRESTART_EVIDENCE"]
        self.assertTrue(tb["read_only_evidence"]["execution_authority_effective"])
        self.assertTrue(tb["read_only_evidence"]["task_read_authority_effective"])
        self.assertTrue(tb["read_only_evidence"]["activation_authority"])
        self.assertFalse(tb["read_only_evidence"]["activation_present"])
        self.assertFalse(tb["read_only_evidence"]["task_read"])
        self.assertFalse(tb["read_only_evidence"]["task_started"])
        self.assertEqual(tb["read_only_evidence"]["benchmark_trials_consumed"],18)

        r2=by_id["R2_FINANCE_SEMANTIC_ADEQUACY_TAIL"]
        self.assertEqual(r2["scheduler_state"],"SLEEPING")
        self.assertFalse(r2["read_only_evidence"]["wake_gate"])
        self.assertTrue(r2["read_only_evidence"]["general_mechanism_closed"])
        self.assertFalse(r2["read_only_evidence"]["finance_tail_closed"])
        self.assertEqual(r2["read_only_evidence"]["minimum_authenticated_observation_count"],1)
        self.assertTrue(r2["read_only_evidence"]["concrete_four_outcome_model_bound"])

if __name__=="__main__":
    unittest.main(verbosity=2)
