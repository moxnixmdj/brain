"""Measure selected-vs-full pytest cost on one disposable, current fixture.

The selected arm intentionally omits cases and is NOT a safe verification gate.
Both arms use the installed pytest and its JUnit reporter; no historical code is
loaded. This measures pytest invocation cost, not end-to-end orchestrator cost.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET


def measure(samples: int) -> dict:
    if samples < 1:
        raise ValueError("samples must be positive")
    with tempfile.TemporaryDirectory(prefix="brain-pytest-safety-cost-") as temporary:
        root = Path(temporary)
        (root / "pkg").mkdir()
        (root / "tests").mkdir()
        (root / "pkg/__init__.py").write_text("")
        (root / "pkg/core.py").write_text("def compute(x):\n    return x + 1\n")
        (root / "tests/test_smoke.py").write_text(
            "from pkg.core import compute\n\ndef test_smoke():\n    assert compute(2) == 3\n")
        (root / "tests/test_unrelated.py").write_text("".join(
            f"def test_unrelated_{i}():\n    assert len(str({i})) == {len(str(i))}\n\n"
            for i in range(30)))
        report = root / "results.xml"
        env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1")
        arms = ("selected_subset_unsafe", "full_default_discovery")
        times: dict[str, list[float]] = {name: [] for name in arms}
        counts = {}

        def run(name: str) -> float:
            command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                       f"--junitxml={report}"]
            if name == "selected_subset_unsafe":
                command.append("tests/test_smoke.py")
            started = time.perf_counter_ns()
            proc = subprocess.run(command, cwd=root, env=env, capture_output=True,
                                  text=True, timeout=60, check=False)
            elapsed = (time.perf_counter_ns() - started) / 1_000_000
            cases = list(ET.parse(report).getroot().iter("testcase"))
            passed = sum(case.find("failure") is None and case.find("error") is None
                         and case.find("skipped") is None for case in cases)
            expected = 1 if name == "selected_subset_unsafe" else 31
            if proc.returncode != 0 or passed != expected or len(cases) != expected:
                raise RuntimeError(f"unexpected pytest outcome for {name}: {proc.returncode}, {passed}/{len(cases)}")
            counts[name] = passed
            return elapsed

        for name in arms:
            run(name)  # warm both arms outside the sample
        for i in range(samples):
            for name in arms if i % 2 == 0 else tuple(reversed(arms)):
                times[name].append(run(name))
        return {
            "schema": "BRAIN_PYTEST_DISCOVERY_COST_PROBE_V1",
            "samples_per_arm": samples,
            "fixture": "one selected and 30 unrelated trivial pytest cases; serial alternating order",
            "median_ms": {name: round(statistics.median(values), 2) for name, values in times.items()},
            "min_ms": {name: round(min(values), 2) for name, values in times.items()},
            "max_ms": {name: round(max(values), 2) for name, values in times.items()},
            "passed_cases": counts,
            "limitations": "pytest invocation only; synthetic fixture; selected subset is unsafe; not a general speed estimate",
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
