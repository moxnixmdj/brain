"""Fail-closed route admission in front of the live Brain.

Why this exists (measured 2026-10-15, see
``canonical/capabilities/true/LIVE_SOLVER_END_TO_END_MEASUREMENT_20261015_V1.json``):
the deterministic goal compiler selects a bound capability by token overlap.  When a
goal mentions a repository path such as ``canonical/astra_runtime/tmp/x.txt`` the path
components (``runtime``, ``tmp`` ...) become goal tokens, and a capability that needs no
inputs and always reports ``output_verified: true`` (``terminal.kstar.root.assess.stdlib``)
is selected for goals it cannot possibly serve ("Translate ... into French and save it to
.../fr.txt").  The live runtime then executes it and reports PASS.  That is a fail-open.

This module does not change the compiler (its bytes are pinned by governance records).  It
re-derives the compiler's own match evidence and refuses to execute when the evidence is
not about the goal:

  R1  PATH_TOKENS_ONLY         every matched token came from a repository path in the goal
  R2  OUTPUT_ARTIFACT_UNSERVED the goal names a file that does not exist yet (an output the
                               user expects) but the selected capability has no output path
                               input, so it cannot produce it
  R3  WEAK_EVIDENCE            at most one matched prose token: one word is never a goal
  R5  TOOL_TRUTH               after execution, a tool result saying ``pass: false`` or a
                               non-success status (OPEN__, UNRESOLVED, FAIL...) can never
                               surface as an overall PASS

Every rejection is a FAIL_CLOSED result with the evidence attached; nothing is executed,
so no side effect happens.  ``solve`` is the fail-closed entry: compile, admit, then run
``live_integrated_brain_v1.run_raw_goal``.  Zero credit, zero spend, zero models.
"""
from __future__ import annotations

import pathlib
import re
from time import perf_counter_ns
from typing import Any, Mapping

from canonical.runtime import goal_compiler
from canonical.runtime.live_integrated_brain_v1 import (
    ROOT,
    SCHEMA as LIVE_SCHEMA,
    load_verified_registry,
    run_raw_goal,
)

SCHEMA = "PROJECT_BRAIN_LIVE_BRAIN_ROUTE_ADMISSION_V1"
_PATH_RE = re.compile(r"[A-Za-z0-9_./-]+/[A-Za-z0-9_.-]+")


def _prose_tokens(goal: str) -> set[str]:
    """Goal tokens that survive when every repository path is removed from the text.

    A token that occurs only inside a path (``canonical/astra_runtime/tmp/x.txt`` ->
    ``runtime``) is not goal intent.  A token that also occurs in the prose (``archive`` in
    "Create a tar.gz archive ... save it to out.tar.gz") is.
    """
    return goal_compiler._tokens(_PATH_RE.sub(" ", goal))


def _future_artifacts(goal: str) -> list[str]:
    """Repository-relative paths named by the goal that do not exist yet."""
    out = []
    for raw, path in goal_compiler._repo_paths(goal, ROOT):
        if pathlib.Path(raw).suffix and not path.exists():
            out.append(raw)
    return out


def _output_keys(entry: Mapping[str, Any]) -> list[str]:
    keys = goal_compiler._placeholders(entry.get("action_template") or {})
    output_stems = {"output", "result", "report", "screenshot", "image", "artifact", "destination", "dest"}
    return sorted(
        k for k in keys
        if k.endswith("_path") and (k.startswith("output_") or k[:-5].lower() in output_stems)
    )


