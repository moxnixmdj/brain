from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "canonical/governance/TB_SCIENCE_RANK20_ONE_SLOT_EXECUTION_AUTHORITY_20261010_V6.json"
LEDGER = ROOT / "canonical/governance/TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261010_V51.json"
CLAIM = ROOT / "canonical/governance/TB_SCIENCE_RANK20_LOGICAL_ATTEMPT_CLAIM_BINDING_20261010_V6.json"
VERIFY = ROOT / "canonical/verification/TB_SCIENCE_RANK20_V6_CLAIM_BINDING_INDEPENDENT_VERIFY_20261010_V1.json"

CLAIM_DIGEST = "sha256:3c4801910a41d14fc31bc7ec5e4b0f3467154aed5e8ac914f727cb6773d10860"
ATTEMPT = "f3d4e55a96b3d2dddb85e4f3c5e085d83ab9f7e6c186bba00b0146a528f339b7"
SLOT = "terminal-bench-science/hysteretic-aquifer-control::trial-0"
TASK = "sha256:681df0c3b2ada03a933ac4d2e11f07983676f87a9f26b61e416987904b880289"


def load(path: Path) -> dict:
    out = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(out, dict)
    return out


def blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class Rank20V6StagedAuthorityTests(unittest.TestCase):
    def test_authority_binds_verified_claim_and_fixed_runtime(self):
        a = load(AUTH)
        self.assertEqual(a["slot_id"], SLOT)
        self.assertEqual(a["task_digest"], TASK)
        self.assertEqual(a["logical_attempt_id"], ATTEMPT)
        self.assertEqual(a["execution_claim_binding_digest"], CLAIM_DIGEST)
        self.assertEqual(a["claim_binding_git_blob_sha"], blob(CLAIM))
        self.assertEqual(a["claim_verification_git_blob_sha"], blob(VERIFY))
        self.assertEqual(a["start_cas_git_blob_sha"], "35cd4c7a31d5ffbafa755dcdf888c2dee1beeb1b")
        self.assertEqual(a["behavior_git_blob_sha"], "8c3d285161f356c9256375c9168e88cdaadd58e5")

    def test_staged_authority_is_not_effective(self):
        a = load(AUTH)
        self.assertTrue(a["execution_authority"])
        self.assertTrue(a["task_read_authority"])
        self.assertFalse(a["execution_authority_effective"])
        self.assertFalse(a["task_read_authority_effective"])
        self.assertFalse(a["activation_authority"])
        self.assertFalse(a["task_read"])
        self.assertFalse(a["task_started"])
        self.assertFalse(a["start_cas_acquired"])
        self.assertEqual(a["benchmark_trials_consumed"], 0)

    def test_ledger_binds_authority_and_freezes_at_public_reseal(self):
        l = load(LEDGER)
        self.assertEqual(l["staged_authority"]["git_blob_sha"], blob(AUTH))
        self.assertEqual(l["claim_binding"]["git_blob_sha"], blob(CLAIM))
        self.assertEqual(l["claim_verification"]["git_blob_sha"], blob(VERIFY))
        self.assertTrue(l["claim_verification"]["pass"])
        self.assertEqual(l["logical_attempt_id"], ATTEMPT)
        self.assertEqual(l["execution_claim_binding_digest"], CLAIM_DIGEST)
        self.assertTrue(l["scheduler"]["frozen"])
        self.assertEqual(
            l["scheduler"]["only_authorized_transition"],
            "PUBLIC_ZERO_EXPOSURE_RESEAL_AGAINST_V6_CANONICAL_AUTHORITY_AND_LEDGER",
        )
        self.assertFalse(l["execution_authority"])
        self.assertFalse(l["task_read_authority"])
        self.assertFalse(l["activation_authority"])

    def test_no_trial_or_credit_consumption(self):
        l = load(LEDGER)
        self.assertEqual(l["counts"]["benchmark_trials_consumed"], 18)
        self.assertEqual(l["rank20_benchmark_trials_consumed"], 0)
        self.assertFalse(l["rank20_task_read_history"])
        self.assertFalse(l["rank20_task_started"])
        self.assertFalse(l["rank20_start_cas_acquired"])
        self.assertEqual(l["acceptance_credit_delta"], 0)
        self.assertEqual(l["capability_credit_delta"], 0)
        self.assertEqual(l["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
