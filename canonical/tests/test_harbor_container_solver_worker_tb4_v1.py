"""Worker-level tests for the experimental terminal-bench-4 candidate path.

The doc compiler and open_model() are patched: these tests exercise routing,
annotation and honest fallback semantics, not benchmark capability.
"""
from __future__ import annotations

import base64
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import brain_unified_model_v1 as brain
from canonical.runtime import epistemic_doc_compiler_agent_v1 as doc_compiler
from canonical.runtime import harbor_container_solver_worker_v1 as worker


def run_worker(request: dict) -> dict:
    token = base64.b64encode(json.dumps(request).encode("utf-8")).decode("ascii")
    stdout = io.StringIO()
    with patch.object(worker.sys, "argv", ["worker", token]), redirect_stdout(stdout):
        rc = worker.main()
    assert rc == 0, stdout.getvalue()
    out = stdout.getvalue().removeprefix(worker.MARKER)
    return json.loads(out)


def tb4_request(repo: str, task: str = "no links in this instruction") -> dict:
    return {"goal": "goal", "mode": "EPISTEMIC", "inputs": {
        "harbor_suite": "terminal-bench-4", "harbor_task": task,
        "harbor_repo": repo, "observations": [],
        "experimental_candidate_path": True}}


class TerminalBenchCandidatePathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = str(Path(self.temp.name).resolve())

    def tearDown(self):
        self.temp.cleanup()

    def test_verified_doc_compiler_executes_in_place_and_is_not_self_trusted(self):
        with patch.object(doc_compiler, "solve_multi_step_with_instant_knowledge",
                          return_value={"status": "VERIFIED", "mode": "MULTI_STEP_DOC_COMPILED_ACTIVE_INFERENCE",
                                        "elapsed_ms": 3.0, "model_calls": 0, "parameters_stored": 0}):
            result = run_worker(tb4_request(self.root))
        self.assertEqual(result["engine_status"], "DOC_COMPILER_VERIFIED")
        self.assertEqual(result["actions"][0]["type"], "finish")
        self.assertEqual(result["apply"]["status"], "CANDIDATE_EXECUTED_IN_PLACE__UNVERIFIED")
        self.assertFalse(result["apply"]["official_verifier_invoked"])
        # Measurement, not self-report, decides candidate_applied/diff_bytes.
        self.assertNotIn("candidate_applied", result)
        self.assertNotIn("diff_bytes", result)

    def test_cli_execution_unverified_falls_back_to_brain_solve_loop(self):
        class FallbackModel:
            def solve(self, goal, **kwargs):
                return {"pass": True, "status": "PASS__PROMOTED_BOUND_CAPABILITY_EXECUTED_AND_TRACE_VERIFIED",
                        "capability_id": "python.test.pipeline.verifier.v1",
                        "actions": [{"type": "finish", "args": {"summary": "done"}}]}

        with patch.object(doc_compiler, "solve_multi_step_with_instant_knowledge",
                          return_value={"status": "FAILED", "mode": "CLI_EXECUTION_UNVERIFIED",
                                        "elapsed_ms": 29.42, "model_calls": 0, "parameters_stored": 0}), \
             patch.object(brain, "open_model", return_value=FallbackModel()) as mocked:
            result = run_worker(tb4_request(self.root))
        mocked.assert_called_once()
        self.assertEqual(result["engine_status"], "DOC_COMPILER_FAILED")
        self.assertEqual(result["fallback"], "OPEN_MODEL_AFTER_FAILED")
        self.assertEqual(result["doc_compiler_fallback"]["mode"], "CLI_EXECUTION_UNVERIFIED")
        self.assertEqual(result["doc_compiler"]["status"], "FAILED")
        self.assertEqual(result["actions"][0]["type"], "finish")
        self.assertEqual(result["world_model"]["status"], "NOT_INVOKED__NO_SUPPORTED_URL")

    def test_fallback_failure_is_an_honest_finish_not_a_crash(self):
        with patch.object(doc_compiler, "solve_multi_step_with_instant_knowledge",
                          return_value={"status": "FAILED", "mode": "CLI_EXECUTION_UNVERIFIED",
                                        "elapsed_ms": 1.0, "model_calls": 0, "parameters_stored": 0}), \
             patch.object(brain, "open_model", side_effect=RuntimeError("MODEL_ARTIFACT_MISSING")):
            result = run_worker(tb4_request(self.root))
        self.assertEqual(result["engine_status"], "DOC_COMPILER_FAILED")
        self.assertEqual(result["fallback"], "OPEN_MODEL_UNAVAILABLE")
        self.assertTrue(result["fallback_error"].startswith("RuntimeError"))
        self.assertEqual(result["actions"][0]["type"], "finish")
        self.assertTrue(result["official_verifier_expected"])

    def test_multi_cycle_observations_route_to_brain_when_experimental(self):
        class LoopModel:
            def solve(self, goal, **kwargs):
                return {"pass": False, "status": "FAIL_CLOSED", "actions": []}

        request = tb4_request(self.root)
        request["inputs"]["observations"] = [{"type": "terminal_exec", "returncode": 0,
                                              "stdout": "x", "stderr": ""}]
        with patch.object(brain, "open_model", return_value=LoopModel()) as mocked:
            result = run_worker(request)
        mocked.assert_called_once()
        self.assertEqual(result["fallback"], "OPEN_MODEL_AFTER_IMPORTED_ENGINE_ROUTE")

    def test_multi_cycle_observations_without_experimental_flag_stay_fail_closed(self):
        request = tb4_request(self.root)
        del request["inputs"]["experimental_candidate_path"]
        request["inputs"]["observations"] = [{"type": "terminal_exec", "returncode": 0,
                                              "stdout": "x", "stderr": ""}]
        result = run_worker(request)
        self.assertEqual(result["engine_status"], "UNEXPECTED_OBSERVATIONS")


