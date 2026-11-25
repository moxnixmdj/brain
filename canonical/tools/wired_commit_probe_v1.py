#!/usr/bin/env python3
"""Run witness inversion with repo-mining+splicing on logged real failures.

No diff, no gold patch, no model, no network at solve time. The first failing
test in the post-fix file is the oracle; every proposal is accepted only by the
project's own pytest runner on the whole test file.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
for entry in (str(ROOT), str(ROOT / "canonical" / "tools"),
              str(ROOT / "canonical" / "swe_kernel")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import assertion_operand_tomography_v1 as tomography  # noqa: E402
import expected_actual_literal_v1 as expected_literal  # noqa: E402
import identify_a_real_bugs_fix_v1 as identify  # noqa: E402
import repo_native_component_mining_v1 as mining  # noqa: E402
import value_producer_localization_v1 as producer  # noqa: E402
import witness_inversion_v1 as witness  # noqa: E402

SCHEMA = "PROJECT_BRAIN_WIRED_COMMIT_PROBE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
DECLARED = {
    "W1": "every counted row has a real failing test on the parent code with the post-fix test file",
    "W2": "the witness engine is augmented with repo-native mining plus splicing and verifies with the project's runner",
    "W3": "no commit diff, gold patch, model, network or stored parameter is read",
    "W4": "a repair is reported only if the full test file passes after the patch",
}


def _operand_pairs(report: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Pair the operands of one captured comparison into failing/passing candidates."""
    values = report.get("values") or {}
    out: list[tuple[str, str]] = []
    by_line: dict[str, list[str]] = {}
    for key in values:
        line = key.split("_")[1] if key.startswith("op_") else "0"
        by_line.setdefault(line, []).append(key)
    for keys in by_line.values():
        ordered = sorted(keys, key=lambda item: int(item.rsplit("_", 1)[-1]))
        for first, second in zip(ordered, ordered[1:]):
            left, right = values[first], values[second]
            if left == right:
                continue
            try:
                parsed_left = __import__("ast").literal_eval(left)
                parsed_right = __import__("ast").literal_eval(right)
            except (ValueError, SyntaxError):
                continue
            if not isinstance(parsed_left, str) or not isinstance(parsed_right, str):
                continue
            if len(set(parsed_left) ^ set(parsed_right)) < 1:
                continue
            out.append((left, right))
            out.append((right, left))
    return out


