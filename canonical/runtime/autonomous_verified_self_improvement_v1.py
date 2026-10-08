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
from canonical.runtime import universal_verified_adaptive_solver_v12 as solver_v12

SCHEMA = "PROJECT_BRAIN_AUTONOMOUS_VERIFIED_SELF_IMPROVEMENT_V1"
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

    return {
        "capability_id": skill_id,
        "reusable_capability": True,
        "independently_verified": True,
        "capability": len(_items(skill.get("postconditions"))),
        "generalization": 2 if relation == "PROVEN_SUPERSET" else 1,
        "reliability": len(source_ids),
        "latency": len(steps),
        "compute": len(steps),
        "memory": io_width,
        "incremental_spend_usd": 0,
    }


def _diagnose_failure(out: Mapping[str, Any]) -> dict[str, Any]:
    status = _s(out.get("status"))
    reason = _s(out.get("reason") or out.get("failure_class"))
    joined = (status + " " + reason).upper()

    if any(token in joined for token in (
        "NO_VERIFIED_CAPABILITY",
        "UNREACHABLE_TARGET",
        "CAPABILITY_OR_TASK_CONTRACT_GAP",
        "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP",
    )):
        repair = "ACQUIRE_COMPOSE_OR_INVENT_VERIFIABLE_CAPABILITY"
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
        + (1 if isinstance(previous, Mapping) and previous.get("status") == "RESOLVED" else 0)
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


def record_success_observation(
    out: Mapping[str, Any],
    *,
    surface: str,
    state_path: str | Path = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    """Durably retain a compact success pointer when no verified episode exists.

    Plain runtime successes are not promoted. They become explicit work to build a
    verifiable episode adapter, preventing successful experience from silently
    disappearing while preserving the independent-verification boundary.
    """
    if not isinstance(out, Mapping) or out.get("pass") is not True:
        raise SelfImprovementError("SUCCESS_OBSERVATION_REQUIRES_PASSING_OUTPUT")
    name = _s(surface) or "UNSPECIFIED_RUNTIME_SURFACE"
    core = {
        "surface": name,
        "schema": _s(out.get("schema")) or None,
        "status": _s(out.get("status")) or None,
        "output_sha256": _sha(out),
    }
    oid = "observation:" + _sha(core)
    state = load_state(state_path)
    previous = state["observations"].get(oid)
    state["observations"][oid] = {
        **core,
        "observation_id": oid,
        "count": int(previous.get("count", 0)) + 1 if isinstance(previous, Mapping) else 1,
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
        "improvement_work_id": work_id,
        "next_improvement_action": _next_improvement_from_state(state),
        "permanent_reuse_authorized": False,
        "terminal_authority": False,
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
    retry_context: Mapping[str, Any] | None = None,
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
            if isinstance(prior_capsule, Mapping) and prior_capsule.get("resolved") is True:
                capsule["resolved"] = True
                capsule["resolved_by"] = prior_capsule.get("resolved_by")
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
                },
            )

    skill_admission = None
    active_skill_id = None
    verified_skill = out.get("verified_executable_skill")
    skill_candidate = out.get("skill_candidate")
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

        existing_ids = list(state["pareto_frontiers"].get(family, []))
        frontier_rows = []
        for old_sid in existing_ids:
            old = state["skills"].get(old_sid)
            if not isinstance(old, Mapping):
                continue
            old_skill = old.get("skill")
            if isinstance(old_skill, Mapping):
                frontier_rows.append(_skill_pareto_row(old_sid, old_skill))

        skill_admission = update_pareto_frontier(frontier_rows, row)
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
        state["skills"][sid] = record

        if skill_admission.get("admitted") is True:
            active_skill_id = sid
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
    known_absent_invalidators: Sequence[str] = (),
) -> dict[str, Any] | None:
    """Select a durable verified skill only when its exact executable skeleton fits.

    V1 reuse is deliberately conservative:
    - current scope must be one of the independently verified source scopes;
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
        if scope_id not in _items(skill.get("source_scopes")):
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

        metrics = record.get("pareto_metrics")
        if not isinstance(metrics, Mapping):
            metrics = {}
        rank = (
            int(metrics.get("latency", len(op_ids))),
            int(metrics.get("compute", len(op_ids))),
            int(metrics.get("memory", 0)),
            -int(metrics.get("reliability", 0)),
            str(sid),
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
            family = record.get("family_id")
            frontier = state["pareto_frontiers"].get(family)
            if isinstance(frontier, Sequence) and not isinstance(frontier, (str, bytes)):
                state["pareto_frontiers"][family] = [
                    sid for sid in frontier if sid != skill_id
                ]
            quarantined = True
            _enqueue_improvement(
                state,
                kind="REVERIFY_QUARANTINED_SKILL",
                priority=5,
                identity={"skill_id": skill_id},
                payload={
                    "skill_id": skill_id,
                    "reason": record["quarantine_reason"],
                    "required_result": "INDEPENDENT_REVERIFICATION_OR_REPLACEMENT",
                },
            )

    _refresh_stats(state)
    _write_state(state, state_path)
    return {
        "skill_id": skill_id,
        "quarantined": quarantined,
        "next_improvement_action": _next_improvement_from_state(state),
    }

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
    selected = _select_active_skill(
        problem,
        state,
        scope_id=scope,
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
            integrated = integrate_solver_output(reuse_out, state_path=state_path, retry_context=retry_context)
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
            integrated = integrate_solver_output(reuse_out, state_path=state_path, retry_context=retry_context)
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
    integrated = integrate_solver_output(out, state_path=state_path, retry_context=retry_context)
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
