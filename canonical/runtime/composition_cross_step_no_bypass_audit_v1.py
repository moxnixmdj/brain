"""Deterministic audit of the known Astra mission-runner cross-step bypass.

The original counterexample was a research -> artifact mission whose shell step
received every prior result through ASTRA_STEP_* environment variables without
an explicit dependency declaration. The repaired boundary is intentionally
narrow: strict missions must declare source step indexes and admitted channels,
and the runtime content-binds each selected result before projection.

This audit closes only that concrete bypass class. Whole-runtime P1/P2 closure
still requires exhaustive channel accounting and independent verification.
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
MODE = "DECLARED_CONTENT_BOUND_V1"


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def evaluate() -> dict[str, Any]:
    errors: list[str] = []
    source = RUNTIME.read_text(encoding="utf-8") if RUNTIME.is_file() else ""
    if not source:
        errors.append("ASTRA_RUNTIME_MISSING")

    if MISSION.is_file():
        raw = json.loads(MISSION.read_text(encoding="utf-8"))
        mission = raw if isinstance(raw, dict) else {}
    else:
        mission = {}
    if not mission:
        errors.append("RESEARCH_ARTIFACT_MISSION_MISSING_OR_INVALID")

    required_runtime_fragments = {
        "strict_mode_constant":
            'DECLARED_CROSS_STEP_CONTEXT_MODE="DECLARED_CONTENT_BOUND_V1"',
        "strict_context_builder":
            "def _declared_context_results(state,step,current_step_index):",
        "source_must_be_prior":
            'raise Blocker("CROSS_STEP_SOURCE_NOT_PRIOR:"+str(source))',
        "source_result_content_hash":
            '"result_sha256":hashlib.sha256(raw).hexdigest()',
        "shell_declaration_match":
            'raise Blocker("CROSS_STEP_BINDING_DECLARATION_MISMATCH")',
        "shell_hash_recheck":
            'raise Blocker("CROSS_STEP_RESULT_HASH_MISMATCH:"+str(source))',
        "forward_loop_uses_boundary":
            "result=execute_step(step, _step_context_results(state,mission,i), mission)",
        "rehydration_uses_boundary":
            "result=execute_step(prior, _step_context_results(state,mission,j), mission)",
    }
    runtime_checks = {
        name: fragment in source
        for name, fragment in required_runtime_fragments.items()
    }
    for name, passed in runtime_checks.items():
        if not passed:
            errors.append("RUNTIME_FRAGMENT_MISSING:" + name)

    forbidden_runtime_fragments = {
        "forward_loop_raw_all_context":
            "result=execute_step(step, context_results(state), mission)",
        "rehydration_raw_all_context":
            "result=execute_step(prior, context_results(state), mission)",
    }
    forbidden_runtime_checks = {
        name: fragment not in source
        for name, fragment in forbidden_runtime_fragments.items()
    }
    for name, passed in forbidden_runtime_checks.items():
        if not passed:
            errors.append("RAW_CONTEXT_BYPASS_STILL_PRESENT:" + name)

    steps = mission.get("steps")
    second = (
        steps[1]
        if isinstance(steps, list) and len(steps) >= 2 and isinstance(steps[1], dict)
        else {}
    )
    mission_checks = {
        "strict_mode_enabled":
            mission.get("cross_step_context_mode") == MODE,
        "later_shell_still_consumes_step0_body":
            second.get("adapter") == "shell"
            and "ASTRA_STEP_0_BODY" in str(second.get("command") or ""),
        "step0_body_dependency_declared_exactly":
            second.get("cross_step_inputs")
            == [{"step_index": 0, "channels": ["BODY"]}],
    }
    for name, passed in mission_checks.items():
        if not passed:
            errors.append("MISSION_CHECK_FAILED:" + name)

    repaired = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__KNOWN_RAW_CROSS_STEP_BYPASS_CLOSED_BY_DECLARED_CONTENT_BOUND_PROJECTION"
            if repaired
            else "FAIL_CLOSED__KNOWN_BYPASS_REPAIR_NOT_ESTABLISHED"
        ),
        "known_counterexample_closed": repaired,
        "errors": sorted(errors),
        "runtime_checks": runtime_checks,
        "forbidden_runtime_checks": forbidden_runtime_checks,
        "mission_checks": mission_checks,
        "runtime_path": str(RUNTIME.relative_to(ROOT)),
        "runtime_git_blob_sha": _git_blob_sha(RUNTIME) if RUNTIME.is_file() else None,
        "mission_path": str(MISSION.relative_to(ROOT)),
        "mission_git_blob_sha": _git_blob_sha(MISSION) if MISSION.is_file() else None,
        "scope": (
            "KNOWN_ASTRA_SHELL_CROSS_STEP_RESULT_HANDOFF_USED_BY_EXPLICIT_"
            "RESEARCH_TO_ARTIFACT_PORTFOLIO_MISSION"
        ),
        "implication": (
            "THE_PREVIOUS_CONSTRUCTIVE_COUNTEREXAMPLE_NO_LONGER_FALSIFIES_"
            "NO_BYPASS_FOR_THIS_EXACT_HANDOFF"
        ),
        "remaining": [
            "EXHAUSTIVE_ACCOUNTING_OF_OTHER_MUTABLE_CROSS_STEP_CHANNELS",
            "SEMANTIC_COMPLETENESS_OF_DECLARED_STATE_AND_EVIDENCE_INPUTS",
            "INDEPENDENT_REPOSITORY_NATIVE_VERIFICATION",
            "P3_CRITICAL_INVARIANT_AGGREGATION_AFTER_P1_P2",
        ],
        "hard_nonclaims": [
            "NO_CLAIM_WHOLE_RUNTIME_P1_IS_PROVED",
            "NO_CLAIM_WHOLE_RUNTIME_P2_IS_PROVED",
            "NO_CLAIM_COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES_IS_CLOSED",
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
