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
from canonical.runtime import universal_verified_adaptive_solver_v10 as solver_v10
from canonical.runtime.universal_solver_episode_verification_authenticator_v1 import (
    reauthenticate_record as reauthenticate_episode_record,
)
from canonical.runtime.executable_skill_verification_authenticator_v1 import (
    authenticate_and_verify as authenticate_skill_verification,
)
from canonical.runtime.verified_skill_macro_planner_v1 import plan_with_skills

SCHEMA = "PROJECT_BRAIN_AUTONOMOUS_VERIFIED_SELF_IMPROVEMENT_V1"
STATE_SCHEMA = "PROJECT_BRAIN_SELF_IMPROVEMENT_STATE_V1"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = ROOT / "canonical/runtime/SELF_IMPROVEMENT_STATE_V1.json"


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


def _empty_state() -> dict[str, Any]:
    return {
        "schema": STATE_SCHEMA,
        "version": 1,
        "episodes": {},
        "skills": {},
        "pareto_frontiers": {},
        "failures": {},
        "stats": {
            "verified_episode_count": 0,
            "verified_skill_count": 0,
            "active_skill_count": 0,
            "failure_class_count": 0,
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
    for key in ("episodes", "skills", "pareto_frontiers", "failures", "stats"):
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
    """Return an exact executable-behavior family.

    Pareto replacement is intentionally limited to the same verified executable
    program and the same declared contract. Different implementations that merely
    share an output label are not comparable without a separate complete
    comparison proof.
    """
    post = _items(skill.get("postconditions"))
    steps = skill.get("steps")
    if not post:
        raise SelfImprovementError("VERIFIED_SKILL_POSTCONDITIONS_EMPTY")
    if not isinstance(steps, Sequence) or isinstance(steps, (str, bytes)) or not steps:
        raise SelfImprovementError("VERIFIED_SKILL_STEPS_INVALID")
    return "family:" + _sha({
        "steps": list(steps),
        "preconditions": _items(skill.get("preconditions")),
        "postconditions": post,
        "invalidators": _items(skill.get("invalidators")),
        "source_scopes": _items(skill.get("source_scopes")),
    })


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


def _refresh_stats(state: dict[str, Any]) -> None:
    state["stats"] = {
        "verified_episode_count": len(state["episodes"]),
        "verified_skill_count": len(state["skills"]),
        "active_skill_count": sum(
            1 for row in state["skills"].values()
            if isinstance(row, Mapping) and row.get("active") is True
        ),
        "failure_class_count": len(state["failures"]),
    }


def _learning_fail(
    reason: str,
    state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED__LEARNING_AUTHORITY_NOT_PROVED",
        "pass": False,
        "reason": reason,
        "state_stats": deepcopy(dict((state or {}).get("stats") or {})),
        "permanent_reuse_authorized": False,
        "terminal_authority": False,
    }


def _reauthenticate_skill_record(
    record: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise SelfImprovementError("SKILL_RECORD_INVALID")
    candidate = record.get("candidate")
    stored_skill = record.get("skill")
    binding = record.get("verification_binding")
    if not isinstance(candidate, Mapping):
        raise SelfImprovementError("SKILL_RECORD_CANDIDATE_MISSING")
    if not isinstance(stored_skill, Mapping):
        raise SelfImprovementError("SKILL_RECORD_VERIFIED_SKILL_MISSING")
    if not isinstance(binding, Mapping):
        raise SelfImprovementError("SKILL_RECORD_VERIFICATION_BINDING_MISSING")
    verdict = authenticate_skill_verification(
        candidate,
        binding,
        repo_root=repo_root,
    )
    if verdict.get("pass") is not True:
        raise SelfImprovementError(
            "SKILL_RECORD_REAUTHENTICATION_FAILED:"
            + str(verdict.get("reason") or "UNKNOWN")
        )
    verified = verdict.get("verified_skill")
    if not isinstance(verified, Mapping):
        raise SelfImprovementError("SKILL_RECORD_REAUTHENTICATED_SKILL_MISSING")
    if _canon(verified) != _canon(stored_skill):
        raise SelfImprovementError("SKILL_RECORD_BYTES_OR_SEMANTICS_DRIFT")
    return deepcopy(dict(verified))


def integrate_solver_output(
    out: Mapping[str, Any],
    *,
    state_path: str | Path = DEFAULT_STATE_PATH,
    repo_root: str | Path = ROOT,
) -> dict[str, Any]:
    """Persist only re-authenticated learning and update exact-behavior Pareto state.

    The input mapping is never trusted merely because it contains fields named
    "verified". Episode and skill authority is reconstructed from the stored
    content-addressed receipt pairs before any reusable state mutation.
    """
    if not isinstance(out, Mapping):
        raise SelfImprovementError("SOLVER_OUTPUT_NOT_OBJECT")
    state = load_state(state_path)
    if out.get("schema") != solver_v10.SCHEMA:
        return _learning_fail("SOLVER_OUTPUT_SCHEMA_INVALID", state)

    if out.get("pass") is not True:
        diagnosis = _diagnose_failure(out)
        fid = diagnosis["failure_fingerprint"]
        previous = state["failures"].get(fid)
        count = int(previous.get("count", 0)) + 1 if isinstance(previous, Mapping) else 1
        state["failures"][fid] = {
            **diagnosis,
            "count": count,
            "authority": "DIAGNOSTIC_ONLY__NOT_CAPABILITY_PROMOTION_EVIDENCE",
        }
        _refresh_stats(state)
        _write_state(state, state_path)
        return {
            "schema": SCHEMA,
            "status": "FAILURE_DIAGNOSED__REPAIR_NOT_SELF_CERTIFIED",
            "pass": False,
            "diagnosis": diagnosis,
            "state_stats": deepcopy(state["stats"]),
            "permanent_reuse_authorized": False,
            "terminal_authority": False,
        }

    authenticated_episode = None
    if out.get("current_episode_verified") is True:
        ep = out.get("current_episode")
        if not isinstance(ep, Mapping):
            return _learning_fail("VERIFIED_EPISODE_MISSING", state)
        verdict = reauthenticate_episode_record(ep, repo_root=repo_root)
        if verdict.get("pass") is not True:
            return _learning_fail(
                "EPISODE_REAUTHENTICATION_FAILED:"
                + str(verdict.get("reason") or "UNKNOWN"),
                state,
            )
        authenticated_episode = verdict.get("authenticated_episode")
        if not isinstance(authenticated_episode, Mapping):
            return _learning_fail("REAUTHENTICATED_EPISODE_MISSING", state)

    authenticated_skill = None
    authenticated_candidate = None
    authenticated_skill_binding = None
    verified_skill = out.get("verified_executable_skill")
    if out.get("verified_skill_reuse_authorized") is True:
        candidate = out.get("skill_candidate")
        auth = out.get("skill_verification_authentication")
        if not isinstance(candidate, Mapping):
            return _learning_fail("VERIFIED_SKILL_CANDIDATE_MISSING", state)
        if not isinstance(verified_skill, Mapping):
            return _learning_fail("VERIFIED_SKILL_MISSING", state)
        if not isinstance(auth, Mapping) or auth.get("pass") is not True:
            return _learning_fail("SKILL_AUTHENTICATION_RECORD_MISSING", state)
        receipt = auth.get("receipt")
        verification = auth.get("verification")
        if not isinstance(receipt, Mapping) or not isinstance(verification, Mapping):
            return _learning_fail("SKILL_AUTHENTICATION_BINDING_MISSING", state)
        binding = {
            "receipt": deepcopy(dict(receipt)),
            "verification": deepcopy(dict(verification)),
        }
        verdict = authenticate_skill_verification(
            candidate,
            binding,
            repo_root=repo_root,
        )
        if verdict.get("pass") is not True:
            return _learning_fail(
                "SKILL_REAUTHENTICATION_FAILED:"
                + str(verdict.get("reason") or "UNKNOWN"),
                state,
            )
        authenticated_skill = verdict.get("verified_skill")
        if not isinstance(authenticated_skill, Mapping):
            return _learning_fail("REAUTHENTICATED_SKILL_MISSING", state)
        if _canon(authenticated_skill) != _canon(verified_skill):
            return _learning_fail("SOLVER_SKILL_DOES_NOT_MATCH_REAUTHENTICATED_SKILL", state)
        authenticated_candidate = deepcopy(dict(candidate))
        authenticated_skill_binding = binding

    episode_added = False
    episode_key = None
    if authenticated_episode is not None:
        episode_key = _episode_key(authenticated_episode)
        episode_added = episode_key not in state["episodes"]
        state["episodes"][episode_key] = deepcopy(dict(authenticated_episode))

    skill_admission = None
    active_skill_id = None
    if authenticated_skill is not None:
        sid = _skill_id(authenticated_skill)
        family = _family_id(authenticated_skill)
        row = _skill_pareto_row(sid, authenticated_skill)

        existing_ids = list(state["pareto_frontiers"].get(family, []))
        frontier_rows = []
        for old_sid in existing_ids:
            old = state["skills"].get(old_sid)
            if not isinstance(old, Mapping):
                return _learning_fail("PARETO_FRONTIER_REFERENCES_MISSING_SKILL:" + str(old_sid), state)
            try:
                old_skill = _reauthenticate_skill_record(old, repo_root=repo_root)
            except SelfImprovementError as exc:
                return _learning_fail(str(exc), state)
            frontier_rows.append(_skill_pareto_row(str(old_sid), old_skill))

        if sid in existing_ids:
            skill_admission = {
                "admitted": True,
                "reason": "ALREADY_ACTIVE_REAUTHENTICATED_SKILL",
                "removed_dominated": [],
                "frontier": frontier_rows,
            }
        else:
            skill_admission = update_pareto_frontier(frontier_rows, row)

        record = {
            "candidate": authenticated_candidate,
            "skill": deepcopy(dict(authenticated_skill)),
            "verification_binding": authenticated_skill_binding,
            "family_id": family,
            "pareto_metrics": {
                **row,
                "metric_basis": (
                    "EXACT_EXECUTABLE_PROGRAM_FAMILY;"
                    "GENERALIZATION_FROM_VERIFIED_SCOPE_RELATION;"
                    "RELIABILITY_PROXY_IS_INDEPENDENT_VERIFIED_EPISODE_COUNT"
                ),
            },
            "active": bool(skill_admission.get("admitted")),
            "dominated_by": skill_admission.get("dominated_by"),
            "compression": {
                "source_episode_count": len(_items(authenticated_skill.get("source_episode_ids"))),
                "stored_program_step_count": len(list(authenticated_skill.get("steps") or [])),
                "repeated_program_copies_eliminated": max(
                    0, len(_items(authenticated_skill.get("source_episode_ids"))) - 1
                ),
            },
        }
        state["skills"][sid] = record

        if skill_admission.get("admitted") is True:
            active_skill_id = sid
            admitted_ids = [
                str(x.get("capability_id"))
                for x in skill_admission.get("frontier", [])
                if isinstance(x, Mapping) and x.get("capability_id")
            ]
            if sid not in admitted_ids:
                admitted_ids.append(sid)
            state["pareto_frontiers"][family] = sorted(set(admitted_ids))
            for removed in skill_admission.get("removed_dominated", []) or []:
                if removed in state["skills"] and isinstance(state["skills"][removed], dict):
                    state["skills"][removed]["active"] = False
                    state["skills"][removed]["dominated_by"] = sid

    _refresh_stats(state)
    _write_state(state, state_path)

    if active_skill_id:
        status = "VERIFIED_SKILL_DURABLY_ADMITTED_FOR_REUSE"
    elif out.get("skill_candidate") is not None:
        status = "SKILL_CANDIDATE_AWAITS_INDEPENDENT_VERIFICATION"
    elif authenticated_episode is not None:
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
        "permanent_reuse_authorized": active_skill_id is not None,
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


def _active_verified_skills(
    state: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> list[dict[str, Any]]:
    verified = []
    for sid, record in sorted((state.get("skills") or {}).items()):
        if not isinstance(record, Mapping) or record.get("active") is not True:
            continue
        skill = _reauthenticate_skill_record(record, repo_root=repo_root)
        if _skill_id(skill) != sid:
            raise SelfImprovementError("ACTIVE_SKILL_ID_DRIFT:" + str(sid))
        verified.append(skill)
    return verified


def _preferred_skill_plan(
    problem: Mapping[str, Any],
    verified_skills: Sequence[Mapping[str, Any]],
    *,
    active_invalidators: Sequence[str] = (),
) -> tuple[dict[str, Any] | None, list[str]]:
    if not verified_skills:
        return None, []
    preview = plan_with_skills(
        problem,
        verified_skills,
        active_invalidators=active_invalidators,
    )
    if preview.get("pass") is not True:
        return preview, []
    used = list(preview.get("used_verified_skill_macros") or [])
    if not used:
        return preview, []
    preferred = [str(x) for x in preview.get("expanded_execution_plan") or []]
    return preview, preferred


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
    active_invalidators: Sequence[str] = (),
) -> dict[str, Any]:
    """Run V10 with authenticated durable experience and verified-skill reuse.

    Active stored skills are independently re-authenticated on every load. Their
    macro expansion is used only as a preferred capability order; V10 still
    executes and independently verifies the underlying capabilities and effect
    semantics. No stored skill becomes execution authority by itself.
    """
    eid = _s(episode_id)
    scope = _s(scope_id)
    if not eid or not scope:
        raise SelfImprovementError("EPISODE_ID_AND_SCOPE_REQUIRED")

    state = load_state(state_path)
    try:
        active_skills = _active_verified_skills(state, repo_root=repo_root)
    except SelfImprovementError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__DURABLE_SKILL_REAUTHENTICATION_FAILED",
            "pass": False,
            "reason": str(exc),
            "solver_output": None,
            "learning": _learning_fail(str(exc), state),
            "terminal_authority": False,
        }

    skill_preview, preferred = _preferred_skill_plan(
        problem,
        active_skills,
        active_invalidators=active_invalidators,
    )
    prior = _prior_verified_episodes(state, scope_id=scope, episode_id=eid)
    out = solver_v10.run(
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
        preferred_capability_order=preferred,
    )
    integrated = integrate_solver_output(
        out,
        state_path=state_path,
        repo_root=repo_root,
    )
    return {
        "schema": SCHEMA,
        "status": integrated["status"],
        "pass": out.get("pass") is True and integrated.get("pass") is True,
        "solver_output": out,
        "learning": integrated,
        "prior_verified_episode_count_used": len(prior),
        "active_verified_skill_count_reauthenticated": len(active_skills),
        "skill_plan_preview": skill_preview,
        "preferred_capability_order": preferred,
        "verified_skill_reuse_attempted": bool(preferred),
        "terminal_authority": False,
    }
