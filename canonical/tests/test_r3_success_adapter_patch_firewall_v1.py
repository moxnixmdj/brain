from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from canonical.runtime import r3_success_adapter_patch_firewall_v1 as firewall


OLD = "from __future__ import annotations\n\ndef adapt(request):\n    return None\n"
NEW = "from __future__ import annotations\n\ndef adapt(request):\n    return {'candidate_only': True}\n"


def digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


class R3SuccessAdapterPatchFirewallV1Tests(unittest.TestCase):
    def _repo(self, td: str) -> Path:
        root = Path(td)
        runtime = root / "canonical" / "runtime"
        runtime.mkdir(parents=True)
        (runtime / "r3_bound_success_adapter_v1.py").write_text(OLD, encoding="utf-8")
        (runtime / "r3_raw_success_adapter_v1.py").write_text(OLD, encoding="utf-8")
        for name in (
            "r3_independent_learning_verifier_v1.py",
            "r3_bound_success_checkpoint_verifier_v1.py",
            "r3_raw_success_checkpoint_verifier_v1.py",
        ):
            (runtime / name).write_text("# immutable\n", encoding="utf-8")
        return root

    def _candidate(self, **overrides):
        row = {
            "schema": "PROJECT_BRAIN_R3_SUCCESS_ADAPTER_PATCH_CANDIDATE_V1",
            "path": "canonical/runtime/r3_bound_success_adapter_v1.py",
            "base_sha256": digest(OLD),
            "content": NEW,
            "content_sha256": digest(NEW),
            "candidate_only": True,
            "verification_authority": False,
            "promotion_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
        }
        row.update(overrides)
        return row

    def test_valid_candidate_changes_only_adapter_and_grants_no_verifier_authority(self):
        with TemporaryDirectory() as td:
            root = self._repo(td)
            verifier = root / "canonical/runtime/r3_independent_learning_verifier_v1.py"
            verifier_before = verifier.read_bytes()
            out = firewall.apply_candidate(self._candidate(), repo_root=root)
            self.assertTrue(out["pass"], out)
            self.assertEqual(
                out["status"],
                "PASS__CANDIDATE_ADAPTER_PATCH_APPLIED__AWAITING_INDEPENDENT_VERIFICATION",
            )
            target = root / "canonical/runtime/r3_bound_success_adapter_v1.py"
            self.assertEqual(target.read_text(encoding="utf-8"), NEW)
            self.assertEqual(verifier.read_bytes(), verifier_before)
            self.assertTrue(out["source_patch_execution_authority"])
            self.assertFalse(out["verification_authority"])
            self.assertFalse(out["promotion_authority"])
            self.assertFalse(out["acceptance_authority"])
            self.assertFalse(out["terminal_authority"])
            self.assertTrue(out["independent_verification_required"])
            self.assertTrue(out["original_success_replay_required"])

    def test_verifier_path_is_never_a_patch_target(self):
        with TemporaryDirectory() as td:
            root = self._repo(td)
            out = firewall.validate_candidate(
                self._candidate(
                    path="canonical/runtime/r3_independent_learning_verifier_v1.py"
                ),
                repo_root=root,
            )
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "TARGET_PATH_OUTSIDE_SUCCESS_ADAPTER_ALLOWLIST")

    def test_authority_escalation_metadata_is_rejected(self):
        with TemporaryDirectory() as td:
            root = self._repo(td)
            out = firewall.validate_candidate(
                self._candidate(verification_authority=True),
                repo_root=root,
            )
            self.assertFalse(out["pass"])
            self.assertIn("CANDIDATE_AUTHORITY_FIREWALL_REQUIRED", out["reason"])

    def test_stale_base_is_rejected(self):
        with TemporaryDirectory() as td:
            root = self._repo(td)
            out = firewall.validate_candidate(
                self._candidate(base_sha256="0" * 64),
                repo_root=root,
            )
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "CANDIDATE_BASE_DRIFT")

    def test_invalid_python_is_rejected_before_write(self):
        with TemporaryDirectory() as td:
            root = self._repo(td)
            bad = "def adapt(:\n"
            out = firewall.apply_candidate(
                self._candidate(content=bad, content_sha256=digest(bad)),
                repo_root=root,
            )
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "CANDIDATE_SOURCE_SYNTAX_INVALID")
            target = root / "canonical/runtime/r3_bound_success_adapter_v1.py"
            self.assertEqual(target.read_text(encoding="utf-8"), OLD)

    def test_symlink_target_is_rejected(self):
        with TemporaryDirectory() as td:
            root = self._repo(td)
            target = root / "canonical/runtime/r3_bound_success_adapter_v1.py"
            real = root / "real_adapter.py"
            real.write_text(OLD, encoding="utf-8")
            target.unlink()
            target.symlink_to(real)
            out = firewall.validate_candidate(self._candidate(), repo_root=root)
            self.assertFalse(out["pass"])
            self.assertIn("TARGET_SYMLINK_FORBIDDEN", out["reason"])

    def test_target_change_after_validation_fails_without_overwrite(self):
        with TemporaryDirectory() as td:
            root = self._repo(td)
            candidate = self._candidate()
            validation = firewall.validate_candidate(candidate, repo_root=root)
            self.assertTrue(validation["pass"], validation)
            target = root / "canonical/runtime/r3_bound_success_adapter_v1.py"
            drift = OLD + "# drift\n"
            target.write_text(drift, encoding="utf-8")
            with patch.object(firewall, "validate_candidate", return_value=validation):
                out = firewall.apply_candidate(candidate, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "TARGET_CHANGED_AFTER_VALIDATION")
            self.assertEqual(target.read_text(encoding="utf-8"), drift)

    def test_verifier_change_after_validation_fails_before_write(self):
        with TemporaryDirectory() as td:
            root = self._repo(td)
            candidate = self._candidate()
            validation = firewall.validate_candidate(candidate, repo_root=root)
            verifier = root / "canonical/runtime/r3_independent_learning_verifier_v1.py"
            verifier.write_text("# externally drifted\n", encoding="utf-8")
            with patch.object(firewall, "validate_candidate", return_value=validation):
                out = firewall.apply_candidate(candidate, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertEqual(
                out["reason"],
                "VERIFICATION_AUTHORITY_CHANGED_AFTER_VALIDATION",
            )
            target = root / "canonical/runtime/r3_bound_success_adapter_v1.py"
            self.assertEqual(target.read_text(encoding="utf-8"), OLD)

    def test_verifier_change_during_write_rolls_target_back(self):
        with TemporaryDirectory() as td:
            root = self._repo(td)
            candidate = self._candidate()
            validation = firewall.validate_candidate(candidate, repo_root=root)
            before = dict(validation["verification_authority_snapshot"])
            after = dict(before)
            first = next(iter(after))
            after[first] = "f" * 64
            with patch.object(firewall, "validate_candidate", return_value=validation), patch.object(
                firewall,
                "_verification_snapshot",
                side_effect=[before, after],
            ):
                out = firewall.apply_candidate(candidate, repo_root=root)
            self.assertFalse(out["pass"])
            self.assertEqual(
                out["reason"],
                "VERIFICATION_AUTHORITY_CHANGED_DURING_PATCH",
            )
            self.assertTrue(out["target_rolled_back"])
            target = root / "canonical/runtime/r3_bound_success_adapter_v1.py"
            self.assertEqual(target.read_text(encoding="utf-8"), OLD)


if __name__ == "__main__":
    unittest.main(verbosity=2)
