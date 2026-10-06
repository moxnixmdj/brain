from __future__ import annotations
import math
class InstanceAmbiguityError(ValueError): pass
def fixed_state_success_upper_bound(k:int)->float:
 if not isinstance(k,int) or isinstance(k,bool) or k<1: raise InstanceAmbiguityError("K")
 return 1.0/k
def runtime_side_bits_for_exact(k:int)->int:
 if not isinstance(k,int) or isinstance(k,bool) or k<1: raise InstanceAmbiguityError("K")
 return 0 if k==1 else math.ceil(math.log2(k))
def fixed_persistent_bits_help(k:int,bits:int)->bool:
 if not isinstance(bits,int) or isinstance(bits,bool) or bits<0: raise InstanceAmbiguityError("BITS")
 fixed_state_success_upper_bound(k); return False
