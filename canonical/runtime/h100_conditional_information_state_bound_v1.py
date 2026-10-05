"""Conditional information-state lower bound with runtime side information.

Runtime evidence partitions N hidden worlds into observational equivalence
classes C_j. With B bits of world-dependent persistent state, at most 2^B
worlds per class can be exactly distinguished. Under a uniform prior:

  success <= (1/N) * sum_j min(|C_j|, 2^B)

This interpolates between:
- no distinguishing runtime evidence: one class of size N -> 2^B/N;
- perfect JIT evidence: N singleton classes -> 1 with B=0.
"""
from __future__ import annotations

import math
from typing import Iterable

SCHEMA="PROJECT_BRAIN_H100_CONDITIONAL_INFORMATION_STATE_BOUND_V1"

class ConditionalInformationBoundError(ValueError):
    pass

def _sizes(class_sizes: Iterable[int]) -> tuple[int,...]:
    vals=tuple(class_sizes)
    if not vals:
        raise ConditionalInformationBoundError("CLASS_SIZES_EMPTY")
    if any((not isinstance(x,int)) or isinstance(x,bool) or x<1 for x in vals):
        raise ConditionalInformationBoundError("CLASS_SIZE_INVALID")
    return vals

def success_upper_bound(class_sizes: Iterable[int], learned_bits: int) -> float:
    sizes=_sizes(class_sizes)
    if not isinstance(learned_bits,int) or isinstance(learned_bits,bool) or learned_bits<0:
        raise ConditionalInformationBoundError("BITS_INVALID")
    cap=1<<learned_bits
    n=sum(sizes)
    return sum(min(s,cap) for s in sizes)/n

def zero_bit_upper_bound(class_sizes: Iterable[int]) -> float:
    sizes=_sizes(class_sizes)
    return len(sizes)/sum(sizes)

def minimum_bits_for_target(class_sizes: Iterable[int], target_success: float) -> int:
    sizes=_sizes(class_sizes)
    try:
        t=float(target_success)
    except Exception as exc:
        raise ConditionalInformationBoundError("TARGET_INVALID") from exc
    if not math.isfinite(t) or not (0.0<t<=1.0):
        raise ConditionalInformationBoundError("TARGET_OUT_OF_RANGE")
    b=0
    while success_upper_bound(sizes,b)+1e-15<t:
        b+=1
    return b

def residual_ambiguity_stats(class_sizes: Iterable[int]) -> dict:
    sizes=_sizes(class_sizes)
    n=sum(sizes)
    return {
        "world_count":n,
        "evidence_class_count":len(sizes),
        "largest_equivalence_class":max(sizes),
        "mean_equivalence_class_size":n/len(sizes),
        "zero_bit_success_upper_bound":len(sizes)/n,
        "bits_for_perfect_identification":math.ceil(math.log2(max(sizes))) if max(sizes)>1 else 0,
    }

def certificate(class_sizes: Iterable[int], learned_bits: int, target_success: float) -> dict:
    sizes=_sizes(class_sizes)
    upper=success_upper_bound(sizes,learned_bits)
    req=minimum_bits_for_target(sizes,target_success)
    return {
        "schema":SCHEMA,
        "status":"FORMAL_CONDITIONAL_INFORMATION_STATE_BOUND",
        "class_sizes":list(sizes),
        "learned_bits":learned_bits,
        "success_upper_bound":upper,
        "target_success":float(target_success),
        "minimum_bits_for_target":req,
        "target_ruled_out_by_current_bits":upper<float(target_success),
        "residual_ambiguity":residual_ambiguity_stats(sizes),
        "deduction":[
            "PERSISTENT_WORLD_DEPENDENT_STATE_ONLY_NEEDS_TO_RESOLVE_AMBIGUITY_LEFT_WITHIN_RUNTIME_EVIDENCE_CLASSES",
            "SINGLETON_RUNTIME_EVIDENCE_CLASSES_REQUIRE_ZERO_PERSISTENT_WORLD_DEPENDENT_BITS_FOR_IDENTIFICATION",
            "ONE_UNDISTINGUISHED_CLASS_RECOVERS_THE_UNCONDITIONAL_2^B_OVER_N_BOUND",
        ],
        "hard_nonclaims":[
            "DOES_NOT_PROVE_REAL_TASK_EVIDENCE_CLASSES_ARE_SMALL",
            "DOES_NOT_PROVE_JIT_EVIDENCE_IS AVAILABLE_OR CHEAP",
            "DOES_NOT_PROVE_ZERO_LEARNED_STATE_IS UNIVERSALLY SUFFICIENT",
        ],
        "h100_terminal_credit_delta":0,
    }