if __name__ == "__main__":
    unittest.main()


class CipherCandidateCycleTests(unittest.TestCase):
    """The general classical-cipher capability fires on cipher-shaped TB4 tasks,
    never on others, and writes a real, self-contained artifact."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        from canonical.runtime import classical_cipher_v1 as cc
        slice_ = _english_prose_slice(620)
        self.assertIsNotNone(slice_, 'repo prose fixture unavailable')
        self.specimen = self.root / "blob.txt"
        self.specimen.write_text(cc.encrypt(slice_, "vigenere", "BRAINCYPHER"))
        self.plaintext = slice_

    def tearDown(self):
        self.temp.cleanup()

    def test_cipher_goal_routes_to_classical_engine_and_writes_cracker(self):
        request = {"goal": f"Build a Python command-line tool at {self.root}/cracker.py that reads "
                            f"one ciphertext file and writes English plaintext to stdout. The specimen is a "
                            f"classical substitution cipher.",
                   "mode": "EPISTEMIC",
                   "inputs": {"harbor_suite": "terminal-bench-4",
                              "harbor_task": f"Write a cracker for the Vigenere-family cipher in {self.root}",
                              "harbor_repo": str(self.root),
                              "observations": [],
                              "experimental_candidate_path": True}}
        result = run_worker(request)
        self.assertEqual(result["engine_status"], "CANDIDATE_WRITTEN__UNVERIFIED")
        self.assertEqual(result["engine"], "classical_cipher_v1")
        cc_info = result["classical_cipher"]
        self.assertEqual(cc_info["variant"] in ("vigenere_straight", "interleaved2", "vigenere_beaufort"), True)
        artifact = Path(cc_info["artifact_path"])
        self.assertTrue(artifact.is_file())
        out = subprocess.run([sys.executable, str(artifact), str(self.specimen)],
                             capture_output=True, text=True, timeout=120)
        import re as _re
        recovered = _re.sub(r"[^A-Z]", "", out.stdout.upper())
        self.assertEqual(recovered, self.plaintext)
        self.assertFalse(cc_info["official_verifier_invoked"])

    def test_non_cipher_goal_does_not_invoke_engine(self):
        request = {"goal": "Fix the failing unit tests in the project",
                   "mode": "EPISTEMIC",
                   "inputs": {"harbor_suite": "terminal-bench-4",
                              "harbor_task": "Fix the failing unit tests in the project",
                              "harbor_repo": str(self.root),
                              "observations": [],
                              "experimental_candidate_path": True}}
        with patch.object(doc_compiler, "solve_multi_step_with_instant_knowledge",
                          return_value={"status": "FAILED", "mode": "CLI_EXECUTION_UNVERIFIED",
                                        "elapsed_ms": 1.0, "model_calls": 0, "parameters_stored": 0}), \
             patch.object(brain, "open_model", side_effect=RuntimeError("no")):
            result = run_worker(request)
        self.assertNotEqual(result.get("engine"), "classical_cipher_v1")


def _english_prose_slice(min_len: int):
    root = Path(__file__).resolve().parents[2]
    for p in sorted(root.rglob("*.md")):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        letters = "".join(ch for ch in text.upper() if ch.isalpha())
        if len(letters) >= min_len:
            return letters[:min_len]
    return None
