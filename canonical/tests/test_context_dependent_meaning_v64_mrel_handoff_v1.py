from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

ACTION = "canonical/action_intents/ACTION_INTENT_CONTEXT_DEPENDENT_MEANING_POSITIVE_COVERAGE_20261009_V8.json"
RECON = "canonical/governance/R2_SEMANTIC_ACQUISITION_RESEARCH_RECONCILIATION_20261009_V8.json"
HANDOFF = "canonical/reasoning/2026-10-09_CONTEXT_DEPENDENT_MEANING_RESEARCH_HANDOFF_V9.json"
LEDGER = "canonical/reasoning/2026-10-09_CONTEXT_DEPENDENT_MEANING_SUCCESSOR_EXECUTION_LEDGER_V5.json"

EXPECTED = {
    "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json": "ae24a56d4de6584c27ab54dcb8e834a98adc1d6e",
    "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V60.json": "b04d4a1deeb2d596683d0fb48df5485d02791375",
    "canonical/verification/R2_V64_FINANCE_MARKED_MENTION_RECONCILIATION_VERIFY_20261009_V1.json": "08fc4dbfb14163788fc8be47d470291f61e12c2b",
    "canonical/runtime/mrel_necessary_property_authority_v1.py": "10d91e251c76695368dc77d3370c30e61f31f09d",
    "canonical/verification/MREL_NECESSARY_PROPERTY_AUTHORITY_REBASE_VERIFY_20261009_V1.json": "ce7a16c8421a6efdb9529ec0db12408f1663593a",
    "canonical/runtime/tlac_mrel_shared_signature_guard_v1.py": "97d5572df0c4387c8ca461ccb900ec1a503530b5",
    "canonical/verification/TLAC_MREL_SHARED_SIGNATURE_GUARD_VERIFY_20261009_V1.json": "01adfa9390d99e80db6b127dd58759545f284e5b",
    "canonical/reasoning/2026-10-09_CONTEXT_DEPENDENT_MEANING_SUCCESSOR_EXECUTION_LEDGER_V4.json": "033175cb5a993f144e6100ff470b2373842dd3d3",
}


def blob(rel: str) -> str:
    raw = (ROOT / rel).read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class Tests(unittest.TestCase):
    def test_all_load_bearing_existing_blobs_are_exact(self):
        observed = {rel: blob(rel) for rel in EXPECTED}
        self.assertEqual(observed, EXPECTED)

    def test_current_r2_and_root_versions_are_v64_v60(self):
        r2 = load("canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json")
        root = load("canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V60.json")
        self.assertIn("__V64__", r2["status"])
        self.assertIn("V60", root["schema"])
        self.assertEqual(
            r2["scheduler_cut"]["git_blob_sha"],
            EXPECTED["canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V60.json"],
        )

    def test_action_intent_preserves_v64_and_mrel_boundaries(self):
        doc = load(ACTION)
        self.assertEqual(doc["live_authority"]["current_r2"]["version"], "V64")
        self.assertEqual(doc["live_authority"]["scheduler_cut"]["version"], "V60")
        self.assertIn(
            "TLAC_MREL_IDENTITY_WHEN_CONTEXT_CONTAINS_ONLY_THE_AUTHENTICATED_SHARED_RESOLUTION_SIGNATURE",
            doc["still_open"],
        )
        self.assertIn("INVENTED_TLAC_MREL_DISJOINTNESS", doc["forbidden_duplicate_work"])
        self.assertEqual(doc["accounting"]["terminal_credit_delta"], 0)

    def test_reconciliation_does_not_fake_r2_v65(self):
        doc = load(RECON)
        self.assertEqual(doc["load_bearing_r2"]["current_r2"]["version"], "V64")
        self.assertEqual(doc["load_bearing_r2"]["scheduler"]["version"], "V60")
        deltas = {x["id"]: x for x in doc["post_v64_semantic_authority_delta"]}
        self.assertFalse(deltas["MREL_BOUND_NECESSARY_PROPERTY_AUTHORITY"]["r2_version_bumped"])
        overlap = deltas["TLAC_MREL_SHARED_SIGNATURE_NONDISCRIMINATION"]
        self.assertFalse(overlap["bundle_separates_pair"])
        self.assertTrue(overlap["identity_discriminator_required"])
        self.assertIn("NO_CLAIM_R2_V65_CREATED", doc["hard_nonclaims"])

    def test_handoff_keeps_shared_signature_non_discriminating(self):
        doc = load(HANDOFF)
        overlap = doc["critical_new_truth"]["tlac_mrel_overlap"]
        self.assertFalse(overlap["bundle_separates_pair"])
        self.assertTrue(overlap["identity_discriminator_required"])
        self.assertIn(
            "TLAC_MREL_IDENTITY_WHEN_ONLY_SHARED_RESOLUTION_SEMANTICS_ARE_AVAILABLE",
            doc["still_open"],
        )
        self.assertIn(
            "NO_CLAIM_TLAC_MREL_EQUIVALENCE_DISJOINTNESS_OR_COEXTENSION",
            doc["hard_nonclaims"],
        )

    def test_ledger_records_exact_verified_merges(self):
        doc = load(LEDGER)
        by_event = {x["event"]: x for x in doc["events"]}
        self.assertEqual(
            by_event["BIND_MREL_NECESSARY_PROPERTY_AUTHORITY"]["merge_commit"],
            "0fa240c2d2b7a465b9bd40f63e641272a330aa0d",
        )
        self.assertEqual(
            by_event["BIND_TLAC_MREL_SHARED_SIGNATURE_NONDISCRIMINATION_GUARD"]["merge_commit"],
            "0a84e425f48c8df1555cdb105c8e982299ca48b2",
        )
        self.assertEqual(doc["accounting"]["terminal_credit_delta"], 0)

    def test_successor_files_form_one_consistent_chain(self):
        action = load(ACTION)
        recon = load(RECON)
        handoff = load(HANDOFF)
        ledger = load(LEDGER)
        self.assertEqual(
            action["semantic_reconciliation"]["path"] if "semantic_reconciliation" in action else RECON,
            RECON,
        )
        self.assertEqual(handoff["successor_controls"]["action_intent"], ACTION)
        self.assertEqual(handoff["successor_controls"]["semantic_reconciliation"], RECON)
        self.assertEqual(handoff["successor_controls"]["execution_ledger"], LEDGER)
        self.assertEqual(ledger["extends"]["path"], "canonical/reasoning/2026-10-09_CONTEXT_DEPENDENT_MEANING_SUCCESSOR_EXECUTION_LEDGER_V4.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
