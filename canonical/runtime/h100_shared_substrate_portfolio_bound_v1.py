from __future__ import annotations
import math

class PortfolioBoundError(ValueError): pass

def _n(x,name):
    if not isinstance(x,int) or isinstance(x,bool) or x<0:
        raise PortfolioBoundError(name)
    return x

def portfolio_bits(shared_bits:int, patch_bits:list[int])->int:
    s=_n(shared_bits,"SHARED_BITS_INVALID")
    if not isinstance(patch_bits,list):
        raise PortfolioBoundError("PATCH_BITS_INVALID")
    return s+sum(_n(x,"PATCH_BITS_INVALID") for x in patch_bits)

def primitive_delta(*,added_shared_bits:int,before_patch_bits:list[int],after_patch_bits:list[int])->dict:
    added=_n(added_shared_bits,"ADDED_SHARED_BITS_INVALID")
    if len(before_patch_bits)!=len(after_patch_bits):
        raise PortfolioBoundError("PATCH_LENGTH_MISMATCH")
    before=sum(_n(x,"PATCH_BITS_INVALID") for x in before_patch_bits)
    after=sum(_n(x,"PATCH_BITS_INVALID") for x in after_patch_bits)
    savings=before-after
    return {
        "added_shared_bits":added,
        "aggregate_patch_savings_bits":savings,
        "net_portfolio_delta_bits":added-savings,
        "beneficial":savings>added,
        "break_even_or_better":savings>=added,
    }

def uniform_break_even_reuse_count(added_shared_bits:int,per_use_patch_savings_bits:int)->int|None:
    a=_n(added_shared_bits,"ADDED_SHARED_BITS_INVALID")
    s=_n(per_use_patch_savings_bits,"SAVINGS_INVALID")
    if s==0: return None
    return math.ceil(a/s)

def compare(shared_before:int,patch_before:list[int],shared_after:int,patch_after:list[int])->dict:
    b=portfolio_bits(shared_before,patch_before)
    a=portfolio_bits(shared_after,patch_after)
    return {"before_bits":b,"after_bits":a,"delta_bits":a-b,"improved":a<b}
