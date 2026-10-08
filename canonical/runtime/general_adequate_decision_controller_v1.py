"""General adequate-decision controller V1.

One fail-closed front door for the Brain's R2 decision loop:
raw goal -> authenticated semantic decision context -> minimum policy-changing
information -> authenticated adequate policy -> grounded realization or verified
execution -> actual-goal satisfaction.

The controller never upgrades routing, provider output, or a successful effect into
semantic success. Every authority-bearing bridge is content-addressed and
independently verified. Provider callbacks are proposal/information carriers only.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.p3_real_context_v3_admission_v12 import evaluate as evaluate_p3
from canonical.runtime.universal_verified_adaptive_solver_v12 import run as run_universal

SCHEMA = "PROJECT_BRAIN_GENERAL_ADEQUATE_DECISION_CONTROLLER_V1"
ROOT = Path(__file__).resolve().parents[2]
GOAL_BINDING_SCHEMA = "PROJECT_BRAIN_GOAL_TO_DECISION_CONTEXT_BINDING_V1"
GOAL_BINDING_VERIFY_SCHEMA = "PROJECT_BRAIN_GOAL_TO_DECISION_CONTEXT_BINDING_INDEPENDENT_VERIFICATION_V1"
POLICY_EXECUTION_SCHEMA = "PROJECT_BRAIN_POLICY_EXECUTION_BINDING_V1"
POLICY_EXECUTION_VERIFY_SCHEMA = "PROJECT_BRAIN_POLICY_EXECUTION_BINDING_INDEPENDENT_VERIFICATION_V1"
GOAL_SATISFACTION_SCHEMA = "PROJECT_BRAIN_GOAL_SATISFACTION_BINDING_V1"
GOAL_SATISFACTION_VERIFY_SCHEMA = "PROJECT_BRAIN_GOAL_SATISFACTION_BINDING_INDEPENDENT_VERIFICATION_V1"
MAX_INFORMATION_ROUNDS = 16


class DecisionControllerError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return "sha256:" + sha256(_canon(value).encode("utf-8")).hexdigest()


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _bound_json(
    ref: Mapping[str, Any],
    *,
    repo_root: Path,
    prefixes: tuple[str, ...],
) -> tuple[dict[str, Any], str, str]:
    if not isinstance(ref, Mapping):
        raise DecisionControllerError("BOUND_REF_REQUIRED")
    rel = str(ref.get("path") or "").strip()
    expected = str(ref.get("git_blob_sha") or "").strip()
    p = Path(rel)
    if not rel or p.is_absolute() or ".." in p.parts:
        raise DecisionControllerError("BOUND_PATH_INVALID")
    if not any(rel.startswith(prefix) for prefix in prefixes):
        raise DecisionControllerError("BOUND_PATH_OUTSIDE_ALLOWED_SCOPE")
    full = repo_root / p
    if not full.is_file():
        raise DecisionControllerError("BOUND_FILE_MISSING:" + rel)
    actual = _git_blob_sha(full)
    if expected != actual:
        raise DecisionControllerError("BOUND_BLOB_DRIFT:" + rel)
    doc = json.loads(full.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise DecisionControllerError("BOUND_JSON_NOT_OBJECT:" + rel)
    return doc, rel, actual


def _authenticate_goal_binding(
    binding: Mapping[str, Any] | None,
    *,
    goal: str,
    decision_payload: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    if not isinstance(binding, Mapping):
        return {"pass": False, "status": "OPEN__GOAL_TO_DECISION_BINDING_REQUIRED"}
    try:
        receipt, receipt_path, receipt_blob = _bound_json(
            binding.get("receipt"),
            repo_root=repo_root,
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        verification, verification_path, verification_blob = _bound_json(
            binding.get("verification"),
            repo_root=repo_root,
            prefixes=("canonical/verification/",),
        )
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        decision_sha = _digest(decision_payload)
        if receipt.get("schema") != GOAL_BINDING_SCHEMA:
            raise DecisionControllerError("GOAL_BINDING_SCHEMA_INVALID")
        if receipt.get("goal_sha256") != goal_sha:
            raise DecisionControllerError("GOAL_BINDING_GOAL_MISMATCH")
        if receipt.get("decision_payload_sha256") != decision_sha:
            raise DecisionControllerError("GOAL_BINDING_DECISION_MISMATCH")
        for field in (
            "binding_proved",
            "load_bearing_constraints_preserved",
            "decision_context_semantically_sufficient",
        ):
            if receipt.get(field) is not True:
                raise DecisionControllerError("GOAL_BINDING_PREMISE_UNPROVED:" + field)
        if verification.get("schema") != GOAL_BINDING_VERIFY_SCHEMA:
            raise DecisionControllerError("GOAL_BINDING_VERIFY_SCHEMA_INVALID")
        if verification.get("subject_git_blob_sha") != receipt_blob:
            raise DecisionControllerError("GOAL_BINDING_VERIFY_SUBJECT_MISMATCH")
        if verification.get("goal_sha256") != goal_sha:
            raise DecisionControllerError("GOAL_BINDING_VERIFY_GOAL_MISMATCH")
        if verification.get("decision_payload_sha256") != decision_sha:
            raise DecisionControllerError("GOAL_BINDING_VERIFY_DECISION_MISMATCH")
        for field in ("pass", "independent_verified", "semantic_preservation_verified"):
            if verification.get(field) is not True:
                raise DecisionControllerError(
                    "GOAL_BINDING_VERIFY_PREMISE_UNPROVED:" + field
                )
        return {
            "pass": True,
            "status": "PASS__GOAL_TO_DECISION_CONTEXT_AUTHENTICATED",
            "goal_sha256": goal_sha,
            "decision_payload_sha256": decision_sha,
            "receipt_path": receipt_path,
            "receipt_git_blob_sha": receipt_blob,
            "verification_path": verification_path,
            "verification_git_blob_sha": verification_blob,
        }
    except Exception as exc:
        return {
            "pass": False,
            "status": "FAIL_CLOSED__GOAL_TO_DECISION_BINDING_INVALID",
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _authenticate_policy_execution_binding(
    binding: Mapping[str, Any] | None,
    *,
    selected_policy_id: str,
    execution_problem: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    if not isinstance(binding, Mapping):
        return {"pass": False, "status": "OPEN__POLICY_EXECUTION_BINDING_REQUIRED"}
    try:
        receipt, receipt_path, receipt_blob = _bound_json(
            binding.get("receipt"),
            repo_root=repo_root,
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        verification, verification_path, verification_blob = _bound_json(
            binding.get("verification"),
            repo_root=repo_root,
            prefixes=("canonical/verification/",),
        )
        problem_sha = _digest(execution_problem)
        if receipt.get("schema") != POLICY_EXECUTION_SCHEMA:
            raise DecisionControllerError("POLICY_EXECUTION_SCHEMA_INVALID")
        if receipt.get("policy_id") != selected_policy_id:
            raise DecisionControllerError("POLICY_EXECUTION_POLICY_MISMATCH")
        if receipt.get("execution_problem_sha256") != problem_sha:
            raise DecisionControllerError("POLICY_EXECUTION_PROBLEM_MISMATCH")
        for field in (
            "binding_proved",
            "brain_owned_execution",
            "execution_success_implies_policy_realization",
            "load_bearing_constraints_preserved",
        ):
            if receipt.get(field) is not True:
                raise DecisionControllerError(
                    "POLICY_EXECUTION_PREMISE_UNPROVED:" + field
                )
        if verification.get("schema") != POLICY_EXECUTION_VERIFY_SCHEMA:
            raise DecisionControllerError("POLICY_EXECUTION_VERIFY_SCHEMA_INVALID")
        if verification.get("subject_git_blob_sha") != receipt_blob:
            raise DecisionControllerError("POLICY_EXECUTION_VERIFY_SUBJECT_MISMATCH")
        if verification.get("policy_id") != selected_policy_id:
            raise DecisionControllerError("POLICY_EXECUTION_VERIFY_POLICY_MISMATCH")
        if verification.get("execution_problem_sha256") != problem_sha:
            raise DecisionControllerError("POLICY_EXECUTION_VERIFY_PROBLEM_MISMATCH")
        for field in ("pass", "independent_verified", "realization_implication_verified"):
            if verification.get(field) is not True:
                raise DecisionControllerError(
                    "POLICY_EXECUTION_VERIFY_PREMISE_UNPROVED:" + field
                )
        return {
            "pass": True,
            "status": "PASS__POLICY_EXECUTION_BINDING_AUTHENTICATED",
            "policy_id": selected_policy_id,
            "execution_problem_sha256": problem_sha,
            "receipt_path": receipt_path,
            "receipt_git_blob_sha": receipt_blob,
            "verification_path": verification_path,
            "verification_git_blob_sha": verification_blob,
        }
    except Exception as exc:
        return {
            "pass": False,
            "status": "FAIL_CLOSED__POLICY_EXECUTION_BINDING_INVALID",
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _authenticate_goal_satisfaction_binding(
    binding: Mapping[str, Any] | None,
    *,
    goal: str,
    selected_policy_id: str,
    realization: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    """Authenticate the final semantic acceptance edge.

    Adequate-policy selection and mechanically verified realization are necessary
    but not sufficient to claim that the caller's original goal was actually
    satisfied. This gate binds an independently verified acceptance receipt to the
    exact raw goal, selected policy, and realized output/execution object.
    """
    if not isinstance(binding, Mapping):
        return {"pass": False, "status": "OPEN__GOAL_SATISFACTION_BINDING_REQUIRED"}
    try:
        receipt, receipt_path, receipt_blob = _bound_json(
            binding.get("receipt"),
            repo_root=repo_root,
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        verification, verification_path, verification_blob = _bound_json(
            binding.get("verification"),
            repo_root=repo_root,
            prefixes=("canonical/verification/",),
        )
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        realization_sha = _digest(realization)
        if receipt.get("schema") != GOAL_SATISFACTION_SCHEMA:
            raise DecisionControllerError("GOAL_SATISFACTION_SCHEMA_INVALID")
        if receipt.get("goal_sha256") != goal_sha:
            raise DecisionControllerError("GOAL_SATISFACTION_GOAL_MISMATCH")
        if receipt.get("policy_id") != selected_policy_id:
            raise DecisionControllerError("GOAL_SATISFACTION_POLICY_MISMATCH")
        if receipt.get("realization_sha256") != realization_sha:
            raise DecisionControllerError("GOAL_SATISFACTION_REALIZATION_MISMATCH")
        for field in (
            "goal_satisfaction_proved",
            "all_load_bearing_constraints_satisfied",
            "acceptance_relation_bound",
        ):
            if receipt.get(field) is not True:
                raise DecisionControllerError(
                    "GOAL_SATISFACTION_PREMISE_UNPROVED:" + field
                )
        if verification.get("schema") != GOAL_SATISFACTION_VERIFY_SCHEMA:
            raise DecisionControllerError("GOAL_SATISFACTION_VERIFY_SCHEMA_INVALID")
        if verification.get("subject_git_blob_sha") != receipt_blob:
            raise DecisionControllerError("GOAL_SATISFACTION_VERIFY_SUBJECT_MISMATCH")
        if verification.get("goal_sha256") != goal_sha:
            raise DecisionControllerError("GOAL_SATISFACTION_VERIFY_GOAL_MISMATCH")
        if verification.get("policy_id") != selected_policy_id:
            raise DecisionControllerError("GOAL_SATISFACTION_VERIFY_POLICY_MISMATCH")
        if verification.get("realization_sha256") != realization_sha:
            raise DecisionControllerError("GOAL_SATISFACTION_VERIFY_REALIZATION_MISMATCH")
        for field in (
            "pass",
            "independent_verified",
            "goal_satisfaction_verified",
            "acceptance_relation_verified",
            "load_bearing_constraints_verified",
        ):
            if verification.get(field) is not True:
                raise DecisionControllerError(
                    "GOAL_SATISFACTION_VERIFY_PREMISE_UNPROVED:" + field
                )
        verifier_id = verification.get("independent_verifier_id")
        if not isinstance(verifier_id, str) or not verifier_id.strip():
            raise DecisionControllerError("GOAL_SATISFACTION_INDEPENDENT_VERIFIER_ID_MISSING")
        return {
            "pass": True,
            "status": "PASS__ACTUAL_GOAL_SATISFACTION_AUTHENTICATED",
            "goal_sha256": goal_sha,
            "policy_id": selected_policy_id,
            "realization_sha256": realization_sha,
            "receipt_path": receipt_path,
            "receipt_git_blob_sha": receipt_blob,
            "verification_path": verification_path,
            "verification_git_blob_sha": verification_blob,
            "independent_verifier_id": verifier_id.strip(),
        }
    except Exception as exc:
        return {
            "pass": False,
            "status": "FAIL_CLOSED__GOAL_SATISFACTION_BINDING_INVALID",
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _extract_information_gap(decision: Mapping[str, Any]) -> dict[str, Any] | None:
    detail = decision.get("detail")
    if not isinstance(detail, Mapping):
        return None
    loop = detail.get("loop_result")
    if not isinstance(loop, Mapping):
        return None
    status = loop.get("status")
    if status not in {
        "OPEN__SELECTED_PREDICATE_PROOF_PAYLOAD_REQUIRED",
        "OPEN__SELECTED_PREDICATE_PROOF_COVERAGE_REQUIRED",
    }:
        return None
    loop_detail = loop.get("detail")
    predicate_id = (
        loop_detail.get("predicate_id") if isinstance(loop_detail, Mapping) else None
    )
    if not isinstance(predicate_id, str) or not predicate_id:
        return None
    return {
        "predicate_id": predicate_id,
        "loop_status": status,
        "loop_reason": loop.get("reason"),
    }


def _append_truth_payload(
    decision_payload: dict[str, Any],
    predicate_id: str,
    payload: Mapping[str, Any],
) -> None:
    loop = decision_payload.get("bound_relevance_cegar_loop")
    if not isinstance(loop, dict):
        raise DecisionControllerError(
            "BOUND_RELEVANCE_CEGAR_LOOP_REQUIRED_FOR_INFORMATION_REFINEMENT"
        )
    by_predicate = loop.setdefault("truth_payloads_by_predicate_id", {})
    if not isinstance(by_predicate, dict):
        raise DecisionControllerError("TRUTH_PAYLOADS_BY_PREDICATE_ID_INVALID")
    prior = by_predicate.get(predicate_id)
    candidate = deepcopy(dict(payload))
    if prior is None:
        by_predicate[predicate_id] = candidate
    elif isinstance(prior, list):
        prior.append(candidate)
    elif isinstance(prior, Mapping):
        by_predicate[predicate_id] = [deepcopy(dict(prior)), candidate]
    else:
        raise DecisionControllerError("EXISTING_TRUTH_PAYLOAD_INVALID")


def _open(
    status: str,
    *,
    task_id: str,
    goal: str,
    raw_contract: Mapping[str, Any],
    **extra: Any,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": False,
        "task_id": task_id,
        "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
        "raw_task_contract_sha256": raw_contract.get("task_contract_sha256"),
        "raw_source_coverage_complete": (
            raw_contract.get("nonwhitespace_source_coverage_complete") is True
        ),
        "semantic_acceptance_complete": False,
        "actual_goal_satisfaction_verified": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def run(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
    information_provider: Callable[
        [Mapping[str, Any], int], Mapping[str, Any] | None
    ]
    | None = None,
    proposal_provider: Callable[..., Mapping[str, Any] | None] | None = None,
    capability_expander: Callable[..., Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else ROOT
    try:
        if not isinstance(request, Mapping):
            raise DecisionControllerError("REQUEST_NOT_OBJECT")
        allowed = {
            "task_id",
            "goal",
            "decision_payload",
            "goal_to_decision_binding",
            "execution_problem",
            "policy_execution_binding",
            "goal_satisfaction_binding",
            "max_information_rounds",
            "episode_id",
            "scope_id",
        }
        extra = set(request) - allowed
        if extra:
            raise DecisionControllerError(
                "UNMODELED_REQUEST_FIELDS:" + ",".join(sorted(extra))
            )
        task_id = str(request.get("task_id") or "").strip()
        goal = str(request.get("goal") or "").strip()
        if not task_id:
            raise DecisionControllerError("TASK_ID_REQUIRED")
        if not goal:
            raise DecisionControllerError("GOAL_REQUIRED")

        raw_contract = compile_contract(
            goal,
            source_id="user",
            routing_target_effects=["decision.adequate_action"],
        )
        if raw_contract.get("pass") is not True:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED__LOSSLESS_RAW_GOAL_CONTRACT",
                "pass": False,
                "task_id": task_id,
                "errors": raw_contract.get("errors"),
                "semantic_acceptance_complete": False,
                "actual_goal_satisfaction_verified": False,
                "terminal_authority": False,
                "terminal_credit_delta": 0,
                "incremental_spend_usd": 0,
            }

        decision_payload = request.get("decision_payload")
        if not isinstance(decision_payload, Mapping):
            return _open(
                "OPEN__DECISION_CONTEXT_REQUIRED",
                task_id=task_id,
                goal=goal,
                raw_contract=raw_contract,
                next_required_edge="AUTHENTICATED_GOAL_TO_DECISION_CONTEXT",
                reason="NO_SOUND_SEMANTIC_DECISION_CONTEXT_BOUND_TO_RAW_GOAL",
            )
        working = deepcopy(dict(decision_payload))

        goal_binding = _authenticate_goal_binding(
            request.get("goal_to_decision_binding"),
            goal=goal,
            decision_payload=decision_payload,
            repo_root=root,
        )
        if goal_binding.get("pass") is not True:
            return _open(
                str(
                    goal_binding.get("status")
                    or "OPEN__GOAL_TO_DECISION_BINDING_REQUIRED"
                ),
                task_id=task_id,
                goal=goal,
                raw_contract=raw_contract,
                next_required_edge="AUTHENTICATED_GOAL_TO_DECISION_CONTEXT",
                goal_to_decision_binding=goal_binding,
            )

        max_rounds = request.get("max_information_rounds", MAX_INFORMATION_ROUNDS)
        if (
            isinstance(max_rounds, bool)
            or not isinstance(max_rounds, int)
            or not 0 <= max_rounds <= MAX_INFORMATION_ROUNDS
        ):
            raise DecisionControllerError("MAX_INFORMATION_ROUNDS_INVALID")

        information_trace: list[dict[str, Any]] = []
        decision = None
        for round_index in range(max_rounds + 1):
            decision = evaluate_p3(working, repo_root=root)
            if decision.get("pass") is True:
                break
            gap = _extract_information_gap(decision)
            if gap is None:
                return _open(
                    "OPEN__ADEQUATE_POLICY_OR_SEMANTIC_COVERAGE_REQUIRED",
                    task_id=task_id,
                    goal=goal,
                    raw_contract=raw_contract,
                    next_required_edge="EXACT_P3_V12_OPEN_EDGE",
                    decision_result=decision,
                    information_trace=information_trace,
                    goal_to_decision_binding=goal_binding,
                )
            request_packet = {
                "schema": "PROJECT_BRAIN_MINIMUM_POLICY_CHANGING_INFORMATION_REQUEST_V1",
                "task_id": task_id,
                "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
                "decision_payload_sha256": _digest(working),
                "predicate_id": gap["predicate_id"],
                "reason": gap["loop_status"],
                "information_authority": False,
                "semantic_truth_authority": False,
            }
            if information_provider is None:
                return _open(
                    "OPEN__MINIMUM_POLICY_CHANGING_INFORMATION_REQUIRED",
                    task_id=task_id,
                    goal=goal,
                    raw_contract=raw_contract,
                    next_required_edge="SOURCE_BOUND_TRUTH_FOR_SELECTED_PREDICATE",
                    next_information_request=request_packet,
                    decision_result=decision,
                    information_trace=information_trace,
                    goal_to_decision_binding=goal_binding,
                )
            if round_index >= max_rounds:
                return _open(
                    "OPEN__MINIMUM_INFORMATION_ROUND_BOUND_EXHAUSTED",
                    task_id=task_id,
                    goal=goal,
                    raw_contract=raw_contract,
                    next_required_edge="STRONGER_INFORMATION_OR_ADEQUACY_EDGE",
                    next_information_request=request_packet,
                    decision_result=decision,
                    information_trace=information_trace,
                    goal_to_decision_binding=goal_binding,
                )
            provided = information_provider(request_packet, round_index)
            information_trace.append(
                {
                    "round": round_index,
                    "predicate_id": gap["predicate_id"],
                    "provider_returned_payload": isinstance(provided, Mapping),
                    "provider_authority": False,
                }
            )
            if not isinstance(provided, Mapping):
                return _open(
                    "OPEN__MINIMUM_POLICY_CHANGING_INFORMATION_REQUIRED",
                    task_id=task_id,
                    goal=goal,
                    raw_contract=raw_contract,
                    next_required_edge="SOURCE_BOUND_TRUTH_FOR_SELECTED_PREDICATE",
                    next_information_request=request_packet,
                    decision_result=decision,
                    information_trace=information_trace,
                    goal_to_decision_binding=goal_binding,
                )
            _append_truth_payload(working, gap["predicate_id"], provided)

        if not isinstance(decision, Mapping) or decision.get("pass") is not True:
            return _open(
                "OPEN__ADEQUATE_DECISION_NOT_CERTIFIED",
                task_id=task_id,
                goal=goal,
                raw_contract=raw_contract,
                decision_result=decision,
                information_trace=information_trace,
                goal_to_decision_binding=goal_binding,
            )

        selected_policy_id = decision.get("selected_policy_id")
        if not isinstance(selected_policy_id, str) or not selected_policy_id:
            raise DecisionControllerError("P3_SELECTED_POLICY_ID_INVALID")

        execution_problem = request.get("execution_problem")
        if execution_problem is None:
            rendered = decision.get("rendered_text")
            if not isinstance(rendered, str) or not rendered:
                return _open(
                    "OPEN__ADEQUATE_POLICY_REALIZATION_REQUIRED",
                    task_id=task_id,
                    goal=goal,
                    raw_contract=raw_contract,
                    next_required_edge="GROUNDED_REALIZATION_OF_SELECTED_POLICY",
                    decision_result=decision,
                    information_trace=information_trace,
                    goal_to_decision_binding=goal_binding,
                )
            realization = {
                "kind": "GROUNDED_DECISION_EXPRESSION",
                "policy_id": selected_policy_id,
                "rendered_text": rendered,
                "decision_result_sha256": _digest(decision),
            }
            goal_satisfaction = _authenticate_goal_satisfaction_binding(
                request.get("goal_satisfaction_binding"),
                goal=goal,
                selected_policy_id=selected_policy_id,
                realization=realization,
                repo_root=root,
            )
            if goal_satisfaction.get("pass") is not True:
                return _open(
                    str(
                        goal_satisfaction.get("status")
                        or "OPEN__GOAL_SATISFACTION_BINDING_REQUIRED"
                    ),
                    task_id=task_id,
                    goal=goal,
                    raw_contract=raw_contract,
                    next_required_edge="INDEPENDENT_ACTUAL_GOAL_SATISFACTION_VERIFICATION",
                    decision_result=decision,
                    realization=realization,
                    goal_satisfaction_binding=goal_satisfaction,
                    information_trace=information_trace,
                    goal_to_decision_binding=goal_binding,
                )
            return {
                "schema": SCHEMA,
                "status": "PASS__GOAL_BOUND_ADEQUATE_DECISION_REALIZED_AND_ACCEPTANCE_VERIFIED",
                "pass": True,
                "task_id": task_id,
                "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
                "raw_task_contract_sha256": raw_contract["task_contract_sha256"],
                "raw_source_coverage_complete": raw_contract[
                    "nonwhitespace_source_coverage_complete"
                ],
                "goal_to_decision_binding": goal_binding,
                "decision_result": decision,
                "selected_policy_id": selected_policy_id,
                "action_kind": "GROUNDED_DECISION_EXPRESSION",
                "action": rendered,
                "realization": realization,
                "goal_satisfaction_binding": goal_satisfaction,
                "information_trace": information_trace,
                "minimum_information_rounds_used": len(information_trace),
                "semantic_acceptance_complete": True,
                "actual_goal_satisfaction_verified": True,
                "verification_scope": (
                    "AUTHENTICATED_GOAL_BOUND_P3_V12_DECISION_CONTEXT"
                ),
                "terminal_authority": False,
                "terminal_credit_delta": 0,
                "incremental_spend_usd": 0,
            }

        if not isinstance(execution_problem, Mapping):
            raise DecisionControllerError("EXECUTION_PROBLEM_NOT_OBJECT")
        execution_binding = _authenticate_policy_execution_binding(
            request.get("policy_execution_binding"),
            selected_policy_id=selected_policy_id,
            execution_problem=execution_problem,
            repo_root=root,
        )
        if execution_binding.get("pass") is not True:
            return _open(
                str(
                    execution_binding.get("status")
                    or "OPEN__POLICY_EXECUTION_BINDING_REQUIRED"
                ),
                task_id=task_id,
                goal=goal,
                raw_contract=raw_contract,
                next_required_edge="AUTHENTICATED_SELECTED_POLICY_TO_EXECUTION_BINDING",
                decision_result=decision,
                information_trace=information_trace,
                goal_to_decision_binding=goal_binding,
                policy_execution_binding=execution_binding,
            )

        execution = run_universal(
            execution_problem,
            repo_root=root,
            episode_id=str(request.get("episode_id") or task_id),
            scope_id=str(request.get("scope_id") or "general-adequate-decision"),
            proposal_provider=proposal_provider,
            capability_expander=capability_expander,
        )
        if execution.get("pass") is not True:
            return _open(
                "OPEN__SELECTED_ADEQUATE_POLICY_EXECUTION_UNRESOLVED",
                task_id=task_id,
                goal=goal,
                raw_contract=raw_contract,
                next_required_edge=(
                    "UNIVERSAL_SOLVER_EXACT_NEXT_REQUIRED_INPUT_OR_CAPABILITY"
                ),
                decision_result=decision,
                execution_result=execution,
                information_trace=information_trace,
                goal_to_decision_binding=goal_binding,
                policy_execution_binding=execution_binding,
            )

        realization = {
            "kind": "VERIFIED_POLICY_EXECUTION",
            "policy_id": selected_policy_id,
            "execution_result": execution,
        }
        goal_satisfaction = _authenticate_goal_satisfaction_binding(
            request.get("goal_satisfaction_binding"),
            goal=goal,
            selected_policy_id=selected_policy_id,
            realization=realization,
            repo_root=root,
        )
        if goal_satisfaction.get("pass") is not True:
            return _open(
                str(
                    goal_satisfaction.get("status")
                    or "OPEN__GOAL_SATISFACTION_BINDING_REQUIRED"
                ),
                task_id=task_id,
                goal=goal,
                raw_contract=raw_contract,
                next_required_edge="INDEPENDENT_ACTUAL_GOAL_SATISFACTION_VERIFICATION",
                decision_result=decision,
                execution_result=execution,
                realization=realization,
                goal_satisfaction_binding=goal_satisfaction,
                information_trace=information_trace,
                goal_to_decision_binding=goal_binding,
                policy_execution_binding=execution_binding,
            )

        return {
            "schema": SCHEMA,
            "status": "PASS__GOAL_BOUND_ADEQUATE_POLICY_EXECUTED_AND_ACCEPTANCE_VERIFIED",
            "pass": True,
            "task_id": task_id,
            "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
            "raw_task_contract_sha256": raw_contract["task_contract_sha256"],
            "raw_source_coverage_complete": raw_contract[
                "nonwhitespace_source_coverage_complete"
            ],
            "goal_to_decision_binding": goal_binding,
            "decision_result": decision,
            "selected_policy_id": selected_policy_id,
            "policy_execution_binding": execution_binding,
            "execution_result": execution,
            "realization": realization,
            "goal_satisfaction_binding": goal_satisfaction,
            "information_trace": information_trace,
            "minimum_information_rounds_used": len(information_trace),
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "verification_scope": (
                "AUTHENTICATED_GOAL_BINDING_PLUS_P3_ADEQUACY_PLUS_"
                "AUTHENTICATED_POLICY_EXECUTION_PLUS_VERIFIED_TARGET_EFFECTS"
            ),
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "incremental_spend_usd": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "semantic_acceptance_complete": False,
            "actual_goal_satisfaction_verified": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "incremental_spend_usd": 0,
        }
