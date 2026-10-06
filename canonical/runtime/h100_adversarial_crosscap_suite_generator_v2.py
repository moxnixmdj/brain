from __future__ import annotations
import hashlib,json,math
from pathlib import Path

def canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def sha(x): return hashlib.sha256(canon(x).encode()).hexdigest()
def ev(seq,op,key,value,prev):
 body={"seq":seq,"op":op,"key":key,"value":value if op=="SET" else None,"prev_hash":prev}
 return {**body,"event_hash":sha(body)}

def ppm_touching():
 w,h=10,6; white=(255,255,255); img=[[white for _ in range(w)] for _ in range(h)]
 # Two semantic objects touch along one edge but have different colors.
 for y in range(1,5):
  for x in range(1,4): img[y][x]=(20,40,180)
  for x in range(4,8): img[y][x]=(180,30,60)
 nums=[]
 for row in img:
  for p in row: nums.extend(p)
 return "P3\n10 6\n255\n"+" ".join(map(str,nums))+"\n"

def build():
 tasks=[]; ans=[]
 # REASONING: two equally valid worlds; hidden answer key picks one. This is an intentional information-gap witness.
 spec={"variables":["a","b"],"domains":{"a":[1,2],"b":[1,2]},"constraints":[{"op":"NEQ","vars":["a","b"]}]}
 tasks.append({"id":"AR1","kind":"REASONING","spec":spec,"question":"return the world selected by the hidden environment bit"})
 ans.append({"id":"AR1","compare_fields":["status","solutions"],"expected":{"status":"UNIQUE","solutions":[{"a":1,"b":2}]}})

 # CODING: cubic is outside the frozen depth-2 practical grammar.
 ex=[{"x":x,"y":x*x*x+1} for x in (-3,-2,-1,0,1,2,3)]
 tasks.append({"id":"AC1","kind":"CODING","examples":ex,"queries":[4,5],"max_depth":2})
 ans.append({"id":"AC1","compare_fields":["status","predictions"],"expected":{"status":"PROGRAM_FOUND","predictions":[65,126]}})

 # LANGUAGE: cue reaches both anchors; answer key selects context not present in graph.
 clauses=[{"cue":"nova","fields":["x"]},{"cue":"result","fields":["y"]}]
 know={"anchors":{"input":"input","target":"output"},"edges":[["nova","predictor"],["predictor","input"],["nova","response"],["response","output"],["result","output"]]}
 tasks.append({"id":"AL1","kind":"LANGUAGE","clauses":clauses,"knowledge":know,"question":"treat nova as predictor in this hidden discourse"})
 ans.append({"id":"AL1","compare_fields":["status","inputs","target"],"expected":{"status":"ROLES_IDENTIFIED","inputs":["x"],"target":"y"}})

 # VISION: semantic objects differ by color but touch geometrically.
 tasks.append({"id":"AV1","kind":"VISION","ppm":ppm_touching(),"component_semantics":"objects are separated by color even when edges touch"})
 ans.append({"id":"AV1","compare_fields":["component_count"],"expected":{"component_count":2}})

 # TOOL: both packs share low-level effect/keys; public purpose field should break the tie.
 packs=[
  {"tool_id":"AUDIT_WRITER","input_schema":{"name":"string","value":"int"},"effects":[["WRITE_JSON","out.json"]],"purpose":"audit"},
  {"tool_id":"CACHE_WRITER","input_schema":{"name":"string","value":"int"},"effects":[["WRITE_JSON","out.json"]],"purpose":"cache"}
 ]
 tasks.append({"id":"AT1","kind":"TOOL_USE","tool_packs":packs,"required_effect":"WRITE_JSON","required_keys":["name","value"],"purpose":"audit"})
 ans.append({"id":"AT1","compare_fields":["status","tool_ids"],"expected":{"status":"UNIQUE","tool_ids":["AUDIT_WRITER"]}})

 # PLANNING: monotonic abstraction ignores removal of key needed at the goal.
 ops=[
  {"operator_id":"take_key","requires":["start"],"provides":["key"],"removes":[]},
  {"operator_id":"open_gate","requires":["key"],"provides":["gate_open"],"removes":["key"]},
  {"operator_id":"duplicate_key","requires":["key"],"provides":["spare_key"],"removes":[]},
  {"operator_id":"restore_key","requires":["spare_key","gate_open"],"provides":["key"],"removes":[]}
 ]
 tasks.append({"id":"AP1","kind":"PLANNING","initial_resources":["start"],"goal_resource":"gate_open","required_final_resources":["gate_open","key"],"operators":ops,"max_length":6})
 ans.append({"id":"AP1","compare_fields":["status","plan"],"expected":{"status":"PLAN_FOUND","plan":["take_key","duplicate_key","open_gate","restore_key"]}})

 # MEMORY: final state is insufficient for a historical maximum query.
 prev="0"*64; events=[]
 vals=[3,9,4,7]
 for i,v in enumerate(vals,1):
  e=ev(i,"SET","score",v,prev); events.append(e); prev=e["event_hash"]
 tasks.append({"id":"AM1","kind":"MEMORY","events":events,"query":{"op":"MAX_SEEN","key":"score"}})
 ans.append({"id":"AM1","compare_fields":["history_max"],"expected":{"history_max":9}})

 # NOVEL DOMAIN: exponential-decay family absent from frozen verified registry.
 xs=[-4,-3,-2,-1,0,1,2,3,4]
 rows=[{"x":x,"y":0.25+0.4*x+1.2*math.exp(-abs(x))} for x in xs]
 qs=[-4.5,4.5]
 preds=[0.25+0.4*x+1.2*math.exp(-abs(x)) for x in qs]
 tasks.append({"id":"AN1","kind":"NOVEL_DOMAIN","rows":rows,"queries":qs})
 ans.append({"id":"AN1","compare_fields":["status","predictions"],"expected":{"status":"LIBRARY_HIT__VERIFY_BEFORE_USE","predictions":preds}})

 return {"schema":"PROJECT_BRAIN_H100_ADVERSARIAL_CROSSCAP_PUBLIC_V2","tasks":tasks},{"schema":"PROJECT_BRAIN_H100_ADVERSARIAL_CROSSCAP_ANSWERS_V2","answers":ans}

def main():
 import argparse
 ap=argparse.ArgumentParser(); ap.add_argument("--tasks",required=True); ap.add_argument("--answers",required=True)
 a=ap.parse_args(); t,k=build()
 Path(a.tasks).write_text(json.dumps(t,indent=2,sort_keys=True)+"\n"); Path(a.answers).write_text(json.dumps(k,indent=2,sort_keys=True)+"\n")
 print(json.dumps({"tasks":len(t["tasks"]),"public_sha256":hashlib.sha256(Path(a.tasks).read_bytes()).hexdigest(),"answers_sha256":hashlib.sha256(Path(a.answers).read_bytes()).hexdigest()},sort_keys=True))
if __name__=="__main__": main()
