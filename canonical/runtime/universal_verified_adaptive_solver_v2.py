"""Universal Verified Adaptive Solver V2.

V2 closes a proof-to-effect laundering hole in V1.

V1 could accept a verifier result for one proposition and then copy arbitrary
`capability.provides` labels into the verified fact set. V2 makes the
verifier-success condition -> effect relation explicit and immutable at the
solver boundary:

* each capability must carry one exact effect_contract;
* effect_contract.effects must equal capability.provides exactly;
* the declared verifier success condition must be the built-in condition for
  that verifier kind;
* no target effect preloaded through task initial_facts or caller
  verified_facts can satisfy the solve predicate;
* every target effect in a PASS result must have been minted in this run after
  the corresponding built-in verifier returned pass=True.

This does NOT prove that a human-readable effect label is semantically correct.
Scope-complete task-contract compilation remains upstream. It does prevent the
solver from silently upgrading an unrelated verification into a target effect.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.capability_planner import PlanningFailure, plan_capabilities
from canonical.runtime.universal_verified_adaptive_solver_v1 import (
    BUILTIN_VERIFIERS,
    PROPOSAL_FREE_VERIFIERS,
    UniversalSolverError,
    _normalize_caps,
)

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_VERIFIED_ADAPTIVE_SOLVER_V2"

SUCCESS_CONDITIONS = {
    "EXACT_JSON_V1": "CANDIDATE_EQUALS_EXPECTED",
    "P2_AUTHENTICATED_TOP_LAW_V1": "P2_TOP_LAW_PASS",
    "FINANCE_JUDGMENT_CONTROL_V1": "CONFIGURED_TERMINAL_DECISION_ACCEPTED",
    "UNKNOWN_DOMAIN_JUDGMENT_CONTROL_V1": "CONFIGURED_TERMINAL_DECISION_ACCEPTED",
    "SOURCE_ALIGNED_SEMANTIC_POLICY_V6": "COMMON_POLICY_CERTIFIED",
    "TYPED_ACCEPTANCE_PROGRAM_V1": "TYPED_ACCEPTANCE_PROGRAM_PASS",
    "INSTRUCTION_CONSTRAINTS_V1": "INSTRUCTION_CONSTRAINTS_PASS",
    "STRUCTURED_METHOD_EXPRESSION_AST_V2": "STRUCTURED_METHOD_COMPILED",
}


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _normalize_effect_contracts(problem: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    caps = _normalize_caps(problem)
    for cid, cap in caps.items():
        provides = cap.get("provides")
        if (
            not isinstance(provides, list)
            or not provides
            or any(not isinstance(x, str) or not x for x in provides)
            or len(provides) != len(set(provides))
        ):
            raise UniversalSolverError("CAPABILITY_PROVIDES_INVALID:" + cid)

        action = cap["action"]
        verifier_id = str(action["verifier_id"])
        contract = action.get("effect_contract")
        if not isinstance(contract, Mapping):
            raise UniversalSolverError("EFFECT_CONTRACT_REQUIRED:" + cid)
        if set(contract) != {"effects", "verifier_success_condition"}:
            raise UniversalSolverError("EFFECT_CONTRACT_FIELDS_INVALID:" + cid)

        effects = contract.get("effects")
        if (
            not isinstance(effects, list)
            or not effects
            or any(not isinstance(x, str) or not x for x in effects)
            or len(effects) != len(set(effects))
        ):
            raise UniversalSolverError("EFFECT_CONTRACT_EFFECTS_INVALID:" + cid)
        if effects != provides:
            raise UniversalSolverError("PROVIDES_EFFECT_CONTRACT_MISMATCH:" + cid)

        expected_condition = SUCCESS_CONDITIONS.get(verifier_id)
        if contract.get("verifier_success_condition") != expected_condition:
            raise UniversalSolverError("VERIFIER_SUCCESS_CONDITION_MISMATCH:" + cid)
    return caps


def run(
    problem: Mapping[str, Any],
    *,
    proposal_packets: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    verified_facts: Sequence[str] = (),
) -> dict[str, Any]:
    """Execute a capability plan with target-local proof-to-effect binding.

    Preloaded facts may be used as planning prerequisites, but a target effect
    must be produced by a successful built-in verifier during this invocation.
    A future receipt-authenticated resume layer may relax that boundary.
    """
    try:
        if not isinstance(problem, Mapping):
            raise UniversalSolverError("PROBLEM_NOT_OBJECT")
        caps = _normalize_effect_contracts(problem)

        initial = problem.get("initial_facts", [])
        if not isinstance(initial, list):
            raise UniversalSolverError("INITIAL_FACTS_INVALID")
        if any(not isinstance(x, str) or not x for x in initial):
            raise UniversalSolverError("INITIAL_FACT_INVALID")

        resumed = [str(x) for x in verified_facts if isinstance(x, str) and x]
        available = sorted(set(initial) | set(resumed))

        target = problem.get("target_effects", [])
        if (
            not isinstance(target, list)
            or not target
            or any(not isinstance(x, str) or not x for x in target)
            or len(target) != len(set(target))
        ):
            raise UniversalSolverError("TARGET_EFFECTS_INVALID")

        preloaded_targets = sorted(set(target) & set(available))
        if preloaded_targets:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED__PRELOADED_TARGET_EFFECT_UNAUTHENTICATED",
                "pass": False,
                "preloaded_target_effects": preloaded_targets,
                "reason": "TARGET_EFFECTS_REQUIRE_THIS_RUN_VERIFIER_PROVENANCE",
                "terminal_authority": False,
                "capability_ownership_credit_delta": 0,
            }

        proposals = proposal_packets if isinstance(proposal_packets, Mapping) else {}
        trace: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        used_packets: set[tuple[str, int]] = set()
        run_verified_effects: set[str] = set()

        max_cycles = int(problem.get("max_solver_cycles", 256))
        if max_cycles < 1 or max_cycles > 10000:
            raise UniversalSolverError("MAX_SOLVER_CYCLES_INVALID")

        for cycle in range(max_cycles):
            if set(target).issubset(run_verified_effects):
                return {
                    "schema": SCHEMA,
                    "status": "SOLVED__ALL_TARGET_EFFECTS_VERIFIER_BOUND",
                    "pass": True,
                    "verified_facts": available,
                    "run_verified_target_effects": sorted(set(target)),
                    "trace": trace,
                    "rejected_proposals": rejected,
                    "cycles": cycle,
                    "proof_to_effect_binding": "EXACT_EFFECT_CONTRACT_PER_ACCEPTED_CAPABILITY",
                    "terminal_authority": False,
                    "capability_ownership_credit_delta": 0,
                }

            replanning_problem = dict(problem)
            replanning_problem["initial_facts"] = available
            try:
                plan = plan_capabilities(replanning_problem)
            except PlanningFailure as exc:
                return {
                    "schema": SCHEMA,
                    "status": "UNRESOLVED__NO_CURRENT_CAPABILITY_PLAN",
                    "pass": False,
                    "reason": str(exc),
                    "verified_facts": available,
                    "run_verified_effects": sorted(run_verified_effects),
                    "trace": trace,
                    "rejected_proposals": rejected,
                    "terminal_authority": False,
                }

            if not plan.get("plan"):
                return {
                    "schema": SCHEMA,
                    "status": "FAIL_CLOSED__PLANNER_RETURNED_EMPTY_UNSOLVED_PLAN",
                    "pass": False,
                    "verified_facts": available,
                    "run_verified_effects": sorted(run_verified_effects),
                    "trace": trace,
                    "terminal_authority": False,
                }

            cid = str(plan["plan"][0])
            cap = caps[cid]
            action = cap["action"]
            verifier_id = str(action["verifier_id"])
            verifier = BUILTIN_VERIFIERS[verifier_id]
            payload = action["verifier_payload"]
            effect_contract = action["effect_contract"]

            packets = proposals.get(cid)
            if verifier_id in PROPOSAL_FREE_VERIFIERS:
                packets = [{}]
            if not isinstance(packets, Sequence) or isinstance(packets, (str, bytes)) or not packets:
                return {
                    "schema": SCHEMA,
                    "status": "NEED_PROPOSAL",
                    "pass": False,
                    "next_capability_id": cid,
                    "verifier_id": verifier_id,
                    "verified_facts": available,
                    "run_verified_effects": sorted(run_verified_effects),
                    "trace": trace,
                    "rejected_proposals": rejected,
                    "proposal_has_authority": False,
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
                    rejected.append({
                        "capability_id": cid,
                        "packet_index": i,
                        "reason": "PROPOSAL_NOT_OBJECT",
                    })
                    continue
                verdict = verifier(payload, packet)
                record = {
                    "cycle": cycle,
                    "capability_id": cid,
                    "verifier_id": verifier_id,
                    "packet_index": i,
                    "proposal_sha256": _digest(packet),
                    "verdict_status": verdict.get("status"),
                    "proof_digest": verdict.get("proof_digest"),
                    "effect_contract_sha256": _digest(effect_contract),
                }
                if verdict.get("pass") is True:
                    accepted = (verdict, record)
                    break
                rejected.append({**record, "reason": verdict.get("reason")})
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
                        "verified_facts": available,
                        "run_verified_effects": sorted(run_verified_effects),
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
                    "verified_facts": available,
                    "run_verified_effects": sorted(run_verified_effects),
                    "trace": trace,
                    "rejected_proposals": rejected,
                    "terminal_authority": False,
                }

            verdict, record = accepted
            new_effects = list(effect_contract["effects"])
            available = sorted(set(available) | set(new_effects))
            run_verified_effects.update(new_effects)
            trace.append({
                **record,
                "verifier_success_condition": effect_contract["verifier_success_condition"],
                "verified_output": verdict.get("verified_output"),
                "new_verified_effects": sorted(new_effects),
            })

        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__MAX_SOLVER_CYCLES_EXCEEDED",
            "pass": False,
            "verified_facts": available,
            "run_verified_effects": sorted(run_verified_effects),
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
