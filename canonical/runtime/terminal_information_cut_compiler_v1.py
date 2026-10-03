"""Deterministic minimum information-cut compiler over verified candidate actions.

The compiler does not invent semantic equivalences, proofs, observations, or
capabilities. It accepts only independently verified, content-addressed action
candidates whose declared coverage is a subset of the current primitive cut,
then computes the lexicographically minimum complete cover.

Multiplexing is explicit: one verified action may cover multiple primitive
facts while paying its reality/capability/verification cost once.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TERMINAL_INFORMATION_CUT_COMPILER_V1"
HEX=set("0123456789abcdef")
CLASSES={"EXISTING_PROOF_REUSE","UNIVERSAL_THEOREM","SAFE_OBSERVATION","MATCHED_COMPARATOR","CAPABILITY_ACQUISITION"}

def _sha(v:Any)->bool:
    return isinstance(v,str) and len(v)==40 and set(v.lower())<=HEX

def _nonneg(v:Any)->bool:
    return not isinstance(v,bool) and isinstance(v,int) and v>=0

def _receipt(v:Any)->bool:
    return isinstance(v,Mapping) and v.get("independent") is True and str(v.get("status","")).startswith("INDEPENDENT") and isinstance(v.get("path"),str) and bool(v.get("path")) and _sha(v.get("git_blob_sha"))

def _fail(*errors:str)->dict[str,Any]:
    return {"schema":SCHEMA,"status":"FAIL_CLOSED","complete_cover":False,"errors":sorted(set(errors)),
            "new_reality_units_consumed":0,"capability_credit_delta":0,"family_credit_delta":0,
            "execution_authority":False,"promotion_authority":False}

def compile_cut(doc:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(doc,Mapping) or doc.get("schema")!=SCHEMA:
        return _fail("SCHEMA_INVALID")
    facts_raw=doc.get("primitive_facts"); actions_raw=doc.get("actions")
    if not isinstance(facts_raw,list) or not facts_raw or any(not isinstance(x,str) or not x for x in facts_raw):
        return _fail("PRIMITIVE_FACTS_INVALID")
    if len(facts_raw)!=len(set(facts_raw)):
        return _fail("PRIMITIVE_FACTS_DUPLICATE")
    if not isinstance(actions_raw,list):
        return _fail("ACTIONS_INVALID")

    facts=sorted(facts_raw); index={f:i for i,f in enumerate(facts)}
    actions=[]; errors=[]; seen=set()
    for i,raw in enumerate(actions_raw):
        if not isinstance(raw,Mapping):
            errors.append(f"ACTION_NOT_OBJECT:{i}"); continue
        aid=raw.get("id"); cls=raw.get("action_class"); covers=raw.get("covers")
        if not isinstance(aid,str) or not aid or aid in seen:
            errors.append(f"ACTION_ID_INVALID_OR_DUPLICATE:{i}"); continue
        seen.add(aid)
        if cls not in CLASSES:
            errors.append(f"ACTION_CLASS_INVALID:{aid}"); continue
        if not isinstance(covers,list) or not covers or any(not isinstance(x,str) or x not in index for x in covers):
            errors.append(f"ACTION_COVERAGE_INVALID:{aid}"); continue
        if len(covers)!=len(set(covers)):
            errors.append(f"ACTION_COVERAGE_DUPLICATE:{aid}"); continue
        if not _receipt(raw.get("feasibility_receipt")):
            errors.append(f"ACTION_FEASIBILITY_NOT_INDEPENDENT_CONTENT_ADDRESSED:{aid}"); continue
        c=raw.get("cost")
        if not isinstance(c,Mapping):
            errors.append(f"ACTION_COST_INVALID:{aid}"); continue
        vals=(c.get("new_reality_units"),c.get("capability_acquisition_units"),c.get("verification_units"))
        if any(not _nonneg(v) for v in vals):
            errors.append(f"ACTION_COST_INVALID:{aid}"); continue
        mask=0
        for f in covers: mask|=1<<index[f]
        actions.append({"id":aid,"action_class":cls,"covers":sorted(covers),"mask":mask,
                        "cost":(int(vals[0]),int(vals[1]),int(vals[2]),1)})
    if errors: return _fail(*errors)

    full=(1<<len(facts))-1
    best={0:((0,0,0,0),())}
    for action in sorted(actions,key=lambda x:x["id"]):
        for mask,(cost,ids) in list(best.items()):
            nm=mask|action["mask"]
            nc=tuple(x+y for x,y in zip(cost,action["cost"]))
            ni=tuple(sorted(ids+(action["id"],)))
            cand=(nc,ni)
            if nm not in best or cand<best[nm]: best[nm]=cand

    if full not in best:
        coverable=0
        for a in actions: coverable|=a["mask"]
        uncovered=[f for f,i in index.items() if not (coverable&(1<<i))]
        return {"schema":SCHEMA,"status":"PASS__INCOMPLETE_VERIFIED_ACTION_COVER","complete_cover":False,
                "selected_actions":[],"uncovered_facts":sorted(uncovered),
                "rule":"NO_UNVERIFIED_ACTION_OR_UNDECLARED_SEMANTIC_COVERAGE_IS_INVENTED",
                "new_reality_units_consumed":0,"capability_credit_delta":0,"family_credit_delta":0,
                "execution_authority":False,"promotion_authority":False}

    cost,ids=best[full]; selected=[next(a for a in actions if a["id"]==aid) for aid in ids]
    return {"schema":SCHEMA,"status":"PASS__EXACT_MINIMUM_VERIFIED_INFORMATION_CUT","complete_cover":True,
            "selected_actions":list(ids),
            "selected_action_classes":{a["id"]:a["action_class"] for a in selected},
            "selected_coverage":{a["id"]:a["covers"] for a in selected},
            "objective":{"new_reality_units":cost[0],"capability_acquisition_units":cost[1],
                         "verification_units":cost[2],"action_count":cost[3]},
            "covered_fact_count":len(facts),"primitive_fact_count":len(facts),
            "rule":"MINIMIZE_NEW_REALITY_THEN_CAPABILITY_ACQUISITION_THEN_VERIFICATION_THEN_ACTION_COUNT__MULTIFACT_CREDIT_ONLY_FROM_ONE_INDEPENDENTLY_VERIFIED_MULTIFACT_ACTION",
            "new_reality_units_consumed":0,"capability_credit_delta":0,"family_credit_delta":0,
            "execution_authority":False,"promotion_authority":False}
