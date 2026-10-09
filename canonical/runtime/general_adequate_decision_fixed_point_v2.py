"""R2 adaptive fixed-point decision controller V2.

This layer turns every unresolved edge from the verified V1 adequate-decision
controller into a typed acquisition request. A general cognition proposal
provider may propose request repairs, but every repaired request is rerun through
V1 and therefore gains no semantic, execution, acceptance, or terminal authority
from the provider itself.

The loop is progress-bounded and cycle-detecting. It does not claim open-world
semantic completeness; it makes unknown coverage executable instead of a manual
dead end while preserving fail-closed truth.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from canonical.runtime.general_adequate_decision_controller_v1 import (
    run as run_controller,
)
from canonical.runtime import r2_direct_end_to_end_adequacy_v19 as direct_adequacy
from canonical.runtime.r2_existing_policy_adequacy_repair_v1 import (
    repair as repair_existing_adequacy,
)
from canonical.runtime.r2_basis_discriminator_repair_v1 import (
    repair as repair_basis_discriminator,
)

SCHEMA = "PROJECT_BRAIN_GENERAL_ADEQUATE_DECISION_FIXED_POINT_V2"
MAX_FIXED_POINT_STEPS = 16
MAX_PROVIDER_CANDIDATES = 4

MUTABLE_REQUEST_FIELDS = frozenset(
    {
        "decision_payload",
        "goal_to_decision_binding",
        "partial_goal_to_decision_binding",
        "execution_problem",
        "policy_execution_binding",
        "goal_satisfaction_binding",
        "policy_cover_observation_bindings",
        "max_policy_cover_observations",
        "max_information_rounds",
        "episode_id",
        "scope_id",
    }
)
IMMUTABLE_REQUEST_FIELDS = frozenset({"task_id", "goal"})


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return "sha256:" + sha256(_canon(value).encode("utf-8")).hexdigest()



def _direct_semantic_open_hint(
    direct_preflight: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Project an open direct-route state into non-authoritative resolver metadata."""
    if direct_preflight.get("direct_route_semantic_open") is not True:
        return None
    return {
        "schema": "PROJECT_BRAIN_R2_DIRECT_SEMANTIC_OPEN_HINT_V1",
        "route_id": direct_preflight.get("route_id"),
        "status": direct_preflight.get("status"),
        "effect_status": direct_preflight.get("effect_status"),
        "minimum_discriminator_slots": deepcopy(
            direct_preflight.get("minimum_discriminator_slots") or []
        ),
        "possible_outcomes": deepcopy(
            direct_preflight.get("possible_outcomes") or []
        ),
        "world_count": direct_preflight.get("world_count"),
        "blocking_residual_document_ids": deepcopy(
            direct_preflight.get("blocking_residual_document_ids") or []
        ),
        "next_proof_obligations": deepcopy(
            direct_preflight.get("next_proof_obligations") or []
        ),
        "blocking_document_ids": deepcopy(
            direct_preflight.get("blocking_document_ids") or []
        ),
        "blocking_unknown_regions": deepcopy(
            direct_preflight.get("blocking_unknown_regions") or []
        ),
        "query_relative_source_completeness_proved": direct_preflight.get(
            "query_relative_source_completeness_proved"
        ),
        "open_lattice_atoms": deepcopy(
            direct_preflight.get("open_lattice_atoms") or []
        ),
        "query_relative_effect_semantics_finite": direct_preflight.get(
            "query_relative_effect_semantics_finite"
        ),
        "semantic_truth_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
    }



