from __future__ import annotations
import math

class PersistentCapabilityBoundError(ValueError):
    pass

def class_bits(function_class_size:int)->int:
    if not isinstance(function_class_size,int) or isinstance(function_class_size,bool) or function_class_size<1:
        raise PersistentCapabilityBoundError("FUNCTION_CLASS_SIZE_INVALID")
    return 0 if function_class_size==1 else math.ceil(math.log2(function_class_size))

def learned_bits_lower_bound(function_class_size:int, deterministic_code_bits:int)->int:
    if not isinstance(deterministic_code_bits,int) or isinstance(deterministic_code_bits,bool) or deterministic_code_bits<0:
        raise PersistentCapabilityBoundError("CODE_BITS_INVALID")
    return max(0,class_bits(function_class_size)-deterministic_code_bits)

def boolean_function_class_size(input_bits:int)->int:
    if not isinstance(input_bits,int) or isinstance(input_bits,bool) or input_bits<0:
        raise PersistentCapabilityBoundError("INPUT_BITS_INVALID")
    return 1 << (1 << input_bits)

def boolean_function_total_bits_lower_bound(input_bits:int)->int:
    return class_bits(boolean_function_class_size(input_bits))

def certificate(function_class_size:int, deterministic_code_bits:int)->dict:
    total=class_bits(function_class_size)
    learned=learned_bits_lower_bound(function_class_size,deterministic_code_bits)
    return {
        "function_class_size":function_class_size,
        "minimum_total_persistent_capability_bits":total,
        "deterministic_code_bits":deterministic_code_bits,
        "minimum_learned_bits_under_code_budget":learned,
        "deduction":"CODE_AND_LEARNED_BITS_SHARE_A_TOTAL_PERSISTENT_CAPABILITY_INFORMATION_BUDGET",
        "h100_terminal_credit_delta":0
    }