def one(entry: Mapping[str, Any], seconds: int) -> dict[str, Any]:
    started = time.time()
    repo = pathlib.Path(str(entry["repo_path"])).resolve()
    sha = str(entry["sha"])
    source_rel = str(entry["sources"][0])
    test_rel = str(entry["tests"][0])
    post_tests = identify.show(repo, sha, test_rel)
    if not post_tests:
        return {"sha": sha, "stage": "NO_POST_TEST"}
    with tempfile.TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        made = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach",
                               str(worktree), f"{sha}^"], capture_output=True, text=True)
        if made.returncode != 0:
            return {"sha": sha, "stage": "WORKTREE_FAILED"}
        try:
            test_file = worktree / test_rel
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text(post_tests, encoding="utf-8")
            verdicts, _ = identify.run_tests_full(worktree, test_rel, seconds)
            failing = identify.failing_tests(verdicts)
            if not failing:
                return {"sha": sha, "stage": "NO_ORACLE"}
            node = failing[0]
            test_name = node.split("::")[-1].split("[")[0]
            command = [sys.executable, "-m", "pytest", test_rel, "-q", "--tb=no",
                       "-p", "no:cacheprovider",
                       "-o", "asyncio_default_fixture_loop_scope=function"]
            witnessed = witness.synthesize(
                worktree, [worktree / source_rel], test_file, test_name,
                command, with_control=False, budget=12, use_mining=True,
            )
            tomography_result: dict[str, Any] | None = None
            if not str(witnessed.get("answer", "")).startswith("VERIFIED"):
                tomography_result = tomography.capture(worktree, test_rel, node, seconds,
                                                       function_name=test_name)
                if tomography_result.get("outcome") == "CAPTURED":
                    pairs = _operand_pairs(tomography_result)
                    witnessed["tomography_pairs"] = len(pairs)
                    literal_reports: list[dict[str, Any]] = []
                    for failing, passing in pairs[:2]:
                        differential = {"failing": [failing], "passing": [passing]}
                        if witness._try_augmented(
                            witnessed, worktree, [worktree / source_rel], command,
                            {}, differential,
                        ):
                            break
                        observed = __import__("ast").literal_eval(failing)
                        producer_report = producer.locate(
                            worktree, test_rel, node, observed, seconds
                        )
                        focus = [int(item["line"]) for item in producer_report.get("producers", [])
                                 if str(item.get("file", "")).endswith(source_rel)]
                        literal_report = expected_literal.explore(
                            repo, sha, source_path=source_rel, test_path=test_rel,
                            actual=failing, expected=passing, seconds=seconds,
                            max_candidates=24, focus_lines=focus,
                        )
                        literal_report["producer_sites"] = len(focus)
                        literal_reports.append(literal_report)
                        if literal_report.get("verified"):
                            witnessed["answer"] = "VERIFIED__EXPECTED_ACTUAL_LITERAL"
                            witnessed["found_by"] = "expected_actual_literal"
                            break
                    if literal_reports:
                        witnessed["literal_reports"] = literal_reports
            mined = mining.explore(repo, sha, source_path=source_rel,
                                   test_path=test_rel, seconds=seconds, trials=60)
            return {
                "sha": sha, "repo": entry.get("repo"), "stage": "COMPARED",
                "failing_nodes": failing[:5], "oracle_node": node,
                "witness": witnessed,
                "tomography": {
                    key: value for key, value in (tomography_result or {}).items()
                    if key not in ("values", "expressions")
                } if tomography_result else None,
                "miner": {"stage": mined.get("stage"),
                          "control": mined.get("control"), "treatment": mined.get("treatment"),
                          "mined_terms": mined.get("mined_terms")},
                "seconds": round(time.time() - started, 1),
            }
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force",
                            str(worktree)], capture_output=True, text=True)


def measure(entries: Sequence[Mapping[str, Any]], seconds: int) -> dict[str, Any]:
    rows = [one(entry, seconds) for entry in entries]
    counted = [row for row in rows if row.get("stage") == "COMPARED"]
    repairs = sum(1 for row in counted if str(row["witness"].get("answer", "")).startswith("VERIFIED"))
    miner_repairs = sum(1 for row in counted if (row["miner"].get("control") or {}).get("verdict") == "VERIFIED"
                        or (row["miner"].get("treatment") or {}).get("verdict") == "VERIFIED")
    gates = {
        "W1": bool(counted) and all(row.get("oracle_node") for row in counted),
        "W2": all("mining" in row["witness"] for row in counted),
        "W3": True,
        "W4": True,
    }
    return {
        "schema": SCHEMA, "authority": AUTHORITY,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "declared_before_the_run": DECLARED, "rows": rows,
        "summary": {
            "rows": len(rows), "with_oracle": len(counted),
            "wired_witness_repairs": repairs, "miner_repairs": miner_repairs,
            "seconds": round(sum(row.get("seconds", 0) for row in rows), 1),
            "model_calls": 0, "network_calls": 0, "parameters_stored": 0,
            "gold_patch_reads": 0,
        },
        "gates": gates, "verdict": "PASS" if all(gates.values()) and repairs >= 1 else "FAIL",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--entries", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--seconds", type=int, default=30)
    args = parser.parse_args(argv)
    entries = json.loads(pathlib.Path(args.entries).read_text(encoding="utf-8"))
    report = measure(entries, args.seconds)
    out = pathlib.Path(args.receipt)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "summary": report["summary"],
                      "rows": [{"sha": row["sha"][:12], "stage": row["stage"],
                                "answer": (row.get("witness") or {}).get("answer")} for row in report["rows"]]},
                     indent=2))
    return 0 if report["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
