from __future__ import annotations

from pathlib import Path
import unittest
from unittest import mock

from canonical.runtime import executable_skill_verification_authenticator_v1 as auth
from canonical.runtime.executable_skill_program_v7 import candidate_digest


class ExecutableSkillVerificationAuthenticatorV1Tests(unittest.TestCase):
    def candidate(self):
        steps = [{"index": 0, "op": "solve", "inputs": [], "outputs": ["goal"]}]
        source_ids = ["ep-a", "ep-b"]
        digest = candidate_digest(
            source_episode_ids=source_ids,
            steps=steps,
            preconditions=[],
            postconditions=["goal"],
            invalidators=[],
        )
        return {
            "schema": "PROJECT_BRAIN_EXECUTABLE_SKILL_PROGRAM_V7",
            "status": "EXECUTABLE_SKILL_CANDIDATE_ONLY",
            "source_episode_ids": source_ids,
            "source_episode_receipts": ["EPVR:a", "EPVR:b"],
            "source_scopes": ["scope"],
            "steps": steps,
            "preconditions": [],
            "postconditions": ["goal"],
            "invalidators": [],
            "candidate_sha256": digest,
            "verified_skill": False,
            "reuse_authorized": False,
            "candidate_only": True,
        }

    def resolver(self, candidate):
        receipt_sha = "1" * 40
        receipt = {
            "schema": auth.RECEIPT_SCHEMA,
            "candidate_sha256": candidate["candidate_sha256"],
            "source_episode_ids": candidate["source_episode_ids"],
            "scope_relation": "EXACT",
            "pass": True,
            "conclusion": "success",
            "exact_byte_bound": True,
            "behavior_preserving_on_claimed_scope": True,
        }
        verification = {
            "schema": auth.VERIFY_SCHEMA,
            "subject_git_blob_sha": receipt_sha,
            "candidate_sha256": candidate["candidate_sha256"],
            "source_episode_ids": candidate["source_episode_ids"],
            "scope_relation": "EXACT",
            "pass": True,
            "independent_verified": True,
            "exact_byte_bound": True,
            "behavior_preserving_on_claimed_scope": True,
            "candidate_reexecuted_or_equivalently_checked": True,
            "source_episode_lineage_reverified": True,
            "independent_verifier_id": "independent-test-verifier",
        }

        def resolve(ref, *, repo_root):
            path = str((ref or {}).get("path") or "")
            if path == "receipt.json":
                return {
                    "document": receipt,
                    "git_blob_sha": receipt_sha,
                    "path": path,
                }
            if path == "verification.json":
                return {
                    "document": verification,
                    "git_blob_sha": "2" * 40,
                    "path": path,
                }
            raise AssertionError("unexpected receipt ref: " + path)

        return resolve

    def test_authenticated_skill_carries_durable_content_addressed_binding(self):
        candidate = self.candidate()
        binding = {
            "receipt": {"path": "receipt.json"},
            "verification": {"path": "verification.json"},
        }
        with mock.patch.object(
            auth,
            "resolve_receipt_bytes",
            side_effect=self.resolver(candidate),
        ):
            out = auth.authenticate_and_verify(
                candidate,
                binding,
                repo_root=Path("."),
            )

        self.assertTrue(out["pass"], out)
        skill = out["verified_skill"]
        self.assertTrue(skill["verified_skill"])
        self.assertTrue(skill["reuse_authorized"])
        self.assertEqual(
            skill["verification_binding"]["receipt"]["git_blob_sha"],
            "1" * 40,
        )
        self.assertEqual(
            skill["verification_binding"]["verification"]["git_blob_sha"],
            "2" * 40,
        )
        self.assertEqual(
            skill["independent_verifier_id"],
            "independent-test-verifier",
        )

    def test_durable_verified_skill_reauthenticates_and_tampering_fails_closed(self):
        candidate = self.candidate()
        binding = {
            "receipt": {"path": "receipt.json"},
            "verification": {"path": "verification.json"},
        }
        resolver = self.resolver(candidate)
        with mock.patch.object(auth, "resolve_receipt_bytes", side_effect=resolver):
            issued = auth.authenticate_and_verify(
                candidate,
                binding,
                repo_root=Path("."),
            )
            self.assertTrue(issued["pass"], issued)
            skill = issued["verified_skill"]
            rechecked = auth.reauthenticate_record(skill, repo_root=Path("."))
            self.assertTrue(rechecked["pass"], rechecked)

            tampered = dict(skill)
            tampered["postconditions"] = ["different-goal"]
            rejected = auth.reauthenticate_record(
                tampered,
                repo_root=Path("."),
            )

        self.assertFalse(rejected["pass"], rejected)
        self.assertIn(
            "CANDIDATE_DIGEST_INVALID",
            rejected["reason"],
        )

    def test_legacy_verified_skill_without_binding_is_not_reauthenticatable(self):
        candidate = self.candidate()
        legacy = {
            **candidate,
            "verified_skill": True,
            "reuse_authorized": True,
            "candidate_only": False,
            "scope_relation": "EXACT",
            "scope_predicate": None,
            "verification_receipt": "SKVR:legacy",
        }
        out = auth.reauthenticate_record(legacy, repo_root=Path("."))
        self.assertFalse(out["pass"], out)
        self.assertIn("VERIFIED_SKILL_RECORD_BINDING_MISSING", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
