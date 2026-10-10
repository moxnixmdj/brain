"""Proof-carrying constructor for Brain-owned reached escape states.

A candidate state is admitted to the reached-state kernel only when the existing
finite-totality certificate proves that every possible kernel refinement path
terminates in a common authenticated safe adequate policy cell.

States that are structurally valid but fail those preconditions are not admitted
as certified reached states. Instead, the constructor emits one deterministic
content-addressed repair obligation. This does not prove the repair is globally
acquirable and grants no execution, promotion, acceptance, or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime import reached_escape_finite_totality_certificate_v1 as finite_totality
from canonical.runtime import reached_escape_state_kernel_v1 as kernel
from canonical.runtime import certified_reached_escape_repair_dispatch_v1 as repair_dispatch

SCHEMA = "PROJECT_BRAIN_CERTIFIED_REACHED_ESCAPE_STATE_CONSTRUCTOR_V1"
REPAIR_SCHEMA = "PROJECT_BRAIN_CERTIFIED_REACHED_ESCAPE_STATE_REPAIR_V1"


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return "sha256:" + sha256(_canon(value).encode("utf-8")).hexdigest()


def _base(*, state_id: Any = None, state_sha256: Any = None) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "state_id": state_id,
        "state_sha256": state_sha256,
        "certified_reached_state_admitted": False,
        "global_escape_progress_totality_proved": False,
        "global_repair_acquirability_proved": False,
        "open_ended_mission_terminal_proved": False,
        "truth_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def _repair_from_open_certificate(cert: Mapping[str, Any]) -> dict[str, Any]:
    status = str(cert.get("status") or "")
    state_id = cert.get("state_id")
    state_sha256 = cert.get("state_sha256")

    if status == "OPEN__REGION_WITHOUT_AUTHENTICATED_SAFE_ADEQUATE_POLICY":
        uncovered = sorted(str(x) for x in cert.get("uncovered_region_ids") or [])
        core = {
            "schema": REPAIR_SCHEMA,
            "kind": "UNCOVERED_REGION_POLICY_REPAIR",
            "state_id": state_id,
            "state_sha256": state_sha256,
            "uncovered_region_ids": uncovered,
            "required_postcondition_any": [
                {
                    "repair_class": "ACQUIRE_OR_SYNTHESIZE_REGION_ADEQUATE_POLICY",
                    "postcondition": (
                        "EVERY_UNCOVERED_REGION_ID_HAS_AT_LEAST_ONE_"
                        "AUTHENTICATED_SAFE_ADEQUATE_POLICY"
                    ),
                    "preferred_existing_bridge": (
                        "R2_POLICY_ADEQUACY_CAPABILITY_EXPANSION_OR_ROOT1_ACQUISITION"
                    ),
                }
            ],
            "provider_truth_authority": False,
            "verification_authority": False,
            "promotion_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
            "global_acquirability_claimed": False,
        }
    elif status == "OPEN__INDISTINGUISHABLE_CLASS_WITHOUT_COMMON_ADEQUATE_POLICY":
        conflicts = []
        for row in cert.get("indistinguishable_policy_conflict_classes") or []:
            if isinstance(row, Mapping):
                conflicts.append({
                    "region_ids": sorted(str(x) for x in row.get("region_ids") or []),
                    "discriminator_signature": deepcopy(row.get("discriminator_signature")),
                })
        conflicts.sort(key=lambda row: row["region_ids"])
        core = {
            "schema": REPAIR_SCHEMA,
            "kind": "UNSPLITTABLE_EQUIVALENCE_CLASS_REPAIR",
            "state_id": state_id,
            "state_sha256": state_sha256,
            "conflict_classes": conflicts,
            "required_postcondition_any": [
                {
                    "repair_class": "ACQUIRE_TRUTHFUL_DISTINGUISHING_OBSERVATION",
                    "postcondition": (
                        "ADD_ONE_AUTHENTICATED_SAFE_TRUTHFUL_COMPLETE_"
                        "DISCRIMINATOR_NONCONSTANT_ON_AT_LEAST_ONE_CONFLICT_CLASS"
                    ),
                    "preferred_existing_bridge": "R3_DISTINGUISHING_EVIDENCE_ACQUISITION",
                },
                {
                    "repair_class": "ACQUIRE_OR_SYNTHESIZE_COMMON_ADEQUATE_POLICY",
                    "postcondition": (
                        "EACH_REMAINING_CONFLICT_CLASS_HAS_AT_LEAST_ONE_COMMON_"
                        "AUTHENTICATED_SAFE_ADEQUATE_POLICY"
                    ),
                    "preferred_existing_bridge": (
                        "R2_POLICY_ADEQUACY_CAPABILITY_EXPANSION_OR_ROOT1_ACQUISITION"
                    ),
                },
            ],
            "provider_truth_authority": False,
            "verification_authority": False,
            "promotion_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
            "global_acquirability_claimed": False,
        }
    else:
        raise ValueError("CERTIFICATE_STATUS_NOT_REPAIRABLE:" + status)

    core["repair_sha256"] = _digest(core)
    return core


def construct(state: Mapping[str, Any]) -> dict[str, Any]:
    cert = finite_totality.certify(state)
    if cert.get("pass") is True and cert.get("reached_state_future_outcome_totality_proved") is True:
        result = kernel.evaluate(state)
        if (
            result.get("pass") is not True
            or result.get("reached_state_progress_proved") is not True
            or result.get("status") not in {
                "TERMINALIZE_WITH_COMMON_POLICY",
                "STRICT_PROGRESS_WITH_DISCRIMINATOR",
            }
        ):
            return {
                **_base(
                    state_id=cert.get("state_id"),
                    state_sha256=cert.get("state_sha256"),
                ),
                "pass": False,
                "status": "FAIL_CLOSED__CERTIFICATE_KERNEL_INCONSISTENCY",
                "certificate": deepcopy(dict(cert)),
                "kernel_result": deepcopy(dict(result)),
            }
        return {
            **_base(
                state_id=cert.get("state_id"),
                state_sha256=cert.get("state_sha256"),
            ),
            "pass": True,
            "status": "PASS__CERTIFIED_REACHED_STATE_ADMITTED",
            "certified_reached_state_admitted": True,
            "reached_state_future_outcome_totality_proved": True,
            "certificate": deepcopy(dict(cert)),
            "kernel_result": deepcopy(dict(result)),
        }

    status = str(cert.get("status") or "")
    if status in {
        "OPEN__REGION_WITHOUT_AUTHENTICATED_SAFE_ADEQUATE_POLICY",
        "OPEN__INDISTINGUISHABLE_CLASS_WITHOUT_COMMON_ADEQUATE_POLICY",
    }:
        repair = _repair_from_open_certificate(cert)
        dispatch_contract = repair_dispatch.compile_repair(
            state_sha256=str(cert.get("state_sha256") or ""),
            repair_request=repair,
        )
        return {
            **_base(
                state_id=cert.get("state_id"),
                state_sha256=cert.get("state_sha256"),
            ),
            "pass": False,
            "status": "REPAIR_REQUIRED__UNCERTIFIED_REACHED_STATE_REJECTED",
            "certificate_status": status,
            "repair_request": repair,
            "repair_sha256": repair["repair_sha256"],
            "repair_dispatch_contract": dispatch_contract,
            "repair_dispatch_sha256": dispatch_contract["dispatch_sha256"],
            "hard_nonclaim": "NO_CLAIM_THE_REQUIRED_REPAIR_IS_GLOBALLY_ACQUIRABLE",
        }

    return {
        **_base(
            state_id=cert.get("state_id"),
            state_sha256=cert.get("state_sha256"),
        ),
        "pass": False,
        "status": "FAIL_CLOSED__REACHED_STATE_CERTIFICATION_FAILED",
        "certificate": deepcopy(dict(cert)),
    }


def run(args: Mapping[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    return construct(args.get("state"))
