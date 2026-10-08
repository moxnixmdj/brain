"""Universal Verified Adaptive Solver V1.

One control loop for Brain-owned capability composition.

Architecture:
    explicit task contract
      -> exact capability planner
      -> untrusted proposal packet(s)
      -> immutable built-in verifier adapter
      -> accept / falsify / request more information
      -> update explicit state only after verification
      -> replan
      -> finish when target effects are verified

This module deliberately does not call a model. A general cognition substrate may
prepare proposal packets, but proposals have zero authority. Verifier adapters are
module-owned and immutable. New verifier kinds require code review plus tests.

Task-contract semantics and source authority remain upstream obligations. External
side effects are not considered successful merely because they are proposed or
semantically authorized; carrier/outcome verification remains separate.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import base64
import json
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.capability_planner import PlanningFailure, plan_capabilities
from canonical.runtime.p2_authenticated_top_law_route_v1 import execute as p2_execute
from canonical.runtime.judgment_control_envelope_v1 import configured_terminal_decision
from canonical.runtime.proof_carrying_semantic_refinement_v6 import resolve_from_source_proof
from canonical.runtime.typed_acceptance_program_v1 import verify as verify_typed_acceptance_program
from canonical.runtime.instruction_constraint_compiler_v1 import compile_constraints, validate_response
from canonical.runtime.structured_method_expression_ast_candidate_v2 import compile_graph as compile_structured_method
from canonical.runtime.source_aligned_acceptance_program_v1 import compile_program as compile_source_acceptance_program
from canonical.runtime.universal_verified_effect_executor_v1 import (
    execute as execute_verified_effect,
    EXECUTOR_ID as VERIFIED_EFFECT_EXECUTOR_ID,
)
from canonical.runtime.typed_acceptance_finite_search_v1 import search as search_typed_acceptance
from canonical.runtime.typed_acceptance_constructive_solver_v1 import solve as solve_typed_acceptance_constructive
from canonical.runtime.universal_solver_state_capsule_v1 import (
    initialize as initialize_state_capsule,
    append_verified_transition as append_state_transition,
    verify_targets as verify_state_targets,
)
from canonical.runtime.general_cognition_proposal_packet_v1 import (
    SCHEMA as PROPOSAL_PACKET_SCHEMA,
    make_request as make_proposal_request,
    unwrap as unwrap_proposal_packet,
)
from canonical.runtime.bound_goal_plan_adapter_v1 import compile_bound_goal
from canonical.runtime.bound_capability_execution_verifier_v1 import (
    verify as verify_bound_capability_execution,
)
from canonical.runtime.authenticated_complete_pareto_comparator_v1 import (
    verify as verify_authenticated_complete_pareto,
)
from canonical.runtime.lossless_raw_task_acceptance_gate_v1 import (
    verify as verify_lossless_raw_task_acceptance,
)

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_VERIFIED_ADAPTIVE_SOLVER_V1"


class UniversalSolverError(ValueError):
    pass


def _json_default(value: Any) -> Any:
    if isinstance(value, bytes):
        return {
            "__brain_type__": "bytes",
            "base64": base64.b64encode(value).decode("ascii"),
        }
    raise TypeError("UNSUPPORTED_CANONICAL_JSON_TYPE:" + type(value).__name__)


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_json_default,
    )


def _digest(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _verify_exact_json(payload: Mapping[str, Any], proposal: Mapping[str, Any]) -> dict[str, Any]:
    if set(payload) != {"expected"}:
        return {"pass": False, "status": "FAIL_CLOSED", "reason": "EXACT_JSON_PAYLOAD_INVALID"}
    if set(proposal) != {"candidate"}:
        return {"pass": False, "status": "REJECTED", "reason": "EXACT_JSON_PROPOSAL_INVALID"}
    ok = _canon(proposal["candidate"]) == _canon(payload["expected"])
    return {
        "pass": ok,
        "status": "VERIFIED" if ok else "FALSIFIED",
        "reason": None if ok else "CANDIDATE_NE_EXPECTED",
        "proof_digest": _digest({
            "verifier": "EXACT_JSON_V1",
            "expected": payload["expected"],
            "candidate": proposal["candidate"],
        }),
        "verified_output": proposal["candidate"] if ok else None,
    }


def _verify_p2(payload: Mapping[str, Any], proposal: Mapping[str, Any]) -> dict[str, Any]:
    if proposal:
        return {"pass": False, "status": "REJECTED", "reason": "P2_TOP_LAW_TAKES_NO_UNTRUSTED_PROPOSAL"}
    raw = payload.get("raw_source")
    source_id = payload.get("source_id")
    if not isinstance(raw, (str, bytes)) or not isinstance(source_id, str):
        return {"pass": False, "status": "FAIL_CLOSED", "reason": "P2_INPUT_INVALID"}
    out = p2_execute(raw, source_id=source_id)
    return {
        "pass": out.get("pass") is True,
        "status": "VERIFIED" if out.get("pass") is True else str(out.get("status") or "UNRESOLVED"),
        "reason": None if out.get("pass") is True else str(out.get("status") or "P2_NOT_VERIFIED"),
        "proof_digest": _digest(out),
        "verified_output": out.get("policy_result") if out.get("pass") is True else None,
        "detail": out,
    }


def _verify_judgment(mode: str, payload: Mapping[str, Any], proposal: Mapping[str, Any]) -> dict[str, Any]:
    proof_bundle = payload.get("proof_bundle")
    if not isinstance(proof_bundle, Mapping):
        return {"pass": False, "status": "FAIL_CLOSED", "reason": "PROOF_BUNDLE_INVALID"}
    out = configured_terminal_decision(proposal, proof_bundle, mode=mode)
    return {
        "pass": out.get("accepted") is True,
        "status": "VERIFIED" if out.get("accepted") is True else "FALSIFIED",
        "reason": None if out.get("accepted") is True else ";".join(out.get("errors") or ["JUDGMENT_REJECTED"]),
        "proof_digest": _digest(out),
        "verified_output": out if out.get("accepted") is True else None,
        "detail": out,
    }


def _verify_semantic_policy_v6(payload: Mapping[str, Any], proposal: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {"claims"}
    if set(proposal) - allowed:
        return {"pass": False, "status": "REJECTED", "reason": "PROPOSAL_TRIES_TO_OVERRIDE_TRUSTED_SEMANTIC_INPUT"}
    claims = proposal.get("claims", payload.get("claims"))
    if not isinstance(claims, Sequence) or isinstance(claims, (str, bytes)):
        return {"pass": False, "status": "REJECTED", "reason": "CLAIMS_REQUIRED"}
    required = (
        "source_text", "source_id", "decision_basis", "policy_conditions",
        "policy_adequacy_bindings",
    )
    if any(key not in payload for key in required):
        return {"pass": False, "status": "FAIL_CLOSED", "reason": "SEMANTIC_POLICY_PAYLOAD_INCOMPLETE"}
    out = resolve_from_source_proof(
        payload["source_text"],
        source_id=payload["source_id"],
        claims=claims,
        decision_basis=payload["decision_basis"],
        policy_conditions=payload["policy_conditions"],
        policy_adequacy_bindings=payload["policy_adequacy_bindings"],
        typed_context=payload.get("typed_context"),
        expected_typed_context_sha256=payload.get("expected_typed_context_sha256"),
        fact_source=payload.get("fact_source"),
        fact_source_id=payload.get("fact_source_id"),
    )
    ok = out.get("status") == "COMMON_POLICY_CERTIFIED" and bool(out.get("certified_common_policies"))
    unresolved = out.get("status") in {
        "UNRESOLVED",
        "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED",
    }
    return {
        "pass": ok,
        "status": "VERIFIED" if ok else ("NEED_MORE_INFORMATION" if unresolved else "FALSIFIED"),
        "reason": None if ok else str(out.get("status") or "SEMANTIC_POLICY_NOT_CERTIFIED"),
        "proof_digest": _digest(out),
        "verified_output": {
            "certified_common_policies": out.get("certified_common_policies", []),
        } if ok else None,
        "detail": out,
    }




def _verify_typed_acceptance_program(payload: Mapping[str, Any], proposal: Mapping[str, Any]) -> dict[str, Any]:
    program = payload.get("program")
    trusted_values = payload.get("trusted_values")
    candidate_values = proposal.get("candidate_values") if isinstance(proposal, Mapping) else None
    if not isinstance(program, Mapping) or not isinstance(trusted_values, Mapping):
        return {"pass": False, "status": "FAIL_CLOSED", "reason": "TYPED_ACCEPTANCE_PAYLOAD_INVALID"}
    if not isinstance(candidate_values, Mapping):
        return {"pass": False, "status": "REJECTED", "reason": "CANDIDATE_VALUES_REQUIRED"}
    out = verify_typed_acceptance_program(
        program,
        trusted_values=trusted_values,
        candidate_values=candidate_values,
    )
    return {
        "pass": out.get("pass") is True,
        "status": "VERIFIED" if out.get("pass") is True else (
            "FALSIFIED" if str(out.get("status") or "").startswith("FALSIFIED") else "FAIL_CLOSED"
        ),
        "reason": None if out.get("pass") is True else str(out.get("status") or "TYPED_ACCEPTANCE_REJECTED"),
        "proof_digest": _digest(out),
        "verified_output": dict(candidate_values) if out.get("pass") is True else None,
        "detail": out,
    }




def _verify_instruction_constraints(payload: Mapping[str, Any], proposal: Mapping[str, Any]) -> dict[str, Any]:
    instruction = payload.get("instruction")
    response = proposal.get("response") if isinstance(proposal, Mapping) else None
    if not isinstance(instruction, str) or not instruction.strip():
        return {"pass": False, "status": "FAIL_CLOSED", "reason": "INSTRUCTION_REQUIRED"}
    if not isinstance(response, str):
        return {"pass": False, "status": "REJECTED", "reason": "RESPONSE_REQUIRED"}
    try:
        constraints = compile_constraints(instruction)
        ok, errors = validate_response(response, constraints)
    except Exception as exc:
        return {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
        }
    detail = {
        "instruction": instruction,
        "response": response,
        "errors": errors,
    }
    return {
        "pass": ok,
        "status": "VERIFIED" if ok else "FALSIFIED",
        "reason": None if ok else ";".join(errors or ["INSTRUCTION_CONSTRAINT_FAILURE"]),
        "proof_digest": _digest(detail),
        "verified_output": response if ok else None,
        "detail": detail,
    }


def _verify_structured_method(payload: Mapping[str, Any], proposal: Mapping[str, Any]) -> dict[str, Any]:
    if proposal:
        return {"pass": False, "status": "REJECTED", "reason": "STRUCTURED_METHOD_ROUTE_TAKES_NO_UNTRUSTED_PROPOSAL"}
    public = payload.get("public")
    if not isinstance(public, Mapping):
        return {"pass": False, "status": "FAIL_CLOSED", "reason": "STRUCTURED_METHOD_PUBLIC_CONTRACT_REQUIRED"}
    out = compile_structured_method(public)
    ok = out.get("status") == "COMPILED"
    return {
        "pass": ok,
        "status": "VERIFIED" if ok else "FAIL_CLOSED",
        "reason": None if ok else str(out.get("reason") or "STRUCTURED_METHOD_COMPILE_FAILED"),
        "proof_digest": _digest(out),
        "verified_output": {
            "outputs": out.get("outputs", []),
            "selected_branch_id": out.get("selected_branch_id"),
            "requirement_lineage": out.get("requirement_lineage", []),
        } if ok else None,
        "detail": out,
    }




def _verify_source_aligned_acceptance_program(payload: Mapping[str, Any], proposal: Mapping[str, Any]) -> dict[str, Any]:
    source_text = payload.get("source_text")
    source_id = payload.get("source_id")
    field_schema = payload.get("field_schema")
    candidate_values = proposal.get("candidate_values") if isinstance(proposal, Mapping) else None
    if not isinstance(source_text, str) or not isinstance(source_id, str) or not isinstance(field_schema, Mapping):
        return {"pass": False, "status": "FAIL_CLOSED", "reason": "SOURCE_ALIGNED_ACCEPTANCE_PAYLOAD_INVALID"}
    if not isinstance(candidate_values, Mapping):
        return {"pass": False, "status": "REJECTED", "reason": "CANDIDATE_VALUES_REQUIRED"}
    compiled = compile_source_acceptance_program(
        source_text,
        source_id=source_id,
        field_schema=field_schema,
    )
    if compiled.get("status") != "COMPILED":
        return {
            "pass": False,
            "status": "NEED_MORE_INFORMATION" if compiled.get("status") == "UNRESOLVED" else "FAIL_CLOSED",
            "reason": str(compiled.get("status") or "SOURCE_ACCEPTANCE_COMPILATION_FAILED"),
            "proof_digest": _digest(compiled),
            "detail": compiled,
        }
    out = verify_typed_acceptance_program(
        compiled["acceptance_program"],
        trusted_values={},
        candidate_values=candidate_values,
    )
    ok = out.get("pass") is True
    return {
        "pass": ok,
        "status": "VERIFIED" if ok else (
            "FALSIFIED" if str(out.get("status") or "").startswith("FALSIFIED") else "FAIL_CLOSED"
        ),
        "reason": None if ok else str(out.get("status") or "SOURCE_ALIGNED_ACCEPTANCE_REJECTED"),
        "proof_digest": _digest({"compiled": compiled, "verdict": out}),
        "verified_output": dict(candidate_values) if ok else None,
        "detail": {"compiled": compiled, "verdict": out},
    }




def _proposal_context(
    verifier_id: str,
    payload: Mapping[str, Any],
    action: Mapping[str, Any],
) -> dict[str, Any]:
    explicit = action.get("proposal_context")
    if isinstance(explicit, Mapping):
        return dict(explicit)
    if verifier_id == "TYPED_ACCEPTANCE_PROGRAM_V1":
        return {
            "program": payload.get("program"),
            "trusted_values": payload.get("trusted_values"),
        }
    if verifier_id == "INSTRUCTION_CONSTRAINTS_V1":
        return {"instruction": payload.get("instruction")}
    if verifier_id == "SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1":
        return {
            "source_text": payload.get("source_text"),
            "source_id": payload.get("source_id"),
            "field_schema": payload.get("field_schema"),
        }
    if verifier_id == "SOURCE_ALIGNED_SEMANTIC_POLICY_V6":
        return {
            "source_text": payload.get("source_text"),
            "source_id": payload.get("source_id"),
            "decision_basis": payload.get("decision_basis"),
            "policy_ids": sorted((payload.get("policy_conditions") or {}).keys()),
        }
    if verifier_id == "EXACT_JSON_V1":
        return {"proposal_shape": {"candidate": "UNTRUSTED_VALUE"}}
    if verifier_id == "BOUND_GOAL_PLAN_V1":
        return {"goal": payload.get("goal"), "proposal_required": False}
    return {"verifier_id": verifier_id}




def _verify_bound_goal_plan(payload: Mapping[str, Any], proposal: Mapping[str, Any]) -> dict[str, Any]:
    if proposal:
        return {"pass": False, "status": "REJECTED", "reason": "BOUND_GOAL_COMPILER_TAKES_NO_UNTRUSTED_PROPOSAL"}
    goal = payload.get("goal")
    if not isinstance(goal, str) or not goal.strip():
        return {"pass": False, "status": "FAIL_CLOSED", "reason": "GOAL_REQUIRED"}
    out = compile_bound_goal(goal)
    ok = out.get("pass") is True
    return {
        "pass": ok,
        "status": "VERIFIED" if ok else (
            "NEED_MORE_INFORMATION" if out.get("status") == "UNRESOLVED" else "FAIL_CLOSED"
        ),
        "reason": None if ok else str(out.get("reason") or out.get("status") or "GOAL_COMPILATION_FAILED"),
        "proof_digest": _digest(out),
        "verified_output": {
            "compiled_plan_sha256": out.get("compiled_plan_sha256"),
            "compiled_plan": out.get("compiled_plan"),
            "execution_authority": False,
        } if ok else None,
        "detail": out,
    }


Verifier = Callable[[Mapping[str, Any], Mapping[str, Any]], dict[str, Any]]

BUILTIN_VERIFIERS: dict[str, Verifier] = {
    "EXACT_JSON_V1": _verify_exact_json,
    "P2_AUTHENTICATED_TOP_LAW_V1": _verify_p2,
    "FINANCE_JUDGMENT_CONTROL_V1": lambda p, q: _verify_judgment("FINANCE", p, q),
    "UNKNOWN_DOMAIN_JUDGMENT_CONTROL_V1": lambda p, q: _verify_judgment("UNKNOWN_DOMAIN", p, q),
    "SOURCE_ALIGNED_SEMANTIC_POLICY_V6": _verify_semantic_policy_v6,
    "TYPED_ACCEPTANCE_PROGRAM_V1": _verify_typed_acceptance_program,
    "INSTRUCTION_CONSTRAINTS_V1": _verify_instruction_constraints,
    "STRUCTURED_METHOD_EXPRESSION_AST_V2": _verify_structured_method,
    "SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1": _verify_source_aligned_acceptance_program,
    "BOUND_GOAL_PLAN_V1": _verify_bound_goal_plan,
    "BOUND_CAPABILITY_EXECUTION_V1": verify_bound_capability_execution,
    "RAW_TASK_ACCEPTANCE_V1": verify_lossless_raw_task_acceptance,
    "AUTHENTICATED_COMPLETE_PARETO_V1": verify_authenticated_complete_pareto,
}

PROPOSAL_FREE_VERIFIERS = {
    "P2_AUTHENTICATED_TOP_LAW_V1",
    "STRUCTURED_METHOD_EXPRESSION_AST_V2",
    "BOUND_GOAL_PLAN_V1",
    "AUTHENTICATED_COMPLETE_PARETO_V1",
}


def _normalize_caps(problem: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw = problem.get("capabilities")
    if not isinstance(raw, list) or not raw:
        raise UniversalSolverError("CAPABILITIES_REQUIRED")
    out: dict[str, Mapping[str, Any]] = {}
    for row in raw:
        if not isinstance(row, Mapping):
            raise UniversalSolverError("CAPABILITY_NOT_OBJECT")
        cid = row.get("id")
        if not isinstance(cid, str) or not cid or cid in out:
            raise UniversalSolverError("CAPABILITY_ID_INVALID_OR_DUPLICATE")
        action = row.get("action")
        if not isinstance(action, Mapping):
            raise UniversalSolverError("CAPABILITY_ACTION_INVALID:" + cid)
        action_type = str(action.get("type") or "")
        if action_type == "verified_effect_tool":
            verifier_id = action.get("pre_verifier_id")
            if verifier_id not in BUILTIN_VERIFIERS:
                raise UniversalSolverError("PRE_VERIFIER_NOT_BUILTIN:" + cid + ":" + str(verifier_id))
            if not isinstance(action.get("pre_verifier_payload"), Mapping):
                raise UniversalSolverError("PRE_VERIFIER_PAYLOAD_INVALID:" + cid)
            if action.get("executor_id") != VERIFIED_EFFECT_EXECUTOR_ID:
                raise UniversalSolverError("EFFECT_EXECUTOR_NOT_BUILTIN:" + cid)
            if not isinstance(action.get("executor_payload"), Mapping):
                raise UniversalSolverError("EFFECT_EXECUTOR_PAYLOAD_INVALID:" + cid)
        else:
            verifier_id = action.get("verifier_id")
            if verifier_id not in BUILTIN_VERIFIERS:
                raise UniversalSolverError("VERIFIER_NOT_BUILTIN:" + cid + ":" + str(verifier_id))
            if not isinstance(action.get("verifier_payload"), Mapping):
                raise UniversalSolverError("VERIFIER_PAYLOAD_INVALID:" + cid)
        generator_id = action.get("proposal_generator_id")
        if generator_id is not None:
            if generator_id not in {"TYPED_ACCEPTANCE_FINITE_SEARCH_V1", "TYPED_ACCEPTANCE_CONSTRUCTIVE_SOLVER_V1"}:
                raise UniversalSolverError("PROPOSAL_GENERATOR_NOT_BUILTIN:" + cid + ":" + str(generator_id))
            gp = action.get("proposal_generator_payload")
            if not isinstance(gp, Mapping):
                raise UniversalSolverError("PROPOSAL_GENERATOR_PAYLOAD_INVALID:" + cid)
            active_verifier = (
                action.get("pre_verifier_id")
                if action_type == "verified_effect_tool"
                else action.get("verifier_id")
            )
            active_payload = (
                action.get("pre_verifier_payload")
                if action_type == "verified_effect_tool"
                else action.get("verifier_payload")
            )
            if active_verifier != "TYPED_ACCEPTANCE_PROGRAM_V1":
                raise UniversalSolverError("TYPED_PROPOSAL_GENERATOR_REQUIRES_TYPED_ACCEPTANCE_VERIFIER:" + cid)
            if not isinstance(active_payload, Mapping):
                raise UniversalSolverError("TYPED_PROPOSAL_GENERATOR_VERIFIER_PAYLOAD_INVALID:" + cid)
            if generator_id == "TYPED_ACCEPTANCE_FINITE_SEARCH_V1":
                if set(gp) - {"candidate_domains", "max_candidates"}:
                    raise UniversalSolverError("PROPOSAL_GENERATOR_PAYLOAD_FIELDS_INVALID:" + cid)
                if not isinstance(gp.get("candidate_domains"), Mapping):
                    raise UniversalSolverError("PROPOSAL_GENERATOR_DOMAINS_INVALID:" + cid)
            else:
                if set(gp):
                    raise UniversalSolverError("CONSTRUCTIVE_GENERATOR_PAYLOAD_MUST_BE_EMPTY:" + cid)
        out[cid] = row
    return out


def run(
    problem: Mapping[str, Any],
    *,
    proposal_packets: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    verified_facts: Sequence[str] = (),
    effect_root: str | None = None,
) -> dict[str, Any]:
    """Run until solved, falsified, or an untrusted proposal/information update is needed.

    Raw cross-run verified_facts are currently rejected because no authenticated
    resume-state receipt has yet been supplied to this API. State accumulated
    inside one run remains trusted only through the verifier/effect gates.
    This function never treats proposal text as a fact.
    """
    try:
        if not isinstance(problem, Mapping):
            raise UniversalSolverError("PROBLEM_NOT_OBJECT")
        caps = _normalize_caps(problem)
        initial = problem.get("initial_facts", [])
        if not isinstance(initial, list):
            raise UniversalSolverError("INITIAL_FACTS_INVALID")
        external_resume = [str(x) for x in verified_facts if isinstance(x, str) and x]
        if external_resume:
            raise UniversalSolverError("RAW_VERIFIED_FACT_RESUME_FORBIDDEN__AUTHENTICATED_STATE_RECEIPT_REQUIRED")
        current = sorted(set(initial))
        target = problem.get("target_effects", [])
        if not isinstance(target, list) or not target:
            raise UniversalSolverError("TARGET_EFFECTS_REQUIRED")
        if set(target) & set(current):
            raise UniversalSolverError("TARGET_EFFECT_MAY_NOT_BE_SELF_ASSERTED_AS_INITIAL_FACT")
        proposals = proposal_packets if isinstance(proposal_packets, Mapping) else {}
        task_contract_sha256 = _digest(problem)
        state_capsule = initialize_state_capsule(problem)

        trace: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        proposal_searches: list[dict[str, Any]] = []
        used_packets: set[tuple[str, int]] = set()

        max_cycles = int(problem.get("max_solver_cycles", 256))
        if max_cycles < 1 or max_cycles > 10000:
            raise UniversalSolverError("MAX_SOLVER_CYCLES_INVALID")

        for cycle in range(max_cycles):
            if set(target).issubset(current):
                target_lineage = verify_state_targets(state_capsule, target)
                if target_lineage.get("pass") is not True:
                    return {
                        "schema": SCHEMA,
                        "status": "FAIL_CLOSED__TARGET_FACTS_WITHOUT_VALID_STATE_LINEAGE",
                        "pass": False,
                        "verified_facts": current,
                        "trace": trace,
                        "state_capsule": state_capsule,
                        "state_target_verdict": target_lineage,
                        "terminal_authority": False,
                    }
                return {
                    "schema": SCHEMA,
                    "status": "SOLVED__ALL_TARGET_EFFECTS_VERIFIED",
                    "pass": True,
                    "verified_facts": current,
                    "trace": trace,
                    "rejected_proposals": rejected,
                    "proposal_searches": proposal_searches,
                    "state_capsule": state_capsule,
                    "state_capsule_head_hash": state_capsule.get("head_hash"),
                    "state_target_verdict": target_lineage,
                    "cycles": cycle,
                    "terminal_authority": False,
                    "capability_ownership_credit_delta": 0,
                }

            replanning_problem = dict(problem)
            replanning_problem["initial_facts"] = current
            try:
                plan = plan_capabilities(replanning_problem)
            except PlanningFailure as exc:
                return {
                    "schema": SCHEMA,
                    "status": "UNRESOLVED__NO_CURRENT_CAPABILITY_PLAN",
                    "pass": False,
                    "reason": str(exc),
                    "verified_facts": current,
                    "trace": trace,
                    "rejected_proposals": rejected,
                    "terminal_authority": False,
                }

            if not plan.get("plan"):
                return {
                    "schema": SCHEMA,
                    "status": "FAIL_CLOSED__PLANNER_RETURNED_EMPTY_UNSOLVED_PLAN",
                    "pass": False,
                    "verified_facts": current,
                    "trace": trace,
                    "terminal_authority": False,
                }

            cid = str(plan["plan"][0])
            cap = caps[cid]
            action = cap["action"]
            action_type = str(action.get("type") or "")
            is_effect = action_type == "verified_effect_tool"
            if is_effect:
                verifier_id = str(action["pre_verifier_id"])
                verifier = BUILTIN_VERIFIERS[verifier_id]
                payload = action["pre_verifier_payload"]
            else:
                verifier_id = str(action["verifier_id"])
                verifier = BUILTIN_VERIFIERS[verifier_id]
                payload = action["verifier_payload"]

            proposal_request = make_proposal_request(
                task_contract_sha256=task_contract_sha256,
                capability_id=cid,
                action_contract_sha256=_digest(action),
                verifier_id=verifier_id,
                proposal_context=_proposal_context(verifier_id, payload, action),
            )
            packets = proposals.get(cid)
            proposal_source = "UNBOUND_EXTERNAL_PROPOSAL"
            if verifier_id in PROPOSAL_FREE_VERIFIERS:
                packets = [{}]
                proposal_source = "DETERMINISTIC_PROPOSAL_FREE_ROUTE"
            if (
                (not isinstance(packets, Sequence) or isinstance(packets, (str, bytes)) or not packets)
                and action.get("proposal_generator_id") == "TYPED_ACCEPTANCE_CONSTRUCTIVE_SOLVER_V1"
            ):
                generated = solve_typed_acceptance_constructive(
                    payload["program"],
                    trusted_values=payload["trusted_values"],
                )
                proposal_searches.append({
                    "cycle": cycle,
                    "capability_id": cid,
                    "generator_id": "TYPED_ACCEPTANCE_CONSTRUCTIVE_SOLVER_V1",
                    "generator_result_sha256": _digest(generated),
                    "status": generated.get("status"),
                    "complete_for_declared_fragment": generated.get("complete_for_declared_fragment"),
                    "cartesian_enumeration_used": generated.get("cartesian_enumeration_used"),
                })
                if generated.get("pass") is True:
                    packets = [{"candidate_values": generated["candidate"]}]
                    proposal_source = "BUILTIN_DIRECT_CONSTRUCTIVE_SOLVER"
                elif generated.get("status") == "PROVED_UNSAT_IN_DECLARED_FRAGMENT":
                    return {
                        "schema": SCHEMA,
                        "status": "NO_PROPOSAL_IN_DECLARED_CONSTRUCTIVE_FRAGMENT",
                        "pass": False,
                        "next_capability_id": cid,
                        "verifier_id": verifier_id,
                        "proposal_search": generated,
                        "verified_facts": current,
                        "trace": trace,
                        "rejected_proposals": rejected,
                        "proposal_searches": proposal_searches,
                        "terminal_authority": False,
                    }
                else:
                    return {
                        "schema": SCHEMA,
                        "status": "FAIL_CLOSED__PROPOSAL_CONSTRUCTION_FAILED",
                        "pass": False,
                        "next_capability_id": cid,
                        "verifier_id": verifier_id,
                        "proposal_search": generated,
                        "verified_facts": current,
                        "trace": trace,
                        "rejected_proposals": rejected,
                        "proposal_searches": proposal_searches,
                        "terminal_authority": False,
                    }
            if (
                (not isinstance(packets, Sequence) or isinstance(packets, (str, bytes)) or not packets)
                and action.get("proposal_generator_id") == "TYPED_ACCEPTANCE_FINITE_SEARCH_V1"
            ):
                gp = action["proposal_generator_payload"]
                generated = search_typed_acceptance(
                    payload["program"],
                    trusted_values=payload["trusted_values"],
                    candidate_domains=gp["candidate_domains"],
                    max_candidates=int(gp.get("max_candidates", 100000)),
                )
                proposal_searches.append({
                    "cycle": cycle,
                    "capability_id": cid,
                    "generator_id": "TYPED_ACCEPTANCE_FINITE_SEARCH_V1",
                    "generator_result_sha256": _digest(generated),
                    "status": generated.get("status"),
                    "examined": generated.get("examined"),
                    "complete_over_declared_domains": generated.get("complete_over_declared_domains"),
                })
                if generated.get("pass") is True:
                    packets = [{"candidate_values": generated["selected_candidate"]}]
                    proposal_source = "BUILTIN_FINITE_COMPLETE_SEARCH"
                elif generated.get("status") == "NO_ACCEPTED_CANDIDATE_IN_DECLARED_DOMAINS":
                    return {
                        "schema": SCHEMA,
                        "status": "NO_PROPOSAL_IN_DECLARED_FINITE_SEARCH_DOMAIN",
                        "pass": False,
                        "next_capability_id": cid,
                        "verifier_id": verifier_id,
                        "proposal_search": generated,
                        "verified_facts": current,
                        "trace": trace,
                        "rejected_proposals": rejected,
                        "proposal_searches": proposal_searches,
                        "terminal_authority": False,
                    }
                else:
                    return {
                        "schema": SCHEMA,
                        "status": "FAIL_CLOSED__PROPOSAL_SEARCH_FAILED",
                        "pass": False,
                        "next_capability_id": cid,
                        "verifier_id": verifier_id,
                        "proposal_search": generated,
                        "verified_facts": current,
                        "trace": trace,
                        "rejected_proposals": rejected,
                        "proposal_searches": proposal_searches,
                        "terminal_authority": False,
                    }
            if not isinstance(packets, Sequence) or isinstance(packets, (str, bytes)) or not packets:
                return {
                    "schema": SCHEMA,
                    "status": "NEED_PROPOSAL",
                    "pass": False,
                    "next_capability_id": cid,
                    "verifier_id": verifier_id,
                    "verified_facts": current,
                    "trace": trace,
                    "rejected_proposals": rejected,
                    "proposal_has_authority": False,
                    "proposal_request": proposal_request,
                    "proposal_searches": proposal_searches,
                    "terminal_authority": False,
                }

            accepted = None
            last_need_info = None
            for i, packet in enumerate(packets):
                key = (cid, i)
                if key in used_packets:
                    continue
                used_packets.add(key)
                if not isinstance(packet, Mapping):
                    rejected.append({"capability_id": cid, "packet_index": i, "reason": "PROPOSAL_NOT_OBJECT"})
                    continue
                actual_packet = packet
                packet_sha256 = None
                packet_source_id = None
                packet_proposal_source = proposal_source
                if packet.get("schema") == PROPOSAL_PACKET_SCHEMA:
                    try:
                        unwrapped = unwrap_proposal_packet(packet, request=proposal_request)
                    except Exception as exc:
                        rejected.append({
                            "capability_id": cid,
                            "packet_index": i,
                            "reason": "PROPOSAL_PACKET_BINDING_FAILED:" + type(exc).__name__ + ":" + str(exc),
                        })
                        continue
                    actual_packet = unwrapped["proposal"]
                    packet_sha256 = unwrapped["packet_sha256"]
                    packet_source_id = unwrapped["source_id"]
                    packet_proposal_source = "GENERAL_COGNITION_SUBSTRATE:" + packet_source_id
                verdict = verifier(payload, actual_packet)
                record = {
                    "cycle": cycle,
                    "capability_id": cid,
                    "verifier_id": verifier_id,
                    "action_contract_sha256": _digest(action),
                    "packet_index": i,
                    "proposal_sha256": _digest(actual_packet),
                    "proposal_source": packet_proposal_source,
                    "proposal_request_sha256": proposal_request.get("request_sha256"),
                    "proposal_packet_sha256": packet_sha256,
                    "proposal_source_id": packet_source_id,
                    "verdict_status": verdict.get("status"),
                    "proof_digest": verdict.get("proof_digest"),
                }
                if verdict.get("pass") is True:
                    accepted = (i, actual_packet, verdict, record)
                    break
                rejected.append({
                    **record,
                    "reason": verdict.get("reason"),
                })
                if verdict.get("status") == "NEED_MORE_INFORMATION":
                    last_need_info = verdict

            if accepted is None:
                if last_need_info is not None:
                    return {
                        "schema": SCHEMA,
                        "status": "NEED_MORE_INFORMATION",
                        "pass": False,
                        "next_capability_id": cid,
                        "verifier_id": verifier_id,
                        "reason": last_need_info.get("reason"),
                        "detail": last_need_info.get("detail"),
                        "verified_facts": current,
                        "trace": trace,
                        "rejected_proposals": rejected,
                        "terminal_authority": False,
                    }
                return {
                    "schema": SCHEMA,
                    "status": "ALL_AVAILABLE_PROPOSALS_FALSIFIED",
                    "pass": False,
                    "next_capability_id": cid,
                    "verifier_id": verifier_id,
                    "verified_facts": current,
                    "trace": trace,
                    "rejected_proposals": rejected,
                    "terminal_authority": False,
                }

            _, accepted_packet, verdict, record = accepted
            record["accepted_proposal"] = dict(accepted_packet)

            effect_result = None
            if is_effect:
                if not isinstance(effect_root, str) or not effect_root.strip():
                    return {
                        "schema": SCHEMA,
                        "status": "BLOCKED__EFFECT_ROOT_REQUIRED",
                        "pass": False,
                        "next_capability_id": cid,
                        "verifier_id": verifier_id,
                        "verified_facts": current,
                        "trace": trace,
                        "rejected_proposals": rejected,
                        "terminal_authority": False,
                    }
                effect_result = execute_verified_effect(
                    executor_id=str(action["executor_id"]),
                    executor_payload=action["executor_payload"],
                    proposal=accepted_packet,
                    effect_root=effect_root,
                )
                if effect_result.get("pass") is not True:
                    return {
                        "schema": SCHEMA,
                        "status": "FAIL_CLOSED__EFFECT_EXECUTION_OR_READBACK_FAILED",
                        "pass": False,
                        "next_capability_id": cid,
                        "verifier_id": verifier_id,
                        "effect_result": effect_result,
                        "verified_facts": current,
                        "trace": trace,
                        "rejected_proposals": rejected,
                        "terminal_authority": False,
                    }

            new_facts = cap.get("provides")
            if not isinstance(new_facts, list) or not new_facts:
                raise UniversalSolverError("CAPABILITY_PROVIDES_INVALID:" + cid)
            if any(not isinstance(x, str) or not x for x in new_facts):
                raise UniversalSolverError("CAPABILITY_PROVIDES_INVALID:" + cid)

            completed_record = {
                **record,
                "action_type": action_type,
                "verified_output": verdict.get("verified_output"),
                "effect_outcome": effect_result.get("outcome") if isinstance(effect_result, Mapping) else None,
                "effect_outcome_sha256": effect_result.get("effect_outcome_sha256") if isinstance(effect_result, Mapping) else None,
                "new_verified_facts": sorted(set(new_facts)),
            }
            if is_effect:
                completed_record["effect_root_sha256"] = _digest(
                    str(Path(effect_root).resolve())
                )
            try:
                state_capsule = append_state_transition(
                    state_capsule,
                    capability=cap,
                    trace_row=completed_record,
                )
            except Exception as exc:
                return {
                    "schema": SCHEMA,
                    "status": "FAIL_CLOSED__STATE_LINEAGE_APPEND_FAILED",
                    "pass": False,
                    "reason": type(exc).__name__ + ":" + str(exc),
                    "verified_facts": current,
                    "trace": trace,
                    "state_capsule": state_capsule,
                    "terminal_authority": False,
                }

            current = sorted(set(current) | set(new_facts))
            trace.append(completed_record)

        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__MAX_SOLVER_CYCLES_EXCEEDED",
            "pass": False,
            "verified_facts": current,
            "trace": trace,
            "rejected_proposals": rejected,
            "terminal_authority": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "terminal_authority": False,
        }
