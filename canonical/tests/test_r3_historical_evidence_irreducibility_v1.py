from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from canonical.runtime import r3_historical_evidence_irreducibility_v1 as cert


ROOT = Path(__file__).resolve().parents[2]


def state_doc(*, replay=False, proof=False, kind=cert.SUPPORTED_KIND):
    oid = "observation:test"
    wid = "work:test"
    replay_capsule = {"sha256": "a" * 64, "context": {"x": 1}} if replay else None
    proof_capsule = {"sha256": "b" * 64, "material": {"x": 1}} if proof else None
    return {
        "schema": "PROJECT_BRAIN_SELF_IMPROVEMENT_STATE_V1",
        "version": 1,
        "episodes": {},
        "skills": {},
        "pareto_frontiers": {},
        "failures": {},
        "reuse": {},
        "observations": {
            oid: {
                "observation_id": oid,
                "surface": "TEST",
                "schema": "TEST_SUCCESS",
                "status": "PASS__TEST",
                "output_sha256": "c" * 64,
                "replay_capsule_sha256": "a" * 64 if replay else None,
                "proof_capsule_sha256": "b" * 64 if proof else None,
                "replay_capsule": replay_capsule,
                "proof_capsule": proof_capsule,
            }
        },
        "improvement_queue": {
            wid: {
                "work_id": wid,
                "kind": kind,
                "status": "PENDING",
                "priority": 50,
                "payload": {
                    "observation_id": oid,
                    "replayable": replay,
                    "proof_available": proof,
                    "replay_capsule_sha256": "a" * 64 if replay else None,
                    "proof_capsule_sha256": "b" * 64 if proof else None,
                },
            }
        },
        "stats": {},
    }


class HistoricalEvidenceIrreducibilityTests(unittest.TestCase):
    def _run(self, doc):
        tmp_root = ROOT / "canonical" / "astra_runtime" / "tmp"
        tmp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp_root) as td:
            p = Path(td) / "state.json"
            p.write_text(json.dumps(doc) + "\n", encoding="utf-8")
            learning = SimpleNamespace(load_state=lambda path: doc)
            with patch.object(cert, "_learning_module", return_value=learning):
                return cert.certify("work:test", state_path=p, repo_root=ROOT)

    def test_exact_historical_missing_evidence_is_certified(self):
        out = self._run(state_doc())
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["irreducible_current_evidence_requirement_proved"])
        self.assertTrue(out["future_evidence_reopens"])
        self.assertFalse(out["permanent_nonlearnability_claimed"])
        self.assertFalse(out["global_external_information_absence_claimed"])
        self.assertEqual(
            out["required_new_information_class"],
            "NEW_INDEPENDENT_EVIDENCE_OR_NEW_REPLAYABLE_EXPERIENCE",
        )

    def test_replay_capsule_prevents_certificate(self):
        out = self._run(state_doc(replay=True))
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "CURRENT_RETAINED_EVIDENCE_NOT_PROVED_ABSENT")

    def test_proof_capsule_prevents_certificate(self):
        out = self._run(state_doc(proof=True))
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "CURRENT_RETAINED_EVIDENCE_NOT_PROVED_ABSENT")

    def test_wrong_work_kind_is_not_certified(self):
        out = self._run(state_doc(kind="VERIFY_EPISODE"))
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "WORK_KIND_NOT_SUPPORTED")

    def test_pending_set_requires_every_row_to_match_bounded_case(self):
        doc = state_doc()
        tmp_root = ROOT / "canonical" / "astra_runtime" / "tmp"
        tmp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp_root) as td:
            p = Path(td) / "state.json"
            p.write_text(json.dumps(doc) + "\n", encoding="utf-8")
            learning = SimpleNamespace(load_state=lambda path: doc)
            with patch.object(cert, "_learning_module", return_value=learning):
                good = cert.certify_pending_set(
                    [{"work_id": "work:test", "kind": cert.SUPPORTED_KIND}],
                    state_path=p,
                    repo_root=ROOT,
                )
                bad = cert.certify_pending_set(
                    [{"work_id": "work:test", "kind": "VERIFY_EPISODE"}],
                    state_path=p,
                    repo_root=ROOT,
                )
        self.assertTrue(good["pass"], good)
        self.assertEqual(good["certificate_count"], 1)
        self.assertFalse(bad["pass"])
        self.assertEqual(bad["reason"], "PENDING_SET_CONTAINS_UNSUPPORTED_KIND")


if __name__ == "__main__":
    unittest.main()
