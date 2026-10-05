import pathlib
import tempfile
import unittest

from canonical.runtime.zero_ambient_authority_launcher_v1 import (
    ConfinementError,
    canonical_policy,
    docker_argv,
    parse_effect_requests,
    policy_sha256,
)

IMAGE = "example.invalid/project/worker@sha256:" + "a" * 64


class Tests(unittest.TestCase):
    def policy(self, d):
        return {
            "image": IMAGE,
            "argv": ["python", "/input/worker.py"],
            "input_dir": str(d),
            "env": {"PYTHONDONTWRITEBYTECODE": "1"},
            "limits": {"pids": 32, "memory_mb": 512, "cpus": 1, "wallclock_s": 30, "scratch_mb": 64},
        }

    def test_hardening_flags_and_only_input_mount(self):
        with tempfile.TemporaryDirectory() as td:
            args = docker_argv(self.policy(td))
        joined = "\n".join(args)
        for token in [
            "--network=none", "--read-only", "--cap-drop=ALL",
            "--security-opt=no-new-privileges:true", "--user=65534:65534",
            "--ipc=private",
        ]:
            self.assertIn(token, args)
        mounts = [x for x in args if x.startswith("--mount=")]
        self.assertEqual(len(mounts), 1)
        self.assertIn("dst=/input,readonly", mounts[0])
        self.assertNotIn("/var/run/docker.sock", joined)

    def test_image_must_be_digest_pinned(self):
        with tempfile.TemporaryDirectory() as td:
            p = self.policy(td)
            p["image"] = "python:3.12"
            with self.assertRaisesRegex(ConfinementError, "IMAGE_MUST_BE_CONTENT_ADDRESSED"):
                canonical_policy(p)

    def test_environment_is_positive_allowlist(self):
        with tempfile.TemporaryDirectory() as td:
            p = self.policy(td)
            p["env"]["API_TOKEN"] = "secret"
            with self.assertRaisesRegex(ConfinementError, "ENV_NAME_NOT_ALLOWLISTED"):
                canonical_policy(p)

    def test_policy_hash_is_stable(self):
        with tempfile.TemporaryDirectory() as td:
            p = self.policy(td)
            self.assertEqual(policy_sha256(p), policy_sha256(dict(p)))

    def test_effect_protocol_ignores_ordinary_output(self):
        stdout = 'hello\nPROJECT_BRAIN_EFFECT_REQUEST_V1:{"type":"artifact_commit","request_id":"r1","payload_sha256":"x"}\n'
        reqs = parse_effect_requests(stdout)
        self.assertEqual(len(reqs), 1)
        self.assertEqual(reqs[0]["request_id"], "r1")

    def test_malformed_effect_request_fails_closed(self):
        with self.assertRaisesRegex(ConfinementError, "EFFECT_REQUEST_JSON_INVALID"):
            parse_effect_requests("PROJECT_BRAIN_EFFECT_REQUEST_V1:{broken")


if __name__ == "__main__":
    unittest.main(verbosity=2)
