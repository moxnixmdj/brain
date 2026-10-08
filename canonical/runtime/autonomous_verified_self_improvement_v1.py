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


def integrate_solver_output(
    out: Mapping[str, Any],
    *,
    state_path: str | Path = DEFAULT_STATE_PATH,
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
        state["failures"][fid] = {**diagnosis, "count": count}
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

    skill_admission = None
    active_skill_id = None
    verified_skill = out.get("verified_executable_skill")
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
    proposal_provider=None,
    capability_expander=None,
    proposal_provider_id: str = "HOST_GENERAL_COGNITION_SUBSTRATE",
    proposal_provider_max_candidates: int = 4,
    capability_expander_id: str = "HOST_CAPABILITY_EXPANDER",
    max_capability_expansions: int = 4,
) -> dict[str, Any]:
    """Run current V12 using durable prior verified episodes, then integrate the result."""
    eid = _s(episode_id)
    scope = _s(scope_id)
    if not eid or not scope:
        raise SelfImprovementError("EPISODE_ID_AND_SCOPE_REQUIRED")

    state = load_state(state_path)
    prior = _prior_verified_episodes(state, scope_id=scope, episode_id=eid)
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
    integrated = integrate_solver_output(out, state_path=state_path)
    return {
        "schema": SCHEMA,
        "status": integrated["status"],
        "pass": out.get("pass") is True,
        "solver_output": out,
        "learning": integrated,
        "prior_verified_episode_count_used": len(prior),
        "terminal_authority": False,
    }
