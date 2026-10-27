"""Content-addressed repository-derived acceptance measurements.

This capability measures an isolated copy of one repository-local source root.
It does not trust caller-supplied acceptance fields. The measured source tree,
measurement program, and measurement specification are content-addressed.

Task success is NOT inferred here. This module only emits objective measurements.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping
import importlib.util


def _load_patch_search():
    """The shared module that owns how a suite is executed.

    Imported by path rather than by package name, matching how every other adapter in this
    directory reaches it.
    """
    here = pathlib.Path(__file__).with_name('python_test_guided_patch_search_v1.py')
    spec = importlib.util.spec_from_file_location('_brain_patch_search', here)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_PATCH = _load_patch_search()



SCHEMA = "PROJECT_BRAIN_PYTHON_REPOSITORY_ACCEPTANCE_MEASUREMENT_V1"
CAPABILITY_ID = "python.repository.acceptance.measure.v1"
MODEL_DEPENDENCY_COUNT = 0
EXTERNAL_MODEL_RUNTIME_CALLS = 0

MEASUREMENT_SCHEMA = {
    "tests_pass": {"type": "boolean", "dimension": "dimensionless"},
    "test_returncode": {"type": "integer", "dimension": "dimensionless"},
    "test_count": {"type": "integer", "dimension": "count"},
    "python_parse_ok": {"type": "boolean", "dimension": "dimensionless"},
    "python_file_count": {"type": "integer", "dimension": "count"},
    "repository_source_unchanged": {"type": "boolean", "dimension": "dimensionless"},
}


class MeasurementError(RuntimeError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_obj(value: Any) -> str:
    return _sha_bytes(_canon(value).encode("utf-8"))


def _safe_dir(repo: pathlib.Path, raw: Any) -> pathlib.Path:
    p = (repo / str(raw or ".")).resolve()
    if p != repo and repo not in p.parents:
        raise MeasurementError("SOURCE_ROOT_OUTSIDE_REPOSITORY")
    if not p.is_dir() or p.is_symlink():
        raise MeasurementError("SOURCE_ROOT_INVALID")
    return p


def _safe_output(repo: pathlib.Path, raw: Any) -> pathlib.Path:
    p = (repo / str(raw or "")).resolve()
    if p == repo or repo not in p.parents:
        raise MeasurementError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    return p


def _rel(root: pathlib.Path, path: pathlib.Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _tree_manifest(root: pathlib.Path, *, max_files: int, max_bytes: int) -> tuple[list[dict[str, Any]], str]:
    rows = []
    total = 0
    for path in sorted(root.rglob("*")):
        if any(part in {".git", "__pycache__", ".pytest_cache"} for part in path.parts):
            continue
        if path.is_symlink():
            raise MeasurementError("SYMLINK_IN_MEASURED_TREE:" + _rel(root, path))
        if not path.is_file():
            continue
        raw = path.read_bytes()
        total += len(raw)
        if len(rows) + 1 > max_files:
            raise MeasurementError("MEASURED_TREE_FILE_LIMIT")
        if total > max_bytes:
            raise MeasurementError("MEASURED_TREE_BYTE_LIMIT")
        rows.append({
            "path": _rel(root, path),
            "bytes": len(raw),
            "sha256": _sha_bytes(raw),
        })
    if not rows:
        raise MeasurementError("MEASURED_TREE_EMPTY")
    return rows, _sha_obj(rows)


def _validate_test_paths(source_root: pathlib.Path, values: Any, repo: pathlib.Path | None = None) -> list[str]:
    """Resolve each stated test path, accepting either spelling of the same path.

    The compiler binds repository-relative paths -- it states
    ``canonical/.../test_calc.py`` -- while this adapter has always read paths
    relative to ``source_root``.  Those are two spellings of one question, and
    refusing the compiler's spelling made the capability unreachable from the
    front door with ``TEST_PATH_INVALID`` even though the sentence named a real
    test file that really is inside the stated source root.

    Both spellings are tried; whichever names a real file inside ``source_root``
    wins.  Containment, regular-file, non-symlink and ``.py`` checks are applied
    to the resolved path exactly as before, so nothing outside the stated source
    root can be measured, and when ``source_root`` is the repository itself the
    two spellings coincide and behaviour is unchanged.
    """
    if not isinstance(values, list) or not values:
        raise MeasurementError("TEST_PATHS_REQUIRED")
    out = []
    for raw in values:
        if not isinstance(raw, str) or not raw:
            raise MeasurementError("TEST_PATH_INVALID")
        spellings = [(source_root / raw).resolve()]
        if repo is not None:
            spellings.append((repo / raw).resolve())
        p = next(
            (c for c in spellings
             if source_root in c.parents and c.is_file() and not c.is_symlink()
             and c.suffix == ".py"),
            None,
        )
        if p is None:
            raise MeasurementError("TEST_PATH_INVALID:" + str(raw))
        rel = _rel(source_root, p)
        if rel not in out:
            out.append(rel)
    return out


def _validate_argv(values: Any, test_paths: list[str],
                   source_root: pathlib.Path | None = None,
                   repo: pathlib.Path | None = None) -> list[str]:
    argv = values
    if argv is None:
        # Executing a test file as a script only starts the tests when the file carries a __main__
        # guard, and 695 of the 2019 unittest files in this repository (34%, measured) do not.
        # Such a run exits 0 having executed nothing, which this measurement then records as
        # returncode 0 with test_count 0 - clean evidence for a repository whose suite fails.
        argv = _PATCH.suite_argv(sys.executable, *test_paths)
    if not isinstance(argv, list) or not argv or any(not isinstance(x, str) or not x for x in argv):
        raise MeasurementError("TEST_ARGV_INVALID")
    exe = pathlib.Path(argv[0]).name.lower()
    allowed = {pathlib.Path(sys.executable).name.lower(), "python", "python3", "py"}
    if exe not in allowed:
        raise MeasurementError("TEST_EXECUTABLE_NOT_PYTHON")
    argv = [str(x) for x in argv]
    if source_root is None:
        return argv
    # The caller states repository-relative paths, but this measurement runs in a
    # COPIED workspace with that workspace as its cwd -- so a token naming
    # ``canonical/.../test_calc.py`` names nothing there, the suite runner loads
    # no tests, and the measurement records returncode 1 with test_count 0 for a
    # suite that passes.  A token naming one of the already-validated test files
    # is therefore rewritten to the workspace-relative name, exactly as the repair
    # controller's candidate layout does.  Only tokens that resolve to a
    # validated test file are touched; every other argument, including a whole
    # harness program carried in one token, passes through verbatim.
    by_abs = {}
    for rel in test_paths:
        by_abs[(source_root / rel).resolve()] = rel
    bases = [b for b in (repo, source_root) if b is not None]
    rewritten = []
    for token in argv:
        hit = None
        for base in bases:
            try:
                candidate = (base / token).resolve()
            except OSError:
                continue
            if candidate in by_abs:
                hit = by_abs[candidate]
                break
        rewritten.append(hit if hit is not None else token)
    return rewritten


def _python_parse_measurement(workspace: pathlib.Path) -> tuple[bool, int, list[dict[str, str]]]:
    errors = []
    count = 0
    for path in sorted(workspace.rglob("*.py")):
        if any(part in {"__pycache__", ".pytest_cache"} for part in path.parts):
            continue
        if path.is_symlink():
            errors.append({"path": _rel(workspace, path), "error": "SYMLINK"})
            continue
        count += 1
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except Exception as exc:
            errors.append({"path": _rel(workspace, path), "error": type(exc).__name__})
    return not errors, count, errors


def _run_tests(workspace: pathlib.Path, argv: list[str], timeout_s: int) -> dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONHASHSEED"] = "0"
    started = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            cwd=workspace,
            text=True,
            capture_output=True,
            timeout=timeout_s,
            env=env,
        )
        return {
            "returncode": int(proc.returncode),
            "timed_out": False,
            "elapsed_s": round(time.monotonic() - started, 6),
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": 124,
            "timed_out": True,
            "elapsed_s": round(time.monotonic() - started, 6),
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }


def _test_count(text: str) -> int:
    m = re.search(r"Ran\s+(\d+)\s+tests?", text)
    return int(m.group(1)) if m else 0


def _copy_source(source_root: pathlib.Path, workspace: pathlib.Path) -> None:
    shutil.copytree(
        source_root,
        workspace,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".pytest_cache"),
    )


def run(args: Mapping[str, Any], root: str | os.PathLike[str]) -> dict[str, Any]:
    if not isinstance(args, Mapping):
        raise MeasurementError("ARGS_NOT_OBJECT")
    repo = pathlib.Path(root).resolve()
    source_root = _safe_dir(repo, args.get("source_root", "."))
    output = _safe_output(repo, args.get("output_path"))
    timeout_s = max(1, min(int(args.get("timeout_s", 60)), 300))
    max_files = max(1, min(int(args.get("max_files", 5000)), 20000))
    max_bytes = max(1024, min(int(args.get("max_bytes", 100_000_000)), 500_000_000))
    test_paths = _validate_test_paths(source_root, args.get("test_paths"), repo)
    argv = _validate_argv(args.get("test_argv"), test_paths, source_root, repo)

    before_manifest, before_sha = _tree_manifest(
        source_root, max_files=max_files, max_bytes=max_bytes
    )

    with tempfile.TemporaryDirectory(prefix="brain-measure-") as td:
        workspace = pathlib.Path(td) / "workspace"
        _copy_source(source_root, workspace)
        parse_ok, python_file_count, parse_errors = _python_parse_measurement(workspace)
        test = _run_tests(workspace, argv, timeout_s)
        combined = (test["stdout"] or "") + "\n" + (test["stderr"] or "")
        count = _test_count(combined)

    after_manifest, after_sha = _tree_manifest(
        source_root, max_files=max_files, max_bytes=max_bytes
    )
    source_unchanged = before_manifest == after_manifest and before_sha == after_sha
    if not source_unchanged:
        raise MeasurementError("SOURCE_ROOT_MUTATED_DURING_MEASUREMENT")

    measurements = {
        "tests_pass": test["returncode"] == 0 and not test["timed_out"],
        "test_returncode": int(test["returncode"]),
        "test_count": int(count),
        "python_parse_ok": bool(parse_ok),
        "python_file_count": int(python_file_count),
        "repository_source_unchanged": True,
    }
    program_sha = _sha_bytes(pathlib.Path(__file__).read_bytes())
    spec = {
        "source_root": _rel(repo, source_root) if source_root != repo else ".",
        "test_paths": test_paths,
        "test_argv": argv,
        "timeout_s": timeout_s,
        "max_files": max_files,
        "max_bytes": max_bytes,
    }
    payload = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "status": "PASS__CONTENT_ADDRESSED_REPOSITORY_MEASUREMENT",
        "pass": True,
        "subject": {
            "source_root": spec["source_root"],
            "snapshot_sha256": before_sha,
            "manifest": before_manifest,
        },
        "measurement_program_sha256": program_sha,
        "measurement_spec": spec,
        "measurement_spec_sha256": _sha_obj(spec),
        "measurement_schema": MEASUREMENT_SCHEMA,
        "measurements": measurements,
        "test_evidence": {
            "returncode": test["returncode"],
            "timed_out": test["timed_out"],
            "test_count": count,
            "stdout_sha256": _sha_bytes((test["stdout"] or "").encode("utf-8")),
            "stderr_sha256": _sha_bytes((test["stderr"] or "").encode("utf-8")),
        },
        "python_parse_errors": parse_errors,
        "model_dependency_count": 0,
        "external_general_purpose_model_runtime_dependency_count": 0,
        "incremental_spend_usd": 0,
        "hard_nonclaims": [
            "MEASUREMENT_SUCCESS_IS_NOT_TASK_ACCEPTANCE",
            "TEST_PASS_IS_NOT_COMPLETE_REQUEST_SEMANTICS",
            "MEASURES_ONLY_THE_DECLARED_SOURCE_ROOT_AND_TEST_COMMAND",
            "NO_BENCHMARK_SCORE_OR_TERMINAL_AUTHORITY",
        ],
        "terminal_authority": False,
    }
    payload["receipt_payload_sha256"] = _sha_obj(payload)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    raw = output.read_bytes()
    return {
        **payload,
        "output_path": _rel(repo, output),
        "output_sha256": _sha_bytes(raw),
        "output_verified": True,
    }
