from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys
import unittest
from unittest.mock import patch

CANONICAL = pathlib.Path(__file__).resolve().parents[1]
RUNTIME = CANONICAL / "runtime" / "astra_runtime.py"


def load_runtime():
    name = "astra_declared_cross_step_boundary_test"
    spec = importlib.util.spec_from_file_location(name, RUNTIME)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


runtime = load_runtime()


def state():
    return {
        "history": [
            {
                "step_index": 0,
                "ok": True,
                "result": {
                    "body_excerpt": "BOUND_BODY",
                    "stdout": "HIDDEN_STDOUT",
                    "status": 200,
                },
            }
        ],
        "rehydrations": [],
    }


def strict_step(channels=None):
    return {
        "id": "consumer",
        "adapter": "shell",
        "command": "printf x",
        "cross_step_inputs": [
            {"step_index": 0, "channels": channels or ["BODY"]}
        ],
    }


class DeclaredCrossStepBoundaryTests(unittest.TestCase):
    def test_declared_body_only_is_projected(self):
        step = strict_step(["BODY"])
        ctx = runtime._declared_context_results(state(), step, 1)
        captured = {}

        def fake_run(*args, **kwargs):
            captured.update(kwargs["env"])
            class P:
                returncode = 0
                stdout = "ok"
                stderr = ""
            return P()

        with patch.object(runtime, "_resolve_bash_executable", return_value="/bin/bash"), \
             patch.object(runtime.subprocess, "run", side_effect=fake_run):
            result = runtime.run_shell(step, ctx)

        self.assertEqual(captured["ASTRA_STEP_0_BODY"], "BOUND_BODY")
        self.assertNotIn("ASTRA_STEP_0_STDOUT", captured)
        self.assertNotIn("ASTRA_STEP_0_RESULT_JSON", captured)
        raw = json.dumps(
            state()["history"][0]["result"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        self.assertEqual(
            captured["ASTRA_STEP_0_RESULT_SHA256"],
            hashlib.sha256(raw).hexdigest(),
        )
        self.assertEqual(
            result["cross_step_context_mode"],
            runtime.DECLARED_CROSS_STEP_CONTEXT_MODE,
        )
        self.assertEqual(result["cross_step_bindings"][0]["channels"], ["BODY"])

    def test_future_or_same_step_source_is_denied(self):
        step = {
            "cross_step_inputs": [{"step_index": 1, "channels": ["BODY"]}]
        }
        with self.assertRaisesRegex(runtime.Blocker, "CROSS_STEP_SOURCE_NOT_PRIOR"):
            runtime._declared_context_results(state(), step, 1)

    def test_payload_hash_tamper_is_denied(self):
        step = strict_step()
        ctx = runtime._declared_context_results(state(), step, 1)
        ctx["bindings"][0]["result"]["body_excerpt"] = "TAMPERED"
        with self.assertRaisesRegex(runtime.Blocker, "CROSS_STEP_RESULT_HASH_MISMATCH"):
            runtime.run_shell(step, ctx)

    def test_extra_undeclared_channel_is_denied(self):
        step = strict_step(["BODY"])
        ctx = runtime._declared_context_results(state(), step, 1)
        ctx["bindings"][0]["channels"] = ["BODY", "STDOUT"]
        with self.assertRaisesRegex(
            runtime.Blocker, "CROSS_STEP_BINDING_DECLARATION_MISMATCH"
        ):
            runtime.run_shell(step, ctx)

    def test_strict_mission_with_no_declared_inputs_gets_empty_context(self):
        mission = {
            "cross_step_context_mode": runtime.DECLARED_CROSS_STEP_CONTEXT_MODE,
            "steps": [{"id": "consumer", "adapter": "shell", "cross_step_inputs": []}],
        }
        ctx = runtime._step_context_results(state(), mission, 0)
        self.assertEqual(ctx["bindings"], [])
        self.assertEqual(ctx["mode"], runtime.DECLARED_CROSS_STEP_CONTEXT_MODE)

    def test_unknown_mission_context_mode_fails_closed(self):
        mission = {
            "cross_step_context_mode": "TRUST_EVERYTHING_V9000",
            "steps": [{"id": "consumer", "adapter": "shell"}],
        }
        with self.assertRaisesRegex(runtime.Blocker, "CROSS_STEP_CONTEXT_MODE_UNKNOWN"):
            runtime._step_context_results(state(), mission, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
