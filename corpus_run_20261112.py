#!/usr/bin/env python3
"""Record two bounded rename exercises on existing repository fixtures.

This is NOT an independently verified corpus, production workload, learning update, or benchmark.
Inputs are snapshotted BEFORE execution through the existing receipt lane's snapshot_inputs helper.
Replay restores only stored bytes and checks their hashes, then repeats the same invocation.
AST and baseline/post-edit unittest checks are local checks, not independent verification.
The deliberately red fixture remains red; PASS_BLIND is recorded, never promoted to PASS.
Writes only to scratch, the content-addressed input store, and local exercise records.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime.bound_capabilities import python_refactor_rename_symbol as rename_symbol  # noqa: E402
from canonical.runtime.capability_receipt_lane_v1 import snapshot_inputs, sha256_canonical  # noqa: E402

FIXTURE = "canonical/tests/fixtures/tree_sitter_swe/python"
SCRATCH = "canonical/astra_runtime/tmp/corpus_tasks"
STORE = "canonical/astra_runtime/instances"
RECORD_DIR = "canonical/astra_runtime/evidence/instances"
CAPABILITY_ID = "python.refactor.rename_symbol.v1"

#: Two explicit rename requests; no claim of task discovery or generalization.
TASKS: list[dict[str, str]] = [
    {"id": "rename_add_in_calc", "module": "calc.py", "qualname": "add", "new_symbol": "add_v2"},
    {"id": "rename_twice_in_util", "module": "util.py", "qualname": "twice", "new_symbol": "twice_v2"},
]


def _digest_tree(root: pathlib.Path) -> dict[str, str]:
    digests: dict[str, str] = {}
    for path in sorted(root.rglob("*.py")):
        digests[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def _keep_bytes(root: pathlib.Path) -> dict[str, str]:
    files = {str(path.relative_to(root)): str(path)
             for path in sorted(root.rglob("*.py"))}
    digests = snapshot_inputs(str(REPO_ROOT), files)
    if len(digests) != len(files):
        raise ValueError("INPUT_SNAPSHOT_INCOMPLETE")
    return digests


def _restore_inputs(scratch: pathlib.Path, digests: dict[str, str]) -> None:
    # Validate every blob and path before removing the old scratch tree.
    blobs = {}
    for name, digest in digests.items():
        relative = pathlib.Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("SNAPSHOT_PATH_ESCAPE")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("SNAPSHOT_DIGEST_INVALID")
        blob = (REPO_ROOT / STORE / (digest + ".bin")).read_bytes()
        if hashlib.sha256(blob).hexdigest() != digest:
            raise ValueError("SNAPSHOT_DIGEST_MISMATCH")
        blobs[relative] = blob
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    for relative, blob in blobs.items():
        path = scratch / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)


def _test_outcome(scratch: pathlib.Path) -> dict[str, Any]:
    # Fresh interpreter prevents imports from another task contaminating this measurement.
    script = ("import json,unittest; r=unittest.TestResult(); "
              "unittest.defaultTestLoader.discover('.',pattern='test_*.py').run(r); "
              "print(json.dumps({'tests_run':r.testsRun,"
              "'failures':sorted(t.id() for t,_ in r.failures),"
              "'errors':sorted(t.id() for t,_ in r.errors),"
              "'skipped':sorted(t.id() for t,_ in r.skipped)}))")
    proc = subprocess.run([sys.executable, "-B", "-c", script], cwd=scratch,
                          text=True, capture_output=True, timeout=20, check=True)
    return json.loads(proc.stdout)


def _defines(path: pathlib.Path, name: str) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return any(isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name
               for node in ast.walk(tree))


def _names(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            used.add(node.attr)
        elif isinstance(node, ast.ImportFrom):
            used.update(alias.name for alias in node.names)
    return used


def postcondition(scratch: pathlib.Path, task: dict[str, str]) -> dict[str, Any]:
    """Check the effect with the AST — a different mechanism from the capability's own gate."""
    module = scratch / task["module"]
    new_present = _defines(module, task["new_symbol"])
    old_gone = not _defines(module, task["qualname"])
    callers_updated = all(task["qualname"] not in _names(path)
                          for path in scratch.rglob("*.py") if path.name != task["module"])
    return {
        "symbol_defined": new_present,
        "symbol_gone": old_gone,
        "call_sites_updated": callers_updated,
        "holds": new_present and old_gone and callers_updated,
        "checked_by": "runner_ast_postcondition",
        "independent": False,
    }


