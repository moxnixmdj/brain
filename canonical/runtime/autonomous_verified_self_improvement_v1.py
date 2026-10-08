"""Autonomous verified self-improvement loop V1.

This module closes the integration seam between the Brain's already-verified
adaptive solver, authenticated episode learning, executable-skill induction,
independent skill verification, and capability-first Pareto replacement.

It deliberately does not let the Brain self-certify. Experience may be stored as
learning evidence only after the existing independent verification authenticators
accept it. A learned skill may become reusable only after the existing skill
verification path marks it verified and reuse-authorized.

The durable state is a compact registry of:
- independently verified episodes;
- independently verified reusable skills;
- active per-effect Pareto frontiers;
- deduplicated failure diagnoses.

The loop is therefore:
  experience -> diagnosis -> verified episode -> skill induction ->
  independent verification -> compression -> Pareto admission -> permanent reuse

Independent verification is an authority boundary, not a manual learning step.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.capability_first_scheduler_v1 import update_pareto_frontier
from canonical.runtime.executable_skill_program_v7 import (
    ExecutableSkillProgramError,
    induce_candidate,
)
from canonical.runtime.executable_skill_verification_authenticator_v1 import (
    authenticate_and_verify as authenticate_skill_verification,
    reauthenticate_record as reauthenticate_skill_record,
)
from canonical.runtime.universal_solver_episode_verification_authenticator_v1 import (
    authenticate as authenticate_episode_verification,
    reauthenticate_record as reauthenticate_episode_record,
)
from canonical.runtime import universal_verified_adaptive_solver_v12 as solver_v12

SCHEMA = "PROJECT_BRAIN_AUTONOMOUS_VERIFIED_SELF_IMPROVEMENT_V1"
VERIFIED_SUPERSET_SCOPE_PREDICATE = "STRUCTURAL_MATCH_V1"
STATE_SCHEMA = "PROJECT_BRAIN_SELF_IMPROVEMENT_STATE_V1"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = ROOT / "canonical/runtime/SELF_IMPROVEMENT_STATE_V1.json"
SENSITIVE_RETRY_KEY_PARTS = (
    "password", "passwd", "secret", "api_key", "apikey", "authorization",
    "cookie", "credential", "access_token", "refresh_token", "private_key",
)


class SelfImprovementError(ValueError):
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


def _s(value: Any) -> str:
    return " ".join(str(value or "").split())


def _items(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return sorted({_s(x) for x in value if _s(x)})


def _validate_retry_value(value: Any, *, path: str = "retry", depth: int = 0) -> None:
    if depth > 32:
        raise SelfImprovementError("RETRY_CONTEXT_TOO_DEEP:" + path)
    if value is None or isinstance(value, (bool, int, float, str)):
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise SelfImprovementError("RETRY_CONTEXT_KEY_NOT_STRING:" + path)
            lowered = key.lower().replace("-", "_")
            if any(part in lowered for part in SENSITIVE_RETRY_KEY_PARTS):
                raise SelfImprovementError("RETRY_CONTEXT_SENSITIVE_KEY_REJECTED:" + path + "." + key)
            _validate_retry_value(item, path=path + "." + key, depth=depth + 1)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for i, item in enumerate(value):
            _validate_retry_value(item, path=f"{path}[{i}]", depth=depth + 1)
        return
    raise SelfImprovementError("RETRY_CONTEXT_VALUE_TYPE_INVALID:" + path + ":" + type(value).__name__)


def _make_retry_capsule(context: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(context, Mapping):
        raise SelfImprovementError("RETRY_CONTEXT_NOT_OBJECT")
    _validate_retry_value(context)
    copied = deepcopy(dict(context))
    raw = _canon(copied).encode("utf-8")
    if len(raw) > 1_000_000:
        raise SelfImprovementError("RETRY_CONTEXT_TOO_LARGE")
    digest = _sha(copied)
    return {
        "schema": "PROJECT_BRAIN_FAILURE_RETRY_CAPSULE_V1",
        "sha256": digest,
        "context": copied,
        "secret_scan": "PASS",
        "replay_authorized": True,
        "resolved": False,
    }


def _make_success_proof_capsule(out: Mapping[str, Any]) -> dict[str, Any] | None:
    """Retain only bounded execution-proof metadata needed for later read-only verification."""
    if not isinstance(out, Mapping) or out.get("pass") is not True:
        return None
    checkpoint = out.get("controller_checkpoint")
    selected_plan = out.get("selected_plan")
    if not isinstance(checkpoint, Mapping):
        return None
    if not isinstance(selected_plan, Sequence) or isinstance(selected_plan, (str, bytes)):
        return None
    checkpoint_path = _s(checkpoint.get("path"))
    plan_sha256 = _s(checkpoint.get("plan_sha256"))
    if not checkpoint_path or len(plan_sha256) != 64:
        return None

    execution_summary: list[dict[str, Any]] = []
    raw_execution = out.get("execution")
    if isinstance(raw_execution, Sequence) and not isinstance(raw_execution, (str, bytes)):
        for raw in raw_execution:
            if not isinstance(raw, Mapping):
                return None
            execution_summary.append({
                "capability_id": _s(raw.get("capability_id")) or None,
                "pass": raw.get("pass") is True,
                "status": _s(raw.get("status")) or None,
                "composition_capsule_head_hash": (
                    _s(raw.get("composition_capsule_head_hash")) or None
                ),
            })

    material = {
        "source_schema": _s(out.get("schema")) or None,
        "source_status": _s(out.get("status")) or None,
        "task_id": _s(out.get("task_id")) or None,
        "selected_plan": [_s(x) for x in selected_plan if _s(x)],
        "verified_target_effects": _items(out.get("verified_target_effects")),
        "controller_checkpoint": {
            "path": checkpoint_path,
            "plan_sha256": plan_sha256,
        },
        "execution": execution_summary,
        "cognition_dependency_class": _s(out.get("cognition_dependency_class")) or None,
        "model_dependency_count": out.get("model_dependency_count"),
        "semantic_acceptance_complete": out.get("semantic_acceptance_complete") is True,
    }
    _validate_retry_value(material, path="success_proof")
    raw = _canon(material).encode("utf-8")
    if len(raw) > 128_000:
        raise SelfImprovementError("SUCCESS_PROOF_CAPSULE_TOO_LARGE")
    return {
        "schema": "PROJECT_BRAIN_SUCCESS_PROOF_CAPSULE_V1",
        "sha256": _sha(material),
        "material": material,
        "secret_scan": "PASS",
    }


def get_success_proof_context(
    observation_id: str,
    *,
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    oid = _s(observation_id)
    state = load_state(state_path)
    observation = state.get("observations", {}).get(oid)
    if not isinstance(observation, Mapping):
        raise SelfImprovementError("SUCCESS_OBSERVATION_UNKNOWN:" + oid)
    capsule = observation.get("proof_capsule")
    if not isinstance(capsule, Mapping):
        raise SelfImprovementError("SUCCESS_OBSERVATION_PROOF_UNAVAILABLE:" + oid)
    material = capsule.get("material")
    expected = _s(capsule.get("sha256"))
    if not isinstance(material, Mapping) or not expected:
        raise SelfImprovementError("SUCCESS_PROOF_CAPSULE_INVALID:" + oid)
    _validate_retry_value(material, path="success_proof")
    actual = _sha(material)
    if actual != expected:
        raise SelfImprovementError("SUCCESS_PROOF_CAPSULE_DIGEST_MISMATCH:" + oid)
    return {
        "observation_id": oid,
        "proof_capsule_sha256": expected,
        "material": deepcopy(dict(material)),
    }


def _empty_state() -> dict[str, Any]:
    return {
        "schema": STATE_SCHEMA,
        "version": 1,
        "episodes": {},
        "skills": {},
        "pareto_frontiers": {},
        "failures": {},
        "reuse": {},
        "observations": {},
        "improvement_queue": {},
        "stats": {
            "verified_episode_count": 0,
            "verified_skill_count": 0,
            "active_skill_count": 0,
            "failure_class_count": 0,
            "success_observation_count": 0,
            "pending_improvement_count": 0,
        },
    }


def load_state(path: str | Path = DEFAULT_STATE_PATH) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return _empty_state()
    doc = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping) or doc.get("schema") != STATE_SCHEMA:
        raise SelfImprovementError("SELF_IMPROVEMENT_STATE_SCHEMA_INVALID")
    state = deepcopy(dict(doc))
    state.setdefault("reuse", {})
    state.setdefault("observations", {})
    state.setdefault("improvement_queue", {})
    for key in (
        "episodes", "skills", "pareto_frontiers", "failures", "reuse",
        "observations", "improvement_queue", "stats",
    ):
        if not isinstance(state.get(key), Mapping):
            raise SelfImprovementError("SELF_IMPROVEMENT_STATE_FIELD_INVALID:" + key)
    return state


def _write_state(state: Mapping[str, Any], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(p)


def _episode_key(ep: Mapping[str, Any]) -> str:
    eid = _s(ep.get("episode_id"))
    scope = _s(ep.get("scope_id"))
    program = _s(ep.get("program_sha256"))
    trace = _s(ep.get("trace_sha256"))
    if not eid or not scope or not program or not trace:
        raise SelfImprovementError("VERIFIED_EPISODE_IDENTITY_INCOMPLETE")
    return "episode:" + _sha(
        {"episode_id": eid, "scope_id": scope, "program": program, "trace": trace}
    )


def _skill_id(skill: Mapping[str, Any]) -> str:
    digest = _s(skill.get("candidate_sha256"))
    if not digest:
        raise SelfImprovementError("VERIFIED_SKILL_DIGEST_MISSING")
    return "skill:" + digest.replace("sha256:", "")


def _family_id(skill: Mapping[str, Any]) -> str:
    post = _items(skill.get("postconditions"))
    if not post:
        raise SelfImprovementError("VERIFIED_SKILL_POSTCONDITIONS_EMPTY")
    return "family:" + _sha({"postconditions": post})


def _skill_pareto_row(skill_id: str, skill: Mapping[str, Any]) -> dict[str, Any]:
    steps = skill.get("steps")
    if not isinstance(steps, Sequence) or isinstance(steps, (str, bytes)) or not steps:
        raise SelfImprovementError("VERIFIED_SKILL_STEPS_INVALID")
    source_ids = _items(skill.get("source_episode_ids"))
    relation = _s(skill.get("scope_relation"))
    if relation not in {"EXACT", "PROVEN_SUPERSET"}:
        raise SelfImprovementError("VERIFIED_SKILL_SCOPE_RELATION_INVALID")

    io_width = 0
    for step in steps:
        if not isinstance(step, Mapping):
            raise SelfImprovementError("VERIFIED_SKILL_STEP_INVALID")
        io_width += len(_items(step.get("inputs"))) + len(_items(step.get("outputs")))

    generalized = (
        relation == "PROVEN_SUPERSET"
        and _s(skill.get("scope_predicate")) == VERIFIED_SUPERSET_SCOPE_PREDICATE
    )
    return {
        "capability_id": skill_id,
        "reusable_capability": True,
        "independently_verified": True,
        "capability": len(_items(skill.get("postconditions"))),
        "generalization": 2 if generalized else 1,
        "reliability": len(source_ids),
        "latency": len(steps),
        "compute": len(steps),
        "memory": io_width,
        "incremental_spend_usd": 0,
    }


def _diagnose_failure(out: Mapping[str, Any]) -> dict[str, Any]:
    status = _s(out.get("status"))
    reason = _s(out.get("reason") or out.get("failure_class"))
    next_edge = _s(out.get("next_required_edge") or out.get("next_required_effect"))
    joined = (status + " " + reason + " " + next_edge).upper()

    if any(token in joined for token in (
        "NO_VERIFIED_CAPABILITY",
        "UNREACHABLE_TARGET",
        "CAPABILITY_OR_TASK_CONTRACT_GAP",
        "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP",
    )):
        repair = "ACQUIRE_COMPOSE_OR_INVENT_VERIFIABLE_CAPABILITY"
    elif any(token in joined for token in (
        "POSITIVE_POLICY_ADEQUACY",
        "POLICY_ADEQUACY_COVERAGE",
        "AUTHENTICATED_POLICY_ADEQUACY",
    )):
        repair = "SYNTHESIZE_OR_AUTHENTICATE_POLICY_ADEQUACY_COVER"
    elif any(token in joined for token in (
        "POLICY_CHANGING_DISCRIMINATOR",
        "POLICY_COVER_OBSERVATION",
        "OBSERVATION_BINDING_REQUIRED",
    )):
        repair = "RESOLVE_MINIMUM_BLOCKING_INFORMATION_AND_RETRY"
    elif "SEMANTIC" in joined:
        repair = "BIND_AND_INDEPENDENTLY_VERIFY_EFFECT_SEMANTICS"
    elif "VERIFICATION" in joined or "NOT_AUTHENTICATED" in joined:
        repair = "OBTAIN_OR_REPAIR_INDEPENDENT_VERIFICATION"
    elif "RECOVERY_REQUIRED" in joined or "EFFECT_MAY_HAVE_OCCURRED" in joined:
        repair = "RECOVER_FROM_OBSERVED_EFFECT_WITHOUT_BLIND_REPLAY"
    elif out.get("falsified_capability_ids"):
        repair = "REPLACE_FALSIFIED_ROUTE"
    elif out.get("deferred_capability_ids"):
        repair = "RESOLVE_MINIMUM_BLOCKING_INFORMATION_AND_RETRY"
    else:
        repair = "LOCALIZE_CAUSAL_FAILURE_AND_GENERATE_MINIMAL_REPAIR"

    core = {
        "status": status or None,
        "reason": reason or None,
        "next_required_edge": next_edge or None,
        "repair_class": repair,
        "falsified_capability_ids": _items(out.get("falsified_capability_ids")),
        "deferred_capability_ids": _items(out.get("deferred_capability_ids")),
        "counterexamples": deepcopy(list(out.get("counterexamples") or [])),
        "attempts": deepcopy(list(out.get("attempts") or [])),
    }
    return {
        **core,
        "failure_fingerprint": _sha(core),
    }


def _work_id(kind: str, identity: Mapping[str, Any]) -> str:
    return "work:" + _sha({"kind": _s(kind), "identity": deepcopy(dict(identity))})


def _enqueue_improvement(
    state: dict[str, Any],
    *,
    kind: str,
    priority: int,
    identity: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> str:
    queue = state.setdefault("improvement_queue", {})
    if not isinstance(queue, dict):
        raise SelfImprovementError("IMPROVEMENT_QUEUE_INVALID")
    wid = _work_id(kind, identity)
    previous = queue.get(wid)
    observations = (
        int(previous.get("observations", 0)) + 1
        if isinstance(previous, Mapping) else 1
    )
    reopen_count = (
        int(previous.get("reopen_count", 0))
        + (1 if previous.get("status") == "RESOLVED" else 0)
        if isinstance(previous, Mapping)
        else 0
    )
    queue[wid] = {
        "work_id": wid,
        "kind": _s(kind),
        "priority": int(priority),
        "identity": deepcopy(dict(identity)),
        "payload": deepcopy(dict(payload)),
        "status": "PENDING",
        "observations": observations,
        "reopen_count": reopen_count,
        "attempt_count": (
            int(previous.get("attempt_count", 0))
            if isinstance(previous, Mapping) else 0
        ),
        "last_attempt_observations": (
            previous.get("last_attempt_observations")
            if isinstance(previous, Mapping) else None
        ),
        "last_attempt_status": (
            previous.get("last_attempt_status")
            if isinstance(previous, Mapping) else None
        ),
        "last_attempt_reason": (
            previous.get("last_attempt_reason")
            if isinstance(previous, Mapping) else None
        ),
    }
    return wid


def _resolve_improvements(
    state: dict[str, Any],
    *,
    kind: str,
    predicate,
    resolved_by: str,
) -> list[str]:
    resolved: list[str] = []
    queue = state.get("improvement_queue", {})
    if not isinstance(queue, Mapping):
        return resolved
    for wid, raw in queue.items():
        if not isinstance(raw, dict) or raw.get("status") != "PENDING":
            continue
        if raw.get("kind") != kind or not predicate(raw):
            continue
        raw["status"] = "RESOLVED"
        raw["resolved_by"] = _s(resolved_by)
        resolved.append(str(wid))
    return sorted(resolved)


def _next_improvement_from_state(state: Mapping[str, Any]) -> dict[str, Any] | None:
    queue = state.get("improvement_queue", {})
    if not isinstance(queue, Mapping):
        return None
    pending = [
        deepcopy(dict(row))
        for row in queue.values()
        if isinstance(row, Mapping) and row.get("status") == "PENDING"
    ]
    if not pending:
        return None
    pending.sort(
        key=lambda row: (
            int(row.get("priority", 10**9)),
            -int(row.get("observations", 0)),
            str(row.get("work_id") or ""),
        )
    )
    return pending[0]


def next_improvement_action(
    *,
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> dict[str, Any] | None:
    """Return the highest-priority unresolved compounding action, deterministically."""
    return _next_improvement_from_state(load_state(state_path))


def _candidate_from_verified_skill(skill: Mapping[str, Any]) -> dict[str, Any]:
    """Recover the immutable candidate payload underlying a verified skill."""
    if not isinstance(skill, Mapping):
        raise SelfImprovementError("VERIFIED_SKILL_NOT_OBJECT")
    candidate = deepcopy(dict(skill))
    for key in (
        "scope_relation",
        "scope_predicate",
        "verification_receipt",
        "verification_binding",
        "independent_verifier_id",
        "verified_skill",
        "reuse_authorized",
        "candidate_only",
        "acceptance_credit_delta",
        "family_credit_delta",
        "capability_credit_delta",
        "ownership_credit_delta",
        "promotion_authority",
        "execution_authority",
    ):
        candidate.pop(key, None)
    candidate["status"] = "EXECUTABLE_SKILL_CANDIDATE_ONLY"
    candidate["verified_skill"] = False
    candidate["reuse_authorized"] = False
    candidate["candidate_only"] = True
    return candidate


def _record_improvement_attempt(
    work_id: str,
    *,
    status: str,
    reason: str | None,
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> None:
    state = load_state(state_path)
    queue = state.get("improvement_queue", {})
    row = queue.get(_s(work_id)) if isinstance(queue, Mapping) else None
    if not isinstance(row, dict) or row.get("status") != "PENDING":
        return
    row["attempt_count"] = int(row.get("attempt_count", 0)) + 1
    row["last_attempt_observations"] = int(row.get("observations", 0))
    row["last_attempt_status"] = _s(status) or "ATTEMPTED"
    row["last_attempt_reason"] = _s(reason) or None
    _refresh_stats(state)
    _write_state(state, state_path)


def advance_verification_queue(
    *,
    state_path: str | Path = DEFAULT_STATE_PATH,
    repo_root: str | Path = ROOT,
    skill_verification_provider=None,
    max_actions: int = 4,
) -> dict[str, Any]:
    """Consume safe verifier-backed compounding work without replaying effects.

    Only already-produced skill evidence is handled here. External-effect replay
    remains in its dedicated guarded repair paths. The independent verifier and
    existing authenticator remain the sole authority for promotion.
    """
    if isinstance(max_actions, bool) or int(max_actions) < 1:
        raise SelfImprovementError("MAX_ACTIONS_INVALID")
    max_actions = int(max_actions)
    if skill_verification_provider is None:
        state = load_state(state_path)
        return {
            "schema": SCHEMA,
            "status": "VERIFICATION_QUEUE_BLOCKED__INDEPENDENT_SKILL_VERIFIER_UNAVAILABLE",
            "pass": False,
            "attempted": 0,
            "completed": 0,
            "next_improvement_action": _next_improvement_from_state(state),
            "terminal_authority": False,
        }

    supported = {
        "VERIFY_SKILL_CANDIDATE",
        "SEEK_VERIFIED_SCOPE_GENERALIZATION",
    }
    attempted = 0
    completed = 0
    results: list[dict[str, Any]] = []

    while attempted < max_actions:
        state = load_state(state_path)
        queue = state.get("improvement_queue", {})
        eligible: list[dict[str, Any]] = []
        if isinstance(queue, Mapping):
            for raw in queue.values():
                if not isinstance(raw, Mapping) or raw.get("status") != "PENDING":
                    continue
                if _s(raw.get("kind")) not in supported:
                    continue
                observations = int(raw.get("observations", 0))
                last_attempt = raw.get("last_attempt_observations")
                if last_attempt is not None and int(last_attempt) >= observations:
                    continue
                eligible.append(deepcopy(dict(raw)))
        eligible.sort(
            key=lambda row: (
                int(row.get("priority", 10**9)),
                -int(row.get("observations", 0)),
                _s(row.get("work_id")),
            )
        )
        if not eligible:
            break

        work = eligible[0]
        work_id = _s(work.get("work_id"))
        kind = _s(work.get("kind"))
        payload = work.get("payload")
        if not isinstance(payload, Mapping):
            _record_improvement_attempt(
                work_id,
                status="FAIL_CLOSED",
                reason="IMPROVEMENT_PAYLOAD_INVALID",
                state_path=state_path,
            )
            attempted += 1
            results.append({
                "work_id": work_id,
                "kind": kind,
                "pass": False,
                "status": "FAIL_CLOSED",
                "reason": "IMPROVEMENT_PAYLOAD_INVALID",
            })
            continue

        candidate: Mapping[str, Any] | None = None
        request_kind = "SKILL_VERIFICATION"
        requested_relation = None
        requested_predicate = None
        if kind == "VERIFY_SKILL_CANDIDATE":
            raw_candidate = payload.get("candidate")
            if isinstance(raw_candidate, Mapping):
                candidate = deepcopy(dict(raw_candidate))
        elif kind == "SEEK_VERIFIED_SCOPE_GENERALIZATION":
            skill_id = _s(
                payload.get("skill_id")
                or work.get("identity", {}).get("skill_id")
            )
            record = state.get("skills", {}).get(skill_id)
            raw_skill = record.get("skill") if isinstance(record, Mapping) else None
            if isinstance(raw_skill, Mapping):
                candidate = _candidate_from_verified_skill(raw_skill)
                request_kind = "SKILL_SCOPE_GENERALIZATION_VERIFICATION"
                requested_relation = "PROVEN_SUPERSET"
                requested_predicate = VERIFIED_SUPERSET_SCOPE_PREDICATE

        if not isinstance(candidate, Mapping):
            _record_improvement_attempt(
                work_id,
                status="FAIL_CLOSED",
                reason="VERIFICATION_CANDIDATE_UNAVAILABLE",
                state_path=state_path,
            )
            attempted += 1
            results.append({
                "work_id": work_id,
                "kind": kind,
                "pass": False,
                "status": "FAIL_CLOSED",
                "reason": "VERIFICATION_CANDIDATE_UNAVAILABLE",
            })
            continue

        request = {
            "kind": request_kind,
            "work_id": work_id,
            "candidate": deepcopy(dict(candidate)),
            "supported_scope_predicates": [VERIFIED_SUPERSET_SCOPE_PREDICATE],
        }
        if requested_relation is not None:
            request["requested_scope_relation"] = requested_relation
            request["requested_scope_predicate"] = requested_predicate

        attempted += 1
        try:
            binding = skill_verification_provider(deepcopy(request))
            if not isinstance(binding, Mapping):
                _record_improvement_attempt(
                    work_id,
                    status="BLOCKED__VERIFIER_RETURNED_NO_BINDING",
                    reason=None,
                    state_path=state_path,
                )
                results.append({
                    "work_id": work_id,
                    "kind": kind,
                    "pass": False,
                    "status": "BLOCKED__VERIFIER_RETURNED_NO_BINDING",
                })
                continue

            auth = authenticate_skill_verification(
                candidate,
                binding,
                repo_root=repo_root,
            )
            if auth.get("pass") is not True:
                reason = _s(auth.get("reason")) or "INDEPENDENT_SKILL_VERIFICATION_FAILED"
                _record_improvement_attempt(
                    work_id,
                    status="FAIL_CLOSED__INDEPENDENT_VERIFICATION_REJECTED",
                    reason=reason,
                    state_path=state_path,
                )
                results.append({
                    "work_id": work_id,
                    "kind": kind,
                    "pass": False,
                    "status": "FAIL_CLOSED__INDEPENDENT_VERIFICATION_REJECTED",
                    "reason": reason,
                })
                continue

            verified = auth.get("verified_skill")
            if not isinstance(verified, Mapping):
                raise SelfImprovementError("AUTHENTICATED_VERIFIED_SKILL_MISSING")
            if kind == "SEEK_VERIFIED_SCOPE_GENERALIZATION":
                if (
                    _s(verified.get("scope_relation")) != "PROVEN_SUPERSET"
                    or _s(verified.get("scope_predicate"))
                    != VERIFIED_SUPERSET_SCOPE_PREDICATE
                ):
                    _record_improvement_attempt(
                        work_id,
                        status="FAIL_CLOSED__GENERALIZATION_PROOF_NOT_SUPERSET",
                        reason="BOUND_PROVEN_SUPERSET_STRUCTURAL_MATCH_REQUIRED",
                        state_path=state_path,
                    )
                    results.append({
                        "work_id": work_id,
                        "kind": kind,
                        "pass": False,
                        "status": "FAIL_CLOSED__GENERALIZATION_PROOF_NOT_SUPERSET",
                        "reason": "BOUND_PROVEN_SUPERSET_STRUCTURAL_MATCH_REQUIRED",
                    })
                    continue

            integrated = integrate_solver_output(
                {
                    "pass": True,
                    "status": "SOLVED__VERIFIED_EXECUTABLE_SKILL_READY",
                    "current_episode_verified": False,
                    "skill_candidate": deepcopy(dict(candidate)),
                    "verified_executable_skill": deepcopy(dict(verified)),
                    "verified_skill_reuse_authorized": True,
                },
                state_path=state_path,
                repo_root=repo_root,
            )
            completed += 1
            results.append({
                "work_id": work_id,
                "kind": kind,
                "pass": True,
                "status": _s(integrated.get("status")),
                "active_skill_id": integrated.get("active_skill_id"),
                "scope_relation": verified.get("scope_relation"),
                "scope_predicate": verified.get("scope_predicate"),
            })
        except Exception as exc:
            reason = type(exc).__name__ + ":" + str(exc)
            _record_improvement_attempt(
                work_id,
                status="FAIL_CLOSED__VERIFICATION_QUEUE_EXCEPTION",
                reason=reason,
                state_path=state_path,
            )
            results.append({
                "work_id": work_id,
                "kind": kind,
                "pass": False,
                "status": "FAIL_CLOSED__VERIFICATION_QUEUE_EXCEPTION",
                "reason": reason,
            })

    state = load_state(state_path)
    return {
        "schema": SCHEMA,
        "status": (
            "VERIFICATION_QUEUE_ADVANCED"
            if completed else "VERIFICATION_QUEUE_NO_PROMOTION"
        ),
        "pass": True,
        "attempted": attempted,
        "completed": completed,
        "results": results,
        "next_improvement_action": _next_improvement_from_state(state),
        "terminal_authority": False,
    }


def record_success_observation(
    out: Mapping[str, Any],
    *,
    surface: str,
    state_path: str | Path = DEFAULT_STATE_PATH,
    replay_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Durably retain a compact success pointer when no verified episode exists.

    Plain runtime successes are not promoted. They become explicit work to build a
    verifiable episode adapter, preventing successful experience from silently
    disappearing while preserving the independent-verification boundary.
    """
    if not isinstance(out, Mapping) or out.get("pass") is not True:
        raise SelfImprovementError("SUCCESS_OBSERVATION_REQUIRES_PASSING_OUTPUT")
    name = _s(surface) or "UNSPECIFIED_RUNTIME_SURFACE"
    replay_capsule = (
        _make_retry_capsule(replay_context)
        if replay_context is not None else None
    )
    replay_sha = (
        str(replay_capsule.get("sha256") or "")
        if isinstance(replay_capsule, Mapping) else ""
    )
    proof_capsule = _make_success_proof_capsule(out)
    proof_sha = (
        str(proof_capsule.get("sha256") or "")
        if isinstance(proof_capsule, Mapping) else ""
    )
    core = {
        "surface": name,
        "schema": _s(out.get("schema")) or None,
        "status": _s(out.get("status")) or None,
        "output_sha256": _sha(out),
        "replay_capsule_sha256": replay_sha or None,
        "proof_capsule_sha256": proof_sha or None,
    }
    oid = "observation:" + _sha(core)
    state = load_state(state_path)
    previous = state["observations"].get(oid)
    state["observations"][oid] = {
        **core,
        "observation_id": oid,
        "count": int(previous.get("count", 0)) + 1 if isinstance(previous, Mapping) else 1,
        "replay_capsule": deepcopy(replay_capsule),
        "proof_capsule": deepcopy(proof_capsule),
    }
    work_id = _enqueue_improvement(
        state,
        kind="ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE",
        priority=50,
        identity={"surface": name, "schema": core["schema"]},
        payload={
            "observation_id": oid,
            "surface": name,
            "output_sha256": core["output_sha256"],
            "replay_capsule_sha256": core["replay_capsule_sha256"],
            "replayable": replay_capsule is not None,
            "proof_capsule_sha256": core["proof_capsule_sha256"],
            "proof_available": proof_capsule is not None,
            "required_result": "VERIFIED_EPISODE_OR_PROVED_NONLEARNABLE_SUCCESS",
        },
    )
    _refresh_stats(state)
    _write_state(state, state_path)
    return {
        "schema": SCHEMA,
        "status": "SUCCESS_OBSERVED__VERIFIABLE_EPISODE_ADAPTER_QUEUED",
        "pass": True,
        "observation_id": oid,
        "replay_capsule_sha256": core["replay_capsule_sha256"],
        "replayable": replay_capsule is not None,
        "proof_capsule_sha256": core["proof_capsule_sha256"],
        "proof_available": proof_capsule is not None,
        "improvement_work_id": work_id,
        "next_improvement_action": _next_improvement_from_state(state),
        "permanent_reuse_authorized": False,
        "terminal_authority": False,
    }


