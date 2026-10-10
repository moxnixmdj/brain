from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
ROOT2 = ROOT / "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261010_V62.json"
TERMINAL = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
ACTION = ROOT / "canonical/action_intents/ACTION_INTENT_CONTEXT_DEPENDENT_MEANING_POSITIVE_COVERAGE_20261010_V10.json"
RECON = ROOT / "canonical/governance/R2_SEMANTIC_ACQUISITION_RESEARCH_RECONCILIATION_20261010_V10.json"
HANDOFF = ROOT / "canonical/reasoning/2026-10-10_CONTEXT_DEPENDENT_MEANING_RESEARCH_HANDOFF_V11.json"
LEDGER = ROOT / "canonical/reasoning/2026-10-10_CONTEXT_DEPENDENT_MEANING_SUCCESSOR_EXECUTION_LEDGER_V7.json"
PROJECTION_VERIFY = ROOT / "canonical/verification/R2_V68_CURRENT_AND_TERMINAL_PROJECTION_VERIFY_20261010_V1.json"
WAKE_VERIFY = ROOT / "canonical/verification/R2_V68_TLAC_MREL_IDENTITY_WAKE_RECONCILIATION_VERIFY_20261010_V1.json"

EXPECTED_R2_SHA = "7710da2a39b93bae6d70f072120605cee3d2c950"
EXPECTED_ROOT2_SHA = "06913aa1c0ba48ba3102a2ac149b94c31fb4d8cd"
EXPECTED_TERMINAL_SHA = "f7eb7d41cc949da10b47c304f683361cf5efe86b"
EXPECTED_PROJECTION_VERIFY_SHA = "d21e834729aad5cb0c6a14c717c9068b8167a064"
EXPECTED_WAKE_VERIFY_SHA = "f077f20ba7daa31c1f5beb94839fee261f484268"

