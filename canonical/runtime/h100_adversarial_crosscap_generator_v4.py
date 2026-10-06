from __future__ import annotations
import hashlib,json,math
from pathlib import Path
def canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def sha(x): return hashlib.sha256(canon(x).encode()).hexdigest()
def ev(seq,key,val,prev):
 b={"seq":seq,"op":"SET","key":key,"value":val,"prev_hash":prev}; return {**b,"event_hash":sha(b)}
def build():
 t=[]; a=[]
 # reasoning: unique under PRODUCT_EQ, a primitive absent from G1/G0
 spec={"variables":["a","b"],"domains":{"a":[0,1,2,3],"b":[0,1,2,3]},"constraints":[{"op":"LT","vars":["a","b"]},{"op":"PRODUCT_EQ","vars":["a","b"],"value":2}]}
 t.append({"id":"R4","kind":"REASONING","spec":spec}); a.append({"id":"R4","compare_fields":["status","solutions"],"expected":{"status":"UNIQUE","solutions":[{"a":1,"b":2}]}})
 # coding: piecewise absolute function
 ex=[{"x":x,"y":abs(x)+2} for x in (-4,-3,-2,-1,0,1,2,3,4)]
 t.append({"id":"C4","kind":"CODING","examples":ex,"queries":[-5,5]}); a.append({"id":"C4","compare_fields":["status","predictions"],"expected":{"status":"PROGRAM_FOUND","predictions":[7,7]}})
 # language: 18-hop input relation exceeds frozen 16-hop walk
 edges=[]; prev="cue_long"
 for i in range(17):
  nxt=f"n{i}"; edges.append([prev,nxt]); prev=nxt
 edges.append([prev,"input"]); edges.append(["cue_out","output"])
 clauses=[{"cue":"cue_long","fields":["x"]},{"cue":"cue_out","fields":["y"]}]
 know={"anchors":{"input":"input","target":"output"},"edges":edges}
 t.append({"id":"L4","kind":"LANGUAGE","clauses":clauses,"knowledge":know}); a.append({"id":"L4","compare_fields":["status","inputs","target"],"expected":{"status":"ROLES_IDENTIFIED","inputs":["x"],"target":"y"}})
 # vision: two source objects same color touch with no visible boundary => pixel K=2 ambiguity witness
 ppm="P3\n6 4\n255\n"+" ".join(map(str,[255,255,255]*6 + [255,255,255,20,40,180,20,40,180,20,40,180,20,40,180,255,255,255] + [255,255,255,20,40,180,20,40,180,20,40,180,20,40,180,255,255,255] + [255,255,255]*6))+"\n"
 t.append({"id":"V4","kind":"VISION","ppm":ppm,"source_semantics":"two_same_color_rectangles_touch_edge_without_visible_boundary"}); a.append({"id":"V4","compare_fields":["component_count"],"expected":{"component_count":2}})
 # tool: choose minimum priority among two valid matching contracts
 packs=[{"tool_id":"slow","input_schema":{"x":"int"},"effects":["WRITE_JSON"],"priority":9},{"tool_id":"fast","input_schema":{"x":"int"},"effects":["WRITE_JSON"],"priority":1}]
 t.append({"id":"T4","kind":"TOOL_USE","tool_packs":packs,"required_effect":"WRITE_JSON","required_keys":["x"],"selection_policy":"MIN_PRIORITY"}); a.append({"id":"T4","compare_fields":["status","tool_ids"],"expected":{"status":"UNIQUE","tool_ids":["fast"]}})
 # planning: shorter path expensive, longer path cheap
 ops=[
  {"operator_id":"a_exp1","requires":["start"],"provides":["mid"],"cost":10},
  {"operator_id":"b_exp2","requires":["mid"],"provides":["goal"],"cost":10},
  {"operator_id":"c_cheap1","requires":["start"],"provides":["u"],"cost":1},
  {"operator_id":"d_cheap2","requires":["u"],"provides":["v"],"cost":1},
  {"operator_id":"e_cheap3","requires":["v"],"provides":["goal"],"cost":1}
 ]
 t.append({"id":"P4","kind":"PLANNING","initial_resources":["start"],"goal_resource":"goal","required_final_resources":["goal"],"operators":ops,"max_length":5,"objective":"MIN_TOTAL_COST"})
 a.append({"id":"P4","semantic_plan":{"max_cost":3}})
 # memory: count unique values, not implemented by G1
 prev="0"*64; events=[]
 for i,v in enumerate([4,7,4,9,7,11],1):
  e=ev(i,"score",v,prev); events.append(e); prev=e["event_hash"]
 t.append({"id":"M4","kind":"MEMORY","events":events,"query":{"op":"COUNT_UNIQUE","key":"score"}}); a.append({"id":"M4","compare_fields":["history_unique_count"],"expected":{"history_unique_count":4}})
 # novel domain: two independent nonlinear bases
 xs=[-4,-3,-2,-1,0,1,2,3,4]
 f=lambda x:.3+.2*x+.7*math.sin(x)+.6*math.exp(-abs(x))
 rows=[{"x":x,"y":f(x)} for x in xs]; qs=[-4.5,4.5]
 t.append({"id":"N4","kind":"NOVEL_DOMAIN","rows":rows,"queries":qs}); a.append({"id":"N4","compare_fields":["status","predictions"],"expected":{"status":"CAPABILITY_HIT__VERIFY_BEFORE_USE","predictions":[f(x) for x in qs]}})
 return {"schema":"PROJECT_BRAIN_H100_CROSSCAP_V4_PUBLIC","tasks":t},{"schema":"PROJECT_BRAIN_H100_CROSSCAP_V4_ANSWERS","answers":a}
def main():
 import argparse
 ap=argparse.ArgumentParser(); ap.add_argument("--tasks",required=True); ap.add_argument("--answers",required=True)
 z=ap.parse_args(); t,a=build(); Path(z.tasks).write_text(json.dumps(t,indent=2,sort_keys=True)+"\n"); Path(z.answers).write_text(json.dumps(a,indent=2,sort_keys=True)+"\n")
 print(json.dumps({"tasks":len(t["tasks"]),"public_sha256":hashlib.sha256(Path(z.tasks).read_bytes()).hexdigest(),"answers_sha256":hashlib.sha256(Path(z.answers).read_bytes()).hexdigest()},sort_keys=True))
if __name__=="__main__": main()
