#!/usr/bin/env python3
"""Run six existing Python diff-review gates against one task-bound change.

This is a local review aid, not a sandbox or independent attestation. Some
stages execute project tests, plugins, configuration and benchmark code as
ordinary host processes. Execution is disabled unless the caller explicitly
sets ``allow_unsafe_host_execution`` to the boolean True. Even with that opt-in,
the reported gates cannot prove behavior, isolation, or security. Filesystem
snapshots detect persistent changes, not transient effects or external writes.

Required inputs: repository-relative ``anchor_path``, ``diff_path`` and
``output_path`` (the output must be outside the anchor); a ``bench_path``
relative to the anchor defining ``bench()``; and a non-empty ``run_tests``
list of anchor-relative Python test files. Optional direct-call controls are
``python_executable``, ``timeout_s``, ``max_wall_time_s``, ``max_mutants``,
``repeats`` and ``tolerance``. Every stage must observe the same diff and pass;
execution stops at the first failure. Time budgets are soft, not process-tree
or filesystem-copy limits.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping

from canonical.runtime.bound_capabilities import (
    python_repository_acceptance_measurement_v1 as measurement,
    python_review_diff_static_triage as lint,
    python_review_diff_type_gate as types,
    python_review_diff_security_gate as security,
    python_review_diff_coverage_gate as coverage,
    python_review_diff_mutation_gate as mutation,
    python_review_diff_perf_gate as perf,
)
from canonical.runtime.bound_capabilities.python_review_diff_static_triage import _parse_diff_ranges

SCHEMA = "PROJECT_BRAIN_SOFTWARE_REVIEW_GATE_COMPOSER_V1"
CAPABILITY_ID = "software.review.gate.composer.v1"
PROVIDES = ["software.review.all_gates.verified", "software.review.composition.typed"]
# The composer consumes the explicitly bound diff, anchor and tests directly;
# it does not depend on a separate choreography claim.
REQUIRES: list[str] = []
GATES = (
    ("lint", lint), ("types", types), ("security", security),
    ("coverage", coverage), ("mutation", mutation), ("performance", perf),
)
_IGNORE = shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache")


def _inside(repo: Path, value: Any, label: str, *, must_exist: bool = False) -> Path:
    if not isinstance(value, (str, Path)) or not str(value):
        raise ValueError(label + "_REQUIRED")
    path = (repo / value).resolve()
    if path == repo or repo not in path.parents:
        raise ValueError(label + "_OUTSIDE_REPOSITORY")
    if must_exist and not path.exists():
        raise ValueError(label + "_MISSING")
    return path


def _manifest(tree: Path) -> tuple[list[dict[str, Any]], str]:
    rows, _ = measurement._tree_manifest(tree, max_files=50000, max_bytes=512 * 1024 * 1024)
    # Executable modes are relevant to project inputs, too.
    for row in rows:
        row["mode"] = (tree / row["path"]).stat().st_mode & 0o7777
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return rows, digest


def _write(output: Path, repo: Path, artifact: dict[str, Any]) -> dict[str, Any]:
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=".brain-review-result-", dir=output.parent, delete=False) as f:
        name = f.name
        try:
            f.write(raw)
            f.flush()
        except BaseException:
            Path(name).unlink(missing_ok=True)
            raise
    try:
        os.replace(name, output)
    finally:
        Path(name).unlink(missing_ok=True)
    return {"adapter": "software_review_gate_composer_v1", "output_path": str(output.relative_to(repo)),
            "output_sha256": hashlib.sha256(raw).hexdigest(), "output_verified": output.read_bytes() == raw,
            "verified": artifact["verified"], "gates_verified": artifact["gates_verified"],
            "status": artifact["status"], "model_dependency_count": 0, "incremental_spend_usd": 0}


def run(args: Mapping[str, Any], root: str | Path) -> dict[str, Any]:
    if not isinstance(args, Mapping):
        raise ValueError("ARGS_NOT_OBJECT")
    repo = Path(root).resolve()
    output = _inside(repo, args.get("output_path") or "canonical/tmp_review_composer.json", "OUTPUT")
    registry = (repo / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").resolve()
    if (output == registry or (output.exists() and registry.exists() and output.samefile(registry))
            or (output.is_file() and (output.suffix == ".py" or output.stat().st_nlink > 1))):
        raise RuntimeError("OUTPUT_OVERLAPS_INPUT")
    artifact: dict[str, Any] = {
        "schema": SCHEMA, "capability_id": CAPABILITY_ID, "stages": [],
        "verified": False, "gates_verified": False,
        "status": "OPEN__UNSAFE_HOST_EXECUTION_NOT_AUTHORIZED",
        "host_execution_is_sandboxed": False, "independent_attestation": False,
        "model_dependency_count": 0, "incremental_spend_usd": 0,
    }
    if args.get("allow_unsafe_host_execution") is not True:
        return _write(output, repo, artifact)

    anchor = _inside(repo, args.get("anchor_path"), "ANCHOR", must_exist=True)
    diff = _inside(repo, args.get("diff_path"), "DIFF", must_exist=True)
    if not anchor.is_dir() or not diff.is_file():
        raise ValueError("INVALID_ANCHOR_OR_DIFF")
    if output == anchor or anchor in output.parents:
        raise RuntimeError("OUTPUT_INSIDE_ANCHOR")
    if output == diff or (output.exists() and output.samefile(diff)):
        raise RuntimeError("OUTPUT_OVERLAPS_INPUT")
    bench_arg = args.get("bench_path")
    if not isinstance(bench_arg, str) or not bench_arg or bench_arg.startswith("-"):
        raise ValueError("BENCH_PATH_REQUIRED")
    bench = (anchor / bench_arg).resolve()
    if anchor not in bench.parents or not bench.is_file() or bench.suffix != ".py":
        raise ValueError("BENCH_PATH_INVALID")
    tests = args.get("run_tests")
    if not isinstance(tests, list) or not tests:
        raise ValueError("TEST_PATHS_REQUIRED")
    test_paths = []
    for name in tests:
        if not isinstance(name, str) or not name or name.startswith("-"):
            raise ValueError("TEST_PATH_INVALID")
        path = (anchor / name).resolve()
        if anchor not in path.parents or not path.is_file() or path.suffix != ".py":
            raise ValueError("TEST_PATH_INVALID")
        rel = str(path.relative_to(anchor))
        if rel not in test_paths:
            test_paths.append(rel)
    timeout = float(args.get("timeout_s") if args.get("timeout_s") is not None else 120)
    budget = float(args.get("max_wall_time_s") if args.get("max_wall_time_s") is not None else 120)
    mutants = int(args.get("max_mutants") if args.get("max_mutants") is not None else 2000)
    repeats = int(args.get("repeats") if args.get("repeats") is not None else 5)
    tolerance = float(args.get("tolerance") if args.get("tolerance") is not None else 0.1)
    if (not math.isfinite(timeout) or not 0 < timeout <= 3600 or not math.isfinite(budget)
            or not 0 < budget <= 3600 or not 0 < mutants <= 20000 or not 3 <= repeats <= 50
            or not math.isfinite(tolerance) or not 0 <= tolerance <= 100):
        raise ValueError("INVALID_RESOURCE_LIMIT")
    python = str(args.get("python_executable") or sys.executable)
    raw_diff = diff.read_bytes()
    if not raw_diff.strip():
        raise ValueError("DIFF_EMPTY")
    try:
        changed, _ = _parse_diff_ranges(raw_diff.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError("DIFF_NOT_UTF8") from exc
    if not any(path.endswith(".py") for path in changed):
        raise ValueError("NO_PYTHON_CHANGES")
    diff_sha = hashlib.sha256(raw_diff).hexdigest()
    started = time.monotonic()
    _, anchor_sha = _manifest(anchor)  # rejects symlinks and bounded oversized trees
    artifact.update({"anchor_path": str(anchor.relative_to(repo)), "anchor_sha256": anchor_sha,
                     "diff_path": str(diff.relative_to(repo)), "diff_sha256": diff_sha,
                     "bench_path": str(bench.relative_to(anchor)), "run_tests": test_paths,
                     "status": "OPEN__REVIEW_INCOMPLETE"})
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".brain-review-", dir=output.parent) as temporary:
        temp = Path(temporary)
        patched = temp / "patched"
        shutil.copytree(anchor, patched, ignore=_IGNORE)
        diff_copy = temp / "task.diff"
        diff_copy.write_bytes(raw_diff)
        for check in (True, False):
            remaining = budget - (time.monotonic() - started)
            if remaining <= 0:
                artifact["status"] = "OPEN__WALL_TIME_BUDGET_EXHAUSTED"
                return _write(output, repo, artifact)
            argv = ["git", "apply"] + (["--check"] if check else []) + ["-"]
            try:
                process = subprocess.run(argv, input=raw_diff, cwd=patched, capture_output=True,
                                         timeout=min(timeout, remaining))
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise RuntimeError("DIFF_APPLY_UNAVAILABLE") from exc
            if process.returncode != 0:
                raise ValueError("DIFF_DOES_NOT_APPLY")
        _, patched_sha = _manifest(patched)
        for name, module in GATES:
            remaining = budget - (time.monotonic() - started)
            if remaining <= 0:
                artifact["status"] = "OPEN__WALL_TIME_BUDGET_EXHAUSTED"
                break
            stage_dir = temp / name
            stage_dir.mkdir()
            stage_output = stage_dir / "report.json"
            stage_args: dict[str, Any] = {
                "diff_path": str(diff_copy.relative_to(repo)),
                "output_path": str(stage_output.relative_to(repo)),
                "python_executable": python, "timeout_s": max(1, int(min(timeout, remaining))),
            }
            if name in ("lint", "types", "security"):
                stage_args["worktree_path"] = str(patched.relative_to(repo))
            else:
                stage_args["anchor_path"] = str(anchor.relative_to(repo))
            if name == "coverage":
                stage_args.update(run_tests=test_paths, min_coverage_ratio=1.0)
            elif name == "mutation":
                stage_args.update(run_tests=test_paths, min_kill_ratio=1.0, max_mutants=mutants,
                                  max_wall_time_s=min(remaining, 3600))
            elif name == "performance":
                stage_args.update(bench_path=str(bench.relative_to(anchor)), repeats=repeats, tolerance=tolerance)
            stage: dict[str, Any] = {"name": name, "gate": "ERROR", "verified": False}
            try:
                result = module.run(stage_args, repo)
                stage_raw = stage_output.read_bytes()
                detail = json.loads(stage_raw)
                result_ok = (isinstance(result, dict) and isinstance(detail, dict)
                             and result.get("output_verified") is True
                             and result.get("output_sha256") == hashlib.sha256(stage_raw).hexdigest()
                             and result.get("diff_sha256") == diff_sha and detail.get("diff_sha256") == diff_sha
                             and result.get("gate") == "PASS" and detail.get("gate") == "PASS"
                             and result.get("verified") is True and result.get("complete") is True
                             and detail.get("complete") is True and time.monotonic() - started <= budget)
                if name == "mutation":
                    result_ok = result_ok and result.get("mutants_generated", 0) > 0
                anchor_intact = _manifest(anchor)[1] == anchor_sha
                patched_intact = _manifest(patched)[1] == patched_sha
                diff_intact = diff.is_file() and diff.read_bytes() == raw_diff and diff_copy.read_bytes() == raw_diff
                stage.update({"gate": result.get("gate", "ERROR"), "verified": bool(result_ok and anchor_intact
                              and patched_intact and diff_intact), "input_integrity": bool(anchor_intact and patched_intact
                              and diff_intact), "result": {k: v for k, v in result.items() if k != "output_path"},
                              "detail": detail})
            except (SystemExit, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
                stage["error"] = str(exc)[:600]
            artifact["stages"].append(stage)
            if not stage["verified"]:
                artifact["status"] = "OPEN__REVIEW_GATE_FAILED_OR_UNOBSERVED"
                break
        if len(artifact["stages"]) == len(GATES) and all(s["verified"] for s in artifact["stages"]):
            artifact.update(status="ALL_LOCAL_REVIEW_GATES_PASS", verified=True, gates_verified=True)
    return _write(output, repo, artifact)
