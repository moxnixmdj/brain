"""Fail-closed construction audit for one reached escape state.

This adapter does not prove global escape totality. It converts the independently
verified finite reached-state totality certificate into one runtime admission
boundary: an exact state is either certified for all future current-discriminator
outcomes, or the adapter emits the exact uncovered-policy / indistinguishable-
policy-conflict counterexample class that keeps the global invariant open.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from canonical.runtime import reached_escape_finite_totality_certificate_v1 as finite_totality

SCHEMA = "PROJECT_BRAIN_REACHED_ESCAPE_STATE_CONSTRUCTION_AUDIT_V1"


def _base() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "global_escape_progress_totality_proved": False,
        "all_actually_reached_states_certified": False,
        "open_ended_mission_terminal_proved": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }


def audit(state: Mapping[str, Any]) -> dict[str, Any]:
    certificate = finite_totality.certify(state)
    base = _base()

    if certificate.get("pass") is True:
        return {
            **base,
            "pass": True,
            "status": "PASS__REACHED_STATE_FUTURE_TOTALITY_CERTIFIED",
            "admitted_as_certified_reached_state": True,
            "counterexample_class": None,
            "state_id": certificate.get("state_id"),
            "state_sha256": certificate.get("state_sha256"),
            "finite_totality_certificate": deepcopy(certificate),
            "reached_state_future_outcome_totality_proved": True,
        }

    status = str(certificate.get("status") or "")
    if status == "OPEN__REGION_WITHOUT_AUTHENTICATED_SAFE_ADEQUATE_POLICY":
        return {
            **base,
            "pass": False,
            "status": "OPEN__EXACT_REACHED_STATE_CONSTRUCTION_COUNTEREXAMPLE",
            "admitted_as_certified_reached_state": False,
            "counterexample_class": "REGION_WITHOUT_AUTHENTICATED_SAFE_ADEQUATE_POLICY",
            "state_id": certificate.get("state_id"),
            "state_sha256": certificate.get("state_sha256"),
            "uncovered_region_ids": deepcopy(certificate.get("uncovered_region_ids") or []),
            "finite_totality_certificate": deepcopy(certificate),
            "reached_state_future_outcome_totality_proved": False,
        }

    if status == "OPEN__INDISTINGUISHABLE_CLASS_WITHOUT_COMMON_ADEQUATE_POLICY":
        return {
            **base,
            "pass": False,
            "status": "OPEN__EXACT_REACHED_STATE_CONSTRUCTION_COUNTEREXAMPLE",
            "admitted_as_certified_reached_state": False,
            "counterexample_class": "INDISTINGUISHABLE_CLASS_WITHOUT_COMMON_ADEQUATE_POLICY",
            "state_id": certificate.get("state_id"),
            "state_sha256": certificate.get("state_sha256"),
            "indistinguishable_policy_conflict_classes": deepcopy(
                certificate.get("indistinguishable_policy_conflict_classes") or []
            ),
            "finite_totality_certificate": deepcopy(certificate),
            "reached_state_future_outcome_totality_proved": False,
        }

    return {
        **base,
        "pass": False,
        "status": "FAIL_CLOSED__REACHED_STATE_CONSTRUCTION_AUDIT",
        "admitted_as_certified_reached_state": False,
        "counterexample_class": "MALFORMED_OR_UNAUTHENTICATED_REACHED_STATE",
        "reason": certificate.get("reason") or status or "FINITE_TOTALITY_CERTIFICATE_FAILED",
        "finite_totality_certificate": deepcopy(certificate),
        "reached_state_future_outcome_totality_proved": False,
    }


def run(args: Mapping[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    state = args.get("state")
    if isinstance(state, Mapping):
        return audit(state)
    return audit(args)
