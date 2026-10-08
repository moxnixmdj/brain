"""R3 verified compounding coordinator around the owned V12 solver.

An episode is NOT learning authority. Only the existing content-addressed
episode authenticator may admit it. A skill is NOT executable authority.
Only the existing separate skill authenticator may enable planner-only reuse.

Persistent state is a local checkout journal; it becomes durable across
ephemeral workers only when an authorized operator commits/synchronizes it.
This module never self-issues verification receipts or promotion authority.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable, Mapping

from canonical.runtime import universal_verified_adaptive_solver_v12 as solver
from canonical.runtime import executable_skill_program_v7 as skill_program
from canonical.runtime.universal_solver_episode_verification_authenticator_v1 import (
    reauthenticate_record,
    authenticate as authenticate_episode_verification,
)
from canonical.runtime.executable_skill_verification_authenticator_v1 import (
    authenticate_and_verify,
)

SCHEMA = "PROJECT_BRAIN_AUTONOMOUS_VERIFIED_COMPOUNDING_V1"


class CompoundingError(ValueError):
    pass


def _canon(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(data: Any) -> str:
    return sha256(_canon(data)).hexdigest()


def _state_path(repo_root: str | Path, state_path: str | Path) -> Path:
    root = Path(repo_root).resolve()
    path = Path(state_path)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    if not path.is_relative_to(root) or ".git" in path.relative_to(root).parts:
        raise CompoundingError("STATE_PATH_OUTSIDE_REPOSITORY")
    return path


def _empty() -> dict[str, Any]:
    return {"schema": SCHEMA, "episodes": [], "candidates": [],
            "skills": [], "failures": []}


def load_state(*, repo_root: str | Path, state_path: str | Path) -> tuple[dict[str, Any], bytes | None]:
    path = _state_path(repo_root, state_path)
    original = path.read_bytes() if path.is_file() else None
    try:
        state = json.loads(original) if original is not None else _empty()
    except (ValueError, TypeError) as exc:
        raise CompoundingError("LEARNING_STATE_JSON_INVALID") from exc
    if not isinstance(state, dict) or state.get("schema") != SCHEMA:
        raise CompoundingError("LEARNING_STATE_SCHEMA_INVALID")
    for key in ("episodes", "candidates", "skills", "failures"):
        if not isinstance(state.get(key), list):
            raise CompoundingError("LEARNING_STATE_INVALID:" + key)
    seen_episodes: set[str] = set()
    for ep in state["episodes"]:
        verdict = reauthenticate_record(ep, repo_root=repo_root)
        if verdict.get("pass") is not True:
            raise CompoundingError("STORED_EPISODE_REAUTH_FAILED:" + str(verdict.get("reason")))
        eid = ep.get("episode_id")
        if not isinstance(eid, str) or eid in seen_episodes:
            raise CompoundingError("STORED_EPISODE_ID_DUPLICATED")
        seen_episodes.add(eid)
    stored_candidates = {}
    for candidate in state["candidates"]:
        if not isinstance(candidate, dict) or candidate.get("candidate_only") is not True:
            raise CompoundingError("STORED_CANDIDATE_INVALID")
        source_ids = candidate.get("source_episode_ids", [])
        if not set(source_ids).issubset(seen_episodes):
            raise CompoundingError("STORED_CANDIDATE_SOURCE_NOT_ADMITTED")
        expected = skill_program.candidate_digest(
            source_episode_ids=source_ids, steps=candidate.get("steps"),
            preconditions=candidate.get("preconditions", []),
            postconditions=candidate.get("postconditions", []),
            invalidators=candidate.get("invalidators", []),
        )
        if expected != candidate.get("candidate_sha256"):
            raise CompoundingError("STORED_CANDIDATE_DIGEST_DRIFT")
        if expected in stored_candidates:
            raise CompoundingError("STORED_CANDIDATE_DUPLICATED")
        stored_candidates[expected] = candidate
    seen_skills: set[str] = set()
    for item in state["skills"]:
        if not isinstance(item, Mapping):
            raise CompoundingError("STORED_SKILL_INVALID")
        candidate = item.get("candidate")
        binding = item.get("binding")
        if not isinstance(candidate, Mapping) or not isinstance(binding, Mapping):
            raise CompoundingError("STORED_SKILL_BINDING_INVALID")
        sha = candidate.get("candidate_sha256")
        if sha not in stored_candidates or stored_candidates[sha] != candidate:
            raise CompoundingError("STORED_SKILL_CANDIDATE_NOT_ADMITTED")
        verdict = authenticate_and_verify(candidate, binding, repo_root=repo_root)
        if verdict.get("pass") is not True:
            raise CompoundingError("STORED_SKILL_REAUTH_FAILED:" + str(verdict.get("reason")))
        if sha in seen_skills:
            raise CompoundingError("STORED_SKILL_DUPLICATED")
        seen_skills.add(sha)
    return state, original


def _save(state: Mapping[str, Any], *, original: bytes | None,
          repo_root: str | Path, state_path: str | Path) -> None:
    path = _state_path(repo_root, state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise CompoundingError("CONCURRENT_LEARNING_WRITER") from exc
    os.close(fd)
    temporary = None
    try:
        observed = path.read_bytes() if path.is_file() else None
        if observed != original:
            raise CompoundingError("LEARNING_JOURNAL_CHANGED__RETRY_FRESH")
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent,
                                         prefix=".r3-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(_canon(state) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def _induce_all(state: dict[str, Any]) -> int:
    groups: dict[str, list[Mapping[str, Any]]] = {}
    for ep in state["episodes"]:
        key = _sha(skill_program.normalize_steps(ep["steps"]))
        groups.setdefault(key, []).append(ep)
    present = {x["candidate_sha256"] for x in state["candidates"]}
    added = 0
    for group in groups.values():
        episodes = sorted(group, key=lambda x: x["episode_id"])
        if len(episodes) < 2:
            continue
        # Stable two-episode basis avoids generating a new candidate on every run.
        candidate = skill_program.induce_candidate(episodes[:2])
        if candidate["candidate_sha256"] not in present:
            state["candidates"].append(candidate)
            present.add(candidate["candidate_sha256"])
            added += 1
    return added


def reconcile(*, repo_root: str | Path, state_path: str | Path,
              candidate_verification_bindings: Mapping[str, Mapping[str, Any]] | None = None,
              candidate_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
              new_episode: Mapping[str, Any] | None = None,
              failure: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Ingest a solver episode or failure; promote only independently verified skills."""
    state, original = load_state(repo_root=repo_root, state_path=state_path)
    if new_episode is not None:
        verdict = reauthenticate_record(new_episode, repo_root=repo_root)
        if verdict.get("pass") is not True:
            raise CompoundingError("NEW_EPISODE_REAUTH_FAILED:" + str(verdict.get("reason")))
        matched = [x for x in state["episodes"]
                   if x["episode_id"] == new_episode["episode_id"]]
        if matched and matched[0] != new_episode:
            raise CompoundingError("EPISODE_ID_CONFLICT")
        if not matched:
            state["episodes"].append(dict(new_episode))
    if failure is not None:
        # Failures are observations, not independently established causal theories.
        state["failures"].append({
            "status": str(failure.get("status", "UNKNOWN"))[:180],
            "trace_sha256": _sha(failure.get("trace", [])),
            "attempts_sha256": _sha(failure.get("attempts", [])),
            "interpretation": "UNDIAGNOSED_OBSERVATION_ONLY",
        })
        state["failures"] = state["failures"][-64:]
    new_candidates = _induce_all(state)
    bindings = dict(candidate_verification_bindings or {})
    verified = {item["candidate"]["candidate_sha256"] for item in state["skills"]}
    promoted = 0
    for candidate in state["candidates"]:
        digest = candidate["candidate_sha256"]
        if digest in verified:
            continue
        if digest not in bindings and candidate_verifier is not None:
            offered = candidate_verifier(candidate)
            if offered is not None:
                if not isinstance(offered, Mapping):
                    raise CompoundingError("CANDIDATE_VERIFIER_BINDING_INVALID")
                bindings[digest] = offered
        if digest not in bindings:
            continue
        verdict = authenticate_and_verify(candidate, bindings[digest], repo_root=repo_root)
        if verdict.get("pass") is not True:
            raise CompoundingError("CANDIDATE_VERIFICATION_FAILED:" + str(verdict.get("reason")))
        state["skills"].append({"candidate": candidate, "binding": dict(bindings[digest])})
        verified.add(digest)
        promoted += 1
    if _canon(state) != _canon(load_state(repo_root=repo_root, state_path=state_path)[0]):
        _save(state, original=original, repo_root=repo_root, state_path=state_path)
    return {
        "schema": SCHEMA, "status": "RECONCILED__GATED_COMPOUNDING",
        "pass": True, "episodes_retained": len(state["episodes"]),
        "candidates_retained": len(state["candidates"]),
        "verified_skills_retained": len(state["skills"]),
        "new_candidates": new_candidates, "new_verified_skills": promoted,
        "failure_observations_retained": len(state["failures"]),
        "independent_receipts_still_required": True,
        "learning_state_is_checkout_local_until_committed": True,
        "terminal_authority": False, "ownership_credit_delta": 0,
    }


