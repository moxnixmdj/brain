"""Compile certified reached-state repair obligations into proof-carrying provider contracts.

This module is intentionally non-effectful. It never edits a reached state, never
trusts a provider's self-asserted truth, and never grants promotion/acceptance/
terminal authority.

A repair-required reached state is compiled into an OR-set of exact alternatives:
- policy construction/acquisition -> capability-synthesis provider class;
- truthful distinguishing observation -> evidence-acquisition provider class.

A provider receipt is not success. The repaired candidate state must later be
independently verified and pass the existing certified reached-state constructor.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_CERTIFIED_REACHED_ESCAPE_REPAIR_DISPATCH_V1"
ALT_SCHEMA = "PROJECT_BRAIN_CERTIFIED_REACHED_ESCAPE_REPAIR_ALTERNATIVE_V1"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class EscapeRepairDispatchError(ValueError):
    pass


def _canon(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise EscapeRepairDispatchError("NON_CANONICAL_VALUE") from exc


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _repair_digest(repair: Mapping[str, Any]) -> str:
    base = deepcopy(dict(repair))
    observed = str(base.pop("repair_sha256", "") or "").strip()
    expected = "sha256:" + _sha(base)
    if observed != expected:
        raise EscapeRepairDispatchError("REPAIR_DIGEST_MISMATCH")
    return observed


def _nonempty_strings(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise EscapeRepairDispatchError(label + "_NOT_SEQUENCE")
    out: list[str] = []
    for raw in value:
        item = str(raw or "").strip()
        if not item:
            raise EscapeRepairDispatchError(label + "_EMPTY_ITEM")
        if item not in out:
            out.append(item)
    if not out:
        raise EscapeRepairDispatchError(label + "_EMPTY")
    return out


def _alt(
    *,
    state_sha256: str,
    repair_sha256: str,
    repair_kind: str,
    repair_class: str,
    postcondition: str,
    provider_kind: str,
    provider_objective: str,
    exact_scope: Mapping[str, Any],
) -> dict[str, Any]:
    basis = {
        "state_sha256": state_sha256,
        "repair_sha256": repair_sha256,
        "repair_kind": repair_kind,
        "repair_class": repair_class,
        "postcondition": postcondition,
        "provider_kind": provider_kind,
        "provider_objective": provider_objective,
        "exact_scope": deepcopy(dict(exact_scope)),
        "candidate_only": True,
        "provider_may_not_self_authenticate_candidate": True,
        "verification_authority_mutation_allowed": False,
        "required_final_check": (
            "INDEPENDENTLY_VERIFY_CANDIDATE_DELTA__APPLY_ONLY_VERIFIED_DELTA__"
            "RERUN_CERTIFIED_REACHED_ESCAPE_STATE_CONSTRUCTOR__REQUIRE_CERTIFIED_ADMISSION"
        ),
    }
    return {
        "schema": ALT_SCHEMA,
        "alternative_id": "escape-repair:" + _sha(basis),
        "basis": basis,
        "proof_precedence": [
            "REUSE_EXISTING_AUTHENTICATED_POLICY_OR_DISCRIMINATOR",
            "REUSE_EXISTING_CONTENT_ADDRESSED_RECEIPT",
            "DETERMINISTIC_PROOF_OR_SCOPE_CERTIFICATE",
            "MINIMUM_NEW_CAPABILITY_OR_POLICY_CHANGING_OBSERVATION",
            "BROAD_NEW_REALITY_ACQUISITION_LAST",
        ],
        "provider_receipt_requirements": {
            "pass": True,
            "receipt_sha256_required": True,
            "frontier_changed": True,
            "verification_authority_mutated": False,
            "independent_candidate_verification_required": True,
            "candidate_delta_sha256_required": True,
        },
        "success_condition": (
            "PROVIDER_RECEIPT_IS_NOT_SUCCESS__ONLY_POST_VERIFICATION_CONSTRUCTOR_"
            "RECERTIFICATION_WITH_CERTIFIED_REACHED_STATE_ADMITTED_TRUE_IS_SUCCESS"
        ),
        "terminal_credit": False,
    }


def compile_repair(
    *,
    state_sha256: str,
    repair_request: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(state_sha256, str) or not state_sha256.startswith("sha256:"):
        raise EscapeRepairDispatchError("STATE_SHA256_INVALID")
    digest_part = state_sha256.removeprefix("sha256:")
    if _HEX64.fullmatch(digest_part) is None:
        raise EscapeRepairDispatchError("STATE_SHA256_INVALID")
    if not isinstance(repair_request, Mapping):
        raise EscapeRepairDispatchError("REPAIR_REQUEST_NOT_OBJECT")

    repair = deepcopy(dict(repair_request))
    repair_sha256 = _repair_digest(repair)
    if str(repair.get("state_sha256") or "") != state_sha256:
        raise EscapeRepairDispatchError("REPAIR_STATE_BINDING_MISMATCH")
    kind = str(repair.get("kind") or "").strip()
    required = repair.get("required_postcondition_any")
    if not isinstance(required, Sequence) or isinstance(required, (str, bytes, bytearray)):
        raise EscapeRepairDispatchError("REPAIR_ALTERNATIVES_INVALID")

    alternatives: list[dict[str, Any]] = []
    for row in required:
        if not isinstance(row, Mapping):
            raise EscapeRepairDispatchError("REPAIR_ALTERNATIVE_NOT_OBJECT")
        repair_class = str(row.get("repair_class") or "").strip()
        postcondition = str(row.get("postcondition") or "").strip()
        if not repair_class or not postcondition:
            raise EscapeRepairDispatchError("REPAIR_ALTERNATIVE_INCOMPLETE")

        if repair_class == "ACQUIRE_TRUTHFUL_DISTINGUISHING_OBSERVATION":
            conflicts = repair.get("conflict_classes")
            if not isinstance(conflicts, Sequence) or isinstance(conflicts, (str, bytes, bytearray)):
                raise EscapeRepairDispatchError("CONFLICT_CLASSES_REQUIRED")
            exact_scope = {
                "conflict_classes": deepcopy(list(conflicts)),
                "required_discriminator_properties": [
                    "AUTHENTICATED",
                    "SAFE",
                    "TRUTHFUL",
                    "COMPLETE_ON_CURRENT_REGION_IDS",
                    "NONCONSTANT_ON_AT_LEAST_ONE_CURRENT_CONFLICT_CLASS",
                ],
            }
            alternatives.append(
                _alt(
                    state_sha256=state_sha256,
                    repair_sha256=repair_sha256,
                    repair_kind=kind,
                    repair_class=repair_class,
                    postcondition=postcondition,
                    provider_kind="EVIDENCE_ACQUISITION",
                    provider_objective=(
                        "ACQUIRE_MINIMUM_POLICY_CHANGING_TRUTHFUL_DISCRIMINATOR"
                    ),
                    exact_scope=exact_scope,
                )
            )
        elif repair_class in {
            "ACQUIRE_OR_SYNTHESIZE_COMMON_ADEQUATE_POLICY",
            "ACQUIRE_OR_SYNTHESIZE_REGION_ADEQUATE_POLICY",
        }:
            if repair_class == "ACQUIRE_OR_SYNTHESIZE_COMMON_ADEQUATE_POLICY":
                conflicts = repair.get("conflict_classes")
                if not isinstance(conflicts, Sequence) or isinstance(conflicts, (str, bytes, bytearray)):
                    raise EscapeRepairDispatchError("CONFLICT_CLASSES_REQUIRED")
                exact_scope = {
                    "conflict_classes": deepcopy(list(conflicts)),
                    "required_policy_properties": [
                        "AUTHENTICATED",
                        "SAFE",
                        "ADEQUATE_FOR_EVERY_REGION_IN_AT_LEAST_ONE_CURRENT_CONFLICT_CLASS",
                    ],
                }
            else:
                uncovered = _nonempty_strings(
                    repair.get("uncovered_region_ids"),
                    label="UNCOVERED_REGION_IDS",
                )
                exact_scope = {
                    "uncovered_region_ids": uncovered,
                    "required_policy_properties": [
                        "AUTHENTICATED",
                        "SAFE",
                        "ADEQUATE_FOR_EVERY_TARGETED_UNCOVERED_REGION",
                    ],
                }
            alternatives.append(
                _alt(
                    state_sha256=state_sha256,
                    repair_sha256=repair_sha256,
                    repair_kind=kind,
                    repair_class=repair_class,
                    postcondition=postcondition,
                    provider_kind="CAPABILITY_SYNTHESIS",
                    provider_objective=(
                        "REUSE_COMPOSE_OR_SYNTHESIZE_MINIMUM_VERIFIABLE_ADEQUATE_POLICY"
                    ),
                    exact_scope=exact_scope,
                )
            )
        else:
            raise EscapeRepairDispatchError(
                "UNSUPPORTED_REPAIR_CLASS:" + repair_class
            )

    if not alternatives:
        raise EscapeRepairDispatchError("NO_SUPPORTED_REPAIR_ALTERNATIVES")
    ids = [row["alternative_id"] for row in alternatives]
    if len(ids) != len(set(ids)):
        raise EscapeRepairDispatchError("DUPLICATE_REPAIR_ALTERNATIVE")

    payload = {
        "schema": SCHEMA,
        "status": "READY__PROOF_CARRYING_REPAIR_ALTERNATIVES_COMPILED",
        "pass": True,
        "state_sha256": state_sha256,
        "repair_sha256": repair_sha256,
        "repair_kind": kind,
        "alternative_semantics": "ANY_ONE_VERIFIED_ALTERNATIVE_MAY_CLOSE_THE_REPAIR",
        "alternatives": sorted(alternatives, key=lambda row: row["alternative_id"]),
        "alternative_count": len(alternatives),
        "required_attempt_rule": (
            "SEARCH_AND_REUSE_BEFORE_NEW_CODE_OR_NEW_REALITY__RACE_INDEPENDENT_"
            "ALTERNATIVES_WHEN_SAFE__STOP_AFTER_FIRST_INDEPENDENTLY_VERIFIED_"
            "CANDIDATE_THAT_RESTORES_CONSTRUCTOR_CERTIFICATION"
        ),
        "provider_success_is_terminal_success": False,
        "independent_candidate_verification_required": True,
        "constructor_recertification_required": True,
        "global_repair_acquirability_proved": False,
        "global_escape_progress_totality_proved": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    payload["dispatch_sha256"] = _sha(payload)
    return payload


def run(args: Mapping[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    try:
        return compile_repair(
            state_sha256=str(args.get("state_sha256") or ""),
            repair_request=args.get("repair_request"),
        )
    except EscapeRepairDispatchError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": str(exc),
            "global_repair_acquirability_proved": False,
            "global_escape_progress_totality_proved": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
