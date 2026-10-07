"""Universal Verified Adaptive Solver V4.

V4 is the first integrated adaptive/learning controller over the existing Brain
universal solver stack.

It reuses V1 as a *single-capability* execution engine because V1 already owns:
- content-bound general-cognition proposal packets,
- immutable verifier adapters,
- proposal-free deterministic routes,
- finite/constructive typed proposal search,
- verified effect execution and readback,
- proposal authority separation.

V4 does NOT trust V1 to mint global facts. Before a capability can contribute any
fact to V4 global state, V4 independently authenticates a V3-style
content-addressed effect-semantics receipt + independent-verification receipt that
binds the exact task contract, capability, prerequisites, verifier payload,
verifier success condition, and provided effects.

V4 adds:
- global append-only verified state lineage,
- counterexample-driven route fallback,
- strict distinction between route falsification and mere proposal exhaustion,
- safe stop on ambiguous external-effect outcomes,
- repeated verified-episode -> executable-skill-candidate induction.

Task/source compilation, open-world capability discovery, independent episode
verification, and final skill behavior-preservation verification remain separate
obligations. No terminal/capability/ownership credit is granted here.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.capability_planner import PlanningFailure, plan_capabilities
from canonical.runtime import universal_verified_adaptive_solver_v1 as v1
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS
from canonical.runtime.universal_verified_adaptive_solver_v3 import (
    BINDING_SCHEMA,
    BINDING_VERIFY_SCHEMA,
    task_contract_sha256,
)
from canonical.runtime.effect_broker_receipt_resolver_v2 import resolve_receipt_bytes
from canonical.runtime.universal_solver_state_capsule_v1 import (
    initialize as initialize_state_capsule,
    append_verified_transition as append_state_transition,
    verify_targets as verify_state_targets,
)
from canonical.runtime.executable_skill_program_v7 import (
    ExecutableSkillProgramError,
    induce_candidate,
    program_digest,
)

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_VERIFIED_ADAPTIVE_SOLVER_V4"


class UniversalSolverV4Error(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _digest(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _tok(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise UniversalSolverV4Error(label + "_INVALID")
    return value.strip()


def _tokens(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise UniversalSolverV4Error(label + "_INVALID")
    out = [_tok(x, label) for x in value]
    if len(out) != len(set(out)):
        raise UniversalSolverV4Error(label + "_DUPLICATE")
    if not allow_empty and not out:
        raise UniversalSolverV4Error(label + "_EMPTY")
    return out


def _caps(problem: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw = problem.get("capabilities")
    if not isinstance(raw, list) or not raw:
        raise UniversalSolverV4Error("CAPABILITIES_REQUIRED")
    out: dict[str, Mapping[str, Any]] = {}
    for row in raw:
        if not isinstance(row, Mapping):
            raise UniversalSolverV4Error("CAPABILITY_NOT_OBJECT")
        cid = _tok(row.get("id"), "CAPABILITY_ID")
        if cid in out:
            raise UniversalSolverV4Error("CAPABILITY_ID_DUPLICATE:" + cid)
        out[cid] = row
    return out


def _active_verifier(cap: Mapping[str, Any]) -> tuple[str, Mapping[str, Any], bool]:
    action = cap.get("action")
    if not isinstance(action, Mapping):
        raise UniversalSolverV4Error("CAPABILITY_ACTION_INVALID:" + str(cap.get("id")))
    effectful = action.get("type") == "verified_effect_tool"
    vid = action.get("pre_verifier_id") if effectful else action.get("verifier_id")
    payload = action.get("pre_verifier_payload") if effectful else action.get("verifier_payload")
    vid = _tok(vid, "ACTIVE_VERIFIER_ID")
    if vid not in v1.BUILTIN_VERIFIERS:
        raise UniversalSolverV4Error("ACTIVE_VERIFIER_NOT_BUILTIN:" + vid)
    if not isinstance(payload, Mapping):
        raise UniversalSolverV4Error("ACTIVE_VERIFIER_PAYLOAD_INVALID")
    return vid, payload, effectful


def _validate_structural_effect_contract(cap: Mapping[str, Any]) -> dict[str, Any]:
    cid = _tok(cap.get("id"), "CAPABILITY_ID")
    requires = sorted(_tokens(cap.get("requires", []), cid + "_REQUIRES"))
    provides = _tokens(cap.get("provides", []), cid + "_PROVIDES", allow_empty=False)
    vid, payload, effectful = _active_verifier(cap)
    success = SUCCESS_CONDITIONS.get(vid)
    if success is None:
        raise UniversalSolverV4Error("VERIFIER_SUCCESS_CONDITION_UNBOUND:" + cid + ":" + vid)
    action = cap["action"]
    contract = action.get("effect_contract")
    if not isinstance(contract, Mapping):
        raise UniversalSolverV4Error("EFFECT_CONTRACT_REQUIRED:" + cid)
    if set(contract) != {"effects", "verifier_success_condition"}:
        raise UniversalSolverV4Error("EFFECT_CONTRACT_FIELDS_INVALID:" + cid)
    effects = _tokens(contract.get("effects"), cid + "_EFFECTS", allow_empty=False)
    if effects != provides:
        raise UniversalSolverV4Error("PROVIDES_EFFECT_CONTRACT_MISMATCH:" + cid)
    if contract.get("verifier_success_condition") != success:
        raise UniversalSolverV4Error("VERIFIER_SUCCESS_CONDITION_MISMATCH:" + cid)
    if not isinstance(cap.get("effect_semantics_binding"), Mapping):
        raise UniversalSolverV4Error("EFFECT_SEMANTICS_BINDING_REQUIRED:" + cid)
    return {
        "capability_id": cid,
        "requires": requires,
        "effects": sorted(effects),
        "verifier_id": vid,
        "verifier_payload_sha256": _digest(payload),
        "verifier_success_condition": success,
        "effectful": effectful,
    }


def _authenticate_effect_semantics(
    problem: Mapping[str, Any],
    cap: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    bound = _validate_structural_effect_contract(cap)
    pair = cap["effect_semantics_binding"]
    rr = resolve_receipt_bytes(pair.get("receipt"), repo_root=repo_root)
    vr = resolve_receipt_bytes(pair.get("verification"), repo_root=repo_root)
    rd = rr["document"]
    vd = vr["document"]
    if rd.get("schema") != BINDING_SCHEMA:
        raise UniversalSolverV4Error("EFFECT_SEMANTICS_SCHEMA_INVALID:" + bound["capability_id"])
    if vd.get("schema") != BINDING_VERIFY_SCHEMA:
        raise UniversalSolverV4Error("EFFECT_SEMANTICS_VERIFY_SCHEMA_INVALID:" + bound["capability_id"])
    if vd.get("subject_git_blob_sha") != rr["git_blob_sha"]:
        raise UniversalSolverV4Error("EFFECT_SEMANTICS_VERIFY_SUBJECT_MISMATCH:" + bound["capability_id"])

    expected = {
        "capability_id": bound["capability_id"],
        "task_contract_sha256": task_contract_sha256(problem),
        "requires": bound["requires"],
        "verifier_id": bound["verifier_id"],
        "verifier_payload_sha256": bound["verifier_payload_sha256"],
        "verifier_success_condition": bound["verifier_success_condition"],
        "provided_effects": bound["effects"],
    }
    for key, value in expected.items():
        if rd.get(key) != value:
            raise UniversalSolverV4Error("EFFECT_SEMANTICS_RECEIPT_MISMATCH:" + bound["capability_id"] + ":" + key)
        if vd.get(key) != value:
            raise UniversalSolverV4Error("EFFECT_SEMANTICS_VERIFY_MISMATCH:" + bound["capability_id"] + ":" + key)
    if rd.get("pass") is not True or rd.get("claim") != "BUILTIN_VERIFIER_PASS_IMPLIES_EXACT_PROVIDED_EFFECTS":
        raise UniversalSolverV4Error("EFFECT_SEMANTICS_RECEIPT_CLAIM_INVALID:" + bound["capability_id"])
    if (
        vd.get("pass") is not True
        or vd.get("independent_verified") is not True
        or vd.get("implication_semantics_verified") is not True
    ):
        raise UniversalSolverV4Error("EFFECT_SEMANTICS_INDEPENDENT_VERIFICATION_INVALID:" + bound["capability_id"])
    verifier = _tok(vd.get("independent_verifier_id"), "INDEPENDENT_VERIFIER_ID")
    return {
        **bound,
        "receipt": {"path": rr["path"], "git_blob_sha": rr["git_blob_sha"]},
        "verification": {"path": vr["path"], "git_blob_sha": vr["git_blob_sha"]},
        "independent_verifier_id": verifier,
    }


def _filtered_problem(problem: Mapping[str, Any], current: Sequence[str], excluded: set[str]) -> dict[str, Any]:
    out = deepcopy(dict(problem))
    out["initial_facts"] = list(current)
    out["capabilities"] = [
        deepcopy(dict(row))
        for row in problem.get("capabilities", [])
        if isinstance(row, Mapping) and str(row.get("id") or "") not in excluded
    ]
    return out


def _single_problem(problem: Mapping[str, Any], current: Sequence[str], cap: Mapping[str, Any]) -> dict[str, Any]:
    current_set = set(current)
    targets = [x for x in _tokens(cap.get("provides", []), "CAP_PROVIDES", allow_empty=False) if x not in current_set]
    if not targets:
        raise UniversalSolverV4Error("SELECTED_CAPABILITY_PROVIDES_NO_NEW_FACT")
    return {
        "initial_facts": list(current),
        "target_effects": targets,
        "capabilities": [deepcopy(dict(cap))],
        "max_solver_cycles": 8,
    }


def _complete_route_failure(cap: Mapping[str, Any], out: Mapping[str, Any]) -> bool:
    status = str(out.get("status") or "")
    action = cap.get("action") or {}
    vid, _, _ = _active_verifier(cap)
    if status == "NO_PROPOSAL_IN_DECLARED_FINITE_SEARCH_DOMAIN":
        search = out.get("proposal_search")
        return isinstance(search, Mapping) and search.get("complete_over_declared_domains") is True
    if status == "NO_PROPOSAL_IN_DECLARED_CONSTRUCTIVE_FRAGMENT":
        search = out.get("proposal_search")
        return isinstance(search, Mapping) and search.get("complete_for_declared_fragment") is True
    if vid in v1.PROPOSAL_FREE_VERIFIERS and status == "ALL_AVAILABLE_PROPOSALS_FALSIFIED":
        return True
    if status == "ALL_AVAILABLE_PROPOSALS_FALSIFIED":
        for row in reversed(out.get("proposal_searches") or []):
            if not isinstance(row, Mapping):
                continue
            if row.get("complete_over_declared_domains") is True or row.get("complete_for_declared_fragment") is True:
                return True
    return False


def _effect_may_have_occurred(cap: Mapping[str, Any], out: Mapping[str, Any]) -> bool:
    _, _, effectful = _active_verifier(cap)
    if not effectful or out.get("pass") is True:
        return False
    status = str(out.get("status") or "")
    guaranteed_precarrier = {
        "NEED_PROPOSAL",
        "NEED_MORE_INFORMATION",
        "ALL_AVAILABLE_PROPOSALS_FALSIFIED",
        "NO_PROPOSAL_IN_DECLARED_FINITE_SEARCH_DOMAIN",
        "NO_PROPOSAL_IN_DECLARED_CONSTRUCTIVE_FRAGMENT",
        "FAIL_CLOSED__PROPOSAL_SEARCH_FAILED",
        "FAIL_CLOSED__PROPOSAL_CONSTRUCTION_FAILED",
        "BLOCKED__EFFECT_ROOT_REQUIRED",
    }
    return status not in guaranteed_precarrier


def _steps(trace: Sequence[Mapping[str, Any]], caps: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in trace:
        cid = str(row.get("capability_id") or "").strip()
        if not cid:
            continue
        cap = caps.get(cid)
        if cap is None:
            raise UniversalSolverV4Error("TRACE_CAPABILITY_UNKNOWN:" + cid)
        out.append({
            "op": cid,
            "inputs": sorted(_tokens(cap.get("requires", []), cid + "_REQUIRES")),
            "outputs": sorted(_tokens(cap.get("provides", []), cid + "_PROVIDES", allow_empty=False)),
        })
    if not out:
        raise UniversalSolverV4Error("SOLVED_TRACE_EMPTY")
    return out


def _episode(problem, trace, caps, episode_id, scope_id, invalidators, receipt):
    steps = _steps(trace, caps)
    pre = sorted(_tokens(problem.get("initial_facts", []), "INITIAL_FACTS"))
    post = sorted(_tokens(problem.get("target_effects", []), "TARGET_EFFECTS", allow_empty=False))
    inv = sorted(invalidators)
    digest = program_digest(steps=steps, preconditions=pre, postconditions=post, invalidators=inv)
    out = {
        "episode_id": episode_id,
        "scope_id": scope_id,
        "steps": steps,
        "preconditions": pre,
        "postconditions": post,
        "invalidators": inv,
        "program_sha256": digest,
    }
    if isinstance(receipt, Mapping):
        out["verification_receipt"] = dict(receipt)
    return out


def _episode_receipt_ok(ep: Mapping[str, Any], receipt: Mapping[str, Any] | None) -> tuple[bool, str | None]:
    if not isinstance(receipt, Mapping):
        return False, "EPISODE_VERIFICATION_RECEIPT_REQUIRED"
    expected = {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "behavior_verified": True,
        "episode_id": ep["episode_id"],
        "scope_id": ep["scope_id"],
        "program_sha256": ep["program_sha256"],
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            return False, "EPISODE_RECEIPT_BINDING_MISMATCH:" + key
    if not isinstance(receipt.get("receipt_id"), str) or not receipt["receipt_id"].strip():
        return False, "EPISODE_RECEIPT_ID_REQUIRED"
    return True, None


def run(
    problem: Mapping[str, Any],
    *,
    proposal_packets: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    repo_root: str | Path,
    effect_root: str | None = None,
    episode_id: str = "episode",
    scope_id: str = "scope",
    episode_verification_receipt: Mapping[str, Any] | None = None,
    prior_verified_episodes: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    try:
        if not isinstance(problem, Mapping):
            return _fail("PROBLEM_NOT_OBJECT")
        _tok(problem.get("task_id"), "TASK_ID")
        caps = _caps(problem)
        initial = _tokens(problem.get("initial_facts", []), "INITIAL_FACTS")
        targets = _tokens(problem.get("target_effects", []), "TARGET_EFFECTS", allow_empty=False)
        if set(initial) & set(targets):
            return _fail("TARGET_EFFECT_MAY_NOT_BE_SELF_ASSERTED_AS_INITIAL_FACT")
        semantics = {
            cid: _authenticate_effect_semantics(problem, cap, repo_root=repo_root)
            for cid, cap in caps.items()
        }
        if not isinstance(prior_verified_episodes, Sequence) or isinstance(prior_verified_episodes, (str, bytes)):
            return _fail("PRIOR_VERIFIED_EPISODES_INVALID")
        episode_id = _tok(episode_id, "EPISODE_ID")
        scope_id = _tok(scope_id, "SCOPE_ID")

        current = sorted(set(initial))
        excluded: set[str] = set()
        falsified: set[str] = set()
        deferred: set[str] = set()
        trace: list[dict[str, Any]] = []
        counterexamples: list[dict[str, Any]] = []
        attempts: list[dict[str, Any]] = []
        pending: list[dict[str, Any]] = []
        capsule = initialize_state_capsule(problem)

        max_cycles = int(problem.get("max_solver_cycles", 256))
        if max_cycles < 1 or max_cycles > 10000:
            return _fail("MAX_SOLVER_CYCLES_INVALID")

        for cycle in range(max_cycles):
            if set(targets).issubset(current):
                verdict = verify_state_targets(capsule, targets)
                if verdict.get("pass") is not True:
                    return _fail("TARGET_FACTS_WITHOUT_VALID_GLOBAL_LINEAGE", state_target_verdict=verdict)
                invalidators = (
                    ["route_falsified:" + x for x in sorted(falsified)]
                    + ["route_deferred:" + x for x in sorted(deferred)]
                )
                ep = _episode(problem, trace, caps, episode_id, scope_id, invalidators, episode_verification_receipt)
                ep_ok, ep_error = _episode_receipt_ok(ep, episode_verification_receipt)
                candidate = None
                candidate_error = None
                if ep_ok and prior_verified_episodes:
                    try:
                        candidate = induce_candidate([*prior_verified_episodes, ep])
                    except ExecutableSkillProgramError as exc:
                        candidate_error = str(exc)
                return {
                    "schema": SCHEMA,
                    "status": (
                        "SOLVED__SKILL_CANDIDATE_READY" if candidate is not None
                        else "SOLVED__VERIFIED_EPISODE" if ep_ok
                        else "SOLVED__EPISODE_VERIFICATION_REQUIRED"
                    ),
                    "pass": True,
                    "verified_facts": current,
                    "trace": trace,
                    "attempts": attempts,
                    "counterexamples": counterexamples,
                    "falsified_capability_ids": sorted(falsified),
                    "deferred_capability_ids": sorted(deferred),
                    "state_capsule": capsule,
                    "state_capsule_head_hash": capsule.get("head_hash"),
                    "state_target_verdict": verdict,
                    "current_episode": ep,
                    "current_episode_verified": ep_ok,
                    "episode_verification_error": ep_error,
                    "skill_candidate": candidate,
                    "skill_candidate_error": candidate_error,
                    "skill_candidate_reuse_authorized": bool(candidate and candidate.get("reuse_authorized")),
                    "learning_boundary": "SKILL_CANDIDATE_REQUIRES_SEPARATE_INDEPENDENT_BEHAVIOR_PRESERVATION_VERIFICATION",
                    "terminal_authority": False,
                    "capability_credit_delta": 0,
                    "ownership_credit_delta": 0,
                }

            planning_problem = _filtered_problem(problem, current, excluded)
            if not planning_problem.get("capabilities"):
                break
            try:
                plan = plan_capabilities(planning_problem)
            except PlanningFailure:
                break
            if not plan.get("plan"):
                break
            cid = str(plan["plan"][0])
            cap = caps[cid]
            single = _single_problem(problem, current, cap)
            out = v1.run(single, proposal_packets=proposal_packets, effect_root=effect_root)
            attempts.append({
                "cycle": cycle,
                "capability_id": cid,
                "status": out.get("status"),
                "excluded_capability_ids": sorted(excluded),
            })

            if out.get("pass") is True and out.get("status") == "SOLVED__ALL_TARGET_EFFECTS_VERIFIED":
                rows = [
                    x for x in (out.get("trace") or [])
                    if isinstance(x, Mapping) and x.get("capability_id") == cid
                ]
                if len(rows) != 1:
                    return _fail("SINGLE_CAPABILITY_TRACE_CARDINALITY_INVALID:" + cid)
                row = dict(rows[0])
                row["cycle"] = len(trace)
                row["verifier_success_condition"] = semantics[cid]["verifier_success_condition"]
                row["effect_semantics_receipt"] = semantics[cid]["receipt"]
                row["effect_semantics_verification"] = semantics[cid]["verification"]
                row["effect_semantics_authenticated"] = True
                row["independent_effect_semantics_verifier_id"] = semantics[cid]["independent_verifier_id"]
                row["new_verified_facts"] = list(semantics[cid]["effects"])
                capsule = append_state_transition(capsule, capability=cap, trace_row=row)
                current = sorted(set(current) | set(row["new_verified_facts"]))
                trace.append(row)
                continue

            if _effect_may_have_occurred(cap, out):
                return {
                    "schema": SCHEMA,
                    "status": "EFFECT_OUTCOME_UNRESOLVED__AUTHENTICATED_RECOVERY_REQUIRED",
                    "pass": False,
                    "capability_id": cid,
                    "solver_v1_result": out,
                    "verified_facts": current,
                    "trace": trace,
                    "attempts": attempts,
                    "counterexamples": counterexamples,
                    "falsified_capability_ids": sorted(falsified),
                    "deferred_capability_ids": sorted(deferred),
                    "state_capsule": capsule,
                    "terminal_authority": False,
                }

            complete = _complete_route_failure(cap, out)
            counterexamples.append({
                "cycle": cycle,
                "capability_id": cid,
                "solver_status": out.get("status"),
                "route_falsified_for_current_contract": complete,
                "reason": out.get("reason"),
            })
            pending.append(out)
            excluded.add(cid)
            (falsified if complete else deferred).add(cid)

        if deferred:
            first = next(
                (
                    x for x in pending
                    if x.get("next_capability_id") in deferred
                    and x.get("status") in {"NEED_PROPOSAL", "NEED_MORE_INFORMATION"}
                ),
                pending[0] if pending else None,
            )
            return {
                "schema": SCHEMA,
                "status": "UNRESOLVED__ALTERNATIVE_ROUTES_EXHAUSTED__DEFERRED_ROUTE_REMAINS",
                "pass": False,
                "verified_facts": current,
                "trace": trace,
                "attempts": attempts,
                "counterexamples": counterexamples,
                "falsified_capability_ids": sorted(falsified),
                "deferred_capability_ids": sorted(deferred),
                "next_required_input": None if first is None else {
                    "capability_id": first.get("next_capability_id"),
                    "status": first.get("status"),
                    "proposal_request": first.get("proposal_request"),
                    "reason": first.get("reason"),
                    "detail": first.get("detail"),
                },
                "state_capsule": capsule,
                "terminal_authority": False,
                "capability_credit_delta": 0,
                "ownership_credit_delta": 0,
            }

        return {
            "schema": SCHEMA,
            "status": "CAPABILITY_DISCOVERY_REQUIRED__ALL_DECLARED_ROUTES_FALSIFIED_OR_UNREACHABLE",
            "pass": False,
            "verified_facts": current,
            "trace": trace,
            "attempts": attempts,
            "counterexamples": counterexamples,
            "falsified_capability_ids": sorted(falsified),
            "deferred_capability_ids": [],
            "target_effects": targets,
            "state_capsule": capsule,
            "proposal_sources_allowed": True,
            "proposal_sources_have_authority": False,
            "terminal_authority": False,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))
