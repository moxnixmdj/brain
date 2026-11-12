#!/usr/bin/env python3
"""Does the registered acceptance predicate accept a repair that failed? Execute and see.

Round 5 showed statically that nine capabilities compute a boolean answer into `pass` while the
registry accepts on `output_verified`, which the adapter sets to True on every path that returns.
This probe removes the word "statically": it builds a workspace whose only test **cannot** be
satisfied by any bounded mutation, runs each adapter for real, and applies both predicates to the
object the adapter actually returned.

Round 7 repointed the nine capabilities from `output_verified` to `pass`. This probe is now a
regression test in both directions: the **live registry** must reject the failure, and the
**legacy predicate** (kept here as a constant, not as live configuration) must still accept it —
so the evidence for why the repoint happened survives the repoint.

LEGACY_EXPECT is the predicate as it stood at fea6498c. It is data in this file, never read back
into the registry.

Authority NONE. Deterministic. Zero model dependency. Each adapter runs with a cut-down candidate
budget (seconds, not minutes) because the point is the *failure* path, not a repair.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import shutil
import sys
import tempfile
import time
from typing import Any, Mapping

REPO_ROOT = pathlib.Path(__file__).resolve().parent
REGISTRY = REPO_ROOT / "canonical" / "runtime" / "BOUND_CAPABILITY_REGISTRY_V1.json"
SEARCH_DIRS = (
    REPO_ROOT / "canonical" / "runtime" / "bound_capabilities",
    REPO_ROOT / "canonical" / "runtime",
)

#: A source file that is wrong, and a test that no single bounded AST mutation can satisfy.
#: `square(3) == 999` is unreachable from `return x` by mutation, literal substitution, or the
#: coupled pair search, so every adapter must report the honest "no repair" answer.
FIXTURE: dict[str, str] = {
    "calc.py": "def square(x):\n    return x\n",
    "test_calc.py": (
        "from calc import square\n\n\n"
        "def test_square():\n"
        "    assert square(3) == 999\n"
    ),
}

TEST_PATHS = ["test_calc.py"]

#: The predicate these nine capabilities carried at fea6498c, before the repoint. Kept as a
#: constant so the probe can show what the old gate would have done, without configuring anything.
LEGACY_EXPECT: dict[str, Any] = {"type": "field_equals", "field": "output_verified", "value": True}
TASK_TEXT = "make test_calc.py pass"

#: capability_id -> (adapter module, args). Every one of these is a DEFINITE case in round 5.
CASES: dict[str, tuple[str, dict[str, Any]]] = {
    "python.patch.search.test_guided.ast.v1": (
        "python_test_guided_patch_search_v1",
        {"source_path": "calc.py", "test_paths": TEST_PATHS,
         "output_path": "out/patch_search.json", "max_candidates": 200, "timeout_s": 20},
    ),
    "python.software.repair.loop.coupled.ast.v1": (
        "python_coupled_software_repair_loop_v1",
        {"source_root": ".", "test_paths": TEST_PATHS,
         "output_path": "out/coupled.json", "max_files": 4, "mutations_per_file": 8,
         "max_symbols_per_file": 4, "max_pair_candidates": 60, "timeout_s": 20},
    ),
    "python.software.repair.loop.strict_progress.ast.v1": (
        "python_iterative_software_repair_loop_v1",
        {"source_root": ".", "test_paths": TEST_PATHS,
         "output_path": "out/strict.json", "max_rounds": 2, "max_files": 4,
         "max_candidates_per_file": 20, "max_total_candidates": 80, "timeout_s": 20},
    ),
    "python.software.repair.loop.test_guided.ast.v1": (
        "python_software_repair_loop_v1",
        {"source_root": ".", "test_paths": TEST_PATHS,
         "output_path": "out/test_guided.json", "timeout_s": 20},
    ),
    "python.software.repair.guided.provenance.coupled.v1": (
        "python_provenance_guided_coupled_repair_v1",
        {"source_root": ".", "test_paths": TEST_PATHS,
         "output_path": "out/provenance.json", "max_guided_files": 4, "max_control_files": 4,
         "mutations_per_file": 8, "max_pair_candidates": 60,
         "max_guided_symbols_per_file": 4, "max_control_symbols_per_file": 4, "timeout_s": 20},
    ),
    "python.software.repair.measured_acceptance.v1": (
        "python_repair_measured_acceptance_controller_v1",
        {"source_root": ".", "test_paths": TEST_PATHS, "task_text": TASK_TEXT,
         "output_path": "out/measured.json", "timeout_s": 20},
    ),
    "python.software.repair.semantic_acceptance.v1": (
        "python_repair_semantic_acceptance_controller_v1",
        {"source_root": ".", "test_paths": TEST_PATHS, "task_text": TASK_TEXT,
         "output_path": "out/semantic.json", "timeout_s": 20},
    ),
    "python.software.request.semantic_behavior.compile.v1": (
        "python_software_request_semantic_acceptance_v1",
        {"task_text": "add a square function that returns x*x",
         "output_path": "out/request.json"},
    ),
}


def _load(module_name: str):
    for directory in SEARCH_DIRS:
        path = directory / f"{module_name}.py"
        if path.exists():
            spec = importlib.util.spec_from_file_location(module_name, str(path))
            if spec is None or spec.loader is None:
                raise ImportError(module_name)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise FileNotFoundError(module_name)


def _expect_for(capability_id: str) -> Mapping[str, Any]:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return registry["capabilities"][capability_id]["action_template"]["expect"]


def apply_predicate(expect: Mapping[str, Any], result: Mapping[str, Any]) -> bool:
    """The registry's own semantics, implemented once so both sides use the same code."""
    kind = expect.get("type")
    field = expect.get("field")
    if kind == "field_equals":
        return result.get(field) == expect.get("value")
    raise ValueError(f"UNSUPPORTED_EXPECT_TYPE:{kind}")


