from __future__ import annotations
import math

class ObservationAmbiguityError(ValueError): pass

def quantized_height(value:int,pixels_per_unit:float)->int:
    if not isinstance(value,int) or isinstance(value,bool): raise ObservationAmbiguityError("VALUE_INVALID")
    p=float(pixels_per_unit)
    if not math.isfinite(p) or p<=0: raise ObservationAmbiguityError("SCALE_INVALID")
    return round(value*p)

def integer_preimage(height:int,pixels_per_unit:float,lo:int,hi:int):
    if not all(isinstance(x,int) and not isinstance(x,bool) for x in (height,lo,hi)) or lo>hi:
        raise ObservationAmbiguityError("DOMAIN_INVALID")
    return [v for v in range(lo,hi+1) if quantized_height(v,pixels_per_unit)==height]

def joint_class_size(heights,pixels_per_unit,lo:int,hi:int)->int:
    total=1
    for h in heights:
        vals=integer_preimage(int(h),pixels_per_unit,lo,hi)
        if not vals: raise ObservationAmbiguityError("EMPTY_PREIMAGE")
        total*=len(vals)
    return total

def missing_instance_bits(heights,pixels_per_unit,lo:int,hi:int)->int:
    k=joint_class_size(heights,pixels_per_unit,lo,hi)
    return 0 if k<=1 else math.ceil(math.log2(k))

def certificate(heights,pixels_per_unit,lo:int,hi:int):
    pre=[integer_preimage(int(h),pixels_per_unit,lo,hi) for h in heights]
    k=joint_class_size(heights,pixels_per_unit,lo,hi)
    return {
        "preimages":pre,
        "joint_equivalence_class_size":k,
        "missing_instance_information_lower_bound_bits":0 if k<=1 else math.ceil(math.log2(k)),
        "persistent_capability_bits_lower_bound_delta":0,
        "deduction":"OBSERVATION_NONINJECTIVITY_CREATES_INSTANCE_INFORMATION_LOSS_NOT_CAPABILITY_DESCRIPTION_REQUIREMENT"
    }