def route_admission(goal: str, compiled: Mapping[str, Any], registry: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Judge one compiled single-capability route. Returns {"admitted": bool, ...evidence}."""
    selected = str(compiled.get("selected_capability") or "").strip()
    mode = compiled.get("compiler_mode")
    if not selected:
        # Controller plans (literal JSON, exact literal, compound) are shaped by explicit
        # grammar matches, not by token overlap; nothing to re-judge here.
        return {"schema": SCHEMA, "admitted": True, "rule": None, "compiler_mode": mode, "selected_capability": None}
    entry = registry.get(selected)
    if entry is None:
        return {"schema": SCHEMA, "admitted": False, "rule": "SELECTED_CAPABILITY_NOT_ADMISSIBLE", "selected_capability": selected}
    score, specificity, evidence = goal_compiler._score(goal, selected, entry)
    matched = set(evidence.get("matched_provides") or []) | set(evidence.get("matched_identity") or []) | set(evidence.get("matched_keywords") or [])
    prose = _prose_tokens(goal)
    semantic = matched & prose
    input_keys = goal_compiler._placeholders(entry.get("action_template") or {})
    output_keys = _output_keys(entry)
    futures = _future_artifacts(goal)
    base = {
        "schema": SCHEMA,
        "compiler_mode": mode,
        "selected_capability": selected,
        "score": score,
        "matched_tokens": sorted(matched),
        "matched_from_paths_only": sorted(matched - prose),
        "semantic_matched_tokens": sorted(semantic),
        "goal_future_artifacts": futures,
        "capability_input_keys": sorted(input_keys),
        "capability_output_keys": output_keys,
    }
    if matched and not semantic:
        return {**base, "admitted": False, "rule": "R1_PATH_TOKENS_ONLY"}
    if futures and not output_keys:
        return {**base, "admitted": False, "rule": "R2_OUTPUT_ARTIFACT_UNSERVED"}
    if len(semantic) <= 1:
        return {**base, "admitted": False, "rule": "R3_WEAK_EVIDENCE"}
    return {**base, "admitted": True, "rule": None}


_NON_SUCCESS_PREFIXES = ("FAIL", "OPEN", "UNRESOLVED", "ERROR", "BLOCKED", "REJECTED", "INCOMPLETE")


def tool_truth_errors(result: Mapping[str, Any]) -> list[str]:
    """R5: the executed tool's own verdict wins over the controller's "it returned".

    The live runtime marks a raw goal PASS when the controller returned 0 and the first
    trace step produced a mapping.  Several bound tools write a report that says
    ``pass: false`` / ``status: OPEN__...`` / ``UNRESOLVED`` while still setting
    ``output_verified: true`` (they verified that they wrote their own failure report).
    That must never surface as PASS.
    """
    errors: list[str] = []
    rows = result.get("execution") if isinstance(result.get("execution"), list) else []
    for row in rows:
        inner = row.get("result") if isinstance(row, Mapping) else None
        if not isinstance(inner, Mapping):
            continue
        status = str(inner.get("status") or inner.get("outcome") or "").upper()
        if inner.get("pass") is False:
            errors.append("TOOL_REPORTED_PASS_FALSE:" + str(row.get("capability_id")))
        elif status.startswith(_NON_SUCCESS_PREFIXES):
            errors.append("TOOL_REPORTED_NON_SUCCESS_STATUS:" + str(row.get("capability_id")) + ":" + status[:48])
    return errors


def solve(request: Mapping[str, Any]) -> dict[str, Any]:
    """Fail-closed live Brain entry: compile -> admit -> execute (run_raw_goal)."""
    started = perf_counter_ns()
    task_id = str((request or {}).get("task_id") or "").strip()
    goal = str((request or {}).get("goal") or "").strip()
    if not task_id or not goal:
        return {"schema": LIVE_SCHEMA, "status": "FAIL_CLOSED", "pass": False, "task_id": task_id,
                "failure_class": "REQUEST_INVALID", "elapsed_ns": perf_counter_ns() - started, "incremental_spend_usd": 0}
    try:
        registry = load_verified_registry()
        admissible = goal_compiler._platform_admissible_registry(dict(registry))
        compiled = goal_compiler.compile_goal(goal, admissible, ROOT)
    except goal_compiler.GoalCompilationFailure as exc:
        return {"schema": LIVE_SCHEMA, "status": "FAIL__RAW_GOAL_COMPILATION_GAP", "pass": False, "task_id": task_id,
                "failure_class": "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP", "compiler_code": exc.code, "compiler_detail": exc.detail,
                "route_admission": None, "elapsed_ns": perf_counter_ns() - started, "incremental_spend_usd": 0}
    except Exception as exc:  # pragma: no cover - defensive, mirrors run_raw_goal
        return {"schema": LIVE_SCHEMA, "status": "FAIL_CLOSED", "pass": False, "task_id": task_id,
                "failure_class": "RAW_GOAL_INTEGRATION_RUNTIME_ERROR", "reason": type(exc).__name__ + ":" + str(exc),
                "elapsed_ns": perf_counter_ns() - started, "incremental_spend_usd": 0}
    admission = route_admission(goal, compiled, admissible)
    if admission.get("admitted") is not True:
        return {"schema": LIVE_SCHEMA, "status": "FAIL_CLOSED__ROUTE_ADMISSION_REJECTED", "pass": False, "task_id": task_id,
                "failure_class": "ROUTE_ADMISSION_REJECTED:" + str(admission.get("rule")), "compiled_capability_id": admission.get("selected_capability"),
                "compiler_mode": compiled.get("compiler_mode"), "route_admission": admission, "executed": False,
                "elapsed_ns": perf_counter_ns() - started, "incremental_spend_usd": 0}
    result = run_raw_goal({"task_id": task_id, "goal": goal})
    result["route_admission"] = admission
    truth = tool_truth_errors(result)
    if truth and result.get("pass") is True:
        result["runtime_status_before_truth_check"] = result.get("status")
        result["status"] = "FAIL_CLOSED__TOOL_REPORTED_NON_SUCCESS"
        result["pass"] = False
        result["failure_class"] = "TOOL_REPORTED_NON_SUCCESS"
        result["tool_truth_errors"] = truth
        result["side_effects_may_exist"] = True
    return result
