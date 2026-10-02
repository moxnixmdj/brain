"""Information-safe whole-normalized-rule preflight for structured calculation graphs."""
from __future__ import annotations
import copy, random
from typing import Any, Mapping

BEHAVIOR_ID="STRUCTURED_METHOD_COMPLETE_CALCULATION_GRAPH_001"
ORIGINS=("formula","constraint","schema","standard","feature_callout")

def _D(**kw): return {k:v for k,v in kw.items() if v}

def _base_case(seed:int,ordinal:int)->dict[str,Any]:
    r=random.Random((seed<<19)^ordinal^0x51A7)
    flag=bool(r.getrandbits(1)); mode=r.choice(["FAST","SAFE","AUDIT"]); tier=r.randrange(0,4)
    inputs={
      "A":{"type":"number","dimension":_D(L=1),"value":float(r.randint(2,20))},
      "B":{"type":"number","dimension":_D(L=1),"value":float(r.randint(2,20))},
      "DT":{"type":"number","dimension":_D(T=1),"value":float(r.randint(1,5))},
      "LIMIT":{"type":"number","dimension":_D(L=1,T=-1),"value":float(r.randint(2,20))},
      "K":{"type":"number","dimension":{},"value":float(r.randint(1,4))},
      "FLAG_INPUT":{"type":"bool","dimension":{},"value":flag},
      "MODE_INPUT":{"type":"string","dimension":{},"value":mode},
    }
    rules=[
      {"id":"R_ADD","origin":"formula","op":"add","inputs":["A","B"],"output":"SUM","output_type":"number","output_dimension":_D(L=1)},
      {"id":"R_RATE","origin":"formula","op":"div","inputs":["SUM","DT"],"output":"RATE","output_type":"number","output_dimension":_D(L=1,T=-1),"invariant":{"kind":"finite"}},
      {"id":"R_LIMIT","origin":"constraint","op":"le","inputs":["RATE","LIMIT"],"output":"WITHIN_LIMIT","output_type":"bool","output_dimension":{}},
      {"id":"R_DIFF","origin":"formula","op":"sub","inputs":["A","B"],"output":"DIFF","output_type":"number","output_dimension":_D(L=1)},
      {"id":"R_MAX","origin":"standard","op":"max","inputs":["A","B"],"output":"MAX_AB","output_type":"number","output_dimension":_D(L=1)},
      {"id":"R_MIN","origin":"standard","op":"min","inputs":["A","B"],"output":"MIN_AB","output_type":"number","output_dimension":_D(L=1)},
      {"id":"R_EQ","origin":"schema","op":"eq","inputs":["MODE_INPUT","MODE_INPUT"],"output":"MODE_SELF_EQ","output_type":"bool","output_dimension":{}},
      {"id":"R_GE","origin":"constraint","op":"ge","inputs":["MAX_AB","MIN_AB"],"output":"MAX_GE_MIN","output_type":"bool","output_dimension":{}},
      {"id":"R_GT","origin":"constraint","op":"gt","inputs":["MAX_AB","DIFF"],"output":"MAX_GT_DIFF","output_type":"bool","output_dimension":{}},
      {"id":"R_LT","origin":"constraint","op":"lt","inputs":["MIN_AB","SUM"],"output":"MIN_LT_SUM","output_type":"bool","output_dimension":{}},
      {"id":"R_ALL","origin":"standard","op":"all","inputs":["MODE_SELF_EQ","MAX_GE_MIN","MAX_GT_DIFF","MIN_LT_SUM"],"output":"STRUCTURE_OK","output_type":"bool","output_dimension":{}},
      {"id":"R_ID","origin":"schema","op":"identity","inputs":["SUM"],"output":"SUM_COPY","output_type":"number","output_dimension":_D(L=1),"invariant":{"kind":"positive"}},
      {"id":"R_MUL","origin":"feature_callout","op":"mul","inputs":["RATE","K"],"output":"SCALED_RATE","output_type":"number","output_dimension":_D(L=1,T=-1),"condition":{"key":"flag","op":"eq","value":True}},
      {"id":"R_NEG","origin":"feature_callout","op":"negate","inputs":["DIFF"],"output":"NEG_DIFF","output_type":"number","output_dimension":_D(L=1),"condition":{"key":"flag","op":"neq","value":True}},
      {"id":"R_MODE","origin":"schema","op":"identity","inputs":["MODE_INPUT"],"output":"MODE_COPY","output_type":"string","output_dimension":{},"condition":{"key":"mode","op":"in","value":["SAFE","AUDIT"]},"invariant":{"kind":"member","values":["FAST","SAFE","AUDIT"]}},
      {"id":"R_TIER_GE","origin":"standard","op":"identity","inputs":["K"],"output":"K_GE","output_type":"number","output_dimension":{},"condition":{"key":"tier","op":"ge","value":1},"invariant":{"kind":"nonzero"}},
      {"id":"R_TIER_GT","origin":"standard","op":"identity","inputs":["K"],"output":"K_GT","output_type":"number","output_dimension":{},"condition":{"key":"tier","op":"gt","value":1}},
      {"id":"R_TIER_LE","origin":"standard","op":"identity","inputs":["K"],"output":"K_LE","output_type":"number","output_dimension":{},"condition":{"key":"tier","op":"le","value":2}},
      {"id":"R_TIER_LT","origin":"standard","op":"identity","inputs":["K"],"output":"K_LT","output_type":"number","output_dimension":{},"condition":{"key":"tier","op":"lt","value":3}},
    ]
    r.shuffle(rules)
    return {"behavior_id":BEHAVIOR_ID,"task":{"branch_values":{"flag":flag,"mode":mode,"tier":tier},"inputs":inputs,"rules":rules,"required_outputs":["RATE","WITHIN_LIMIT","STRUCTURE_OK"]}}

