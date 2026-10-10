"""Execute one proof-carrying reached-state repair under independent verification.

Provider proposals are candidate-only. Only an independent verifier may return a
verified additive state delta. The Brain applies that verified delta structurally
and counts repair success only when the existing certified reached-state
constructor re-certifies the resulting state.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import certified_reached_escape_state_constructor_v1 as constructor
from canonical.runtime import certified_reached_escape_repair_dispatch_v1 as dispatch

SCHEMA = "PROJECT_BRAIN_CERTIFIED_REACHED_ESCAPE_REPAIR_EXECUTOR_V1"
CANDIDATE_SCHEMA = "PROJECT_BRAIN_ESCAPE_REPAIR_CANDIDATE_DELTA_V1"
VERIFICATION_SCHEMA = "PROJECT_BRAIN_ESCAPE_REPAIR_CANDIDATE_VERIFICATION_V1"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class EscapeRepairExecutionError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _valid_sha(value: Any) -> bool:
    return isinstance(value, str) and _HEX64.fullmatch(value) is not None


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "repair_verified": False,
        "global_repair_acquirability_proved": False,
        "global_escape_progress_totality_proved": False,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _validate_provider_receipt(
    result: Mapping[str, Any] | None,
    *,
    alternative: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(result, Mapping):
        raise EscapeRepairExecutionError("PROVIDER_RETURNED_NO_RECEIPT")
    receipt = deepcopy(dict(result))
    if receipt.get("pass") is not True:
        raise EscapeRepairExecutionError("PROVIDER_DID_NOT_PASS")
    if not _valid_sha(receipt.get("receipt_sha256")):
        raise EscapeRepairExecutionError("PROVIDER_RECEIPT_SHA256_INVALID")
    if receipt.get("frontier_changed") is not True:
        raise EscapeRepairExecutionError("PROVIDER_FRONTIER_NOT_CHANGED")
    if receipt.get("verification_authority_mutated") is not False:
        raise EscapeRepairExecutionError("PROVIDER_VERIFICATION_AUTHORITY_MUTATION")
    for key in (
        "truth_authority",
        "verification_authority",
        "promotion_authority",
        "acceptance_authority",
        "terminal_authority",
    ):
        if receipt.get(key) is True:
            raise EscapeRepairExecutionError("PROVIDER_AUTHORITY_ESCALATION:" + key)

    candidate = receipt.get("candidate_delta")
    if not isinstance(candidate, Mapping):
        raise EscapeRepairExecutionError("PROVIDER_CANDIDATE_DELTA_MISSING")
    candidate = deepcopy(dict(candidate))
    if candidate.get("schema") != CANDIDATE_SCHEMA:
        raise EscapeRepairExecutionError("PROVIDER_CANDIDATE_SCHEMA_INVALID")
    if str(candidate.get("alternative_id") or "") != str(
        alternative.get("alternative_id") or ""
    ):
        raise EscapeRepairExecutionError("PROVIDER_CANDIDATE_ALTERNATIVE_MISMATCH")

    declared = str(receipt.get("candidate_delta_sha256") or "")
    actual = _sha(candidate)
    if declared != actual:
        raise EscapeRepairExecutionError("PROVIDER_CANDIDATE_DIGEST_MISMATCH")
    return receipt, candidate


def _validate_verifier_receipt(
    result: Mapping[str, Any] | None,
    *,
    candidate: Mapping[str, Any],
    alternative: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(result, Mapping):
        raise EscapeRepairExecutionError("INDEPENDENT_VERIFIER_RETURNED_NO_RECEIPT")
    receipt = deepcopy(dict(result))
    if receipt.get("schema") != VERIFICATION_SCHEMA or receipt.get("pass") is not True:
        raise EscapeRepairExecutionError("INDEPENDENT_VERIFICATION_DID_NOT_PASS")
    if not _valid_sha(receipt.get("receipt_sha256")):
        raise EscapeRepairExecutionError("INDEPENDENT_VERIFICATION_RECEIPT_INVALID")
    if str(receipt.get("candidate_delta_sha256") or "") != _sha(candidate):
        raise EscapeRepairExecutionError("INDEPENDENT_VERIFICATION_CANDIDATE_MISMATCH")
    if str(receipt.get("alternative_id") or "") != str(
        alternative.get("alternative_id") or ""
    ):
        raise EscapeRepairExecutionError("INDEPENDENT_VERIFICATION_ALTERNATIVE_MISMATCH")
    if receipt.get("verification_authority_mutated") is not False:
        raise EscapeRepairExecutionError("INDEPENDENT_VERIFIER_AUTHORITY_MUTATION")

    verified = receipt.get("verified_delta")
    if not isinstance(verified, Mapping):
        raise EscapeRepairExecutionError("VERIFIED_DELTA_MISSING")
    verified = deepcopy(dict(verified))
    if str(receipt.get("verified_delta_sha256") or "") != _sha(verified):
        raise EscapeRepairExecutionError("VERIFIED_DELTA_DIGEST_MISMATCH")
    return receipt, verified


def _region_ids(state: Mapping[str, Any]) -> list[str]:
    rows = state.get("regions")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        raise EscapeRepairExecutionError("STATE_REGIONS_INVALID")
    out = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise EscapeRepairExecutionError("STATE_REGION_ROW_INVALID")
        rid = str(row.get("region_id") or "").strip()
        if not rid or rid in out:
            raise EscapeRepairExecutionError("STATE_REGION_ID_INVALID")
        out.append(rid)
    if not out:
        raise EscapeRepairExecutionError("STATE_REGIONS_EMPTY")
    return sorted(out)


def _apply_verified_delta(
    state: Mapping[str, Any],
    verified: Mapping[str, Any],
    *,
    alternative: Mapping[str, Any],
) -> dict[str, Any]:
    candidate = deepcopy(dict(state))
    regions = _region_ids(candidate)
    region_set = set(regions)
    kind = str(verified.get("kind") or "").strip()
    basis = alternative.get("basis")
    if not isinstance(basis, Mapping):
        raise EscapeRepairExecutionError("ALTERNATIVE_BASIS_INVALID")
    provider_kind = str(basis.get("provider_kind") or "").strip()
    repair_class = str(basis.get("repair_class") or "").strip()
    if provider_kind == "EVIDENCE_ACQUISITION":
        if repair_class != "ACQUIRE_TRUTHFUL_DISTINGUISHING_OBSERVATION" or kind != "ADD_DISCRIMINATOR":
            raise EscapeRepairExecutionError("VERIFIED_DELTA_KIND_MISMATCH_WITH_EVIDENCE_ALTERNATIVE")
    elif provider_kind == "CAPABILITY_SYNTHESIS":
        if repair_class not in {
            "ACQUIRE_OR_SYNTHESIZE_COMMON_ADEQUATE_POLICY",
            "ACQUIRE_OR_SYNTHESIZE_REGION_ADEQUATE_POLICY",
        } or kind != "ADD_POLICY":
            raise EscapeRepairExecutionError("VERIFIED_DELTA_KIND_MISMATCH_WITH_POLICY_ALTERNATIVE")
    else:
        raise EscapeRepairExecutionError("ALTERNATIVE_PROVIDER_KIND_UNSUPPORTED")

    row = verified.get("row")
    if not isinstance(row, Mapping):
        raise EscapeRepairExecutionError("VERIFIED_DELTA_ROW_INVALID")
    row = deepcopy(dict(row))

    if kind == "ADD_POLICY":
        pid = str(row.get("policy_id") or "").strip()
        if not pid or row.get("authenticated") is not True or row.get("safe") is not True:
            raise EscapeRepairExecutionError("VERIFIED_POLICY_NOT_AUTHENTICATED_SAFE")
        covers = row.get("adequate_region_ids")
        if not isinstance(covers, Sequence) or isinstance(covers, (str, bytes, bytearray)):
            raise EscapeRepairExecutionError("VERIFIED_POLICY_COVER_INVALID")
        cover = sorted({str(x).strip() for x in covers if str(x).strip()})
        if not cover or not set(cover) <= region_set:
            raise EscapeRepairExecutionError("VERIFIED_POLICY_COVER_OUTSIDE_STATE")
        policies = list(candidate.get("policies") or [])
        if any(isinstance(x, Mapping) and str(x.get("policy_id") or "") == pid for x in policies):
            raise EscapeRepairExecutionError("VERIFIED_POLICY_ID_COLLISION")
        row["adequate_region_ids"] = cover
        policies.append(row)
        candidate["policies"] = policies
        return candidate

    if kind == "ADD_DISCRIMINATOR":
        did = str(row.get("discriminator_id") or "").strip()
        if (
            not did
            or row.get("authenticated") is not True
            or row.get("safe") is not True
            or row.get("truthful") is not True
            or row.get("complete") is not True
        ):
            raise EscapeRepairExecutionError(
                "VERIFIED_DISCRIMINATOR_NOT_AUTHENTICATED_SAFE_TRUTHFUL_COMPLETE"
            )
        outcomes = row.get("outcomes")
        if not isinstance(outcomes, Mapping) or set(map(str, outcomes.keys())) != region_set:
            raise EscapeRepairExecutionError("VERIFIED_DISCRIMINATOR_DOMAIN_NOT_EXACT")
        discriminators = list(candidate.get("discriminators") or [])
        if any(
            isinstance(x, Mapping)
            and str(x.get("discriminator_id") or "") == did
            for x in discriminators
        ):
            raise EscapeRepairExecutionError("VERIFIED_DISCRIMINATOR_ID_COLLISION")
        row["outcomes"] = {rid: deepcopy(outcomes[rid]) for rid in regions}
        discriminators.append(row)
        candidate["discriminators"] = discriminators
        return candidate

    raise EscapeRepairExecutionError("VERIFIED_DELTA_KIND_UNSUPPORTED:" + kind)


def execute(
    state: Mapping[str, Any],
    *,
    capability_synthesis_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    evidence_acquisition_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    candidate_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    initial = constructor.construct(state)
    if initial.get("pass") is True:
        return {
            "schema": SCHEMA,
            "status": "PASS__STATE_ALREADY_CERTIFIED",
            "pass": True,
            "repair_verified": False,
            "constructor_result": initial,
            "global_repair_acquirability_proved": False,
            "global_escape_progress_totality_proved": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    contract = initial.get("repair_dispatch_contract")
    if not isinstance(contract, Mapping) or contract.get("pass") is not True:
        return _fail(
            "REPAIR_DISPATCH_CONTRACT_UNAVAILABLE",
            constructor_result=initial,
        )
    if candidate_verifier is None:
        return {
            **_fail("INDEPENDENT_CANDIDATE_VERIFIER_REQUIRED"),
            "status": "OPEN__INDEPENDENT_CANDIDATE_VERIFIER_REQUIRED",
            "repair_dispatch_contract": deepcopy(dict(contract)),
        }

    expected = dispatch.compile_repair(
        state_sha256=str(initial.get("state_sha256") or ""),
        repair_request=initial["repair_request"],
    )
    if str(contract.get("dispatch_sha256") or "") != expected["dispatch_sha256"]:
        return _fail("REPAIR_DISPATCH_CONTRACT_BINDING_MISMATCH")

    attempts = []
    for alternative in expected["alternatives"]:
        kind = alternative["basis"]["provider_kind"]
        provider = (
            capability_synthesis_provider
            if kind == "CAPABILITY_SYNTHESIS"
            else evidence_acquisition_provider
            if kind == "EVIDENCE_ACQUISITION"
            else None
        )
        if provider is None:
            attempts.append({
                "alternative_id": alternative["alternative_id"],
                "provider_kind": kind,
                "status": "PROVIDER_UNAVAILABLE",
            })
            continue
        provider_request = {
            "schema": "PROJECT_BRAIN_ESCAPE_REPAIR_PROVIDER_REQUEST_V1",
            "state_sha256": expected["state_sha256"],
            "repair_sha256": expected["repair_sha256"],
            "dispatch_sha256": expected["dispatch_sha256"],
            "alternative": deepcopy(dict(alternative)),
            "candidate_only": True,
            "provider_truth_authority": False,
            "provider_verification_authority": False,
            "provider_promotion_authority": False,
            "required_success_condition": (
                "INDEPENDENT_VERIFICATION_PLUS_CONSTRUCTOR_RECERTIFICATION"
            ),
        }
        try:
            provider_receipt, candidate = _validate_provider_receipt(
                provider(deepcopy(provider_request)),
                alternative=alternative,
            )
            verifier_request = {
                "schema": "PROJECT_BRAIN_ESCAPE_REPAIR_CANDIDATE_VERIFICATION_REQUEST_V1",
                "state_sha256": expected["state_sha256"],
                "repair_sha256": expected["repair_sha256"],
                "dispatch_sha256": expected["dispatch_sha256"],
                "alternative": deepcopy(dict(alternative)),
                "candidate_delta": deepcopy(dict(candidate)),
                "candidate_delta_sha256": _sha(candidate),
                "provider_receipt_sha256": provider_receipt["receipt_sha256"],
            }
            verifier_receipt, verified_delta = _validate_verifier_receipt(
                candidate_verifier(deepcopy(verifier_request)),
                candidate=candidate,
                alternative=alternative,
            )
            candidate_state = _apply_verified_delta(
                state,
                verified_delta,
                alternative=alternative,
            )
            recertified = constructor.construct(candidate_state)
            attempt = {
                "alternative_id": alternative["alternative_id"],
                "provider_kind": kind,
                "provider_receipt_sha256": provider_receipt["receipt_sha256"],
                "verifier_receipt_sha256": verifier_receipt["receipt_sha256"],
                "verified_delta_sha256": verifier_receipt["verified_delta_sha256"],
                "recertified": recertified.get("certified_reached_state_admitted") is True,
                "recertification_status": recertified.get("status"),
            }
            attempts.append(attempt)
            if (
                recertified.get("pass") is True
                and recertified.get("certified_reached_state_admitted") is True
            ):
                return {
                    "schema": SCHEMA,
                    "status": "PASS__REPAIR_VERIFIED_BY_CONSTRUCTOR_RECERTIFICATION",
                    "pass": True,
                    "repair_verified": True,
                    "selected_alternative_id": alternative["alternative_id"],
                    "selected_provider_kind": kind,
                    "provider_receipt": provider_receipt,
                    "verifier_receipt": verifier_receipt,
                    "verified_delta": verified_delta,
                    "candidate_state": candidate_state,
                    "constructor_result": recertified,
                    "attempts": attempts,
                    "global_repair_acquirability_proved": False,
                    "global_escape_progress_totality_proved": False,
                    "promotion_authority": False,
                    "acceptance_authority": False,
                    "terminal_authority": False,
                    "terminal_credit_delta": 0,
                }
        except Exception as exc:
            attempts.append({
                "alternative_id": alternative["alternative_id"],
                "provider_kind": kind,
                "status": "REJECTED",
                "reason": type(exc).__name__ + ":" + str(exc),
            })

    return {
        **_fail("NO_VERIFIED_ALTERNATIVE_RESTORED_CERTIFICATION"),
        "status": "OPEN__NO_VERIFIED_ALTERNATIVE_RESTORED_CERTIFICATION",
        "repair_dispatch_contract": deepcopy(dict(expected)),
        "attempts": attempts,
    }


def run(args: Mapping[str, Any] | None = None, **providers: Any) -> dict[str, Any]:
    args = args or {}
    return execute(
        args.get("state"),
        capability_synthesis_provider=providers.get("capability_synthesis_provider"),
        evidence_acquisition_provider=providers.get("evidence_acquisition_provider"),
        candidate_verifier=providers.get("candidate_verifier"),
    )
