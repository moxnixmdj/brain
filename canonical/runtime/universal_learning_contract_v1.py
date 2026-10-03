"""Universal learning control contract for Project Brain.

This module proves control-flow properties about novelty handling. It does NOT
claim that every novel environment is solvable, nor that finite samples prove
open-world success. The theorem is deliberately narrower and load-bearing:

1. Only explicitly verified coverage may use the known-capability route.
2. Everything else is captured as UNKNOWN and routed to LEARN.
3. Learning may combine prior-knowledge transfer, retrieval, observation,
   experiment, and deduction.
4. A learned candidate cannot become trusted/reusable until verification passes.
5. Environment/version change invalidates learned trust back to UNKNOWN.

Success-rate noninferiority remains an empirical acceptance question.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_LEARNING_CONTRACT_V1"

LEARNING_CHANNELS = (
    "TRANSFER_PRIOR_KNOWLEDGE",
    "RETRIEVE_DIRECT_OR_INDIRECT_EVIDENCE",
    "OBSERVE_ENVIRONMENT",
    "SAFE_EXPERIMENT",
    "DERIVE_AND_REASON",
)

STATES = (
    "UNKNOWN",
    "LEARNING",
    "CANDIDATE",
    "VERIFIED",
    "REJECTED",
)

EVENTS = (
    "START_LEARNING",
    "ACQUIRE_EVIDENCE",
    "FORM_CANDIDATE",
    "VERIFY_PASS",
    "VERIFY_FAIL",
    "RETRY",
    "REUSE",
    "ENVIRONMENT_CHANGED",
)


class UniversalLearningContractError(ValueError):
    pass


def route_input(*, verified_coverage: Any) -> dict[str, Any]:
    """Route an input using explicit verified coverage only.

    Truthiness is intentionally insufficient. Only literal True authorizes the
    known-capability path; False, None, missing/unknown sentinels, strings, and
    other values all fail closed into learning.
    """
    known = verified_coverage is True
    return {
        "schema": SCHEMA,
        "route": "USE_VERIFIED_CAPABILITY" if known else "LEARN",
        "verified_coverage": known,
        "unknown_captured": not known,
        "trusted_execution_authorized": known,
    }


def transition(state: str, event: str) -> str:
    if state not in STATES:
        raise UniversalLearningContractError("STATE_INVALID")
    if event not in EVENTS:
        raise UniversalLearningContractError("EVENT_INVALID")

    table = {
        ("UNKNOWN", "START_LEARNING"): "LEARNING",
        ("LEARNING", "ACQUIRE_EVIDENCE"): "LEARNING",
        ("LEARNING", "FORM_CANDIDATE"): "CANDIDATE",
        ("CANDIDATE", "VERIFY_PASS"): "VERIFIED",
        ("CANDIDATE", "VERIFY_FAIL"): "REJECTED",
        ("REJECTED", "RETRY"): "LEARNING",
        ("VERIFIED", "REUSE"): "VERIFIED",
        ("VERIFIED", "ENVIRONMENT_CHANGED"): "UNKNOWN",
    }
    try:
        return table[(state, event)]
    except KeyError as exc:
        raise UniversalLearningContractError(
            f"TRANSITION_FORBIDDEN:{state}:{event}"
        ) from exc


def promotion_allowed(state: str) -> bool:
    if state not in STATES:
        raise UniversalLearningContractError("STATE_INVALID")
    return state == "VERIFIED"


def learning_request(
    *,
    missing_question: str,
    prior_knowledge_refs: list[str] | tuple[str, ...] = (),
    channels: list[str] | tuple[str, ...] = LEARNING_CHANNELS,
) -> dict[str, Any]:
    question = " ".join(str(missing_question or "").split())
    if not question:
        raise UniversalLearningContractError("MISSING_QUESTION_REQUIRED")

    normalized = tuple(dict.fromkeys(str(x) for x in channels))
    if not normalized:
        raise UniversalLearningContractError("LEARNING_CHANNEL_REQUIRED")
    unknown = sorted(set(normalized) - set(LEARNING_CHANNELS))
    if unknown:
        raise UniversalLearningContractError(
            "UNKNOWN_LEARNING_CHANNEL:" + ",".join(unknown)
        )

    return {
        "schema": SCHEMA,
        "state": "LEARNING",
        "missing_question": question,
        "prior_knowledge_refs": sorted(
            {str(x).strip() for x in prior_knowledge_refs if str(x).strip()}
        ),
        "channels": list(normalized),
        "candidate_trusted": False,
        "promotion_authorized": False,
    }


def verify_candidate(*, candidate_id: str, verification_pass: bool) -> dict[str, Any]:
    cid = " ".join(str(candidate_id or "").split())
    if not cid:
        raise UniversalLearningContractError("CANDIDATE_ID_REQUIRED")
    state = transition(
        "CANDIDATE", "VERIFY_PASS" if verification_pass is True else "VERIFY_FAIL"
    )
    return {
        "schema": SCHEMA,
        "candidate_id": cid,
        "state": state,
        "trusted": state == "VERIFIED",
        "promotion_authorized": promotion_allowed(state),
    }


def prove_control_invariants() -> dict[str, Any]:
    """Exhaustively verify the finite control alphabet.

    This is a universal theorem over this declared transition system, not over
    semantic task success. Any future integration claiming this theorem must
    prove all relevant execution paths pass through this exact gate or an
    independently verified equivalent/superset gate.
    """
    errors: list[str] = []

    # Unknown capture: literal True is the sole known-route authority.
    probes = (True, False, None, 0, 1, "", "true", [], {}, object())
    for value in probes:
        out = route_input(verified_coverage=value)
        if value is True:
            if out["route"] != "USE_VERIFIED_CAPABILITY":
                errors.append("VERIFIED_TRUE_NOT_ROUTED_TO_KNOWN")
        else:
            if out["route"] != "LEARN" or out["trusted_execution_authorized"]:
                errors.append("NONTRUE_COVERAGE_BYPASSED_LEARNING")

    # Exhaust complete finite state/event product. Any unspecified edge must
    # fail closed, and the only edge entering VERIFIED is VERIFY_PASS.
    allowed = {
        ("UNKNOWN", "START_LEARNING"): "LEARNING",
        ("LEARNING", "ACQUIRE_EVIDENCE"): "LEARNING",
        ("LEARNING", "FORM_CANDIDATE"): "CANDIDATE",
        ("CANDIDATE", "VERIFY_PASS"): "VERIFIED",
        ("CANDIDATE", "VERIFY_FAIL"): "REJECTED",
        ("REJECTED", "RETRY"): "LEARNING",
        ("VERIFIED", "REUSE"): "VERIFIED",
        ("VERIFIED", "ENVIRONMENT_CHANGED"): "UNKNOWN",
    }
    checked = 0
    for state in STATES:
        for event in EVENTS:
            checked += 1
            expected = allowed.get((state, event))
            try:
                got = transition(state, event)
            except UniversalLearningContractError:
                got = None
            if got != expected:
                errors.append(f"TRANSITION_MISMATCH:{state}:{event}:{got}:{expected}")
            if got == "VERIFIED" and (state, event) != ("CANDIDATE", "VERIFY_PASS"):
                errors.append("VERIFIED_REACHED_WITHOUT_VERIFY_PASS")

    for state in STATES:
        if promotion_allowed(state) != (state == "VERIFIED"):
            errors.append("PROMOTION_GATE_INCORRECT:" + state)

    changed = transition("VERIFIED", "ENVIRONMENT_CHANGED")
    if changed != "UNKNOWN":
        errors.append("ENVIRONMENT_CHANGE_DID_NOT_INVALIDATE")

    req = learning_request(
        missing_question="new environment capability",
        prior_knowledge_refs=["known-language-semantics", "known-tool-patterns"],
    )
    if set(req["channels"]) != set(LEARNING_CHANNELS):
        errors.append("LEARNING_CHANNEL_SET_INCOMPLETE")
    if req["candidate_trusted"] or req["promotion_authorized"]:
        errors.append("LEARNING_REQUEST_PRETRUSTED")

    passed = not errors
    return {
        "schema": SCHEMA,
        "status": "UNIVERSAL_CONTROL_INVARIANTS_PASS" if passed else "FAIL_CLOSED",
        "pass": passed,
        "errors": errors,
        "proved": {
            "unknown_capture_total_over_declared_coverage_input": passed,
            "only_verified_coverage_uses_known_route": passed,
            "learning_channels_include_transfer_retrieval_observation_experiment_deduction": passed,
            "candidate_requires_verification_before_trust": passed,
            "promotion_requires_verified_state": passed,
            "environment_change_invalidates_to_unknown": passed,
            "finite_control_product_exhaustively_checked": passed,
        },
        "finite_control_pairs_checked": checked,
        "uses_empirical_generalization": False,
        "semantic_success_rate_proved": False,
        "tool_learning_noninferiority_proved": False,
        "unknown_domain_noninferiority_proved": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "incremental_spend_usd": 0,
    }
