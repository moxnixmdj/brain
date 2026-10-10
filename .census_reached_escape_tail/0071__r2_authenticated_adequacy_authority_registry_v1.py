"""Self-authenticating adequacy authority discovery for R2.

Only authorities that recompute scope membership from the raw task source and
bind policy adequacy to repository-owned verified evidence belong here. This
module accepts no caller/provider semantic truth flags and grants no final goal
satisfaction or terminal authority.

A matched authority proves only that one Brain-owned policy/result is adequate
inside that authority's exact source class. R2 must still verify that the
realization satisfies the caller's original goal.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime.p2_authenticated_top_law_route_v1 import (
    execute as execute_p2_top_law,
)
from canonical.runtime.p3_binary_explicit_contract_membership_v1 import (
    compile_membership as compile_p3_binary_membership,
)
from canonical.runtime.p3_binary_explicit_top_law_region_verifier_v1 import (
    verify as verify_p3_binary_region,
)

SCHEMA = "PROJECT_BRAIN_R2_AUTHENTICATED_ADEQUACY_AUTHORITY_REGISTRY_V1"
P2_AUTHORITY_ID = "P2_EXPLICIT_CONTRACT_AUTHENTICATED_TOP_LAW_V1"
P3_BINARY_AUTHORITY_ID = "P3_STRICT_BINARY_AUTHENTICATED_TOP_LAW_V1"
P3_BINARY_POLICY_ID = "P3_BOUND_BINARY_REAL_CONTEXT_GROUNDED_DECISION_TOP_LAW_V1"


class AdequacyAuthorityError(ValueError):
    pass


def _source_bytes(raw_source: str | bytes) -> bytes:
    raw = raw_source.encode("utf-8") if isinstance(raw_source, str) else raw_source
    if not isinstance(raw, bytes) or not raw:
        raise AdequacyAuthorityError("RAW_SOURCE_TEXT_OR_BYTES_REQUIRED")
    return raw


def _unresolved_attempt(
    authority_id: str,
    result: Mapping[str, Any] | None,
    *,
    reason: str | None = None,
) -> dict[str, Any]:
    row = {
        "authority_id": authority_id,
        "matched": False,
        "policy_selection_authorized": False,
        "selected_policy_adequacy_verified": False,
        "terminal_authority": False,
    }
    if isinstance(result, Mapping):
        row["authority_status"] = result.get("status")
        row["authority_pass"] = result.get("pass") is True
        errors = result.get("errors")
        if isinstance(errors, list):
            row["errors"] = deepcopy(errors)
    if reason:
        row["reason"] = reason
    return row


def _p2_candidate(raw_source: str | bytes, source_id: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    try:
        result = execute_p2_top_law(raw_source, source_id=source_id)
    except Exception as exc:
        return None, _unresolved_attempt(
            P2_AUTHORITY_ID,
            None,
            reason=type(exc).__name__ + ":" + str(exc),
        )
    if not isinstance(result, Mapping):
        return None, _unresolved_attempt(
            P2_AUTHORITY_ID, None, reason="AUTHORITY_RESULT_NOT_OBJECT"
        )
    if result.get("pass") is not True:
        return None, _unresolved_attempt(P2_AUTHORITY_ID, result)

    policy_id = result.get("policy_id")
    raw_sha = result.get("raw_source_sha256")
    policy_result = result.get("policy_result")
    adequacy = result.get("policy_adequacy")
    if (
        not isinstance(policy_id, str)
        or not policy_id
        or not isinstance(raw_sha, str)
        or not raw_sha
        or not isinstance(policy_result, Mapping)
        or not isinstance(adequacy, Mapping)
        or adequacy.get("pass") is not True
        or adequacy.get("adequacy_proved") is not True
        or adequacy.get("brain_owned") is not True
        or adequacy.get("load_bearing_constraints_preserved") is not True
        or not isinstance(adequacy.get("membership_recognizer_git_blob_sha"), str)
        or not adequacy.get("membership_recognizer_git_blob_sha")
        or result.get("terminal_authority") is not False
        or policy_result.get("terminal_authority") is not False
    ):
        return None, _unresolved_attempt(
            P2_AUTHORITY_ID,
            result,
            reason="P2_PASS_WITHOUT_REQUIRED_AUTHORITY_BOUNDARIES",
        )

    candidate = {
        "authority_id": P2_AUTHORITY_ID,
        "policy_id": policy_id,
        "raw_source_sha256": raw_sha,
        "scope_membership_verified": True,
        "selected_policy_adequacy_verified": True,
        "policy_selection_authorized": True,
        "policy_result": deepcopy(dict(policy_result)),
        "adequacy_evidence": deepcopy(dict(adequacy)),
        "authority_result": deepcopy(dict(result)),
        "realization": {
            "kind": "AUTHENTICATED_SPECIALIST_POLICY_RESULT",
            "authority_id": P2_AUTHORITY_ID,
            "policy_id": policy_id,
            "raw_source_sha256": raw_sha,
            "policy_result": deepcopy(dict(policy_result)),
        },
        "terminal_authority": False,
    }
    return candidate, {
        "authority_id": P2_AUTHORITY_ID,
        "matched": True,
        "policy_id": policy_id,
        "policy_selection_authorized": True,
        "selected_policy_adequacy_verified": True,
        "terminal_authority": False,
    }


def _p3_binary_candidate(
    raw_source: str | bytes,
    source_id: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    try:
        membership = compile_p3_binary_membership(raw_source, source_id=source_id)
    except Exception as exc:
        return None, _unresolved_attempt(
            P3_BINARY_AUTHORITY_ID,
            None,
            reason=type(exc).__name__ + ":" + str(exc),
        )
    if not isinstance(membership, Mapping):
        return None, _unresolved_attempt(
            P3_BINARY_AUTHORITY_ID,
            None,
            reason="MEMBERSHIP_RESULT_NOT_OBJECT",
        )
    if membership.get("pass") is not True:
        return None, _unresolved_attempt(P3_BINARY_AUTHORITY_ID, membership)

    try:
        region = verify_p3_binary_region()
    except Exception as exc:
        return None, _unresolved_attempt(
            P3_BINARY_AUTHORITY_ID,
            membership,
            reason="REGION_VERIFY_EXCEPTION:" + type(exc).__name__ + ":" + str(exc),
        )
    if not isinstance(region, Mapping) or region.get("pass") is not True:
        return None, _unresolved_attempt(
            P3_BINARY_AUTHORITY_ID,
            region if isinstance(region, Mapping) else membership,
            reason="P3_BINARY_REGION_NOT_INDEPENDENTLY_VERIFIED",
        )
    if (
        region.get("parameterized_D_B_region_candidate") is not True
        or region.get("terminal") is not False
        or region.get("terminal_credit_delta") != 0
    ):
        return None, _unresolved_attempt(
            P3_BINARY_AUTHORITY_ID,
            region,
            reason="P3_BINARY_REGION_AUTHORITY_BOUNDARY_INVALID",
        )

    policy = membership.get("policy_receipt")
    raw_sha = membership.get("raw_source_sha256")
    if (
        not isinstance(policy, Mapping)
        or policy.get("pass") is not True
        or policy.get("bound_cell_required_decision_coverage_complete") is not True
        or policy.get("decision_expression_covered") is not True
        or policy.get("policy_adequacy_authority") is not False
        or policy.get("terminal_authority") is not False
        or not isinstance(policy.get("rendered_text"), str)
        or not str(policy.get("rendered_text")).strip()
        or not isinstance(raw_sha, str)
        or not raw_sha
        or membership.get("selected_class_membership_authenticated") is not True
        or membership.get("membership_self_assertion_permitted") is not False
    ):
        return None, _unresolved_attempt(
            P3_BINARY_AUTHORITY_ID,
            membership,
            reason="P3_BINARY_MEMBERSHIP_OR_POLICY_BOUNDARY_INVALID",
        )

    candidate = {
        "authority_id": P3_BINARY_AUTHORITY_ID,
        "policy_id": P3_BINARY_POLICY_ID,
        "raw_source_sha256": raw_sha,
        "scope_membership_verified": True,
        "selected_policy_adequacy_verified": True,
        "policy_selection_authorized": True,
        "policy_result": deepcopy(dict(policy)),
        "adequacy_evidence": deepcopy(dict(region)),
        "authority_result": {
            "membership": deepcopy(dict(membership)),
            "region_verification": deepcopy(dict(region)),
        },
        "realization": {
            "kind": "AUTHENTICATED_SPECIALIST_GROUNDED_DECISION_EXPRESSION",
            "authority_id": P3_BINARY_AUTHORITY_ID,
            "policy_id": P3_BINARY_POLICY_ID,
            "raw_source_sha256": raw_sha,
            "rendered_text": str(policy["rendered_text"]),
            "policy_result_sha256": "sha256:" + sha256(
                json.dumps(
                    dict(policy),
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                ).encode("utf-8")
            ).hexdigest(),
        },
        "terminal_authority": False,
    }
    return candidate, {
        "authority_id": P3_BINARY_AUTHORITY_ID,
        "matched": True,
        "policy_id": P3_BINARY_POLICY_ID,
        "policy_selection_authorized": True,
        "selected_policy_adequacy_verified": True,
        "terminal_authority": False,
    }


def discover(
    raw_source: str | bytes,
    *,
    source_id: str,
) -> dict[str, Any]:
    try:
        raw = _source_bytes(raw_source)
        if not isinstance(source_id, str) or not source_id.strip():
            raise AdequacyAuthorityError("SOURCE_ID_REQUIRED")
        source_sha = sha256(raw).hexdigest()

        candidates: list[dict[str, Any]] = []
        attempts: list[dict[str, Any]] = []
        for resolver in (_p2_candidate, _p3_binary_candidate):
            candidate, attempt = resolver(raw_source, source_id.strip())
            attempts.append(attempt)
            if candidate is not None:
                if candidate.get("raw_source_sha256") != source_sha:
                    return {
                        "schema": SCHEMA,
                        "status": "FAIL_CLOSED",
                        "pass": False,
                        "reason": "AUTHORITY_RAW_SOURCE_BINDING_MISMATCH",
                        "authority_attempts": attempts,
                        "policy_selection_authorized": False,
                        "selected_policy_adequacy_verified": False,
                        "actual_goal_satisfaction_verified": False,
                        "terminal_authority": False,
                        "terminal_credit_delta": 0,
                    }
                candidates.append(candidate)

        if not candidates:
            return {
                "schema": SCHEMA,
                "status": "UNRESOLVED__NO_SELF_AUTHENTICATING_ADEQUACY_AUTHORITY_MATCHED",
                "pass": False,
                "raw_source_sha256": source_sha,
                "authority_attempts": attempts,
                "policy_selection_authorized": False,
                "selected_policy_adequacy_verified": False,
                "actual_goal_satisfaction_verified": False,
                "terminal_authority": False,
                "terminal_credit_delta": 0,
            }

        if len(candidates) != 1:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "pass": False,
                "reason": "MULTIPLE_SELF_AUTHENTICATING_ADEQUACY_AUTHORITIES_MATCHED",
                "raw_source_sha256": source_sha,
                "matched_authority_ids": sorted(
                    str(x.get("authority_id")) for x in candidates
                ),
                "authority_attempts": attempts,
                "policy_selection_authorized": False,
                "selected_policy_adequacy_verified": False,
                "actual_goal_satisfaction_verified": False,
                "terminal_authority": False,
                "terminal_credit_delta": 0,
            }

        selected = candidates[0]
        return {
            "schema": SCHEMA,
            "status": "PASS__SELF_AUTHENTICATING_ADEQUATE_POLICY_DISCOVERED",
            "pass": True,
            "raw_source_sha256": source_sha,
            "authority_id": selected["authority_id"],
            "policy_id": selected["policy_id"],
            "scope_membership_verified": True,
            "selected_policy_adequacy_verified": True,
            "policy_selection_authorized": True,
            "policy_result": selected["policy_result"],
            "adequacy_evidence": selected["adequacy_evidence"],
            "authority_result": selected["authority_result"],
            "realization": selected["realization"],
            "authority_attempts": attempts,
            "actual_goal_satisfaction_verified": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "policy_selection_authorized": False,
            "selected_policy_adequacy_verified": False,
            "actual_goal_satisfaction_verified": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
