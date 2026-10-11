from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime import osworld_reference_instruction_authenticity_v1 as auth


class OsworldReferenceInstructionAuthenticityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.identity = json.loads((cls.root / "canonical/governance/OSWORLD_V21_PINNED_TASK_UNIVERSE_IDENTITY_20261010_V1.json").read_text())
        cls.reference = json.loads((cls.root / "canonical/governance/OSWORLD_V21_PUBLIC_REFERENCE_SEMANTIC_COVERAGE_20261011_V1.json").read_text())
        cls.verify = json.loads((cls.root / "canonical/verification/OSWORLD_V21_PUBLIC_REFERENCE_SEMANTIC_COVERAGE_INDEPENDENT_VERIFY_20261011_V1.json").read_text())

    def test_current_exact_sources_close_instruction_authenticity_only(self):
        out = auth.evaluate(self.identity, self.reference, self.verify)
        self.assertTrue(out["pass"])
        self.assertTrue(out["instruction_authenticity_closed"])
        self.assertFalse(out["full_task_implementation_semantics_closed"])
        self.assertFalse(out["evaluator_implementation_closed"])
        self.assertFalse(out["score_ready"])
        self.assertEqual(out["task_count"], 108)

    def test_manifest_mismatch_fails_closed(self):
        r = copy.deepcopy(self.reference)
        r["public_reference_source"]["scorecard_task_integrity_hash_manifest_sha256"] = "0" * 64
        out = auth.evaluate(self.identity, r, self.verify)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "TASK_HASH_MANIFEST_IDENTITY_MISMATCH")

    def test_missing_instruction_record_identity_fails_closed(self):
        v = copy.deepcopy(self.verify)
        v["source_replay"]["instruction_task_record_identity_checks_passed"] = 107
        out = auth.evaluate(self.identity, self.reference, v)
        self.assertFalse(out["pass"])
        self.assertIn("independent_instruction_task_record_checks", out["reason"])

    def test_scorecard_integrity_attestation_is_load_bearing(self):
        r = copy.deepcopy(self.reference)
        r["public_reference_source"]["source_claim"] = "UNBOUND"
        out = auth.evaluate(self.identity, r, self.verify)
        self.assertFalse(out["pass"])
        self.assertIn("reference_subject_claims_integrity_check", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