def run_task(task: dict[str, str], where: pathlib.Path,
             saved_inputs: dict[str, str] | None = None) -> dict[str, Any]:
    scratch = where / task["id"]
    if saved_inputs is None:
        if scratch.exists():
            shutil.rmtree(scratch)
        scratch.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(REPO_ROOT / FIXTURE, scratch)
        inputs = _keep_bytes(scratch)
    else:
        _restore_inputs(scratch, saved_inputs)
        inputs = _digest_tree(scratch)
        if inputs != saved_inputs:
            raise ValueError("RESTORED_INPUTS_DIFFER")
    baseline = _test_outcome(scratch)

    result = rename_symbol.run({
        "capability_id": CAPABILITY_ID,
        "source_root": str(scratch.relative_to(REPO_ROOT)),
        "module": task["module"],
        "qualname": task["qualname"],
        "new_symbol": task["new_symbol"],
        "output_path": str((where / f"{task['id']}.json").relative_to(REPO_ROOT)),
    }, str(REPO_ROOT))

    return {
        "schema": "PROJECT_BRAIN_INSTANCE_RECORD_V1",
        "kind": "LOCAL_FIXTURE_EXERCISE",
        "source": FIXTURE,
        "module_path": "canonical/runtime/bound_capabilities/python_refactor_rename_symbol.py",
        "module_sha256": hashlib.sha256(pathlib.Path(rename_symbol.__file__).read_bytes()).hexdigest(),
        "independently_verified": False,
        "task_id": task["id"],
        "capability_id": CAPABILITY_ID,
        "request": {key: task[key] for key in ("module", "qualname", "new_symbol")},
        "input_digests": inputs,
        "input_count": len(inputs),
        "result_sha256": sha256_canonical(result),
        "output_digests": _digest_tree(scratch),
        "baseline_tests": baseline,
        "post_edit_tests": _test_outcome(scratch),
        "observed": {"status": result.get("status"), "gate": result.get("gate"),
                     "edit_count": result.get("edit_count")},
        "postcondition": postcondition(scratch, task),
        "ran_by": "arena-agent-20261112",
        "independent_verifier": None,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }


def run() -> dict[str, Any]:
    where = REPO_ROOT / SCRATCH
    records = []
    for task in TASKS:
        first = run_task(task, where)
        # Delete the edited tree: replay can use ONLY content-addressed pre-edit bytes.
        shutil.rmtree(where / task["id"])
        second = run_task(task, where, saved_inputs=first["input_digests"])
        first["replayed"] = (first["result_sha256"] == second["result_sha256"]
                             and first["output_digests"] == second["output_digests"]
                             and first["input_digests"] == second["input_digests"]
                             and first["post_edit_tests"] == second["post_edit_tests"])
        first["baseline_preserved"] = (first["baseline_tests"] == first["post_edit_tests"]
                                       and first["baseline_tests"]["tests_run"] > 0
                                       and not first["post_edit_tests"]["errors"])
        first["replay_result_sha256"] = second["result_sha256"]
        records.append(first)

    record_dir = REPO_ROOT / RECORD_DIR
    record_dir.mkdir(parents=True, exist_ok=True)
    for record in records:
        (record_dir / f"INSTANCE__{record['task_id']}__RECORD.json").write_text(
            json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "runner": "corpus_run",
        "executed": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "tasks": len(records),
        "independently_verified_instances": 0,
        "baseline_preserved": sum(record["baseline_preserved"] for record in records),
        "capabilities_used": sorted({record["capability_id"] for record in records}),
        "records_with_inputs": sum(1 for record in records if record["input_digests"]),
        "input_files_recorded": sum(record["input_count"] for record in records),
        "postconditions_holding": sum(1 for record in records if record["postcondition"]["holds"]),
        "replayed_identically": sum(1 for record in records if record["replayed"]),
        "records": [{key: record[key] for key in
                     ("task_id", "capability_id", "input_count", "result_sha256",
                      "replayed", "postcondition")} for record in records],
        "what_this_is_not": [
            "NOT_PRODUCTION_WORK__these are bounded exercises on existing fixtures",
            "NOT_A_LEARNING_UPDATE_OR_VERIFIED_CORPUS_ADMISSION",
            "NOT_INDEPENDENTLY_VERIFIED__the postcondition is the runner's own AST check",
            "NOT_A_BENCHMARK",
            "GATE_IS_PASS_BLIND__run_tests_omitted__baseline_suite_is_red",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)

    report = run()
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("Local fixture exercises, with pre-edit inputs kept (not verified corpus admissions)")
    print("=" * 78)
    print(f"  tasks executed                        {report['tasks']:>4}")
    print(f"  input files recorded                  {report['input_files_recorded']:>4}")
    print(f"  postconditions holding                {report['postconditions_holding']:>4}")
    print(f"  replayed with the same result hash     {report['replayed_identically']:>4}")
    print()
    for row in report["records"]:
        print(f"  {row['task_id']:<22} inputs={row['input_count']}  "
              f"result={row['result_sha256'][:12]}  replayed={row['replayed']}  "
              f"effect={row['postcondition']['holds']}")
    return 0 if (report["postconditions_holding"] == report["tasks"]
                 and report["baseline_preserved"] == report["tasks"]
                 and report["replayed_identically"] == report["tasks"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