PAIR_RESIDUAL = (
    "TLAC_MREL_IDENTITY_CASES_OUTSIDE_VERIFIED_EXACT_TLAC_MREL_PAIR_SCOPE_OR_"
    "WITHOUT_AUTHENTICATED_MREL_CASE_BY_CASE_RESOLUTION_AUTHORITY_OR_TLAC_FSB_"
    "GSIB_STANDARD_MARKERS_REQUIRE_AN_ADDITIONAL_AUTHENTICATED_IDENTITY_DISCRIMINATOR"
)
OLD_PAIR_RESIDUAL = (
    "TLAC_MREL_IDENTITY_CASES_WHERE_THE_AUTHENTICATED_SHARED_LOSS_ABSORPTION_"
    "RECAPITALISATION_RESOLUTION_SIGNATURE_IS_NONSEPARATING_REQUIRE_AN_"
    "ADDITIONAL_AUTHENTICATED_IDENTITY_DISCRIMINATOR"
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def credits(v):
    out = []
    if isinstance(v, dict):
        for k, x in v.items():
            if k.endswith("credit_delta") and isinstance(x, (int, float)):
                out.append((k, x))
            out.extend(credits(x))
    elif isinstance(v, list):
        for x in v:
            out.extend(credits(x))
    return out


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r2 = load(R2)
        cls.root2 = load(ROOT2)
        cls.terminal = load(TERMINAL)
        cls.action = load(ACTION)
        cls.recon = load(RECON)
        cls.handoff = load(HANDOFF)
        cls.ledger = load(LEDGER)

    def test_control_sync_does_not_change_current_authority_bytes(self):
        self.assertEqual(git_blob(R2), EXPECTED_R2_SHA)
        self.assertEqual(git_blob(ROOT2), EXPECTED_ROOT2_SHA)
        self.assertEqual(git_blob(TERMINAL), EXPECTED_TERMINAL_SHA)
        self.assertIn("V68", self.r2["status"])
        self.assertIn("CURRENT_R2_V68", self.terminal["status"])

    def test_current_v68_oewn_live_state_is_preserved(self):
        dynamic = self.r2["direct_adequacy"]["dynamic_admissions"]
        self.assertEqual(dynamic["admission_count"], 4)
        self.assertIn(
            "DIRECT_ADEQUACY::OEWN_DECISION_MANIFEST_LATTICE_V1",
            dynamic["route_ids"],
        )
        rows = [
            row
            for row in self.r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]["verified_positive_subregions"]
            if isinstance(row, dict)
            and row.get("id") == "OEWN_SOURCE_PROVED_RELEASE_RELATIVE_DECISION_MANIFEST_LATTICE"
        ]
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["current_dynamic_route_admitted"])

    def test_action_intent_matches_exact_current_authority_and_residual(self):
        self.assertIn("R2_V68_ROOT2_V62", self.action["status"])
        auth = self.action["current_authority"]
        self.assertEqual(auth["r2_git_blob_sha"], EXPECTED_R2_SHA)
        self.assertEqual(auth["root2_git_blob_sha"], EXPECTED_ROOT2_SHA)
        self.assertEqual(auth["terminal_git_blob_sha"], EXPECTED_TERMINAL_SHA)
        self.assertIn(PAIR_RESIDUAL, self.action["still_open"])
        self.assertNotIn(OLD_PAIR_RESIDUAL, self.action["still_open"])
        self.assertIn(
            "REUSE_BOUND_TLAC_MREL_IDENTITY_DISCRIMINATOR_WHEN_EXACT_PAIR_SCOPE_AND_AUTHENTICATED_GOVERNING_REQUIREMENT_MARKER_IS_AVAILABLE",
            self.action["execution_order"],
        )
        self.assertIn("SECOND_TLAC_MREL_IDENTITY_DISCRIMINATOR", self.action["forbidden_duplicate_work"])

    def test_reconciliation_is_projection_only_and_uses_current_verifications(self):
        self.assertIn("CURRENT_R2_V68_ROOT2_V62", self.recon["status"])
        self.assertEqual(self.recon["load_bearing"]["r2_git_blob_sha"], EXPECTED_R2_SHA)
        self.assertEqual(self.recon["load_bearing"]["root2_git_blob_sha"], EXPECTED_ROOT2_SHA)
        self.assertIn(PAIR_RESIDUAL, self.recon["current_real_residual"])
        self.assertEqual(
            self.recon["current_projection_verification"]["git_blob_sha"],
            EXPECTED_PROJECTION_VERIFY_SHA,
        )
        self.assertEqual(
            self.recon["current_tlac_mrel_wake_verification"]["git_blob_sha"],
            EXPECTED_WAKE_VERIFY_SHA,
        )
        self.assertIn("NO_NEW_R2_AUTHORITY_CREATED_BY_THIS_CONTROL_SYNC", self.recon["hard_nonclaims"])

    def test_handoff_points_to_current_v68_and_narrow_residual(self):
        self.assertIn("R2_V68_ROOT2_V62", self.handoff["status"])
        self.assertEqual(self.handoff["load_bearing"]["r2_git_blob_sha"], EXPECTED_R2_SHA)
        self.assertEqual(self.handoff["load_bearing"]["root2_git_blob_sha"], EXPECTED_ROOT2_SHA)
        self.assertIn(PAIR_RESIDUAL, self.handoff["still_open"])
        self.assertNotIn(OLD_PAIR_RESIDUAL, self.handoff["still_open"])
        self.assertEqual(
            self.handoff["successor_controls"]["action_intent"],
            "canonical/action_intents/ACTION_INTENT_CONTEXT_DEPENDENT_MEANING_POSITIVE_COVERAGE_20261010_V10.json",
        )

    def test_ledger_records_projection_observation_not_duplicate_authority(self):
        by_event = {
            row.get("event"): row
            for row in self.ledger["events"]
            if isinstance(row, dict)
        }
        self.assertIn("VERIFY_CURRENT_R2_V68_TLAC_MREL_PAIR_PROJECTION", by_event)
        self.assertIn("SYNC_CONTEXT_DEPENDENT_MEANING_CONTROL_DOCS_TO_V68", by_event)
        self.assertIn("already bind", by_event["VERIFY_CURRENT_R2_V68_TLAC_MREL_PAIR_PROJECTION"]["result"])

    def test_current_v68_verification_receipts_are_exact(self):
        self.assertEqual(git_blob(PROJECTION_VERIFY), EXPECTED_PROJECTION_VERIFY_SHA)
        self.assertEqual(git_blob(WAKE_VERIFY), EXPECTED_WAKE_VERIFY_SHA)
        self.assertIn("ZERO_CREDIT", load(PROJECTION_VERIFY)["status"])
        self.assertIn("ZERO_CREDIT", load(WAKE_VERIFY)["status"])

    def test_terminal_remains_false_and_one_finance_residual_remains(self):
        self.assertFalse(self.terminal["live_truth"]["terminal"])
        fin = self.r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
        self.assertEqual(fin["state"], "INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT")
        self.assertIn(PAIR_RESIDUAL, fin["remaining_boundary"])
        self.assertIn("ONE_PRIMARY_FINANCE_SEMANTIC_RESIDUAL_REMAINS", self.r2["status"])

    def test_sync_documents_add_zero_credit_only(self):
        for path in (ACTION, RECON, HANDOFF, LEDGER):
            for key, value in credits(load(path)):
                self.assertEqual(value, 0, (path, key, value))


if __name__ == "__main__":
    unittest.main(verbosity=2)
