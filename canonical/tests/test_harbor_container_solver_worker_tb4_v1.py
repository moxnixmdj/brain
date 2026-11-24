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
