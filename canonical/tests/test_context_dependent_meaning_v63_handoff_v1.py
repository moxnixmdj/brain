from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

PATHS = {
    "r2": ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
    "root2": ROOT / "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V59.json",
    "terminal": ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
    "semrec": ROOT / "canonical/governance/R2_SEMANTIC_ACQUISITION_RESEARCH_RECONCILIATION_20261009_V6.json",
    "intent": ROOT / "canonical/action_intents/ACTION_INTENT_CONTEXT_DEPENDENT_MEANING_POSITIVE_COVERAGE_20261009_V6.json",
    "ledger": ROOT / "canonical/reasoning/2026-10-09_CONTEXT_DEPENDENT_MEANING_SUCCESSOR_EXECUTION_LEDGER_V3.json",
    "handoff": ROOT / "canonical/reasoning/2026-10-09_CONTEXT_DEPENDENT_MEANING_RESEARCH_HANDOFF_V7.json",
}


def load(name):
    return json.loads(PATHS[name].read_text(encoding="utf-8"))


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = {name: load(name) for name in PATHS}

    def test_current_authority_is_v63_v59_terminal113(self):
        self.assertIn("ACTIVE_CURRENT_R2_AUTHORITY__V63__", self.docs["r2"]["status"])
        self.assertEqual(
            self.docs["r2"]["scheduler_cut"]["path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V59.json",
        )
        self.assertEqual(self.docs["r2"]["scheduler_cut"]["git_blob_sha"], git_blob(PATHS["root2"]))
        self.assertEqual(self.docs["terminal"]["pointer_revision"], 113)
        self.assertIn("CURRENT_R2_V63", self.docs["terminal"]["status"])

    def test_semantic_reconciliation_binds_exact_current_authority(self):
        cur = self.docs["semrec"]["current_r2"]
        self.assertEqual(cur["version"], "V63")
        self.assertEqual(cur["pointer_git_blob_sha"], git_blob(PATHS["r2"]))
        self.assertEqual(cur["scheduler_cut_git_blob_sha"], git_blob(PATHS["root2"]))
        self.assertEqual(cur["terminal_pointer_git_blob_sha"], git_blob(PATHS["terminal"]))
        self.assertEqual(cur["direct_route_count"], 39)
        self.assertEqual(cur["bounded_family_count"], 36)
        self.assertEqual(cur["primary_internal_unsolved_count"], 1)

    def test_action_intent_points_to_semantic_reconciliation(self):
        intent = self.docs["intent"]
        ref = intent["semantic_reconciliation"]
        self.assertEqual(ref["git_blob_sha"], git_blob(PATHS["semrec"]))
        self.assertIn("R2_V63", intent["status"])
        self.assertIn(
            "SECOND_REGCAP_CCOB_CCYB_TLAC_CONTEXTUAL_STACK",
            intent["forbidden_duplicate_work"],
        )

    def test_ledger_records_v63_merge_and_preserves_nonclaims(self):
        ledger = self.docs["ledger"]
        self.assertEqual(
            ledger["extends"]["git_blob_sha"],
            "097aa109d247d02abfd713488f37da13f1e25683",
        )
        event = next(x for x in ledger["events"] if x["order"] == 20)
        self.assertEqual(event["merge_commit"], "93782a47b80dde37c4c880affff066e753eeae03")
        self.assertEqual(event["current_r2_git_blob_sha"], git_blob(PATHS["r2"]))
        self.assertEqual(event["scheduler_git_blob_sha"], git_blob(PATHS["root2"]))
        self.assertEqual(event["terminal_pointer_git_blob_sha"], git_blob(PATHS["terminal"]))
        self.assertIn("NO_CLAIM_FINANCE_SEMANTIC_TAIL_CLOSED", ledger["hard_nonclaims"])

    def test_handoff_links_all_successor_controls_by_blob(self):
        h = self.docs["handoff"]
        controls = h["successor_controls"]
        self.assertEqual(
            controls["semantic_reconciliation"]["git_blob_sha"],
            git_blob(PATHS["semrec"]),
        )
        self.assertEqual(controls["action_intent"]["git_blob_sha"], git_blob(PATHS["intent"]))
        self.assertEqual(
            controls["successor_execution_ledger"]["git_blob_sha"],
            git_blob(PATHS["ledger"]),
        )
        self.assertEqual(h["live_authority"]["r2_pointer_git_blob_sha"], git_blob(PATHS["r2"]))
        self.assertEqual(h["live_authority"]["scheduler_cut_git_blob_sha"], git_blob(PATHS["root2"]))
        self.assertEqual(h["live_authority"]["terminal_pointer_git_blob_sha"], git_blob(PATHS["terminal"]))

    def test_handoff_starts_successor_after_closed_regcap_subregion(self):
        closed = self.docs["handoff"]["what_is_now_closed"]
        self.assertIn(
            "AUTHENTICATED_THREE_RIVAL_REGCAP_CONTEXT_LOGICAL_EQUIVALENCE_IN_SCOPE_FOR_BOUND_SIGNATURES",
            closed,
        )
        self.assertIn(
            "DO_NOT_REBUILD_REGCAP_CONTEXTUAL_MAPPING",
            self.docs["handoff"]["critical_path"],
        )
        self.assertIn(
            "NO_CLAIM_GLOBAL_LOSS_ABSORBING_CUSHION_IDENTITY",
            self.docs["handoff"]["hard_nonclaims"],
        )

    def test_all_successor_artifacts_keep_zero_credit(self):
        for name in ("semrec", "intent", "ledger", "handoff"):
            acc = self.docs[name]["accounting"]
            self.assertEqual(acc["incremental_spend_usd"], 0, name)
            self.assertEqual(acc["acceptance_credit_delta"], 0, name)
            self.assertEqual(acc["terminal_credit_delta"], 0, name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
