"""One-shot verified closure supervisor.

This module composes the existing R3 queue driver into a fixed-point operation.
It grants no new verification, promotion, terminal, or external-reality authority.

The operation stops only when one of these conditions is proved on the current
state/provider frontier:
1. the improvement queue is empty;
2. every remaining work item is non-actionable and the residual class is typed;
3. a proof-carrying information-theoretic certificate proves that the exact
   residual cannot be resolved by any admitted internal route;
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
from canonical.runtime import information_theoretic_externality_gate_v1 as externality_gate
from canonical.runtime import r3_structural_adapter_rule_acquisition_provider_v1 as root1_adapter_acquisition

SCHEMA = "PROJECT_BRAIN_ONE_SHOT_VERIFIED_CLOSURE_V1"

LOAD_BEARING_PATHS = (
    "canonical/runtime/autonomous_verified_self_improvement_v1.py",
    "canonical/runtime/r3_improvement_queue_driver_v1.py",
    "canonical/runtime/r3_structural_adapter_rule_acquisition_provider_v1.py",
    "canonical/runtime/information_theoretic_externality_gate_v1.py",
    "canonical/runtime/live_brain_runtime_v1.py",
    "canonical/runtime/unified_cognitive_fabric_v1.py",
    "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
)

INTERNAL_ROOT1_BLOCKERS = {
    "ROOT1_CONSTRUCTIVE_R3_VERIFICATION_FRONTIER_GAP__NO_BOUND_ACQUISITION_ROUTE",
    "ROOT1_CONSTRUCTIVE_R3_ADAPTER_AUTHORING_GAP__NO_BOUND_ACQUISITION_ROUTE",  # legacy receipts
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


def _compile_r2_acquisition_request(
    cell: Mapping[str, Any],
    *,
    authority_sha256: str | None = None,
) -> dict[str, Any] | None:
    """Preserve one exact pending-acquisition R2 cell as a proof-carrying request."""
    state = str(cell.get("state") or "")
    if "PENDING_ACQUISITION_OR_EXPERIMENT" not in state:
        return None
    cell_id = str(cell.get("cell_id") or "").strip()
    if not cell_id:
        return None
    wake_on = sorted({
        str(x).strip()
        for x in (cell.get("wake_on") or [])
        if str(x).strip()
    })
    payload = {
        "schema": "PROJECT_BRAIN_R2_PENDING_ACQUISITION_REQUEST_V1",
        "cell_id": cell_id,
        "state": state,
        "required_action": cell.get("required_action"),
        "remaining_boundary": cell.get("remaining_boundary"),
        "wake_conditions": wake_on,
        "request_kind": "R2_POLICY_CHANGING_EVIDENCE_OR_SCOPE_CERTIFICATE",
        "proof_or_existing_receipt_precedes_new_reality": True,
        "broad_acquisition_forbidden_without_minimality_proof": True,
        "full_benchmark_default": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if authority_sha256:
        payload["source_r2_authority_sha256"] = authority_sha256
    payload["request_sha256"] = _sha(payload)
    return payload


def _canonical_r2_residual(root: Path) -> dict[str, Any]:
    """Read current canonical R2 truth without inventing closure from an empty R3 queue."""
    target = (root / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json").resolve(strict=True)
    target.relative_to(root)
    raw = target.read_bytes()
    doc = json.loads(raw.decode("utf-8"))
    if not isinstance(doc, Mapping):
        raise OneShotClosureError("CURRENT_R2_AUTHORITY_NOT_OBJECT")

    authority_sha256 = sha256(raw).hexdigest()
    cells = doc.get("current_cell_classifications")
    open_cells: list[dict[str, Any]] = []
    acquisition_requests: list[dict[str, Any]] = []
    if isinstance(cells, Mapping):
        for cell_id, row in cells.items():
            if not isinstance(row, Mapping):
                continue
            state = str(row.get("state") or "")
            if not state.startswith("INTERNAL_UNSOLVED"):
                continue
            cell = {
                "cell_id": str(cell_id),
                "state": state,
                "required_action": row.get("required_action"),
                "remaining_boundary": row.get("remaining_boundary"),
                "wake_on": deepcopy(list(row.get("wake_on") or [])),
                "information_theoretic_externality_proved": (
                    row.get("information_theoretic_externality_proved") is True
                ),
            }
            if isinstance(row.get("decision_relative_sense_control"), Mapping):
                cell["decision_relative_sense_control"] = deepcopy(
                    dict(row["decision_relative_sense_control"])
                )
            request = _compile_r2_acquisition_request(
                cell,
                authority_sha256=authority_sha256,
            )
            if request is not None:
                cell["acquisition_request_sha256"] = request["request_sha256"]
                acquisition_requests.append(request)
            open_cells.append(cell)

    mechanism = doc.get("mechanism_closure")
    positive_coverage_closed = (
        isinstance(mechanism, Mapping)
        and mechanism.get("universal_positive_action_coverage_closed") is True
    )
    raw_hard_frontier = doc.get("remaining_hard_frontier")
    if isinstance(raw_hard_frontier, str):
        remaining_hard_frontier = [raw_hard_frontier] if raw_hard_frontier else []
    elif isinstance(raw_hard_frontier, list):
        remaining_hard_frontier = deepcopy(raw_hard_frontier)
    else:
        remaining_hard_frontier = []
    return {
        "authority_path": "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
        "authority_sha256": authority_sha256,
        "status": doc.get("status"),
        "primary_primitive": doc.get("primary_primitive"),
        "primary_primitive_state": doc.get("primary_primitive_state"),
        "remaining_problem_class": doc.get("remaining_problem_class"),
        "remaining_hard_frontier": remaining_hard_frontier,
        "universal_positive_action_coverage_closed": positive_coverage_closed,
        "current_internal_unsolved_cells": sorted(
            open_cells, key=lambda row: row["cell_id"]
        ),
        "current_internal_unsolved_count": len(open_cells),
        "pending_acquisition_requests": sorted(
            acquisition_requests, key=lambda row: row["cell_id"]
        ),
        "pending_acquisition_request_count": len(acquisition_requests),
    }


def _terminal_checkpoint_snapshot(root: Path) -> dict[str, Any]:
    """Retain checkpoint evidence debt as measurement, not automatic capability debt."""
    target = (root / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json").resolve(strict=True)
    target.relative_to(root)
    raw = target.read_bytes()
    doc = json.loads(raw.decode("utf-8"))
    if not isinstance(doc, Mapping):
        raise OneShotClosureError("CURRENT_TERMINAL_AUTHORITY_NOT_OBJECT")
    live = doc.get("live_truth")
    live = live if isinstance(live, Mapping) else {}
    return {
        "authority_path": "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
        "authority_sha256": sha256(raw).hexdigest(),
        "terminal": live.get("terminal"),
        "family_pass": live.get("frozen_terminal_family_pass_count"),
        "family_open": live.get("frozen_terminal_family_open_count"),
        "atoms_proved": live.get("frozen_atomic_predicates_proved"),
        "atoms_unresolved": live.get("frozen_atomic_predicates_unresolved"),
        "role": "MEASUREMENT_DEBT_ONLY__NOT_AUTOMATIC_CAPABILITY_GAP",
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
                    "blocked_success_work_id": payload.get(
                        "blocked_success_work_id"
                    ),
                    "observation_id": payload.get("observation_id"),
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
        "r2_residual": _canonical_r2_residual(root),
        "terminal_checkpoint": _terminal_checkpoint_snapshot(root),
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
                "internal_unsolved": True,
                "pending_acquisition_or_experiment_required": False,
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
            "internal_unsolved": False,
            "pending_acquisition_or_experiment_required": False,
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
            blocked_id = str(payload.get("blocked_success_work_id") or "")
            blocked_work = pending_by_id.get(blocked_id, {})
            blocked_payload = (
                blocked_work.get("payload")
                if isinstance(blocked_work, Mapping)
                and isinstance(blocked_work.get("payload"), Mapping)
                else {}
            )
            proof_unavailable = (
                blocked_payload.get("proof_available") is False
                or "RETAINED_SUCCESS_PROOF_UNAVAILABLE" in reason
                or "SUCCESS_OBSERVATION_PROOF_UNAVAILABLE" in reason
            )
            if proof_unavailable:
                evidence.add(
                    "NEW_PROOF_BEARING_EXPERIENCE_REQUIRED__SUCCESS_PROOF_UNAVAILABLE"
                )
                continue
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
    elif evidence:
        cls = "PENDING_ACQUISITION_OR_EXPERIMENT"
    else:
        cls = "NONE"
    pending_acquisition = bool(evidence) and not bool(internal)
    return {
        "class": cls,
        "internally_solvable_gap_remaining": bool(internal),
        "internal_unsolved": bool(internal or evidence),
        "pending_acquisition_or_experiment_required": pending_acquisition,
        "external_or_new_evidence_required": pending_acquisition,
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
    externality_certificate_provider: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
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

    if verification_frontier_acquisition_provider is None:
        verification_frontier_acquisition_provider = (
            root1_adapter_acquisition.make_provider(
                repo_root=repo_root,
                state_path=state_path,
            )
        )
        verification_frontier_acquisition_provider_id = (
            "ROOT1_STRUCTURAL_ADAPTER_RULE_ACQUISITION_PROVIDER_V1"
        )

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
            r2_residual = after["payload"].get("r2_residual")
            r2_residual = (
                r2_residual if isinstance(r2_residual, Mapping) else {}
            )
            open_r2 = list(
                r2_residual.get("current_internal_unsolved_cells") or []
            )
            if open_r2:
                residual = classify_residual([], pending=[])
                acquisition_requests = [
                    deepcopy(dict(row))
                    for row in (
                        r2_residual.get("pending_acquisition_requests") or []
                    )
                    if isinstance(row, Mapping)
                ]
                by_cell = {
                    str(row.get("cell_id") or ""): row
                    for row in acquisition_requests
                }
                evidence_blockers: list[str] = []
                internal_blockers: list[str] = []
                for raw_cell in open_r2:
                    if not isinstance(raw_cell, Mapping):
                        continue
                    cell = deepcopy(dict(raw_cell))
                    cell_id = str(cell.get("cell_id") or "")
                    state = str(cell.get("state") or "")
                    if "PENDING_ACQUISITION_OR_EXPERIMENT" in state:
                        if cell_id and cell_id not in by_cell:
                            request = _compile_r2_acquisition_request(
                                cell,
                                authority_sha256=str(
                                    r2_residual.get("authority_sha256") or ""
                                )
                                or None,
                            )
                            if request is not None:
                                by_cell[cell_id] = request
                        evidence_blockers.append(
                            "R2_PENDING_ACQUISITION:" + cell_id
                        )
                    else:
                        internal_blockers.append(
                            "R2_CURRENT_INTERNAL_UNSOLVED:" + cell_id
                        )
                acquisition_requests = [
                    deepcopy(by_cell[key])
                    for key in sorted(by_cell)
                    if key
                ]
                acquisition_only = bool(evidence_blockers) and not bool(
                    internal_blockers
                )
                residual.update({
                    "class": (
                        "PENDING_ACQUISITION_OR_EXPERIMENT"
                        if acquisition_only
                        else "INTERNAL_SOLVABLE_OR_CONSTRUCTIVE_GAP"
                    ),
                    "internally_solvable_gap_remaining": True,
                    "internal_unsolved": True,
                    "pending_acquisition_or_experiment_required": bool(
                        evidence_blockers
                    ),
                    "internal_blockers": sorted(set(internal_blockers)),
                    "evidence_blockers": sorted(set(evidence_blockers)),
                    "r2_acquisition_requests": acquisition_requests,
                    "r2_acquisition_request_count": len(acquisition_requests),
                    "r2_residual": deepcopy(r2_residual),
                })
                return {
                    "schema": SCHEMA,
                    "status": (
                        "OPEN__INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT"
                        if acquisition_only
                        else "OPEN__INTERNAL_UNSOLVED_R2_GAP_REMAINS"
                    ),
                    "pass": False,
                    "fixed_point": True,
                    "closure_class": residual["class"],
                    "initial_frontier_digest": initial["digest"],
                    "final_frontier_digest": after["digest"],
                    "final_state_sha256": after["state_sha256"],
                    "rounds_executed": round_index + 1,
                    "transcript": transcript,
                    "residual": residual,
                    "verified_goal_satisfied_or_irreducible_external_only": False,
                    "internal_improvement_queue_closed": True,
                    "irreducible_external_information_proved": False,
                    "terminal_authority": False,
                }
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
                "verified_goal_satisfied_or_irreducible_external_only": False,
                "internal_improvement_queue_closed": True,
                "irreducible_external_information_proved": False,
                "terminal_authority": False,
            }

        if not changed and int(drained.get("progress_count", 0)) == 0:
            residual = classify_residual(blockers, pending=pending)
            internal = residual["internally_solvable_gap_remaining"]
            bounded_historical_certificate = None
            historical_failure_state_certificate = None
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

                historical_failure_state_certificate = (
                    historical_failure.certify_pending_set(
                        pending,
                        state_path=state_path,
                        repo_root=repo_root,
                    )
                )
                if historical_failure_state_certificate.get("pass") is True:
                    residual["historical_replay_information_absence_proved"] = True
                    residual["historical_replay_information_certificate"] = deepcopy(
                        historical_failure_state_certificate
                    )
                    residual["historical_replay_information_boundary"] = (
                        "EXACT_HISTORICAL_FAILURE_REPLAY_CONTEXT_IS_ABSENT_FROM_"
                        "CURRENT_DURABLE_R3_STATE__THIS_IS_SUPPORTING_EVIDENCE_ONLY_"
                        "AND_DOES_NOT_PROVE_INFORMATION_THEORETIC_EXTERNALITY"
                    )

            externality_certificate = None
            externality_provider_error = None
            if (
                not internal
                and residual.get("external_or_new_evidence_required") is True
                and externality_certificate_provider is not None
            ):
                request = {
                    "schema": SCHEMA,
                    "request": "PROVE_INFORMATION_THEORETIC_EXTERNALITY",
                    "pending": deepcopy(list(pending)),
                    "residual": deepcopy(residual),
                    "bounded_historical_evidence_certificate": deepcopy(
                        bounded_historical_certificate
                    ),
                    "historical_failure_state_certificate": deepcopy(
                        historical_failure_state_certificate
                    ),
                }
                try:
                    candidate = externality_certificate_provider(request)
                    if isinstance(candidate, Mapping):
                        externality_certificate = deepcopy(dict(candidate))
                except Exception as exc:
                    externality_provider_error = type(exc).__name__ + ":" + str(exc)

            externality_verification = externality_gate.verify_certificate(
                externality_certificate,
                pending=pending,
            )
            residual["externality_verification"] = deepcopy(
                externality_verification
            )
            if externality_provider_error is not None:
                residual["externality_provider_error"] = externality_provider_error

            external_proved = (
                externality_verification.get(
                    "irreducible_external_information_proved"
                )
                is True
            )
            residual["irreducible_external_information_proved"] = external_proved
            if external_proved:
                residual["irreducible_external_certificate"] = deepcopy(
                    externality_certificate
                )
            elif not internal:
                internal = True
                if residual.get("pending_acquisition_or_experiment_required") is True:
                    residual["class"] = "INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT"
                else:
                    residual["class"] = "INTERNAL_UNSOLVED__EXTERNALITY_NOT_PROVED"
                residual["internally_solvable_gap_remaining"] = True
                residual["internal_unsolved"] = True
                residual["external_or_new_evidence_required"] = False
                blockers_now = set(residual.get("internal_blockers") or [])
                blockers_now.add(
                    "EXTERNALITY_NOT_PROVED__CONTINUE_INTERNAL_SEARCH_SYNTHESIS_OR_BYPASS"
                )
                residual["internal_blockers"] = sorted(blockers_now)

            if internal and residual.get("pending_acquisition_or_experiment_required") is True:
                status = "OPEN__INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT"
            elif internal:
                status = "OPEN__INTERNAL_UNSOLVED_GAP_REMAINS"
            elif external_proved:
                status = "VERIFIED_FIXED_POINT__PROVED_INFORMATION_THEORETICALLY_EXTERNAL"
            else:
                status = "OPEN__INTERNAL_UNSOLVED_GAP_REMAINS"
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
                "historical_failure_state_certificate": deepcopy(
                    historical_failure_state_certificate
                ),
                "information_theoretic_externality_verification": deepcopy(
                    externality_verification
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
