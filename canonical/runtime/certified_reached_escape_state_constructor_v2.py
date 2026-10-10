"""Truth-authority boundary for reached escape states.

V1 constructor treats already-authenticated state rows as its input contract.
V2 makes that boundary explicit: caller booleans never create authentication.
Every policy/discriminator row that can support certified progress must be bound
to a content-addressed receipt returned by a separately supplied verifier.

This module grants no terminal authority and does not prove global repair
acquirability or resource admissibility.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import math
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import certified_reached_escape_state_constructor_v1 as v1

SCHEMA = "PROJECT_BRAIN_CERTIFIED_REACHED_ESCAPE_STATE_CONSTRUCTOR_V2"
STATE_SCHEMA = "PROJECT_BRAIN_REACHED_ESCAPE_STATE_V1"
CLAIM_SCHEMA = "PROJECT_BRAIN_REACHED_ESCAPE_AUTHORITY_CLAIM_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_REACHED_ESCAPE_AUTHORITY_RECEIPT_V1"

Verifier = Callable[[Mapping[str, Any]], Mapping[str, Any] | None]


class ReachedEscapeAuthorityError(ValueError):
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
        raise ReachedEscapeAuthorityError("NON_CANONICAL_JSON_VALUE") from exc


def _digest(value: Any) -> str:
    return "sha256:" + sha256(_canon(value).encode("utf-8")).hexdigest()


def _sid(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 512:
        raise ReachedEscapeAuthorityError(label + "_INVALID")
    return value.strip()


def _seq(value: Any, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ReachedEscapeAuthorityError(label + "_INVALID")
    return list(value)


def _receipt_core(receipt: Mapping[str, Any]) -> dict[str, Any]:
    core = deepcopy(dict(receipt))
    core.pop("receipt_sha256", None)
    return core


def _verify_receipt(
    *,
    claim: Mapping[str, Any],
    verifier: Verifier | None,
    expected_kind: str,
    expected_state_sha256: str,
) -> dict[str, Any]:
    if verifier is None:
        raise ReachedEscapeAuthorityError(expected_kind + "_VERIFIER_REQUIRED")
    raw = verifier(deepcopy(dict(claim)))
    if not isinstance(raw, Mapping):
        raise ReachedEscapeAuthorityError(expected_kind + "_VERIFIER_RESULT_NOT_OBJECT")
    receipt = deepcopy(dict(raw))
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise ReachedEscapeAuthorityError(expected_kind + "_RECEIPT_SCHEMA_INVALID")
    if receipt.get("pass") is not True:
        raise ReachedEscapeAuthorityError(expected_kind + "_RECEIPT_NOT_PASSING")
    claim_sha = _digest(claim)
    if receipt.get("claim_sha256") != claim_sha:
        raise ReachedEscapeAuthorityError(expected_kind + "_CLAIM_BINDING_MISMATCH")
    if receipt.get("candidate_state_sha256") != expected_state_sha256:
        raise ReachedEscapeAuthorityError(expected_kind + "_STATE_BINDING_MISMATCH")
    if receipt.get("authority_kind") != expected_kind:
        raise ReachedEscapeAuthorityError(expected_kind + "_AUTHORITY_KIND_MISMATCH")
    if receipt.get("verification_authority_mutated") is not False:
        raise ReachedEscapeAuthorityError(expected_kind + "_AUTHORITY_MUTATION_FORBIDDEN")
    authority_id = receipt.get("authority_id")
    if not isinstance(authority_id, str) or not authority_id.strip():
        raise ReachedEscapeAuthorityError(expected_kind + "_AUTHORITY_ID_REQUIRED")
    observed_digest = receipt.get("receipt_sha256")
    expected_digest = _digest(_receipt_core(receipt))
    if observed_digest != expected_digest:
        raise ReachedEscapeAuthorityError(expected_kind + "_RECEIPT_DIGEST_MISMATCH")
    return receipt


def _resource_bound(receipt: Mapping[str, Any], *, label: str) -> tuple[float, str]:
    verified = receipt.get("verified")
    if not isinstance(verified, Mapping):
        raise ReachedEscapeAuthorityError(label + "_VERIFIED_PAYLOAD_REQUIRED")
    bound = verified.get("resource_bound")
    if not isinstance(bound, Mapping):
        raise ReachedEscapeAuthorityError(label + "_RESOURCE_BOUND_REQUIRED")
    amount = bound.get("amount")
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise ReachedEscapeAuthorityError(label + "_RESOURCE_AMOUNT_INVALID")
    amount = float(amount)
    if not math.isfinite(amount) or amount < 0:
        raise ReachedEscapeAuthorityError(label + "_RESOURCE_AMOUNT_INVALID")
    unit = bound.get("unit")
    if not isinstance(unit, str) or not unit.strip():
        raise ReachedEscapeAuthorityError(label + "_RESOURCE_UNIT_INVALID")
    return amount, unit.strip()


def _prepare_candidate(state: Mapping[str, Any]) -> tuple[str, list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(state, Mapping) or state.get("schema") != STATE_SCHEMA:
        raise ReachedEscapeAuthorityError("STATE_SCHEMA_INVALID")
    state_id = _sid(state.get("state_id"), "STATE_ID")

    region_ids: list[str] = []
    seen_regions: set[str] = set()
    for row in _seq(state.get("regions"), "REGIONS"):
        if not isinstance(row, Mapping):
            raise ReachedEscapeAuthorityError("REGION_ROW_INVALID")
        rid = _sid(row.get("region_id"), "REGION_ID")
        if rid in seen_regions:
            raise ReachedEscapeAuthorityError("DUPLICATE_REGION_ID:" + rid)
        seen_regions.add(rid)
        region_ids.append(rid)
    if not region_ids:
        raise ReachedEscapeAuthorityError("REGIONS_EMPTY")
    region_ids.sort()
    region_set = set(region_ids)

    policies: list[dict[str, Any]] = []
    seen_policies: set[str] = set()
    for row in _seq(state.get("policies", []), "POLICIES"):
        if not isinstance(row, Mapping):
            raise ReachedEscapeAuthorityError("POLICY_ROW_INVALID")
        pid = _sid(row.get("policy_id"), "POLICY_ID")
        if pid in seen_policies:
            raise ReachedEscapeAuthorityError("DUPLICATE_POLICY_ID:" + pid)
        seen_policies.add(pid)
        covers = []
        for raw in _seq(row.get("adequate_region_ids"), "POLICY_ADEQUACY"):
            rid = _sid(raw, "POLICY_ADEQUACY_REGION_ID")
            if rid not in region_set:
                raise ReachedEscapeAuthorityError("POLICY_ADEQUACY_REGION_OUTSIDE_STATE:" + pid)
            if rid not in covers:
                covers.append(rid)
        covers.sort()
        policies.append({"policy_id": pid, "adequate_region_ids": covers})
    policies.sort(key=lambda x: x["policy_id"])

    discriminators: list[dict[str, Any]] = []
    seen_discriminators: set[str] = set()
    for row in _seq(state.get("discriminators", []), "DISCRIMINATORS"):
        if not isinstance(row, Mapping):
            raise ReachedEscapeAuthorityError("DISCRIMINATOR_ROW_INVALID")
        did = _sid(row.get("discriminator_id"), "DISCRIMINATOR_ID")
        if did in seen_discriminators:
            raise ReachedEscapeAuthorityError("DUPLICATE_DISCRIMINATOR_ID:" + did)
        seen_discriminators.add(did)
        outcomes = row.get("outcomes")
        if not isinstance(outcomes, Mapping):
            raise ReachedEscapeAuthorityError("DISCRIMINATOR_OUTCOMES_INVALID:" + did)
        if {str(k) for k in outcomes} != region_set:
            raise ReachedEscapeAuthorityError("DISCRIMINATOR_OUTCOME_DOMAIN_NOT_EXACT:" + did)
        normalized = {rid: deepcopy(outcomes[rid]) for rid in region_ids}
        _canon(normalized)
        discriminators.append({"discriminator_id": did, "outcomes": normalized})
    discriminators.sort(key=lambda x: x["discriminator_id"])
    return state_id, region_ids, policies, discriminators


def construct(
    state: Mapping[str, Any],
    *,
    policy_authority_verifier: Verifier | None = None,
    discriminator_authority_verifier: Verifier | None = None,
) -> dict[str, Any]:
    base = {
        "schema": SCHEMA,
        "pass": False,
        "certified_reached_state_admitted": False,
        "truth_authority_bound": False,
        "global_escape_progress_totality_proved": False,
        "global_repair_acquirability_proved": False,
        "resource_admissibility_proved": False,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    try:
        state_id, region_ids, policies, discriminators = _prepare_candidate(state)
        candidate_state_core = {
            "schema": STATE_SCHEMA,
            "state_id": state_id,
            "regions": [{"region_id": rid} for rid in region_ids],
            "policies": deepcopy(policies),
            "discriminators": deepcopy(discriminators),
        }
        candidate_state_sha256 = _digest(candidate_state_core)

        verified_policies: list[dict[str, Any]] = []
        policy_receipts: list[dict[str, Any]] = []
        resource_bounds: list[tuple[str, str, float, str]] = []
        for row in policies:
            claim = {
                "schema": CLAIM_SCHEMA,
                "claim_type": "POLICY_ADEQUACY_SAFETY_AND_RESOURCE",
                "candidate_state_sha256": candidate_state_sha256,
                "state_id": state_id,
                "region_ids": region_ids,
                "policy_id": row["policy_id"],
                "adequate_region_ids": row["adequate_region_ids"],
            }
            receipt = _verify_receipt(
                claim=claim,
                verifier=policy_authority_verifier,
                expected_kind="POLICY_ADEQUACY_SAFETY_AND_RESOURCE",
                expected_state_sha256=candidate_state_sha256,
            )
            verified = receipt.get("verified")
            if not isinstance(verified, Mapping):
                raise ReachedEscapeAuthorityError("POLICY_VERIFIED_PAYLOAD_REQUIRED")
            if verified.get("safe") is not True:
                raise ReachedEscapeAuthorityError("POLICY_SAFETY_NOT_VERIFIED:" + row["policy_id"])
            if sorted(verified.get("adequate_region_ids") or []) != row["adequate_region_ids"]:
                raise ReachedEscapeAuthorityError("POLICY_ADEQUACY_NOT_EXACT:" + row["policy_id"])
            amount, unit = _resource_bound(receipt, label="POLICY:" + row["policy_id"])
            resource_bounds.append(("POLICY", row["policy_id"], amount, unit))
            verified_policies.append(
                {
                    "policy_id": row["policy_id"],
                    "authenticated": True,
                    "safe": True,
                    "adequate_region_ids": row["adequate_region_ids"],
                }
            )
            policy_receipts.append(receipt)

        verified_discriminators: list[dict[str, Any]] = []
        discriminator_receipts: list[dict[str, Any]] = []
        for row in discriminators:
            claim = {
                "schema": CLAIM_SCHEMA,
                "claim_type": "DISCRIMINATOR_TRUTH_SAFETY_COMPLETENESS_AND_RESOURCE",
                "candidate_state_sha256": candidate_state_sha256,
                "state_id": state_id,
                "region_ids": region_ids,
                "discriminator_id": row["discriminator_id"],
                "outcomes": row["outcomes"],
            }
            receipt = _verify_receipt(
                claim=claim,
                verifier=discriminator_authority_verifier,
                expected_kind="DISCRIMINATOR_TRUTH_SAFETY_COMPLETENESS_AND_RESOURCE",
                expected_state_sha256=candidate_state_sha256,
            )
            verified = receipt.get("verified")
            if not isinstance(verified, Mapping):
                raise ReachedEscapeAuthorityError("DISCRIMINATOR_VERIFIED_PAYLOAD_REQUIRED")
            if not all(verified.get(k) is True for k in ("safe", "truthful", "complete")):
                raise ReachedEscapeAuthorityError(
                    "DISCRIMINATOR_TRUTH_OR_SAFETY_NOT_VERIFIED:" + row["discriminator_id"]
                )
            if _digest(verified.get("outcomes")) != _digest(row["outcomes"]):
                raise ReachedEscapeAuthorityError(
                    "DISCRIMINATOR_OUTCOMES_NOT_EXACT:" + row["discriminator_id"]
                )
            amount, unit = _resource_bound(
                receipt, label="DISCRIMINATOR:" + row["discriminator_id"]
            )
            resource_bounds.append(
                ("DISCRIMINATOR", row["discriminator_id"], amount, unit)
            )
            verified_discriminators.append(
                {
                    "discriminator_id": row["discriminator_id"],
                    "authenticated": True,
                    "safe": True,
                    "truthful": True,
                    "complete": True,
                    "outcomes": row["outcomes"],
                }
            )
            discriminator_receipts.append(receipt)

        resource_units = sorted({row[3] for row in resource_bounds})
        if len(resource_units) > 1:
            raise ReachedEscapeAuthorityError("RESOURCE_UNITS_NOT_COMPARABLE")
        resource_unit = resource_units[0] if resource_units else None

        verified_state = {
            "schema": STATE_SCHEMA,
            "state_id": state_id,
            "regions": [{"region_id": rid} for rid in region_ids],
            "policies": verified_policies,
            "discriminators": verified_discriminators,
        }
        result = v1.construct(verified_state)
        return {
            **deepcopy(dict(result)),
            "schema": SCHEMA,
            "truth_authority_bound": True,
            "candidate_state_sha256": candidate_state_sha256,
            "authority_receipts": {
                "policy": policy_receipts,
                "discriminator": discriminator_receipts,
            },
            "candidate_authority_flags_ignored": True,
            "resource_admissibility_proved": bool(resource_bounds),
            "resource_unit": resource_unit,
            "resource_bounds": [
                {
                    "kind": kind,
                    "subject_id": subject_id,
                    "finite_upper_bound": amount,
                    "unit": unit,
                }
                for kind, subject_id, amount, unit in resource_bounds
            ],
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return {
            **base,
            "status": "FAIL_CLOSED__REACHED_ESCAPE_TRUTH_AUTHORITY",
            "reason": type(exc).__name__ + ":" + str(exc),
            "candidate_authority_flags_ignored": True,
        }


def run(args: Mapping[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    return construct(args.get("state") or {})
