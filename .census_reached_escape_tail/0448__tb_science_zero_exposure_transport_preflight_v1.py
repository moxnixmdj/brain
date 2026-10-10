"""Zero-benchmark-exposure live transport preflight for TB-Science.

This module never reads or executes a Terminal-Bench-Science task. It drives the
exact pinned local planner transport with an inert synthetic prompt whose fully
rendered chat/tool payload is at least as large as the observed rank-12 prompt.
Passing proves the repaired control plane can survive the relevant prompt scale;
it grants no benchmark or scientific-capability credit.
"""
from __future__ import annotations

import json
from typing import Any

from canonical.runtime import harbor_science_planner_v1 as planner

SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_ZERO_EXPOSURE_LONG_PROMPT_PREFLIGHT_V1"
TARGET_MIN_INPUT_TOKENS = 7200
TARGET_MAX_INPUT_TOKENS = 7600
MAX_FILLER_UNITS = 12000
MAX_SEARCH_CALLS = 20
REQUESTED_TIMEOUT_S = 300

_BASE = (
    "ZERO-BENCHMARK-EXPOSURE TRANSPORT PREFLIGHT. "
    "This is synthetic control-plane data, not a benchmark task and not scientific evidence. "
    "Return exactly one harmless local proposal candidate. Use material requirement PRECHECK. "
    "The candidate command must be 'printf preflight-ready' and its verify_command must be "
    "'printf preflight-verified'. Do not use files, network, packages, benchmark content, or secrets.\n"
)
_FILLER = "SYNTHETIC_INERT_TRANSPORT_CONTEXT_UNIT "


class PreflightError(RuntimeError):
    pass


def _prompt(units: int) -> str:
    if not isinstance(units, int) or isinstance(units, bool) or units < 0:
        raise PreflightError("PREFLIGHT_FILLER_UNITS_INVALID")
    return _BASE + (_FILLER * units)


def _input_tokens(prompt: str) -> int:
    return planner.count_input_tokens(planner._request_payload(prompt))


def select_prompt() -> tuple[str, int, int]:
    """Find the shortest inert prompt whose exact rendered payload clears the floor."""
    calls = 0
    lo, hi = 0, MAX_FILLER_UNITS
    hi_tokens = _input_tokens(_prompt(hi))
    calls += 1
    if hi_tokens < TARGET_MIN_INPUT_TOKENS:
        raise PreflightError("PREFLIGHT_TARGET_UNREACHABLE")

    best: tuple[str, int] | None = None
    while lo <= hi and calls < MAX_SEARCH_CALLS:
        mid = (lo + hi) // 2
        candidate = _prompt(mid)
        tokens = _input_tokens(candidate)
        calls += 1
        if tokens >= TARGET_MIN_INPUT_TOKENS:
            best = (candidate, tokens)
            hi = mid - 1
        else:
            lo = mid + 1

    if best is None:
        raise PreflightError("PREFLIGHT_PROMPT_SELECTION_FAILED")
    prompt, tokens = best
    if tokens > TARGET_MAX_INPUT_TOKENS:
        raise PreflightError(
            f"PREFLIGHT_TARGET_WINDOW_OVERSHOT:{tokens}>{TARGET_MAX_INPUT_TOKENS}"
        )
    return prompt, tokens, calls


def _validate_proposal(text: str) -> dict[str, Any]:
    obj = planner.normalize_proposal_object(planner.extract_json_object(text))
    reqs = obj.get("material_requirements")
    candidates = obj.get("candidates")
    if not isinstance(reqs, list) or not reqs:
        raise PreflightError("PREFLIGHT_MATERIAL_REQUIREMENTS_MISSING")
    if not isinstance(candidates, list) or len(candidates) != 1:
        raise PreflightError("PREFLIGHT_EXACTLY_ONE_CANDIDATE_REQUIRED")
    row = candidates[0]
    if not isinstance(row, dict):
        raise PreflightError("PREFLIGHT_CANDIDATE_OBJECT_REQUIRED")
    for field in ("action_id", "covers", "command", "verify_command"):
        if field not in row:
            raise PreflightError("PREFLIGHT_CANDIDATE_FIELD_MISSING:" + field)
    return obj


def run_preflight() -> dict[str, Any]:
    prompt, selected_tokens, selection_calls = select_prompt()
    expected_timeout = planner.effective_timeout_s(
        selected_tokens, REQUESTED_TIMEOUT_S
    )
    out = planner.plan(prompt, timeout_s=REQUESTED_TIMEOUT_S)
    observed_tokens = out.get("input_tokens")
    observed_timeout = out.get("effective_timeout_s")
    if observed_tokens != selected_tokens:
        raise PreflightError(
            f"PREFLIGHT_TOKEN_COUNT_NOT_STABLE:{selected_tokens}!={observed_tokens}"
        )
    if observed_timeout != expected_timeout:
        raise PreflightError(
            f"PREFLIGHT_TIMEOUT_NOT_EXACT:{expected_timeout}!={observed_timeout}"
        )
    proposal = _validate_proposal(str(out.get("text") or ""))
    return {
        "schema": SCHEMA,
        "status": "PASS__ZERO_BENCHMARK_EXPOSURE_LONG_PROMPT_TRANSPORT",
        "pass": True,
        "benchmark_task_exposure": 0,
        "benchmark_trials_executed": 0,
        "scientific_capability_credit": 0,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
        "target_min_input_tokens": TARGET_MIN_INPUT_TOKENS,
        "target_max_input_tokens": TARGET_MAX_INPUT_TOKENS,
        "selected_input_tokens": selected_tokens,
        "selection_token_count_calls": selection_calls,
        "observed_input_tokens": observed_tokens,
        "effective_timeout_s": observed_timeout,
        "planner_duration_s": out.get("duration_s"),
        "planner_model": out.get("model"),
        "planner_transport": out.get("transport"),
        "planner_endpoint": out.get("endpoint"),
        "token_count_endpoint": out.get("token_count_endpoint"),
        "proposal_material_requirements": proposal.get("material_requirements"),
        "proposal_candidate_count": len(proposal.get("candidates") or []),
    }


def main() -> int:
    try:
        receipt = run_preflight()
    except Exception as exc:
        receipt = {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__ZERO_EXPOSURE_PREFLIGHT_FAILED",
            "pass": False,
            "benchmark_task_exposure": 0,
            "benchmark_trials_executed": 0,
            "acceptance_credit_delta": 0,
            "terminal_credit_delta": 0,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
