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
        docs = {key: _load(rel) for key, rel in PATHS.items()}
        shas = {rel: _git_blob_sha(rel) for rel in PATHS.values()}
        return docs, shas

    def evaluate(self, docs, shas):
        return evaluate_documents(
            docs["authority"],
            docs["closure"],
            docs["matrix"],
            docs["scope_reconciliation"],
            docs["atomic_bindings"],
            docs["p1_propagation"],
            shas,
        )

    def test_live_projection_is_consistent(self):
        docs, shas = self.live()
        out = self.evaluate(docs, shas)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["whole_scope_contract_passes"], 11)
        self.assertEqual(out["unaffected_behavioral_family_passes"], 11)
        self.assertEqual(out["p1_dependent_behavioral_families_quarantined"], 8)
        self.assertEqual(out["acceptance_closed_families"], 2)
        self.assertEqual(out["atomic_predicates_proved"], 7)
        self.assertEqual(out["atomic_predicates_unresolved"], 31)

    def test_stale_19_of_19_behavioral_authority_fails_closed(self):
        docs, shas = self.live()
        docs = copy.deepcopy(docs)
        docs["authority"]["truth"]["behavioral_families"] = "19/19_PASS"
        out = self.evaluate(docs, shas)
        self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_BEHAVIORAL_FAMILY_STATE_MISMATCH", out["errors"])

    def test_stale_12_of_12_contract_authority_fails_closed(self):
        docs, shas = self.live()
        docs = copy.deepcopy(docs)
        docs["authority"]["truth"]["contracts"] = "12/12_PASS"
        out = self.evaluate(docs, shas)
        self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_WHOLE_SCOPE_CONTRACT_STATE_MISMATCH", out["errors"])

    def test_reopening_p1_must_leave_unproved_counter_nonzero(self):
        docs, shas = self.live()
        docs = copy.deepcopy(docs)
        docs["closure"]["counters"]["unproved_required_behaviors"] = 0
        out = self.evaluate(docs, shas)
        self.assertFalse(out["pass"])
        self.assertIn("CLOSURE_UNPROVED_REQUIRED_BEHAVIOR_COUNT_NOT_1", out["errors"])

    def test_stale_four_family_acceptance_fails_closed(self):
        docs, shas = self.live()
        docs = copy.deepcopy(docs)
        docs["closure"]["opus55_acceptance_summary"]["calibrated_family_count"] = 4
        docs["closure"]["opus55_acceptance_summary"]["pending_family_count"] = 15
        out = self.evaluate(docs, shas)
        self.assertFalse(out["pass"])
        self.assertIn("CLOSURE_ACCEPTANCE_SUMMARY_MISMATCH", out["errors"])

    def test_p1_family_set_drift_fails_closed(self):
        docs, shas = self.live()
        docs = copy.deepcopy(docs)
        docs["p1_propagation"]["quarantined_families"].append(
            "TOOL_DISCOVERY_SELECTION_AND_LEARNING"
        )
        out = self.evaluate(docs, shas)
        self.assertFalse(out["pass"])
        self.assertIn("P1_QUARANTINED_FAMILY_SET_MISMATCH", out["errors"])

    def test_stale_authority_blob_pointer_fails_closed(self):
        docs, shas = self.live()
        docs = copy.deepcopy(docs)
        docs["authority"]["sources"]["terminal_closure_manifest"]["git_blob_sha"] = "0" * 40
        out = self.evaluate(docs, shas)
        self.assertFalse(out["pass"])
        self.assertIn(
            "AUTHORITY_SOURCE_BLOB_MISMATCH:terminal_closure_manifest",
            out["errors"],
        )

    def test_authorized_case_action_fails_while_frontier_is_zero(self):
        docs, shas = self.live()
        docs = copy.deepcopy(docs)
        docs["authority"]["atomic_acceptance_frontier"][
            "authorized_acceptance_case_actions"
        ] = ["BAD"]
        out = self.evaluate(docs, shas)
        self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_UNAUTHORIZED_CASE_ACTION_PRESENT", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
