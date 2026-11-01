"""Bound capability adapter `software.analysis.diagnose_and_architect.v1`.

Read-only analysis, profiling, race-condition detection, overflow fuzzing,
test-failure root-cause explanation, API/dependency auditing, coverage measurement,
git-history inspection, and architecture/ADR/migration synthesis.
No source write or promotion authority; writes only its declared report artifact.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Mapping

from canonical.swe_kernel import diagnostics_perf_and_design_engine_v1 as engine


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

    if not op or not out_raw:
        raise RuntimeError("DIAGNOSE_ARCHITECT_MISSING_REQUIRED_ARGUMENTS")

    out_path = _safe_path(repo, out_raw, must_exist=False)
    target: pathlib.Path | None = None
    if target_raw and target_raw != ".":
        target = _safe_path(repo, target_raw, must_exist=True)

    if op == "profile_hotspot":
        if target is None:
            raise RuntimeError("PROFILE_TARGET_MISSING")
        res = engine.profile_module_hotspots(target)
    elif op == "benchmark_git_ref":
        if target is None:
            raise RuntimeError("BENCHMARK_TARGET_MISSING")
        res = engine.benchmark_against_git_ref(target, brain_root=repo)
    elif op == "find_race_condition":
        if target is None:
            raise RuntimeError("RACE_TARGET_MISSING")
        res = engine.detect_race_conditions(target)
    elif op == "fuzz_overflow":
        if target is None:
            raise RuntimeError("FUZZ_TARGET_MISSING")
        res = engine.fuzz_integer_overflow(target, fn_name=fn_name)
    elif op in {"diagnose_test_suite", "find_root_cause"}:
        if target is None:
            raise RuntimeError("DIAGNOSE_TARGET_MISSING")
        res = engine.run_suite_and_explain_failures(target)
    elif op == "explain_behavior":
        if target is None:
            raise RuntimeError("EXPLAIN_TARGET_MISSING")
        res = engine.explain_function_behavior(target, fn_name=fn_name, goal=goal_spec)
    elif op == "explain_bug":
        if target is None:
            raise RuntimeError("EXPLAIN_BUG_TARGET_MISSING")
        res = engine.explain_module_bug(target)
    elif op == "security_audit":
        if target is None:
            raise RuntimeError("SECURITY_AUDIT_TARGET_MISSING")
        res = engine.security_audit_package(target)
    elif op == "review_api_design":
        if target is None:
            raise RuntimeError("REVIEW_TARGET_MISSING")
        res = engine.review_api_design(target)
    elif op == "audit_dependencies":
        if target is None:
            raise RuntimeError("AUDIT_TARGET_MISSING")
        res = engine.audit_dependency_vulnerabilities(target)
    elif op == "measure_coverage":
        if target is None:
            raise RuntimeError("COVERAGE_TARGET_MISSING")
        res = engine.measure_package_coverage(target)
    elif op == "find_dead_code":
        if target is None:
            raise RuntimeError("DEAD_CODE_TARGET_MISSING")
        res = engine.find_dead_code_symbols(target)
    elif op == "measure_mutation_score":
        if target is None:
            raise RuntimeError("MUTATION_TARGET_MISSING")
        res = engine.measure_module_mutation_score(target)
    elif op == "lint_javascript":
        if target is None:
            raise RuntimeError("JS_LINT_TARGET_MISSING")
        res = engine.lint_javascript_file(target)
    elif op == "run_js_tests":
        if target is None:
            raise RuntimeError("JS_TEST_TARGET_MISSING")
        res = engine.run_javascript_test_suite(target)
    elif op in {"design_adr", "migration_plan", "package_split_design"}:
        res = engine.synthesize_architecture_artifact(target, goal_spec)
    elif op in {"git_changelog", "git_diff_ref", "git_blame_line"}:
        res = engine.git_read_history_analysis(target or repo, goal_spec, brain_root=repo)
    elif op == "trace_data_flow":
        if target is None:
            raise RuntimeError("TRACE_FLOW_TARGET_MISSING")
        res = engine.trace_intermodule_data_flow(target, goal_spec)
    elif op == "plan_rename":
        if target is None:
            raise RuntimeError("PLAN_RENAME_TARGET_MISSING")
        res = engine.plan_rename_files(target, fn_name, goal_spec, repo_root=repo)
    elif op == "validate_json_schema":
        if target is None:
            raise RuntimeError("JSON_SCHEMA_TARGET_MISSING")
        res = engine.validate_json_config_schema(target, goal_spec)
    elif op == "analyze_log_exception":
        if target is None:
            raise RuntimeError("LOG_TARGET_MISSING")
        res = engine.analyze_log_exception(target, goal_spec)
    elif op == "review_pull_request":
        if target is None:
            raise RuntimeError("PR_REVIEW_TARGET_MISSING")
        res = engine.review_pull_request_changes(target, goal_spec, brain_root=repo)
    elif op == "show_definition":
        if target is None:
            raise RuntimeError("SHOW_DEFINITION_TARGET_MISSING")
        res = engine.show_symbol_definition(target, fn_name, goal_spec, repo_root=repo)
    elif op == "which_modules_import":
        if target is None:
            raise RuntimeError("IMPORTERS_TARGET_MISSING")
        res = engine.find_importing_modules(target, fn_name, goal_spec, repo_root=repo)
    elif op == "import_cycles":
        if target is None:
            raise RuntimeError("IMPORT_CYCLES_TARGET_MISSING")
        res = engine.detect_import_cycles(target, repo_root=repo)
    elif op == "class_hierarchy":
        if target is None:
            raise RuntimeError("CLASS_HIERARCHY_TARGET_MISSING")
        res = engine.inspect_class_hierarchy(target, fn_name, goal_spec, repo_root=repo)
    elif op == "run_single_test":
        if target is None:
            raise RuntimeError("RUN_TEST_TARGET_MISSING")
        res = engine.run_single_test_target(target, goal_spec)
    elif op == "trace_value_provenance":
        if target is None:
            raise RuntimeError("PROVENANCE_TARGET_MISSING")
        res = engine.trace_value_provenance_in_file(target, fn_name, goal_spec)
    elif op == "find_flaky_tests":
        if target is None:
            raise RuntimeError("FLAKY_TEST_TARGET_MISSING")
        res = engine.detect_flaky_tests(target, goal_spec)
    else:
        raise RuntimeError("DIAGNOSE_ARCHITECT_UNSUPPORTED_OPERATION:" + op)

    if not res.get("verified") or res.get("gate") != "PASS":
        raise RuntimeError("DIAGNOSE_ARCHITECT_REFUSED:" + str(res.get("reason") or "UNVERIFIED"))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "PROJECT_BRAIN_SOFTWARE_DIAGNOSE_AND_ARCHITECT_V1",
        "adapter": "software_analysis_diagnose_and_architect_v1",
        **res,
        "output_verified": True,
    }
    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    out_path.write_bytes(raw)
    return {
        **report,
        "output_path": out_path.relative_to(repo).as_posix(),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
    }
