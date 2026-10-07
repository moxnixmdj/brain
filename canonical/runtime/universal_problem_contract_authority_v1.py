"""Brain-owned problem-contract authority for the Universal Verified Adaptive Solver.

This module separates two notions that must not be conflated:

1. Root task authority:
   The upstream task/evaluation ingress defines what the task actually is.
   No solver can derive the authority of its own input from the input itself.
   This remains an explicit root-of-trust boundary.

2. Executable problem authority:
   Once the root task input is fixed, only Brain-owned deterministic compilers
   may turn it into target effects, capabilities, verifier IDs, proposal
   generators, and effect executors for owned-capability mode.

Raw caller-authored solver problems are therefore NOT accepted here.

Supported owned contract classes:
- SOURCE_ALIGNED_FINITE_STRUCTURED_TASK_V1
- P2_EXPLICIT_TOP_LAW_V1
- BOUND_GOAL_PLAN_V1

A successful compile proves only that the executable problem was recomputed by a
Brain-owned compiler from the supplied root task contract. It does not prove that
the upstream supplied task was the user's true intent; that is the ingress root.
"""
from __future__ import annotations

from hashlib import sha256
import base64
import json
from typing import Any, Mapping

from canonical.runtime.source_aligned_acceptance_program_v1 import compile_program
from canonical.runtime.p2_explicit_contract_membership_v1 import compile_membership
from canonical.runtime.bound_goal_plan_adapter_v1 import compile_bound_goal

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_PROBLEM_CONTRACT_AUTHORITY_V1"
CONTRACT_SCHEMA = "PROJECT_BRAIN_OWNED_PROBLEM_CONTRACT_V1"

SOURCE_ALIGNED = "SOURCE_ALIGNED_FINITE_STRUCTURED_TASK_V1"
P2_TOP_LAW = "P2_EXPLICIT_TOP_LAW_V1"
BOUND_GOAL_PLAN = "BOUND_GOAL_PLAN_V1"
KINDS = {SOURCE_ALIGNED, P2_TOP_LAW, BOUND_GOAL_PLAN}

ALLOWED_EFFECT_TOOLS = {"JSON_RECEIPT_WRITER_V1", "JSONL_LEDGER_APPEND_V1"}


class ProblemContractError(ValueError):
    pass


def _default(value: Any) -> Any:
    if isinstance(value, bytes):
        return {
            "__brain_type__": "bytes",
            "base64": base64.b64encode(value).decode("ascii"),
        }
    raise TypeError(type(value).__name__)


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_default,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _exact_keys(value: Mapping[str, Any], allowed: set[str], required: set[str], label: str) -> None:
    keys = set(value)
    missing = sorted(required - keys)
    extra = sorted(keys - allowed)
    if missing or extra:
        raise ProblemContractError(
            label + "_KEYS_INVALID:missing=" + ",".join(missing) + ";extra=" + ",".join(extra)
        )


