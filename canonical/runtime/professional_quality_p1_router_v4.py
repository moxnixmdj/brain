"""Professional Quality P1 Router V4.

V4 removes caller self-attestation for the first profile step:
COMPILE_TARGET_SPEC_AND_HARD_CONSTRAINTS.

The step is executed by the Brain through the bounded, content-addressed R1
professional target-instance compiler. All later P1 steps retain V3/V2 behavior
until they are similarly internalized. This is deliberate incremental closure,
not a claim that the whole professional-quality loop is autonomous.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_p1_router_v3 as legacy
from canonical.runtime import professional_target_instance_compiler_v1 as target_compiler

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_ROUTER_V4"
TARGET_STEP = "COMPILE_TARGET_SPEC_AND_HARD_CONSTRAINTS"
PREFLIGHT_STEP = legacy.PREFLIGHT_STEP


def _base(status: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "quality_judgment_authority": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "new_root_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "capability_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return _base("FAIL_CLOSED", reason=reason, **extra)


def route(
    state: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(state, Mapping):
        return _fail("STATE_NOT_OBJECT")
    try:
        if not legacy._profile_ok(repo_root):
            return _fail("PROFILE_ROUTER_CONTRACT_DRIFT")
    except Exception:
        return _fail("PROFILE_LOAD_FAILURE")

    supplied = state.get("step_results", {})
    if not isinstance(supplied, Mapping):
        return _fail("STEP_RESULTS_NOT_OBJECT")
    if TARGET_STEP in supplied:
        return _fail("TARGET_STEP_SELF_ATTESTATION_FORBIDDEN")

    target_instance = state.get("target_instance")
    if not isinstance(target_instance, Mapping):
        return _base(
            "ABSTAIN__P1_INCOMPLETE",
            route="ABSTAIN",
            blocking_steps=[TARGET_STEP],
            target_step_self_attestation_allowed=False,
            target_instance_compiled_by_brain=False,
        )

    target = target_compiler.compile_target(
        target_instance,
        repo_root=repo_root,
    )
    if (
        target.get("pass") is not True
        or target.get("r1_target_step_verified") is not True
        or target.get("terminal_authority") is not False
    ):
        return _base(
            "ABSTAIN__P1_TARGET_SPEC_UNRESOLVED",
            route="ABSTAIN",
            blocking_steps=[TARGET_STEP],
            target_compilation_result=target,
            target_step_self_attestation_allowed=False,
            target_instance_compiled_by_brain=True,
        )

    delegated = deepcopy(dict(state))
    delegated.pop("target_instance", None)
    delegated_results = deepcopy(dict(supplied))
    delegated_results[TARGET_STEP] = "PASS"
    delegated["step_results"] = delegated_results

    out = legacy.route(delegated, repo_root=repo_root)
    result = deepcopy(dict(out))
    result["schema"] = SCHEMA
    result["target_compilation_result"] = target
    result["target_step_self_attestation_allowed"] = False
    result["target_instance_compiled_by_brain"] = True
    result["r1_target_step_verified"] = True
    result["r1_target_instance_sha256"] = target.get("target_instance_sha256")
    result["quality_judgment_authority"] = False
    result["semantic_truth_authority"] = False
    result["acceptance_authority"] = False
    result["promotion_authority"] = False
    result["terminal_authority"] = False
    result["terminal_credit_delta"] = 0
    result["capability_credit_delta"] = 0
    result["incremental_spend_usd"] = 0
    return result


def run(
    args: Mapping[str, Any] | None = None,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    return route(args or {}, repo_root=repo_root)
