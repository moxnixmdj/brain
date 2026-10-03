"""Zero-task preflight for binding Project Brain's existing Harbor agent to Terminal-Bench-Science 0.1.

This module intentionally consumes no terminal task instruction or result. It checks that the
already-present Brain-owned Harbor control path can be combined with the independently verified
zero-cost local Qwen planner route and the frozen Terminal-Bench-Science carrier without changing
the frozen acceptance predicate.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_BRAIN_ADAPTER_PREFLIGHT_V1"

EXPECTED_BLOBS = {
    "canonical/runtime/harbor_brain_agent.py": "3d7d803bdd25df0379d81b360af3ea40da254771",
    "canonical/runtime/astra_runtime.py": "7f5d16b1db69cb620954bc778e0ba6e15e687b75",
    "canonical/runtime/harbor_command_policy.py": "a525773417291c7a4841bf35e1baff5370350d0d",
    "canonical/verification/TERMINAL_BENCH_SCIENCE_0_1_ZERO_CASE_ROUTE_VERIFICATION_20261002_V1.json": "6ba9d041576c3e4ffad5e0f7310110149be2fe6b",
    "canonical/verification/TOOLATHLON_LOCAL_QWEN_TOOLCALL_PREFLIGHT_20261003_V1.json": "df65f00a46de5570f0366eec5292c9b92b9d03ed",
    "canonical/governance/OPUS55_PUBLIC_BAR_SCORE_READINESS_MATRIX_V1.json": "4e59e30461c9ff1bee1a9474627d5fb4074844b2",
}

REQUIRED_TERMINAL_ENV = {
    "PROJECT_BRAIN_TERMINAL_LOCAL_PLANNER_ONLY": "1",
    "PROJECT_BRAIN_TERMINAL_LOCAL_PLANNER_MODEL": "brain-qwen3.5-9b",
    "PROJECT_BRAIN_TERMINAL_LOCAL_PLANNER_BACKEND": "LOCAL_LLAMA_SERVER",
}


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _load_json(rel: str) -> dict[str, Any]:
    value = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON_OBJECT_REQUIRED:{rel}")
    return value


def _find_tbs_row(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        if value.get("surface") == "Terminal-Bench-Science 0.1":
            return value
        for child in value.values():
            row = _find_tbs_row(child)
            if row is not None:
                return row
    elif isinstance(value, list):
        for child in value:
            row = _find_tbs_row(child)
            if row is not None:
                return row
    return None


def run_preflight() -> dict[str, Any]:
    errors: list[str] = []
    observed_blobs: dict[str, str] = {}

    for rel, expected in EXPECTED_BLOBS.items():
        path = ROOT / rel
        if not path.is_file():
            errors.append(f"MISSING_BOUND_FILE:{rel}")
            continue
        actual = _git_blob_sha(path.read_bytes())
        observed_blobs[rel] = actual
        if actual != expected:
            errors.append(f"BOUND_BLOB_DRIFT:{rel}:{actual}")

    harbor_text = (ROOT / "canonical/runtime/harbor_brain_agent.py").read_text(encoding="utf-8")
    astra_text = (ROOT / "canonical/runtime/astra_runtime.py").read_text(encoding="utf-8")
    policy_text = (ROOT / "canonical/runtime/harbor_command_policy.py").read_text(encoding="utf-8")

    try:
        ast.parse(harbor_text)
        ast.parse(astra_text)
        ast.parse(policy_text)
    except SyntaxError as exc:
        errors.append(f"BOUND_PYTHON_SYNTAX_INVALID:{exc.filename or 'unknown'}:{exc.lineno}")

    harbor_required = [
        "class HarborBrainAgent",
        "run_bounded_harbor_goal",
        "astra_runtime._planner_post",
        "validate_environment_command",
        "HarborEnvironmentTransport",
        "validate_finish",
        'typ not in {"environment_exec","finish"}',
        '"model_has_terminal_authority":False',
        "context.cost_usd=0.0",
    ]
    for token in harbor_required:
        if token not in harbor_text:
            errors.append("HARBOR_CONTROL_TOKEN_MISSING:" + token)

    astra_required = [
        "PROJECT_BRAIN_TERMINAL_LOCAL_PLANNER_ONLY",
        "PROJECT_BRAIN_TERMINAL_LOCAL_PLANNER_MODEL",
        "PROJECT_BRAIN_TERMINAL_LOCAL_PLANNER_BACKEND",
        'models=("local",) if terminal_local_only',
        "TERMINAL_LOCAL_PLANNER_MODEL_IDENTITY_MISMATCH",
        "TERMINAL_LOCAL_PLANNER_BACKEND_IDENTITY_MISMATCH",
        "TERMINAL_LOCAL_PLANNER_BRIDGE_REQUIRED",
    ]
    for token in astra_required:
        if token not in astra_text:
            errors.append("LOCAL_ONLY_PLANNER_GATE_MISSING:" + token)

    for token in ("curl", "wget", "git\\s+(clone|fetch|pull)", "pip|pip3|uv|poetry", "ssh", "scp"):
        if token not in policy_text:
            errors.append("HARBOR_COMMAND_GUARD_MISSING:" + token)

    tbs = _load_json(
        "canonical/verification/TERMINAL_BENCH_SCIENCE_0_1_ZERO_CASE_ROUTE_VERIFICATION_20261002_V1.json"
    )
    if not str(tbs.get("status", "")).startswith("INDEPENDENT_PASS__"):
        errors.append("TBS_ZERO_CASE_ROUTE_NOT_INDEPENDENT_PASS")
    src = tbs.get("source") or {}
    dataset = tbs.get("harbor_dataset") or {}
    carrier = tbs.get("carrier") or {}
    if src.get("tag") != "v0.1.0":
        errors.append("TBS_SOURCE_TAG_DRIFT")
    if src.get("commit") != "f81afac4f11048e77a15dfc8fb1dbfb897fea0ce":
        errors.append("TBS_SOURCE_COMMIT_DRIFT")
    if dataset.get("content_hash") != "sha256:91531bf50016a7c64f6cc60794a17c64c6b2c14858a8ae0de39ca16f2abd611a":
        errors.append("TBS_DATASET_HASH_DRIFT")
    if carrier.get("runner") != "ubuntu-24.04" or carrier.get("local_docker") is not True:
        errors.append("TBS_ZERO_COST_CARRIER_DRIFT")
    if carrier.get("paid_or_larger_runner_required") is not False:
        errors.append("TBS_CARRIER_REQUIRES_NONZERO_OR_LARGER_RESOURCE")
    if tbs.get("terminal_results_observed") != 0:
        errors.append("TBS_PREFLIGHT_ALREADY_OBSERVED_TERMINAL_RESULTS")

    qwen = _load_json(
        "canonical/verification/TOOLATHLON_LOCAL_QWEN_TOOLCALL_PREFLIGHT_20261003_V1.json"
    )
    if not str(qwen.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__"):
        errors.append("LOCAL_QWEN_ROUTE_NOT_INDEPENDENT_PASS")
    route = qwen.get("exact_route") or {}
    observed = qwen.get("observed_contract") or {}
    if route.get("execution_surface") != "PUBLIC_GITHUB_ACTIONS_UBUNTU_24_04":
        errors.append("LOCAL_QWEN_RUNNER_CLASS_MISMATCH")
    if route.get("model_sha256") != "f41c0a0c0e43bf721fb2da29374cd1a97271bac0bab08a9dc42964525e82350c":
        errors.append("LOCAL_QWEN_MODEL_HASH_DRIFT")
    if route.get("model_bytes") != 5060174144:
        errors.append("LOCAL_QWEN_MODEL_SIZE_DRIFT")
    if route.get("incremental_spend_usd") != 0:
        errors.append("LOCAL_QWEN_ROUTE_NONZERO_SPEND")
    if observed.get("openai_chat_completions_status") != 200 or observed.get("structured_tool_calls_present") is not True:
        errors.append("LOCAL_QWEN_OPENAI_CONTRACT_NOT_PROVED")

    readiness = _load_json("canonical/governance/OPUS55_PUBLIC_BAR_SCORE_READINESS_MATRIX_V1.json")
    row = _find_tbs_row(readiness)
    if row is None:
        errors.append("TBS_READINESS_ROW_MISSING")
    else:
        if row.get("brain_route") != "NO_BOUND_GENERAL_BRAIN_AGENT_ADAPTER_FOR_TERMINAL_SCIENCE_TASKS":
            errors.append("TBS_READINESS_PREMISE_ALREADY_CHANGED")
        if row.get("score_producing_route_ready") is not False:
            errors.append("TBS_SCORE_ROUTE_ALREADY_READY")

    passed = not errors
    return {
        "schema": SCHEMA,
        "pass": passed,
        "errors": errors,
        "target_family": "AGENTIC_SCIENTIFIC_RESEARCH",
        "target_predicate": "TB_SCIENCE_GE_58_7",
        "candidate_closes_readiness_gap": (
            "NO_BOUND_GENERAL_BRAIN_AGENT_ADAPTER_FOR_TERMINAL_SCIENCE_TASKS" if passed else None
        ),
        "bound_adapter": "canonical/runtime/harbor_brain_agent.py",
        "bound_surface_receipt": (
            "canonical/verification/TERMINAL_BENCH_SCIENCE_0_1_ZERO_CASE_ROUTE_VERIFICATION_20261002_V1.json"
        ),
        "bound_local_planner_receipt": (
            "canonical/verification/TOOLATHLON_LOCAL_QWEN_TOOLCALL_PREFLIGHT_20261003_V1.json"
        ),
        "required_terminal_env": REQUIRED_TERMINAL_ENV,
        "observed_bound_blob_shas": observed_blobs,
        "terminal_task_content_consumed": False,
        "terminal_result_observed": False,
        "incremental_spend_usd": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "remaining_before_terminal_execution": [
            "INDEPENDENT_EXACT_BYTE_VERIFICATION_OF_THIS_ADAPTER_BINDING",
            "PER_TASK_RESOURCE_FIT_OR_PREDECLARED_RESOURCE_FAILURE_POLICY_PROOF",
            "EXACT_HARBOR_AGENT_REGISTRATION_AND_BOOTSTRAP_IDENTITY_BINDING",
            "POINT_OF_USE_LOCAL_QWEN_MODEL_HASH_AND_BACKEND_RECHECK",
            "PROMOTION_PREFLIGHT_PROVING_A_FROZEN_TB_SCIENCE_SCORE_GE_58_7_IS_ADMISSIBLE_AND_PROMOTES_THE_FAMILY",
            "EXACT_FROZEN_TRIAL_ACCOUNTING_AND_SCORER_IDENTITY_BINDING",
        ],
        "outcome_rule": (
            "NO_TERMINAL_TASK_EXPOSURE_FROM_THIS_PREFLIGHT__"
            "PASS_ONLY_REMOVES_THE_STALE_NO_BOUND_ADAPTER_READINESS_GAP_AFTER_INDEPENDENT_VERIFICATION"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run_preflight(), indent=2, sort_keys=True))
