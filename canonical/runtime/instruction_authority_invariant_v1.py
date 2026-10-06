"""Fail-closed normalized instruction-authority invariant.

This kernel deliberately starts *after* semantic extraction.  It accepts a
normalized requirement graph, a normalized authority state, and a proposed
action.  It proves the deterministic enforcement slice only.

The repaired causal decomposition is:

    critical authority violation
        => semantic extraction error
        OR point-in-time deterministic enforcement error
        OR temporal authorization handoff / linearization error
        OR true execution-route bypass

The pure evaluator below proves only point-in-time normalized eligibility.  It
never returns reusable execution authority.  Consequential effects must pass
through InstructionAuthorityCommitGate, which revalidates the current state at
the commit linearization point, consumes a one-use grant, and executes the
effect while authority-state changes are serialized against that effect.

This module makes no claim that arbitrary natural-language requirements were
normalized correctly and no claim that all execution surfaces are already
routed through the commit gate.
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
import uuid
from typing import Any, Callable, Mapping

from canonical.runtime.requirement_graph_kernel import compile_requirement_contract

SCHEMA = "PROJECT_BRAIN_INSTRUCTION_AUTHORITY_INVARIANT_V1"
GRANT_SCHEMA = "PROJECT_BRAIN_INSTRUCTION_AUTHORITY_GRANT_V1"
COMMIT_SCHEMA = "PROJECT_BRAIN_INSTRUCTION_AUTHORITY_COMMIT_V1"


class AuthorityCommitError(RuntimeError):
    pass


def _digest(value: Any) -> str:
    try:
        raw = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    except Exception as exc:
        raise AuthorityCommitError("AUTHORITY_BINDING_NOT_CANONICAL_JSON") from exc
    return hashlib.sha256(raw).hexdigest()


def _strset(value: Any, field: str, errors: list[str]) -> set[str]:
    if not isinstance(value, list):
        errors.append(field + "_NOT_LIST")
        return set()
    out: set[str] = set()
    for i, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{field}_INVALID:{i}")
            continue
        item = item.strip()
        if item in out:
            errors.append(f"{field}_DUPLICATE:{item}")
        out.add(item)
    return out


def _fail(errors: list[str], *, graph: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "ABSTAIN__FAIL_CLOSED",
        "pass": False,
        "execution_authority": False,
        "point_in_time_authority": False,
        "commit_gate_required": True,
        "errors": sorted(set(errors)),
        "requirement_graph": dict(graph or {}),
        "deterministic_enforcement_error_possible_for_allowed_action": False,
        "semantic_extraction_proved": False,
        "bypass_coverage_proved": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


def evaluate_instruction_action(
    requirements: list[dict[str, Any]],
    state: Mapping[str, Any],
    proposal: Mapping[str, Any],
) -> dict[str, Any]:
    """Return point-in-time eligibility when normalized authority invariants hold.

    This function intentionally never returns durable execution authority.
    Callers must issue and consume a one-use grant through
    InstructionAuthorityCommitGate for consequential effects.

    Required normalized state:
      current_epoch: non-negative int
      active_requirement_ids: exact ids expected in the requirement graph
      superseded_requirement_ids: ids invalidated by requirement change
      authorized_scopes: authority atoms the current instruction permits
      forbidden_scopes: authority atoms the current instruction forbids
      unresolved_authority_questions: unresolved scope/authority ambiguities

    Required proposal:
      action_id: stable non-empty id
      epoch: epoch against which the action was planned
      requirement_ids: normalized active requirements the action depends on
      required_scopes: normalized authority atoms the action would exercise

    Soundness is conditional on semantic normalization being correct and on all
    consequential execution being forced through this function.
    """
    errors: list[str] = []

    if not isinstance(requirements, list):
        return _fail(["REQUIREMENTS_NOT_LIST"])
    if not isinstance(state, Mapping):
        return _fail(["STATE_NOT_OBJECT"])
    if not isinstance(proposal, Mapping):
        return _fail(["PROPOSAL_NOT_OBJECT"])

    active = _strset(state.get("active_requirement_ids"), "ACTIVE_REQUIREMENT_IDS", errors)
    superseded = _strset(
        state.get("superseded_requirement_ids", []),
        "SUPERSEDED_REQUIREMENT_IDS",
        errors,
    )
    authorized = _strset(state.get("authorized_scopes"), "AUTHORIZED_SCOPES", errors)
    forbidden = _strset(state.get("forbidden_scopes", []), "FORBIDDEN_SCOPES", errors)
    unresolved = _strset(
        state.get("unresolved_authority_questions", []),
        "UNRESOLVED_AUTHORITY_QUESTIONS",
        errors,
    )

    epoch = state.get("current_epoch")
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 0:
        errors.append("CURRENT_EPOCH_INVALID")

    action_id = proposal.get("action_id")
    if not isinstance(action_id, str) or not action_id.strip():
        errors.append("ACTION_ID_INVALID")

    proposal_epoch = proposal.get("epoch")
    if not isinstance(proposal_epoch, int) or isinstance(proposal_epoch, bool):
        errors.append("PROPOSAL_EPOCH_INVALID")
    elif isinstance(epoch, int) and proposal_epoch != epoch:
        errors.append("STALE_OR_FUTURE_PROPOSAL_EPOCH")

    proposal_requirements = _strset(
        proposal.get("requirement_ids"),
        "PROPOSAL_REQUIREMENT_IDS",
        errors,
    )
    required_scopes = _strset(
        proposal.get("required_scopes"),
        "PROPOSAL_REQUIRED_SCOPES",
        errors,
    )

    # The normalized requirement substrate itself must be structurally complete.
    graph = compile_requirement_contract(
        requirements,
        expected_required_ids=sorted(active),
    )
    if graph.get("pass") is not True:
        errors.append("REQUIREMENT_GRAPH_FAIL_CLOSED")

    if active & superseded:
        errors.append("ACTIVE_AND_SUPERSEDED_OVERLAP")
    if proposal_requirements - active:
        errors.append(
            "PROPOSAL_REFERENCES_NONACTIVE_REQUIREMENTS:"
            + ",".join(sorted(proposal_requirements - active))
        )
    if proposal_requirements & superseded:
        errors.append(
            "PROPOSAL_REFERENCES_SUPERSEDED_REQUIREMENTS:"
            + ",".join(sorted(proposal_requirements & superseded))
        )

    if unresolved:
        errors.append("UNRESOLVED_AUTHORITY_AMBIGUITY")

    if authorized & forbidden:
        errors.append("AUTHORITY_STATE_CONTRADICTION")

    missing_authority = required_scopes - authorized
    if missing_authority:
        errors.append("REQUIRED_SCOPE_NOT_AUTHORIZED:" + ",".join(sorted(missing_authority)))

    forbidden_exercise = required_scopes & forbidden
    if forbidden_exercise:
        errors.append("FORBIDDEN_SCOPE_REQUESTED:" + ",".join(sorted(forbidden_exercise)))

    if errors:
        return _fail(errors, graph=graph)

    return {
        "schema": SCHEMA,
        "status": "PASS__NORMALIZED_AUTHORITY_INVARIANTS_HOLD",
        "pass": True,
        "execution_authority": False,
        "point_in_time_authority": True,
        "commit_gate_required": True,
        "action_id": action_id.strip(),
        "epoch": epoch,
        "active_requirement_ids": sorted(active),
        "proposal_requirement_ids": sorted(proposal_requirements),
        "authorized_scopes": sorted(authorized),
        "required_scopes": sorted(required_scopes),
        "forbidden_scopes": sorted(forbidden),
        "errors": [],
        "requirement_graph": graph,
        "proved_normalized_enforcement_properties": [
            "ACTION_PLAN_EPOCH_EQUALS_CURRENT_REQUIREMENT_EPOCH",
            "PROPOSAL_REFERENCES_ONLY_ACTIVE_NONSUPERSEDED_REQUIREMENTS",
            "NO_UNRESOLVED_AUTHORITY_AMBIGUITY",
            "EVERY_EXERCISED_SCOPE_IS_EXPLICITLY_AUTHORIZED",
            "NO_EXERCISED_SCOPE_IS_FORBIDDEN",
            "NORMALIZED_REQUIREMENT_GRAPH_FAILS_CLOSED_ON_STRUCTURAL_AMBIGUITY_OR_OMISSION",
        ],
        "deterministic_enforcement_error_possible_for_allowed_action": False,
        "semantic_extraction_proved": False,
        "bypass_coverage_proved": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


class InstructionAuthorityCommitGate:
    """Linearizable one-use commit gate for normalized instruction authority.

    Soundness boundary:
      * all authority-state changes for the claimed surface use advance_requirements;
      * all consequential effects for the claimed surface use commit;
      * semantic normalization remains an upstream obligation.

    The effect callback runs while the gate lock is held.  This is deliberate:
    no requirement/authority epoch transition can interleave between the final
    current-state validation and the consequential effect.
    """

    def __init__(
        self,
        requirements: list[dict[str, Any]],
        state: Mapping[str, Any],
    ) -> None:
        if not isinstance(requirements, list):
            raise AuthorityCommitError("REQUIREMENTS_NOT_LIST")
        if not isinstance(state, Mapping):
            raise AuthorityCommitError("STATE_NOT_OBJECT")
        self._lock = threading.RLock()
        self._requirements = copy.deepcopy(requirements)
        self._state = copy.deepcopy(dict(state))
        self._issued: set[str] = set()
        self._consumed: set[str] = set()
        self._in_commit = False

        initial = evaluate_instruction_action(
            self._requirements,
            self._state,
            {
                "action_id": "__gate_initialization_probe__",
                "epoch": self._state.get("current_epoch"),
                "requirement_ids": list(self._state.get("active_requirement_ids") or []),
                "required_scopes": [],
            },
        )
        if initial.get("pass") is not True:
            raise AuthorityCommitError(
                "INITIAL_AUTHORITY_STATE_INVALID:" + ",".join(initial.get("errors") or [])
            )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._state)

    def issue_grant(
        self,
        proposal: Mapping[str, Any],
        *,
        grant_id: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            if self._in_commit:
                raise AuthorityCommitError("GRANT_ISSUE_DURING_COMMIT_FORBIDDEN")
            decision = evaluate_instruction_action(
                self._requirements,
                self._state,
                proposal,
            )
            if decision.get("pass") is not True:
                return {
                    "schema": GRANT_SCHEMA,
                    "status": "ABSTAIN__FAIL_CLOSED",
                    "pass": False,
                    "execution_authority": False,
                    "commit_gate_required": True,
                    "errors": list(decision.get("errors") or []),
                    "grant": None,
                }

            gid = str(grant_id or uuid.uuid4().hex).strip()
            if not gid:
                raise AuthorityCommitError("GRANT_ID_INVALID")
            if gid in self._issued or gid in self._consumed:
                raise AuthorityCommitError("GRANT_ID_REUSE_FORBIDDEN")

            required_scopes = sorted(
                str(x).strip()
                for x in (proposal.get("required_scopes") or [])
                if isinstance(x, str) and x.strip()
            )
            grant = {
                "schema": GRANT_SCHEMA,
                "unique_grant_id": gid,
                "action_digest": _digest(dict(proposal)),
                "requirement_epoch": self._state.get("current_epoch"),
                "normalized_authority_state_digest": _digest(self._state),
                "requirement_contract_digest": _digest(self._requirements),
                "required_scope_set": required_scopes,
            }
            self._issued.add(gid)
            return {
                "schema": GRANT_SCHEMA,
                "status": "PASS__ONE_USE_GRANT_ISSUED",
                "pass": True,
                "execution_authority": False,
                "point_in_time_authority": True,
                "commit_gate_required": True,
                "errors": [],
                "grant": grant,
            }

    def advance_requirements(
        self,
        requirements: list[dict[str, Any]],
        *,
        active_requirement_ids: list[str],
        authorized_scopes: list[str],
        forbidden_scopes: list[str] | None = None,
        unresolved_authority_questions: list[str] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            if self._in_commit:
                raise AuthorityCommitError(
                    "AUTHORITY_STATE_CHANGE_DURING_COMMIT_FORBIDDEN"
                )
            if not isinstance(requirements, list):
                raise AuthorityCommitError("REQUIREMENTS_NOT_LIST")

            candidate = next_requirement_epoch(
                self._state,
                active_requirement_ids=active_requirement_ids,
                authorized_scopes=authorized_scopes,
                forbidden_scopes=forbidden_scopes,
                unresolved_authority_questions=unresolved_authority_questions,
            )
            graph = compile_requirement_contract(
                requirements,
                expected_required_ids=sorted(
                    str(x).strip()
                    for x in candidate.get("active_requirement_ids") or []
                    if isinstance(x, str) and x.strip()
                ),
            )
            if graph.get("pass") is not True:
                raise AuthorityCommitError("REQUIREMENT_GRAPH_FAIL_CLOSED")

            self._requirements = copy.deepcopy(requirements)
            self._state = copy.deepcopy(candidate)
            return copy.deepcopy(candidate)

    def commit(
        self,
        grant: Mapping[str, Any],
        proposal: Mapping[str, Any],
        effect: Callable[[], Any],
    ) -> dict[str, Any]:
        if not callable(effect):
            raise AuthorityCommitError("EFFECT_NOT_CALLABLE")

        with self._lock:
            if self._in_commit:
                raise AuthorityCommitError("NESTED_COMMIT_FORBIDDEN")
            if not isinstance(grant, Mapping) or grant.get("schema") != GRANT_SCHEMA:
                raise AuthorityCommitError("GRANT_SCHEMA_INVALID")

            gid = str(grant.get("unique_grant_id") or "").strip()
            if not gid or gid not in self._issued:
                raise AuthorityCommitError("GRANT_NOT_ISSUED_BY_GATE")
            if gid in self._consumed:
                raise AuthorityCommitError("GRANT_REPLAY_FORBIDDEN")

            decision = evaluate_instruction_action(
                self._requirements,
                self._state,
                proposal,
            )
            if decision.get("pass") is not True:
                raise AuthorityCommitError(
                    "CURRENT_AUTHORITY_REVALIDATION_FAILED:"
                    + ",".join(decision.get("errors") or [])
                )

            if grant.get("action_digest") != _digest(dict(proposal)):
                raise AuthorityCommitError("GRANT_ACTION_DIGEST_MISMATCH")
            if grant.get("requirement_epoch") != self._state.get("current_epoch"):
                raise AuthorityCommitError("GRANT_EPOCH_MISMATCH")
            if (
                grant.get("normalized_authority_state_digest")
                != _digest(self._state)
            ):
                raise AuthorityCommitError("GRANT_STATE_DIGEST_MISMATCH")
            if (
                grant.get("requirement_contract_digest")
                != _digest(self._requirements)
            ):
                raise AuthorityCommitError("GRANT_REQUIREMENT_DIGEST_MISMATCH")

            required_scopes = sorted(
                str(x).strip()
                for x in (proposal.get("required_scopes") or [])
                if isinstance(x, str) and x.strip()
            )
            if list(grant.get("required_scope_set") or []) != required_scopes:
                raise AuthorityCommitError("GRANT_SCOPE_SET_MISMATCH")

            # Consume before invoking the effect.  A callback failure cannot be
            # retried under the same grant, which removes replay-after-partial-
            # effect ambiguity.
            self._consumed.add(gid)
            self._in_commit = True
            try:
                effect_result = effect()
            finally:
                self._in_commit = False

            return {
                "schema": COMMIT_SCHEMA,
                "status": "PASS__EFFECT_COMMITTED_UNDER_CURRENT_ONE_USE_AUTHORITY",
                "pass": True,
                "execution_authority": True,
                "effect_committed": True,
                "unique_grant_id": gid,
                "requirement_epoch": self._state.get("current_epoch"),
                "normalized_authority_state_digest": _digest(self._state),
                "action_digest": _digest(dict(proposal)),
                "effect_result": effect_result,
                "errors": [],
                "semantic_extraction_proved": False,
                "route_coverage_proved": False,
                "acceptance_credit_delta": 0,
                "family_credit_delta": 0,
                "capability_credit_delta": 0,
                "ownership_credit_delta": 0,
            }


def next_requirement_epoch(
    previous_state: Mapping[str, Any],
    *,
    active_requirement_ids: list[str],
    authorized_scopes: list[str],
    forbidden_scopes: list[str] | None = None,
    unresolved_authority_questions: list[str] | None = None,
) -> dict[str, Any]:
    """Create a requirement-change epoch that invalidates all older proposals."""
    prior = previous_state.get("current_epoch") if isinstance(previous_state, Mapping) else None
    if not isinstance(prior, int) or isinstance(prior, bool) or prior < 0:
        raise ValueError("PREVIOUS_EPOCH_INVALID")

    old_active = {
        str(x).strip()
        for x in (previous_state.get("active_requirement_ids") or [])
        if isinstance(x, str) and str(x).strip()
    }
    new_active = {str(x).strip() for x in active_requirement_ids if str(x).strip()}
    old_superseded = {
        str(x).strip()
        for x in (previous_state.get("superseded_requirement_ids") or [])
        if isinstance(x, str) and str(x).strip()
    }

    return {
        "current_epoch": prior + 1,
        "active_requirement_ids": sorted(new_active),
        "superseded_requirement_ids": sorted(old_superseded | (old_active - new_active)),
        "authorized_scopes": list(authorized_scopes),
        "forbidden_scopes": list(forbidden_scopes or []),
        "unresolved_authority_questions": list(unresolved_authority_questions or []),
    }
