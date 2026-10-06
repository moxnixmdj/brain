from __future__ import annotations

class IncompressibilityError(ValueError): pass

def truth_table_bits(input_bits:int)->int:
    if not isinstance(input_bits,int) or isinstance(input_bits,bool) or input_bits<0:
        raise IncompressibilityError("INPUT_BITS_INVALID")
    return 1 << input_bits

def log2_total_boolean_functions(input_bits:int)->int:
    return truth_table_bits(input_bits)

def log2_short_description_fraction_upper_bound(input_bits:int, description_bits:int)->int:
    if not isinstance(description_bits,int) or isinstance(description_bits,bool) or description_bits<0:
        raise IncompressibilityError("DESCRIPTION_BITS_INVALID")
    return description_bits-truth_table_bits(input_bits)

def some_function_requires_more_than(input_bits:int, description_bits:int)->bool:
    return description_bits<truth_table_bits(input_bits)

def minimum_total_bits_for_universal_exact_coverage(input_bits:int)->int:
    return truth_table_bits(input_bits)

def minimum_learned_bits_given_code_budget_for_universal_exact_coverage(input_bits:int, code_bits:int)->int:
    if not isinstance(code_bits,int) or isinstance(code_bits,bool) or code_bits<0:
        raise IncompressibilityError("CODE_BITS_INVALID")
    return max(0,truth_table_bits(input_bits)-code_bits)

def bytes_for_truth_table_bound(input_bits:int)->int:
    bits=truth_table_bits(input_bits)
    return (bits+7)//8

def certificate(input_bits:int, budget_bytes:int)->dict:
    if budget_bytes<0: raise IncompressibilityError("BUDGET_INVALID")
    b=8*budget_bytes
    logfrac=log2_short_description_fraction_upper_bound(input_bits,b)
    return {
        "input_bits":input_bits,
        "budget_bytes":budget_bytes,
        "truth_table_bits":truth_table_bits(input_bits),
        "log2_fraction_with_description_at_most_budget_upper_bound":logfrac,
        "some_function_exceeds_budget":some_function_requires_more_than(input_bits,b),
        "minimum_total_bytes_for_universal_exact_coverage":bytes_for_truth_table_bound(input_bits)
    }