def get_success_replay_context(
    observation_id: str,
    *,
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    oid = _s(observation_id)
    state = load_state(state_path)
    observation = state.get("observations", {}).get(oid)
    if not isinstance(observation, Mapping):
        raise SelfImprovementError("SUCCESS_OBSERVATION_UNKNOWN:" + oid)
    capsule = observation.get("replay_capsule")
    if not isinstance(capsule, Mapping):
        raise SelfImprovementError("SUCCESS_OBSERVATION_NOT_REPLAYABLE:" + oid)
    context = capsule.get("context")
    expected = _s(capsule.get("sha256"))
    if not isinstance(context, Mapping) or not expected:
        raise SelfImprovementError("SUCCESS_REPLAY_CAPSULE_INVALID:" + oid)
    _validate_retry_value(context)
    actual = _sha(context)
    if actual != expected:
        raise SelfImprovementError("SUCCESS_REPLAY_CAPSULE_DIGEST_MISMATCH:" + oid)
    return {
        "observation_id": oid,
        "replay_capsule_sha256": expected,
        "context": deepcopy(dict(context)),
        "replay_authorized": capsule.get("replay_authorized") is True,
    }


def _refresh_stats(state: dict[str, Any]) -> None:
    queue = state.get("improvement_queue", {})
    state["stats"] = {
        "verified_episode_count": len(state["episodes"]),
        "verified_skill_count": len(state["skills"]),
        "active_skill_count": sum(
            1 for row in state["skills"].values()
            if isinstance(row, Mapping) and row.get("active") is True
        ),
        "failure_class_count": len(state["failures"]),
        "success_observation_count": len(state.get("observations", {})),
        "pending_improvement_count": sum(
            1 for row in queue.values()
            if isinstance(row, Mapping) and row.get("status") == "PENDING"
        ) if isinstance(queue, Mapping) else 0,
    }


def integrate_solver_output(
    out: Mapping[str, Any],
    *,
    state_path: str | Path = DEFAULT_STATE_PATH,
    repo_root: str | Path = ROOT,
    retry_context: Mapping[str, Any] | None = None,
    verification_problem: Mapping[str, Any] | None = None,
    verification_effect_root: str | Path | None = None,
) -> dict[str, Any]:
    """Persist only independently verified learning and update Pareto reuse state."""
    if not isinstance(out, Mapping):
        raise SelfImprovementError("SOLVER_OUTPUT_NOT_OBJECT")
    state = load_state(state_path)

    if out.get("pass") is not True:
        diagnosis = _diagnose_failure(out)
        fid = diagnosis["failure_fingerprint"]
        previous = state["failures"].get(fid)
        count = int(previous.get("count", 0)) + 1 if isinstance(previous, Mapping) else 1
        retry_capsules = {}
        repair_receipts = {}
        if isinstance(previous, Mapping):
            if isinstance(previous.get("retry_capsules"), Mapping):
                retry_capsules = deepcopy(dict(previous["retry_capsules"]))
            if isinstance(previous.get("repair_receipts"), Mapping):
                repair_receipts = deepcopy(dict(previous["repair_receipts"]))
        retry_sha = None
        if retry_context is not None:
            capsule = _make_retry_capsule(retry_context)
            retry_sha = capsule["sha256"]
            prior_capsule = retry_capsules.get(retry_sha)
            autonomous_replay_authorized = not _effect_may_have_occurred(out)
            autonomous_replay_reason = (
                "NO_EFFECT_OUTCOME_RECORDED"
                if autonomous_replay_authorized
                else "EFFECT_MAY_HAVE_OCCURRED__RECOVERY_OR_EXPLICIT_REPLAY_REQUIRED"
            )
            if isinstance(prior_capsule, Mapping):
                # Replay safety is monotonic. Once this exact retry context has
                # evidence that an effect may have occurred, or comes from a
                # legacy capsule without an explicit autonomous-safety proof,
                # a later observation cannot silently upgrade it to replayable.
                if prior_capsule.get("autonomous_replay_authorized") is not True:
                    autonomous_replay_authorized = False
                    autonomous_replay_reason = (
                        prior_capsule.get("autonomous_replay_reason")
                        or "LEGACY_OR_UNSAFE_RETRY_CAPSULE__EXPLICIT_RECOVERY_REQUIRED"
                    )
                if prior_capsule.get("resolved") is True:
                    capsule["resolved"] = True
                    capsule["resolved_by"] = prior_capsule.get("resolved_by")
            capsule["autonomous_replay_authorized"] = autonomous_replay_authorized
            capsule["autonomous_replay_reason"] = autonomous_replay_reason
            retry_capsules[retry_sha] = capsule
        state["failures"][fid] = {
            **diagnosis,
            "count": count,
            "retry_capsules": retry_capsules,
            "last_retry_capsule_sha256": retry_sha or (
                previous.get("last_retry_capsule_sha256") if isinstance(previous, Mapping) else None
            ),
            "repair_receipts": repair_receipts,
        }
        work_id = _enqueue_improvement(
            state,
            kind="REPAIR_FAILURE_CLASS",
            priority=30,
            identity={
                "failure_fingerprint": fid,
                "retry_capsule_sha256": retry_sha,
            },
            payload={
                "failure_fingerprint": fid,
                "repair_class": diagnosis["repair_class"],
                "status": diagnosis.get("status"),
                "reason": diagnosis.get("reason"),
                "retry_capsule_sha256": retry_sha,
            },
        )
        _refresh_stats(state)
        _write_state(state, state_path)
        return {
            "schema": SCHEMA,
            "status": "FAILURE_DIAGNOSED__REPAIR_QUEUED",
            "pass": False,
            "diagnosis": diagnosis,
            "retry_capsule_sha256": retry_sha,
            "retry_capsule_persisted": retry_sha is not None,
            "improvement_work_id": work_id,
            "next_improvement_action": _next_improvement_from_state(state),
            "state_stats": deepcopy(state["stats"]),
            "permanent_reuse_authorized": False,
            "terminal_authority": False,
        }

    episode_added = False
    episode_key = None
    if out.get("current_episode_verified") is True:
        ep = out.get("current_episode")
        if not isinstance(ep, Mapping):
            raise SelfImprovementError("VERIFIED_EPISODE_MISSING")
        binding = ep.get("verification_binding")
        receipt = ep.get("verification_receipt")
        if not isinstance(binding, Mapping) or not isinstance(receipt, Mapping):
            raise SelfImprovementError("VERIFIED_EPISODE_AUTHORITY_MISSING")
        episode_authority = reauthenticate_episode_record(ep, repo_root=repo_root)
        if episode_authority.get("pass") is not True:
            raise SelfImprovementError(
                "VERIFIED_EPISODE_REAUTHENTICATION_FAILED:"
                + _s(episode_authority.get("reason"))
            )
        authenticated_ep = episode_authority.get("authenticated_episode")
        if not isinstance(authenticated_ep, Mapping):
            raise SelfImprovementError("VERIFIED_EPISODE_REAUTHENTICATED_VALUE_MISSING")
        ep = authenticated_ep
        episode_key = _episode_key(ep)
        episode_added = episode_key not in state["episodes"]
        state["episodes"][episode_key] = deepcopy(dict(ep))
        _resolve_improvements(
            state,
            kind="VERIFY_EPISODE",
            predicate=lambda row: (
                row.get("identity", {}).get("episode_id") == _s(ep.get("episode_id"))
                and row.get("identity", {}).get("scope_id") == _s(ep.get("scope_id"))
                and row.get("identity", {}).get("program_sha256") == _s(ep.get("program_sha256"))
                and row.get("identity", {}).get("trace_sha256") == _s(ep.get("trace_sha256"))
            ),
            resolved_by=episode_key,
        )
    else:
        raw_ep = out.get("current_episode")
        if isinstance(raw_ep, Mapping):
            _enqueue_improvement(
                state,
                kind="VERIFY_EPISODE",
                priority=20,
                identity={
                    "episode_id": _s(raw_ep.get("episode_id")),
                    "scope_id": _s(raw_ep.get("scope_id")),
                    "program_sha256": _s(raw_ep.get("program_sha256")),
                    "trace_sha256": _s(raw_ep.get("trace_sha256")),
                },
                payload={
                    "episode_id": _s(raw_ep.get("episode_id")),
                    "scope_id": _s(raw_ep.get("scope_id")),
                    "program_sha256": _s(raw_ep.get("program_sha256")),
                    "trace_sha256": _s(raw_ep.get("trace_sha256")),
                    "verification_error": _s(out.get("episode_verification_error")) or None,
                    "episode": deepcopy(dict(raw_ep)),
                    "trace": deepcopy(list(out.get("trace") or [])),
                    "problem": (
                        deepcopy(dict(verification_problem))
                        if isinstance(verification_problem, Mapping)
                        else None
                    ),
                    "fact_capsule_head_hash": _s(out.get("state_capsule_head_hash")),
                    "value_capsule_head_hash": _s(out.get("value_capsule_head_hash")),
                    "effect_root": (
                        str(verification_effect_root)
                        if verification_effect_root is not None
                        else None
                    ),
                },
            )

    skill_admission = None
    active_skill_id = None
    verified_skill = out.get("verified_executable_skill")
    skill_candidate = out.get("skill_candidate")
    if (
        out.get("verified_skill_reuse_authorized") is True
        and isinstance(verified_skill, Mapping)
    ):
        skill_authority = reauthenticate_skill_record(
            verified_skill,
            repo_root=repo_root,
        )
        if skill_authority.get("pass") is not True:
            raise SelfImprovementError(
                "VERIFIED_SKILL_REAUTHENTICATION_FAILED:"
                + _s(skill_authority.get("reason"))
            )
        authenticated_skill = skill_authority.get("verified_skill")
        if not isinstance(authenticated_skill, Mapping):
            raise SelfImprovementError("VERIFIED_SKILL_REAUTHENTICATED_VALUE_MISSING")
        verified_skill = authenticated_skill
    if isinstance(skill_candidate, Mapping) and not isinstance(verified_skill, Mapping):
        candidate_sha = _s(skill_candidate.get("candidate_sha256"))
        if candidate_sha:
            candidate_scopes = set(_items(skill_candidate.get("source_scopes")))
            candidate_postconditions = _items(skill_candidate.get("postconditions"))
            _resolve_improvements(
                state,
                kind="COLLECT_MATCHING_VERIFIED_EPISODE",
                predicate=lambda work: (
                    work.get("payload", {}).get("scope_id") in candidate_scopes
                    and _items(work.get("payload", {}).get("postconditions"))
                    == candidate_postconditions
                ),
                resolved_by=candidate_sha,
            )
            _enqueue_improvement(
                state,
                kind="VERIFY_SKILL_CANDIDATE",
                priority=10,
                identity={"candidate_sha256": candidate_sha},
                payload={
                    "candidate_sha256": candidate_sha,
                    "source_episode_ids": _items(skill_candidate.get("source_episode_ids")),
                    "source_scopes": _items(skill_candidate.get("source_scopes")),
                    "postconditions": _items(skill_candidate.get("postconditions")),
                    "candidate": deepcopy(dict(skill_candidate)),
                },
            )
    elif out.get("current_episode_verified") is True and not isinstance(skill_candidate, Mapping):
        ep = out.get("current_episode")
        if isinstance(ep, Mapping):
            _enqueue_improvement(
                state,
                kind="COLLECT_MATCHING_VERIFIED_EPISODE",
                priority=40,
                identity={
                    "scope_id": _s(ep.get("scope_id")),
                    "program_sha256": _s(ep.get("program_sha256")),
                    "postconditions": _items(ep.get("postconditions")),
                },
                payload={
                    "scope_id": _s(ep.get("scope_id")),
                    "program_sha256": _s(ep.get("program_sha256")),
                    "postconditions": _items(ep.get("postconditions")),
                    "minimum_verified_episode_count": 2,
                },
            )

    if (
        out.get("verified_skill_reuse_authorized") is True
        and isinstance(verified_skill, Mapping)
        and verified_skill.get("verified_skill") is True
        and verified_skill.get("reuse_authorized") is True
    ):
        sid = _skill_id(verified_skill)
        family = _family_id(verified_skill)
        row = _skill_pareto_row(sid, verified_skill)

        existing_ids = [
            old_sid
            for old_sid in state["pareto_frontiers"].get(family, [])
            if old_sid != sid
        ]
        frontier_rows = []
        for old_sid in existing_ids:
            old = state["skills"].get(old_sid)
            if not isinstance(old, dict):
                continue
            old_skill = old.get("skill")
            if not isinstance(old_skill, Mapping):
                old["active"] = False
                old["authority_invalidated"] = "STORED_SKILL_MISSING"
                continue
            old_authority = reauthenticate_skill_record(
                old_skill,
                repo_root=repo_root,
            )
            authenticated_old = old_authority.get("verified_skill")
            valid_old = (
                old_authority.get("pass") is True
                and isinstance(authenticated_old, Mapping)
            )
            if valid_old:
                try:
                    valid_old = (
                        _skill_id(authenticated_old) == str(old_sid)
                        and _family_id(authenticated_old) == family
                    )
                except SelfImprovementError:
                    valid_old = False
            if not valid_old:
                old["active"] = False
                old["authority_invalidated"] = (
                    _s(old_authority.get("reason"))
                    or "STORED_SKILL_ID_OR_FAMILY_MISMATCH"
                )
                continue
            frontier_rows.append(
                _skill_pareto_row(str(old_sid), authenticated_old)
            )

        skill_admission = update_pareto_frontier(frontier_rows, row)
        previous_record = state["skills"].get(sid)
        preserved_counterexample_scopes = (
            _items(previous_record.get("generalization_counterexample_scopes"))
            if isinstance(previous_record, Mapping)
            else []
        )
        record = {
            "skill": deepcopy(dict(verified_skill)),
            "family_id": family,
            "pareto_metrics": row,
            "active": bool(skill_admission.get("admitted")),
            "dominated_by": skill_admission.get("dominated_by"),
            "compression": {
                "source_episode_count": len(_items(verified_skill.get("source_episode_ids"))),
                "stored_program_step_count": len(list(verified_skill.get("steps") or [])),
                "repeated_program_copies_eliminated": max(
                    0, len(_items(verified_skill.get("source_episode_ids"))) - 1
                ),
            },
        }
        if preserved_counterexample_scopes:
            record["generalization_counterexample_scopes"] = preserved_counterexample_scopes
            record["generalization_repromotion_blocked"] = True
            if _s(verified_skill.get("scope_relation")) == "EXACT":
                record["recovered_from_quarantine_by_scope_contraction"] = True
        state["skills"][sid] = record
        _resolve_improvements(
            state,
            kind="VERIFY_SKILL_CANDIDATE",
            predicate=lambda work: work.get("identity", {}).get("candidate_sha256")
            == _s(verified_skill.get("candidate_sha256")),
            resolved_by=sid,
        )
        _resolve_improvements(
            state,
            kind="REVERIFY_QUARANTINED_SKILL",
            predicate=lambda work: work.get("identity", {}).get("skill_id") == sid,
            resolved_by=sid,
        )

        if skill_admission.get("admitted") is True:
            active_skill_id = sid
            _resolve_improvements(
                state,
                kind="REVERIFY_QUARANTINED_SKILL",
                predicate=lambda work: (
                    work.get("payload", {}).get("family_id") == family
                ),
                resolved_by=sid,
            )
            source_scopes = set(_items(verified_skill.get("source_scopes")))
            postconditions = _items(verified_skill.get("postconditions"))
            _resolve_improvements(
                state,
                kind="COLLECT_MATCHING_VERIFIED_EPISODE",
                predicate=lambda work: (
                    work.get("payload", {}).get("scope_id") in source_scopes
                    and _items(work.get("payload", {}).get("postconditions")) == postconditions
                ),
                resolved_by=sid,
            )
            verified_generalization = (
                _s(verified_skill.get("scope_relation")) == "PROVEN_SUPERSET"
                and _s(verified_skill.get("scope_predicate"))
                == VERIFIED_SUPERSET_SCOPE_PREDICATE
            )
            if not verified_generalization and not preserved_counterexample_scopes:
                _enqueue_improvement(
                    state,
                    kind="SEEK_VERIFIED_SCOPE_GENERALIZATION",
                    priority=60,
                    identity={"family_id": family, "skill_id": sid},
                    payload={
                        "family_id": family,
                        "skill_id": sid,
                        "source_scopes": sorted(source_scopes),
                        "postconditions": postconditions,
                        "required_result": "INDEPENDENTLY_VERIFIED_PROVEN_SUPERSET_SKILL",
                    },
                )
            elif not verified_generalization:
                _resolve_improvements(
                    state,
                    kind="SEEK_VERIFIED_SCOPE_GENERALIZATION",
                    predicate=lambda work: work.get("identity", {}).get("skill_id") == sid,
                    resolved_by=sid + ":GENERALIZATION_BLOCKED_BY_COUNTEREXAMPLE",
                )
            else:
                _resolve_improvements(
                    state,
                    kind="SEEK_VERIFIED_SCOPE_GENERALIZATION",
                    predicate=lambda work: work.get("identity", {}).get("family_id") == family,
                    resolved_by=sid,
                )
            admitted_ids = [
                str(x.get("capability_id"))
                for x in skill_admission.get("frontier", [])
                if isinstance(x, Mapping) and x.get("capability_id")
            ]
            state["pareto_frontiers"][family] = sorted(set(admitted_ids))
            for removed in skill_admission.get("removed_dominated", []) or []:
                if removed in state["skills"] and isinstance(state["skills"][removed], dict):
                    state["skills"][removed]["active"] = False
                    state["skills"][removed]["dominated_by"] = sid

    _refresh_stats(state)
    _write_state(state, state_path)

    if active_skill_id:
        status = "VERIFIED_SKILL_PERMANENTLY_ADMITTED_FOR_REUSE"
    elif out.get("skill_candidate") is not None:
        status = "SKILL_CANDIDATE_AWAITS_INDEPENDENT_VERIFICATION"
    elif out.get("current_episode_verified") is True:
        status = "VERIFIED_EPISODE_PERSISTED__MORE_EVIDENCE_NEEDED_FOR_SKILL"
    else:
        status = "EPISODE_AWAITS_INDEPENDENT_VERIFICATION"

    return {
        "schema": SCHEMA,
        "status": status,
        "pass": True,
        "episode_added": episode_added,
        "episode_key": episode_key,
        "active_skill_id": active_skill_id,
        "skill_admission": deepcopy(skill_admission),
        "state_stats": deepcopy(state["stats"]),
        "next_improvement_action": _next_improvement_from_state(state),
        "permanent_reuse_authorized": active_skill_id is not None,
        "terminal_authority": False,
    }


def get_failure_retry_context(
    failure_fingerprint: str,
    *,
    state_path: str | Path = DEFAULT_STATE_PATH,
    retry_capsule_sha256: str | None = None,
) -> dict[str, Any]:
    fid = _s(failure_fingerprint)
    if not fid:
        raise SelfImprovementError("FAILURE_FINGERPRINT_REQUIRED")
    state = load_state(state_path)
    record = state.get("failures", {}).get(fid)
    if not isinstance(record, Mapping):
        raise SelfImprovementError("FAILURE_FINGERPRINT_UNKNOWN:" + fid)
    capsules = record.get("retry_capsules")
    if not isinstance(capsules, Mapping) or not capsules:
        raise SelfImprovementError("FAILURE_RETRY_CAPSULE_MISSING:" + fid)
    wanted = _s(retry_capsule_sha256) if retry_capsule_sha256 is not None else _s(record.get("last_retry_capsule_sha256"))
    if not wanted:
        wanted = sorted(str(k) for k in capsules)[-1]
    capsule = capsules.get(wanted)
    if not isinstance(capsule, Mapping):
        raise SelfImprovementError("FAILURE_RETRY_CAPSULE_UNKNOWN:" + wanted)
    context = capsule.get("context")
    if not isinstance(context, Mapping):
        raise SelfImprovementError("FAILURE_RETRY_CONTEXT_INVALID:" + wanted)
    if capsule.get("replay_authorized") is not True or capsule.get("secret_scan") != "PASS":
        raise SelfImprovementError("FAILURE_RETRY_CAPSULE_NOT_AUTHORIZED:" + wanted)
    if _sha(context) != wanted:
        raise SelfImprovementError("FAILURE_RETRY_CAPSULE_DIGEST_MISMATCH:" + wanted)
    return {
        "failure_fingerprint": fid,
        "retry_capsule_sha256": wanted,
        "context": deepcopy(dict(context)),
        "autonomous_replay_authorized": (
            capsule.get("autonomous_replay_authorized") is True
        ),
        "autonomous_replay_reason": capsule.get("autonomous_replay_reason"),
        "resolved": capsule.get("resolved") is True,
        "resolved_by": capsule.get("resolved_by"),
    }


def record_repair_outcome(
    failure_fingerprint: str,
    *,
    retry_capsule_sha256: str,
    repair_record: Mapping[str, Any],
    original_replay_pass: bool,
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    if not isinstance(repair_record, Mapping):
        raise SelfImprovementError("REPAIR_RECORD_NOT_OBJECT")
    fid = _s(failure_fingerprint)
    retry_sha = _s(retry_capsule_sha256)
    state = load_state(state_path)
    failure = state.get("failures", {}).get(fid)
    if not isinstance(failure, dict):
        raise SelfImprovementError("FAILURE_FINGERPRINT_UNKNOWN:" + fid)
    capsules = failure.get("retry_capsules")
    if not isinstance(capsules, dict) or retry_sha not in capsules:
        raise SelfImprovementError("FAILURE_RETRY_CAPSULE_UNKNOWN:" + retry_sha)
    repair = deepcopy(dict(repair_record))
    repair_sha = _sha(repair)
    receipts = failure.setdefault("repair_receipts", {})
    if not isinstance(receipts, dict):
        raise SelfImprovementError("FAILURE_REPAIR_RECEIPTS_INVALID")
    receipts[repair_sha] = {
        "sha256": repair_sha,
        "repair": repair,
        "original_replay_pass": bool(original_replay_pass),
    }
    capsule = capsules[retry_sha]
    if not isinstance(capsule, dict):
        raise SelfImprovementError("FAILURE_RETRY_CAPSULE_INVALID:" + retry_sha)
    if original_replay_pass:
        capsule["resolved"] = True
        capsule["resolved_by"] = repair_sha
        _resolve_improvements(
            state,
            kind="REPAIR_FAILURE_CLASS",
            predicate=lambda work: (
                work.get("identity", {}).get("failure_fingerprint") == fid
                and work.get("identity", {}).get("retry_capsule_sha256") == retry_sha
            ),
            resolved_by=repair_sha,
        )
    _refresh_stats(state)
    _write_state(state, state_path)
    unresolved = sum(
        1 for item in capsules.values()
        if isinstance(item, Mapping) and item.get("resolved") is not True
    )
    return {
        "failure_fingerprint": fid,
        "retry_capsule_sha256": retry_sha,
        "repair_receipt_sha256": repair_sha,
        "original_replay_pass": bool(original_replay_pass),
        "retry_instance_resolved": capsule.get("resolved") is True,
        "unresolved_retry_instance_count": unresolved,
        "terminal_authority": False,
    }


def _prior_verified_episodes(
    state: Mapping[str, Any],
    *,
    scope_id: str,
    episode_id: str,
) -> list[Mapping[str, Any]]:
    out = []
    for ep in state.get("episodes", {}).values():
        if not isinstance(ep, Mapping):
            continue
        if _s(ep.get("scope_id")) != scope_id:
            continue
        if _s(ep.get("episode_id")) == episode_id:
            continue
        out.append(deepcopy(dict(ep)))
    out.sort(key=lambda x: (_s(x.get("episode_id")), _s(x.get("program_sha256"))))
    return out



def _all_prior_verified_episodes(
    state: Mapping[str, Any],
    *,
    episode_id: str,
) -> list[Mapping[str, Any]]:
    out = []
    for ep in state.get("episodes", {}).values():
        if not isinstance(ep, Mapping):
            continue
        if _s(ep.get("episode_id")) == episode_id:
            continue
        out.append(deepcopy(dict(ep)))
    out.sort(
        key=lambda x: (
            _s(x.get("scope_id")),
            _s(x.get("episode_id")),
            _s(x.get("program_sha256")),
        )
    )
    return out


def _effect_may_have_occurred(out: Mapping[str, Any]) -> bool:
    trace = out.get("trace")
    if not isinstance(trace, Sequence) or isinstance(trace, (str, bytes)):
        return False
    return any(
        isinstance(row, Mapping) and bool(row.get("effect_outcome_sha256"))
        for row in trace
    )


def _select_active_skill(
    problem: Mapping[str, Any],
    state: Mapping[str, Any],
    *,
    scope_id: str,
    repo_root: str | Path = ROOT,
    known_absent_invalidators: Sequence[str] = (),
) -> dict[str, Any] | None:
    """Select a durable verified skill only when its exact executable skeleton fits.

    V1 reuse is deliberately conservative:
    - EXACT skills remain limited to independently verified source scopes;
    - PROVEN_SUPERSET skills may cross scope only when independent verification
      binds STRUCTURAL_MATCH_V1;
    - every stored invalidator must be explicitly known absent;
    - current capability ids and requires/provides must exactly match every skill step;
    - the skill preconditions must already hold and its postconditions must cover
      the current target effects.

    This makes a stored skill a planning compression hint, never semantic authority.
    The ordinary V12 effect semantics and execution verification still run.
    """
    if not isinstance(problem, Mapping):
        raise SelfImprovementError("PROBLEM_NOT_OBJECT")
    if not isinstance(known_absent_invalidators, Sequence) or isinstance(
        known_absent_invalidators, (str, bytes)
    ):
        raise SelfImprovementError("KNOWN_ABSENT_INVALIDATORS_INVALID")

    initial = set(_items(problem.get("initial_facts")))
    targets = set(_items(problem.get("target_effects")))
    absent = set(_items(known_absent_invalidators))
    raw_caps = problem.get("capabilities")
    if not isinstance(raw_caps, Sequence) or isinstance(raw_caps, (str, bytes)):
        return None

    cap_by_id: dict[str, Mapping[str, Any]] = {}
    for cap in raw_caps:
        if not isinstance(cap, Mapping):
            return None
        cid = _s(cap.get("id"))
        if not cid or cid in cap_by_id:
            return None
        cap_by_id[cid] = cap

    candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    for sid, record in state.get("skills", {}).items():
        if not isinstance(record, Mapping) or record.get("active") is not True:
            continue
        skill = record.get("skill")
        if not isinstance(skill, Mapping):
            continue
        if skill.get("verified_skill") is not True or skill.get("reuse_authorized") is not True:
            continue
        authority = reauthenticate_skill_record(skill, repo_root=repo_root)
        if authority.get("pass") is not True:
            continue
        skill = authority.get("verified_skill")
        if not isinstance(skill, Mapping):
            continue
        try:
            authenticated_sid = _skill_id(skill)
            authenticated_family = _family_id(skill)
        except SelfImprovementError:
            continue
        if str(sid) != authenticated_sid:
            continue
        if _s(record.get("family_id")) != authenticated_family:
            continue
        relation = _s(skill.get("scope_relation"))
        source_scopes = set(_items(skill.get("source_scopes")))
        if relation == "EXACT":
            if scope_id not in source_scopes:
                continue
        elif relation == "PROVEN_SUPERSET":
            # Historical/unbound superset receipts remain source-scope-only.
            # Cross-scope reuse is authorized only by an independently bound,
            # machine-defined structural predicate.
            if _s(skill.get("scope_predicate")) != VERIFIED_SUPERSET_SCOPE_PREDICATE:
                if scope_id not in source_scopes:
                    continue
        else:
            continue
        invalidators = set(_items(skill.get("invalidators")))
        if not invalidators.issubset(absent):
            continue
        if not set(_items(skill.get("preconditions"))).issubset(initial):
            continue
        if not targets.issubset(set(_items(skill.get("postconditions")))):
            continue

        steps = skill.get("steps")
        if not isinstance(steps, Sequence) or isinstance(steps, (str, bytes)) or not steps:
            continue
        available = set(initial)
        op_ids: list[str] = []
        valid = True
        for raw_step in steps:
            if not isinstance(raw_step, Mapping):
                valid = False
                break
            op = _s(raw_step.get("op"))
            cap = cap_by_id.get(op)
            if cap is None or op in op_ids:
                valid = False
                break
            step_inputs = set(_items(raw_step.get("inputs")))
            step_outputs = set(_items(raw_step.get("outputs")))
            if step_inputs != set(_items(cap.get("requires"))):
                valid = False
                break
            if step_outputs != set(_items(cap.get("provides"))):
                valid = False
                break
            if not step_inputs.issubset(available):
                valid = False
                break
            available.update(step_outputs)
            op_ids.append(op)
        if not valid or not targets.issubset(available):
            continue

        metrics = _skill_pareto_row(authenticated_sid, skill)
        rank = (
            int(metrics["latency"]),
            int(metrics["compute"]),
            int(metrics["memory"]),
            -int(metrics["reliability"]),
            authenticated_sid,
        )
        candidates.append(
            (
                rank,
                {
                    "skill_id": str(sid),
                    "skill": deepcopy(dict(skill)),
                    "operation_ids": op_ids,
                },
            )
        )

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _restrict_problem_to_skill(
    problem: Mapping[str, Any],
    selected: Mapping[str, Any],
) -> dict[str, Any]:
    op_ids = list(selected.get("operation_ids") or [])
    wanted = set(op_ids)
    raw_caps = problem.get("capabilities")
    if not isinstance(raw_caps, Sequence) or isinstance(raw_caps, (str, bytes)):
        raise SelfImprovementError("PROBLEM_CAPABILITIES_INVALID")
    by_id = {
        _s(cap.get("id")): deepcopy(dict(cap))
        for cap in raw_caps
        if isinstance(cap, Mapping) and _s(cap.get("id")) in wanted
    }
    if set(by_id) != wanted:
        raise SelfImprovementError("ACTIVE_SKILL_CAPABILITY_SET_CHANGED")
    derived = deepcopy(dict(problem))
    derived["capabilities"] = [by_id[cid] for cid in op_ids]
    derived["max_solver_cycles"] = min(
        int(problem.get("max_solver_cycles", 256)),
        len(op_ids) + 2,
    )
    return derived


def _record_reuse_result(
    *,
    state_path: str | Path,
    skill_id: str,
    success: bool,
    effect_may_have_occurred: bool,
    failure_output: Mapping[str, Any] | None = None,
    retry_context: Mapping[str, Any] | None = None,
    counterexample_scope_id: str | None = None,
) -> dict[str, Any]:
    state = load_state(state_path)
    row = dict(state["reuse"].get(skill_id) or {})
    row["attempts"] = int(row.get("attempts", 0)) + 1
    row["successes"] = int(row.get("successes", 0)) + (1 if success else 0)
    row["pre_effect_failures"] = int(row.get("pre_effect_failures", 0)) + (
        1 if (not success and not effect_may_have_occurred) else 0
    )
    row["effectful_failures"] = int(row.get("effectful_failures", 0)) + (
        1 if (not success and effect_may_have_occurred) else 0
    )
    state["reuse"][skill_id] = row

    quarantined = False
    if not success and effect_may_have_occurred:
        record = state["skills"].get(skill_id)
        if isinstance(record, dict):
            record["active"] = False
            record["quarantined"] = True
            record["quarantine_reason"] = "VERIFIED_REUSE_ROUTE_EFFECTFUL_FAILURE_COUNTEREXAMPLE"
            raw_skill = record.get("skill")
            source_scopes = (
                set(_items(raw_skill.get("source_scopes")))
                if isinstance(raw_skill, Mapping)
                else set()
            )
            relation = (
                _s(raw_skill.get("scope_relation"))
                if isinstance(raw_skill, Mapping)
                else ""
            )
            counterexample_scope = _s(counterexample_scope_id)
            scope_contraction_safe = (
                relation == "PROVEN_SUPERSET"
                and bool(counterexample_scope)
                and counterexample_scope not in source_scopes
            )
            if scope_contraction_safe:
                prior = set(_items(record.get("generalization_counterexample_scopes")))
                prior.add(counterexample_scope)
                record["generalization_counterexample_scopes"] = sorted(prior)
                record["generalization_repromotion_blocked"] = True
            family = record.get("family_id")
            frontier = state["pareto_frontiers"].get(family)
            if isinstance(frontier, Sequence) and not isinstance(frontier, (str, bytes)):
                state["pareto_frontiers"][family] = [
                    sid for sid in frontier if sid != skill_id
                ]
            quarantined = True
            diagnosis = (
                _diagnose_failure(failure_output)
                if isinstance(failure_output, Mapping)
                else {}
            )
            retry_capsule_sha256 = None
            if isinstance(retry_context, Mapping):
                retry_capsule_sha256 = _make_retry_capsule(retry_context)["sha256"]
            _enqueue_improvement(
                state,
                kind="REVERIFY_QUARANTINED_SKILL",
                priority=5,
                identity={
                    "skill_id": skill_id,
                    "family_id": _s(family),
                },
                payload={
                    "skill_id": skill_id,
                    "family_id": _s(family),
                    "reason": record["quarantine_reason"],
                    "failure_fingerprint": diagnosis.get("failure_fingerprint"),
                    "failure_status": diagnosis.get("status"),
                    "repair_class": diagnosis.get("repair_class"),
                    "falsified_capability_ids": diagnosis.get("falsified_capability_ids", []),
                    "counterexamples": diagnosis.get("counterexamples", []),
                    "retry_capsule_sha256": retry_capsule_sha256,
                    "counterexample_scope_id": counterexample_scope or None,
                    "source_scopes": sorted(source_scopes),
                    "previous_scope_relation": relation or None,
                    "scope_contraction_safe": scope_contraction_safe,
                    "required_result": (
                        "INDEPENDENT_REVERIFICATION_OR_VERIFIED_FAMILY_REPLACEMENT"
                    ),
                },
            )

    _refresh_stats(state)
    _write_state(state, state_path)
    return {
        "skill_id": skill_id,
        "quarantined": quarantined,
        "next_improvement_action": _next_improvement_from_state(state),
    }

def _post_execution_independent_verification(
    out: Mapping[str, Any],
    *,
    problem: Mapping[str, Any],
    prior_verified_episode_records: Sequence[Mapping[str, Any]],
    generalization_episode_records: Sequence[Mapping[str, Any]] = (),
    repo_root: str | Path,
    episode_verification_provider=None,
    skill_verification_provider=None,
    effect_root: str | Path | None = None,
) -> dict[str, Any]:
    """Complete the independent-verifier handshake after execution, without replay.

    Providers only supply content-addressed bindings. Existing authenticators remain
    the authority. This permits autonomous two-phase verification while keeping the
    executor unable to certify its own episode or skill.
    """
    result = deepcopy(dict(out))
    if result.get("pass") is not True:
        return result

    episode = result.get("current_episode")
    if (
        result.get("current_episode_verified") is not True
        and isinstance(episode, Mapping)
        and episode_verification_provider is not None
    ):
        trace = result.get("trace")
        if not isinstance(trace, Sequence) or isinstance(trace, (str, bytes)):
            result["post_execution_episode_verification_error"] = "TRACE_INVALID"
        else:
            request = {
                "kind": "EPISODE_VERIFICATION",
                "problem": deepcopy(dict(problem)),
                "episode": deepcopy(dict(episode)),
                "trace": deepcopy(list(trace)),
                "fact_capsule_head_hash": _s(result.get("state_capsule_head_hash")),
                "value_capsule_head_hash": _s(result.get("value_capsule_head_hash")),
                "effect_root": str(effect_root) if effect_root is not None else None,
            }
            try:
                binding = episode_verification_provider(deepcopy(request))
                if binding is not None and not isinstance(binding, Mapping):
                    raise SelfImprovementError("EPISODE_VERIFICATION_PROVIDER_RESULT_INVALID")
                if isinstance(binding, Mapping):
                    auth = authenticate_episode_verification(
                        binding,
                        problem=problem,
                        episode=episode,
                        trace=trace,
                        fact_capsule_head_hash=request["fact_capsule_head_hash"],
                        value_capsule_head_hash=request["value_capsule_head_hash"],
                        repo_root=repo_root,
                    )
                    result["episode_verification_authentication"] = auth
                    if auth.get("pass") is True:
                        result["current_episode"] = auth["authenticated_episode"]
                        result["current_episode_verified"] = True
                        result["episode_verification_error"] = None
                    else:
                        result["episode_verification_error"] = _s(auth.get("reason"))
                else:
                    result["post_execution_episode_verification_error"] = (
                        "EPISODE_VERIFICATION_PROVIDER_RETURNED_NO_BINDING"
                    )
            except Exception as exc:
                result["post_execution_episode_verification_error"] = (
                    type(exc).__name__ + ":" + str(exc)
                )

    candidate = result.get("skill_candidate")
    if result.get("current_episode_verified") is True:
        current_episode = result.get("current_episode")
        current_program = (
            _s(current_episode.get("program_sha256"))
            if isinstance(current_episode, Mapping) else ""
        )
        current_scope = (
            _s(current_episode.get("scope_id"))
            if isinstance(current_episode, Mapping) else ""
        )

        pool: list[Mapping[str, Any]] = []
        seen_episode_ids: set[str] = set()
        candidate_errors: list[str] = []
        for record in [
            *prior_verified_episode_records,
            *generalization_episode_records,
        ]:
            if not isinstance(record, Mapping):
                continue
            rid = _s(record.get("episode_id"))
            if not rid or rid in seen_episode_ids:
                continue
            # Cross-context generalization is proposed only from independently
            # verified executions of the exact same executable program. Scope
            # widening still grants zero authority until the independent skill
            # verifier proves the claimed scope relation.
            if current_program and _s(record.get("program_sha256")) != current_program:
                continue
            verdict = reauthenticate_episode_record(record, repo_root=repo_root)
            if verdict.get("pass") is not True:
                candidate_errors.append(
                    "PRIOR_EPISODE_REAUTHENTICATION_FAILED:"
                    + _s(verdict.get("reason"))
                )
                continue
            authenticated = verdict["authenticated_episode"]
            seen_episode_ids.add(rid)
            pool.append(authenticated)

        if isinstance(current_episode, Mapping) and pool:
            try:
                generalized = induce_candidate([*pool, current_episode])
                existing_scopes = (
                    set(_items(candidate.get("source_scopes")))
                    if isinstance(candidate, Mapping) else set()
                )
                generalized_scopes = set(_items(generalized.get("source_scopes")))
                if (
                    not isinstance(candidate, Mapping)
                    or len(generalized_scopes) > len(existing_scopes)
                    or (
                        len(generalized_scopes) == len(existing_scopes)
                        and len(_items(generalized.get("source_episode_ids")))
                        > len(_items(candidate.get("source_episode_ids")))
                    )
                ):
                    candidate = generalized
                    result["skill_candidate"] = candidate
                    result["skill_candidate_error"] = None
                    result["cross_scope_candidate_induced"] = (
                        len(generalized_scopes) > 1
                    )
                    result["candidate_source_scopes"] = sorted(generalized_scopes)
            except ExecutableSkillProgramError as exc:
                candidate_errors.append(str(exc))

        if candidate_errors and not isinstance(result.get("skill_candidate"), Mapping):
            result["skill_candidate_error"] = ";".join(sorted(set(candidate_errors)))


    candidate = result.get("skill_candidate")
    if (
        isinstance(candidate, Mapping)
        and not isinstance(result.get("verified_executable_skill"), Mapping)
        and skill_verification_provider is not None
    ):
        request = {
            "kind": "SKILL_VERIFICATION",
            "candidate": deepcopy(dict(candidate)),
            "current_episode": deepcopy(dict(result.get("current_episode") or {})),
            "supported_scope_predicates": [VERIFIED_SUPERSET_SCOPE_PREDICATE],
        }
        try:
            binding = skill_verification_provider(deepcopy(request))
            if binding is not None and not isinstance(binding, Mapping):
                raise SelfImprovementError("SKILL_VERIFICATION_PROVIDER_RESULT_INVALID")
            if isinstance(binding, Mapping):
                auth = authenticate_skill_verification(
                    candidate,
                    binding,
                    repo_root=repo_root,
                )
                result["skill_verification_authentication"] = auth
                if auth.get("pass") is True:
                    verified = auth["verified_skill"]
                    result["verified_executable_skill"] = verified
                    result["verified_skill_reuse_authorized"] = bool(
                        verified.get("reuse_authorized")
                    )
                else:
                    result["skill_verification_error"] = _s(auth.get("reason"))
            else:
                result["post_execution_skill_verification_error"] = (
                    "SKILL_VERIFICATION_PROVIDER_RETURNED_NO_BINDING"
                )
        except Exception as exc:
            result["post_execution_skill_verification_error"] = (
                type(exc).__name__ + ":" + str(exc)
            )

    if isinstance(result.get("verified_executable_skill"), Mapping):
        result["status"] = "SOLVED__VERIFIED_EXECUTABLE_SKILL_READY"
    elif isinstance(result.get("skill_candidate"), Mapping):
        result["status"] = "SOLVED__SKILL_CANDIDATE_READY"
    elif result.get("current_episode_verified") is True:
        result["status"] = "SOLVED__VERIFIED_EPISODE"
    return result


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
    episode_verification_provider=None,
    skill_verification_provider=None,
    resume_binding: Mapping[str, Any] | None = None,
    known_absent_invalidators: Sequence[str] = (),
    proposal_provider=None,
    capability_expander=None,
    proposal_provider_id: str = "HOST_GENERAL_COGNITION_SUBSTRATE",
    proposal_provider_max_candidates: int = 4,
    capability_expander_id: str = "HOST_CAPABILITY_EXPANDER",
    max_capability_expansions: int = 4,
    retry_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run verified learned routes first, then fall back safely to full V12 search.

    A learned route is used only as a planning compression overlay. V12 still
    authenticates semantics and verifies execution. If a reuse attempt fails after
    any verified effect may already have occurred, full-search fallback is blocked
    to prevent blind replay.
    """
    eid = _s(episode_id)
    scope = _s(scope_id)
    if not eid or not scope:
        raise SelfImprovementError("EPISODE_ID_AND_SCOPE_REQUIRED")

    state = load_state(state_path)
    prior = _prior_verified_episodes(state, scope_id=scope, episode_id=eid)
    generalization_prior = _all_prior_verified_episodes(state, episode_id=eid)
    selected = _select_active_skill(
        problem,
        state,
        scope_id=scope,
        repo_root=repo_root,
        known_absent_invalidators=known_absent_invalidators,
    )
    reuse_attempt = None

    if selected is not None:
        learned_problem = _restrict_problem_to_skill(problem, selected)
        reuse_out = solver_v12.run(
            learned_problem,
            proposal_packets=proposal_packets,
            repo_root=repo_root,
            resolved_semantics_bindings=resolved_semantics_bindings,
            effect_root=effect_root,
            episode_id=eid,
            scope_id=scope,
            episode_verification_binding=episode_verification_binding,
            prior_verified_episode_records=prior,
            skill_verification_binding=skill_verification_binding,
            resume_binding=resume_binding,
        proposal_provider=proposal_provider,
        capability_expander=capability_expander,
        proposal_provider_id=proposal_provider_id,
        proposal_provider_max_candidates=proposal_provider_max_candidates,
        capability_expander_id=capability_expander_id,
        max_capability_expansions=max_capability_expansions,
        )
        effectful = _effect_may_have_occurred(reuse_out)
        reuse_learning = _record_reuse_result(
            state_path=state_path,
            skill_id=selected["skill_id"],
            success=reuse_out.get("pass") is True,
            effect_may_have_occurred=effectful,
            failure_output=(reuse_out if reuse_out.get("pass") is not True else None),
            retry_context=retry_context,
            counterexample_scope_id=scope,
        )
        reuse_attempt = {
            "skill_id": selected["skill_id"],
            "operation_ids": list(selected["operation_ids"]),
            "pass": reuse_out.get("pass") is True,
            "effect_may_have_occurred": effectful,
            "status": reuse_out.get("status"),
            "reuse_learning": reuse_learning,
        }
        if reuse_out.get("pass") is True:
            reuse_out = _post_execution_independent_verification(
                reuse_out,
                problem=learned_problem,
                prior_verified_episode_records=prior,
                generalization_episode_records=generalization_prior,
                repo_root=repo_root,
                episode_verification_provider=episode_verification_provider,
                skill_verification_provider=skill_verification_provider,
                effect_root=effect_root,
            )
            integrated = integrate_solver_output(
                reuse_out,
                state_path=state_path,
                repo_root=repo_root,
                retry_context=retry_context,
                verification_problem=learned_problem,
                verification_effect_root=effect_root,
            )
            return {
                "schema": SCHEMA,
                "status": integrated["status"],
                "pass": True,
                "solver_output": reuse_out,
                "learning": integrated,
                "prior_verified_episode_count_used": len(prior),
                "reuse_first": True,
                "reused_skill_id": selected["skill_id"],
                "reuse_attempt": reuse_attempt,
                "fallback_used": False,
                "terminal_authority": False,
            }
        if effectful:
            integrated = integrate_solver_output(
                reuse_out,
                state_path=state_path,
                repo_root=repo_root,
                retry_context=retry_context,
                verification_problem=learned_problem,
                verification_effect_root=effect_root,
            )
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED__LEARNED_ROUTE_EFFECT_OCCURRED__NO_BLIND_REPLAY",
                "pass": False,
                "solver_output": reuse_out,
                "learning": integrated,
                "prior_verified_episode_count_used": len(prior),
                "reuse_first": True,
                "reused_skill_id": selected["skill_id"],
                "reuse_attempt": reuse_attempt,
                "fallback_used": False,
                "fallback_blocked_effect_may_have_occurred": True,
                "terminal_authority": False,
            }

    out = solver_v12.run(
        problem,
        proposal_packets=proposal_packets,
        repo_root=repo_root,
        resolved_semantics_bindings=resolved_semantics_bindings,
        effect_root=effect_root,
        episode_id=eid,
        scope_id=scope,
        episode_verification_binding=episode_verification_binding,
        prior_verified_episode_records=prior,
        skill_verification_binding=skill_verification_binding,
        resume_binding=resume_binding,
        proposal_provider=proposal_provider,
        capability_expander=capability_expander,
        proposal_provider_id=proposal_provider_id,
        proposal_provider_max_candidates=proposal_provider_max_candidates,
        capability_expander_id=capability_expander_id,
        max_capability_expansions=max_capability_expansions,
    )
    out = _post_execution_independent_verification(
        out,
        problem=problem,
        prior_verified_episode_records=prior,
        generalization_episode_records=generalization_prior,
        repo_root=repo_root,
        episode_verification_provider=episode_verification_provider,
        skill_verification_provider=skill_verification_provider,
        effect_root=effect_root,
    )
    integrated = integrate_solver_output(
        out,
        state_path=state_path,
        repo_root=repo_root,
        retry_context=retry_context,
        verification_problem=problem,
        verification_effect_root=effect_root,
    )
    return {
        "schema": SCHEMA,
        "status": integrated["status"],
        "pass": out.get("pass") is True,
        "solver_output": out,
        "learning": integrated,
        "prior_verified_episode_count_used": len(prior),
        "reuse_first": selected is not None,
        "reused_skill_id": selected["skill_id"] if selected is not None else None,
        "reuse_attempt": reuse_attempt,
        "fallback_used": selected is not None,
        "terminal_authority": False,
    }