def _next_meta_action(base: Mapping[str, Any]) -> dict[str, Any]:
    """Map every verified/open/fail-closed controller state to one typed next move.

    This is a control-level totality law only. It does not invent semantic truth,
    policy adequacy, execution success, or goal satisfaction.
    """
    status = str(base.get("status") or "")
    edge = str(
        base.get("next_required_edge")
        or base.get("next_required_effect")
        or status
        or "UNSPECIFIED_OPEN_EDGE"
    )

    if base.get("pass") is True:
        kind = "RETURN_VERIFIED_GOAL_SATISFACTION"
    elif status.startswith("FAIL_CLOSED"):
        kind = "ABSTAIN_FAIL_CLOSED"
    elif isinstance(base.get("next_information_request"), Mapping):
        kind = "ACQUIRE_MINIMUM_DECISION_INFORMATION"
    elif isinstance(base.get("next_observation_request"), Mapping):
        kind = "ACQUIRE_MINIMUM_DECISION_INFORMATION"
    elif isinstance(base.get("next_policy_request"), Mapping):
        kind = "REPAIR_OR_PROVE_POLICY_ADEQUACY"
    elif "GOAL_SATISFACTION" in edge or "ACCEPTANCE" in edge:
        kind = "VERIFY_ACTUAL_GOAL_SATISFACTION"
    elif "EXECUTION" in edge or "REALIZATION" in edge:
        kind = "BIND_OR_EXECUTE_SELECTED_POLICY"
    elif "ADEQUACY" in edge or "POLICY" in edge:
        kind = "REPAIR_OR_PROVE_POLICY_ADEQUACY"
    elif "INFORMATION" in edge or "TRUTH" in edge or "OBSERVATION" in edge:
        kind = "ACQUIRE_MINIMUM_DECISION_INFORMATION"
    else:
        kind = "RESOLVE_EXACT_OPEN_EDGE"

    return {
        "kind": kind,
        "source_status": status or None,
        "required_edge": edge,
        "routing_total": True,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
    }

def _decorate(
    base: Mapping[str, Any],
    *,
    fixed_point_status: str,
    steps: int,
    trace: list[dict[str, Any]],
) -> dict[str, Any]:
    out = deepcopy(dict(base))
    out["r2_fixed_point_schema"] = SCHEMA
    out["r2_fixed_point_status"] = fixed_point_status
    out["r2_fixed_point_steps"] = steps
    out["r2_fixed_point_trace"] = deepcopy(trace)
    out["r2_fixed_point_closure"] = out.get("pass") is True
    out["r2_edge_resolver_authority"] = False
    out["r2_edge_resolver_semantic_truth_authority"] = False
    out["r2_edge_resolver_execution_authority"] = False
    out["r2_edge_resolver_acceptance_authority"] = False
    out["r2_next_meta_action"] = _next_meta_action(out)
    out["r2_control_policy_total"] = True
    out.setdefault("terminal_authority", False)
    out.setdefault("terminal_credit_delta", 0)
    out.setdefault("incremental_spend_usd", 0)
    return out


