import pathlib
import tempfile
import unittest

from canonical.runtime.zero_ambient_authority_launcher_v2 import (
    ConfinementError,
    canonical_policy,
    docker_argv,
)

IMAGE = "example.invalid/project/worker@sha256:" + "a" * 64


def policy(input_dir):
    return {
        "image": IMAGE,
        "argv": ["python", "/input/worker.py"],
        "input_dir": str(input_dir),
        "env": {"PYTHONDONTWRITEBYTECODE": "1"},
        "limits": {
            "pids": 32,
            "memory_mb": 512,
            "cpus": 1,
            "wallclock_s": 30,
            "scratch_mb": 64,
        },
    }


class Tests(unittest.TestCase):
    def test_filesystem_root_cannot_be_trusted_input_root(self):
        with self.assertRaisesRegex(
            ConfinementError, "TRUSTED_INPUT_ROOT_MUST_NOT_BE_FILESYSTEM_ROOT"
        ):
            canonical_policy(policy("/"), trusted_input_root=pathlib.Path("/"))

    def test_input_outside_trusted_root_fails_closed(self):
        with tempfile.TemporaryDirectory() as trusted, tempfile.TemporaryDirectory() as outside:
            with self.assertRaisesRegex(ConfinementError, "INPUT_DIR_OUTSIDE_TRUSTED_ROOT"):
                canonical_policy(policy(outside), trusted_input_root=trusted)

    def test_nested_input_inside_trusted_root_passes(self):
        with tempfile.TemporaryDirectory() as trusted:
            nested = pathlib.Path(trusted) / "bundle"
            nested.mkdir()
            out = canonical_policy(policy(nested), trusted_input_root=trusted)
            self.assertEqual(out["input_dir"], str(nested.resolve()))
            self.assertTrue(out["host_input_disclosure_boundary_enforced"])

    def test_emitted_bind_is_the_checked_nested_directory(self):
        with tempfile.TemporaryDirectory() as trusted:
            nested = pathlib.Path(trusted) / "bundle"
            nested.mkdir()
            args = docker_argv(policy(nested), trusted_input_root=trusted)
            mounts = [x for x in args if x.startswith("--mount=")]
            self.assertEqual(len(mounts), 1)
            self.assertIn("src=" + str(nested.resolve()), mounts[0])
            self.assertIn("dst=/input,readonly", mounts[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
