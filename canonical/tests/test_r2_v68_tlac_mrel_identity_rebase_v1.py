from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
ROOT2 = ROOT / "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261010_V62.json"
ROOT2_OLD = ROOT / "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V61.json"
TERMINAL = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
ACTION = ROOT / "canonical/action_intents/ACTION_INTENT_CONTEXT_DEPENDENT_MEANING_POSITIVE_COVERAGE_20261010_V10.json"
RECON = ROOT / "canonical/governance/R2_SEMANTIC_ACQUISITION_RESEARCH_RECONCILIATION_20261010_V10.json"
HANDOFF = ROOT / "canonical/reasoning/2026-10-10_CONTEXT_DEPENDENT_MEANING_RESEARCH_HANDOFF_V11.json"
LEDGER = ROOT / "canonical/reasoning/2026-10-10_CONTEXT_DEPENDENT_MEANING_SUCCESSOR_EXECUTION_LEDGER_V7.json"
PAIR_VERIFY = ROOT / "canonical/verification/TLAC_MREL_IDENTITY_DISCRIMINATOR_VERIFY_20261010_V1.json"

OLD_RESIDUAL = (
    "TLAC_MREL_IDENTITY_CASES_WHERE_THE_AUTHENTICATED_SHARED_LOSS_ABSORPTION_"
    "RECAPITALISATION_RESOLUTION_SIGNATURE_IS_NONSEPARATING_REQUIRE_AN_"
    "ADDITIONAL_AUTHENTICATED_IDENTITY_DISCRIMINATOR"
)
NEW_RESIDUAL = (
    "TLAC_MREL_IDENTITY_CASES_OUTSIDE_VERIFIED_EBA_CASE_BY_CASE_MREL_AND_FSB_"
    "GSIB_TLAC_GOVERNING_REQUIREMENT_PAIR_SCOPE_REQUIRE_ADDITIONAL_AUTHENTICATED_"
    "IDENTITY_EVIDENCE"
)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def recursive_credit_values(value):
    out = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith("credit_delta") and isinstance(item, (int, float)):
                out.append((key, item))
            out.extend(recursive_credit_values(item))
    elif isinstance(value, list):
        for item in value:
            out.extend(recursive_credit_values(item))
    return out


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r2 = load(R2)
        cls.root2 = load(ROOT2)
        cls.old_root2 = load(ROOT2_OLD)
        cls.terminal = load(TERMINAL)
        cls.action = load(ACTION)
        cls.recon = load(RECON)
        cls.handoff = load(HANDOFF)
        cls.ledger = load(LEDGER)

    def test_current_r2_is_v68_and_route_counts_are_preserved(self):
        self.assertIn("V68", self.r2["status"])
        self.assertEqual(
            self.r2["direct_adequacy"]["current_route_count"],
            39,
        )
        self.assertEqual(
            self.r2["direct_adequacy"]["bounded_family_count"],
            36,
        )
        self.assertIn("FORTY_DIRECT_ROUTES", self.r2["status"])
        self.assertIn("THIRTY_SIX_BOUNDED_FAMILIES", self.r2["status"])

    def test_scheduler_binds_exact_root2_v62_blob(self):
        self.assertEqual(
            self.r2["scheduler_cut"]["path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261010_V62.json",
        )
        self.assertEqual(self.r2["scheduler_cut"]["git_blob_sha"], git_blob(ROOT2))
        self.assertIn("V62", self.root2["schema"])
        self.assertEqual(
            self.root2["supersedes"]["git_blob_sha"],
            git_blob(ROOT2_OLD),
        )

    def test_tlac_mrel_residual_is_refined_not_deleted_globally(self):
        fin = self.r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
        self.assertNotIn(OLD_RESIDUAL, fin["remaining_boundary"])
        self.assertIn(NEW_RESIDUAL, fin["remaining_boundary"])
        self.assertIn("ONE_PRIMARY_FINANCE_SEMANTIC_RESIDUAL_REMAINS", self.r2["status"])
        self.assertEqual(fin["state"], "INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT")

    def test_pair_scope_is_one_verified_positive_subregion(self):
        fin = self.r2["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
        rows = [
            row for row in fin["verified_positive_subregions"]
            if isinstance(row, dict)
            and row.get("id") == "TLAC_MREL_AUTHENTICATED_BOUNDED_GOVERNING_REQUIREMENT_IDENTITY_DISCRIMINATOR"
        ]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertFalse(row["global_semantic_identity_authority"])
        self.assertFalse(row["tlac_mrel_disjointness_authority"])
        self.assertFalse(row["open_world_regcap_complete"])
        self.assertFalse(row["terminal_authority"])
        self.assertEqual(
            row["verification"],
            "canonical/verification/TLAC_MREL_IDENTITY_DISCRIMINATOR_VERIFY_20261010_V1.json",
        )

    def test_action_reconciliation_handoff_all_preserve_narrow_residual(self):
        self.assertIn("V68_ROOT2_V62", self.action["status"])
        self.assertIn(NEW_RESIDUAL, self.action["still_open"])
        self.assertNotIn(OLD_RESIDUAL, self.action["still_open"])

        self.assertIn("V68_ROOT2_V62", self.recon["status"])
        self.assertIn(NEW_RESIDUAL, self.recon["current_real_residual"])
        self.assertEqual(
            self.recon["load_bearing"]["r2_git_blob_sha"],
            git_blob(R2),
        )
        self.assertEqual(
            self.recon["load_bearing"]["root2_git_blob_sha"],
            git_blob(ROOT2),
        )

        self.assertIn("R2_V68_ROOT2_V62", self.handoff["status"])
        self.assertIn(NEW_RESIDUAL, self.handoff["still_open"])
        self.assertEqual(
            self.handoff["load_bearing"]["r2_git_blob_sha"],
            git_blob(R2),
        )
        self.assertEqual(
            self.handoff["load_bearing"]["root2_git_blob_sha"],
            git_blob(ROOT2),
        )

    def test_ledger_records_pair_projection_and_v68_advance(self):
        events = {row.get("event") for row in self.ledger["events"] if isinstance(row, dict)}
        self.assertIn("PROJECT_TLAC_MREL_BOUNDED_IDENTITY_DISCRIMINATOR", events)
        self.assertIn("ADVANCE_R2_V68_ROOT2_V62", events)

    def test_v68_oewn_live_dynamic_admission_is_preserved(self):
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
        self.assertIn(
            "OEWN_DECISION_MANIFEST_LATTICE_LIVE_DYNAMIC_ROUTE_BOUND",
            self.r2["status"],
        )

    def test_terminal_projection_matches_v68_and_remains_false(self):
        auth = self.terminal["authoritative_sources"]["current_r2_decision_intelligence"]
        self.assertEqual(auth["status"], self.r2["status"])
        self.assertEqual(
            auth["scheduler_cut"]["path"],
            "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261010_V62.json",
        )
        self.assertEqual(auth["scheduler_cut"]["git_blob_sha"], git_blob(ROOT2))
        self.assertIn("CURRENT_R2_V68", self.terminal["status"])
        self.assertFalse(self.terminal["live_truth"]["terminal"])
        self.assertTrue(
            self.terminal["live_truth"]["r2_tlac_mrel_bounded_identity_discriminator_bound"]
        )
        self.assertFalse(
            self.terminal["live_truth"]["r2_tlac_mrel_global_identity_closed"]
        )
        row = self.terminal["r2_v68_tlac_mrel_identity_reconciliation_20261010_v1"]
        self.assertFalse(row["terminal"])
        self.assertFalse(row["finance_tail_closed"])

    def test_pair_verification_receipt_is_present_and_terminal_false(self):
        row = load(PAIR_VERIFY)
        self.assertIn("37_OF_37", row["status"])
        self.assertEqual(row["accounting"]["terminal_credit_delta"], 0)
        self.assertIn("NO_FINANCE_SEMANTIC_TAIL_CLOSURE", row["hard_nonclaims"])

    def test_new_successor_documents_add_zero_credit_only(self):
        for path in (R2, ROOT2, TERMINAL, ACTION, RECON, HANDOFF, LEDGER):
            for key, value in recursive_credit_values(load(path)):
                self.assertEqual(value, 0, (path, key, value))


if __name__ == "__main__":
    unittest.main(verbosity=2)
