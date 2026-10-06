from __future__ import annotations
import hashlib,json,math,random
from pathlib import Path
S={"REASONING":842001,"CODING":842002,"LANGUAGE":842003,"VISION":842004,"TOOL_USE":842005,"PLANNING":842006,"MEMORY":842007,"NOVEL_DOMAIN":842008}
def canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def sha(x): return hashlib.sha256(canon(x).encode()).hexdigest()
def event(seq,op,key,val,prev):
 b={"seq":seq,"op":op,"key":key,"value":val if op=="SET" else None,"prev_hash":prev}
 return {**b,"event_hash":sha(b)}
def ppm_case(rng,idx):
 w,h=14,8; img=[[(255,255,255) for _ in range(w)] for _ in range(h)]
 colors=[(15,80,180),(180,50,40),(30,160,90),(140,60,170)]
 rects=[]
 # touching chain of 3 colored rectangles
 x=1
 for j in range(3):
  rw=rng.randint(2,4); rh=rng.randint(3,5); y=1+rng.randint(0,1)
  col=colors[(idx+j)%len(colors)]
  for yy in range(y,y+rh):
   for xx in range(x,x+rw): img[yy][xx]=col
  rects.append({"area":rw*rh,"bbox":[x,y,x+rw-1,y+rh-1]})
  x=x+rw  # touching edge, different color
 nums=[]
 for row in img:
  for p in row: nums.extend(p)
 return "P3\n%d %d\n255\n%s\n"%(w,h," ".join(map(str,nums))),rects
