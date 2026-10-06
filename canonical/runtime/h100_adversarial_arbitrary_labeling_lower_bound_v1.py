from __future__ import annotations
import math

class ArbitraryLabelingBoundError(ValueError): pass

def labeling_class_size(point_count:int)->int:
    if not isinstance(point_count,int) or isinstance(point_count,bool) or point_count<1:
        raise ArbitraryLabelingBoundError("POINT_COUNT_INVALID")
    return 1 << point_count

def total_target_adapted_bits_lower_bound(point_count:int)->int:
    if not isinstance(point_count,int) or isinstance(point_count,bool) or point_count<1:
        raise ArbitraryLabelingBoundError("POINT_COUNT_INVALID")
    return point_count

def learned_bits_lower_bound(point_count:int, deterministic_target_bits:int)->int:
    if not isinstance(deterministic_target_bits,int) or isinstance(deterministic_target_bits,bool) or deterministic_target_bits<0:
        raise ArbitraryLabelingBoundError("CODE_BUDGET_INVALID")
    return max(0,point_count-deterministic_target_bits)

def exact_universal_coverage_fraction(point_count:int,total_target_adapted_bits:int)->float:
    if point_count<1 or total_target_adapted_bits<0:
        raise ArbitraryLabelingBoundError("INVALID")
    return min(1.0,2.0**(total_target_adapted_bits-point_count))

def certificate(point_count:int,deterministic_target_bits:int)->dict:
    return {
        "point_count":point_count,
        "labeling_class_size":labeling_class_size(point_count),
        "total_target_adapted_bits_lower_bound":total_target_adapted_bits_lower_bound(point_count),
        "deterministic_target_bits":deterministic_target_bits,
        "learned_bits_lower_bound":learned_bits_lower_bound(point_count,deterministic_target_bits),
        "deduction":"ARBITRARY_UNSTRUCTURED_LABELING_UNIVERSALITY_HAS_A_POSITIVE_PERSISTENT_CAPABILITY_INFORMATION_REQUIREMENT",
        "hard_nonclaim":"THIS_ADVERSARIAL_CLASS_IS_NOT_A_MODEL_OF_ALL_REAL_FRONTIER_TASKS"
    }
