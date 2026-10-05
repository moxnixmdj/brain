from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from canonical.runtime.confined_effect_broker_v1 import (
    ConfinedEffectError,
    REQUEST_SCHEMA,
    apply_request,
    docker_command,
    request_id_for,
    run_confined,
)


def request(target="proof/result.txt", text="ok\n", effect_type="write_text_artifact"):
    body = {
        "schema": REQUEST_SCHEMA,
        "effect_type": effect_type,
        "target": target,
        "payload": {"text": text},
        "guard_context": {"test": True},
    }
    body["request_id"] = request_id_for(body)
    return body


class ConfinedEffectBrokerTests(unittest.TestCase):
    def test_typed_broker_writes_only_under_output_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            response = apply_request(request("a/b.txt", "hello"), root)
            self.assertEqual(response["status"], "applied")
            self.assertEqual((root / "a/b.txt").read_text(), "hello")

    def test_path_escape_and_unknown_effect_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(ConfinedEffectError):
                apply_request(request("../escape.txt"), root)
            bad = request(effect_type="unknown")
            with self.assertRaises(ConfinedEffectError):
                apply_request(bad, root)

    def test_request_id_binds_effect_target_payload_and_guard_context(self):
        req = request()
        original = req["request_id"]
        req["payload"]["text"] = "tampered"
        self.assertNotEqual(request_id_for(req), original)
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ConfinedEffectError):
                apply_request(req, Path(td))

    def test_docker_command_has_required_confinement_and_no_output_mount(self):
        fake = Path("/tmp/brain-spool-test")
        cmd = docker_command(
            image_id="sha256:" + "a" * 64,
            repo_root=Path("/repo-source"),
            spool_root=fake,
            child_command=["python", "-V"],
        )
        joined = " ".join(cmd)
        self.assertIn("--network none", joined)
        self.assertIn("--read-only", cmd)
        self.assertIn("--cap-drop ALL", joined)
        self.assertIn("no-new-privileges:true", joined)
        self.assertIn("dst=/repo,readonly", joined)
        self.assertIn("dst=/broker", joined)
        self.assertNotIn("output", joined.lower())


@unittest.skipUnless(
    os.environ.get("PROJECT_BRAIN_RUN_DOCKER_ESCAPE_TEST") == "1",
    "docker escape test enabled only in dedicated verification job",
)
class DockerEscapeTests(unittest.TestCase):
    def test_direct_and_descendant_escape_blocked_broker_write_succeeds(self):
        image = os.environ["PROJECT_BRAIN_CONFINED_IMAGE"]
        repo_root = Path(__file__).resolve().parents[2]
        direct = repo_root / ".confined_effect_escape_probe"
        descendant = repo_root / ".confined_effect_descendant_escape"
        direct.unlink(missing_ok=True)
        descendant.unlink(missing_ok=True)
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "approved-output"
            result = run_confined(
                ["python", "/repo/canonical/tests/confined_effect_escape_probe_v1.py", "/broker"],
                output,
                image=image,
                timeout_s=45,
            )
            self.assertEqual(result["returncode"], 0, result["stderr"])
            lines = [json.loads(x) for x in result["stdout"].splitlines() if x.strip().startswith("{")]
            observation = next(x for x in lines if x.get("schema") == "PROJECT_BRAIN_CONFINED_EFFECT_ESCAPE_OBSERVATION_V1")
            self.assertTrue(observation["direct_repo_write_blocked"])
            self.assertTrue(observation["direct_network_blocked"])
            self.assertTrue(observation["descendant_repo_write_blocked"])
            self.assertTrue(observation["descendant_network_blocked"])
            self.assertEqual(result["broker_applied"], 1)
            self.assertEqual(result["broker_denied"], 0)
            self.assertEqual((output / "proof/approved.txt").read_text(), "broker-approved\n")
            self.assertFalse(result["output_root_mounted_into_child"])
        self.assertFalse(direct.exists())
        self.assertFalse(descendant.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
