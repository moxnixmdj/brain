"""Fail-closed admission for consequential external side effects.

Composes canonical blocker-lease identity with the exact minimum-reality-cut
solver. It prevents a connected-app side effect from duplicating an unresolved
external acquisition merely because it occurs outside the PR lease guard.

This guard grants no execution, acceptance, capability, ownership, or terminal
credit. It only determines whether a proposed external side effect is admissible.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
_MINCUT_PATH = ROOT / "canonical" / "runtime" / "minimum_reality_cut.py"
_spec = importlib.util.spec_from_file_location(
    "project_brain_external_side_effect_minimum_reality_cut",
    _MINCUT_PATH,
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("MINIMUM_REALITY_CUT_LOAD_FAILED")
minimum_reality_cut = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(minimum_reality_cut)

SCHEMA = "PROJECT_BRAIN_EXTERNAL_SIDE_EFFECT_ADMISSION_V1"
_PENDING_STATES = {
    "PENDING",
    "IN_FLIGHT",
    "WAITING_FOR_REPLY",
    "EVENT_WAIT_ONLY",
    "PENDING_OWNER_INFORMATION",
    "SENT_RESPONSE_PENDING",
}


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def blocker_lease_key(
    canonical_generation: str,
    capability_target: str,
    causal_blocker: str,
) -> str:
    parts = [
        str(canonical_generation or "").strip(),
        str(capability_target or "").strip(),
        str(causal_blocker or "").strip(),
    ]
    if not all(parts):
        raise ValueError("BLOCKER_LEASE_IDENTITY_INCOMPLETE")
    return "::".join(parts)


def _string_set(value: Any) -> set[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return set()
    return {str(x).strip() for x in value if str(x).strip()}


def _material_delta_valid(raw: Any) -> tuple[bool, list[str]]:
    if raw is None:
        return False, ["MATERIAL_DELTA_MISSING"]
    if not isinstance(raw, Mapping):
        return False, ["MATERIAL_DELTA_NOT_OBJECT"]
    errors: list[str] = []
    if raw.get("verified") is not True:
        errors.append("MATERIAL_DELTA_NOT_VERIFIED")
    if raw.get("changes_terminal_decision") is not True:
        errors.append("MATERIAL_DELTA_NO_TERMINAL_DECISION_VALUE")
    path = str(raw.get("source_path") or "").strip()
    sha = str(raw.get("source_sha") or "").strip()
    if not path:
        errors.append("MATERIAL_DELTA_SOURCE_PATH_MISSING")
    if len(sha) < 7:
        errors.append("MATERIAL_DELTA_SOURCE_SHA_MISSING")
    new_distinctions = _string_set(raw.get("new_distinctions"))
    new_route = raw.get("new_route_authoritatively_bound") is True
    invalidates_prior_wait = raw.get("prior_wait_invalidated") is True
    if not (new_distinctions or new_route or invalidates_prior_wait):
        errors.append("MATERIAL_DELTA_DOES_NOT_CHANGE_ACTION_BASIS")
    return not errors, errors


def evaluate(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "admitted": False,
            "status": "FAIL_CLOSED__INPUT_NOT_OBJECT",
            "errors": ["INPUT_NOT_OBJECT"],
            "execution_authority": False,
            "terminal_credit_delta": 0,
        }

    errors: list[str] = []
    generation = str(payload.get("canonical_generation") or "").strip()
    target = str(payload.get("capability_target") or "").strip()
    blocker = str(payload.get("causal_blocker") or "").strip()
    try:
        lease = blocker_lease_key(generation, target, blocker)
    except ValueError as exc:
        errors.append(str(exc))
        lease = ""

    proposed = payload.get("proposed_action")
    if not isinstance(proposed, Mapping):
        errors.append("PROPOSED_ACTION_NOT_OBJECT")
        proposed = {}
    action_id = str(proposed.get("action_id") or "").strip()
    if not action_id:
        errors.append("PROPOSED_ACTION_ID_MISSING")
    requested = _string_set(proposed.get("requested_distinctions"))
    if not requested:
        errors.append("PROPOSED_REQUESTED_DISTINCTIONS_EMPTY")

    prior_actions = payload.get("prior_actions", [])
    if not isinstance(prior_actions, list):
        errors.append("PRIOR_ACTIONS_NOT_LIST")
        prior_actions = []

    duplicate_prior: list[dict[str, Any]] = []
    for raw in prior_actions:
        if not isinstance(raw, Mapping):
            errors.append("PRIOR_ACTION_NOT_OBJECT")
            continue
        prior_lease = str(raw.get("blocker_lease_key") or "").strip()
        if not prior_lease:
            try:
                prior_lease = blocker_lease_key(
                    str(raw.get("canonical_generation") or ""),
                    str(raw.get("capability_target") or ""),
                    str(raw.get("causal_blocker") or ""),
                )
            except ValueError:
                continue
        if lease and prior_lease != lease:
            continue
        state = str(raw.get("state") or "").strip().upper()
        awaiting = (
            raw.get("awaiting_external_event") is True
            or state in _PENDING_STATES
        )
        if not awaiting:
            continue
        prior_requested = _string_set(raw.get("requested_distinctions"))
        equivalent = (
            not prior_requested
            or requested <= prior_requested
            or prior_requested <= requested
        )
        if equivalent:
            duplicate_prior.append({
                "action_id": str(raw.get("action_id") or ""),
                "state": state,
                "requested_distinctions": sorted(prior_requested),
                "source_path": raw.get("source_path"),
            })

    delta_ok, delta_errors = _material_delta_valid(payload.get("material_delta"))
    if duplicate_prior and not delta_ok:
        return {
            "schema": SCHEMA,
            "pass": False,
            "admitted": False,
            "status": "BLOCKED__DUPLICATE_EXTERNAL_SIDE_EFFECT__EVENT_WAIT_ONLY",
            "blocker_lease_key": lease,
            "duplicate_prior_actions": duplicate_prior,
            "material_delta_errors": delta_errors,
            "rule": (
                "ONE_UNRESOLVED_EXTERNAL_ACQUISITION_OWNER_PER_CAUSAL_BLOCKER__"
                "NEW_SIDE_EFFECT_REQUIRES_VERIFIED_POLICY_CHANGING_DELTA"
            ),
            "execution_authority": False,
            "acceptance_credit_delta": 0,
            "terminal_credit_delta": 0,
        }

    mincut_input = payload.get("minimum_reality_cut")
    if not isinstance(mincut_input, Mapping):
        errors.append("MINIMUM_REALITY_CUT_INPUT_MISSING")
        cut = None
    else:
        try:
            cut = minimum_reality_cut.solve(deepcopy(dict(mincut_input)))
        except Exception as exc:
            errors.append(
                "MINIMUM_REALITY_CUT_EXCEPTION:"
                + type(exc).__name__
                + ":"
                + str(exc)
            )
            cut = None

    if cut is not None:
        if cut.get("exact_minimum") is not True:
            errors.append("EXACT_MINIMUM_REALITY_CUT_NOT_PROVED")
        selected = set(cut.get("selected_observations") or [])
        if cut.get("rule") == "NO_REALITY_QUERY_REQUIRED":
            errors.append("NO_REALITY_QUERY_REQUIRED")
        elif action_id not in selected:
            errors.append("PROPOSED_ACTION_NOT_IN_EXACT_MINIMUM_REALITY_CUT")

    if errors:
        return {
            "schema": SCHEMA,
            "pass": False,
            "admitted": False,
            "status": "FAIL_CLOSED__EXTERNAL_SIDE_EFFECT_NOT_ADMISSIBLE",
            "blocker_lease_key": lease,
            "errors": sorted(set(errors)),
            "minimum_reality_cut_result": cut,
            "execution_authority": False,
            "acceptance_credit_delta": 0,
            "terminal_credit_delta": 0,
        }

    basis = {
        "blocker_lease_key": lease,
        "action_id": action_id,
        "requested_distinctions": sorted(requested),
        "minimum_reality_cut_result": cut,
        "material_delta": deepcopy(dict(payload.get("material_delta") or {})),
    }
    return {
        "schema": SCHEMA,
        "pass": True,
        "admitted": True,
        "status": "PASS__EXTERNAL_SIDE_EFFECT_ADMISSIBLE",
        "blocker_lease_key": lease,
        "admission_digest": _sha(basis),
        "minimum_reality_cut_result": cut,
        "duplicate_prior_action_count": len(duplicate_prior),
        "material_delta_required": bool(duplicate_prior),
        "material_delta_valid": delta_ok if duplicate_prior else None,
        "execution_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
