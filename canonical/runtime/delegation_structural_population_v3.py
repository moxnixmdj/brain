"""Structurally varied information-safe delegation population V3.

Closes the residual topology dimension only: fresh explicit finite task graphs vary
fanout/fanin, alternative plans, chain depth, resource conflicts and worker capability
placement. Receipt-driven replanning remains covered by the independently verified V2
route and is not re-claimed by this file.
"""
from __future__ import annotations
from collections import defaultdict, deque
from itertools import combinations, permutations
import math, random
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_DELEGATION_STRUCTURAL_POPULATION_V3"

def _rid(r, prefix, i): return f"{prefix}_{i}_{r.randrange(100000,999999)}"

def generate_case(seed:int, ordinal:int)->dict[str,Any]:
    r=random.Random((seed<<23)^ordinal^0xD3A6)
    branch_count=2+(ordinal%2)
    raw=_rid(r,"RAW",0); final=_rid(r,"FINAL",0)
    steps=[]; workers=[]; required_inputs=[]
    resource_caps={}
    all_caps=[]
    # Each branch has a cheaper selected path and a costlier alternative.
    for b in range(branch_count):
        cap1=_rid(r,"CAPA",b); cap2=_rid(r,"CAPB",b); all_caps += [cap1,cap2]
        x=_rid(r,"X",b)
        direct=_rid(r,"DIRECT",b)
        alt1=_rid(r,"ALT1",b); alt2=_rid(r,"ALT2",b)
        lock=_rid(r,"LOCK",b//2 if ordinal%3==0 else b)
        resource_caps.setdefault(lock,1 if ordinal%3==0 else 2)
        # Alternate cost pattern varies which route is cheapest.
        direct_cost=1.0 if (ordinal+b)%2==0 else 4.0
        alt_cost=3.0 if direct_cost==1.0 else 1.0
        steps.append({"id":direct,"requires":[raw],"produces":[x],"cost":direct_cost,
                      "capability":cap1,"writes":[lock],"evidence_outputs":[_rid(r,"EVD",b)]})
        mid=_rid(r,"MID",b)
        steps.append({"id":alt1,"requires":[raw],"produces":[mid],"cost":alt_cost,
                      "capability":cap1,"writes":[lock],"evidence_outputs":[_rid(r,"EVA",b)]})
        steps.append({"id":alt2,"requires":[mid],"produces":[x],"cost":alt_cost,
                      "capability":cap2,"writes":[lock],"evidence_outputs":[_rid(r,"EVB",b)]})
        required_inputs.append(x)
    join_cap=_rid(r,"JOINCAP",0); all_caps.append(join_cap)
    join=_rid(r,"JOIN",0)
    steps.append({"id":join,"requires":required_inputs,"produces":[final],"cost":1.0,
                  "capability":join_cap,"writes":[_rid(r,"FINALLOCK",0)],
                  "evidence_outputs":[_rid(r,"EVJ",0)]})
    # Add a dominated decoy branch to test partitioning.
    decoy_cap=_rid(r,"DECOYCAP",0); all_caps.append(decoy_cap)
    steps.append({"id":_rid(r,"DECOY",0),"requires":[raw],"produces":[_rid(r,"NOISE",0)],
                  "cost":10.0,"capability":decoy_cap,"writes":[_rid(r,"NOISELOCK",0)],
                  "evidence_outputs":[_rid(r,"EVDX",0)]})
    # Enough heterogeneous workers to permit parallelism when resources allow.
    for i,cap in enumerate(all_caps):
        workers.append({"id":_rid(r,"W",i),"capabilities":[cap]})
    workers.append({"id":_rid(r,"WFLEX",0),"capabilities":sorted(set(all_caps))})
    task={
      "initial_facts":[raw],
      "required_outputs":[final],
      "steps":steps,
      "workers":workers,
      "resource_capacities":resource_caps,
      "evidence_rules":{"producer_owns_output":True,"fanin_preserves_all_ancestor_evidence":True},
    }
    return {"schema":SCHEMA,"behavior_id":"TASK_TO_DELEGATION_GRAPH_001",
            "case_id":f"DELEGATION-STRUCTURAL-V3-{seed}-{ordinal}","task":task}

def public_task(case:Mapping[str,Any])->dict[str,Any]:
    return {"schema":case["schema"],"case_id":case["case_id"],"task":case["task"]}

def _effective(task):
    steps={x["id"]:{
      "requires":set(x["requires"]),"produces":set(x["produces"]),"cost":float(x["cost"]),
      "capability":x["capability"],"writes":set(x["writes"]),"evidence":set(x["evidence_outputs"])
    } for x in task["steps"]}
    workers={x["id"]:set(x["capabilities"]) for x in task["workers"]}
    caps={str(k):int(v) for k,v in task["resource_capacities"].items()}
    return steps,workers,caps

def _optimal(task):
    steps,_,_= _effective(task)
    ids=sorted(steps)
    initial=set(task["initial_facts"]); required=set(task["required_outputs"])
    best=None
    for k in range(len(ids)+1):
      for subset in combinations(ids,k):
        for order in permutations(subset):
          facts=set(initial); producer={}; deps={}; ok=True
          for sid in order:
            row=steps[sid]
            if not row["requires"].issubset(facts): ok=False; break
            deps[sid]=sorted({producer[f] for f in row["requires"] if f not in initial and f in producer})
            for f in row["produces"]:
              if f not in facts: producer[f]=sid
            facts |= row["produces"]
          if not ok or not required.issubset(facts): continue
          cost=sum(steps[s]["cost"] for s in order)
          key=(cost,len(order),tuple(order))
          if best is None or key<best[0]: best=(key,{"task_ids":list(order),"dependencies":deps,"total_cost":cost})
    if best is None: raise ValueError("NO_PLAN")
    return best[1]

def _resource_ok(tasks,steps,caps):
    use=defaultdict(int)
    for sid in tasks:
      for res in steps[sid]["writes"]: use[res]+=1
    return all(use[r] <= caps.get(r,1) for r in use)

def _min_waves(task,opt):
    steps,workers,caps=_effective(task); ids=opt["task_ids"]; deps=opt["dependencies"]
    q=deque([(frozenset(),0)]); seen={frozenset()}
    while q:
      done,d=q.popleft()
      if done==frozenset(ids): return d
      ready=[s for s in ids if s not in done and set(deps[s]).issubset(done)]
      for k in range(1,min(len(ready),len(workers))+1):
        for tasks in combinations(sorted(ready),k):
          if not _resource_ok(tasks,steps,caps): continue
          for ws in permutations(sorted(workers),k):
            if all(steps[s]["capability"] in workers[w] for s,w in zip(tasks,ws)):
              nd=frozenset(set(done)|set(tasks))
              if nd not in seen: seen.add(nd); q.append((nd,d+1))
    raise ValueError("NO_SCHEDULE")

def score_case(case:Mapping[str,Any], cand:Mapping[str,Any])->dict[str,Any]:
    if cand.get("status")!="PASS": return {"pass":False,"reason":"STATUS"}
    task=case["task"]; opt=_optimal(task)
    if cand.get("task_ids")!=opt["task_ids"]: return {"pass":False,"reason":"TASK_SET_OR_ORDER"}
    if cand.get("dependencies")!=opt["dependencies"]: return {"pass":False,"reason":"DEPENDENCIES"}
    if cand.get("total_cost")!=opt["total_cost"]: return {"pass":False,"reason":"COST"}
    waves=cand.get("waves"); assignment=cand.get("assignment")
    if not isinstance(waves,list) or len(waves)!=_min_waves(task,opt): return {"pass":False,"reason":"WAVES"}
    steps,workers,caps=_effective(task); seen=set()
    for wave in waves:
      if not _resource_ok(wave,steps,caps): return {"pass":False,"reason":"RESOURCE_CONFLICT"}
      used=set()
      for sid in wave:
        if sid in seen or not set(opt["dependencies"][sid]).issubset(seen): return {"pass":False,"reason":"DEPENDENCY_OR_REPLAY"}
        wid=assignment.get(sid) if isinstance(assignment,Mapping) else None
        if wid not in workers or steps[sid]["capability"] not in workers[wid] or wid in used: return {"pass":False,"reason":"ASSIGNMENT"}
        used.add(wid)
      seen.update(wave)
    if seen!=set(opt["task_ids"]): return {"pass":False,"reason":"COVERAGE"}
    expected_evidence=set()
    for sid in opt["task_ids"]: expected_evidence |= steps[sid]["evidence"]
    if set(cand.get("terminal_evidence") or [])!=expected_evidence: return {"pass":False,"reason":"FANIN"}
    naive=sum(x["cost"] for x in steps.values())
    if not (len(waves)<len(opt["task_ids"]) or float(cand.get("total_cost",math.inf))<naive):
      return {"pass":False,"reason":"NO_BASELINE_ADVANTAGE"}
    return {"pass":True,"reason":"PASS"}

def topology_fingerprint(case):
    t=case["task"]; req=sorted(len(x["requires"]) for x in t["steps"])
    prod=sorted(len(x["produces"]) for x in t["steps"])
    return (len(t["steps"]),tuple(req),tuple(prod),len(t["resource_capacities"]))

def run_batch(seed:int,count:int,solver):
    rows=[]; fps=set(); fanin=False; alternatives=False
    for i in range(count):
      c=generate_case(seed,i); fps.add(topology_fingerprint(c))
      fanin |= any(len(x["requires"])>1 for x in c["task"]["steps"])
      produced=defaultdict(int)
      for x in c["task"]["steps"]:
        for f in x["produces"]: produced[f]+=1
      alternatives |= any(v>1 for v in produced.values())
      try: v=score_case(c,solver(public_task(c)))
      except Exception as e: v={"pass":False,"reason":type(e).__name__+":"+str(e)}
      rows.append({"case_id":c["case_id"],**v})
    return {"all_pass":all(x["pass"] for x in rows),"case_count":count,
            "topology_fingerprint_count":len(fps),"fanin_present":fanin,
            "alternative_plan_present":alternatives,
            "failures":[x for x in rows if not x["pass"]],
            "terminal_authority":False,"capability_credit_delta":0}
