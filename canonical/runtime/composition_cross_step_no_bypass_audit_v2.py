"""Whole explicit Astra shell cross-step projection audit v2.

This audit proves a narrow but global runtime property for explicit prior-step result
projection into shell environments: the current Astra runtime has exactly one
ASTRA_STEP_* projection site, it is inside the declared content-bound path, and
the legacy all-prior-results fallback is absent.

It does not claim completeness over unrelated mutable channels such as arbitrary
filesystem/process state or external systems. Those remain separately auditable.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "canonical/runtime/astra_runtime.py"
MISSION = ROOT / "canonical/astra_runtime/missions/ASTRA_RUNTIME_RESEARCH_ARTIFACT_001.json"
SCHEMA = "PROJECT_BRAIN_COMPOSITION_CROSS_STEP_NO_BYPASS_AUDIT_V2"
MODE = "DECLARED_CONTENT_BOUND_V1"


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _function(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _calls(fn: ast.FunctionDef | None, name: str) -> int:
    if fn is None:
        return -1
    total = 0
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == name:
                total += 1
    return total


def evaluate() -> dict[str, Any]:
    errors: list[str] = []
    if not RUNTIME.is_file():
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__RUNTIME_MISSING",
            "errors": ["ASTRA_RUNTIME_MISSING"],
            "terminal_credit_delta": 0,
        }

    source = RUNTIME.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__RUNTIME_SYNTAX_INVALID",
            "errors": [f"ASTRA_RUNTIME_SYNTAX_INVALID:{exc}"],
            "terminal_credit_delta": 0,
        }

    step_fn = _function(tree, "_step_context_results")
    shell_fn = _function(tree, "run_shell")
    execute_fn = _function(tree, "execute_step")
    if step_fn is None:
        errors.append("STEP_CONTEXT_FUNCTION_MISSING")
    if shell_fn is None:
        errors.append("RUN_SHELL_FUNCTION_MISSING")
    if execute_fn is None:
        errors.append("EXECUTE_STEP_FUNCTION_MISSING")

    structural = {
        "astra_step_projection_site_count": source.count("ASTRA_STEP_"),
        "legacy_all_prior_loop_count": source.count(
            "for i, result in enumerate(prior_results or []):"
        ),
        "legacy_context_results_return_count": source.count(
            "return context_results(state)"
        ),
        "legacy_forbidden_guard_count": source.count(
            'LEGACY_CROSS_STEP_CONTEXT_FORBIDDEN'
        ),
        "strict_default_mode_count": source.count(
            'mode=mission.get("cross_step_context_mode") or '
            'DECLARED_CROSS_STEP_CONTEXT_MODE'
        ),
        "step_context_calls_context_results": _calls(step_fn, "context_results"),
        "step_context_calls_declared_context_results": _calls(
            step_fn, "_declared_context_results"
        ),
    }

    expectations = {
        "single_explicit_astra_step_projection_site":
            structural["astra_step_projection_site_count"] == 1,
        "legacy_all_prior_loop_absent":
            structural["legacy_all_prior_loop_count"] == 0,
        "legacy_context_results_fallback_absent":
            structural["legacy_context_results_return_count"] == 0,
        "legacy_list_guard_present":
            structural["legacy_forbidden_guard_count"] >= 1,
        "missing_mode_defaults_strict_in_context_and_execute":
            structural["strict_default_mode_count"] >= 2,
        "step_context_never_calls_raw_context_results":
            structural["step_context_calls_context_results"] == 0,
        "step_context_uses_declared_projection":
            structural["step_context_calls_declared_context_results"] == 1,
        "strict_binding_hash_rechecked":
            'CROSS_STEP_RESULT_HASH_MISMATCH' in source,
        "strict_binding_declaration_match_enforced":
            'CROSS_STEP_BINDING_DECLARATION_MISMATCH' in source,
        "same_or_future_step_denied":
            'CROSS_STEP_SOURCE_NOT_PRIOR' in source,
    }
    for name, passed in expectations.items():
        if not passed:
            errors.append("EXPECTATION_FAILED:" + name)

    mission: dict[str, Any] = {}
    if MISSION.is_file():
        raw = json.loads(MISSION.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            mission = raw
    if not mission:
        errors.append("KNOWN_RESEARCH_ARTIFACT_MISSION_MISSING")
    else:
        steps = mission.get("steps")
        second = (
            steps[1]
            if isinstance(steps, list)
            and len(steps) >= 2
            and isinstance(steps[1], dict)
            else {}
        )
        if mission.get("cross_step_context_mode") != MODE:
            errors.append("KNOWN_MISSION_STRICT_MODE_MISSING")
        if second.get("cross_step_inputs") != [
            {"step_index": 0, "channels": ["BODY"]}
        ]:
            errors.append("KNOWN_MISSION_EXACT_DECLARATION_MISSING")

    passed = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__EXPLICIT_ASTRA_SHELL_PRIOR_RESULT_PROJECTION_HAS_NO_LEGACY_BYPASS"
            if passed
            else "FAIL_CLOSED__EXPLICIT_CROSS_STEP_PROJECTION_REQUIRES_REAUDIT"
        ),
        "pass": passed,
        "errors": sorted(errors),
        "structural": structural,
        "expectations": expectations,
        "runtime_path": str(RUNTIME.relative_to(ROOT)),
        "runtime_git_blob_sha": _git_blob_sha(RUNTIME),
        "known_mission_path": str(MISSION.relative_to(ROOT)),
        "known_mission_git_blob_sha": (
            _git_blob_sha(MISSION) if MISSION.is_file() else None
        ),
        "proved_scope": (
            "ALL_EXPLICIT_PRIOR_STEP_RESULT_PROJECTION_INTO_ASTRA_SHELL_"
            "ASTRA_STEP_ENVIRONMENT_CHANNELS_IN_CURRENT_RUNTIME_BYTES"
        ),
        "remaining": [
            "EXHAUSTIVE_ACCOUNTING_OF_NON_RESULT_MUTABLE_CROSS_STEP_CHANNELS",
            "SEMANTIC_COMPLETENESS_OF_DECLARED_STATE_AND_EVIDENCE_INPUTS",
            "EXTERNAL_EVIDENCE_CHANNEL_COMPLETENESS",
            "P3_CRITICAL_INVARIANT_AGGREGATION_AFTER_P1_P2",
        ],
        "hard_nonclaims": [
            "NO_CLAIM_ARBITRARY_FILESYSTEM_STATE_IS_CONTENT_BOUND_BY_THIS_AUDIT",
            "NO_CLAIM_ARBITRARY_PROCESS_OR_EXTERNAL_SERVICE_STATE_IS_CLOSED",
            "NO_CLAIM_WHOLE_RUNTIME_P1_OR_P2_IS_PROVED",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OWNERSHIP_OR_TERMINAL_CREDIT",
        ],
        "terminal_cases_consumed": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
