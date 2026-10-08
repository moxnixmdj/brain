"""Zero-benchmark-exposure live multi-action transport preflight for TB-Science V8.

This module never reads, enumerates, or executes a Terminal-Bench-Science task.
It exercises the exact current local planner transport at rank-12-class prompt
scale and requires one structured proposal containing three harmless synthetic
actions, including one explicit dependency and bounded timeout fields.
"""
from __future__ import annotations

import json
from typing import Any

from canonical.runtime import harbor_science_planner_v1 as planner

SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_ZERO_EXPOSURE_MULTI_ACTION_PREFLIGHT_V1"
TARGET_MIN_INPUT_TOKENS = 7200
TARGET_MAX_INPUT_TOKENS = 7600
MAX_FILLER_UNITS = 12000
MAX_SEARCH_CALLS = 20
REQUESTED_TIMEOUT_S = 300

_BASE = (
    "ZERO-BENCHMARK-EXPOSURE MULTI-ACTION TRANSPORT PREFLIGHT. "
    "This is synthetic control-plane data, not a benchmark task and not scientific evidence. "
    "Use exactly the three material requirements PRECHECK_A, PRECHECK_B, PRECHECK_C. "
    "Return exactly three harmless local candidates in one proposal. "
    "Candidate PREFLIGHT_A must cover PRECHECK_A, have command 'printf preflight-a', "
    "and verify_command 'printf verify-a'. "
    "Candidate PREFLIGHT_B must cover PRECHECK_B, depend_on exactly ['PREFLIGHT_A'], "
    "set timeout_sec to 1200 and verify_timeout_sec to 300, "
    "have command 'printf preflight-b', and verify_command 'printf verify-b'. "
    "Candidate PREFLIGHT_C must cover PRECHECK_C, have no dependency, "
    "have command 'printf preflight-c', and verify_command 'printf verify-c'. "
    "Do not use files, network, packages, benchmark content, or secrets.\n"
)
_FILLER = "SYNTHETIC_INERT_MULTI_ACTION_CONTEXT_UNIT "


class PreflightError(RuntimeError):
    pass


def _prompt(units: int) -> str:
    if not isinstance(units, int) or isinstance(units, bool) or units < 0:
        raise PreflightError("PREFLIGHT_FILLER_UNITS_INVALID")
    return _BASE + (_FILLER * units)


def _input_tokens(prompt: str) -> int:
    return planner.count_input_tokens(planner._request_payload(prompt))


def select_prompt() -> tuple[str, int, int]:
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
    if obj.get("material_requirements") != ["PRECHECK_A", "PRECHECK_B", "PRECHECK_C"]:
        raise PreflightError("PREFLIGHT_MATERIAL_REQUIREMENTS_NOT_EXACT")
    candidates = obj.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 3:
        raise PreflightError("PREFLIGHT_EXACTLY_THREE_CANDIDATES_REQUIRED")
    by_id = {row.get("action_id"): row for row in candidates if isinstance(row, dict)}
    if set(by_id) != {"PREFLIGHT_A", "PREFLIGHT_B", "PREFLIGHT_C"}:
        raise PreflightError("PREFLIGHT_ACTION_IDS_NOT_EXACT")
    expected = {
        "PREFLIGHT_A": {
            "covers": ["PRECHECK_A"],
            "command": "printf preflight-a",
            "verify_command": "printf verify-a",
        },
        "PREFLIGHT_B": {
            "covers": ["PRECHECK_B"],
            "depends_on": ["PREFLIGHT_A"],
            "timeout_sec": 1200,
            "verify_timeout_sec": 300,
            "command": "printf preflight-b",
            "verify_command": "printf verify-b",
        },
        "PREFLIGHT_C": {
            "covers": ["PRECHECK_C"],
            "command": "printf preflight-c",
            "verify_command": "printf verify-c",
        },
    }
    for aid, fields in expected.items():
        row = by_id[aid]
        for field, value in fields.items():
            if row.get(field) != value:
                raise PreflightError(f"PREFLIGHT_FIELD_NOT_EXACT:{aid}:{field}")
        if aid in {"PREFLIGHT_A", "PREFLIGHT_C"} and row.get("depends_on") not in (None, []):
            raise PreflightError(f"PREFLIGHT_UNEXPECTED_DEPENDENCY:{aid}")
    return obj


def run_preflight() -> dict[str, Any]:
    prompt, selected_tokens, selection_calls = select_prompt()
    expected_timeout = planner.effective_timeout_s(selected_tokens, REQUESTED_TIMEOUT_S)
    out = planner.plan(prompt, timeout_s=REQUESTED_TIMEOUT_S)
    if out.get("input_tokens") != selected_tokens:
        raise PreflightError(
            f"PREFLIGHT_TOKEN_COUNT_NOT_STABLE:{selected_tokens}!={out.get('input_tokens')}"
        )
    if out.get("effective_timeout_s") != expected_timeout:
        raise PreflightError(
            f"PREFLIGHT_TIMEOUT_NOT_EXACT:{expected_timeout}!={out.get('effective_timeout_s')}"
        )
    proposal = _validate_proposal(str(out.get("text") or ""))
    return {
        "schema": SCHEMA,
        "status": "PASS__ZERO_BENCHMARK_EXPOSURE_MULTI_ACTION_LONG_PROMPT_TRANSPORT",
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
        "observed_input_tokens": out.get("input_tokens"),
        "effective_timeout_s": out.get("effective_timeout_s"),
        "planner_duration_s": out.get("duration_s"),
        "planner_model": out.get("model"),
        "planner_transport": out.get("transport"),
        "planner_endpoint": out.get("endpoint"),
        "token_count_endpoint": out.get("token_count_endpoint"),
        "proposal_candidate_count": len(proposal["candidates"]),
        "proposal_action_ids": sorted(row["action_id"] for row in proposal["candidates"]),
        "dependency_edge_verified": proposal["candidates"][
            next(i for i,r in enumerate(proposal["candidates"]) if r["action_id"]=="PREFLIGHT_B")
        ].get("depends_on") == ["PREFLIGHT_A"],
    }


def main() -> int:
    try:
        receipt = run_preflight()
    except Exception as exc:
        receipt = {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__ZERO_EXPOSURE_MULTI_ACTION_PREFLIGHT_FAILED",
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
