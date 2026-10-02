from __future__ import annotations

import copy
import unittest

from canonical.runtime.terminal_projection_consistency_v1 import (
    PATHS,
    _git_blob_sha,
    _load,
    evaluate_documents,
)

class TerminalProjectionConsistencyTests(unittest.TestCase):
    def live(self):
        docs = {k: _load(v) for k, v in PATHS.items()}
        shas = {v: _git_blob_sha(v) for v in PATHS.values()}
        return docs, shas

    def evaluate(self, docs, shas):
        return evaluate_documents(
            docs["authority"], docs["closure"], docs["matrix"], docs["calibration"],
            docs["residual"], docs["plan"], docs["kernel"], shas,
        )

    def test_live_projection_is_consistent(self):
        docs, shas = self.live()
        out = self.evaluate(docs, shas)
        self.assertTrue(out["pass"], out)

    def test_stale_closure_count_fails_closed(self):
        docs, shas = self.live()
        docs = copy.deepcopy(docs)
        docs["closure"]["opus55_acceptance_summary"]["calibrated_family_count"] = 2
        out = self.evaluate(docs, shas)
        self.assertFalse(out["pass"])
        self.assertIn("CLOSURE_ACCEPTANCE_SUMMARY_MISMATCH", out["errors"])

    def test_stale_authority_blob_pointer_fails_closed(self):
        docs, shas = self.live()
        docs = copy.deepcopy(docs)
        docs["authority"]["sources"]["terminal_closure_manifest"]["git_blob_sha"] = "0" * 40
        out = self.evaluate(docs, shas)
        self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_SOURCE_BLOB_MISMATCH:terminal_closure_manifest", out["errors"])

    def test_authorized_case_action_fails_while_residual_is_blocked(self):
        docs, shas = self.live()
        docs = copy.deepcopy(docs)
        docs["authority"]["atomic_acceptance_frontier"]["authorized_acceptance_case_actions"] = ["BAD"]
        out = self.evaluate(docs, shas)
        self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_UNAUTHORIZED_CASE_ACTION_PRESENT", out["errors"])


    def test_delegation_cannot_reenter_residual_plan(self):
        docs, shas = self.live()
        docs = copy.deepcopy(docs)
        docs["plan"]["residual_families"].append("SUBAGENT_DELEGATION_AND_COORDINATION")
        docs["plan"]["residual_family_count"] += 1
        out = self.evaluate(docs, shas)
        self.assertFalse(out["pass"])
        self.assertIn("PLAN_RETAINS_ALREADY_CALIBRATED_DELEGATION", out["errors"])

    def test_delegation_acceptance_cannot_be_misreported_as_ownership_promotion(self):
        docs, shas = self.live()
        docs = copy.deepcopy(docs)
        row = next(r for r in docs["matrix"]["rows"] if r.get("family") == "SUBAGENT_DELEGATION_AND_COORDINATION")
        row["postwave_ownership_credit"] = "PROMOTED"
        out = self.evaluate(docs, shas)
        self.assertFalse(out["pass"])
        self.assertIn("MATRIX_DELEGATION_PROMOTION_OVERCLAIM", out["errors"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
