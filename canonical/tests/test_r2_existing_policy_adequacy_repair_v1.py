from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import r2_existing_policy_adequacy_repair_v1 as repair


class R2ExistingPolicyAdequacyRepairV1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "canonical/governance").mkdir(parents=True)
        (self.root / "canonical/verification").mkdir(parents=True)
        self.condition = {"op": "ATOM", "id": "x"}

    def tearDown(self):
        self.tmp.cleanup()

    def _request(self, existing=None):
        problem = {
            "decision_basis": ["x"],
            "policy_conditions": {"policy.p": self.condition},
        }
        if existing is not None:
            problem["policy_adequacy_bindings"] = existing
        return {
            "task_id": "t",
            "goal": "g",
            "decision_payload": {
                "context_id": "ctx",
                "bound_relevance_cegar_loop": {
                    "cegar_problem": problem,
                    "truth_payloads_by_discriminator_id": {},
                    "truth_payloads_by_predicate_id": {},
                    "source_positive_selection_contracts": {},
                },
            },
        }

    def _policy_request(self, artifact="POSITIVE_POLICY_ADEQUACY_CERTIFICATE"):
        return {
            "schema": "PROJECT_BRAIN_MINIMUM_POLICY_REPAIR_REQUEST_V1",
            "required_artifact": artifact,
        }

    def _write_evidence(self, condition=None):
        condition = condition or self.condition
        cert = self.root / "canonical/governance/policy.p.json"
        cert.write_text(
            json.dumps(
                {
                    "schema": repair.ADEQUACY_SCHEMA,
                    "policy_id": "policy.p",
                    "policy_condition_sha256": repair._condition_sha256(condition),
                    "adequacy_proved": True,
                    "brain_owned": True,
                    "load_bearing_constraints_preserved": True,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        cert_blob = repair._git_blob_sha(cert)
        verify = self.root / "canonical/verification/policy.p.json"
        verify.write_text(
            json.dumps(
                {
                    "schema": repair.VERIFY_SCHEMA,
                    "policy_id": "policy.p",
                    "subject_git_blob_sha": cert_blob,
                    "pass": True,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return cert, verify

    def test_exact_existing_certificate_is_discovered_as_request_patch_only(self):
        cert, verify = self._write_evidence()
        out = repair.repair(
            self._request(),
            self._policy_request(),
            repo_root=self.root,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["added_policy_ids"], ["policy.p"])
        binding = out["request_patch"]["decision_payload"][
            "bound_relevance_cegar_loop"
        ]["cegar_problem"]["policy_adequacy_bindings"]["policy.p"]
        self.assertEqual(
            binding["adequacy_certificate_path"],
            "canonical/governance/policy.p.json",
        )
        self.assertEqual(binding["adequacy_certificate_blob_sha"], repair._git_blob_sha(cert))
        self.assertEqual(
            binding["independent_verification_path"],
            "canonical/verification/policy.p.json",
        )
        self.assertEqual(binding["independent_verification_blob_sha"], repair._git_blob_sha(verify))
        self.assertFalse(out["policy_adequacy_authority"])
        self.assertTrue(out["downstream_reverification_required"])

    def test_wrong_policy_condition_is_not_reused(self):
        self._write_evidence(condition={"op": "NOT", "arg": self.condition})
        out = repair.repair(
            self._request(),
            self._policy_request(),
            repo_root=self.root,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_NEW_EXISTING_POLICY_ADEQUACY_BINDING_DISCOVERED",
        )

    def test_existing_binding_is_never_rewritten(self):
        self._write_evidence()
        existing = {
            "policy.p": {
                "adequacy_certificate_path": "canonical/governance/already.json"
            }
        }
        out = repair.repair(
            self._request(existing=existing),
            self._policy_request(),
            repo_root=self.root,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_NEW_EXISTING_POLICY_ADEQUACY_BINDING_DISCOVERED",
        )

    def test_symlinked_certificate_is_not_discovered(self):
        outside = self.root / "outside.json"
        outside.write_text(
            json.dumps(
                {
                    "schema": repair.ADEQUACY_SCHEMA,
                    "policy_id": "policy.p",
                    "policy_condition_sha256": repair._condition_sha256(self.condition),
                    "adequacy_proved": True,
                    "brain_owned": True,
                    "load_bearing_constraints_preserved": True,
                }
            ),
            encoding="utf-8",
        )
        link = self.root / "canonical/governance/policy.p.json"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable")
        out = repair.repair(
            self._request(),
            self._policy_request(),
            repo_root=self.root,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_NEW_EXISTING_POLICY_ADEQUACY_BINDING_DISCOVERED",
        )

    def test_unrelated_policy_gap_is_not_applicable(self):
        out = repair.repair(
            self._request(),
            self._policy_request("SOURCE_POSITIVE_SELECTION_CONTRACT"),
            repo_root=self.root,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "NOT_APPLICABLE__POLICY_ARTIFACT_NOT_REUSE_DISCOVERABLE",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