def _fail(reason: str, *, trace: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "r2_fixed_point_status": "FAIL_CLOSED",
        "r2_fixed_point_steps": len(trace or []),
        "r2_fixed_point_trace": deepcopy(trace or []),
        "r2_fixed_point_closure": False,
        "semantic_acceptance_complete": False,
        "actual_goal_satisfaction_verified": False,
        "r2_edge_resolver_authority": False,
        "r2_edge_resolver_semantic_truth_authority": False,
        "r2_edge_resolver_execution_authority": False,
        "r2_edge_resolver_acceptance_authority": False,
        "r2_next_meta_action": {
            "kind": "ABSTAIN_FAIL_CLOSED",
            "source_status": "FAIL_CLOSED",
            "required_edge": "FAIL_CLOSED",
            "routing_total": True,
            "semantic_truth_authority": False,
            "policy_adequacy_authority": False,
            "execution_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
        },
        "r2_control_policy_total": True,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _normalize_provider_candidate(
    generated: Mapping[str, Any],
) -> tuple[dict[str, Any], str | None]:
    if (
        isinstance(generated.get("proposal"), Mapping)
        and isinstance(generated.get("source_id"), str)
    ):
        return deepcopy(dict(generated["proposal"])), str(generated["source_id"])
    return deepcopy(dict(generated)), None


def _edge_request(
    current: Mapping[str, Any],
    unresolved: Mapping[str, Any],
    *,
    step: int,
    direct_preflight_hint: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema": "PROJECT_BRAIN_R2_UNRESOLVED_EDGE_ACQUISITION_REQUEST_V1",
        "proposal_kind": "R2_REQUEST_REPAIR",
        "step": step,
        "task_id": current.get("task_id"),
        "goal": current.get("goal"),
        "goal_sha256": unresolved.get("goal_sha256"),
        "current_request_sha256": _digest(current),
        "unresolved_status": unresolved.get("status"),
        "next_required_edge": (
            unresolved.get("next_required_edge")
            or unresolved.get("next_required_effect")
            or unresolved.get("status")
        ),
        "next_information_request": deepcopy(
            unresolved.get("next_information_request")
        ),
        "next_observation_request": deepcopy(
            unresolved.get("next_observation_request")
        ),
        "next_policy_request": deepcopy(
            unresolved.get("next_policy_request")
        ),
        "unresolved_output": deepcopy(dict(unresolved)),
        "direct_preflight_hint": (
            deepcopy(dict(direct_preflight_hint))
            if isinstance(direct_preflight_hint, Mapping)
            else None
        ),
        "allowed_request_patch_fields": sorted(MUTABLE_REQUEST_FIELDS),
        "immutable_request_fields": sorted(IMMUTABLE_REQUEST_FIELDS),
        "required_response_shape": {
            "request_patch": "mapping containing only allowed_request_patch_fields"
        },
        "provider_is_semantic_truth_authority": False,
        "provider_is_execution_authority": False,
        "provider_is_acceptance_authority": False,
        "provider_is_terminal_authority": False,
    }


def _merge_candidate(
    current: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    patch = candidate.get("request_patch")
    if not isinstance(patch, Mapping):
        return None, "REQUEST_PATCH_REQUIRED"
    extra = set(patch) - MUTABLE_REQUEST_FIELDS
    if extra:
        return None, "UNMODELED_REQUEST_PATCH_FIELDS:" + ",".join(sorted(extra))
    if any(key in patch for key in IMMUTABLE_REQUEST_FIELDS):
        return None, "IMMUTABLE_REQUEST_FIELD_PATCH_FORBIDDEN"

    merged = deepcopy(dict(current))
    for key, value in patch.items():
        if key == "policy_cover_observation_bindings":
            if not isinstance(value, Mapping):
                return None, "POLICY_COVER_OBSERVATION_BINDINGS_PATCH_NOT_OBJECT"
            prior_bindings = merged.get(key, {})
            if not isinstance(prior_bindings, Mapping):
                return None, "EXISTING_POLICY_COVER_OBSERVATION_BINDINGS_NOT_OBJECT"
            combined = deepcopy(dict(prior_bindings))
            for discriminator_id, binding in value.items():
                if not isinstance(discriminator_id, str) or not discriminator_id:
                    return None, "POLICY_COVER_OBSERVATION_DISCRIMINATOR_ID_INVALID"
                if discriminator_id in combined and combined[discriminator_id] != binding:
                    return None, (
                        "POLICY_COVER_OBSERVATION_BINDING_MUTATION_FORBIDDEN:"
                        + discriminator_id
                    )
                combined[discriminator_id] = deepcopy(binding)
            merged[key] = combined
            continue
        merged[key] = deepcopy(value)

    if merged.get("task_id") != current.get("task_id"):
        return None, "TASK_ID_MUTATION_FORBIDDEN"
    if merged.get("goal") != current.get("goal"):
        return None, "GOAL_MUTATION_FORBIDDEN"
    return merged, None


def run(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
    information_provider: Callable[
        [Mapping[str, Any], int], Mapping[str, Any] | None
    ]
    | None = None,
    proposal_provider: Callable[
        [Mapping[str, Any], int, tuple[Mapping[str, Any], ...]],
        Mapping[str, Any] | None,
    ]
    | None = None,
    capability_expander: Callable[..., Mapping[str, Any] | None] | None = None,
    execution_provider: Callable[..., Mapping[str, Any]] | None = None,
    max_fixed_point_steps: int = MAX_FIXED_POINT_STEPS,
    provider_max_candidates: int = MAX_PROVIDER_CANDIDATES,
) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        return _fail("REQUEST_NOT_OBJECT")
    if (
        isinstance(max_fixed_point_steps, bool)
        or not isinstance(max_fixed_point_steps, int)
        or not 0 <= max_fixed_point_steps <= MAX_FIXED_POINT_STEPS
    ):
        return _fail("MAX_FIXED_POINT_STEPS_INVALID")
    if (
        isinstance(provider_max_candidates, bool)
        or not isinstance(provider_max_candidates, int)
        or not 1 <= provider_max_candidates <= 8
    ):
        return _fail("PROVIDER_MAX_CANDIDATES_INVALID")

    current = deepcopy(dict(request))
    seen = {_digest(current)}
    trace: list[dict[str, Any]] = []
    prior_candidates: list[dict[str, Any]] = []

    direct_preflight = direct_adequacy.preflight(current, repo_root=repo_root)
    direct_semantic_hint = _direct_semantic_open_hint(direct_preflight)
    if direct_preflight.get("matched") is True:
        direct_result = direct_adequacy.run(current, repo_root=repo_root)
        trace.append(
            {
                "step": 0,
                "kind": "DIRECT_END_TO_END_ADEQUACY",
                "route_id": direct_preflight.get("route_id"),
                "status": direct_result.get("status"),
                "pass": direct_result.get("pass") is True,
                "execution_attempted": direct_result.get("execution_attempted") is True,
            }
        )
        return _decorate(
            direct_result,
            fixed_point_status=(
                "PASS__R2_DIRECT_END_TO_END_ADEQUACY_CLOSED"
                if direct_result.get("pass") is True
                else "OPEN__R2_MATCHED_DIRECT_ROUTE_DID_NOT_VERIFY"
            ),
            steps=0,
            trace=trace,
        )

    for step in range(max_fixed_point_steps + 1):
        # Any accepted fixed-point repair mutates `current`. Re-run the direct
        # adequacy surface on that repaired state before invoking the semantic
        # controller again. Otherwise a newly closed direct route can remain
        # stranded behind a stale pre-repair semantic-open hint.
        if step > 0:
            direct_preflight = direct_adequacy.preflight(
                current, repo_root=repo_root
            )
            direct_semantic_hint = _direct_semantic_open_hint(direct_preflight)
            if direct_preflight.get("matched") is True:
                direct_result = direct_adequacy.run(current, repo_root=repo_root)
                trace.append(
                    {
                        "step": step,
                        "kind": "DIRECT_END_TO_END_ADEQUACY_REENTRY",
                        "request_sha256": _digest(current),
                        "route_id": direct_preflight.get("route_id"),
                        "status": direct_result.get("status"),
                        "pass": direct_result.get("pass") is True,
                        "execution_attempted": (
                            direct_result.get("execution_attempted") is True
                        ),
                    }
                )
                return _decorate(
                    direct_result,
                    fixed_point_status=(
                        "PASS__R2_DIRECT_END_TO_END_ADEQUACY_CLOSED_AFTER_REPAIR"
                        if direct_result.get("pass") is True
                        else "OPEN__R2_REPAIRED_MATCHED_DIRECT_ROUTE_DID_NOT_VERIFY"
                    ),
                    steps=step,
                    trace=trace,
                )

        result = run_controller(
            current,
            repo_root=repo_root,
            information_provider=information_provider,
            proposal_provider=proposal_provider,
            capability_expander=capability_expander,
            execution_provider=execution_provider,
        )
        if not isinstance(result, Mapping):
            return _fail("V1_CONTROLLER_RESULT_NOT_OBJECT", trace=trace)

        trace.append(
            {
                "step": step,
                "kind": "V1_CONTROLLER",
                "request_sha256": _digest(current),
                "status": result.get("status"),
                "pass": result.get("pass") is True,
                "next_required_edge": result.get("next_required_edge"),
                "direct_preflight_hint": deepcopy(direct_semantic_hint),
            }
        )
        if result.get("pass") is True:
            return _decorate(
                result,
                fixed_point_status="PASS__R2_ADAPTIVE_FIXED_POINT_CLOSED",
                steps=step,
                trace=trace,
            )

        if step >= max_fixed_point_steps:
            return _decorate(
                result,
                fixed_point_status="OPEN__R2_FIXED_POINT_STEP_BOUND_EXHAUSTED",
                steps=step,
                trace=trace,
            )

        policy_request = result.get("next_policy_request")
        if isinstance(policy_request, Mapping):
            automatic = repair_existing_adequacy(
                current,
                policy_request,
                repo_root=repo_root,
            )
            trace[-1]["automatic_existing_adequacy_repair"] = {
                "status": automatic.get("status"),
                "pass": automatic.get("pass") is True,
                "added_policy_ids": deepcopy(automatic.get("added_policy_ids", [])),
                "repair_authority": False,
            }
            if automatic.get("status") == "FAIL_CLOSED":
                return _fail(
                    "BUILTIN_EXISTING_ADEQUACY_REPAIR_FAIL_CLOSED:"
                    + str(automatic.get("reason") or "UNKNOWN"),
                    trace=trace,
                )
            if automatic.get("pass") is True:
                candidate = {"request_patch": automatic.get("request_patch")}
                merged, error = _merge_candidate(current, candidate)
                if error is not None or merged is None:
                    return _fail(
                        "BUILTIN_EXISTING_ADEQUACY_REPAIR_PATCH_INVALID:"
                        + str(error),
                        trace=trace,
                    )
                candidate_digest = _digest(merged)
                if candidate_digest == _digest(current) or candidate_digest in seen:
                    return _fail(
                        "BUILTIN_EXISTING_ADEQUACY_REPAIR_NO_PROGRESS",
                        trace=trace,
                    )
                trace[-1]["automatic_existing_adequacy_repair"][
                    "candidate_request_sha256"
                ] = candidate_digest
                trace[-1]["automatic_existing_adequacy_repair"][
                    "downstream_reverification_required"
                ] = True
                current = merged
                seen.add(candidate_digest)
                continue

            basis_repair = repair_basis_discriminator(
                current,
                policy_request,
            )
            trace[-1]["automatic_basis_discriminator_repair"] = {
                "status": basis_repair.get("status"),
                "pass": basis_repair.get("pass") is True,
                "added_discriminator_ids": deepcopy(
                    basis_repair.get("added_discriminator_ids", [])
                ),
                "added_basis_atoms": deepcopy(
                    basis_repair.get("added_basis_atoms", [])
                ),
                "repair_authority": False,
                "semantic_truth_authority": False,
            }
            if basis_repair.get("status") == "FAIL_CLOSED":
                return _fail(
                    "BUILTIN_BASIS_DISCRIMINATOR_REPAIR_FAIL_CLOSED:"
                    + str(basis_repair.get("reason") or "UNKNOWN"),
                    trace=trace,
                )
            if basis_repair.get("pass") is True:
                candidate = {"request_patch": basis_repair.get("request_patch")}
                merged, error = _merge_candidate(current, candidate)
                if error is not None or merged is None:
                    return _fail(
                        "BUILTIN_BASIS_DISCRIMINATOR_REPAIR_PATCH_INVALID:"
                        + str(error),
                        trace=trace,
                    )
                candidate_digest = _digest(merged)
                if candidate_digest == _digest(current) or candidate_digest in seen:
                    return _fail(
                        "BUILTIN_BASIS_DISCRIMINATOR_REPAIR_NO_PROGRESS",
                        trace=trace,
                    )
                trace[-1]["automatic_basis_discriminator_repair"][
                    "candidate_request_sha256"
                ] = candidate_digest
                trace[-1]["automatic_basis_discriminator_repair"][
                    "downstream_cegar_reverification_required"
                ] = True
                current = merged
                seen.add(candidate_digest)
                continue

        # After deterministic reuse/repair is exhausted, an explicit policy
        # adequacy gap may require a genuinely new verifiable capability. Give
        # the existing capability expander a first-class escape path here. The
        # expander has zero authority: it can only propose a normal request_patch,
        # and the complete patched request must be re-run through the V1 authority
        # kernel before it can influence a policy choice.
        if isinstance(policy_request, Mapping) and capability_expander is not None:
            expansion_packet = {
                "schema": (
                    "PROJECT_BRAIN_R2_POLICY_ADEQUACY_CAPABILITY_EXPANSION_REQUEST_V1"
                ),
                "proposal_kind": "R2_POLICY_ADEQUACY_CAPABILITY_EXPANSION",
                "step": step,
                "task_id": current.get("task_id"),
                "goal": current.get("goal"),
                "goal_sha256": result.get("goal_sha256"),
                "current_request_sha256": _digest(current),
                "unresolved_status": result.get("status"),
                "next_required_edge": result.get("next_required_edge"),
                "next_policy_request": deepcopy(dict(policy_request)),
                "allowed_request_patch_fields": sorted(MUTABLE_REQUEST_FIELDS),
                "immutable_request_fields": sorted(IMMUTABLE_REQUEST_FIELDS),
                "required_response_shape": {
                    "request_patch": (
                        "mapping containing only allowed_request_patch_fields"
                    )
                },
                "expansion_authority": False,
                "semantic_truth_authority": False,
                "policy_adequacy_authority": False,
                "execution_authority": False,
                "acceptance_authority": False,
                "terminal_authority": False,
            }
            expansion_record: dict[str, Any] = {
                "request_sha256": _digest(expansion_packet),
                "expansion_authority": False,
                "semantic_truth_authority": False,
                "policy_adequacy_authority": False,
                "terminal_authority": False,
            }
            try:
                generated = capability_expander(
                    expansion_packet,
                    step,
                    deepcopy(current),
                )
            except Exception as exc:
                expansion_record["status"] = "EXPANDER_EXCEPTION"
                expansion_record["reason"] = type(exc).__name__ + ":" + str(exc)
            else:
                if generated is None:
                    expansion_record["status"] = "NO_EXPANSION"
                elif not isinstance(generated, Mapping):
                    expansion_record["status"] = "CANDIDATE_REJECTED"
                    expansion_record["reason"] = "EXPANDER_RESULT_NOT_OBJECT"
                else:
                    candidate, source_id = _normalize_provider_candidate(generated)
                    merged, error = _merge_candidate(current, candidate)
                    if error is not None or merged is None:
                        expansion_record["status"] = "CANDIDATE_REJECTED"
                        expansion_record["source_id"] = source_id
                        expansion_record["reason"] = error
                    else:
                        candidate_digest = _digest(merged)
                        if candidate_digest == _digest(current):
                            expansion_record["status"] = "CANDIDATE_REJECTED"
                            expansion_record["source_id"] = source_id
                            expansion_record["reason"] = "NO_PROGRESS"
                        elif candidate_digest in seen:
                            expansion_record["status"] = "CANDIDATE_REJECTED"
                            expansion_record["source_id"] = source_id
                            expansion_record["reason"] = "FIXED_POINT_CYCLE_DETECTED"
                        else:
                            expansion_record["status"] = (
                                "PROGRESSIVE_POLICY_ADEQUACY_EXPANSION_"
                                "ACCEPTED_FOR_REVERIFICATION"
                            )
                            expansion_record["source_id"] = source_id
                            expansion_record["candidate_request_sha256"] = (
                                candidate_digest
                            )
                            expansion_record[
                                "downstream_reverification_required"
                            ] = True
                            trace[-1][
                                "policy_adequacy_capability_expansion"
                            ] = expansion_record
                            current = merged
                            seen.add(candidate_digest)
                            continue

            trace[-1]["policy_adequacy_capability_expansion"] = expansion_record

        if proposal_provider is None:
            return _decorate(
                result,
                fixed_point_status="OPEN__R2_EDGE_RESOLVER_UNAVAILABLE",
                steps=step,
                trace=trace,
            )

        packet = _edge_request(
            current,
            result,
            step=step,
            direct_preflight_hint=direct_semantic_hint,
        )
        attempts: list[dict[str, Any]] = []
        progressive: dict[str, Any] | None = None
        progressive_digest: str | None = None

        for provider_index in range(provider_max_candidates):
            try:
                generated = proposal_provider(
                    packet,
                    provider_index,
                    tuple(prior_candidates),
                )
            except Exception as exc:
                attempts.append(
                    {
                        "index": provider_index,
                        "status": "PROVIDER_EXCEPTION",
                        "reason": type(exc).__name__ + ":" + str(exc),
                    }
                )
                continue

            if generated is None:
                attempts.append(
                    {"index": provider_index, "status": "NO_CANDIDATE"}
                )
                continue
            if not isinstance(generated, Mapping):
                attempts.append(
                    {
                        "index": provider_index,
                        "status": "CANDIDATE_REJECTED",
                        "reason": "PROVIDER_RESULT_NOT_OBJECT",
                    }
                )
                continue

            candidate, source_id = _normalize_provider_candidate(generated)
            prior_candidates.append(deepcopy(candidate))
            merged, error = _merge_candidate(current, candidate)
            if error is not None or merged is None:
                attempts.append(
                    {
                        "index": provider_index,
                        "status": "CANDIDATE_REJECTED",
                        "source_id": source_id,
                        "reason": error,
                    }
                )
                continue

            candidate_digest = _digest(merged)
            if candidate_digest == _digest(current):
                attempts.append(
                    {
                        "index": provider_index,
                        "status": "CANDIDATE_REJECTED",
                        "source_id": source_id,
                        "reason": "NO_PROGRESS",
                    }
                )
                continue
            if candidate_digest in seen:
                attempts.append(
                    {
                        "index": provider_index,
                        "status": "CANDIDATE_REJECTED",
                        "source_id": source_id,
                        "reason": "FIXED_POINT_CYCLE_DETECTED",
                    }
                )
                continue

            progressive = merged
            progressive_digest = candidate_digest
            attempts.append(
                {
                    "index": provider_index,
                    "status": "PROGRESSIVE_REQUEST_PATCH_ACCEPTED_FOR_REVERIFICATION",
                    "source_id": source_id,
                    "candidate_request_sha256": candidate_digest,
                    "provider_authority": False,
                }
            )
            break

        trace[-1]["resolver_request_sha256"] = _digest(packet)
        trace[-1]["resolver_attempts"] = attempts

        if progressive is None or progressive_digest is None:
            return _decorate(
                result,
                fixed_point_status="OPEN__R2_EDGE_RESOLVER_NO_PROGRESSIVE_CANDIDATE",
                steps=step,
                trace=trace,
            )

        current = progressive
        seen.add(progressive_digest)

    return _fail("UNREACHABLE_FIXED_POINT_LOOP_EXIT", trace=trace)
