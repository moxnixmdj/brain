"""Time real command re-inspection, including namespace overhead where used."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.raw_goal_trace_acceptance_v1 import _inspect_shell_command_run  # noqa: E402


def measure(iterations: int = 12) -> dict:
    if not 1 <= iterations <= 100:
        raise ValueError("ITERATIONS_MUST_BE_1_TO_100")
    cases = (
        ("cat", ["cat", "a.txt"], "alpha\nbeta\n"),
        ("wc_line_count", ["wc", "-l", "a.txt"], "2 a.txt\n"),
        ("sort", ["sort", "a.txt"], "alpha\nbeta\n"),
    )
    rows = []
    with tempfile.TemporaryDirectory(prefix="brain-reinspection-timing-") as td:
        root = Path(td)
        (root / "a.txt").write_bytes(b"alpha\nbeta\n")
        for name, argv, stdout in cases:
            samples = []
            evidence = {}
            reason = ""
            for index in range(iterations + 1):
                start = time.perf_counter_ns()
                ok, reason, evidence = _inspect_shell_command_run(
                    {"argv": argv}, {"stdout": stdout, "stderr": "", "returncode": 0}, root)
                elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
                if not ok:
                    break
                if index:  # exclude the first-call import and namespace warmup
                    samples.append(elapsed_ms)
            if len(samples) != iterations:
                rows.append({"case": name, "status": "REFUSED", "reason": reason})
                continue
            rows.append({"case": name, "status": "MEASURED", "n": len(samples),
                         "median_ms": round(statistics.median(samples), 3),
                         "min_ms": round(min(samples), 3), "max_ms": round(max(samples), 3),
                         "input_files_reopened": evidence.get("input_files_reopened"),
                         "replay_read_only_namespace": evidence.get("replay_read_only_namespace")})
    return {"schema": "BRAIN_REINSPECTION_TIMING_PROBE_V1", "rows": rows,
            "terminal_authority": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=12)
    args = parser.parse_args()
    report = measure(args.iterations)
    print(json.dumps(report, indent=2, sort_keys=True))
    return int(any(row["status"] != "MEASURED" for row in report["rows"]))


if __name__ == "__main__":
    raise SystemExit(main())
