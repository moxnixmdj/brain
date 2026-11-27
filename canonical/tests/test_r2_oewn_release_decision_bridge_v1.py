from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import r2_oewn_release_decision_bridge_v1 as bridge
from canonical.runtime import unified_cognitive_fabric_v1 as fabric


def universe(*, sense_count: int = 2) -> dict:
    senses = [
        {
            "sense_id": "margin%1:21:00::",
            "synset_id": "13281661-n",
            "part_of_speech": "n",
        },
        {
            "sense_id": "margin%1:21:01::",
            "synset_id": "13372293-n",
            "part_of_speech": "n",
        },
    ][:sense_count]
    return {
        "schema": bridge.release.SCHEMA,
        "status": "PASS__OEWN_2025_RELEASE_RELATIVE_SENSE_UNIVERSE_ENUMERATED",
        "pass": True,
        "release_id": bridge.release.RELEASE_ID,
        "archive_sha256": bridge.release.RELEASE_SHA256,
        "lemma": "margin",
        "requested_part_of_speech": "n",
        "sense_count": len(senses),
        "senses": senses,
        "release_relative_absence": sense_count == 0,
        "candidate_set_complete_relative_to_release": True,
        "open_world_english_sense_completeness_claimed": False,
    }


class R2OEWNReleaseDecisionBridgeV1Tests(unittest.TestCase):
    def _root_with_archive(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        archive = root / "canonical" / "evidence" / "oewn-2025.zip"
        archive.parent.mkdir(parents=True)
        archive.write_bytes(b"test-archive-placeholder")
        return tmp, root, archive

    def test_rejects_repository_escape_before_enumeration(self):
        with tempfile.TemporaryDirectory() as td, patch.object(
            bridge.release, "enumerate_senses"
        ) as enum:
            out = bridge.resolve(
                {
                    "oewn_release_archive_path": "../secret.zip",
                    "lemma": "margin",
                    "part_of_speech": "n",
                    "decision_manifest": {},
                },
                repo_root=td,
            )
        self.assertFalse(out["pass"])
        self.assertIn("MUST_BE_REPOSITORY_RELATIVE", out["reason"])
        enum.assert_not_called()

    def test_failed_release_enumeration_never_reaches_decision_control(self):
        tmp, root, _ = self._root_with_archive()
        self.addCleanup(tmp.cleanup)
        failed = {
            "schema": bridge.release.SCHEMA,
            "status": "FAIL_CLOSED__OEWN_2025_RELEASE_HASH_MISMATCH",
            "pass": False,
        }
        with patch.object(
            bridge.release, "enumerate_senses", return_value=failed
        ), patch.object(bridge.decision, "resolve") as resolve:
            out = bridge.resolve(
                {
                    "oewn_release_archive_path": "canonical/evidence/oewn-2025.zip",
                    "lemma": "margin",
                    "part_of_speech": "n",
                    "decision_manifest": {},
                },
                repo_root=root,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], failed["status"])
        resolve.assert_not_called()

    def test_release_relative_absence_stays_open_not_false(self):
        tmp, root, _ = self._root_with_archive()
        self.addCleanup(tmp.cleanup)
        empty = universe(sense_count=0)
        empty["status"] = "PASS__LEMMA_OR_POS_ABSENT_FROM_OEWN_2025_RELEASE"
        with patch.object(
            bridge.release, "enumerate_senses", return_value=empty
        ), patch.object(bridge.decision, "resolve") as resolve:
            out = bridge.resolve(
                {
                    "oewn_release_archive_path": "canonical/evidence/oewn-2025.zip",
                    "lemma": "nonexistent",
                    "part_of_speech": "n",
                    "decision_manifest": {},
                },
                repo_root=root,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__LEMMA_OR_POS_ABSENT_FROM_EXACT_OEWN_2025_RELEASE",
        )
        self.assertTrue(
            out["candidate_sense_set_complete_relative_to_oewn_release"]
        )
        self.assertFalse(out["open_world_english_sense_completeness_claimed"])
        resolve.assert_not_called()

    def test_composes_complete_release_universe_into_existing_authority_gate(self):
        tmp, root, _ = self._root_with_archive()
        self.addCleanup(tmp.cleanup)
        u = universe()
        controlled = {
            "schema": bridge.decision.SCHEMA,
            "status": "PASS__OEWN_SENSE_AMBIGUITY_DECISION_SUFFICIENT",
            "pass": True,
            "decision_sufficient": True,
            "intended_sense_identified": False,
            "semantic_truth_authority": False,
            "terminal_authority": False,
        }
        manifest = {"schema": bridge.decision.MANIFEST_SCHEMA}
        authority_receipt = {"receipt": "authority"}
        evidence_receipts = [{"receipt": "evidence"}]
        authority_verifier = lambda value: value
        evidence_verifier = lambda value: value

        with patch.object(
            bridge.release, "enumerate_senses", return_value=u
        ) as enum, patch.object(
            bridge.decision, "resolve", return_value=controlled
        ) as resolve:
            out = bridge.resolve(
                {
                    "oewn_release_archive_path": "canonical/evidence/oewn-2025.zip",
                    "lemma": "margin",
                    "part_of_speech": "n",
                    "decision_manifest": manifest,
                    "authority_receipt": authority_receipt,
                    "evidence_receipts": evidence_receipts,
                    "ambiguity_owner": "SYSTEM_MODEL",
                },
                repo_root=root,
                authority_verifier=authority_verifier,
                evidence_verifier=evidence_verifier,
            )

        self.assertTrue(out["pass"], out)
        self.assertTrue(
            out["candidate_sense_set_complete_relative_to_oewn_release"]
        )
        self.assertFalse(out["intended_sense_identified"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["terminal_authority"])
        enum.assert_called_once()
        kwargs = resolve.call_args.kwargs
        self.assertEqual(kwargs["sense_universe"], u)
        self.assertEqual(kwargs["decision_manifest"], manifest)
        self.assertIs(kwargs["authority_verifier"], authority_verifier)
        self.assertIs(kwargs["evidence_verifier"], evidence_verifier)

    def test_fabric_auto_routes_release_plus_manifest_to_bridge(self):
        payload = {
            "oewn_release_archive_path": "canonical/evidence/oewn-2025.zip",
            "lemma": "margin",
            "part_of_speech": "n",
            "decision_manifest": {"schema": bridge.decision.MANIFEST_SCHEMA},
        }
        inner = {
            "schema": bridge.SCHEMA,
            "status": "OPEN__AUTHENTICATED_OEWN_DECISION_MANIFEST_REQUIRED",
            "pass": False,
            "terminal_authority": False,
        }
        with patch.object(
            fabric.oewn_release_decision, "resolve", return_value=inner
        ) as resolver:
            out = fabric.run({"payload": payload})
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "OEWN_RELEASE_DECISION_SENSE")
        self.assertEqual(
            out["engine"],
            "r2_oewn_release_decision_bridge_v1.resolve",
        )
        self.assertEqual(out["result"], inner)
        resolver.assert_called_once()

    def test_catalog_exposes_release_decision_composition(self):
        catalog = fabric.catalog()
        self.assertIn("OEWN_RELEASE_DECISION_SENSE", catalog["engines"])
        self.assertEqual(
            catalog["engines"]["OEWN_RELEASE_DECISION_SENSE"],
            "r2_oewn_release_decision_bridge_v1.resolve",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
