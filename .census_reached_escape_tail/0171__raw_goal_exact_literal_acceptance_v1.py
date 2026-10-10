"""Independent raw-goal acceptance for strict exact-literal responses.

Scope is intentionally tiny:
  Reply/respond with exactly <literal>.

The grammar is delegated to the existing deterministic goal compiler. Acceptance
requires lossless raw-source coverage and an observed model-independent controller
trace whose single finish action and result both equal the requested literal.
Execution success by itself is never acceptance.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping

from canonical.runtime import goal_compiler
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract

SCHEMA = "PROJECT_BRAIN_RAW_GOAL_EXACT_LITERAL_ACCEPTANCE_V1"
ROUTING_EFFECT = "response.exact_literal"


def preflight(goal: str) -> dict[str, Any]:
    compiled = goal_compiler._compile_exact_literal_response_goal(goal)
    if not isinstance(compiled, Mapping):
        return {
            "schema": SCHEMA,
            "status": "NO_MATCH",
            "pass": False,
            "matched": False,
            "semantic_acceptance_complete": False,
            "terminal_authority": False,
        }
    actions = compiled.get("controller_actions")
    if not isinstance(actions, list) or len(actions) != 1:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "matched": False,
            "reason": "EXACT_LITERAL_COMPILED_ACTION_SHAPE_INVALID",
            "semantic_acceptance_complete": False,
            "terminal_authority": False,
        }
    action = actions[0]
    if (
        not isinstance(action, Mapping)
        or action.get("type") != "finish"
        or not isinstance(action.get("args"), Mapping)
        or not isinstance(action["args"].get("summary"), str)
    ):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "matched": False,
            "reason": "EXACT_LITERAL_FINISH_ACTION_INVALID",
            "semantic_acceptance_complete": False,
            "terminal_authority": False,
        }
    literal = action["args"]["summary"]
    return {
        "schema": SCHEMA,
        "status": "EXACT_LITERAL_RAW_GOAL_MATCHED",
        "pass": False,
        "matched": True,
        "literal": literal,
        "literal_sha256": sha256(literal.encode("utf-8")).hexdigest(),
        "goal_sha256": sha256(str(goal).encode("utf-8")).hexdigest(),
        "compiler_mode": compiled.get("compiler_mode"),
        "semantic_acceptance_complete": False,
        "preflight_execution_authority": False,
        "terminal_authority": False,
    }


def verify(*, goal: str, raw_result: Mapping[str, Any]) -> dict[str, Any]:
    pf = preflight(goal)
    if pf.get("matched") is not True:
        return {
            **pf,
            "status": "FAIL_CLOSED__EXACT_LITERAL_GOAL_NOT_MATCHED",
            "accepted_obligation_ids": [],
        }
    if not isinstance(raw_result, Mapping):
        return {
            **pf,
            "status": "FAIL_CLOSED__RAW_RESULT_NOT_OBJECT",
            "accepted_obligation_ids": [],
        }

    contract = compile_contract(
        str(goal),
        source_id="user",
        routing_target_effects=[ROUTING_EFFECT],
    )
    if contract.get("pass") is not True:
        return {
            **pf,
            "status": "FAIL_CLOSED__LOSSLESS_RAW_CONTRACT_INVALID",
            "accepted_obligation_ids": [],
            "contract_errors": contract.get("errors"),
        }
    obligations = contract["acceptance_contract"]["obligations"]
    required_ids = list(contract["acceptance_contract"]["required_obligation_ids"])
    controller = raw_result.get("controller_execution")
    trace = controller.get("trace") if isinstance(controller, Mapping) else None
    literal = pf["literal"]

    trace_ok = (
        isinstance(controller, Mapping)
        and controller.get("returncode") == 0
        and controller.get("controller_mode") == "MODEL_INDEPENDENT_ACTION_PLAN"
        and controller.get("final_summary") == literal
        and isinstance(trace, list)
        and len(trace) == 1
        and isinstance(trace[0], Mapping)
        and isinstance(trace[0].get("plan"), Mapping)
        and trace[0]["plan"].get("type") == "finish"
        and isinstance(trace[0]["plan"].get("args"), Mapping)
        and trace[0]["plan"]["args"].get("summary") == literal
        and isinstance(trace[0].get("result"), Mapping)
        and trace[0]["result"].get("summary") == literal
    )

    full = (
        raw_result.get("pass") is True
        and raw_result.get("compiler_mode") == "DETERMINISTIC_EXACT_LITERAL_RESPONSE"
        and raw_result.get("raw_goal_sha256") == pf["goal_sha256"]
        and raw_result.get("raw_task_contract_sha256") == contract["task_contract_sha256"]
        and raw_result.get("raw_source_coverage_complete") is True
        and raw_result.get("raw_acceptance_obligation_count") == len(obligations)
        and raw_result.get("controller_action_count") == 1
        and raw_result.get("model_dependency_count") == 0
        and raw_result.get("cognition_dependency_class") == "MODEL_INDEPENDENT"
        and trace_ok
        and len(required_ids) == len(obligations)
        and len(required_ids) > 0
    )

    if not full:
        return {
            "schema": SCHEMA,
            "status": "OPEN__EXACT_LITERAL_RAW_ACCEPTANCE_NOT_VERIFIED",
            "pass": False,
            "matched": True,
            "goal_sha256": pf["goal_sha256"],
            "literal_sha256": pf["literal_sha256"],
            "required_obligation_count": len(required_ids),
            "accepted_obligation_ids": [],
            "semantic_acceptance_complete": False,
            "actual_goal_satisfaction_verified": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_LITERAL_RAW_GOAL_ACCEPTED",
        "pass": True,
        "matched": True,
        "goal_sha256": pf["goal_sha256"],
        "literal_sha256": pf["literal_sha256"],
        "required_obligation_count": len(required_ids),
        "accepted_obligation_ids": required_ids,
        "semantic_acceptance_complete": True,
        "actual_goal_satisfaction_verified": True,
        "routing_success_authority": False,
        "acceptance_basis": (
            "STRICT_FULLMATCH_GOAL__LOSSLESS_RAW_SOURCE_COVERAGE__"
            "MODEL_INDEPENDENT_SINGLE_FINISH_TRACE_EQUALS_REQUESTED_LITERAL"
        ),
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
