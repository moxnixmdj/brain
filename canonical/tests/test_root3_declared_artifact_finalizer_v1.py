from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime.root3_declared_artifact_finalizer_v1 import (
    ArtifactFinalizeDenied,
    build_plan,
    commit,
    effect_request,
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class DeclaredArtifactFinalizerTests(unittest.TestCase):
    def make_root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "canonical/astra_runtime/artifacts").mkdir(parents=True)
        return td, root

    def plan(self, payload=b"artifact-bytes\n", expected="ABSENT"):
        return build_plan(
            mission_id="m1",
            capsule_head_sha256="c" * 64,
            action_ref="artifact:case1",
            destination_path="canonical/astra_runtime/artifacts/out.bin",
            payload=payload,
            expected_pre_sha256=expected,
            content_type="application/octet-stream",
            producer_sha256="p".replace("p", "a") * 64,
            toolchain_sha256="b" * 64,
        )

    def final_allow(self, request):
        return {
            "allowed": True,
            "status": "ALLOW_FINAL_AUTHORIZATION",
            "request_sha256": request["request_sha256"],
            "effect_kind": "FINAL_OUTPUT",
            "resource": request["resource"],
            "operation": "replace",
            "payload_sha256": request["payload_sha256"],
        }

    def test_current_empty_semantic_registry_denies_without_mutation(self):
        td, root = self.make_root()
        try:
            payload = b"artifact-bytes\n"
            plan = self.plan(payload)
            target = root / "canonical/astra_runtime/artifacts/out.bin"
            with self.assertRaisesRegex(ArtifactFinalizeDenied, "FINAL_AUTHORIZATION_DENIED"):
                commit(root, plan, payload, {"placeholder": True})
            self.assertFalse(target.exists())
        finally:
            td.cleanup()

    def test_mocked_exact_final_allow_commits_and_reads_back(self):
        td, root = self.make_root()
        try:
            payload = b"artifact-bytes\n"
            plan = self.plan(payload)
            request = effect_request(plan, payload)
            with patch(
                "canonical.runtime.root3_declared_artifact_finalizer_v1.authorize_effect",
                return_value=self.final_allow(request),
            ):
                receipt = commit(root, plan, payload, {"placeholder": True})
            target = root / "canonical/astra_runtime/artifacts/out.bin"
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(receipt["post_sha256"], sha(payload))
            self.assertTrue(receipt["atomic_replace"])
            self.assertTrue(receipt["exact_readback"])
        finally:
            td.cleanup()

    def test_payload_tamper_denies_before_mutation(self):
        td, root = self.make_root()
        try:
            plan = self.plan(b"good\n")
            with self.assertRaisesRegex(ArtifactFinalizeDenied, "PLAN_OR_PAYLOAD_MISMATCH"):
                commit(root, plan, b"evil\n", {"placeholder": True})
            self.assertFalse((root / "canonical/astra_runtime/artifacts/out.bin").exists())
        finally:
            td.cleanup()

    def test_stale_prestate_denies_before_authorizer(self):
        td, root = self.make_root()
        try:
            target = root / "canonical/astra_runtime/artifacts/out.bin"
            target.write_bytes(b"old\n")
            plan = self.plan(b"new\n", expected="ABSENT")
            with patch(
                "canonical.runtime.root3_declared_artifact_finalizer_v1.authorize_effect"
            ) as auth:
                with self.assertRaisesRegex(ArtifactFinalizeDenied, "PRESTATE_MISMATCH"):
                    commit(root, plan, b"new\n", {"placeholder": True})
                auth.assert_not_called()
            self.assertEqual(target.read_bytes(), b"old\n")
        finally:
            td.cleanup()

    def test_path_escape_rejected(self):
        with self.assertRaisesRegex(ArtifactFinalizeDenied, "DESTINATION_PATH_NOT_ALLOWED"):
            build_plan(
                mission_id="m1",
                capsule_head_sha256="c" * 64,
                action_ref="artifact:case1",
                destination_path="canonical/astra_runtime/artifacts/../state/pwn.json",
                payload=b"x\n",
                expected_pre_sha256="ABSENT",
                content_type="application/octet-stream",
                producer_sha256="a" * 64,
                toolchain_sha256="b" * 64,
            )

    def test_symlink_target_rejected(self):
        td, root = self.make_root()
        try:
            outside = root / "outside"
            outside.write_bytes(b"x")
            target = root / "canonical/astra_runtime/artifacts/out.bin"
            target.symlink_to(outside)
            plan = self.plan(b"new\n")
            with self.assertRaisesRegex(ArtifactFinalizeDenied, "TARGET_SYMLINK_DENIED"):
                commit(root, plan, b"new\n", {"placeholder": True})
            self.assertEqual(outside.read_bytes(), b"x")
        finally:
            td.cleanup()

    def test_final_authorization_must_bind_exact_request(self):
        td, root = self.make_root()
        try:
            payload = b"artifact-bytes\n"
            plan = self.plan(payload)
            request = effect_request(plan, payload)
            forged = self.final_allow(request)
            forged["payload_sha256"] = "0" * 64
            with patch(
                "canonical.runtime.root3_declared_artifact_finalizer_v1.authorize_effect",
                return_value=forged,
            ):
                with self.assertRaisesRegex(ArtifactFinalizeDenied, "FINAL_AUTHORIZATION_DENIED"):
                    commit(root, plan, payload, {"placeholder": True})
            self.assertFalse((root / "canonical/astra_runtime/artifacts/out.bin").exists())
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
