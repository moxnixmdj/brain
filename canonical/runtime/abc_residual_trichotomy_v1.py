from __future__ import annotations

def classify(worlds, policies, dominates, partition):
    worlds=tuple(worlds); policies=tuple(policies)
    W=set(worlds)
    if set().union(*(set(c) for c in partition)) != W:
        raise ValueError("PARTITION_COVER_MISMATCH")
    seen=set()
    for c in partition:
        s=set(c)
        if not s or seen & s:
            raise ValueError("PARTITION_NOT_DISJOINT")
        seen |= s
    def covers(p,cell):
        return all(bool(dominates.get((p,w),False)) for w in cell)
    uncovered_cells=[]
    witnesses={}
    for idx,cell in enumerate(partition):
        ps=[p for p in policies if covers(p,cell)]
        if ps:
            witnesses[idx]=ps
        else:
            uncovered_cells.append(list(cell))
    M=[w for w in worlds if not any(bool(dominates.get((p,w),False)) for p in policies)]
    robust=[p for p in policies if covers(p,worlds)]
    return {
      "closed_under_current_information":not uncovered_cells,
      "robust_policies":robust,
      "cell_cover_witnesses":witnesses,
      "uncovered_information_cells":uncovered_cells,
      "singleton_capability_region":M,
      "capability_gap_proved":False,
      "rule":"M_MEMBERSHIP_IS_A_CAPABILITY_GAP_REGION__ACTUAL_GAP_REQUIRES_TARGET_OCCUPANCY_OR_UNAVOIDABILITY_PROOF",
    }

if __name__=="__main__":
    import json
    worlds=["mu0","mu1"]
    policies=["p0","p1"]
    dominance={("p0","mu0"):True,("p1","mu1"):True}
    print(json.dumps(classify(worlds,policies,dominance,[worlds]),indent=2,sort_keys=True))
