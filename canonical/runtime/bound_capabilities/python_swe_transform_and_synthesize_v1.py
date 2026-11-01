"""Bound capability adapter `python.swe.transform_and_synthesize.v1`.

Strict Python writer capability executing e-graph equality-saturation speedups,
memoization, thread-pool & GIL-releasing native kernels, unit/Hypothesis/mutation
test synthesis, CLI/logging/retry features, structural module refactors, and
standalone-repository git write operations. Rolls back on any test failure.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Mapping

from canonical.swe_kernel import egraph_and_deductive_synthesizer_v1 as engine


def _safe_path(repo: pathlib.Path, raw: str, *, must_exist: bool = True) -> pathlib.Path:
    if not raw or not isinstance(raw, str):
        raise RuntimeError("MISSING_OR_INVALID_PATH_ARGUMENT")
    p = (repo / raw).resolve()
    if p != repo and repo not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY:" + raw)
    if must_exist and not p.exists():
        raise RuntimeError("PATH_MISSING:" + raw)
    return p


def run(args: Mapping[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    op = str(args.get("operation") or "").strip()
    target_raw = str(args.get("target_path") or "").strip()
    out_raw = str(args.get("output_path") or "").strip()
    goal_spec = str(args.get("request_spec") or op).strip()
    fn_raw = str(args.get("symbol") or "").strip()
    fn_name = None if fn_raw in {"", "auto"} else fn_raw

    if not op or not target_raw or not out_raw:
        raise RuntimeError("PYTHON_SWE_MISSING_REQUIRED_ARGUMENTS")

    target = _safe_path(repo, target_raw, must_exist=True)
    out_path = _safe_path(repo, out_raw, must_exist=False)
    test_raw = str(args.get("test_target") or args.get("test_file_path") or "").strip()
    explicit_test = _safe_path(repo, test_raw, must_exist=False) if test_raw and test_raw != "auto" else None
    sec_raw = str(args.get("secondary_path") or "").strip()
    secondary_target = _safe_path(repo, sec_raw, must_exist=True) if sec_raw else None
    if secondary_target is None and op == "crossfile_feature":
        for cand_py in __import__("re").findall(r"[A-Za-z0-9_./-]+\.py", goal_spec):
            if cand_py != target_raw:
                try:
                    cp = _safe_path(repo, cand_py, must_exist=True)
                    if cp != target and not cp.name.startswith("test_"):
                        secondary_target = cp
                        break
                except RuntimeError:
                    continue

    if op == "optimize_function":
        res = engine.egraph_optimize_function(target, fn_name=fn_name)
    elif op == "memoize_function":
        res = engine.memoize_function(target, fn_name=fn_name)
    elif op == "add_thread_pool":
        res = engine.add_thread_pool_parallel(target, fn_name=fn_name)
    elif op == "release_gil":
        res = engine.release_gil_sum_kernel(target, fn_name=fn_name)
    elif op in {
        "write_unit_test", "write_property_test", "write_regression_test",
        "advance_mutation_kill", "tests_from_docstrings", "raise_coverage",
        "add_benchmark", "parallel_test_suite",
    }:
        res = engine.author_verified_tests(target, goal_spec, explicit_test_path=explicit_test, fn_name=fn_name)
    elif op in {
        "add_cli_flag", "add_logging", "add_retries", "implement_issue", "crossfile_feature",
        "add_error_handling", "sqlalchemy_model", "add_fastapi_endpoint", "add_http_client",
        "harden_path_traversal", "add_counter_metric", "make_async",
    }:
        res = engine.synthesize_feature_transform(target, goal_spec, secondary_target=secondary_target)
    elif op in {
        "split_module", "replace_deprecated", "add_type_hints", "extract_constant",
        "format_python", "remove_dead_code", "lint_and_fix", "move_module", "safe_helper_refactor",
        "remove_unused_imports", "inline_function", "fix_memory_leak",
    }:
        res = engine.structural_refactor_python(target, goal_spec)
    elif op in {"git_commit", "git_branch_and_commit", "git_cherry_pick", "git_worktree", "git_revert", "git_rebase"}:
        res = engine.git_write_surgeon(target, goal_spec, brain_root=repo)
    else:
        raise RuntimeError("PYTHON_SWE_UNSUPPORTED_OPERATION:" + op)

    if not res.get("verified") or res.get("gate") != "PASS":
        raise RuntimeError("PYTHON_SWE_REFUSED:" + str(res.get("reason") or "UNVERIFIED"))

    tf_str = str(res.get("target_file") or "")
    written_target = pathlib.Path(tf_str).resolve() if tf_str else None
    if written_target is not None and out_path == written_target:
        out_path = out_path.with_name(out_path.name + ".report.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "schema": "PROJECT_BRAIN_PYTHON_SWE_TRANSFORM_SYNTHESIZE_V1",
        "adapter": "python_swe_transform_and_synthesize_v1",
        **res,
        "output_verified": True,
    }
    if written_target is not None and (written_target == repo or repo in written_target.parents):
        report["target_relpath"] = written_target.relative_to(repo).as_posix()

    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    out_path.write_bytes(raw)
    return {
        **report,
        "output_path": out_path.relative_to(repo).as_posix(),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
    }
