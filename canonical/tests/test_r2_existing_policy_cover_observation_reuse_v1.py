from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import r2_existing_policy_cover_observation_reuse_v1 as reuse


class R2ExistingPolicyCoverObservationReuseV1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        (self.root/"canonical/governance").mkdir(parents=True)
        (self.root/"canonical/verification").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _request(self):
        return {
            "schema":"PROJECT_BRAIN_POLICY_COVER_OBSERVATION_REQUEST_V1",
            "state_id":"state-1",
            "discriminator_id":"disc-1",
            "surviving_world_ids":["w1","w2"],
            "observation_authority":False,
        }

    def _write_pair(self,name,outcome):
        receipt=self.root/f"canonical/governance/{name}.json"
        receipt.write_text(json.dumps({
            "schema":reuse.cover.OBSERVATION_SCHEMA,
            "state_id":"state-1",
            "discriminator_id":"disc-1",
            "outcome":outcome,
            "observation_proved":True,
            "truth_preserving":True,
            "safe_observation":True,
            "precommitment":True,
        },sort_keys=True),encoding="utf-8")
        receipt_blob=reuse._git_blob_sha(receipt)
        verification=self.root/f"canonical/verification/{name}.json"
        verification.write_text(json.dumps({
            "schema":reuse.cover.OBSERVATION_VERIFY_SCHEMA,
            "subject_git_blob_sha":receipt_blob,
            "state_id":"state-1",
            "discriminator_id":"disc-1",
            "outcome_sha256":reuse.cover._digest(outcome),
            "pass":True,
            "independent_verified":True,
            "observation_semantics_verified":True,
            "precommitment_verified":True,
            "independent_verifier_id":"test-independent",
        },sort_keys=True),encoding="utf-8")
        return receipt,verification

    def test_exact_authenticated_observation_is_discovered_for_reauthentication(self):
        receipt,verification=self._write_pair("obs-a","yes")
        out=reuse.discover(self._request(),repo_root=self.root)
        self.assertTrue(out["pass"],out)
        self.assertEqual(
            out["status"],
            "PASS__EXISTING_AUTHENTICATED_POLICY_COVER_OBSERVATION_REUSED",
        )
        self.assertEqual(
            out["observation_binding"]["receipt"]["path"],
            "canonical/governance/obs-a.json",
        )
        self.assertEqual(
            out["observation_binding"]["receipt"]["git_blob_sha"],
            reuse._git_blob_sha(receipt),
        )
        self.assertEqual(
            out["observation_binding"]["verification"]["git_blob_sha"],
            reuse._git_blob_sha(verification),
        )
        self.assertTrue(out["downstream_reauthentication_required"])
        self.assertFalse(out["semantic_truth_authority"])

    def test_conflicting_authenticated_outcomes_fail_closed(self):
        self._write_pair("obs-a","yes")
        self._write_pair("obs-b","no")
        out=reuse.discover(self._request(),repo_root=self.root)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "CONFLICTING_AUTHENTICATED_OBSERVATION_OUTCOMES",
        )

    def test_symlinked_receipt_is_not_reused(self):
        outside=self.root/"outside.json"
        outside.write_text(json.dumps({
            "schema":reuse.cover.OBSERVATION_SCHEMA,
            "state_id":"state-1",
            "discriminator_id":"disc-1",
            "outcome":"yes",
            "observation_proved":True,
            "truth_preserving":True,
            "safe_observation":True,
            "precommitment":True,
        }),encoding="utf-8")
        link=self.root/"canonical/governance/obs-link.json"
        try:
            link.symlink_to(outside)
        except (OSError,NotImplementedError):
            self.skipTest("symlink creation unavailable")
        out=reuse.discover(self._request(),repo_root=self.root)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_EXISTING_AUTHENTICATED_OBSERVATION_RECEIPT",
        )

    def test_wrong_discriminator_is_not_reused(self):
        self._write_pair("obs-a","yes")
        req=self._request()
        req["discriminator_id"]="disc-other"
        out=reuse.discover(req,repo_root=self.root)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_EXISTING_AUTHENTICATED_OBSERVATION_RECEIPT",
        )


if __name__=="__main__":
    unittest.main(verbosity=2)