def run(problem: Mapping[str, Any], *, repo_root: str | Path,
        state_path: str | Path = "canonical/learning/R3_VERIFIED_COMPOUNDING_STATE.json",
        episode_id: str, scope_id: str,
        episode_verification_binding: Mapping[str, Any] | None = None,
        candidate_verification_bindings: Mapping[str, Mapping[str, Any]] | None = None,
        episode_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
        candidate_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
        **solver_kwargs: Any) -> dict[str, Any]:
    """Execute V12, retain only authenticated learning, and reuse verified macros."""
    state, _ = load_state(repo_root=repo_root, state_path=state_path)
    if any(ep["episode_id"] == episode_id for ep in state["episodes"]):
        raise CompoundingError("EPISODE_ID_ALREADY_RECORDED")
    forbidden = {"prior_verified_episode_records", "verified_skill_records",
                 "skill_verification_binding"}
    if forbidden.intersection(solver_kwargs):
        raise CompoundingError("USE_R3_LEARNING_BINDINGS_NOT_RAW_SOLVER_BYPASS")
    prior = [ep for ep in state["episodes"] if ep.get("scope_id") == scope_id]
    result = solver.run(
        problem, repo_root=repo_root, episode_id=episode_id, scope_id=scope_id,
        episode_verification_binding=episode_verification_binding,
        prior_verified_episode_records=prior,
        verified_skill_records=list(state["skills"]),
        **solver_kwargs,
    )
    ep = (result.get("current_episode")
          if result.get("pass") is True and result.get("current_episode_verified") is True
          else None)
    late_auth = None
    if (ep is None and result.get("pass") is True and episode_verifier is not None
            and isinstance(result.get("current_episode"), Mapping)):
        offered = episode_verifier(result)
        if offered is not None:
            late_auth = authenticate_episode_verification(
                offered, problem=result.get("expanded_problem", problem),
                episode=result["current_episode"], trace=result.get("trace", []),
                fact_capsule_head_hash=result.get("state_capsule_head_hash", ""),
                value_capsule_head_hash=result.get("value_capsule_head_hash", ""),
                repo_root=repo_root,
            )
            if late_auth.get("pass") is True:
                ep = late_auth["authenticated_episode"]
    learning = reconcile(
        repo_root=repo_root, state_path=state_path,
        new_episode=ep,
        failure=result if result.get("pass") is not True else None,
        candidate_verification_bindings=candidate_verification_bindings,
        candidate_verifier=candidate_verifier,
    )
    return {**result, "r3_learning": learning,
            "r3_post_execution_episode_authentication": late_auth,
            "r3_episode_admitted": ep is not None}
