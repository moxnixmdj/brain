"""Universal Verified Adaptive Solver V3.

V3 closes the remaining V2 verifier-to-effect semantic self-certification channel.

V2 required a structural effect_contract but both capability.provides and the
effect_contract were still caller-controlled labels. V3 requires a separate
content-addressed effect-semantics receipt plus a separate content-addressed
independent-verification receipt. Those receipts bind:

- exact task contract,
- exact capability id and prerequisites,
- exact built-in verifier id,
- exact verifier payload digest,
- exact built-in verifier success condition,
- exact provided effect set.

Only after both the built-in verifier passes and that implication binding
authenticates may the effect enter trusted state.

V3 removes arbitrary verified_facts resume. Every run recomputes from the task
contract. Persistent state reuse requires a future independently authenticated
state capsule.

This remains a pure control/verification loop. External side effects require
separate effect-broker/carrier authorization and are not executed here.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.capability_planner import PlanningFailure, plan_capabilities
from canonical.runtime.effect_broker_receipt_resolver_v2 import (
    ReceiptResolutionError,
    resolve_receipt_bytes,
)
from canonical.runtime.universal_verified_adaptive_solver_v1 import (
    BUILTIN_VERIFIERS,
    PROPOSAL_FREE_VERIFIERS,
    UniversalSolverError,
    _normalize_caps,
)
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_VERIFIED_ADAPTIVE_SOLVER_V3"
BINDING_SCHEMA = "PROJECT_BRAIN_CAPABILITY_EFFECT_SEMANTICS_BINDING_V1"
BINDING_VERIFY_SCHEMA = "PROJECT_BRAIN_CAPABILITY_EFFECT_SEMANTICS_INDEPENDENT_VERIFICATION_V1"


class UniversalSolverV3Error(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise UniversalSolverV3Error(label + "_INVALID")
    return value.strip()


def _string_list(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise UniversalSolverV3Error(label + "_INVALID")
    out = [_token(x, label) for x in value]
    if not allow_empty and not out:
        raise UniversalSolverV3Error(label + "_EMPTY")
    if len(out) != len(set(out)):
        raise UniversalSolverV3Error(label + "_DUPLICATE")
    return out


def _task_contract(problem: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "task_id": _token(problem.get("task_id"), "TASK_ID"),
        "initial_facts": sorted(_string_list(problem.get("initial_facts", []), "INITIAL_FACTS")),
        "target_effects": sorted(_string_list(problem.get("target_effects", []), "TARGET_EFFECTS", allow_empty=False)),
    }


def task_contract_sha256(problem: Mapping[str, Any]) -> str:
    return _digest(_task_contract(problem))


def _normalize_caps_v3(problem: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    caps = _normalize_caps(problem)
    for cid, cap in caps.items():
        provides = _string_list(cap.get("provides", []), cid + ".provides", allow_empty=False)
        requires = _string_list(cap.get("requires", []), cid + ".requires")
        action = cap["action"]
        verifier_id = str(action["verifier_id"])
        success = SUCCESS_CONDITIONS.get(verifier_id)
        if success is None:
            raise UniversalSolverV3Error("VERIFIER_SUCCESS_CONDITION_UNBOUND:" + cid)

        contract = action.get("effect_contract")
        if not isinstance(contract, Mapping):
            raise UniversalSolverV3Error("EFFECT_CONTRACT_REQUIRED:" + cid)
        if set(contract) != {"effects", "verifier_success_condition"}:
            raise UniversalSolverV3Error("EFFECT_CONTRACT_FIELDS_INVALID:" + cid)
        if contract.get("effects") != provides:
            raise UniversalSolverV3Error("PROVIDES_EFFECT_CONTRACT_MISMATCH:" + cid)
        if contract.get("verifier_success_condition") != success:
            raise UniversalSolverV3Error("VERIFIER_SUCCESS_CONDITION_MISMATCH:" + cid)

        binding = cap.get("effect_semantics_binding")
        if not isinstance(binding, Mapping):
            raise UniversalSolverV3Error("EFFECT_SEMANTICS_BINDING_REQUIRED:" + cid)

        row = dict(cap)
        row["requires"] = requires
        row["provides"] = provides
        row["effect_semantics_binding"] = dict(binding)
        caps[cid] = row
    return caps


def _authenticate_effect_semantics(
    *,
    problem: Mapping[str, Any],
    cap: Mapping[str, Any],
    repo_root: str | Path,
) -> dict[str, Any]:
    pair = cap["effect_semantics_binding"]
    try:
        rr = resolve_receipt_bytes(pair.get("receipt"), repo_root=repo_root)
        vr = resolve_receipt_bytes(pair.get("verification"), repo_root=repo_root)
    except ReceiptResolutionError as exc:
        raise UniversalSolverV3Error("EFFECT_SEMANTICS_RECEIPT_RESOLUTION_FAILED:" + str(exc)) from exc

    rd = rr["document"]
    vd = vr["document"]
    if rd.get("schema") != BINDING_SCHEMA:
        raise UniversalSolverV3Error("EFFECT_SEMANTICS_SCHEMA_INVALID:" + cap["id"])
    if vd.get("schema") != BINDING_VERIFY_SCHEMA:
        raise UniversalSolverV3Error("EFFECT_SEMANTICS_VERIFY_SCHEMA_INVALID:" + cap["id"])
    if vd.get("subject_git_blob_sha") != rr["git_blob_sha"]:
        raise UniversalSolverV3Error("EFFECT_SEMANTICS_VERIFY_SUBJECT_MISMATCH:" + cap["id"])

    verifier_id = str(cap["action"]["verifier_id"])
    payload_sha = _digest(cap["action"]["verifier_payload"])
    success = SUCCESS_CONDITIONS[verifier_id]
    contract_sha = task_contract_sha256(problem)
    requires = sorted(cap["requires"])
    effects = sorted(cap["provides"])

    required = {
        "capability_id": cap["id"],
        "task_contract_sha256": contract_sha,
        "requires": requires,
        "verifier_id": verifier_id,
        "verifier_payload_sha256": payload_sha,
        "verifier_success_condition": success,
        "provided_effects": effects,
        "pass": True,
        "claim": "BUILTIN_VERIFIER_PASS_IMPLIES_EXACT_PROVIDED_EFFECTS",
    }
    for key, expected in required.items():
        if rd.get(key) != expected:
            raise UniversalSolverV3Error("EFFECT_SEMANTICS_RECEIPT_MISMATCH:" + cap["id"] + ":" + key)

    required_verify = {
        "capability_id": cap["id"],
        "task_contract_sha256": contract_sha,
        "requires": requires,
        "verifier_id": verifier_id,
        "verifier_payload_sha256": payload_sha,
        "verifier_success_condition": success,
        "provided_effects": effects,
        "pass": True,
        "independent_verified": True,
        "implication_semantics_verified": True,
    }
    for key, expected in required_verify.items():
        if vd.get(key) != expected:
            raise UniversalSolverV3Error("EFFECT_SEMANTICS_VERIFY_MISMATCH:" + cap["id"] + ":" + key)

    return {
        "receipt": {"path": rr["path"], "git_blob_sha": rr["git_blob_sha"]},
        "verification": {"path": vr["path"], "git_blob_sha": vr["git_blob_sha"]},
        "independent_verifier_id": _token(vd.get("independent_verifier_id"), "INDEPENDENT_VERIFIER_ID"),
        "provided_effects": effects,
        "verifier_success_condition": success,
    }


def run(
    problem: Mapping[str, Any],
    *,
    proposal_packets: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    repo_root: str | Path,
) -> dict[str, Any]:
    try:
        if not isinstance(problem, Mapping):
            raise UniversalSolverV3Error("PROBLEM_NOT_OBJECT")
        contract = _task_contract(problem)
        caps = _normalize_caps_v3(problem)

        initial = list(contract["initial_facts"])
        target = list(contract["target_effects"])
        preloaded_targets = sorted(set(initial) & set(target))
        if preloaded_targets:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED__PRELOADED_TARGET_EFFECT_UNAUTHENTICATED",
                "pass": False,
                "preloaded_target_effects": preloaded_targets,
                "terminal_authority": False,
            }

        planning_problem = dict(problem)
        planning_problem["initial_facts"] = initial
        plan_capabilities(planning_problem)

        available = sorted(initial)
        run_verified_effects: set[str] = set()
        proposals = proposal_packets if isinstance(proposal_packets, Mapping) else {}
        trace: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        used_packets: set[tuple[str, int]] = set()

        max_cycles = int(problem.get("max_solver_cycles", 256))
        if max_cycles < 1 or max_cycles > 10000:
            raise UniversalSolverV3Error("MAX_SOLVER_CYCLES_INVALID")

        for cycle in range(max_cycles):
            if set(target).issubset(run_verified_effects):
                return {
                    "schema": SCHEMA,
                    "status": "SOLVED__ALL_TARGET_EFFECTS_INDEPENDENTLY_SEMANTICS_BOUND",
                    "pass": True,
                    "task_contract": contract,
                    "task_contract_sha256": task_contract_sha256(problem),
                    "verified_facts": available,
                    "run_verified_target_effects": sorted(set(target)),
                    "trace": trace,
                    "rejected_proposals": rejected,
                    "cycles": cycle,
                    "caller_verified_fact_injection_supported": False,
                    "terminal_authority": False,
                    "capability_ownership_credit_delta": 0,
                }

            replanning = dict(problem)
            replanning["initial_facts"] = available
            try:
                plan = plan_capabilities(replanning)
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
                raise UniversalSolverV3Error("PLANNER_EMPTY_PLAN_WITH_UNMET_TARGETS")

            cid = str(plan["plan"][0])
            cap = caps[cid]
            semantics = _authenticate_effect_semantics(
                problem=problem,
                cap=cap,
                repo_root=repo_root,
            )

            action = cap["action"]
            verifier_id = str(action["verifier_id"])
            verifier = BUILTIN_VERIFIERS[verifier_id]
            payload = action["verifier_payload"]
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
                    "effect_semantics_binding": semantics,
                    "verified_facts": available,
                    "trace": trace,
                    "rejected_proposals": rejected,
                    "proposal_has_authority": False,
                    "terminal_authority": False,
                }

            accepted = None
            need_info = None
            for i, packet in enumerate(packets):
                key = (cid, i)
                if key in used_packets:
                    continue
                used_packets.add(key)
                if not isinstance(packet, Mapping):
                    rejected.append({"capability_id": cid, "packet_index": i, "reason": "PROPOSAL_NOT_OBJECT"})
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
                    "effect_semantics_receipt": semantics["receipt"],
                    "effect_semantics_verification": semantics["verification"],
                }
                if verdict.get("pass") is True:
                    accepted = (verdict, record)
                    break
                rejected.append({**record, "reason": verdict.get("reason")})
                if verdict.get("status") == "NEED_MORE_INFORMATION":
                    need_info = verdict

            if accepted is None:
                if need_info is not None:
                    return {
                        "schema": SCHEMA,
                        "status": "NEED_MORE_INFORMATION",
                        "pass": False,
                        "next_capability_id": cid,
                        "verifier_id": verifier_id,
                        "reason": need_info.get("reason"),
                        "detail": need_info.get("detail"),
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
            new_effects = list(semantics["provided_effects"])
            available = sorted(set(available) | set(new_effects))
            run_verified_effects.update(new_effects)
            trace.append({
                **record,
                "verifier_success_condition": semantics["verifier_success_condition"],
                "verified_output": verdict.get("verified_output"),
                "new_verified_effects": new_effects,
                "effect_semantics_authenticated": True,
                "independent_effect_semantics_verifier_id": semantics["independent_verifier_id"],
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
