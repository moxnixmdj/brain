from __future__ import annotations
from typing import Any,Mapping,Sequence
from canonical.runtime import h100_crosscap_g0_v1 as g0
from canonical.runtime import h100_crosscap_g1_v1 as g1

def execute_task(task:Mapping[str,Any])->dict[str,Any]:
 kind=str(task["kind"])
 if kind=="REASONING":
  r=g1.solve_reasoning(task); return {"status":r["status"],"solutions":r["solutions"]}
 if kind=="CODING":
  r=g1.synthesize_polynomial(task["examples"],3)
  return {"status":r["status"],"source":r["source"],"predictions":None if r["status"]!="PROGRAM_FOUND" else [g1.predict_polynomial(r,x) for x in task["queries"]]}
 if kind=="LANGUAGE":
  knowledge=dict(task["knowledge"]); knowledge["edges"]=list(knowledge.get("edges",[]))+list(task.get("side_knowledge_edges",[]))
  return g0.resolve_lexical_roles(task["clauses"],knowledge)
 if kind=="VISION":
  r=g1.ppm_color_components(task["ppm"]); comps=r["components"]
  return {"component_count":len(comps),"areas":sorted(c["area"] for c in comps),"bboxes":sorted(c["bbox"] for c in comps)}
 if kind=="TOOL_USE":
  r=g1.select_tool(task); return {"status":r["status"],"tool_ids":[str(x.get("tool_id")) for x in r["matches"]]}
 if kind=="PLANNING":
  return g1.plan_nonmonotonic(task)
 if kind=="MEMORY":
  base=g0.replay_events(task["events"]); out={"state":base["state"],"last_seq":base["last_seq"],"last_event_hash":base["last_event_hash"]}
  if "query" in task:
   val=g1.query_history(task["events"],task["query"]); op=str(task["query"]["op"])
   key={"MAX_SEEN":"history_max","MIN_SEEN":"history_min","COUNT_SET":"history_count","LAST_VALUE":"history_last"}[op]; out[key]=val
  return out
 if kind=="NOVEL_DOMAIN":
  r=g1.resolve_generic_numeric(task["rows"])
  return {"status":r["status"],"basis":r.get("basis"),"predictions":None if r["status"]!="CAPABILITY_HIT__VERIFY_BEFORE_USE" else [g1.predict_generic_numeric(r,x) for x in task["queries"]]}
 raise ValueError(kind)

def run_suite(tasks:Sequence[Mapping[str,Any]])->dict[str,Any]:
 return {"schema":"PROJECT_BRAIN_H100_CROSSCAP_G1_OUTPUT_V1","rows":[{"id":str(t["id"]),"kind":str(t["kind"]),"output":execute_task(t)} for t in tasks]}
