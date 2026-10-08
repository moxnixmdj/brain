"""One-shot verified closure supervisor.

This module composes the existing R3 queue driver into a fixed-point operation.
It grants no new verification, promotion, terminal, or external-reality authority.

The operation stops only when one of these conditions is proved on the current
state/provider frontier:
1. the improvement queue is empty;
2. every remaining work item is non-actionable and the residual class is typed;
3. an explicit strict certificate proves the exact residual requires information
   absent from current durable state;
4. a claimed-progress invariant is violated, in which case it fails closed.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_improvement_queue_driver_v1 as r3
from canonical.runtime import r3_historical_evidence_irreducibility_v1 as historical_evidence
from canonical.runtime import r3_historical_failure_irreducibility_v1 as historical_failure

SCHEMA = "PROJECT_BRAIN_ONE_SHOT_VERIFIED_CLOSURE_V1"

LOAD_BEARING_PATHS = (
    "canonical/runtime/autonomous_verified_self_improvement_v1.py",
    "canonical/runtime/r3_improvement_queue_driver_v1.py",
    "canonical/runtime/live_brain_runtime_v1.py",
    "canonical/runtime/unified_cognitive_fabric_v1.py",
    "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
)

INTERNAL_ROOT1_BLOCKERS = {
    "ROOT1_CONSTRUCTIVE_R3_ADAPTER_AUTHORING_GAP__NO_BOUND_ACQUISITION_ROUTE",
    "ROOT1_VERIFICATION_CAPABILITY_ACQUISITION_REQUIRED",
}

EXTERNAL_OR_NEW_EVIDENCE_BLOCKERS = {
    "WAITING_FOR_NEW_INDEPENDENTLY_VERIFIED_EXPERIENCE",
}


class OneShotClosureError(RuntimeError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _safe_file_digest(root: Path, relative: str) -> dict[str, Any]:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise OneShotClosureError("LOAD_BEARING_PATH_INVALID:" + relative)
    target = (root / rel).resolve(strict=True)
    target.relative_to(root)
    raw = target.read_bytes()
    return {
        "path": relative,
        "sha256": sha256(raw).hexdigest(),
        "bytes": len(raw),
    }


def frontier_snapshot(
    *,
    repo_root: str | Path,
    state_path: str | Path,
) -> dict[str, Any]:
    root = Path(repo_root).resolve(strict=True)
    state_target = Path(state_path).resolve(strict=True)
    state_target.relative_to(root)
    state_raw = state_target.read_bytes()
    state = learning.load_state(state_target)
    queue = state.get("improvement_queue", {})
    pending: list[dict[str, Any]] = []
    if isinstance(queue, Mapping):
        for wid, raw in queue.items():
            if not isinstance(raw, Mapping):
                continue
            if raw.get("status") not in {"PENDING", "PARKED"}:
                continue
            payload = raw.get("payload") if isinstance(raw.get("payload"), Mapping) else {}
            pending.append({
                "work_id": str(wid),
                "kind": str(raw.get("kind") or ""),
                "status": str(raw.get("status") or ""),
                "observations": int(raw.get("observations", 0)),
                "last_attempt_observations": raw.get("last_attempt_observations"),
                "last_attempt_provider_id": raw.get("last_attempt_provider_id"),
                "last_attempt_frontier_sha256": raw.get(
                    "last_attempt_frontier_sha256"
                ),
                "last_attempt_status": raw.get("last_attempt_status"),
                "last_attempt_reason": raw.get("last_attempt_reason"),
                "frontier_expansion_work_id": raw.get("frontier_expansion_work_id"),
                "verification_frontier_sha256": raw.get(
                    "verification_frontier_sha256"
                ),
                "adapter_frontier_sha256": raw.get("adapter_frontier_sha256"),
                "verification_authority_sha256": raw.get(
                    "verification_authority_sha256"
                ),
                "payload": {
                    "replayable": payload.get("replayable"),
                    "proof_available": payload.get("proof_available"),
                    "proof_capsule_sha256": payload.get("proof_capsule_sha256"),
                    "replay_capsule_sha256": payload.get("replay_capsule_sha256"),
                    "retry_capsule_sha256": payload.get("retry_capsule_sha256"),
                    "repair_class": payload.get("repair_class"),
                    "required_result": payload.get("required_result"),
                    "surface": payload.get("surface"),
                    "boundary_root": payload.get("boundary_root"),
                    "required_capability_class": payload.get(
                        "required_capability_class"
                    ),
                },
            })
    files = [_safe_file_digest(root, rel) for rel in LOAD_BEARING_PATHS]
    payload = {
        "state_file": {
            "path": state_target.relative_to(root).as_posix(),
            "sha256": sha256(state_raw).hexdigest(),
            "bytes": len(state_raw),
        },
        "files": files,
        "pending": sorted(pending, key=lambda x: (x["kind"], x["work_id"])),
        "stats": deepcopy(state.get("stats", {})),
    }
    return {
        "schema": SCHEMA,
        "digest": _sha(payload),
        "state_sha256": payload["state_file"]["sha256"],
        "payload": payload,
    }


def _extract_blockers(actions: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for action in actions:
        candidates = []
        if isinstance(action.get("blockers"), list):
            candidates.extend(action.get("blockers") or [])
        if isinstance(action.get("blockers_skipped"), list):
            candidates.extend(action.get("blockers_skipped") or [])
        for raw in candidates:
            if not isinstance(raw, Mapping):
                continue
            row = {
                "work_id": str(raw.get("work_id") or ""),
                "kind": str(raw.get("kind") or ""),
                "blocker": str(raw.get("blocker") or ""),
                "boundary_root": raw.get("boundary_root"),
                "required_capability_class": raw.get("required_capability_class"),
                "root1_positive_gap_established": (
                    raw.get("root1_positive_gap_established") is True
                ),
            }
            key = _sha(row)
            if key not in seen:
                seen.add(key)
                out.append(row)
    return out


def classify_residual(
    blockers: list[Mapping[str, Any]],
    *,
    pending: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if not blockers:
        if pending:
            return {
                "class": "UNCLASSIFIED_UNRESOLVED_WORK",
                "internally_solvable_gap_remaining": True,
                "external_or_new_evidence_required": False,
                "irreducible_external_information_proved": False,
                "internal_blockers": [
                    "UNCLASSIFIED_UNRESOLVED_WORK_WITHOUT_BLOCKER_CERTIFICATE"
                ],
                "evidence_blockers": [],
            }
        return {
            "class": "NONE",
            "internally_solvable_gap_remaining": False,
            "external_or_new_evidence_required": False,
            "irreducible_external_information_proved": False,
            "internal_blockers": [],
            "evidence_blockers": [],
        }

    pending_by_id = {
        str(row.get("work_id") or ""): row
        for row in (pending or [])
        if isinstance(row, Mapping)
    }
    internal: set[str] = set()
    evidence: set[str] = set()

    for blocker_row in blockers:
        blocker = str(blocker_row.get("blocker") or "")
        wid = str(blocker_row.get("work_id") or "")
        kind = str(blocker_row.get("kind") or "")
        work = pending_by_id.get(wid, {})
        status = str(work.get("last_attempt_status") or "")
        reason = str(work.get("last_attempt_reason") or "")
        payload = work.get("payload") if isinstance(work.get("payload"), Mapping) else {}

        if blocker in INTERNAL_ROOT1_BLOCKERS:
            internal.add(blocker)
            continue
        if blocker in EXTERNAL_OR_NEW_EVIDENCE_BLOCKERS:
            evidence.add(blocker)
            continue
        if blocker == "FRONTIER_ACQUISITION_ALREADY_ATTEMPTED_FOR_CURRENT_PROVIDER_AND_FRONTIER":
            internal.add("ROOT1_ACQUISITION_EXHAUSTED_ON_CURRENT_PROVIDER_FRONTIER")
            continue
        if blocker != "WORK_ALREADY_ATTEMPTED_FOR_CURRENT_EVIDENCE":
            internal.add(blocker or "UNCLASSIFIED_BLOCKER")
            continue

        if kind == "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE":
            replayable = payload.get("replayable")
            proof_available = payload.get("proof_available")
            replay_capsule = payload.get("replay_capsule_sha256")
            if (
                replayable is False
                and proof_available is not True
                and not replay_capsule
            ) or "SUCCESS_OBSERVATION_NOT_REPLAYABLE" in reason:
                evidence.add(
                    "NEW_EXPERIENCE_REQUIRED__HISTORICAL_SUCCESS_NOT_REPLAYABLE"
                )
                continue
            if (
                status == "IMPROVEMENT_PROVIDER_RETURNED_NO_SUCCESS_ADAPTATION"
                or work.get("frontier_expansion_work_id")
            ):
                internal.add("ROOT1_SUCCESS_ADAPTER_OR_VERIFIER_FRONTIER_GAP")
                continue
            internal.add("UNRESOLVED_SUCCESS_ADAPTATION_GAP")
            continue

        if kind == "REPAIR_FAILURE_CLASS":
            retry_capsule = payload.get("retry_capsule_sha256")
            repair_class = str(payload.get("repair_class") or "")
            if (
                not retry_capsule
                or status == "IMPROVEMENT_REPAIR_BLOCKED__REPLAY_CAPSULE_REQUIRED"
            ):
                evidence.add(
                    "NEW_EXPERIENCE_REQUIRED__HISTORICAL_FAILURE_REPLAY_CAPSULE_MISSING"
                )
                continue
            if (
                repair_class == "ACQUIRE_COMPOSE_OR_INVENT_VERIFIABLE_CAPABILITY"
                or status == "REPAIR_CYCLE_UNRESOLVED_AT_SYNTHESIS"
            ):
                internal.add(
                    "ROOT1_CAPABILITY_ACQUISITION_OR_REPAIR_SYNTHESIS_GAP"
                )
                continue
            internal.add("UNRESOLVED_FAILURE_REPAIR_GAP")
            continue

        internal.add("UNRESOLVED_BACKOFF_GAP:" + (kind or "UNKNOWN"))

    if internal:
        cls = "INTERNAL_SOLVABLE_OR_CONSTRUCTIVE_GAP"
    else:
        cls = "NEW_INFORMATION_OR_EXPERIENCE_REQUIRED"
    return {
        "class": cls,
        "internally_solvable_gap_remaining": bool(internal),
        "external_or_new_evidence_required": bool(evidence) and not bool(internal),
        "irreducible_external_information_proved": False,
        "internal_blockers": sorted(internal),
        "evidence_blockers": sorted(evidence),
    }


def run(
    *,
    repo_root: str | Path,
    state_path: str | Path = learning.DEFAULT_STATE_PATH,
    verification_frontier_acquisition_provider: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ] | None = None,
    verification_frontier_acquisition_provider_id: str = (
        "ONE_SHOT_ROOT1_ACQUISITION_PROVIDER"
    ),
    failure_repair_provider: Callable[
        [Mapping[str, Any]], Mapping[str, Any]
    ] | None = None,
    max_rounds: int = 64,
    max_actions_per_round: int = 32,
) -> dict[str, Any]:
    if (
        isinstance(max_rounds, bool)
        or not isinstance(max_rounds, int)
        or max_rounds < 1
        or max_rounds > 512
    ):
        raise OneShotClosureError("MAX_ROUNDS_INVALID")
    if (
        isinstance(max_actions_per_round, bool)
        or not isinstance(max_actions_per_round, int)
        or max_actions_per_round < 1
        or max_actions_per_round > 32
    ):
        raise OneShotClosureError("MAX_ACTIONS_PER_ROUND_INVALID")

    transcript: list[dict[str, Any]] = []
    initial = frontier_snapshot(repo_root=repo_root, state_path=state_path)
    final = initial
    final_blockers: list[dict[str, Any]] = []

    for round_index in range(max_rounds):
        before = frontier_snapshot(repo_root=repo_root, state_path=state_path)
        drained = r3.drain(
            state_path=state_path,
            repo_root=repo_root,
            failure_repair_provider=failure_repair_provider,
            verification_frontier_acquisition_provider=(
                verification_frontier_acquisition_provider
            ),
            verification_frontier_acquisition_provider_id=(
                verification_frontier_acquisition_provider_id
            ),
            max_actions=max_actions_per_round,
        )
        after = frontier_snapshot(repo_root=repo_root, state_path=state_path)
        actions = [
            deepcopy(dict(x))
            for x in (drained.get("actions") or [])
            if isinstance(x, Mapping)
        ]
        blockers = _extract_blockers(actions)
        changed = before["digest"] != after["digest"]
        claimed_progress = int(drained.get("progress_count", 0)) > 0

        if claimed_progress and not changed:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED__CLAIMED_PROGRESS_WITHOUT_STATE_OR_FRONTIER_CHANGE",
                "pass": False,
                "fixed_point": False,
                "round": round_index,
                "initial_frontier_digest": initial["digest"],
                "initial_state_sha256": initial["state_sha256"],
                "before_frontier_digest": before["digest"],
                "after_frontier_digest": after["digest"],
                "drain_result": deepcopy(dict(drained)),
                "terminal_authority": False,
            }

        transcript.append({
            "round": round_index,
            "before_frontier_digest": before["digest"],
            "after_frontier_digest": after["digest"],
            "frontier_changed": changed,
            "progress_count": int(drained.get("progress_count", 0)),
            "status": drained.get("status"),
            "blockers": blockers,
        })
        final = after
        final_blockers = blockers

        pending = after["payload"]["pending"]
        if not pending:
            return {
                "schema": SCHEMA,
                "status": "VERIFIED_INTERNAL_FIXED_POINT__IMPROVEMENT_QUEUE_EMPTY",
                "pass": True,
                "fixed_point": True,
                "closure_class": "NO_CURRENT_INTERNAL_IMPROVEMENT_WORK_REMAINS",
                "initial_frontier_digest": initial["digest"],
                "final_frontier_digest": after["digest"],
                "final_state_sha256": after["state_sha256"],
                "rounds_executed": round_index + 1,
                "transcript": transcript,
                "residual": classify_residual([], pending=[]),
                "verified_goal_satisfied_or_irreducible_external_only": True,
                "irreducible_external_information_proved": False,
                "terminal_authority": False,
            }

        if not changed and int(drained.get("progress_count", 0)) == 0:
            residual = classify_residual(blockers, pending=pending)
            internal = residual["internally_solvable_gap_remaining"]
            bounded_historical_certificate = None
            strict_external_failure_certificate = None
            if (
                not internal
                and residual.get("external_or_new_evidence_required") is True
            ):
                bounded_historical_certificate = (
                    historical_evidence.certify_pending_set(
                        pending,
                        state_path=state_path,
                        repo_root=repo_root,
                    )
                )
                if bounded_historical_certificate.get("pass") is True:
                    residual["current_evidence_irreducibility_proved"] = True
                    residual["current_evidence_certificate"] = deepcopy(
                        bounded_historical_certificate
                    )
                    residual["current_evidence_boundary"] = (
                        "EXACT_HISTORICAL_OBSERVATIONS_REQUIRE_NEW_INDEPENDENT_"
                        "EVIDENCE_OR_NEW_REPLAYABLE_EXPERIENCE"
                    )

                strict_external_failure_certificate = (
                    historical_failure.certify_pending_set(
                        pending,
                        state_path=state_path,
                        repo_root=repo_root,
                    )
                )
                if strict_external_failure_certificate.get("pass") is True:
                    residual["irreducible_external_information_proved"] = True
                    residual["irreducible_external_certificate"] = deepcopy(
                        strict_external_failure_certificate
                    )
                    residual["irreducible_external_boundary"] = (
                        "EXACT_HISTORICAL_FAILURE_REPLAY_CONTEXT_IS_ABSENT_FROM_"
                        "CURRENT_DURABLE_R3_STATE__NEW_EXTERNAL_REPLAY_INFORMATION_"
                        "OR_NEW_REPLAYABLE_FAILURE_EXPERIENCE_REQUIRED"
                    )
            external_proved = (
                residual.get("irreducible_external_information_proved") is True
            )
            if internal:
                status = "OPEN__INTERNAL_SOLVABLE_GAP_REMAINS"
            elif external_proved:
                status = "VERIFIED_FIXED_POINT__IRREDUCIBLE_EXTERNAL_INFORMATION_REQUIRED"
            else:
                status = "OPEN__NEW_INFORMATION_OR_EXPERIENCE_REQUIRED__IRREDUCIBILITY_NOT_PROVED"
            return {
                "schema": SCHEMA,
                "status": status,
                "pass": (not internal) and external_proved,
                "fixed_point": True,
                "closure_class": residual["class"],
                "initial_frontier_digest": initial["digest"],
                "final_frontier_digest": after["digest"],
                "final_state_sha256": after["state_sha256"],
                "rounds_executed": round_index + 1,
                "transcript": transcript,
                "residual": residual,
                "verified_goal_satisfied_or_irreducible_external_only": (
                    (not internal) and external_proved
                ),
                "irreducible_external_information_proved": external_proved,
                "bounded_historical_evidence_certificate": deepcopy(
                    bounded_historical_certificate
                ),
                "strict_external_failure_certificate": deepcopy(
                    strict_external_failure_certificate
                ),
                "terminal_authority": False,
            }

    residual = classify_residual(
        final_blockers, pending=final["payload"]["pending"]
    )
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED__MAX_ROUNDS_REACHED_BEFORE_FIXED_POINT",
        "pass": False,
        "fixed_point": False,
        "initial_frontier_digest": initial["digest"],
        "initial_state_sha256": initial["state_sha256"],
        "final_frontier_digest": final["digest"],
        "final_state_sha256": final["state_sha256"],
        "rounds_executed": max_rounds,
        "transcript": transcript,
        "residual": residual,
        "terminal_authority": False,
    }
