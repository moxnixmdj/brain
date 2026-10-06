from __future__ import annotations

class ComplexityBoundError(ValueError): pass

def interval(lower_bits:int, upper_bits:int, *, time_budget:int, memory_bytes:int):
    vals=(lower_bits,upper_bits,time_budget,memory_bytes)
    if any((not isinstance(x,int)) or isinstance(x,bool) or x<0 for x in vals):
        raise ComplexityBoundError("NONNEGATIVE_INTEGER_REQUIRED")
    if lower_bits>upper_bits:
        raise ComplexityBoundError("LOWER_EXCEEDS_UPPER")
    return {
        "lower_bits":lower_bits,
        "upper_bits":upper_bits,
        "gap_bits":upper_bits-lower_bits,
        "time_budget":time_budget,
        "memory_bytes":memory_bytes,
    }

def tighten(current:dict, *, new_lower_bits:int|None=None, new_upper_bits:int|None=None):
    lo=current["lower_bits"]; hi=current["upper_bits"]
    if new_lower_bits is not None: lo=max(lo,int(new_lower_bits))
    if new_upper_bits is not None: hi=min(hi,int(new_upper_bits))
    return interval(lo,hi,time_budget=current["time_budget"],memory_bytes=current["memory_bytes"])

def encoding_total_bits(*parts:int)->int:
    if any((not isinstance(x,int)) or isinstance(x,bool) or x<0 for x in parts):
        raise ComplexityBoundError("ENCODING_PART_INVALID")
    return sum(parts)

def representation_invariant_total(*,learned_bits:int,deterministic_bits:int)->int:
    return encoding_total_bits(learned_bits,deterministic_bits)

def explicit_upper_bound(program_bytes:int, auxiliary_persistent_bytes:int=0)->int:
    if program_bytes<0 or auxiliary_persistent_bytes<0:
        raise ComplexityBoundError("BYTE_COUNT_INVALID")
    return 8*(program_bytes+auxiliary_persistent_bytes)

def record(scope_id:str, reference_machine_id:str, runtime_information_id:str, *, lower_bits:int, upper_bits:int, time_budget:int, memory_bytes:int):
    if not all(isinstance(x,str) and x for x in (scope_id,reference_machine_id,runtime_information_id)):
        raise ComplexityBoundError("ID_INVALID")
    out=interval(lower_bits,upper_bits,time_budget=time_budget,memory_bytes=memory_bytes)
    return {
        "scope_id":scope_id,
        "reference_machine_id":reference_machine_id,
        "runtime_information_id":runtime_information_id,
        **out,
        "exact_complexity_claimed":False
    }
