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
from typing import Any, Callable, Mapping, Sequence

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
        "reuse": {},
        "expanded_capabilities": {},
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
    state.setdefault("reuse", {})
    state.setdefault("expanded_capabilities", {})
    for key in (
        "episodes",
        "skills",
        "pareto_frontiers",
        "failures",
        "reuse",
        "expanded_capabilities",
        "stats",
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
    The ordinary V10 effect semantics and execution verification still run.
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
) -> None:
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
    _write_state(state, state_path)


def _task_contract_key(problem: Mapping[str, Any]) -> str:
    task_id = _s(problem.get("task_id"))
    if not task_id:
        raise SelfImprovementError("TASK_ID_REQUIRED_FOR_EXPANSION_CACHE")
    return "task:" + _sha(
        {
            "task_id": task_id,
            "initial_facts": _items(problem.get("initial_facts")),
            "target_effects": _items(problem.get("target_effects")),
        }
    )


def _rehydrate_verified_expansions(
    problem: Mapping[str, Any],
    state: Mapping[str, Any],
) -> tuple[dict[str, Any], int, str]:
    """Reattach authenticated V12 graph growth only for the exact task contract."""
    key = _task_contract_key(problem)
    record = state.get("expanded_capabilities", {}).get(key)
    if record is None:
        return deepcopy(dict(problem)), 0, key
    if not isinstance(record, Mapping):
        raise SelfImprovementError("EXPANSION_CACHE_RECORD_INVALID")
    rows = record.get("capabilities", [])
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise SelfImprovementError("EXPANSION_CACHE_CAPABILITIES_INVALID")

    derived = deepcopy(dict(problem))
    raw_caps = derived.get("capabilities")
    if raw_caps is None:
        raw_caps = []
    if not isinstance(raw_caps, list):
        raise SelfImprovementError("PROBLEM_CAPABILITIES_MUST_BE_LIST_FOR_REHYDRATION")
    derived["capabilities"] = raw_caps
    existing = {
        _s(cap.get("id")): cap
        for cap in raw_caps
        if isinstance(cap, Mapping) and _s(cap.get("id"))
    }
    added = 0
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise SelfImprovementError("EXPANSION_CACHE_CAPABILITY_INVALID")
        row = deepcopy(dict(raw))
        cid = _s(row.get("id"))
        if not cid:
            raise SelfImprovementError("EXPANSION_CACHE_CAPABILITY_ID_REQUIRED")
        prior = existing.get(cid)
        if prior is not None:
            if _canon(prior) != _canon(row):
                raise SelfImprovementError(
                    "EXPANSION_CACHE_CAPABILITY_ID_COLLISION:" + cid
                )
            continue
        raw_caps.append(row)
        existing[cid] = row
        added += 1
    return derived, added, key


