"""Task-bound review fan-in, plus a real six-gate integration fixture."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime import astra_runtime
from canonical.runtime import verified_bound_capability_execution_adapter_v1 as adapter
from canonical.runtime.bound_capabilities import (
    python_review_diff_static_triage as lint,
    python_review_diff_type_gate as types,
    python_review_diff_security_gate as security,
    python_review_diff_coverage_gate as coverage,
    python_review_diff_mutation_gate as mutation,
    python_review_diff_perf_gate as perf,
    software_review_gate_composer_v1 as composer,
)

DIFF = """--- a/m.py
+++ b/m.py
@@ -1,2 +1,2 @@
 def calculate(a: int, b: int) -> int:
-    return a + b
+    return a - b
"""
MODULES = (lint, types, security, coverage, mutation, perf)


class ReviewCompositionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="brain-review-composition-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.anchor = self.root / "project"
        (self.anchor / "tests").mkdir(parents=True)
        (self.anchor / "m.py").write_text("def calculate(a: int, b: int) -> int:\n    return a + b\n")
        (self.anchor / "tests/test_m.py").write_text(
            "from m import calculate\ndef test_calculate():\n    assert calculate(3, 2) == 1\n")
        (self.anchor / "bench.py").write_text("def bench():\n    return sum(range(20000))\n")
        (self.root / "patch.diff").write_text(DIFF)
        self.args = {"anchor_path": "project", "diff_path": "patch.diff", "bench_path": "bench.py",
                     "output_path": "out/report.json", "python_executable": sys.executable,
                     "run_tests": ["tests/test_m.py"], "timeout_s": 30, "max_wall_time_s": 90,
                     "max_mutants": 20, "repeats": 3, "tolerance": 1.0,
                     "allow_unsafe_host_execution": True}

    def fake_gate(self, calls, *, fail=None, tamper_anchor=False, bad_hash=False):
        def run(args, root):
            index = len(calls)
            calls.append(args.copy())
            if tamper_anchor:
                (self.anchor / "m.py").write_text("tampered = True\n")
            sha = hashlib.sha256((Path(root) / args["diff_path"]).read_bytes()).hexdigest()
            data = {"gate": "FAIL" if index == fail else "PASS", "verified": index != fail,
                    "diff_sha256": sha, "complete": True}
            out = Path(root) / args["output_path"]
            out.parent.mkdir(parents=True, exist_ok=True)
            raw = json.dumps(data).encode()
            out.write_bytes(raw)
            return {**data, "output_verified": True, "output_sha256": hashlib.sha256(raw).hexdigest(),
                    "diff_sha256": "bad" if bad_hash else sha, "mutants_generated": 1}
        return run

    def patched_gates(self, calls, **kwargs):
        stack = contextlib.ExitStack()
        for module in MODULES:
            stack.enter_context(mock.patch.object(module, "run", side_effect=self.fake_gate(calls, **kwargs)))
        return stack

    def test_no_explicit_host_consent_does_not_execute_gates(self):
        calls = []
        with self.patched_gates(calls):
            result = composer.run({**self.args, "allow_unsafe_host_execution": False}, self.root)
        self.assertFalse(result["verified"])
        self.assertFalse(result["gates_verified"])
        self.assertEqual(calls, [])

    def test_all_stages_use_the_same_task_and_fail_fast(self):
        calls = []
        with self.patched_gates(calls):
            result = composer.run(self.args, self.root)
        self.assertTrue(result["gates_verified"], result)
        self.assertEqual(len(calls), 6)
        report = json.loads((self.root / "out/report.json").read_text())
        self.assertEqual(len(report["stages"]), 6)
        self.assertTrue(all(stage["verified"] for stage in report["stages"]))
        self.assertEqual((self.anchor / "m.py").read_text(),
                         "def calculate(a: int, b: int) -> int:\n    return a + b\n")
        calls = []
        with self.patched_gates(calls, fail=1):
            result = composer.run(self.args, self.root)
        self.assertFalse(result["gates_verified"])
        self.assertEqual(len(calls), 2)

    def test_registry_binds_task_inputs_and_explicit_opt_in(self):
        registry_path = Path(__file__).resolve().parents[1] / "runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
        action = json.loads(registry_path.read_text())["capabilities"][composer.CAPABILITY_ID]["action_template"]
        rendered = astra_runtime._render_bound_template(action, self.args)
        self.assertIs(rendered["args"]["allow_unsafe_host_execution"], True)
        self.assertEqual(rendered["args"]["run_tests"], ["tests/test_m.py"])
        calls = []
        with self.patched_gates(calls):
            result = composer.run(rendered["args"], self.root)
        self.assertTrue(result["gates_verified"])
        astra_runtime._verify_action_expectation(rendered, result)
        self.assertEqual(len(calls), 6)

    def test_live_adapter_requires_consent_and_reports_historical_verification(self):
        root = Path(__file__).resolve().parents[2]
        scratch = root / "canonical/astra_runtime/tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="review-bound-", dir=scratch) as td:
            base = Path(td)
            shutil.copytree(self.anchor, base / "project")
            (base / "patch.diff").write_text(DIFF)
            rel = base.relative_to(root)
            inputs = {
                "anchor_path": (rel / "project").as_posix(),
                "diff_path": (rel / "patch.diff").as_posix(),
                "output_path": (rel / "report.json").as_posix(),
                "bench_path": "bench.py", "run_tests": ["tests/test_m.py"],
                "allow_unsafe_host_execution": False,
            }
            calls = []
            with self.patched_gates(calls):
                refused = adapter.execute(composer.CAPABILITY_ID, inputs=inputs)
            self.assertFalse(refused["pass"])
            self.assertEqual(calls, [])
            inputs["allow_unsafe_host_execution"] = True
            with self.patched_gates(calls):
                result = adapter.execute(composer.CAPABILITY_ID, inputs=inputs)
            self.assertTrue(result["pass"], result)
            self.assertEqual(len(calls), 6)
            self.assertIs(result["current_implementation_independently_verified"], False)
            self.assertIn("NO_INDEPENDENT_CREDIT", result["semantic_boundary"])
            self.assertEqual(result["capability_credit_delta"], 0)

    def test_wrong_diff_hash_or_changed_anchor_never_verifies(self):
        for option in ("bad_hash", "tamper_anchor"):
            with self.subTest(option=option):
                (self.anchor / "m.py").write_text("def calculate(a: int, b: int) -> int:\n    return a + b\n")
                calls = []
                with self.patched_gates(calls, **{option: True}):
                    result = composer.run(self.args, self.root)
                self.assertFalse(result["gates_verified"], result)
                self.assertEqual(len(calls), 1)

    def test_output_and_benchmark_paths_are_confined(self):
        for changes in ({"output_path": "patch.diff"}, {"output_path": "project/m.py"},
                        {"bench_path": "../patch.diff"}):
            with self.subTest(changes=changes):
                before = (self.root / "patch.diff").read_bytes(), (self.anchor / "m.py").read_bytes()
                with self.assertRaises((ValueError, RuntimeError, SystemExit)):
                    composer.run({**self.args, **changes}, self.root)
                self.assertEqual(before, ((self.root / "patch.diff").read_bytes(), (self.anchor / "m.py").read_bytes()))

    def test_zero_budgets_and_invalid_limits_are_refused_before_execution(self):
        for change in ({"timeout_s": 0}, {"max_wall_time_s": 0}, {"max_mutants": 0},
                       {"repeats": 0}, {"tolerance": -1}):
            with self.subTest(change=change):
                calls = []
                with self.patched_gates(calls):
                    with self.assertRaisesRegex(ValueError, "INVALID_RESOURCE_LIMIT"):
                        composer.run({**self.args, **change}, self.root)
                self.assertEqual(calls, [])

    def test_real_six_gate_fixture(self):
        for name in ("pytest", "coverage", "mypy", "ruff", "bandit"):
            if importlib.util.find_spec(name) is None:
                self.skipTest(name + " is not installed")
        result = composer.run(self.args, self.root)
        self.assertTrue(result["gates_verified"], result)
        report = json.loads((self.root / "out/report.json").read_text())
        self.assertEqual([row["gate"] for row in report["stages"]], ["PASS"] * 6)
        mutation_stage = next(row for row in report["stages"] if row["name"] == "mutation")
        self.assertGreater(mutation_stage["result"]["mutants_generated"], 0)


if __name__ == "__main__":
    unittest.main()
