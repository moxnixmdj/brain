"""Verified repair cycle for uncertified reached escape states.

The certified reached-state constructor may return one exact repair obligation.
This module makes that obligation executable without granting proposal authority:
a provider may propose one candidate policy/discriminator, an independent verifier
must authenticate the exact content-addressed candidate, and only then is the
candidate projected into a fresh state and re-certified.

No path proves global repair acquirability or open-ended mission completion.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import certified_reached_escape_state_constructor_v1 as constructor

SCHEMA = "PROJECT_BRAIN_REACHED_ESCAPE_REPAIR_CYCLE_V1"
CANDIDATE_SCHEMA = "PROJECT_BRAIN_REACHED_ESCAPE_REPAIR_CANDIDATE_V1"
VERIFY_REQUEST_SCHEMA = "PROJECT_BRAIN_REACHED_ESCAPE_REPAIR_VERIFY_REQUEST_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_REACHED_ESCAPE_REPAIR_VERIFICATION_V1"

DISCRIMINATOR_PROPERTY = (
    "AUTHENTICATED_SAFE_TRUTHFUL_COMPLETE_FOR_EXACT_STATE_REGION_DOMAIN"
)
POLICY_PROPERTY = "AUTHENTICATED_SAFE_ADEQUATE_FOR_DECLARED_REGION_IDS"


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


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "global_repair_acquirability_proved": False,
        "global_escape_progress_totality_proved": False,
        "open_ended_mission_terminal_proved": False,
        "provider_truth_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _candidate_request(
    state: Mapping[str, Any],
    repair: Mapping[str, Any],
    dispatch: Mapping[str, Any],
    *,
    round_index: int,
) -> dict[str, Any]:
    return {
        "schema": "PROJECT_BRAIN_REACHED_ESCAPE_REPAIR_ACQUISITION_REQUEST_V2",
        "round_index": round_index,
        "state_id": state.get("state_id"),
        "state_sha256": repair.get("state_sha256"),
        "repair_sha256": repair.get("repair_sha256"),
        "repair_kind": repair.get("kind"),
        "repair_request": deepcopy(dict(repair)),
        "repair_dispatch_sha256": dispatch.get("dispatch_sha256"),
        "repair_dispatch_contract": deepcopy(dict(dispatch)),
        "alternatives": deepcopy(list(dispatch.get("alternatives") or [])),
        "provider_contract": {
            "candidate_only": True,
            "provider_truth_authority": False,
            "provider_verification_authority": False,
            "provider_promotion_authority": False,
            "provider_acceptance_authority": False,
            "provider_terminal_authority": False,
            "exact_dispatch_alternative_binding_required": True,
            "independent_exact_candidate_verification_required": True,
        },
    }


def _required_target_regions(
    repair: Mapping[str, Any],
    candidate_kind: str,
) -> list[set[str]]:
    if repair.get("kind") == "UNCOVERED_REGION_POLICY_REPAIR":
        return [
            {str(x) for x in repair.get("uncovered_region_ids") or []}
        ] if candidate_kind == "POLICY" else []

    if repair.get("kind") != "UNSPLITTABLE_EQUIVALENCE_CLASS_REPAIR":
        return []

    out: list[set[str]] = []
    for row in repair.get("conflict_classes") or []:
        if isinstance(row, Mapping):
            ids = {str(x) for x in row.get("region_ids") or []}
            if ids:
                out.append(ids)
    return out


def _validated_dispatch(
    result: Mapping[str, Any],
    repair: Mapping[str, Any],
) -> tuple[Mapping[str, Any] | None, str | None]:
    dispatch = result.get("repair_dispatch_contract")
    if not isinstance(dispatch, Mapping):
        return None, "REPAIR_DISPATCH_CONTRACT_MISSING"
    if dispatch.get("pass") is not True:
        return None, "REPAIR_DISPATCH_CONTRACT_NOT_PASS"
    if dispatch.get("state_sha256") != repair.get("state_sha256"):
        return None, "REPAIR_DISPATCH_STATE_BINDING_MISMATCH"
    if dispatch.get("repair_sha256") != repair.get("repair_sha256"):
        return None, "REPAIR_DISPATCH_REPAIR_BINDING_MISMATCH"
    observed = str(result.get("repair_dispatch_sha256") or "").strip()
    expected = str(dispatch.get("dispatch_sha256") or "").strip()
    if not observed or observed != expected:
        return None, "REPAIR_DISPATCH_DIGEST_BINDING_MISMATCH"
    alternatives = dispatch.get("alternatives")
    if not isinstance(alternatives, Sequence) or isinstance(
        alternatives, (str, bytes, bytearray)
    ) or not alternatives:
        return None, "REPAIR_DISPATCH_ALTERNATIVES_INVALID"
    return dispatch, None


def _selected_alternative(
    dispatch: Mapping[str, Any],
    candidate_result: Mapping[str, Any],
    candidate_kind: str,
) -> tuple[Mapping[str, Any] | None, str | None]:
    alternative_id = str(candidate_result.get("alternative_id") or "").strip()
    if not alternative_id:
        return None, "REPAIR_ALTERNATIVE_ID_REQUIRED"
    matches = [
        row for row in dispatch.get("alternatives") or []
        if isinstance(row, Mapping) and row.get("alternative_id") == alternative_id
    ]
    if len(matches) != 1:
        return None, "REPAIR_ALTERNATIVE_ID_NOT_EXACT"
    row = matches[0]
    basis = row.get("basis")
    if not isinstance(basis, Mapping):
        return None, "REPAIR_ALTERNATIVE_BASIS_INVALID"
    expected_kind = (
        "DISCRIMINATOR"
        if basis.get("provider_kind") == "EVIDENCE_ACQUISITION"
        else "POLICY"
        if basis.get("provider_kind") == "CAPABILITY_SYNTHESIS"
        else None
    )
    if expected_kind != candidate_kind:
        return None, "REPAIR_ALTERNATIVE_CANDIDATE_KIND_MISMATCH"
    return row, None


def _state_identity_sets(
    state: Mapping[str, Any],
) -> tuple[set[str], set[str], set[str]]:
    if not isinstance(state, Mapping):
        raise ValueError("STATE_NOT_OBJECT")
    if state.get("schema") != "PROJECT_BRAIN_REACHED_ESCAPE_STATE_V1":
        raise ValueError("STATE_SCHEMA_INVALID")

    region_ids: set[str] = set()
    rows = state.get("regions")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        raise ValueError("STATE_REGIONS_INVALID")
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("STATE_REGION_ROW_INVALID")
        rid = row.get("region_id")
        if not isinstance(rid, str) or not rid.strip() or rid.strip() in region_ids:
            raise ValueError("STATE_REGION_ID_INVALID_OR_DUPLICATE")
        region_ids.add(rid.strip())
    if not region_ids:
        raise ValueError("STATE_REGIONS_EMPTY")

    policy_ids: set[str] = set()
    policies = state.get("policies", [])
    if not isinstance(policies, Sequence) or isinstance(
        policies, (str, bytes, bytearray)
    ):
        raise ValueError("STATE_POLICIES_INVALID")
    for row in policies:
        if not isinstance(row, Mapping):
            raise ValueError("STATE_POLICY_ROW_INVALID")
        pid = row.get("policy_id")
        if not isinstance(pid, str) or not pid.strip() or pid.strip() in policy_ids:
            raise ValueError("STATE_POLICY_ID_INVALID_OR_DUPLICATE")
        policy_ids.add(pid.strip())

    discriminator_ids: set[str] = set()
    discriminators = state.get("discriminators", [])
    if not isinstance(discriminators, Sequence) or isinstance(
        discriminators, (str, bytes, bytearray)
    ):
        raise ValueError("STATE_DISCRIMINATORS_INVALID")
    for row in discriminators:
        if not isinstance(row, Mapping):
            raise ValueError("STATE_DISCRIMINATOR_ROW_INVALID")
        did = row.get("discriminator_id")
        if (
            not isinstance(did, str)
            or not did.strip()
            or did.strip() in discriminator_ids
        ):
            raise ValueError("STATE_DISCRIMINATOR_ID_INVALID_OR_DUPLICATE")
        discriminator_ids.add(did.strip())

    return region_ids, policy_ids, discriminator_ids


def _validate_candidate_structure(
    state: Mapping[str, Any],
    repair: Mapping[str, Any],
    candidate_kind: str,
    candidate: Mapping[str, Any],
) -> tuple[bool, str | None]:
    try:
        region_ids, policy_ids, discriminator_ids = _state_identity_sets(state)
    except ValueError as exc:
        return False, str(exc)

    if candidate_kind == "DISCRIMINATOR":
        if repair.get("kind") != "UNSPLITTABLE_EQUIVALENCE_CLASS_REPAIR":
            return False, "DISCRIMINATOR_NOT_ALLOWED_FOR_REPAIR_KIND"
        did = candidate.get("discriminator_id")
        if not isinstance(did, str) or not did.strip():
            return False, "DISCRIMINATOR_ID_INVALID"
        if did.strip() in discriminator_ids:
            return False, "DISCRIMINATOR_ID_COLLISION"
        outcomes = candidate.get("outcomes")
        if not isinstance(outcomes, Mapping) or {str(k) for k in outcomes} != region_ids:
            return False, "DISCRIMINATOR_OUTCOME_DOMAIN_NOT_EXACT"
        try:
            for rid in sorted(region_ids):
                _canon(outcomes[rid])
        except Exception:
            return False, "DISCRIMINATOR_OUTCOME_NOT_CANONICAL"

        targets = _required_target_regions(repair, candidate_kind)
        separates = False
        for ids in targets:
            values = {_canon(outcomes[rid]) for rid in ids}
            if len(values) > 1:
                separates = True
                break
        if not separates:
            return False, "DISCRIMINATOR_DOES_NOT_SPLIT_ANY_CONFLICT_CLASS"
        return True, None

    if candidate_kind == "POLICY":
        pid = candidate.get("policy_id")
        if not isinstance(pid, str) or not pid.strip():
            return False, "POLICY_ID_INVALID"
        if pid.strip() in policy_ids:
            return False, "POLICY_ID_COLLISION"
        raw = candidate.get("adequate_region_ids")
        if (
            not isinstance(raw, Sequence)
            or isinstance(raw, (str, bytes, bytearray))
            or any(not isinstance(x, str) or x not in region_ids for x in raw)
        ):
            return False, "POLICY_ADEQUACY_REGION_SET_INVALID"
        covered = set(raw)
        targets = _required_target_regions(repair, candidate_kind)
        if not targets or not any(target and target.issubset(covered) for target in targets):
            return False, "POLICY_DOES_NOT_CLOSE_ANY_REQUIRED_REGION_SET"
        return True, None

    return False, "CANDIDATE_KIND_INVALID"


def _verification_request(
    state: Mapping[str, Any],
    repair: Mapping[str, Any],
    dispatch: Mapping[str, Any],
    alternative: Mapping[str, Any],
    *,
    candidate_kind: str,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_sha = _digest(candidate)
    return {
        "schema": VERIFY_REQUEST_SCHEMA,
        "state_id": state.get("state_id"),
        "state_sha256": repair.get("state_sha256"),
        "repair_sha256": repair.get("repair_sha256"),
        "repair_dispatch_sha256": dispatch.get("dispatch_sha256"),
        "alternative_id": alternative.get("alternative_id"),
        "candidate_kind": candidate_kind,
        "candidate_sha256": candidate_sha,
        "candidate": deepcopy(dict(candidate)),
        "required_verified_property": (
            DISCRIMINATOR_PROPERTY
            if candidate_kind == "DISCRIMINATOR"
            else POLICY_PROPERTY
        ),
        "verifier_contract": {
            "independent_of_candidate_provider": True,
            "exact_candidate_binding_required": True,
            "truth_or_adequacy_authority_required": True,
            "promotion_authority": False,
            "terminal_authority": False,
        },
    }


def _verify_candidate(
    request: Mapping[str, Any],
    verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None],
) -> tuple[bool, Mapping[str, Any] | None, str | None]:
    receipt = verifier(deepcopy(dict(request)))
    if not isinstance(receipt, Mapping):
        return False, None, "REPAIR_VERIFIER_RETURNED_NO_RECEIPT"
    if receipt.get("schema") != VERIFY_SCHEMA or receipt.get("pass") is not True:
        return False, receipt, "REPAIR_VERIFICATION_NOT_PASS"
    if receipt.get("independent_verification") is not True:
        return False, receipt, "REPAIR_VERIFICATION_NOT_INDEPENDENT"
    verifier_id = str(receipt.get("verifier_id") or "").strip()
    if not verifier_id:
        return False, receipt, "REPAIR_VERIFIER_ID_MISSING"
    for key in ("promotion_authority", "acceptance_authority", "terminal_authority"):
        if receipt.get(key) is True:
            return False, receipt, "REPAIR_VERIFIER_AUTHORITY_ESCALATION:" + key
    for key in (
        "state_sha256",
        "repair_sha256",
        "repair_dispatch_sha256",
        "alternative_id",
        "candidate_sha256",
        "candidate_kind",
    ):
        if receipt.get(key) != request.get(key):
            return False, receipt, "REPAIR_VERIFICATION_BINDING_MISMATCH:" + key
    required = request.get("required_verified_property")
    verified = receipt.get("verified_properties")
    if (
        not isinstance(verified, Sequence)
        or isinstance(verified, (str, bytes, bytearray))
        or required not in verified
    ):
        return False, receipt, "REPAIR_REQUIRED_PROPERTY_NOT_VERIFIED"
    return True, receipt, None


def _apply_verified_candidate(
    state: Mapping[str, Any],
    *,
    candidate_kind: str,
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    out = deepcopy(dict(state))
    if candidate_kind == "DISCRIMINATOR":
        out["discriminators"] = list(out.get("discriminators") or []) + [{
            "discriminator_id": str(candidate["discriminator_id"]).strip(),
            "authenticated": True,
            "safe": True,
            "truthful": True,
            "complete": True,
            "outcomes": deepcopy(dict(candidate["outcomes"])),
        }]
    else:
        out["policies"] = list(out.get("policies") or []) + [{
            "policy_id": str(candidate["policy_id"]).strip(),
            "authenticated": True,
            "safe": True,
            "adequate_region_ids": sorted(set(candidate["adequate_region_ids"])),
        }]
    return out


def run(
    state: Mapping[str, Any],
    *,
    provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None],
    verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None],
    max_rounds: int = 4,
) -> dict[str, Any]:
    if (
        isinstance(max_rounds, bool)
        or not isinstance(max_rounds, int)
        or max_rounds < 1
        or max_rounds > 16
    ):
        return _base("FAIL_CLOSED", reason="MAX_REPAIR_ROUNDS_INVALID")

    if provider is verifier:
        return _base(
            "FAIL_CLOSED__REPAIR_PROVIDER_AND_VERIFIER_NOT_INDEPENDENT",
            reason="PROVIDER_AND_VERIFIER_CALLABLE_IDENTICAL",
        )

    current = deepcopy(dict(state)) if isinstance(state, Mapping) else state
    trace: list[dict[str, Any]] = []

    for round_index in range(1, max_rounds + 1):
        result = constructor.construct(current)
        if result.get("pass") is True:
            return _base(
                "PASS__REACHED_ESCAPE_REPAIR_CYCLE_CLOSED",
                passed=True,
                repair_cycle_closed=True,
                repair_rounds_completed=len(trace),
                repair_trace=trace,
                final_state=deepcopy(current),
                final_result=deepcopy(dict(result)),
            )

        repair = result.get("repair_request")
        if (
            result.get("status") != "REPAIR_REQUIRED__UNCERTIFIED_REACHED_STATE_REJECTED"
            or not isinstance(repair, Mapping)
        ):
            return _base(
                "FAIL_CLOSED__REACHED_STATE_NOT_REPAIRABLE_BY_CYCLE",
                initial_or_current_result=deepcopy(dict(result)),
                repair_trace=trace,
            )

        dispatch, dispatch_error = _validated_dispatch(result, repair)
        if dispatch is None:
            return _base(
                "FAIL_CLOSED__REPAIR_DISPATCH_INVALID",
                reason=dispatch_error,
                initial_or_current_result=deepcopy(dict(result)),
                repair_trace=trace,
            )

        acquisition_request = _candidate_request(
            current,
            repair,
            dispatch,
            round_index=round_index,
        )
        candidate_result = provider(deepcopy(acquisition_request))
        if not isinstance(candidate_result, Mapping):
            return _base(
                "OPEN__REPAIR_PROVIDER_RETURNED_NO_CANDIDATE",
                initial_or_current_result=deepcopy(dict(result)),
                acquisition_request=acquisition_request,
                repair_trace=trace,
            )
        for key in (
            "truth_authority",
            "verification_authority",
            "promotion_authority",
            "acceptance_authority",
            "terminal_authority",
        ):
            if candidate_result.get(key) is True:
                return _base(
                    "FAIL_CLOSED__REPAIR_PROVIDER_AUTHORITY_ESCALATION",
                    authority_field=key,
                    repair_trace=trace,
                )
        if (
            candidate_result.get("schema") != CANDIDATE_SCHEMA
            or candidate_result.get("pass") is not True
            or candidate_result.get("repair_sha256") != repair.get("repair_sha256")
            or candidate_result.get("repair_dispatch_sha256")
            != dispatch.get("dispatch_sha256")
        ):
            return _base(
                "OPEN__REPAIR_CANDIDATE_BINDING_INVALID",
                candidate_result=deepcopy(dict(candidate_result)),
                repair_trace=trace,
            )

        candidate_kind = str(candidate_result.get("candidate_kind") or "").strip().upper()
        alternative, alternative_error = _selected_alternative(
            dispatch,
            candidate_result,
            candidate_kind,
        )
        if alternative is None:
            return _base(
                "FAIL_CLOSED__REPAIR_ALTERNATIVE_BINDING_INVALID",
                reason=alternative_error,
                repair_trace=trace,
            )
        candidate = candidate_result.get("candidate")
        if not isinstance(candidate, Mapping):
            return _base("FAIL_CLOSED__REPAIR_CANDIDATE_NOT_OBJECT", repair_trace=trace)

        valid, reason = _validate_candidate_structure(
            current,
            repair,
            candidate_kind,
            candidate,
        )
        if not valid:
            return _base(
                "FAIL_CLOSED__REPAIR_CANDIDATE_STRUCTURALLY_INVALID",
                reason=reason,
                repair_trace=trace,
            )

        verify_request = _verification_request(
            current,
            repair,
            dispatch,
            alternative,
            candidate_kind=candidate_kind,
            candidate=candidate,
        )
        verified, receipt, reason = _verify_candidate(verify_request, verifier)
        if not verified:
            return _base(
                "OPEN__REPAIR_CANDIDATE_NOT_INDEPENDENTLY_VERIFIED",
                reason=reason,
                verification_request=verify_request,
                verification_receipt=(
                    deepcopy(dict(receipt)) if isinstance(receipt, Mapping) else None
                ),
                repair_trace=trace,
            )

        next_state = _apply_verified_candidate(
            current,
            candidate_kind=candidate_kind,
            candidate=candidate,
        )
        trace.append({
            "round_index": round_index,
            "repair_sha256": repair.get("repair_sha256"),
            "repair_kind": repair.get("kind"),
            "repair_dispatch_sha256": dispatch.get("dispatch_sha256"),
            "alternative_id": alternative.get("alternative_id"),
            "candidate_kind": candidate_kind,
            "candidate_sha256": verify_request["candidate_sha256"],
            "verified_property": verify_request["required_verified_property"],
            "provider_truth_authority": False,
            "verification_receipt_bound": True,
            "verifier_id": str(receipt.get("verifier_id") or "").strip(),
            "independent_verification": True,
        })
        current = next_state

    final = constructor.construct(current)
    if final.get("pass") is True:
        return _base(
            "PASS__REACHED_ESCAPE_REPAIR_CYCLE_CLOSED",
            passed=True,
            repair_cycle_closed=True,
            repair_rounds_completed=len(trace),
            repair_trace=trace,
            final_state=deepcopy(current),
            final_result=deepcopy(dict(final)),
        )
    return _base(
        "OPEN__REPAIR_ROUND_BOUND_EXHAUSTED",
        repair_cycle_closed=False,
        repair_rounds_completed=len(trace),
        repair_trace=trace,
        final_state=deepcopy(current),
        final_result=deepcopy(dict(final)),
    )