def build():
 tasks=[]; ans=[]
 # reasoning: underdetermined base + runtime side constraint makes K=1
 for i,op in enumerate(["LT","GT"],1):
  spec={"variables":["a","b"],"domains":{"a":[1,2],"b":[1,2]},"constraints":[{"op":"NEQ","vars":["a","b"]}]}
  side=[{"op":op,"vars":["a","b"]}]
  sol={"a":1,"b":2} if op=="LT" else {"a":2,"b":1}
  tid=f"R3_{i}"; tasks.append({"id":tid,"kind":"REASONING","spec":spec,"side_constraints":side})
  ans.append({"id":tid,"compare_fields":["status","solutions"],"expected":{"status":"UNIQUE","solutions":[sol]}})
 # coding: fresh cubic polynomials
 rng=random.Random(S["CODING"])
 for i in range(2):
  c0=rng.randint(-3,3); c1=rng.randint(-2,2); c2=rng.randint(-2,2); c3=rng.choice([-2,-1,1,2])
  f=lambda x,c0=c0,c1=c1,c2=c2,c3=c3:c0+c1*x+c2*x*x+c3*x*x*x
  ex=[{"x":x,"y":f(x)} for x in range(-3,4)]; qs=[-4,4]
  tid=f"C3_{i+1}"; tasks.append({"id":tid,"kind":"CODING","examples":ex,"queries":qs})
  ans.append({"id":tid,"compare_fields":["status","predictions"],"expected":{"status":"PROGRAM_FOUND","predictions":[f(x) for x in qs]}})
 # language: side knowledge provides the disambiguating edges
 rng=random.Random(S["LANGUAGE"]); syll=["ka","vo","mi","ze","tor","lun","sha","pri"]
 for i in range(2):
  ci="".join(rng.sample(syll,2))+str(i); co="".join(rng.sample(syll,2))+str(i+5)
  clauses=[{"cue":ci,"fields":["feature"]},{"cue":co,"fields":["label"]}]
  base={"anchors":{"input":"input","target":"output"},"edges":[]}
  side=[[ci,"predictor"],["predictor","input"],[co,"response"],["response","output"]]
  tid=f"L3_{i+1}"; tasks.append({"id":tid,"kind":"LANGUAGE","clauses":clauses,"knowledge":base,"side_knowledge_edges":side})
  ans.append({"id":tid,"compare_fields":["status","inputs","target"],"expected":{"status":"ROLES_IDENTIFIED","inputs":["feature"],"target":"label"}})
 # vision: fresh touching colored objects
 rng=random.Random(S["VISION"])
 for i in range(2):
  ppm,rects=ppm_case(rng,i)
  tid=f"V3_{i+1}"; tasks.append({"id":tid,"kind":"VISION","ppm":ppm})
  ans.append({"id":tid,"compare_fields":["component_count","areas","bboxes"],"expected":{"component_count":3,"areas":sorted(r["area"] for r in rects),"bboxes":sorted(r["bbox"] for r in rects)}})
 # tools: same low-level effect, fresh metadata values
 purposes=["archive","publish"]
 for i,purp in enumerate(purposes,1):
  packs=[
   {"tool_id":f"A{i}","input_schema":{"name":"string","value":"int"},"effects":[["WRITE_JSON","out.json"]],"purpose":purp},
   {"tool_id":f"B{i}","input_schema":{"name":"string","value":"int"},"effects":[["WRITE_JSON","out.json"]],"purpose":"other"},
   {"tool_id":f"C{i}","input_schema":{"event":"string"},"effects":[["APPEND_JSONL","log.jsonl"]],"purpose":purp}
  ]
  tid=f"T3_{i}"; tasks.append({"id":tid,"kind":"TOOL_USE","tool_packs":packs,"required_effect":"WRITE_JSON","required_keys":["name","value"],"purpose":purp})
  ans.append({"id":tid,"compare_fields":["status","tool_ids"],"expected":{"status":"UNIQUE","tool_ids":[f"A{i}"]}})
 # planning: fresh nonmonotonic state transitions
 for i in range(2):
  ops=[
   {"operator_id":f"{i}a_get","requires":["start"],"provides":["key"]},
   {"operator_id":f"{i}b_copy","requires":["key"],"provides":["backup"]},
   {"operator_id":f"{i}c_open","requires":["key"],"provides":["gate"],"removes":["key"]},
   {"operator_id":f"{i}d_restore","requires":["backup","gate"],"provides":["key"]},
   {"operator_id":f"{i}z_decoy","requires":["start"],"provides":["noise"]}
  ]
  want=[f"{i}a_get",f"{i}b_copy",f"{i}c_open",f"{i}d_restore"]
  tid=f"P3_{i+1}"; tasks.append({"id":tid,"kind":"PLANNING","initial_resources":["start"],"goal_resource":"gate","required_final_resources":["gate","key"],"operators":ops,"max_length":6})
  ans.append({"id":tid,"compare_fields":["status","plan"],"expected":{"status":"PLAN_FOUND","plan":want}})
 # memory: new historical reducers
 rng=random.Random(S["MEMORY"])
 for i,op in enumerate(["MIN_SEEN","COUNT_SET"],1):
  prev="0"*64; evs=[]; vals=[]
  for seq in range(1,7):
   v=rng.randint(5,99); vals.append(v); e=event(seq,"SET","score",v,prev); evs.append(e); prev=e["event_hash"]
  tid=f"M3_{i}"; tasks.append({"id":tid,"kind":"MEMORY","events":evs,"query":{"op":op,"key":"score"}})
  key="history_min" if op=="MIN_SEEN" else "history_count"; val=min(vals) if op=="MIN_SEEN" else len(vals)
  ans.append({"id":tid,"compare_fields":[key],"expected":{key:val}})
 # novel domain: fresh bases unseen in V2
 rng=random.Random(S["NOVEL_DOMAIN"])
 bases=[("EXP_NEG_SQUARE",lambda x:math.exp(-(x*x))),("TANH",lambda x:math.tanh(x))]
 xs=[-4,-3,-2,-1,0,1,2,3,4]
 for i,(name,fn) in enumerate(bases,1):
  a=rng.uniform(-.8,.8); b=rng.uniform(-.35,.35); c=rng.choice([-1,1])*rng.uniform(.5,1.4)
  rows=[{"x":x,"y":a+b*x+c*fn(x)} for x in xs]; qs=[-4.5,4.5]
  preds=[a+b*x+c*fn(x) for x in qs]
  tid=f"N3_{i}"; tasks.append({"id":tid,"kind":"NOVEL_DOMAIN","rows":rows,"queries":qs})
  ans.append({"id":tid,"compare_fields":["status","predictions"],"expected":{"status":"CAPABILITY_HIT__VERIFY_BEFORE_USE","predictions":preds}})
 return {"schema":"PROJECT_BRAIN_H100_CROSSCAP_V3_PUBLIC","tasks":tasks},{"schema":"PROJECT_BRAIN_H100_CROSSCAP_V3_ANSWERS","answers":ans}
def main():
 import argparse
 ap=argparse.ArgumentParser(); ap.add_argument("--tasks",required=True); ap.add_argument("--answers",required=True)
 a=ap.parse_args(); t,k=build(); Path(a.tasks).write_text(json.dumps(t,indent=2,sort_keys=True)+"\n"); Path(a.answers).write_text(json.dumps(k,indent=2,sort_keys=True)+"\n")
 print(json.dumps({"tasks":len(t["tasks"]),"public_sha256":hashlib.sha256(Path(a.tasks).read_bytes()).hexdigest(),"answers_sha256":hashlib.sha256(Path(a.answers).read_bytes()).hexdigest()},sort_keys=True))
if __name__=="__main__": main()
