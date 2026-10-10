"""Bounded iterative proof-carrying repair for finite reached escape states.

V1 required one verified provider delta to restore full constructor certification
immediately. V2 preserves that fast path and additionally retains an independently
verified additive delta when the canonical repair potential strictly decreases.
Because the potential is a nonnegative integer, accepted partial repairs are
well-founded and can occur at most the initial potential before certificate
eligibility. Provider availability is never inferred from this loop.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping

from canonical.runtime import certified_reached_escape_repair_executor_v1 as v1
from canonical.runtime import certified_reached_escape_state_constructor_v1 as constructor
from canonical.runtime import certified_reached_escape_repair_dispatch_v1 as dispatch
from canonical.runtime import reached_escape_repair_potential_v1 as repair_potential

SCHEMA = "PROJECT_BRAIN_CERTIFIED_REACHED_ESCAPE_REPAIR_EXECUTOR_V2"


def _open(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": reason,
        "pass": False,
        "repair_verified": False,
        "strict_progress_verified": bool(extra.get("strict_progress_history")),
        "global_repair_acquirability_proved": False,
        "global_escape_progress_totality_proved": False,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _provider_for(
    kind: str,
    *,
    capability_synthesis_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
    evidence_acquisition_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
):
    if kind == "CAPABILITY_SYNTHESIS":
        return capability_synthesis_provider
    if kind == "EVIDENCE_ACQUISITION":
        return evidence_acquisition_provider
    return None


def execute(
    state: Mapping[str, Any],
    *,
    capability_synthesis_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    evidence_acquisition_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    candidate_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    max_strict_progress_steps: int | None = None,
) -> dict[str, Any]:
    initial_constructor = constructor.construct(state)
    if initial_constructor.get("pass") is True:
        return {
            "schema": SCHEMA,
            "status": "PASS__STATE_ALREADY_CERTIFIED",
            "pass": True,
            "repair_verified": False,
            "strict_progress_verified": False,
            "constructor_result": initial_constructor,
            "strict_progress_history": [],
            "global_repair_acquirability_proved": False,
            "global_escape_progress_totality_proved": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    if candidate_verifier is None:
        return _open(
            "OPEN__INDEPENDENT_CANDIDATE_VERIFIER_REQUIRED",
            constructor_result=initial_constructor,
            strict_progress_history=[],
        )

    initial_measure = repair_potential.measure(state)
    if initial_measure.get("pass") is not True:
        return _open(
            "FAIL_CLOSED__REPAIR_POTENTIAL_UNAVAILABLE",
            constructor_result=initial_constructor,
            repair_potential_result=initial_measure,
            strict_progress_history=[],
        )
    initial_potential = int(initial_measure["repair_potential"])
    if initial_potential <= 0:
        return _open(
            "FAIL_CLOSED__OPEN_STATE_WITH_ZERO_REPAIR_POTENTIAL",
            constructor_result=initial_constructor,
            repair_potential_result=initial_measure,
            strict_progress_history=[],
        )

    if max_strict_progress_steps is None:
        progress_budget = initial_potential
    elif (
        isinstance(max_strict_progress_steps, bool)
        or not isinstance(max_strict_progress_steps, int)
        or max_strict_progress_steps < 0
    ):
        return _open(
            "FAIL_CLOSED__STRICT_PROGRESS_BUDGET_INVALID",
            initial_repair_potential=initial_potential,
            strict_progress_history=[],
        )
    else:
        progress_budget = min(max_strict_progress_steps, initial_potential)

    current_state = deepcopy(dict(state))
    attempts: list[dict[str, Any]] = []
    progress_history: list[dict[str, Any]] = []
    round_index = 0

    while True:
        current_constructor = constructor.construct(current_state)
        if (
            current_constructor.get("pass") is True
            and current_constructor.get("certified_reached_state_admitted") is True
        ):
            return {
                "schema": SCHEMA,
                "status": (
                    "PASS__ITERATIVE_REPAIR_VERIFIED_BY_CONSTRUCTOR_RECERTIFICATION"
                    if progress_history
                    else "PASS__STATE_ALREADY_CERTIFIED"
                ),
                "pass": True,
                "repair_verified": bool(progress_history),
                "strict_progress_verified": bool(progress_history),
                "constructor_result": current_constructor,
                "candidate_state": current_state,
                "attempts": attempts,
                "strict_progress_history": progress_history,
                "initial_repair_potential": initial_potential,
                "final_repair_potential": 0,
                "accepted_strict_progress_steps": len(progress_history),
                "maximum_strict_progress_steps_by_theorem": initial_potential,
                "global_repair_acquirability_proved": False,
                "global_escape_progress_totality_proved": False,
                "promotion_authority": False,
                "acceptance_authority": False,
                "terminal_authority": False,
                "terminal_credit_delta": 0,
            }

        contract = current_constructor.get("repair_dispatch_contract")
        if not isinstance(contract, Mapping) or contract.get("pass") is not True:
            return _open(
                "OPEN__REPAIR_DISPATCH_CONTRACT_UNAVAILABLE",
                constructor_result=current_constructor,
                candidate_state=current_state,
                attempts=attempts,
                strict_progress_history=progress_history,
                initial_repair_potential=initial_potential,
            )

        if len(progress_history) >= progress_budget:
            return _open(
                "OPEN__STRICT_PROGRESS_BUDGET_EXHAUSTED",
                constructor_result=current_constructor,
                candidate_state=current_state,
                repair_dispatch_contract=deepcopy(dict(contract)),
                attempts=attempts,
                strict_progress_history=progress_history,
                initial_repair_potential=initial_potential,
                current_repair_potential=repair_potential.measure(current_state).get("repair_potential"),
                accepted_strict_progress_steps=len(progress_history),
            )

        expected = dispatch.compile_repair(
            state_sha256=str(current_constructor.get("state_sha256") or ""),
            repair_request=current_constructor["repair_request"],
        )
        if str(contract.get("dispatch_sha256") or "") != expected["dispatch_sha256"]:
            return _open(
                "FAIL_CLOSED__REPAIR_DISPATCH_CONTRACT_BINDING_MISMATCH",
                attempts=attempts,
                strict_progress_history=progress_history,
                initial_repair_potential=initial_potential,
            )

        accepted_progress = None
        round_attempt_count = 0
        for alternative in expected["alternatives"]:
            kind = alternative["basis"]["provider_kind"]
            provider = _provider_for(
                kind,
                capability_synthesis_provider=capability_synthesis_provider,
                evidence_acquisition_provider=evidence_acquisition_provider,
            )
            if provider is None:
                attempts.append({
                    "round": round_index,
                    "alternative_id": alternative["alternative_id"],
                    "provider_kind": kind,
                    "status": "PROVIDER_UNAVAILABLE",
                })
                continue

            round_attempt_count += 1
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
                    "INDEPENDENT_VERIFICATION_PLUS_CONSTRUCTOR_RECERTIFICATION_OR_"
                    "STRICT_CANONICAL_REPAIR_POTENTIAL_DECREASE"
                ),
            }
            try:
                provider_receipt, candidate = v1._validate_provider_receipt(
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
                    "candidate_delta_sha256": v1._sha(candidate),
                    "provider_receipt_sha256": provider_receipt["receipt_sha256"],
                }
                verifier_receipt, verified_delta = v1._validate_verifier_receipt(
                    candidate_verifier(deepcopy(verifier_request)),
                    candidate=candidate,
                    alternative=alternative,
                )
                candidate_state = v1._apply_verified_delta(current_state, verified_delta)
                recertified = constructor.construct(candidate_state)
                progress = repair_potential.verify_monotone_repair(
                    current_state,
                    candidate_state,
                )
                attempt = {
                    "round": round_index,
                    "alternative_id": alternative["alternative_id"],
                    "provider_kind": kind,
                    "provider_receipt_sha256": provider_receipt["receipt_sha256"],
                    "verifier_receipt_sha256": verifier_receipt["receipt_sha256"],
                    "verified_delta_sha256": verifier_receipt["verified_delta_sha256"],
                    "recertified": recertified.get("certified_reached_state_admitted") is True,
                    "recertification_status": recertified.get("status"),
                    "strict_progress_proved": progress.get("strict_progress_proved") is True,
                    "before_repair_potential": progress.get("before_repair_potential"),
                    "after_repair_potential": progress.get("after_repair_potential"),
                }
                attempts.append(attempt)

                if (
                    recertified.get("pass") is True
                    and recertified.get("certified_reached_state_admitted") is True
                ):
                    return {
                        "schema": SCHEMA,
                        "status": (
                            "PASS__ITERATIVE_REPAIR_VERIFIED_BY_CONSTRUCTOR_RECERTIFICATION"
                            if progress_history
                            else "PASS__REPAIR_VERIFIED_BY_CONSTRUCTOR_RECERTIFICATION"
                        ),
                        "pass": True,
                        "repair_verified": True,
                        "strict_progress_verified": bool(progress_history),
                        "selected_alternative_id": alternative["alternative_id"],
                        "selected_provider_kind": kind,
                        "provider_receipt": provider_receipt,
                        "verifier_receipt": verifier_receipt,
                        "verified_delta": verified_delta,
                        "candidate_state": candidate_state,
                        "constructor_result": recertified,
                        "attempts": attempts,
                        "strict_progress_history": progress_history,
                        "initial_repair_potential": initial_potential,
                        "final_repair_potential": 0,
                        "accepted_strict_progress_steps": len(progress_history),
                        "maximum_strict_progress_steps_by_theorem": initial_potential,
                        "global_repair_acquirability_proved": False,
                        "global_escape_progress_totality_proved": False,
                        "promotion_authority": False,
                        "acceptance_authority": False,
                        "terminal_authority": False,
                        "terminal_credit_delta": 0,
                    }

                if (
                    progress.get("pass") is True
                    and progress.get("strict_progress_proved") is True
                ):
                    accepted_progress = (
                        candidate_state,
                        alternative,
                        provider_receipt,
                        verifier_receipt,
                        verified_delta,
                        progress,
                    )
                    break
            except Exception as exc:
                attempts.append({
                    "round": round_index,
                    "alternative_id": alternative["alternative_id"],
                    "provider_kind": kind,
                    "status": "REJECTED",
                    "reason": type(exc).__name__ + ":" + str(exc),
                })

        if accepted_progress is None:
            return _open(
                "OPEN__NO_VERIFIED_ALTERNATIVE_RESTORED_CERTIFICATION_OR_STRICT_PROGRESS",
                constructor_result=current_constructor,
                candidate_state=current_state,
                repair_dispatch_contract=deepcopy(dict(expected)),
                attempts=attempts,
                strict_progress_history=progress_history,
                initial_repair_potential=initial_potential,
                current_repair_potential=repair_potential.measure(current_state).get("repair_potential"),
                attempted_provider_calls_in_last_round=round_attempt_count,
            )

        (
            current_state,
            alternative,
            provider_receipt,
            verifier_receipt,
            verified_delta,
            progress,
        ) = accepted_progress
        progress_history.append({
            "round": round_index,
            "alternative_id": alternative["alternative_id"],
            "provider_kind": alternative["basis"]["provider_kind"],
            "provider_receipt_sha256": provider_receipt["receipt_sha256"],
            "verifier_receipt_sha256": verifier_receipt["receipt_sha256"],
            "verified_delta_sha256": verifier_receipt["verified_delta_sha256"],
            "before_repair_potential": progress["before_repair_potential"],
            "after_repair_potential": progress["after_repair_potential"],
            "repair_potential_delta": progress["repair_potential_delta"],
        })
        round_index += 1


def run(args: Mapping[str, Any] | None = None, **providers: Any) -> dict[str, Any]:
    args = args or {}
    return execute(
        args.get("state"),
        capability_synthesis_provider=providers.get("capability_synthesis_provider"),
        evidence_acquisition_provider=providers.get("evidence_acquisition_provider"),
        candidate_verifier=providers.get("candidate_verifier"),
        max_strict_progress_steps=args.get("max_strict_progress_steps"),
    )
