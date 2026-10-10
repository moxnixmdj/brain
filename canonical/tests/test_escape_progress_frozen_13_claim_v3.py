from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from canonical.runtime.coverage_claim_scope_guard_v1 import validate_claim

ROOT = Path(__file__).resolve().parents[2]
CLAIM_PATH = ROOT / "canonical/governance/ESCAPE_PROGRESS_TOTALITY_FROZEN_13_CLAIM_20261010_V3.json"
MISSION_PATH = ROOT / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json"


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def canon_sha(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


class EscapeProgressFrozen13ClaimV3Tests(unittest.TestCase):
    def setUp(self):
        self.claim = json.loads(CLAIM_PATH.read_text(encoding="utf-8"))

    def test_current_mission_binding_and_claim_id(self):
        mission_sha = blob_sha(MISSION_PATH)
        out = validate_claim(self.claim, current_mission_blob_sha=mission_sha)
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            self.claim["claim_id"],
            "d8dec5e454c4cbae50de7a0b23f0cf220e4caeb1c1b620e40dd53c267da1ae28",
        )
        self.assertEqual(self.claim["mission_blob_sha"], mission_sha)

    def test_scope_target_and_semantics_digests(self):
        self.assertEqual(canon_sha(self.claim["scope"]), self.claim["scope_sha256"])
        self.assertEqual(
            canon_sha(self.claim["target_predicate"]),
            self.claim["target_predicate_sha256"],
        )
        self.assertEqual(
            canon_sha(self.claim["semantics"]),
            self.claim["semantics_sha256"],
        )

    def test_content_addressed_dependencies_and_exact_obligations(self):
        for key in ("mission_pointer", "quotient", "adaptive_theorem"):
            ref = self.claim["source_bindings"][key]
            path = ROOT / ref["path"]
            self.assertTrue(path.is_file(), ref)
            self.assertEqual(blob_sha(path), ref["git_blob_sha"], ref)
        quotient = json.loads(
            (ROOT / self.claim["scope"]["quotient_path"]).read_text(encoding="utf-8")
        )
        self.assertEqual(
            self.claim["scope"]["obligation_ids"],
            quotient["independent_open_obligations"],
        )

    def test_zero_credit_and_no_root_claim(self):
        self.assertEqual(self.claim["terminal_credit_delta"], 0)
        self.assertIn("NO_ROOT_CERTIFICATE_PROVED", self.claim["hard_nonclaims"])
        self.assertIn("NO_TERMINAL_CREDIT", self.claim["hard_nonclaims"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
