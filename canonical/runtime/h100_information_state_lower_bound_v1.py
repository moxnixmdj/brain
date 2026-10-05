"""Information-theoretic lower bounds on persistent learned state.

This module separates two questions that are often conflated:

1. Can a deterministic / JIT / tool-using system solve a task when all
   information needed for the answer is available at runtime? Often yes.

2. Can zero persistent learned state solve a task family when the correct world
   is *not distinguishable* from runtime observations, tools, external
   knowledge, or deterministic code? No, except at chance or by prior coding.

We model N possible hidden worlds that are observationally identical at runtime.
A system may carry B bits of world-dependent persistent learned state. Such state
has at most 2^B distinguishable values. For exact world identification under a
uniform prior, average success is therefore at most min(1, 2^B / N).

This is a storage lower bound on missing information, not a claim about current
frontier benchmarks or Opus-level capability.
"""
from __future__ import annotations

import math

SCHEMA = "PROJECT_BRAIN_H100_INFORMATION_STATE_LOWER_BOUND_V1"


class InformationStateBoundError(ValueError):
    pass


def max_distinguishable_states(bits: int) -> int:
    if not isinstance(bits, int) or isinstance(bits, bool) or bits < 0:
        raise InformationStateBoundError("BITS_INVALID")
    return 1 << bits


def exact_identification_success_upper_bound(world_count: int, learned_bits: int) -> float:
    """Maximum average exact-identification success under a uniform prior.

    Assumptions:
    - all runtime observations and allowed external channels are identical
      across the worlds;
    - deterministic code is fixed and world-independent;
    - only the B-bit persistent learned state may depend on the hidden world;
    - success requires outputting the exact world identity.

    At most 2^B worlds can map to distinct persistent states that yield distinct
    exact outputs, hence success <= min(1, 2^B / N).
    """
    if not isinstance(world_count, int) or isinstance(world_count, bool) or world_count < 1:
        raise InformationStateBoundError("WORLD_COUNT_INVALID")
    return min(1.0, max_distinguishable_states(learned_bits) / world_count)


def minimum_bits_for_average_success(world_count: int, target_success: float) -> int:
    """Smallest integer B satisfying min(1,2^B/N) >= target_success."""
    if not isinstance(world_count, int) or isinstance(world_count, bool) or world_count < 1:
        raise InformationStateBoundError("WORLD_COUNT_INVALID")
    try:
        t = float(target_success)
    except Exception as exc:
        raise InformationStateBoundError("TARGET_SUCCESS_INVALID") from exc
    if not math.isfinite(t) or not (0.0 < t <= 1.0):
        raise InformationStateBoundError("TARGET_SUCCESS_OUT_OF_RANGE")
    need = world_count * t
    if need <= 1.0:
        return 0
    return int(math.ceil(math.log2(need)))


def binary_hidden_bit_zero_learned_bound() -> dict:
    """Canonical two-world witness for zero learned state."""
    return {
        "world_count": 2,
        "learned_bits": 0,
        "average_success_upper_bound": exact_identification_success_upper_bound(2, 0),
        "worst_case_exact_success_upper_bound": 0.5,
        "deduction": "ZERO_WORLD_DEPENDENT_PERSISTENT_BITS_CANNOT_EXCEED_CHANCE_WHEN_TWO_OPPOSITE_WORLDS_ARE_RUNTIME_INDISTINGUISHABLE",
    }


def bytes_to_bits(byte_count: int) -> int:
    if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count < 0:
        raise InformationStateBoundError("BYTE_COUNT_INVALID")
    return 8 * byte_count


def maximum_uniform_worlds_for_exact_success(learned_bytes: int, target_success: float = 1.0) -> int:
    """Largest N for which the storage counting bound does not rule out target success.

    This is only a counting bound. It does not prove an implementation exists.
    """
    bits = bytes_to_bits(learned_bytes)
    try:
        t = float(target_success)
    except Exception as exc:
        raise InformationStateBoundError("TARGET_SUCCESS_INVALID") from exc
    if not math.isfinite(t) or not (0.0 < t <= 1.0):
        raise InformationStateBoundError("TARGET_SUCCESS_OUT_OF_RANGE")
    return int(math.floor((1 << bits) / t))


def certificate(world_count: int, learned_bits: int, target_success: float) -> dict:
    upper = exact_identification_success_upper_bound(world_count, learned_bits)
    required = minimum_bits_for_average_success(world_count, target_success)
    return {
        "schema": SCHEMA,
        "status": "FORMAL_INFORMATION_STATE_LOWER_BOUND",
        "world_count": world_count,
        "learned_bits": learned_bits,
        "target_success": float(target_success),
        "success_upper_bound": upper,
        "minimum_bits_required_by_counting_bound": required,
        "target_ruled_out_by_current_bits": upper < float(target_success),
        "assumptions": [
            "RUNTIME_OBSERVATIONS_IDENTICAL_ACROSS_WORLDS",
            "ALLOWED_EXTERNAL_KNOWLEDGE_AND_TOOL_OUTPUTS_IDENTICAL_ACROSS_WORLDS",
            "DETERMINISTIC_CODE_IS_WORLD_INDEPENDENT",
            "ONLY_PERSISTENT_LEARNED_STATE_MAY_DEPEND_ON_HIDDEN_WORLD",
            "EXACT_WORLD_IDENTIFICATION_IS_REQUIRED",
            "UNIFORM_WORLD_PRIOR_FOR_AVERAGE_SUCCESS_BOUND",
        ],
        "hard_nonclaims": [
            "DOES_NOT_SHOW_CURRENT_FRONTIER_TASKS_CONTAIN_RUNTIME_INDISTINGUISHABLE_WORLDS",
            "DOES_NOT_SHOW_OPUS_LEVEL_CAPABILITY_REQUIRES_ANY_POSITIVE_LEARNED_STATE",
            "DOES_NOT_DISTINGUISH_LEARNED_BITS_FROM_OTHER_WORLD_DEPENDENT_PERSISTENT_BITS_IF_POLICY_ACCOUNTING_RECLASSIFIES_THEM",
            "DOES_NOT_PROVE_SUFFICIENCY_AT_THE_LOWER_BOUND",
        ],
        "h100_terminal_credit_delta": 0,
    }