def _update_authenticated_expansion_cache(
    out: Mapping[str, Any],
    *,
    base_problem: Mapping[str, Any],
    state_path: str | Path,
) -> tuple[int, int]:
    """Persist authenticated V12 growth and evict any later-falsified repair."""
    state = load_state(state_path)
    key = _task_contract_key(base_problem)
    current = state["expanded_capabilities"].get(key)
    existing_rows = []
    if current is not None:
        if not isinstance(current, Mapping):
            raise SelfImprovementError("EXPANSION_CACHE_RECORD_INVALID")
        existing_rows = list(current.get("capabilities") or [])
    existing_by_id = {
        _s(row.get("id")): deepcopy(dict(row))
        for row in existing_rows
        if isinstance(row, Mapping) and _s(row.get("id"))
    }

    falsified = set(_items(out.get("falsified_capability_ids")))
    removed = 0
    for cid in sorted(falsified):
        if cid in existing_by_id:
            del existing_by_id[cid]
            removed += 1

    expanded_ids = [
        cid
        for cid in _items(out.get("expanded_capability_ids"))
        if cid not in falsified
    ]
    added = 0
    if expanded_ids:
        attempts = out.get("capability_expansion_attempts")
        expanded_problem = out.get("expanded_problem")
        if (
            not isinstance(attempts, Sequence)
            or isinstance(attempts, (str, bytes))
            or not isinstance(expanded_problem, Mapping)
        ):
            raise SelfImprovementError("EXPANSION_AUTHENTICATION_EVIDENCE_MISSING")

        admitted: set[str] = set()
        for attempt in attempts:
            if not isinstance(attempt, Mapping):
                continue
            for row in attempt.get("admitted") or []:
                if not isinstance(row, Mapping):
                    continue
                cid = _s(row.get("capability_id"))
                if not cid:
                    continue
                if not isinstance(row.get("effect_semantics_receipt"), Mapping):
                    continue
                if not isinstance(row.get("effect_semantics_verification"), Mapping):
                    continue
                admitted.add(cid)

        if not set(expanded_ids).issubset(admitted):
            raise SelfImprovementError(
                "EXPANDED_CAPABILITY_WITHOUT_AUTHENTICATED_ADMISSION"
            )

        raw_caps = expanded_problem.get("capabilities")
        if not isinstance(raw_caps, Sequence) or isinstance(raw_caps, (str, bytes)):
            raise SelfImprovementError("EXPANDED_PROBLEM_CAPABILITIES_INVALID")
        by_id = {
            _s(row.get("id")): deepcopy(dict(row))
            for row in raw_caps
            if isinstance(row, Mapping) and _s(row.get("id"))
        }

        for cid in expanded_ids:
            row = by_id.get(cid)
            if not isinstance(row, Mapping):
                raise SelfImprovementError(
                    "AUTHENTICATED_EXPANDED_CAPABILITY_ROW_MISSING:" + cid
                )
            if not isinstance(row.get("effect_semantics_binding"), Mapping):
                raise SelfImprovementError(
                    "AUTHENTICATED_EXPANSION_SEMANTICS_BINDING_MISSING:" + cid
                )
            prior = existing_by_id.get(cid)
            if prior is not None:
                if _canon(prior) != _canon(row):
                    raise SelfImprovementError(
                        "EXPANSION_CACHE_AUTHENTICATED_ROW_DRIFT:" + cid
                    )
                continue
            existing_by_id[cid] = deepcopy(dict(row))
            added += 1

    if existing_by_id:
        state["expanded_capabilities"][key] = {
            "task_contract_key": key,
            "capabilities": [
                existing_by_id[cid] for cid in sorted(existing_by_id)
            ],
        }
    else:
        state["expanded_capabilities"].pop(key, None)
    _write_state(state, state_path)
    return added, removed

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
    proposal_provider: Callable[..., Mapping[str, Any] | None] | None = None,
    capability_expander: Callable[..., Mapping[str, Any] | None] | None = None,
    proposal_provider_id: str = "HOST_GENERAL_COGNITION_SUBSTRATE",
    proposal_provider_max_candidates: int = 4,
    capability_expander_id: str = "HOST_CAPABILITY_EXPANDER",
    max_capability_expansions: int = 4,
) -> dict[str, Any]:
    """Run verified learned routes first, then use V12 authenticated repair growth.

    A learned route is used only as a planning compression overlay. V12 still
    authenticates semantics and verifies execution. If a reuse attempt fails after
    any verified effect may already have occurred, full-search fallback is blocked
    to prevent blind replay.
    """
    eid = _s(episode_id)
    scope = _s(scope_id)
    if not eid or not scope:
        raise SelfImprovementError("EPISODE_ID_AND_SCOPE_REQUIRED")

    base_problem = deepcopy(dict(problem))
    state = load_state(state_path)
    working_problem, rehydrated_expansion_count, task_contract_key = (
        _rehydrate_verified_expansions(base_problem, state)
    )
    prior = _prior_verified_episodes(state, scope_id=scope, episode_id=eid)
    selected = _select_active_skill(
        working_problem,
        state,
        scope_id=scope,
        known_absent_invalidators=known_absent_invalidators,
    )
    reuse_attempt = None

    if selected is not None:
        learned_problem = _restrict_problem_to_skill(working_problem, selected)
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
            capability_expander=None,
            proposal_provider_id=proposal_provider_id,
            proposal_provider_max_candidates=proposal_provider_max_candidates,
            capability_expander_id=capability_expander_id,
            max_capability_expansions=0,
        )
        effectful = _effect_may_have_occurred(reuse_out)
        _record_reuse_result(
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
        }
        if reuse_out.get("pass") is True:
            integrated = integrate_solver_output(reuse_out, state_path=state_path)
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
                "rehydrated_expansion_count": rehydrated_expansion_count,
                "persisted_expansion_count": 0,
                "invalidated_expansion_count": 0,
                "task_contract_key": task_contract_key,
                "terminal_authority": False,
            }
        if effectful:
            integrated = integrate_solver_output(reuse_out, state_path=state_path)
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
                "rehydrated_expansion_count": rehydrated_expansion_count,
                "persisted_expansion_count": 0,
                "invalidated_expansion_count": 0,
                "task_contract_key": task_contract_key,
                "terminal_authority": False,
            }

    out = solver_v12.run(
        working_problem,
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
    persisted_expansion_count, invalidated_expansion_count = (
        _update_authenticated_expansion_cache(
            out,
            base_problem=base_problem,
            state_path=state_path,
        )
    )
    integrated = integrate_solver_output(out, state_path=state_path)
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
        "rehydrated_expansion_count": rehydrated_expansion_count,
        "persisted_expansion_count": persisted_expansion_count,
        "invalidated_expansion_count": invalidated_expansion_count,
        "task_contract_key": task_contract_key,
        "capability_expander_enabled": capability_expander is not None,
        "terminal_authority": False,
    }
