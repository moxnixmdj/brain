"""Deterministic counterexample audit for composition cross-step no-bypass.

This audit proves only that the current Astra mission runtime exposes a prior
step result to a later shell step outside composition_state_capsule_v1/v2.
It does not claim that every composition route uses this channel.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "canonical/runtime/astra_runtime.py"
MISSION = ROOT / "canonical/astra_runtime/missions/ASTRA_RUNTIME_RESEARCH_ARTIFACT_001.json"
SCHEMA = "PROJECT_BRAIN_COMPOSITION_CROSS_STEP_NO_BYPASS_AUDIT_V1"


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def evaluate() -> dict[str, Any]:
    errors: list[str] = []
    if not RUNTIME.is_file():
        errors.append("ASTRA_RUNTIME_MISSING")
        source = ""
    else:
        source = RUNTIME.read_text(encoding="utf-8")

    if not MISSION.is_file():
        errors.append("RESEARCH_ARTIFACT_MISSION_MISSING")
        mission: dict[str, Any] = {}
    else:
        value = json.loads(MISSION.read_text(encoding="utf-8"))
        mission = value if isinstance(value, dict) else {}
        if not mission:
            errors.append("RESEARCH_ARTIFACT_MISSION_INVALID")

    required_runtime_fragments = {
        "context_results_collects_history":
            'for rec in state.get("history",[]):',
        "mission_loop_passes_all_context":
            "result=execute_step(step, context_results(state), mission)",
        "shell_receives_prior_results":
            "return run_shell(step, prior_results)",
        "shell_exports_result_json":
            'prefix+"RESULT_JSON"',
        "shell_exports_body":
            'prefix+"BODY"',
        "shell_exports_stdout":
            'prefix+"STDOUT"',
    }
    runtime_checks = {
        name: fragment in source
        for name, fragment in required_runtime_fragments.items()
    }
    for name, passed in runtime_checks.items():
        if not passed:
            errors.append("RUNTIME_FRAGMENT_MISSING:" + name)

    steps = mission.get("steps")
    mission_checks = {
        "two_or_more_steps": isinstance(steps, list) and len(steps) >= 2,
        "first_step_http": (
            isinstance(steps, list)
            and len(steps) >= 1
            and isinstance(steps[0], dict)
            and steps[0].get("adapter") == "http"
        ),
        "later_shell_consumes_step0_body": (
            isinstance(steps, list)
            and len(steps) >= 2
            and isinstance(steps[1], dict)
            and steps[1].get("adapter") == "shell"
            and "ASTRA_STEP_0_BODY" in str(steps[1].get("command") or "")
        ),
    }
    for name, passed in mission_checks.items():
        if not passed:
            errors.append("MISSION_CHECK_FAILED:" + name)

    capsule_bound_at_shell_boundary = (
        "composition_state_capsule_v1" in source
        or "composition_state_capsule_v2" in source
    )
    if capsule_bound_at_shell_boundary:
        errors.append("CAPSULE_REFERENCE_PRESENT_REQUIRES_MANUAL_REAUDIT")

    counterexample_holds = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__CURRENT_ASTRA_CROSS_STEP_CHANNEL_FALSIFIES_NO_BYPASS_PREMISE"
            if counterexample_holds
            else "FAIL_CLOSED__SOURCE_OR_SCOPE_DRIFT_REQUIRES_REAUDIT"
        ),
        "counterexample_holds": counterexample_holds,
        "errors": sorted(errors),
        "runtime_checks": runtime_checks,
        "mission_checks": mission_checks,
        "capsule_bound_at_shell_boundary": capsule_bound_at_shell_boundary,
        "runtime_path": str(RUNTIME.relative_to(ROOT)),
        "runtime_git_blob_sha": _git_blob_sha(RUNTIME) if RUNTIME.is_file() else None,
        "mission_path": str(MISSION.relative_to(ROOT)),
        "mission_git_blob_sha": _git_blob_sha(MISSION) if MISSION.is_file() else None,
        "scope": (
            "ASTRA_SHELL_CROSS_STEP_RESULT_HANDOFF_USED_BY_EXPLICIT_"
            "RESEARCH_TO_ARTIFACT_PORTFOLIO_MISSION"
        ),
        "implication": (
            "COMPOSITION_STATE_CAPSULE_P1_P2_NO_BYPASS_INTEGRATION_PREMISE_"
            "IS_FALSE_FOR_THIS_RUNTIME_SCOPE_UNTIL_RESTRICTED_OR_INTEGRATED"
        ),
        "hard_nonclaims": [
            "NO_CLAIM_ALL_COMPOSITION_ROUTES_USE_THIS_CHANNEL",
            "NO_CLAIM_WHOLE_COMPOSITION_FAMILY_FAILS",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
        "new_reality_units_consumed": 0,
        "terminal_cases_consumed": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
