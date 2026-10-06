from __future__ import annotations
from canonical.runtime import h100_resource_bounded_persistent_capability_bound_v1 as b

def standalone_learned_lower_bound(function_class_size:int)->int:
    total=b.class_bits(function_class_size)
    # If deterministic capability code is allowed to consume the full total
    # description lower bound, the residual lower bound on learned bits is zero.
    return b.learned_bits_lower_bound(function_class_size,total)

def learned_lower_bound_under_code_budget(function_class_size:int, code_bits:int)->int:
    return b.learned_bits_lower_bound(function_class_size,code_bits)

def certificate(function_class_size:int)->dict:
    total=b.class_bits(function_class_size)
    return {
        "function_class_size":function_class_size,
        "minimum_total_persistent_capability_bits":total,
        "standalone_learned_bit_lower_bound_without_code_budget":standalone_learned_lower_bound(function_class_size),
        "deduction":"LEARNED_BITS_ALONE_HAVE_NO_POSITIVE_CARDINALITY_LOWER_BOUND_WHEN_DETERMINISTIC_CAPABILITY_CODE_IS_UNBOUNDED",
        "h100_terminal_credit_delta":0
    }
