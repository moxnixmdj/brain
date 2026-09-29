#!/usr/bin/env python3
"""Deterministic plain-goal grounding over Project Brain's verified bound registry."""
from __future__ import annotations
import hashlib, json, pathlib, re

SCHEMA="PROJECT_BRAIN_PLAIN_GOAL_BOUND_GROUNDING_V1"
GENERIC={
 "a","an","and","as","at","be","best","bound","by","capability","capabilities",
 "choose","cost","existing","for","from","in","independent","into","is","it","of",
 "on","or","output","result","route","select","the","them","then","through","to",
 "using","verified","with","zero","already","available","brain"
}

def _tokens(value):
    if isinstance(value,(list,tuple,set)):
        value=" ".join(str(x) for x in value)
    return {
        x.lower() for x in re.findall(r"[A-Za-z0-9]+",str(value or ""))
        if len(x)>=2
    }

def _distinct(tokens):
    return {x for x in tokens if x not in GENERIC}

def _overlap(left,right):
    pairs=set()
    for a in _distinct(left):
        for b in _distinct(right):
            if a==b or (min(len(a),len(b))>=5 and a[:5]==b[:5]):
                pairs.add((a,b))
    return pairs

def _verified_zero_cost(entry):
    if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return False
    try:
        return float(entry.get("incremental_spend_usd",0) or 0)==0
    except Exception:
        return False

def ground(goal, registry, max_candidates=16):
    goal=" ".join(str(goal or "").split())
    if not goal:
        raise ValueError("GOAL_REQUIRED")
    gt=_tokens(goal)
    ranked=[]
    for cid,entry in sorted((registry or {}).items()):
        if cid=="goal.ground.bound_capabilities.stdlib" or not _verified_zero_cost(entry):
            continue
        provides=_tokens(entry.get("provides") or [])
        keywords=_tokens(entry.get("keywords") or [])
        identity=_tokens(cid)
        requires=_tokens(entry.get("requires") or [])
        p=_overlap(gt,provides)
        k=_overlap(gt,keywords)
        i=_overlap(gt,identity)
        r=_overlap(gt,requires)
        distinctive=sorted({a for a,_ in (p|k|i)})
        # A provided-effect match is direct semantic evidence. Without one,
        # require at least two distinct keyword/identity matches. Preconditions
        # refine a candidate but can never create one.
        admitted=bool(p) or len(distinctive)>=2
        if not admitted:
            continue
        score=8*len(p)+4*len(k)+2*len(i)+len(r)
        if score<6:
            continue
        ranked.append({
          "capability_id":str(cid),
          "score":score,
          "matched_goal_tokens":distinctive,
          "matched_provides":sorted([list(x) for x in p]),
          "matched_keywords":sorted([list(x) for x in k]),
          "matched_identity":sorted([list(x) for x in i]),
          "matched_requires":sorted([list(x) for x in r]),
          "provides":list(entry.get("provides") or []),
          "requires":list(entry.get("requires") or []),
          "incremental_spend_usd":float(entry.get("incremental_spend_usd",0) or 0),
        })
    ranked.sort(key=lambda x:(-x["score"],-len(x["matched_goal_tokens"]),x["capability_id"]))
    ranked=ranked[:max(1,min(int(max_candidates),64))]
    return {
      "schema":SCHEMA,
      "goal":goal,
      "goal_sha256":hashlib.sha256(goal.encode("utf-8")).hexdigest(),
      "status":"GROUNDED" if ranked else "ABSTAIN_NO_JUSTIFIED_BOUND_CAPABILITY",
      "candidates":ranked,
      "candidate_count":len(ranked),
      "external_discovery_allowed":not bool(ranked),
      "model_dependency_count":0,
      "policy":"BOUND_VERIFIED_ZERO_COST_REGISTRY_FIRST__PRESERVE_MULTI_CANDIDATE_SET__ABSTAIN_ON_NO_JUSTIFIED_MATCH",
    }

def run(payload, root):
    root=pathlib.Path(root).resolve()
    goal=str((payload or {}).get("goal") or "")
    registry_path=root/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
    registry=json.loads(registry_path.read_text(encoding="utf-8"))
    registry=registry.get("capabilities",registry)
    result=ground(goal,registry,(payload or {}).get("max_candidates",16))
    output_path=(payload or {}).get("output_path")
    if output_path:
        out=(root/str(output_path)).resolve()
        if root not in out.parents and out!=root:
            raise ValueError("OUTPUT_PATH_OUTSIDE_ROOT")
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        result["output_path"]=str(out.relative_to(root))
    result["output_verified"]=True
    return result
