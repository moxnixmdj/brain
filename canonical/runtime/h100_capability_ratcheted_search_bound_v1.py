"""Capability-ratcheted search bounds for H100.

A verified deterministic capability library can shorten future proposal
descriptions without adding persistent learned bytes. Under the generic
prefix-search bound, shortening a proposal by D bits improves the worst-case
candidate-step bound by exactly 2^D for the same verifier cost.

This is a formal storage/compute tradeoff result, not a claim that every real
task belongs to a compiled family.
"""
from __future__ import annotations

import math

SCHEMA="PROJECT_BRAIN_H100_CAPABILITY_RATCHETED_SEARCH_BOUND_V1"


class RatchetBoundError(ValueError):
    pass


def ceil_log2_choices(n: int) -> int:
    if not isinstance(n,int) or isinstance(n,bool) or n < 1:
        raise RatchetBoundError("CHOICE_COUNT_INVALID")
    return 0 if n == 1 else (n-1).bit_length()


def raw_dovetail_bound(program_bits: int, verifier_steps: int) -> int:
    if not isinstance(program_bits,int) or isinstance(program_bits,bool) or program_bits < 1:
        raise RatchetBoundError("PROGRAM_BITS_INVALID")
    if not isinstance(verifier_steps,int) or isinstance(verifier_steps,bool) or verifier_steps < 1:
        raise RatchetBoundError("VERIFIER_STEPS_INVALID")
    return (1 << program_bits) * verifier_steps


def compiled_reference_bits(
    library_size: int,
    parameter_bits_total: int,
    *,
    mode_tag_bits: int = 1,
) -> int:
    if not isinstance(parameter_bits_total,int) or isinstance(parameter_bits_total,bool) or parameter_bits_total < 0:
        raise RatchetBoundError("PARAMETER_BITS_INVALID")
    if not isinstance(mode_tag_bits,int) or isinstance(mode_tag_bits,bool) or mode_tag_bits < 1:
        raise RatchetBoundError("MODE_TAG_BITS_INVALID")
    return mode_tag_bits + ceil_log2_choices(library_size) + parameter_bits_total


def compiled_dovetail_bound(
    library_size: int,
    parameter_bits_total: int,
    verifier_steps: int,
    *,
    mode_tag_bits: int = 1,
) -> int:
    bits=compiled_reference_bits(
        library_size,
        parameter_bits_total,
        mode_tag_bits=mode_tag_bits,
    )
    return raw_dovetail_bound(bits,verifier_steps)


def speedup_exponent(raw_program_bits: int, compiled_bits: int) -> int:
    if not isinstance(raw_program_bits,int) or isinstance(raw_program_bits,bool) or raw_program_bits < 1:
        raise RatchetBoundError("RAW_BITS_INVALID")
    if not isinstance(compiled_bits,int) or isinstance(compiled_bits,bool) or compiled_bits < 1:
        raise RatchetBoundError("COMPILED_BITS_INVALID")
    return raw_program_bits-compiled_bits


def exact_search_bound_ratio(raw_program_bits: int, compiled_bits: int) -> float | int:
    d=speedup_exponent(raw_program_bits,compiled_bits)
    if d >= 0:
        return 1 << d
    return 1.0/(1 << (-d))


def certificate(
    *,
    raw_program_bits: int,
    library_size: int,
    parameter_bits_total: int,
    verifier_steps: int,
    mode_tag_bits: int = 1,
) -> dict:
    cbits=compiled_reference_bits(
        library_size,parameter_bits_total,mode_tag_bits=mode_tag_bits
    )
    raw=raw_dovetail_bound(raw_program_bits,verifier_steps)
    comp=raw_dovetail_bound(cbits,verifier_steps)
    delta=raw_program_bits-cbits
    return {
        "schema":SCHEMA,
        "status":"CAPABILITY_RATCHET_SEARCH_BOUND_COMPUTED",
        "raw_program_bits":raw_program_bits,
        "library_size":library_size,
        "library_selector_bits":ceil_log2_choices(library_size),
        "parameter_bits_total":parameter_bits_total,
        "mode_tag_bits":mode_tag_bits,
        "compiled_reference_bits":cbits,
        "description_bit_reduction":delta,
        "verifier_steps":verifier_steps,
        "raw_candidate_step_bound":raw,
        "compiled_candidate_step_bound":comp,
        "search_bound_ratio_raw_over_compiled":exact_search_bound_ratio(raw_program_bits,cbits),
        "persistent_learned_bytes_added":0,
        "deduction":[
            "DETERMINISTIC_VERIFIED_LIBRARY_GROWTH_ADDS_ZERO_LEARNED_BYTES_UNDER_H100_ACCOUNTING",
            "LIBRARY_SELECTION_COST_GROWS_LOGARITHMICALLY_WITH_LIBRARY_SIZE",
            "EVERY_SAVED_DESCRIPTION_BIT_HALVES_THE_GENERIC_DOVETAIL_SEARCH_BOUND",
            "A_D_BIT_DESCRIPTION_REDUCTION_GIVES_2^D_SEARCH_BOUND_REDUCTION_FOR_EQUAL_VERIFIER_COST",
        ],
        "hard_nonclaims":[
            "DOES_NOT_PROVE_A_NOVEL_TASK_MATCHES_AN_EXISTING_LIBRARY_FAMILY",
            "DOES_NOT_BOUND_REQUIRED_PARAMETER_PRECISION_FOR_ALL_REAL_TASKS",
            "DOES_NOT_REDUCE_VERIFIER_COST_BY_ITSELF",
            "DOES_NOT_PROVE_FULL_H100_TERMINAL_SUCCESS",
        ],
        "h100_terminal_credit_delta":0,
    }
