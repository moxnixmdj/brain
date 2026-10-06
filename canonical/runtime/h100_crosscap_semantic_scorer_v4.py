from __future__ import annotations
import math
from typing import Any,Mapping,Sequence

def _eq(a,b):
 if isinstance(a,(int,float)) and isinstance(b,(int,float)):
  return math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=1e-9)
 if isinstance(a,list) and isinstance(b,list):
  return len(a)==len(b) and all(_eq(x,y) for x,y in zip(a,b))
 if isinstance(a,dict) and isinstance(b,dict):
  return set(a)==set(b) and all(_eq(a[k],b[k]) for k in a)
 return a==b

def validate_plan(task,plan):
 if not isinstance(plan,list): return {"valid":False,"cost":None}
 state=set(map(str,task["initial_resources"])); by={str(o["operator_id"]):o for o in task["operators"]}; cost=0.0
 for oid in plan:
  op=by.get(str(oid))
  if op is None: return {"valid":False,"cost":None}
  if not set(map(str,op.get("requires",[]))).issubset(state): return {"valid":False,"cost":None}
  state.difference_update(map(str,op.get("removes",[]))); state.update(map(str,op.get("provides",[])))
  cost+=float(op.get("cost",1.0))
 req=set(map(str,task.get("required_final_resources") or [task["goal_resource"]]))
 return {"valid":req.issubset(state),"cost":cost,"final_state":sorted(state)}

def score(tasks,outputs,answers):
 tby={str(t["id"]):t for t in tasks}; oby={str(r["id"]):r for r in outputs["rows"]}; aby={str(a["id"]):a for a in answers["answers"]}
 rows=[]
 for tid,t in tby.items():
  row=oby[tid]; exp=aby[tid]; checks={}
  if row.get("error") is not None:
   rows.append({"id":tid,"kind":t["kind"],"pass":False,"checks":{"no_error":False},"error":row["error"]}); continue
  got=row["output"]
  if t["kind"]=="PLANNING" and exp.get("semantic_plan"):
   v=validate_plan(t,got.get("plan"))
   checks["valid_plan"]=v["valid"]
   if "max_cost" in exp["semantic_plan"]: checks["cost"]=v["cost"]<=float(exp["semantic_plan"]["max_cost"])+1e-12
  else:
   for f in exp["compare_fields"]: checks[f]=_eq(got.get(f),exp["expected"].get(f))
  rows.append({"id":tid,"kind":t["kind"],"pass":all(checks.values()),"checks":checks})
 return {"schema":"PROJECT_BRAIN_H100_CROSSCAP_SEMANTIC_SCORE_V4","passed":sum(r["pass"] for r in rows),"total":len(rows),"all_pass":all(r["pass"] for r in rows),"rows":rows}
