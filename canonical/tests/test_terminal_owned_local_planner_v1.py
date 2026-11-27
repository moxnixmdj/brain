from __future__ import annotations

import ast
import hashlib
import io
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from canonical.runtime import astra_runtime


ROOT = pathlib.Path(__file__).resolve().parents[2]
HARBOR = ROOT / "canonical/runtime/harbor_brain_agent.py"


class _FakeHTTPResponse:
    def __init__(self, payload):
        self._body = io.BytesIO(json.dumps(payload).encode("utf-8"))

    def read(self, n=-1):
        return self._body.read(n)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TerminalOwnedLocalPlannerTests(unittest.TestCase):
    def setUp(self):
        self.old_env = {
            key: os.environ.get(key)
            for key in (
                "PROJECT_BRAIN_TERMINAL_LOCAL_MODEL_PATH",
                "PROJECT_BRAIN_TERMINAL_LLAMA_CPP_DIR",
                "PROJECT_BRAIN_TERMINAL_LOCAL_PLANNER_SERVER",
                "PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR",
            )
        }
        self.old_cache = astra_runtime._TERMINAL_LOCAL_SUBSTRATE_CACHE
        self.old_sha = astra_runtime.TERMINAL_OWNED_MODEL_SHA256
        self.old_bytes = astra_runtime.TERMINAL_OWNED_MODEL_BYTES
        self.old_commit = astra_runtime.TERMINAL_OWNED_LLAMA_CPP_COMMIT

    def tearDown(self):
        for key, value in self.old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        astra_runtime._TERMINAL_LOCAL_SUBSTRATE_CACHE = self.old_cache
        astra_runtime.TERMINAL_OWNED_MODEL_SHA256 = self.old_sha
        astra_runtime.TERMINAL_OWNED_MODEL_BYTES = self.old_bytes
        astra_runtime.TERMINAL_OWNED_LLAMA_CPP_COMMIT = self.old_commit

    @staticmethod
    def _fake_git_repo(path: pathlib.Path, commit: str):
        git = path / ".git"
        (git / "refs/heads").mkdir(parents=True)
        (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
        (git / "refs/heads/main").write_text(commit + "\n", encoding="utf-8")

    def _bind_tiny_owned_substrate(self, td: str):
        root = pathlib.Path(td)
        model = root / "model.gguf"
        payload = b"owned-local-model-fixture"
        model.write_bytes(payload)
        llama = root / "llama.cpp"
        llama.mkdir()
        commit = "1" * 40
        self._fake_git_repo(llama, commit)

        astra_runtime.TERMINAL_OWNED_MODEL_SHA256 = hashlib.sha256(payload).hexdigest()
        astra_runtime.TERMINAL_OWNED_MODEL_BYTES = len(payload)
        astra_runtime.TERMINAL_OWNED_LLAMA_CPP_COMMIT = commit
        astra_runtime._TERMINAL_LOCAL_SUBSTRATE_CACHE = None
        os.environ["PROJECT_BRAIN_TERMINAL_LOCAL_MODEL_PATH"] = str(model)
        os.environ["PROJECT_BRAIN_TERMINAL_LLAMA_CPP_DIR"] = str(llama)
        return model, llama

    def test_runtime_verifies_local_model_bytes_and_git_revision(self):
        with tempfile.TemporaryDirectory() as td:
            self._bind_tiny_owned_substrate(td)
            got = astra_runtime._terminal_local_substrate_identity()
            self.assertEqual(got["model_sha256"], astra_runtime.TERMINAL_OWNED_MODEL_SHA256)
            self.assertEqual(got["model_bytes"], astra_runtime.TERMINAL_OWNED_MODEL_BYTES)
            self.assertEqual(got["llama_cpp_commit"], astra_runtime.TERMINAL_OWNED_LLAMA_CPP_COMMIT)

    def test_wrong_model_hash_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            model, _ = self._bind_tiny_owned_substrate(td)
            model.write_bytes(b"tampered")
            astra_runtime._TERMINAL_LOCAL_SUBSTRATE_CACHE = None
            with self.assertRaisesRegex(astra_runtime.Blocker, "MODEL_(BYTES|SHA256)_MISMATCH"):
                astra_runtime._terminal_local_substrate_identity()

    def test_wrong_llama_revision_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            _, llama = self._bind_tiny_owned_substrate(td)
            (llama / ".git/refs/heads/main").write_text("2" * 40 + "\n", encoding="utf-8")
            astra_runtime._TERMINAL_LOCAL_SUBSTRATE_CACHE = None
            with self.assertRaisesRegex(astra_runtime.Blocker, "LLAMA_CPP_REVISION_MISMATCH"):
                astra_runtime._terminal_local_substrate_identity()

    def test_non_loopback_terminal_server_is_rejected(self):
        os.environ["PROJECT_BRAIN_TERMINAL_LOCAL_PLANNER_SERVER"] = "https://text.pollinations.ai/"
        with self.assertRaisesRegex(astra_runtime.Blocker, "SERVER_NOT_LOOPBACK"):
            astra_runtime._terminal_owned_planner_server_url()

    def test_terminal_planner_bypasses_generic_external_bridge(self):
        response = {
            "choices": [{"message": {"content": '{"actions":[{"type":"finish","args":{"summary":"ok"}}]}'}}],
        }
        identity = {
            "model": astra_runtime.TERMINAL_OWNED_PLANNER_MODEL,
            "backend": astra_runtime.TERMINAL_OWNED_PLANNER_BACKEND,
            "model_sha256": astra_runtime.TERMINAL_OWNED_MODEL_SHA256,
            "model_bytes": astra_runtime.TERMINAL_OWNED_MODEL_BYTES,
            "llama_cpp_commit": astra_runtime.TERMINAL_OWNED_LLAMA_CPP_COMMIT,
        }
        os.environ["PROJECT_BRAIN_TERMINAL_LOCAL_PLANNER_SERVER"] = "http://127.0.0.1:8080"
        os.environ["PROJECT_BRAIN_EXTERNAL_TOOL_BRIDGE_DIR"] = "/definitely/not/used"
        with (
            mock.patch.object(astra_runtime, "_terminal_local_substrate_identity", return_value=identity),
            mock.patch.object(
                astra_runtime,
                "_external_tool_bridge",
                side_effect=AssertionError("generic bridge must not be used by terminal planner"),
            ),
            mock.patch.object(
                astra_runtime,
                "_ORIGINAL_URLOPEN",
                return_value=_FakeHTTPResponse(response),
            ) as urlopen,
        ):
            got = astra_runtime._terminal_owned_planner_post("test", timeout_s=3)
        self.assertEqual(got["transport"], "BRAIN_OWNED_LOOPBACK_LLAMA_CPP_V1")
        self.assertEqual(got["model_sha256"], astra_runtime.TERMINAL_OWNED_MODEL_SHA256)
        called_url = urlopen.call_args.args[0].full_url
        self.assertTrue(called_url.startswith("http://127.0.0.1:8080/"))

    def test_harbor_uses_terminal_owned_planner_only(self):
        tree = ast.parse(HARBOR.read_text(encoding="utf-8"))
        attrs = [
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name) and node.func.value.id == "astra_runtime"
        ]
        self.assertIn("_terminal_owned_planner_post", attrs)
        self.assertNotIn("_planner_post", attrs)

    def test_harbor_reports_owned_not_unowned_model_dependency(self):
        text = HARBOR.read_text(encoding="utf-8")
        self.assertNotIn("BRAIN_OWNED_CONTROL__OPTIONAL_MODEL_PROPOSAL", text)
        self.assertGreaterEqual(text.count('"owned_model_dependency_count":1'), 2)
        self.assertGreaterEqual(text.count('"unowned_model_dependency_count":0'), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
