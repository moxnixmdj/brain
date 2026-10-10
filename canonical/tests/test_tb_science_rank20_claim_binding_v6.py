from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAIM_PATH = ROOT / "canonical/governance/TB_SCIENCE_RANK20_LOGICAL_ATTEMPT_CLAIM_BINDING_20261010_V6.json"
V5_PATH = ROOT / "canonical/governance/TB_SCIENCE_RANK20_LOGICAL_ATTEMPT_CLAIM_BINDING_20261010_V5.json"
LEDGER_PATH = ROOT / "canonical/governance/TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261010_V50.json"
ABORT_PATH = ROOT / "canonical/verification/TB_SCIENCE_RANK20_V2_START_CAS_IMPORT_ABORT_TRUTH_20261010_V1.json"

EXPECTED_CLAIM_DIGEST = "sha256:3c4801910a41d14fc31bc7ec5e4b0f3467154aed5e8ac914f727cb6773d10860"
EXPECTED_ATTEMPT_ID = "f3d4e55a96b3d2dddb85e4f3c5e085d83ab9f7e6c186bba00b0146a528f339b7"
OLD_CLAIM_DIGEST = "sha256:aa0d91d18bb597319414b7385a92248992c093e14bf9c8f5677b72c05cb09beb"
OLD_ATTEMPT_ID = "c7a02ecc6b11f4338120f05cd922370d361ce79e104549f95b656df3b51cb2bb"


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _canon(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canon(value)).hexdigest()


def _git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _attempt(slot_id: str, task_digest: str, claim_digest: str) -> str:
    material = {
        "schema": "PROJECT_BRAIN_LOGICAL_ATTEMPT_IDENTITY_V2",
        "slot_id": slot_id,
        "task_digest": task_digest,
        "execution_claim_binding_digest": claim_digest,
    }
    return hashlib.sha256(_canon(material)).hexdigest()


class Rank20ClaimBindingV6Tests(unittest.TestCase):
    def test_exact_new_claim_digest_and_attempt_identity(self):
        claim = _load(CLAIM_PATH)
        digest = _sha256(claim)
        self.assertEqual(digest, EXPECTED_CLAIM_DIGEST)
        attempt = _attempt(claim["slot_id"], claim["task_digest"], digest)
        self.assertEqual(attempt, EXPECTED_ATTEMPT_ID)
        self.assertNotEqual(digest, OLD_CLAIM_DIGEST)
        self.assertNotEqual(attempt, OLD_ATTEMPT_ID)

    def test_supersedes_exact_v5_and_binds_current_abort_truth(self):
        claim = _load(CLAIM_PATH)
        self.assertEqual(claim["supersedes_git_blob_sha"], _git_blob(V5_PATH))
        self.assertEqual(claim["preclaim_ledger_blob"], _git_blob(LEDGER_PATH))
        self.assertEqual(claim["predecessor_result_truth_blob"], _git_blob(ABORT_PATH))
        abort = _load(ABORT_PATH)
        self.assertEqual(abort["failure"]["root_class"], "START_CAS_IMPORT_PATH_DEFECT")
        self.assertFalse(abort["accounting"]["task_read"])
        self.assertFalse(abort["accounting"]["task_started"])
        self.assertEqual(abort["accounting"]["benchmark_trials_consumed"], 0)

    def test_reuses_verified_fixed_behavior_without_reauthorizing_execution(self):
        claim = _load(CLAIM_PATH)
        self.assertEqual(claim["behavior_blob"], "8c3d285161f356c9256375c9168e88cdaadd58e5")
        self.assertEqual(claim["workflow_blob"], "e4cb372e501790fd9ed5aa72193d18109a599102")
        self.assertEqual(claim["zero_exposure_test_blob"], "ba2d467c54a9f9720bc1b647befe655b80555fab")
        self.assertEqual(claim["execution_branch"], "execute/tb-science-rank20-20261010-v2")
        self.assertEqual(claim["activation_filename"], "ACTIVATE_RANK20_V2_PR.json")
        self.assertNotIn("execution_authority", claim)
        self.assertNotIn("activation_authority", claim)
        self.assertNotIn("acceptance_credit_delta", claim)
        self.assertNotIn("terminal_credit_delta", claim)


if __name__ == "__main__":
    unittest.main(verbosity=2)
