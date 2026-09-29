#!/usr/bin/env python3
"""Independent verifier for plain-goal bound-capability grounding."""
from __future__ import annotations
import json, pathlib, re

GENERIC={
 "a","an","and","as","at","be","best","bound","by","capability","capabilities",
 "choose","cost","existing","for","from","in","independent","into","is","it","of",
 "on","or","output","result","route","select","the","them","then","through","to",
 "using","verified","with","zero","already","available","brain"
}
def toks(v):
    if isinstance(v,(list,tuple,set)): v=" ".join(map(str,v))
    return {x.lower() for x in re.findall(r"[A-Za-z0-9]+",str(v or "")) if len(x)>=2 and x.lower() not in GENERIC}
def overlaps(a,b):
    return {(x,y) for x in a for y in b if x==y or (min(len(x),len(y))>=5 and x[:5]==y[:5])}

def verify(result,registry):
    if result.get("schema")!="PROJECT_BRAIN_PLAIN_GOAL_BOUND_GROUNDING_V1": return False,"SCHEMA"
    goal=toks(result.get("goal"))
    actual={str(x.get("capability_id")):x for x in result.get("candidates",[]) if isinstance(x,dict)}
    expected=set()
    for cid,e in sorted((registry or {}).items()):
        if cid=="goal.ground.bound_capabilities.stdlib" or not isinstance(e,dict) or e.get("status")!="VERIFIED_BOUND_CAPABILITY": continue
        try:
            if float(e.get("incremental_spend_usd",0) or 0)!=0: continue
        except Exception: continue
        p=overlaps(goal,toks(e.get("provides") or []))
        k=overlaps(goal,toks(e.get("keywords") or []))
        i=overlaps(goal,toks(cid))
        r=overlaps(goal,toks(e.get("requires") or []))
        distinct={x for x,_ in (p|k|i)}
        score=8*len(p)+4*len(k)+2*len(i)+len(r)
        if (p or len(distinct)>=2) and score>=6:
            expected.add(str(cid))
    # Producer is intentionally bounded to max_candidates. Verify no admitted
    # item is unjustified, and that every expected item is present when the
    # expected set fits in the producer's bounded result.
    if not set(actual).issubset(expected): return False,"UNJUSTIFIED_CANDIDATE"
    if len(expected)<=16 and set(actual)!=expected: return False,"EXPECTED_CANDIDATE_OMITTED"
    if bool(actual)!=(result.get("status")=="GROUNDED"): return False,"STATUS_MISMATCH"
    if result.get("external_discovery_allowed") is bool(actual): return False,"DISCOVERY_POLICY_MISMATCH"
    if result.get("model_dependency_count")!=0: return False,"MODEL_DEPENDENCY"
    return True,"PASS"

def run(payload,root):
    root=pathlib.Path(root).resolve()
    result_path=(root/str(payload["result_path"])).resolve()
    result=json.loads(result_path.read_text(encoding="utf-8"))
    registry=json.loads((root/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8"))
    registry=registry.get("capabilities",registry)
    ok,reason=verify(result,registry)
    return {"verified":ok,"reason":reason,"candidate_count":len(result.get("candidates",[])),"model_dependency_count":0}
