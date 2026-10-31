"""Measure current diff-gate cost and the pytest JUnit reporter on one fixture.

All arms execute current code and installed tools. Plain pytest omits the
reporter only to measure invocation cost; it is not a safe verification gate.
This is a synthetic local measurement, not independent verification or a
claim about arbitrary repositories.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.bound_capabilities import python_repo_diff_apply_full_testgate as test_gate  # noqa: E402
from canonical.runtime.bound_capabilities import python_review_diff_coverage_gate as coverage_gate  # noqa: E402
from canonical.runtime.bound_capabilities import python_review_diff_mutation_gate as mutation_gate  # noqa: E402
from canonical.runtime.bound_capabilities.quality_flake_detect_v1 import _junit_cases  # noqa: E402


def measure(samples: int) -> dict:
    if samples < 1:
        raise ValueError("samples must be positive")
    if subprocess.run([sys.executable, "-m", "coverage", "--version"],
                      capture_output=True, text=True, check=False).returncode != 0:
        raise RuntimeError("coverage.py is required for this comparison")
    with tempfile.TemporaryDirectory(prefix="brain-diff-gate-cost-") as temporary:
        root = Path(temporary)
        anchor = root / "anchor"
        (anchor / "tests").mkdir(parents=True)
        (anchor / "subject.py").write_text("def compute(value):\n    return value + 1\n")
        (anchor / "tests/test_subject.py").write_text(
            "import pytest\nfrom subject import compute\n"
            "@pytest.mark.parametrize('value', range(31))\n"
            "def test_compute(value):\n    assert compute(value) == value + 2\n")
        (root / "change.diff").write_text(
            "--- a/subject.py\n+++ b/subject.py\n@@ -1,2 +1,2 @@\n"
            " def compute(value):\n-    return value + 1\n+    return value + 2\n")
        raw = root / "patched"
        shutil.copytree(anchor, raw)
        (raw / "subject.py").write_text("def compute(value):\n    return value + 2\n")
        report = root / "results.xml"
        env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1")
        old_autoload = os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD")
        os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        names = ("pytest_without_junit", "pytest_with_junit", "current_test_gate",
                 "current_coverage_gate", "current_mutation_gate_one_mutant")
        timings = {name: [] for name in names}

        def run(name: str) -> float:
            start = time.perf_counter_ns()
            if name.startswith("pytest_"):
                cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
                if name == "pytest_with_junit":
                    cmd.append(f"--junitxml={report}")
                proc = subprocess.run(cmd, cwd=raw, env=env, capture_output=True,
                                      text=True, timeout=30, check=False)
                if proc.returncode != 0 or "31 passed" not in proc.stdout:
                    raise RuntimeError(f"unexpected pytest result for {name}: {proc.stdout}\n{proc.stderr}")
                if name == "pytest_with_junit":
                    cases = _junit_cases(report)
                    if len(cases) != 31 or any(outcome != "passed" for _, outcome in cases):
                        raise RuntimeError("unexpected JUnit result")
            else:
                module = {"current_test_gate": test_gate, "current_coverage_gate": coverage_gate,
                          "current_mutation_gate_one_mutant": mutation_gate}[name]
                args = {"anchor_path": "anchor", "diff_path": "change.diff",
                        "output_path": f"out/{name}.json", "python_executable": sys.executable,
                        "timeout_s": 30}
                if module is mutation_gate:
                    args["max_mutants"] = 1
                result = module.run(args, root)
                if result["gate"] != "UNRESOLVED__UNAUTHENTICATED_EVIDENCE" or result["local_gate"] != "PASS" or result["verified"]:
                    raise RuntimeError(f"unexpected {name} result: {result}")
                if module is mutation_gate:
                    if result["mutants_generated"] != 1 or result["mutants_killed"] != 1:
                        raise RuntimeError(f"unexpected mutation result: {result}")
                elif result["tests_passed"] != 31:
                    raise RuntimeError(f"unexpected test count: {result}")
            return (time.perf_counter_ns() - start) / 1_000_000

        try:
            for name in names:
                run(name)  # warm each arm
            for index in range(samples):
                order = names[index % len(names):] + names[:index % len(names)]
                for name in order if index % 2 == 0 else tuple(reversed(order)):
                    timings[name].append(run(name))
        finally:
            if old_autoload is None:
                os.environ.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)
            else:
                os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = old_autoload
        return {
            "schema": "BRAIN_DIFF_GATE_EVIDENCE_COST_PROBE_V1",
            "samples_per_arm": samples,
            "fixture": "one changed Python function, 31 parametrized passing cases; mutation capped at one; serial rotated order",
            "median_ms": {key: round(statistics.median(values), 2) for key, values in timings.items()},
            "min_ms": {key: round(min(values), 2) for key, values in timings.items()},
            "max_ms": {key: round(max(values), 2) for key, values in timings.items()},
            "limitations": ("Synthetic single fixture and machine; the gate arms perform different work. "
                            "The pytest-only pair measures reporter cost, not total before/after gate cost. "
                            "Without JUnit, a zero pytest exit is not a safe gate."),
            "terminal_authority": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=8)
    args = parser.parse_args()
    print(json.dumps(measure(args.samples), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
