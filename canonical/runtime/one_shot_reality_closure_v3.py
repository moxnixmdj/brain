"""One-shot reality closure V3: proof-gated externality.

V3 preserves the existing V1 fixed-point engine and V2 provider machinery but
removes the invalid implication:

    missing current evidence -> irreducibly external

A residual is external only after information_theoretic_externality_gate_v1
accepts a complete certificate. Until then, every unresolved residual remains
internal-unsolved and reality acquisition is forbidden.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping

from canonical.runtime import one_shot_verified_closure_v1 as v1
from canonical.runtime import one_shot_reality_closure_v2 as v2
from canonical.runtime import information_theoretic_externality_gate_v1 as externality

SCHEMA = "PROJECT_BRAIN_ONE_SHOT_REALITY_CLOSURE_V3"


def compile_gap_contract(
    closure_result: Mapping[str, Any],
    *,
    externality_certificate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    row = deepcopy(dict(closure_result))
    residual = row.get("residual")
    if not isinstance(residual, Mapping):
        residual = {}

    internal = sorted({str(x) for x in residual.get("internal_blockers", []) if str(x)})
    evidence = sorted({str(x) for x in residual.get("evidence_blockers", []) if str(x)})
    weak_external_claim = (
        row.get("irreducible_external_information_proved") is True
        or residual.get("irreducible_external_information_proved") is True
    )
    ext = externality.verify_certificate(externality_certificate)
    external_proved = ext.get("pass") is True

    empty_queue_fixed_point = (
        row.get("status") == "VERIFIED_INTERNAL_FIXED_POINT__IMPROVEMENT_QUEUE_EMPTY"
        and row.get("fixed_point") is True
    )

    if internal:
        gap_class = "CONSTRUCTIVE_CAPABILITY_GAP"
        required_action = "SYNTHESIZE_OR_ACQUIRE_VERIFIABLE_CAPABILITY"
    elif external_proved:
        gap_class = "STRICT_INFORMATION_THEORETIC_EXTERNAL_GAP"
        required_action = "ACQUIRE_MINIMUM_POLICY_CHANGING_INFORMATION"
    elif evidence or weak_external_claim:
        gap_class = "INTERNAL_UNSOLVED__EXTERNALITY_NOT_PROVED"
        required_action = (
            "CONTINUE_INTERNAL_SEARCH_DERIVATION_COMPOSITION_SYNTHESIS_OR_"
            "PRODUCE_INFORMATION_THEORETIC_EXTERNALITY_CERTIFICATE"
        )
    elif empty_queue_fixed_point:
        gap_class = "NO_R3_QUEUE_WORK__TERMINAL_MISSION_NOT_INFERRED"
        required_action = "RECOMPUTE_TERMINAL_RESIDUAL_FROM_CANONICAL_GOAL"
    elif row.get("pass") is True:
        gap_class = "VERIFIED_CLOSURE_RESULT__TERMINAL_AUTHORITY_NOT_INFERRED"
        required_action = "RECOMPUTE_TERMINAL_RESIDUAL_FROM_CANONICAL_GOAL"
    else:
        gap_class = "INTERNAL_UNSOLVED__UNCLASSIFIED"
        required_action = "REFINE_AND_SOLVE_INTERNAL_GAP"

    basis = {
        "source_schema": str(row.get("schema") or ""),
        "source_status": str(row.get("status") or ""),
        "source_initial_frontier_digest": str(row.get("initial_frontier_digest") or ""),
        "source_final_frontier_digest": str(row.get("final_frontier_digest") or ""),
        "source_final_state_sha256": str(row.get("final_state_sha256") or ""),
        "closure_class": str(row.get("closure_class") or ""),
        "internal_blockers": internal,
        "evidence_blockers": evidence,
        "weak_external_claim_seen": weak_external_claim,
        "information_theoretic_externality_proved": external_proved,
        "externality_certificate_digest": ext.get("certificate_digest"),
    }
    return {
        "schema": v2.GAP_SCHEMA,
        "gap_class": gap_class,
        "required_action": required_action,
        "basis": basis,
        "basis_digest": v2._sha(basis),
        "verification_authority_mutation_allowed": False,
        "terminal_credit": False,
        "externality_gate": ext,
    }


def run(
    *,
    repo_root,
    state_path=None,
    verification_frontier_acquisition_provider=None,
    verification_frontier_acquisition_provider_id="ONE_SHOT_ROOT1_ACQUISITION_PROVIDER",
    failure_repair_provider=None,
    capability_synthesis_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    reality_acquisition_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    externality_certificate_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    max_repair_rounds: int = 8,
    v1_max_rounds: int = 64,
    v1_max_actions_per_round: int = 32,
) -> dict[str, Any]:
    rounds = v2._positive_int("MAX_REPAIR_ROUNDS", max_repair_rounds)
    previous_frontier_after_provider: str | None = None
    transcript: list[dict[str, Any]] = []

    for repair_round in range(rounds):
        kwargs = {
            "repo_root": repo_root,
            "verification_frontier_acquisition_provider": verification_frontier_acquisition_provider,
            "verification_frontier_acquisition_provider_id": verification_frontier_acquisition_provider_id,
            "failure_repair_provider": failure_repair_provider,
            "max_rounds": v1_max_rounds,
            "max_actions_per_round": v1_max_actions_per_round,
        }
        if state_path is not None:
            kwargs["state_path"] = state_path
        closure = v1.run(**kwargs)

        current_initial = str(closure.get("initial_frontier_digest") or "")
        if (
            previous_frontier_after_provider is not None
            and current_initial
            and current_initial == previous_frontier_after_provider
        ):
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED__PROVIDER_RECEIPT_WITHOUT_OBSERVED_FRONTIER_CHANGE",
                "pass": False,
                "repair_round": repair_round,
                "transcript": transcript,
                "last_closure": deepcopy(dict(closure)),
                "terminal_authority": False,
            }

        request = {
            "closure_schema": closure.get("schema"),
            "closure_status": closure.get("status"),
            "residual": deepcopy(dict(closure.get("residual") or {})),
            "bounded_historical_evidence_certificate": deepcopy(
                closure.get("bounded_historical_evidence_certificate")
            ),
            "strict_external_failure_certificate": deepcopy(
                closure.get("strict_external_failure_certificate")
            ),
        }
        candidate = (
            externality_certificate_provider(deepcopy(request))
            if externality_certificate_provider is not None
            else None
        )
        contract = compile_gap_contract(
            closure,
            externality_certificate=candidate,
        )
        transcript.append({
            "repair_round": repair_round,
            "closure_status": closure.get("status"),
            "closure_pass": closure.get("pass") is True,
            "gap_class": contract["gap_class"],
            "basis_digest": contract["basis_digest"],
            "information_theoretic_externality_proved": (
                contract["externality_gate"].get("pass") is True
            ),
        })

        gap_class = contract["gap_class"]
        if gap_class == "STRICT_INFORMATION_THEORETIC_EXTERNAL_GAP":
            if reality_acquisition_provider is None:
                return {
                    "schema": SCHEMA,
                    "status": "OPEN__PROVEN_EXTERNAL_INFORMATION__REALITY_PROVIDER_REQUIRED",
                    "pass": False,
                    "gap_contract": contract,
                    "transcript": transcript,
                    "terminal_authority": False,
                }
            receipt = v2._validate_provider_receipt(
                reality_acquisition_provider(deepcopy(contract)),
                provider_kind="REALITY_ACQUISITION",
            )
        elif gap_class == "CONSTRUCTIVE_CAPABILITY_GAP":
            if capability_synthesis_provider is None:
                return {
                    "schema": SCHEMA,
                    "status": "OPEN__CAPABILITY_SYNTHESIS_PROVIDER_REQUIRED",
                    "pass": False,
                    "gap_contract": contract,
                    "transcript": transcript,
                    "terminal_authority": False,
                }
            receipt = v2._validate_provider_receipt(
                capability_synthesis_provider(deepcopy(contract)),
                provider_kind="CAPABILITY_SYNTHESIS",
            )
        elif gap_class.startswith("INTERNAL_UNSOLVED"):
            return {
                "schema": SCHEMA,
                "status": "OPEN__INTERNAL_UNSOLVED__EXTERNALITY_ESCAPE_FORBIDDEN",
                "pass": False,
                "gap_contract": contract,
                "transcript": transcript,
                "irreducible_external_information_proved": False,
                "terminal_authority": False,
            }
        else:
            return {
                "schema": SCHEMA,
                "status": "OPEN__TERMINAL_RECOMPUTATION_REQUIRED",
                "pass": False,
                "gap_contract": contract,
                "transcript": transcript,
                "terminal_authority": False,
            }

        previous_frontier_after_provider = str(closure.get("final_frontier_digest") or "")
        transcript[-1]["provider_receipt_sha256"] = receipt["receipt_sha256"]
        transcript[-1]["provider_kind"] = gap_class

    return {
        "schema": SCHEMA,
        "status": "OPEN__REPAIR_ROUND_LIMIT_REACHED",
        "pass": False,
        "repair_rounds_executed": rounds,
        "transcript": transcript,
        "terminal_authority": False,
    }
