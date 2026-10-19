#!/usr/bin/env python3
"""Measure capability growth: real tasks, learned at runtime, held out.

Each task is learned from one real observation (examples or a checkable goal),
then executed on real data the learner never saw.  The report shows the wall
time to acquire each skill and whether the result was exact.

    python3 -m canonical.runtime.living_agent_growth_v1
    python3 -m canonical.runtime.living_agent_growth_v1 --json

Authority: NONE.  This is a measurement of this tree on this machine, not a
verification receipt and not a capability grant.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from canonical.runtime import living_agent_benchmark_v1 as benchmark
from canonical.runtime.living_agent_v1 import LivingAgent

SCHEMA = "PROJECT_BRAIN_LIVING_AGENT_GROWTH_V1"
ROOT = Path(__file__).resolve().parents[2]


def shell_lines(text: str) -> list[str]:
    parts = text.split("\n")
    if parts and parts[-1] == "":
        parts.pop()
    return parts


def _sorted(text: str) -> str:
    return "\n".join(sorted(shell_lines(text), key=lambda line: line.encode())) + "\n"


def measure() -> dict[str, Any]:
    demo_dirs = [ROOT / "canonical" / "capabilities", ROOT / "execution_guard"]
    holdout_dirs = [ROOT / "canonical" / "governance", ROOT / "canonical" / "laws", ROOT / "tests"]
    tasks: list[dict[str, Any]] = []
    started_all = time.perf_counter()

    with tempfile.TemporaryDirectory() as tmp:
        agent = LivingAgent(tmp)
        demos = [benchmark.real_tree_table(d, pattern="*") for d in demo_dirs]
        for index, demo in enumerate(demos, start=1):
            agent.computer.write(f"demo{index}.csv", demo.to_csv())

        def examples(make: Callable[[Any], str]) -> list[tuple[str, str]]:
            return [(f"demo{index}.csv", make(demo)) for index, demo in enumerate(demos, start=1)]

        acquisitions: list[tuple[str, Callable[[str], dict[str, Any]]]] = [
            (
                "file names",
                lambda: agent.acquire(
                    "list the file names in the listing",
                    examples(lambda t: "\n".join(r["name"] for r in t.rows) + "\n"),
                ),
            ),
            (
                "total bytes",
                lambda: agent.acquire(
                    "total the sizes in the listing",
                    examples(lambda t: "%.0f\n" % sum(int(r["size"]) for r in t.rows)),
                ),
            ),
            (
                "distinct extensions",
                lambda: agent.acquire(
                    "list the distinct extensions in the listing",
                    examples(lambda t: "\n".join(sorted({r["ext"] for r in t.rows})) + "\n"),
                ),
            ),
        ]

        for label, acquire in acquisitions:
            before = time.perf_counter()
            try:
                outcome = acquire()
                status = outcome.get("status")
                stages = outcome.get("stages")
            except Exception as exc:  # a failure is recorded, never hidden
                status, stages = "ERROR:" + type(exc).__name__ + ":" + str(exc), None
            tasks.append(
                {
                    "task": label,
                    "learn_seconds": round(time.perf_counter() - before, 4),
                    "status": status,
                    "stages": stages,
                }
            )

        # direct intent, no example output
        for index, source in enumerate((ROOT / "canonical" / "runtime" / "living_agent_v1.py",)):
            name = f"doc{index}.txt"
            agent.computer.write(name, source.read_text(encoding="utf-8"))
            before = time.perf_counter()
            try:
                outcome = agent.fulfil(f"sort the lines of '{name}'", name)
                status = outcome.get("status")
                stages = outcome.get("stages")
            except Exception as exc:
                status, stages = "ERROR:" + type(exc).__name__ + ":" + str(exc), None
            tasks.append(
                {
                    "task": "sort a real file",
                    "learn_seconds": round(time.perf_counter() - before, 4),
                    "status": status,
                    "stages": stages,
                }
            )

        # held-out execution: the learned skills run on untouched real data
        heldout: list[dict[str, Any]] = []
        for directory in holdout_dirs:
            table = benchmark.real_tree_table(directory, pattern="*")
            agent.computer.write("held.csv", table.to_csv())
            checks = {
                "file names": "\n".join(r["name"] for r in table.rows) + "\n",
                "total bytes": "%.0f\n" % sum(int(row["size"]) for row in table.rows),
                "distinct extensions": "\n".join(sorted({r["ext"] for r in table.rows})) + "\n",
            }
            goals = {
                "file names": "list the file names in 'held.csv'",
                "total bytes": "total the sizes in 'held.csv'",
                "distinct extensions": "list the distinct extensions in 'held.csv'",
            }
            for label, want in checks.items():
                try:
                    result = agent.solve(goals[label])
                    exact = result.get("stdout") == want
                    status = result.get("status")
                except Exception as exc:
                    exact = False
                    status = "ERROR:" + type(exc).__name__
                heldout.append(
                    {
                        "task": label,
                        "directory": str(directory.relative_to(ROOT)),
                        "status": status,
                        "exact": exact,
                    }
                )

            name = "held.txt"
            text = (directory / "README.md").read_text(encoding="utf-8") if (directory / "README.md").is_file() else table.to_csv()
            agent.computer.write(name, text)
            try:
                result = agent.solve(f"sort the lines of '{name}'")
                exact = result.get("stdout") == _sorted(text)
                status = result.get("status")
            except Exception as exc:
                exact, status = False, "ERROR:" + type(exc).__name__
            heldout.append(
                {
                    "task": "sort a real file",
                    "directory": str(directory.relative_to(ROOT)),
                    "status": status,
                    "exact": exact,
                }
            )

    learn_times = [task["learn_seconds"] for task in tasks]
    return {
        "schema": SCHEMA,
        "authority": "NONE",
        "kind": "MEASUREMENT_NOT_RECEIPT",
        "acquisitions": tasks,
        "heldout": heldout,
        "totals": {
            "skills_acquired": sum(1 for task in tasks if str(task["status"]) == "PASS"),
            "acquisition_attempts": len(tasks),
            "median_learn_seconds": round(sorted(learn_times)[len(learn_times) // 2], 4),
            "max_learn_seconds": round(max(learn_times), 4),
            "heldout_exact": sum(1 for row in heldout if row["exact"]),
            "heldout_cases": len(heldout),
            "model_dependency_count": 0,
            "incremental_spend_usd": 0,
            "wall_seconds": round(time.perf_counter() - started_all, 3),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = measure()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for task in report["acquisitions"]:
            print(
                f"learn {task['task']:22s} status={task['status']:6s} "
                f"t={task['learn_seconds']:.3f}s stages={task['stages']}"
            )
        for row in report["heldout"]:
            print(
                f"held  {row['task']:22s} {row['directory']:28s} "
                f"exact={row['exact']} status={row['status']}"
            )
        totals = report["totals"]
        print(
            f"TOTAL acquired={totals['skills_acquired']}/{totals['acquisition_attempts']} "
            f"heldout={totals['heldout_exact']}/{totals['heldout_cases']} "
            f"median_learn={totals['median_learn_seconds']:.3f}s "
            f"max_learn={totals['max_learn_seconds']:.3f}s "
            f"wall={totals['wall_seconds']:.2f}s spend=${totals['incremental_spend_usd']}"
        )
    totals = report["totals"]
    return 0 if totals["heldout_exact"] == totals["heldout_cases"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
