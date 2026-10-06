from __future__ import annotations
import math

def bits_needed_for_distinct_worlds(n:int)->int:
    if isinstance(n,bool) or not isinstance(n,int) or n<1:
        raise ValueError("n must be positive integer")
    return 0 if n==1 else math.ceil(math.log2(n))

def messages_available(bits:int)->int:
    if isinstance(bits,bool) or not isinstance(bits,int) or bits<0:
        raise ValueError("bits must be nonnegative integer")
    return 1<<bits

def can_guarantee_all_distinct_worlds(n:int,bits:int)->bool:
    return messages_available(bits)>=n

def verify_cut()->dict[str,object]:
    for n in range(1,65):
        b=bits_needed_for_distinct_worlds(n)
        assert can_guarantee_all_distinct_worlds(n,b)
        if b>0:
            assert not can_guarantee_all_distinct_worlds(n,b-1)
    return {"exact_pigeonhole_bound":True,"checked_world_counts":64}
