from __future__ import annotations

def success_pair(prob_action0: float)->tuple[float,float]:
    if isinstance(prob_action0,bool) or not isinstance(prob_action0,(int,float)):
        raise TypeError("prob_action0 must be numeric")
    q=float(prob_action0)
    if q<0 or q>1:
        raise ValueError("probability out of range")
    # Same precommitment observation in both worlds forces same action distribution.
    return (q,1.0-q)

def worst_case_success(prob_action0: float)->float:
    return min(success_pair(prob_action0))

def best_symmetric_worst_case(grid:int=1000)->float:
    if grid<=0:
        raise ValueError("grid must be positive")
    return max(worst_case_success(i/grid) for i in range(grid+1))

def mapping_aware_success()->tuple[float,float]:
    return (1.0,1.0)

def verify()->dict[str,object]:
    bound=best_symmetric_worst_case()
    assert abs(bound-0.5)<1e-12
    assert mapping_aware_success()==(1.0,1.0)
    return {"permutation_blind_worst_case_upper_bound":bound,"mapping_breaks_symmetry":True}