def _materialise() -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp(prefix="failed_repair_"))
    for name, body in FIXTURE.items():
        (root / name).write_text(body, encoding="utf-8")
    return root


def _one(capability_id: str, module_name: str, args: Mapping[str, Any]) -> dict[str, Any]:
    root = _materialise()
    started = time.time()
    try:
        module = _load(module_name)
        result = module.run(dict(args), str(root))
    except Exception as exc:  # an adapter that cannot run is not evidence either way
        return {
            "capability_id": capability_id,
            "adapter_module": module_name,
            "ran": False,
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_s": round(time.time() - started, 2),
        }
    finally:
        shutil.rmtree(root, ignore_errors=True)

    expect = _expect_for(capability_id)
    return {
        "capability_id": capability_id,
        "adapter_module": module_name,
        "ran": True,
        "passed": bool(result.get("pass")),
        "output_verified": result.get("output_verified"),
        "status": result.get("status"),
        "registry_expect": dict(expect),
        "registry_accepts": apply_predicate(expect, result),
        "legacy_expect": dict(LEGACY_EXPECT),
        "legacy_accepts": apply_predicate(LEGACY_EXPECT, result),
        # `corrected` is the outcome predicate; the live registry now equals it for these eight.
        "corrected_expect": {"type": "field_equals", "field": "pass", "value": True},
        "corrected_accepts": apply_predicate(
            {"type": "field_equals", "field": "pass", "value": True}, result
        ),
        "declared_result_fields": (
            "pass" in (json.loads(REGISTRY.read_text(encoding="utf-8"))
                       ["capabilities"][capability_id].get("result_fields") or [])
        ),
        "elapsed_s": round(time.time() - started, 2),
    }


def run() -> dict[str, Any]:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    records = [_one(cid, mod, args) for cid, (mod, args) in CASES.items()]
    ran = [r for r in records if r["ran"]]
    return {
        "probe": "gate_accepts_a_failed_repair",
        "authority": "NONE",
        "executed": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "fixture": FIXTURE,
        "fixture_note": (
            "square(3) == 999 is unreachable from 'return x' by single AST mutation, test-literal "
            "substitution, or the bounded two-edit pair search, so every adapter must answer "
            "'no repair'."
        ),
        "records": records,
        "summary": {
            "capabilities": len(records),
            "ran": len(ran),
            "failed_to_run": len(records) - len(ran),
            "honest_answer_no_repair": sum(1 for r in ran if r["passed"] is False),
            "legacy_accepts_the_failure": sum(1 for r in ran if r["legacy_accepts"] is True),
            "registry_rejects_the_failure": sum(
                1 for r in ran if r["registry_accepts"] is False
            ),
            "registry_reads_the_outcome": sum(
                1 for r in ran if r["registry_expect"].get("field") == "pass"
            ),
            "output_verified_true": sum(1 for r in ran if r["output_verified"] is True),
            "pass_declared_in_result_fields": sum(
                1 for r in ran if r["declared_result_fields"]
            ),
        },
        "hard_nonclaims": [
            "NO_CAPABILITY_RE_REGISTERED",
            "NO_ADAPTER_CHANGED",
            "NO_ACCEPTANCE_CREDIT",
            "NO_TRUTH_ACHIEVED",
            "NO_GENERAL_REPAIR_COMPLETENESS",
            "MEASURES_THE_FAILURE_PATH_ONLY",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    parser.add_argument("--list", action="store_true", help="print every executed record")
    args = parser.parse_args(argv)

    report = run()
    s = report["summary"]
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("The gate, fed a repair that provably cannot succeed")
    print("=" * 72)
    print(f"  adapters executed                                        {s['ran']:>4}")
    print(f"  reported the honest answer (pass == False)               "
          f"{s['honest_answer_no_repair']:>4}")
    print(f"  set output_verified == True anyway                       "
          f"{s['output_verified_true']:>4}")
    print(f"  the LEGACY predicate accepted the failure                "
          f"{s['legacy_accepts_the_failure']:>4}")
    print(f"  the LIVE registry predicate rejects it                   "
          f"{s['registry_rejects_the_failure']:>4}")
    print(f"  ...with 'pass' declared in the capability's result_fields "
          f"{s['pass_declared_in_result_fields']:>3}")
    if s["failed_to_run"]:
        print(f"  adapters that could not run                              {s['failed_to_run']:>4}")

    if args.list:
        print()
        for r in report["records"]:
            if not r["ran"]:
                print(f"  SKIP      {r['capability_id']:<52}{r['error'][:40]}")
                continue
            verdict = "ACCEPTED" if r["registry_accepts"] else "rejected"
            legacy = "old:accepted" if r["legacy_accepts"] else "old:rejected"
            print(f"  {verdict:<9}{legacy:<13}{r['capability_id']:<52}{str(r['status'])[:44]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
