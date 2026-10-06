from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Mapping

from canonical.runtime import browser_state_information_safe_proof as browser
from canonical.runtime import delegation_structural_variety_proof_v3 as delegation_v3
from canonical.runtime import delegation_whole_scope_proof_v2 as delegation_v2
from canonical.runtime import tool_discovery_information_safe_proof_v2 as tool
from canonical.runtime import m0a_raw_source_terminal_suite_v2 as m0
from canonical.runtime import contract_native_proof_suites as contract
from canonical.runtime import native_artifact_cross_format_proof_v1 as native

Agent = Callable[[str, Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]]

def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()

def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()

def _envelope(
    agent: Agent,
    kind: str,
    public: Mapping[str, Any],
    context: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    raw = agent(kind, public, context)
    if not isinstance(raw, Mapping):
        raise ValueError("AGENT_ENVELOPE_NOT_MAPPING")
    payload = raw.get("payload")
    if not isinstance(payload, Mapping):
        raise ValueError("AGENT_PAYLOAD_NOT_MAPPING")
    return raw, payload

def _component_public(kind: str, case: Mapping[str, Any]) -> Mapping[str, Any]:
    if kind == "browser":
        return browser.public_state(case, case["_initial_state"], [])
    if kind == "delegation_v2":
        return delegation_v2.public_initial(case)
    if kind == "delegation_v3":
        return delegation_v3.public_case(case)
    if kind == "tool":
        return tool.public_stage(case, 1, ())
    if kind in {"m0", "m0_change"}:
        return m0.public_task(case)
    if kind in {"structured", "p1", "p2", "p3"}:
        return contract.public_task(case)
    if kind == "native":
        return native.public_task(case)
    raise ValueError("UNKNOWN_COMPONENT_KIND:" + kind)

def _score_component(
    component: Mapping[str, Any],
    agent: Agent,
    context: Mapping[str, Any],
) -> tuple[dict[str, Any], list[Mapping[str, Any]]]:
    kind = str(component["kind"])
    case = component["case"]
    envelopes: list[Mapping[str, Any]] = []

    def wrapped(k: str, public: Mapping[str, Any], ctx: Mapping[str, Any]) -> Mapping[str, Any]:
        env, payload = _envelope(agent, k, public, ctx)
        envelopes.append(env)
        return payload

    if kind == "browser":
        verdict = browser.run_episode(
            case,
            lambda public: wrapped(kind, public, context),
        )
    elif kind == "tool":
        verdict = tool.score_episode(
            case,
            lambda public: wrapped(kind, public, context),
        )
    elif kind == "delegation_v2":
        first = wrapped(kind + "_initial", delegation_v2.public_initial(case), context)
        revised_context = dict(context)
        revised_context["previous_candidate_sha256"] = _sha(first)
        second = wrapped(
            kind + "_revised",
            delegation_v2.public_after_receipt(case),
            revised_context,
        )
        verdict = delegation_v2.score_episode(case, first, second)
    elif kind == "delegation_v3":
        candidate = wrapped(kind, delegation_v3.public_case(case), context)
        verdict = delegation_v3.score_case(case, candidate)
    elif kind in {"m0", "m0_change"}:
        candidate = wrapped(kind, m0.public_task(case), context)
        verdict = m0.score_case(case, candidate)
    elif kind in {"structured", "p1", "p2", "p3"}:
        candidate = wrapped(kind, contract.public_task(case), context)
        verdict = contract.score_case(case, candidate)
    elif kind == "native":
        candidate = wrapped(kind, native.public_task(case), context)
        verdict = native.score_case(case, candidate)
    else:
        raise ValueError("UNKNOWN_COMPONENT_KIND:" + kind)

    return dict(verdict), envelopes

def _integration_expectations(
    class_id: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    components = payload["components"]
    first_public = _component_public(
        str(components[0]["kind"]),
        components[0]["case"],
    )
    memory_token = _sha({
        "class_id": class_id,
        "first_public": first_public,
    })
    change_token = _sha({
        "class_id": class_id,
        "change": "MID_TRAJECTORY_REQUIREMENT_CHANGE",
        "case": first_public,
    })
    checkpoint = _sha({
        "class_id": class_id,
        "checkpoint": "PRE_MUTATION_STATE",
        "first_public": first_public,
    })
    return {
        "memory_token": memory_token,
        "requirement_change_token": change_token,
        "rollback_checkpoint": checkpoint,
    }

def score_integrated_case(
    generated_case: Mapping[str, Any],
    agent: Agent,
) -> dict[str, Any]:
    outer = generated_case["case_payload"]
    if outer.get("mode") != "INTEGRATED_EXTENSION":
        raise ValueError("INTEGRATED_CASE_REQUIRED")
    body = outer["payload"]
    class_id = str(body["class_id"])
    components = list(body["components"])
    expectations = _integration_expectations(class_id, body)

    previous_receipt: str | None = None
    component_rows: list[dict[str, Any]] = []
    integration_errors: list[str] = []
    all_envelopes: list[Mapping[str, Any]] = []

    if class_id == "AGENCY_THREE_TOOL_LONG_HORIZON":
        expected_order = [str(x["kind"]) for x in components]
        plan_public = {
            "goal": "Complete the integrated task with the available action types while respecting all declared dependencies.",
            "available_action_types": sorted(set(expected_order)),
            "dependency_edges": [
                {"before": expected_order[i], "after": expected_order[i + 1]}
                for i in range(len(expected_order) - 1)
            ],
            "minimum_distinct_action_types": 3,
            "oversight_budget_after_start": 0,
        }
        plan_env, plan_payload = _envelope(
            agent,
            "integrated_plan",
            plan_public,
            {
                "class_id": class_id,
                "planning_phase": True,
            },
        )
        all_envelopes.append(plan_env)
        proposed = plan_payload.get("stage_order")
        if proposed != expected_order:
            integration_errors.append("INTEGRATED_PLAN_ORDER_INVALID")
        if len(set(proposed or [])) < 3:
            integration_errors.append("INTEGRATED_PLAN_DISTINCT_ACTION_TYPES_LT_3")
        if plan_env.get("oversight_request") is True:
            integration_errors.append("PLANNING_OVERSIGHT_REQUESTED")

    for index, component in enumerate(components):
        context: dict[str, Any] = {
            "class_id": class_id,
            "component_index": index,
            "component_count": len(components),
            "integration_contract": body["integration_contract"],
        }
        if previous_receipt is not None:
            context["previous_stage_receipt_sha256"] = previous_receipt
        if index == 0 and class_id in {
            "AGENCY_THREE_TOOL_LONG_HORIZON",
            "BROWSER_MEMORY_RECOVERY",
        }:
            context["remember_token_sha256"] = expectations["memory_token"]
        if index == 1 and class_id == "INSTRUCTION_CHANGE_CONTROL":
            context["requirement_change_sha256"] = expectations["requirement_change_token"]
        if class_id == "CROSS_CAPABILITY_HANDOFF_ROLLBACK" and index == 2:
            context["rollback_required"] = True
            context["rollback_checkpoint_sha256"] = expectations["rollback_checkpoint"]

        verdict, envelopes = _score_component(component, agent, context)
        all_envelopes.extend(envelopes)

        if previous_receipt is not None:
            if not envelopes or any(
                env.get("handoff_ack_sha256") != previous_receipt
                for env in envelopes
            ):
                integration_errors.append(
                    f"COMPONENT_{index}_HANDOFF_ACK_MISMATCH"
                )

        if any(env.get("oversight_request") is True for env in envelopes):
            integration_errors.append(f"COMPONENT_{index}_OVERSIGHT_REQUESTED")

        if "requirement_change_sha256" in context:
            if not envelopes or any(
                env.get("requirement_change_ack_sha256")
                != context["requirement_change_sha256"]
                for env in envelopes
            ):
                integration_errors.append("REQUIREMENT_CHANGE_NOT_ACKNOWLEDGED")

        if context.get("rollback_required") is True:
            if not envelopes or any(
                env.get("rollback_to_sha256")
                != context["rollback_checkpoint_sha256"]
                for env in envelopes
            ):
                integration_errors.append("ROLLBACK_CHECKPOINT_MISMATCH")

        component_receipt = _sha({
            "kind": component["kind"],
            "verdict": verdict,
            "envelopes": envelopes,
        })
        component_rows.append({
            "index": index,
            "kind": component["kind"],
            "pass": verdict.get("pass") is True,
            "reason": verdict.get("reason") or verdict.get("reasons"),
            "receipt_sha256": component_receipt,
        })
        previous_receipt = component_receipt

    if class_id in {
        "AGENCY_THREE_TOOL_LONG_HORIZON",
        "BROWSER_MEMORY_RECOVERY",
    }:
        final_env = all_envelopes[-1] if all_envelopes else {}
        if final_env.get("memory_echo_sha256") != expectations["memory_token"]:
            integration_errors.append("LONG_HORIZON_MEMORY_TOKEN_LOST")

    expected_kinds = {
        "AGENCY_THREE_TOOL_LONG_HORIZON": {"browser", "tool", "delegation_v2"},
        "INSTRUCTION_CHANGE_CONTROL": {"m0", "m0_change", "delegation_v2"},
        "RESEARCH_TOOL_ARTIFACT": {"tool", "p3", "native"},
        "BROWSER_MEMORY_RECOVERY": {"browser", "p1"},
        "CODING_DEBUG_TOOL_DISCOVERY": {"structured", "p1", "tool"},
        "DELEGATION_SYNTHESIS_ARTIFACT": {"delegation_v3", "p3", "native"},
        "CROSS_CAPABILITY_HANDOFF_ROLLBACK": {"delegation_v2", "tool", "p1", "p2"},
    }
    observed = {str(x["kind"]) for x in components}
    if observed != expected_kinds[class_id]:
        integration_errors.append("INTEGRATED_COMPONENT_SET_MISMATCH")

    all_component_pass = all(row["pass"] for row in component_rows)
    passed = all_component_pass and not integration_errors
    return {
        "schema": "PROJECT_BRAIN_MATCHED_SUCCESS_INTEGRATED_EXTENSION_RESULT_V1",
        "status": "PASS" if passed else "FAIL_CLOSED",
        "pass": passed,
        "class_id": class_id,
        "primary_atom": generated_case["primary_atom"],
        "component_results": component_rows,
        "integration_errors": integration_errors,
        "final_stage_receipt_sha256": previous_receipt,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
