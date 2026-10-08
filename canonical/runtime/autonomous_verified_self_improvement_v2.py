"""Autonomous verified self-improvement loop V2.

V2 wraps V1 with the missing bounded repair ratchet. A failed, non-effectful
learning episode may trigger zero-authority repair proposals. Those proposals are
never trusted directly: they are converted into a constrained next attempt and
must pass the ordinary V12 execution, semantic, episode and skill verification
boundaries before any durable learning or reuse is admitted.

Invariant:
  experience -> causal diagnosis -> repair proposal -> ordinary verification
  -> verified episode/skill -> Pareto admission -> durable reuse

No repair provider can change the task identity, initial facts, target effects,
or claim verification/promotion authority. Repeated identical repairs terminate.
Any failure after an effect may have occurred terminates fail-closed without a
blind replay.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import autonomous_verified_self_improvement_v1 as v1

SCHEMA = "PROJECT_BRAIN_AUTONOMOUS_VERIFIED_SELF_IMPROVEMENT_V2"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = v1.DEFAULT_STATE_PATH
load_state = v1.load_state
solver_v12 = v1.solver_v12

RepairProvider = Callable[[Mapping[str, Any], int], Mapping[str, Any] | None]

_ALLOWED_REPAIR_KEYS = {
    "problem",
    "proposal_packets",
    "resolved_semantics_bindings",
    "episode_verification_binding",
    "skill_verification_binding",
    "resume_binding",
    "known_absent_invalidators",
}
_IMMUTABLE_PROBLEM_FIELDS = ("task_id", "initial_facts", "target_effects")


class SelfImprovementV2Error(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    )


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _effect_may_have_occurred(result: Mapping[str, Any]) -> bool:
    solver = result.get("solver_output")
    if not isinstance(solver, Mapping):
        return False
    trace = solver.get("trace")
    if not isinstance(trace, Sequence) or isinstance(trace, (str, bytes)):
        return False
    return any(
        isinstance(row, Mapping) and bool(row.get("effect_outcome_sha256"))
        for row in trace
    )


def _diagnosis(result: Mapping[str, Any]) -> Mapping[str, Any]:
    learning = result.get("learning")
    if isinstance(learning, Mapping) and isinstance(learning.get("diagnosis"), Mapping):
        return learning["diagnosis"]
    solver = result.get("solver_output")
    if isinstance(solver, Mapping):
        return v1._diagnose_failure(solver)
    return {
        "status": result.get("status"),
        "reason": result.get("reason"),
        "repair_class": "LOCALIZE_CAUSAL_FAILURE_AND_GENERATE_MINIMAL_REPAIR",
        "failure_fingerprint": _sha(
            {"status": result.get("status"), "reason": result.get("reason")}
        ),
    }


def _normalized_tokens(value: Any, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise SelfImprovementV2Error(label + "_INVALID")
    out = []
    for item in value:
        token = " ".join(str(item or "").split())
        if not token:
            raise SelfImprovementV2Error(label + "_ITEM_INVALID")
        out.append(token)
    return sorted(out)


def _validate_problem_repair(
    original: Mapping[str, Any],
    repaired: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(repaired, Mapping):
        raise SelfImprovementV2Error("REPAIRED_PROBLEM_NOT_OBJECT")

    for field in _IMMUTABLE_PROBLEM_FIELDS:
        if field == "task_id":
            left = " ".join(str(original.get(field) or "").split())
            right = " ".join(str(repaired.get(field) or "").split())
        else:
            left = _normalized_tokens(original.get(field) or [], "ORIGINAL_" + field.upper())
            right = _normalized_tokens(repaired.get(field) or [], "REPAIRED_" + field.upper())
        if left != right:
            raise SelfImprovementV2Error("REPAIR_MAY_NOT_CHANGE_" + field.upper())

    # Repairs may add/replace candidate capability rows, but V12 remains the
    # execution/semantics authority. The repair channel itself grants nothing.
    caps = repaired.get("capabilities")
    if not isinstance(caps, list):
        raise SelfImprovementV2Error("REPAIRED_CAPABILITIES_NOT_LIST")
    ids = []
    for row in caps:
        if not isinstance(row, Mapping):
            raise SelfImprovementV2Error("REPAIRED_CAPABILITY_NOT_OBJECT")
        cid = " ".join(str(row.get("id") or "").split())
        if not cid or cid in ids:
            raise SelfImprovementV2Error("REPAIRED_CAPABILITY_ID_INVALID_OR_DUPLICATE")
        ids.append(cid)

    return deepcopy(dict(repaired))


def _apply_repair(
    original_problem: Mapping[str, Any],
    current_problem: Mapping[str, Any],
    repair: Mapping[str, Any],
    options: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(repair, Mapping):
        raise SelfImprovementV2Error("REPAIR_NOT_OBJECT")
    unknown = sorted(set(repair) - _ALLOWED_REPAIR_KEYS)
    if unknown:
        raise SelfImprovementV2Error("REPAIR_KEYS_FORBIDDEN:" + ",".join(unknown))

    next_problem = deepcopy(dict(current_problem))
    if "problem" in repair:
        next_problem = _validate_problem_repair(original_problem, repair["problem"])

    next_options = deepcopy(options)
    for key in _ALLOWED_REPAIR_KEYS - {"problem"}:
        if key in repair:
            next_options[key] = deepcopy(repair[key])

    return next_problem, next_options


def run_learning_episode(
    problem: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
    state_path: str | Path = DEFAULT_STATE_PATH,
    proposal_packets: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    resolved_semantics_bindings: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    effect_root: str | None = None,
    episode_id: str = "episode",
    scope_id: str = "scope",
    episode_verification_binding: Mapping[str, Any] | None = None,
    skill_verification_binding: Mapping[str, Any] | None = None,
    resume_binding: Mapping[str, Any] | None = None,
    known_absent_invalidators: Sequence[str] = (),
    proposal_provider=None,
    capability_expander=None,
    proposal_provider_id: str = "HOST_GENERAL_COGNITION_SUBSTRATE",
    proposal_provider_max_candidates: int = 4,
    capability_expander_id: str = "HOST_CAPABILITY_EXPANDER",
    max_capability_expansions: int = 4,
    repair_provider: RepairProvider | None = None,
    max_repair_rounds: int = 3,
) -> dict[str, Any]:
    """Run V1 plus bounded automatic causal repair.

    The repair provider is a proposal source only. Every repair must survive the
    existing V12 verification stack before V1 can persist it as learning.
    """
    if not isinstance(problem, Mapping):
        raise SelfImprovementV2Error("PROBLEM_NOT_OBJECT")
    if not isinstance(max_repair_rounds, int) or isinstance(max_repair_rounds, bool):
        raise SelfImprovementV2Error("MAX_REPAIR_ROUNDS_INVALID")
    if max_repair_rounds < 0 or max_repair_rounds > 16:
        raise SelfImprovementV2Error("MAX_REPAIR_ROUNDS_OUT_OF_RANGE")
    if repair_provider is not None and not callable(repair_provider):
        raise SelfImprovementV2Error("REPAIR_PROVIDER_NOT_CALLABLE")

    original_problem = deepcopy(dict(problem))
    current_problem = deepcopy(dict(problem))
    options: dict[str, Any] = {
        "proposal_packets": proposal_packets,
        "resolved_semantics_bindings": resolved_semantics_bindings,
        "episode_verification_binding": episode_verification_binding,
        "skill_verification_binding": skill_verification_binding,
        "resume_binding": resume_binding,
        "known_absent_invalidators": list(known_absent_invalidators),
    }
    repair_fingerprints: set[str] = set()
    ratchet_trace: list[dict[str, Any]] = []

    for round_index in range(max_repair_rounds + 1):
        result = v1.run_learning_episode(
            current_problem,
            repo_root=repo_root,
            state_path=state_path,
            proposal_packets=options.get("proposal_packets"),
            resolved_semantics_bindings=options.get("resolved_semantics_bindings"),
            effect_root=effect_root,
            episode_id=episode_id,
            scope_id=scope_id,
            episode_verification_binding=options.get("episode_verification_binding"),
            skill_verification_binding=options.get("skill_verification_binding"),
            resume_binding=options.get("resume_binding"),
            known_absent_invalidators=options.get("known_absent_invalidators", ()),
            proposal_provider=proposal_provider,
            capability_expander=capability_expander,
            proposal_provider_id=proposal_provider_id,
            proposal_provider_max_candidates=proposal_provider_max_candidates,
            capability_expander_id=capability_expander_id,
            max_capability_expansions=max_capability_expansions,
        )

        entry = {
            "round": round_index,
            "status": result.get("status"),
            "pass": result.get("pass") is True,
            "problem_sha256": _sha(current_problem),
            "effect_may_have_occurred": _effect_may_have_occurred(result),
        }
        if result.get("pass") is True:
            ratchet_trace.append(entry)
            out = deepcopy(dict(result))
            out["schema"] = SCHEMA
            out["ratchet_status"] = "COMPOUNDING_LOOP_SUCCESS"
            out["repair_rounds_used"] = round_index
            out["ratchet_trace"] = ratchet_trace
            out["self_certification_used"] = False
            return out

        diagnosis = _diagnosis(result)
        entry["diagnosis"] = deepcopy(dict(diagnosis))
        ratchet_trace.append(entry)

        if entry["effect_may_have_occurred"]:
            out = deepcopy(dict(result))
            out["schema"] = SCHEMA
            out["ratchet_status"] = "FAIL_CLOSED__EFFECTFUL_FAILURE__NO_AUTOMATIC_REPLAY"
            out["repair_rounds_used"] = round_index
            out["ratchet_trace"] = ratchet_trace
            out["self_certification_used"] = False
            return out

        if round_index >= max_repair_rounds:
            out = deepcopy(dict(result))
            out["schema"] = SCHEMA
            out["ratchet_status"] = "FAIL_CLOSED__REPAIR_BUDGET_EXHAUSTED"
            out["repair_rounds_used"] = round_index
            out["ratchet_trace"] = ratchet_trace
            out["self_certification_used"] = False
            return out

        if repair_provider is None:
            out = deepcopy(dict(result))
            out["schema"] = SCHEMA
            out["ratchet_status"] = "BLOCKED__NO_REPAIR_PROVIDER"
            out["repair_rounds_used"] = round_index
            out["ratchet_trace"] = ratchet_trace
            out["self_certification_used"] = False
            return out

        request = {
            "schema": "PROJECT_BRAIN_SELF_IMPROVEMENT_REPAIR_REQUEST_V2",
            "round": round_index,
            "task_id": current_problem.get("task_id"),
            "original_problem_sha256": _sha(original_problem),
            "current_problem_sha256": _sha(current_problem),
            "diagnosis": deepcopy(dict(diagnosis)),
            "allowed_repair_keys": sorted(_ALLOWED_REPAIR_KEYS),
            "immutable_problem_fields": list(_IMMUTABLE_PROBLEM_FIELDS),
            "repair_authority": False,
            "verification_authority": False,
            "promotion_authority": False,
        }

        repair = repair_provider(request, round_index)
        if repair is None:
            out = deepcopy(dict(result))
            out["schema"] = SCHEMA
            out["ratchet_status"] = "BLOCKED__REPAIR_PROVIDER_RETURNED_NONE"
            out["repair_rounds_used"] = round_index
            out["ratchet_trace"] = ratchet_trace
            out["self_certification_used"] = False
            return out

        fp = _sha(repair)
        if fp in repair_fingerprints:
            out = deepcopy(dict(result))
            out["schema"] = SCHEMA
            out["ratchet_status"] = "FAIL_CLOSED__DUPLICATE_REPAIR_LOOP"
            out["repair_rounds_used"] = round_index
            out["ratchet_trace"] = ratchet_trace
            out["duplicate_repair_sha256"] = fp
            out["self_certification_used"] = False
            return out
        repair_fingerprints.add(fp)

        try:
            current_problem, options = _apply_repair(
                original_problem,
                current_problem,
                repair,
                options,
            )
        except Exception as exc:
            out = deepcopy(dict(result))
            out["schema"] = SCHEMA
            out["ratchet_status"] = "FAIL_CLOSED__REPAIR_REJECTED"
            out["repair_rounds_used"] = round_index
            out["ratchet_trace"] = ratchet_trace
            out["repair_rejection_reason"] = type(exc).__name__ + ":" + str(exc)
            out["self_certification_used"] = False
            return out

        ratchet_trace[-1]["repair_sha256"] = fp
        ratchet_trace[-1]["repair_accepted_as_candidate_only"] = True

    raise AssertionError("UNREACHABLE")
