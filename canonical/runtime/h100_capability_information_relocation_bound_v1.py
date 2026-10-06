from __future__ import annotations
import math

class RelocationBoundError(ValueError): pass

def class_bits(config_count:int)->int:
    if not isinstance(config_count,int) or isinstance(config_count,bool) or config_count<1:
        raise RelocationBoundError("CONFIG_COUNT_INVALID")
    return 0 if config_count==1 else math.ceil(math.log2(config_count))

def minimum_missing_bits(config_count:int,internal_bits:int,external_bits:int,code_bits:int)->int:
    for x in (internal_bits,external_bits,code_bits):
        if not isinstance(x,int) or isinstance(x,bool) or x<0:
            raise RelocationBoundError("BITS_INVALID")
    need=class_bits(config_count)
    return max(0,need-internal_bits-external_bits-code_bits)

def total_capacity_sufficient(config_count:int,internal_bits:int,external_bits:int,code_bits:int)->bool:
    return minimum_missing_bits(config_count,internal_bits,external_bits,code_bits)==0

def relocation_example(config_count:int,total_bits:int)->list[dict]:
    if total_bits<0: raise RelocationBoundError("BITS_INVALID")
    rows=[]
    for internal in range(total_bits+1):
        external=total_bits-internal
        rows.append({
          "internal_bits":internal,
          "external_bits":external,
          "code_bits":0,
          "sufficient":total_capacity_sufficient(config_count,internal,external,0)
        })
    return rows