def _compile_source_aligned(task: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    allowed = {
        "source_text", "source_id", "field_schema", "candidate_domains",
        "target_effect", "max_candidates", "effect",
    }
    required = {
        "source_text", "source_id", "field_schema", "candidate_domains", "target_effect",
    }
    _exact_keys(task, allowed, required, "SOURCE_ALIGNED_TASK")

    source_text = task.get("source_text")
    source_id = task.get("source_id")
    field_schema = task.get("field_schema")
    candidate_domains = task.get("candidate_domains")
    target_effect = task.get("target_effect")
    if not isinstance(source_text, str) or not source_text.strip():
        raise ProblemContractError("SOURCE_TEXT_REQUIRED")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ProblemContractError("SOURCE_ID_REQUIRED")
    if not isinstance(field_schema, Mapping) or not field_schema:
        raise ProblemContractError("FIELD_SCHEMA_REQUIRED")
    if not isinstance(candidate_domains, Mapping) or not candidate_domains:
        raise ProblemContractError("CANDIDATE_DOMAINS_REQUIRED")
    if not isinstance(target_effect, str) or not target_effect.strip():
        raise ProblemContractError("TARGET_EFFECT_REQUIRED")

    max_candidates = task.get("max_candidates", 100000)
    if not isinstance(max_candidates, int) or isinstance(max_candidates, bool) or not (1 <= max_candidates <= 100000):
        raise ProblemContractError("MAX_CANDIDATES_INVALID")

    compiled = compile_program(
        source_text,
        source_id=source_id,
        field_schema=field_schema,
    )
    if compiled.get("status") != "COMPILED":
        raise ProblemContractError(
            "SOURCE_ACCEPTANCE_PROGRAM_NOT_COMPILED:" + str(compiled.get("status"))
        )

    action: dict[str, Any] = {
        "type": "verified_policy",
        "verifier_id": "TYPED_ACCEPTANCE_PROGRAM_V1",
        "verifier_payload": {
            "program": compiled["acceptance_program"],
            "trusted_values": {},
        },
        "proposal_generator_id": "TYPED_ACCEPTANCE_FINITE_SEARCH_V1",
        "proposal_generator_payload": {
            "candidate_domains": dict(candidate_domains),
            "max_candidates": max_candidates,
        },
    }

    effect = task.get("effect")
    effect_bound = False
    if effect is not None:
        if not isinstance(effect, Mapping):
            raise ProblemContractError("EFFECT_INVALID")
        _exact_keys(effect, {"tool_id", "sandbox_rel"}, {"tool_id", "sandbox_rel"}, "EFFECT")
        tool_id = effect.get("tool_id")
        sandbox_rel = effect.get("sandbox_rel")
        if tool_id not in ALLOWED_EFFECT_TOOLS:
            raise ProblemContractError("EFFECT_TOOL_NOT_ALLOWED")
        if not isinstance(sandbox_rel, str) or not sandbox_rel:
            raise ProblemContractError("EFFECT_SANDBOX_REL_REQUIRED")
        action = {
            "type": "verified_effect_tool",
            "pre_verifier_id": "TYPED_ACCEPTANCE_PROGRAM_V1",
            "pre_verifier_payload": {
                "program": compiled["acceptance_program"],
                "trusted_values": {},
            },
            "proposal_generator_id": "TYPED_ACCEPTANCE_FINITE_SEARCH_V1",
            "proposal_generator_payload": {
                "candidate_domains": dict(candidate_domains),
                "max_candidates": max_candidates,
            },
            "executor_id": "H100_VERIFIED_EFFECT_TOOL_REGISTRY_V1",
            "executor_payload": {
                "tool_id": tool_id,
                "sandbox_rel": sandbox_rel,
            },
        }
        effect_bound = True

    problem = {
        "initial_facts": [],
        "target_effects": [target_effect.strip()],
        "max_solver_cycles": 8,
        "capabilities": [{
            "id": "owned-source-aligned-structured-task",
            "requires": [],
            "provides": [target_effect.strip()],
            "cost": 1,
            "result_fields": [],
            "action": action,
        }],
    }
    evidence = {
        "compiler": "source_aligned_acceptance_program_v1",
        "source_sha256": compiled.get("source_sha256"),
        "compiled_requirement_count": len(compiled.get("compiled_requirements") or []),
        "unresolved_normative_requirement_count": len(compiled.get("unresolved_normative_requirements") or []),
        "effect_bound": effect_bound,
    }
    return problem, evidence


def _compile_p2(task: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    _exact_keys(task, {"raw_source", "source_id"}, {"raw_source", "source_id"}, "P2_TASK")
    raw = task.get("raw_source")
    source_id = task.get("source_id")
    if not isinstance(raw, (str, bytes)):
        raise ProblemContractError("P2_RAW_SOURCE_REQUIRED")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ProblemContractError("P2_SOURCE_ID_REQUIRED")

    membership = compile_membership(raw, source_id=source_id)
    if membership.get("pass") is not True:
        raise ProblemContractError("P2_MEMBERSHIP_NOT_PROVED")

    problem = {
        "initial_facts": [],
        "target_effects": ["P2_PLAN_VERIFIED"],
        "max_solver_cycles": 4,
        "capabilities": [{
            "id": "owned-p2-top-law",
            "requires": [],
            "provides": ["P2_PLAN_VERIFIED"],
            "cost": 1,
            "result_fields": [],
            "action": {
                "type": "verified_policy",
                "verifier_id": "P2_AUTHENTICATED_TOP_LAW_V1",
                "verifier_payload": {
                    "raw_source": raw,
                    "source_id": source_id,
                },
            },
        }],
    }
    evidence = {
        "compiler": "p2_explicit_contract_membership_v1",
        "membership_receipt": membership.get("membership_receipt"),
        "raw_source_sha256": membership.get("raw_source_sha256"),
        "normalized_public_sha256": membership.get("normalized_public_sha256"),
    }
    return problem, evidence


def _compile_bound_goal(task: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    _exact_keys(task, {"goal"}, {"goal"}, "BOUND_GOAL_TASK")
    goal = task.get("goal")
    if not isinstance(goal, str) or not goal.strip():
        raise ProblemContractError("GOAL_REQUIRED")
    compiled = compile_bound_goal(goal)
    if compiled.get("pass") is not True:
        raise ProblemContractError("BOUND_GOAL_NOT_COMPILED:" + str(compiled.get("status")))

    problem = {
        "initial_facts": [],
        "target_effects": ["BOUND_PLAN_VERIFIED"],
        "max_solver_cycles": 4,
        "capabilities": [{
            "id": "owned-bound-goal-plan",
            "requires": [],
            "provides": ["BOUND_PLAN_VERIFIED"],
            "cost": 1,
            "result_fields": [],
            "action": {
                "type": "verified_policy",
                "verifier_id": "BOUND_GOAL_PLAN_V1",
                "verifier_payload": {"goal": goal},
            },
        }],
    }
    evidence = {
        "compiler": "bound_goal_plan_adapter_v1",
        "goal_sha256": compiled.get("goal_sha256"),
        "compiled_plan_sha256": compiled.get("compiled_plan_sha256"),
        "execution_authority": False,
    }
    return problem, evidence


_COMPILERS = {
    SOURCE_ALIGNED: _compile_source_aligned,
    P2_TOP_LAW: _compile_p2,
    BOUND_GOAL_PLAN: _compile_bound_goal,
}


def compile_owned_problem(contract: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(contract, Mapping):
            raise ProblemContractError("CONTRACT_NOT_OBJECT")
        _exact_keys(contract, {"schema", "kind", "task"}, {"schema", "kind", "task"}, "CONTRACT")
        if contract.get("schema") != CONTRACT_SCHEMA:
            raise ProblemContractError("CONTRACT_SCHEMA_INVALID")
        kind = contract.get("kind")
        if kind not in KINDS:
            raise ProblemContractError("CONTRACT_KIND_UNSUPPORTED")
        task = contract.get("task")
        if not isinstance(task, Mapping):
            raise ProblemContractError("TASK_NOT_OBJECT")

        problem, evidence = _COMPILERS[str(kind)](task)
        contract_sha = _sha(contract)
        problem_sha = _sha(problem)
        authority_core = {
            "contract_schema": CONTRACT_SCHEMA,
            "contract_kind": kind,
            "contract_sha256": contract_sha,
            "problem_sha256": problem_sha,
            "compiler_evidence": evidence,
            "raw_solver_problem_injection_permitted": False,
            "caller_verifier_selection_permitted": False,
            "caller_capability_graph_injection_permitted": False,
        }
        return {
            "schema": SCHEMA,
            "status": "PASS__BRAIN_OWNED_EXECUTABLE_PROBLEM_RECOMPUTED",
            "pass": True,
            "contract_kind": kind,
            "contract_sha256": contract_sha,
            "problem_sha256": problem_sha,
            "problem": problem,
            "authority_receipt_sha256": _sha(authority_core),
            "authority": authority_core,
            "task_root_authority": {
                "state": "UPSTREAM_ROOT_OF_TRUST",
                "self_proved_by_solver": False,
                "rule": (
                    "THE_UPSTREAM_TASK_OR_EVALUATION_INGRESS_DEFINES_THE_TASK;"
                    "THIS_MODULE_PROVES_ONLY_THAT_THE_EXECUTABLE_PROBLEM_IS_A_DETERMINISTIC_BRAIN_OWNED_COMPILATION_OF_THAT_INPUT"
                ),
            },
            "execution_authority": False,
            "terminal_authority": False,
            "ownership_boundary": (
                "NO_CALLER_AUTHORED_CAPABILITY_GRAPH_VERIFIER_ID_OR_ACTION_PAYLOAD_ENTERS_OWNED_MODE;"
                "ROOT_TASK_INPUT_AUTHORITY_REMAINS_THE_UNAVOIDABLE_UPSTREAM_TRUST_ROOT"
            ),
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "execution_authority": False,
            "terminal_authority": False,
        }
