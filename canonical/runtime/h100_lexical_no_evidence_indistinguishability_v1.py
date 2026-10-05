"""Information-theoretic lexical no-evidence bound for H100.

If a novel term has no distinguishing evidence, two semantic worlds may expose
the exact same observation while assigning different canonical roles to that
term. Any decision rule receiving that identical observation must therefore
behave identically in both worlds. A forced role is wrong in at least one world;
abstention is the only fail-closed answer valid across both.

This is an information bound, not a model-size claim.
"""
from __future__ import annotations

from typing import Literal

SCHEMA = "PROJECT_BRAIN_H100_LEXICAL_NO_EVIDENCE_INDISTINGUISHABILITY_V1"
Role = Literal["INPUT", "TARGET"]


class LexicalIndistinguishabilityError(ValueError):
    pass


def deterministic_two_world_outcome(forced_role: Role) -> dict:
    if forced_role not in {"INPUT", "TARGET"}:
        raise LexicalIndistinguishabilityError("ROLE_INVALID")
    worlds = {"WORLD_INPUT": "INPUT", "WORLD_TARGET": "TARGET"}
    correct = {name: forced_role == truth for name, truth in worlds.items()}
    return {
        "forced_role": forced_role,
        "world_truths": worlds,
        "world_correct": correct,
        "correct_world_count": sum(correct.values()),
        "world_count": len(worlds),
        "worst_case_correct": all(correct.values()),
    }


def randomized_two_world_worst_case(input_probability: float) -> dict:
    try:
        p = float(input_probability)
    except (TypeError, ValueError) as exc:
        raise LexicalIndistinguishabilityError("PROBABILITY_INVALID") from exc
    if not 0.0 <= p <= 1.0:
        raise LexicalIndistinguishabilityError("PROBABILITY_OUT_OF_RANGE")
    input_world_accuracy = p
    target_world_accuracy = 1.0 - p
    return {
        "p_input": p,
        "input_world_accuracy": input_world_accuracy,
        "target_world_accuracy": target_world_accuracy,
        "worst_case_accuracy": min(input_world_accuracy, target_world_accuracy),
    }


def minimax_randomized_accuracy() -> dict:
    # max_p min(p, 1-p) is attained at p=1/2 and equals 1/2.
    p = 0.5
    row = randomized_two_world_worst_case(p)
    return {
        **row,
        "minimax_probability_input": p,
        "minimax_worst_case_accuracy": row["worst_case_accuracy"],
    }


def fail_closed_decision(*, distinguishing_evidence_present: bool) -> dict:
    if distinguishing_evidence_present:
        status = "EVIDENCE_REQUIRED__DELEGATE_TO_VERIFIED_SOURCE_RESOLVER"
    else:
        status = "ABSTAIN_NO_DISTINGUISHING_EVIDENCE"
    return {
        "schema": SCHEMA,
        "status": status,
        "role": None,
        "persistent_learned_bytes_required_by_theorem": 0,
        "external_learned_capability_calls": 0,
        "hard_nonclaims": [
            "THE_THEOREM_DOES_NOT_SAY_REAL_TERMS_NEVER_HAVE_EVIDENCE",
            "THE_THEOREM_DOES_NOT_LIMIT_ACCURACY_WHEN_DISTINGUISHING_EVIDENCE_EXISTS",
            "THE_THEOREM_DOES_NOT_PROVE_FULL_H100_TERMINAL_SUCCESS",
        ],
        "h100_terminal_credit_delta": 0,
    }


def certificate() -> dict:
    input_forced = deterministic_two_world_outcome("INPUT")
    target_forced = deterministic_two_world_outcome("TARGET")
    minimax = minimax_randomized_accuracy()
    return {
        "schema": SCHEMA,
        "status": "FORMAL_NO_EVIDENCE_INDISTINGUISHABILITY_BOUND",
        "deterministic_forced_input_worst_case_correct": input_forced["worst_case_correct"],
        "deterministic_forced_target_worst_case_correct": target_forced["worst_case_correct"],
        "randomized_minimax_worst_case_accuracy": minimax["minimax_worst_case_accuracy"],
        "sound_no_evidence_action": "ABSTAIN",
        "deduction": [
            "IDENTICAL_OBSERVATIONS_WITH_OPPOSITE_HIDDEN_ROLES_MAKE_FORCED_UNIVERSAL_CORRECTNESS_IMPOSSIBLE",
            "RANDOMIZATION_CANNOT_EXCEED_ONE_HALF_WORST_CASE_ACCURACY_IN_THE_TWO_ROLE_SYMMETRIC_NO_EVIDENCE_GAME",
            "ARBITRARY_NOVEL_TERM_CORRECTNESS_REQUIRES_DISTINGUISHING_INFORMATION_FROM_SOURCE_CONTEXT_OR_OTHER_OBSERVATION",
            "FAIL_CLOSED_ABSTENTION_IS_SOUND_WHEN_SUCH_INFORMATION_IS_ABSENT",
        ],
        "persistent_learned_bytes_required_by_theorem": 0,
        "h100_terminal_credit_delta": 0,
    }
