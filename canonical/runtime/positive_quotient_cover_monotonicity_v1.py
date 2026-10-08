from collections import defaultdict

SCHEMA="PROJECT_BRAIN_POSITIVE_QUOTIENT_COVER_MONOTONICITY_V1"

def verify(regions, policies, adequate_policies_by_region, discriminator_outcomes):
    H=tuple(map(str,regions)); P=tuple(map(str,policies))
    if not H or len(set(H))!=len(H): return {"schema":SCHEMA,"pass":False,"reason":"REGIONS_INVALID","terminal_credit_delta":0}
    if not P or len(set(P))!=len(P): return {"schema":SCHEMA,"pass":False,"reason":"POLICIES_INVALID","terminal_credit_delta":0}
    pset=set(P); adequacy={}
    for h in H:
        if h not in adequate_policies_by_region: return {"schema":SCHEMA,"pass":False,"reason":"ADEQUACY_ROW_MISSING:"+h,"terminal_credit_delta":0}
        vals={str(x) for x in adequate_policies_by_region[h]}
        if not vals <= pset: return {"schema":SCHEMA,"pass":False,"reason":"ADEQUACY_UNKNOWN_POLICY:"+h,"terminal_credit_delta":0}
        adequacy[h]=vals
    qids=tuple(sorted(map(str,discriminator_outcomes.keys())))
    outcomes={}
    for q in qids:
        row=discriminator_outcomes[q]
        if set(map(str,row.keys()))!=set(H):
            return {"schema":SCHEMA,"pass":False,"reason":"DISCRIMINATOR_REGION_DOMAIN_MISMATCH:"+q,"terminal_credit_delta":0}
        outcomes[q]={str(h):repr(row[h]) for h in row}
    groups=defaultdict(list)
    for h in H:
        groups[tuple(outcomes[q][h] for q in qids)].append(h)
    classes=[]; uncovered=[]
    for sig,members in sorted(groups.items(),key=lambda kv:repr(kv[0])):
        common=set(P)
        for h in members: common &= adequacy[h]
        row={"signature":list(sig),"regions":sorted(members),"common_adequate_policies":sorted(common)}
        classes.append(row)
        if not common: uncovered.append(row)
    ok=not uncovered
    return {
      "schema":SCHEMA,"pass":ok,
      "status":"PASS__SELECTED_DISCRIMINATOR_SUBSET_POSITIVE_COVER" if ok else "FAIL_CLOSED__POSITIVE_COVER_NOT_PROVED",
      "selected_discriminator_library_complete_required_for_positive_cover":False,
      "observational_class_count":len(classes),"classes":classes,"uncovered_classes":uncovered,
      "negative_impossibility_authorized":False,
      "scope_completeness_verified":False,"adequacy_receipt_truth_verified":False,
      "brain_ownership_verified":False,"u_empty_authorized":False,
      "abc_closed_authorized":False,"terminal_authority":False,"terminal_credit_delta":0
    }

def verify_theorem():
    a=verify(["w0","w1"],["p"],{"w0":["p"],"w1":["p"]},{})
    assert a["pass"]
    b=verify(["w0","w1"],["p0","p1"],{"w0":["p0"],"w1":["p1"]},{"q":{"w0":0,"w1":1}})
    assert b["pass"]
    c=verify(["w0","w1"],["p0","p1"],{"w0":["p0"],"w1":["p1"]},{})
    assert not c["pass"] and not c["negative_impossibility_authorized"]
    return {"schema":SCHEMA,"status":"PASS__POSITIVE_QUOTIENT_COVER_MONOTONICITY_THEOREM","positive_cover_does_not_require_discriminator_library_completeness":True,"terminal_credit_delta":0}
