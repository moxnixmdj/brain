"""Independent Python-stdlib replay, no pytest or remote model needed."""
import copy
import hashlib
import json
import random
from canonical.runtime.p3_audience_grounded_numeric_synthesis_v1 import solve, UnresolvedEvidence
CONTRACT="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
PREF={"executive":"trend","engineer":"mechanism","auditor":"control","operator":"operational"}
def case(audience="executive", value="105"):
    return {"contract":CONTRACT,"task":{
        "audience":audience,"required_claims":["req"],
        "claims":[
            {"claim_id":"req","metric":"m","unit":"kg","kind":"risk","relation":"at_least","threshold":"100"},
            *[{"claim_id":k,"metric":"m","unit":"kg","kind":v,"relation":"at_least","threshold":"100"}
              for k,v in [("trend","trend"),("mechanism","mechanism"),("control","control"),("operational","operational")]],
        ],
        "evidence":[{"evidence_id":"e","metric":"m","unit":"kg","value":value,"source_id":"src"}],
        "format_constraints":{"max_claims":2,"ordered_required_first":True}
    }}
checks=0
for audience,kind in PREF.items():
    out=solve(case(audience))
    assert out["selected_claims"]==["req",kind],(audience,out)
    assert out["source_authorization_verified"] is False
    assert out["terminal_credit_delta"]==0
    assert out["claim_provenance"]["req"][0]["evidence_id"]=="e"
    checks+=1
rng=random.Random(7721)
for i in range(200):
    v=rng.randint(100,300)
    audience=rng.choice(list(PREF))
    output=solve(case(audience,str(v)))
    assert output["selected_claims"]==["req",PREF[audience]]
    assert output["uncertainty_claims"]==[]
    checks+=1
for bad in ["99.999999999999999999999","NaN","Infinity","-Infinity","not-number"]:
    p=case(value=bad)
    try:
        solve(p)
    except UnresolvedEvidence:
        checks+=1
    else:
        raise AssertionError("unverified truth admitted: "+bad)
p=case()
p["task"]["evidence"][0]["support"]="supported"
try:
    solve(p)
except UnresolvedEvidence:
    checks+=1
else:
    raise AssertionError("hidden support accepted")
p=case()
p["task"]["claims"][1]["relevance"]="required"
try:
    solve(p)
except UnresolvedEvidence:
    checks+=1
else:
    raise AssertionError("hidden relevance accepted")
p=case()
p["task"]["audience"]="auditor"
a=solve(p)
p["task"]["audience"]="engineer"
b=solve(p)
assert a["input_sha256"]!=b["input_sha256"]
checks+=1
print(json.dumps({"pass":True,"carrier":"separate_running_sprite","stdlib_only":True,
                  "adversarial_checks":checks,"terminal_credit":0}))
