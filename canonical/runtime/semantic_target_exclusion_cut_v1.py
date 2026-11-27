from __future__ import annotations
from typing import Any,Mapping,Sequence
from canonical.runtime.semantic_observational_equivalence_cut_v1 import observational_equivalence_classes

def target_exclusion_cut(worlds:Sequence[str],policies:Sequence[str],adequate:Mapping[str,Sequence[str]],queries:Mapping[str,Mapping[str,Any]]):
    ws=tuple(map(str,worlds)); ps=tuple(map(str,policies))
    a={w:set(map(str,adequate[w])) for w in ws}
    classes=observational_equivalence_classes(ws,queries)
    assignment={}; excluded=set()
    for cell in classes:
        best=None
        for p in ps:
            bad=tuple(sorted(w for w in cell if p not in a[w]))
            cand=(len(bad),bad,p)
            if best is None or cand<best: best=cand
        assignment[cell]=best[2]; excluded.update(best[1])
    return {"assignment":assignment,"excluded":tuple(sorted(excluded)),"excluded_count":len(excluded),"terminal_credit_delta":0}

def certify_target_support(worlds,policies,adequate,queries,target_support):
    cut=target_exclusion_cut(worlds,policies,adequate,queries)
    target=set(map(str,target_support))
    return {"certified":target.isdisjoint(set(cut["excluded"])),"target_escape_intersection":tuple(sorted(target&set(cut["excluded"]))),"cut":cut,"exact_target_identity_required":False,"terminal_credit_delta":0}

def find_assignment_for_target_support(worlds,policies,adequate,queries,target_support):
    ws=tuple(map(str,worlds)); ps=tuple(map(str,policies)); target=set(map(str,target_support))
    a={w:set(map(str,adequate[w])) for w in ws}
    classes=observational_equivalence_classes(ws,queries); assignment={}; excluded=set()
    for cell in classes:
        occupied=[w for w in cell if w in target]
        if not occupied:
            assignment[cell]=ps[0]; continue
        common=set(ps)
        for w in occupied: common &= a[w]
        if not common:
            return {"certified":False,"assignment":assignment,"reason":"NO_COMMON_POLICY_ON_TARGET_OCCUPIED_EQUIVALENCE_CELL","cell":cell,"terminal_credit_delta":0}
        p=sorted(common)[0]; assignment[cell]=p
        excluded.update(w for w in cell if p not in a[w])
    return {"certified":target.isdisjoint(excluded),"assignment":assignment,"excluded":tuple(sorted(excluded)),"exact_target_identity_required":False,"terminal_credit_delta":0}