def _dim(v): return {k:int(x) for k,x in sorted((v or {}).items()) if int(x)!=0}
def _add(a,b,s=1):
    z=dict(a)
    for k,v in b.items():
        z[k]=z.get(k,0)+s*v
        if not z[k]: del z[k]
    return dict(sorted(z.items()))
def _cond(c,b):
    if not c or c.get("op","always")=="always": return True
    op=c["op"]; x=b[c["key"]]; y=c.get("value")
    if op=="eq": return x==y
    if op=="neq": return x!=y
    if op=="in": return x in y
    if op=="ge": return x>=y
    if op=="gt": return x>y
    if op=="le": return x<=y
    if op=="lt": return x<y
    raise ValueError(op)
def _derive(op,args):
    ts=[x["type"] for x in args]; ds=[x["dimension"] for x in args]
    if op in {"identity","negate"}: return ts[0],dict(ds[0])
    if op in {"add","sub","max","min"}: return "number",dict(ds[0])
    if op=="mul": return "number",_add(ds[0],ds[1])
    if op=="div": return "number",_add(ds[0],ds[1],-1)
    if op in {"eq","ge","gt","le","lt","all"}: return "bool",{}
    raise ValueError(op)
def _oracle(public):
    t=public["task"]; nodes={k:{"id":k,"kind":"input","type":v["type"],"dimension":_dim(v.get("dimension",{}))} for k,v in t["inputs"].items()}
    pending={x["id"]:x for x in t["rules"] if _cond(x.get("condition"),t["branch_values"])}
    exclusions=[{"rule_id":x["id"],"reason":"CONDITION_FALSE","condition":dict(x.get("condition") or {"op":"always"})} for x in t["rules"] if not _cond(x.get("condition"),t["branch_values"])]
    edges=[]; inv=[]; checks=[]; applied=[]
    while pending:
      progress=False
      for rid,r in list(pending.items()):
        if any(x not in nodes for x in r["inputs"]): continue
        typ,dim=_derive(r["op"],[nodes[x] for x in r["inputs"]])
        assert typ==r["output_type"] and dim==_dim(r.get("output_dimension",{}))
        node={"id":r["output"],"kind":"derived","type":typ,"dimension":dim,"rule_id":rid,"origin":r["origin"],"op":r["op"]}; nodes[r["output"]]=node
        for src in r["inputs"]: edges.append({"source":src,"target":r["output"],"rule_id":rid,"origin":r["origin"],"op":r["op"]})
        if "invariant" in r:
          q={"node":r["output"],"kind":r["invariant"]["kind"]}
          if q["kind"]=="member": q["values"]=r["invariant"]["values"]
          inv.append(q)
        checks.append({"rule_id":rid,"target":r["output"],"dependency_count":len(r["inputs"]),"check":"EDGE_CONSEQUENCE"})
        applied.append(rid); del pending[rid]; progress=True
      if not progress: raise ValueError("ORACLE_UNRESOLVED")
    return {"nodes":sorted(nodes.values(),key=lambda x:x["id"]),"edges":sorted(edges,key=lambda x:(x["target"],x["source"],x["rule_id"])),"exclusions":sorted(exclusions,key=lambda x:x["rule_id"]),"invariants":sorted(inv,key=lambda x:(x["node"],x["kind"])),"acceptance_checks":sorted(checks,key=lambda x:x["rule_id"]),"required_outputs":sorted(t["required_outputs"]),"applied_rule_ids":sorted(applied)}

def generate_case(seed:int,ordinal:int)->dict[str,Any]:
    public=_base_case(seed,ordinal); return {"public":public,"_oracle":_oracle(public)}
def public_task(case:Mapping[str,Any])->dict[str,Any]: return copy.deepcopy(case["public"])
def score_case(case:Mapping[str,Any],out:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(out,Mapping): return {"pass":False,"reason":"OUTPUT_NOT_MAPPING"}
    gold=case["_oracle"]; bad=[k for k,v in gold.items() if out.get(k)!=v]
    return {"pass":not bad,"reason":"PASS" if not bad else "MISMATCH:"+",".join(bad)}
def run_batch(seed:int,count:int,solver)->dict[str,Any]:
    fail=[]; origins=set(); conds=set()
    for i in range(count):
      case=generate_case(seed,i); public=public_task(case)
      for r in public["task"]["rules"]:
        origins.add(r["origin"]); conds.add((r.get("condition") or {"op":"always"})["op"])
      try: v=score_case(case,solver(public))
      except Exception as e: v={"pass":False,"reason":type(e).__name__+":"+str(e)}
      if not v["pass"]: fail.append({"ordinal":i,"reason":v["reason"]})
    return {"pass":not fail,"count":count,"failures":fail,"origins":sorted(origins),"condition_ops":sorted(conds),"terminal_authority":False,"capability_credit_delta":0}
