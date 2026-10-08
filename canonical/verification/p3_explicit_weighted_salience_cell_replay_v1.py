from __future__ import annotations
import itertools, json, random
from canonical.runtime.p3_explicit_weighted_salience_cell_v1 import evaluate
from canonical.runtime.synthesis_certified_visible_support_policy_v3 import INPUT_SCHEMA

def constraints(max_items):
    return {
        "output_format":"BULLETS","citation_mode":"INLINE_SOURCE_IDS",
        "style":"VERBATIM_GROUNDED","required_sections":[],"allowed_sections":None,
        "max_items":max_items,"max_chars":100000,"heading_level":2,"require_title":False,
    }

def make_case(weights, required_ids, max_items):
    ids=sorted(weights)
    claims=[]; evidence=[]
    for i,cid in enumerate(ids):
        claims.append({"claim_id":cid,"text":f"Item{i} value is {i+1}.","required":cid in required_ids})
        evidence.append({"evidence_id":"E"+cid,"text":f"Source{cid} states Item{i} value is {i+1}.",
                         "verified":True,"provenance":[{"source_id":"S"+cid,"locator":"p1"}]})
    return {"objective_weights":dict(weights),"v3_input":{"schema":INPUT_SCHEMA,"task":{
        "claims":claims,"evidence":evidence,
        "audience_profile":{"profile_id":"EXPLICIT","constraints":constraints(max_items)},
        "required_uncertainty_units":[]}}}

def brute(weights, required_ids, max_items):
    optional=[x for x in weights if x not in required_ids and weights[x]>0]
    slots=max_items-len(required_ids)
    best=None
    for r in range(len(optional)+1):
        for subset in itertools.combinations(optional,r):
            if len(subset)>slots: continue
            chosen=set(required_ids)|set(subset)
            value=sum(weights[x] for x in chosen)
            optional_order=sorted(subset,key=lambda x:(-weights[x],x))
            key=(value, tuple(optional_order))
            if best is None or value>best[0]:
                best=(value,chosen)
            elif value==best[0]:
                # implementation's deterministic optimum is top weights, then ids.
                impl=sorted(chosen-set(required_ids),key=lambda x:(-weights[x],x))
                prev=sorted(best[1]-set(required_ids),key=lambda x:(-weights[x],x))
                if tuple(impl)<tuple(prev): best=(value,chosen)
    chosen=best[1]
    order=sorted(chosen,key=lambda x:(-weights[x],x))
    return [x for x in sorted(weights) if x in chosen], order, best[0]

checks=0
# Directed positive/tie/negative cases.
for weights,req,cap in [
    ({"A":10,"B":5,"C":1},{"A"},2),
    ({"A":-5,"B":7,"C":7},{"A"},2),
    ({"A":1,"B":0,"C":-1},{"A"},3),
    ({"A":3,"B":9,"C":2,"D":8},{"A","C"},3),
    ({"A":5,"B":5,"C":5},set(),2),
    ({"A":-2,"B":9},set(),1),
    ({"A":4},{"A"},1),
    ({"A":4,"B":6},{"A","B"},2),
]:
    p=make_case(weights,req,cap); out=evaluate(p)
    assert out["pass"],out
    es,eo,ev=brute(weights,req,cap)
    assert out["selected_claim_ids"]==es,(out,es)
    assert out["claim_order"]==eo,(out,eo)
    assert out["objective_value"]==ev,(out,ev)
    assert out["terminal_credit_delta"]==0
    checks+=1

rng=random.Random(10082026)
for n in range(600):
    count=rng.randint(1,7)
    ids=[chr(65+i) for i in range(count)]
    weights={cid:rng.randint(-5,12) for cid in ids}
    required={cid for cid in ids if rng.random()<0.28}
    cap=rng.randint(len(required),count)
    p=make_case(weights,required,cap)
    out=evaluate(p)
    es,eo,ev=brute(weights,required,cap)
    if not es:
        assert out["pass"] is False,(n,out,p)
        assert out["reason"]=="OBJECTIVE_SELECTS_NO_CLAIMS",(n,out)
    else:
        assert out["pass"],(n,out,p)
        assert out["selected_claim_ids"]==es,(n,out["selected_claim_ids"],es,weights,required,cap)
        assert out["claim_order"]==eo,(n,out["claim_order"],eo)
        assert out["objective_value"]==ev,(n,out["objective_value"],ev)
        assert not out["db_admission_authority"] and not out["u_subtraction_authority"]
    checks+=1

# Adversarial failures.
p=make_case({"A":2,"B":1},{"A"},2); p["objective_weights"].pop("B")
assert evaluate(p)["reason"]=="OBJECTIVE_WEIGHTS_MUST_EXACTLY_COVER_ALL_CLAIMS"; checks+=1
p=make_case({"A":2,"B":1},{"A"},2); p["v3_input"]["task"]["claims"][1]["include"]=True
assert evaluate(p)["reason"]=="CALLER_INCLUDE_FORBIDDEN"; checks+=1
p=make_case({"A":2,"B":1},{"A"},2); p["v3_input"]["task"]["claim_order"]=["A","B"]
assert evaluate(p)["reason"]=="CALLER_CLAIM_ORDER_FORBIDDEN"; checks+=1
p=make_case({"A":2,"B":1},{"A"},2); p["v3_input"]["task"]["required_uncertainty_units"]=[{"uncertainty_id":"U","text":"Unknown.","provenance":[{"source_id":"S","locator":"p"}]}]
assert evaluate(p)["reason"]=="NONEMPTY_OR_UNBOUND_UNCERTAINTY_OUTSIDE_WEIGHTED_CELL"; checks+=1
p=make_case({"A":2},{"A"},1); p["v3_input"]["task"]["evidence"].append({"evidence_id":"BAD","text":"Other states Item0 value is 999.","verified":True,"provenance":[{"source_id":"O","locator":"p"}]})
assert evaluate(p)["reason"]=="CONFLICT_REQUIRES_UNCERTAINTY_SEMANTICS"; checks+=1
p=make_case({"A":2},{"A"},1); del p["v3_input"]["task"]["audience_profile"]["constraints"]["max_chars"]
assert evaluate(p)["reason"]=="AUDIENCE_FORMAT_CONTRACT_NOT_EXPLICITLY_COMPLETE"; checks+=1
p=make_case({"A":2},{"A"},1); p["v3_input"]["task"]["evidence"][0]["verified"]=False
assert evaluate(p)["reason"]=="UNVERIFIED_EVIDENCE_UNIT"; checks+=1
p=make_case({"A":2},{"A"},1); p["objective_weights"]["A"]=2.5
assert evaluate(p)["reason"]=="INTEGER_OBJECTIVE_WEIGHT_REQUIRED"; checks+=1
p=make_case({"A":2},{"A"},1); p["v3_input"]["task"]["audience_profile"]["persona"]="executive"
assert evaluate(p)["reason"]=="UNMODELED_AUDIENCE_PROFILE_FIELDS"; checks+=1

print(json.dumps({"pass":True,"checks":checks,"random_exhaustive_crosschecks":600,
                  "directed_positive":8,"adversarial_fail_closed":9,
                  "terminal_credit_delta":0},sort_keys=True))
