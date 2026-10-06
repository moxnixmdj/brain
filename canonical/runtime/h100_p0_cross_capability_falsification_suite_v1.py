from __future__ import annotations
from collections import deque
from typing import Any

SCHEMA="PROJECT_BRAIN_H100_P0_CROSS_CAPABILITY_FALSIFICATION_SUITE_V1"

def bfs_path(start,goal,edges):
    g={}
    for a,b in edges:g.setdefault(a,[]).append(b)
    q=deque([(start,[start])]); seen={start}
    while q:
        x,p=q.popleft()
        if x==goal:return p
        for y in g.get(x,[]):
            if y not in seen:seen.add(y);q.append((y,p+[y]))
    return None

def symbolic_reasoning(task):
    # Derive conclusion by directed implication closure.
    return bfs_path(task["start"],task["goal"],task["implications"]) is not None

def _programs():
    return {
      "REVERSE":lambda s:s[::-1],
      "ROTATE_LEFT":lambda s:s[1:]+s[:1] if s else s,
      "ROTATE_RIGHT":lambda s:s[-1:]+s[:-1] if s else s,
      "DUPLICATE":lambda s:s+s,
      "SORT":lambda s:"".join(sorted(s)),
      "PAIR_SWAP":lambda s:"".join(s[i+1:i+2]+s[i:i+1] for i in range(0,len(s),2)),
    }

def program_synthesis(task):
    survivors=[]
    for name,f in _programs().items():
        if all(f(x)==y for x,y in task["examples"]):survivors.append((name,f))
    if len(survivors)!=1:return {"status":"ABSTAIN","reason":"PROGRAM_AMBIGUITY","survivors":[x[0] for x in survivors]}
    name,f=survivors[0]
    return {"status":"SOLVED","program":name,"answer":f(task["query"])}

def lexical_semantics(task):
    cue_to_role={}
    for cue in task["cues"]:
        inp=bfs_path(cue,"INPUT",task["relations"])
        tgt=bfs_path(cue,"TARGET",task["relations"])
        if bool(inp)==bool(tgt):return {"status":"ABSTAIN","reason":"ROLE_AMBIGUITY","cue":cue}
        cue_to_role[cue]="INPUT" if inp else "TARGET"
    return {"status":"SOLVED","roles":cue_to_role}

def raster_components(grid):
    h=len(grid);w=len(grid[0]);seen=set();out=[]
    for y in range(h):
      for x in range(w):
        if grid[y][x]!="#" or (y,x) in seen:continue
        q=[(y,x)];seen.add((y,x));pts=[]
        while q:
          yy,xx=q.pop();pts.append((yy,xx))
          for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
            ny,nx=yy+dy,xx+dx
            if 0<=ny<h and 0<=nx<w and grid[ny][nx]=="#" and (ny,nx) not in seen:
              seen.add((ny,nx));q.append((ny,nx))
        out.append(pts)
    return out

def raster_vision(task):
    comps=[c for c in raster_components(task["grid"]) if len(c)>=task.get("min_component_pixels",2)]
    boxes=[]
    for c in comps:
      ys=[p[0] for p in c];xs=[p[1] for p in c]
      boxes.append({"minx":min(xs),"maxx":max(xs),"miny":min(ys),"maxy":max(ys),"height":max(ys)-min(ys)+1,"width":max(xs)-min(xs)+1})
    boxes.sort(key=lambda b:b["minx"])
    return {"status":"SOLVED","count":len(boxes),"tallest_index":max(range(len(boxes)),key=lambda i:boxes[i]["height"]) if boxes else None,"boxes":boxes}

def tool_selection(task):
    matches=[]
    for t in task["tools"]:
        if task["required_effect"] in t["effects"] and set(task["required_fields"]).issubset(set(t["fields"])):
            matches.append(t["id"])
    return {"status":"SOLVED","tool_id":matches[0]} if len(matches)==1 else {"status":"ABSTAIN","reason":"TOOL_AMBIGUITY","matches":matches}

def planning(task):
    start=frozenset(task["initial"])
    q=deque([(start,[])])
    seen={start}
    while q:
      state,path=q.popleft()
      if task["goal"] in state:return {"status":"SOLVED","plan":path}
      for op in task["operators"]:
        if set(op["requires"]).issubset(state):
          ns=frozenset(set(state)|set(op["provides"]))
          if ns not in seen:
            seen.add(ns);q.append((ns,path+[op["id"]]))
    return {"status":"ABSTAIN","reason":"NO_PLAN"}

def event_memory(task):
    state={}
    for e in task["events"]:
        if e["op"]=="SET":state[e["key"]]=e["value"]
        elif e["op"]=="DEL":state.pop(e["key"],None)
        elif e["op"]=="INC":state[e["key"]]=state.get(e["key"],0)+e["value"]
        else:return {"status":"ABSTAIN","reason":"UNKNOWN_EVENT_OP"}
    return {"status":"SOLVED","answer":state.get(task["query_key"])}

def unknown_domain(task):
    grammar={
      "2X_PLUS_3":lambda x:2*x+3,
      "X2_MINUS_1":lambda x:x*x-1,
      "3X_MINUS_2":lambda x:3*x-2,
      "ABS_X_PLUS_4":lambda x:abs(x)+4,
      "X3_PLUS_X":lambda x:x**3+x,
    }
    surv=[(n,f) for n,f in grammar.items() if all(f(x)==y for x,y in task["examples"])]
    if len(surv)!=1:return {"status":"ABSTAIN","reason":"MECHANISM_AMBIGUITY","survivors":[x[0] for x in surv]}
    n,f=surv[0];return {"status":"SOLVED","mechanism":n,"answer":f(task["query"])}

def missing_information_control(task):
    # Runtime evidence is intentionally identical under two worlds requiring opposite answers.
    if task["world_a_observation"]==task["world_b_observation"] and task["world_a_answer"]!=task["world_b_answer"]:
        return {"status":"ABSTAIN","reason":"INFORMATION","residual_worlds":2}
    return {"status":"INVALID_CONTROL"}

TASKS={
"SYMBOLIC_REASONING":{"start":"A","goal":"F","implications":[["A","C"],["C","D"],["D","F"],["B","E"]],"expected":True},
"PROGRAM_SYNTHESIS":{"examples":[["abcd","bcda"],["wxyz","xyzw"],["pqrs","qrsp"]],"query":"mango","expected":"angom"},
"LEXICAL_SEMANTICS":{"cues":["signalword","answerword"],"relations":[["signalword","predictor"],["predictor","INPUT"],["answerword","response"],["response","TARGET"]],"expected":{"signalword":"INPUT","answerword":"TARGET"}},
"RASTER_VISION":{"grid":["................","..##............","..##....##......","..##....##..##..","..##....##..##..","..##....##..##..","..##....##..##..","..##....##..##..","..##....##..##..","..##....##..##..","..##....##..##..","..##....##..##.."],"min_component_pixels":4,"expected":{"count":3,"tallest_index":0}},
"TYPED_TOOL_SELECTION":{"required_effect":"APPEND_JSONL","required_fields":["event","value"],"tools":[{"id":"RECEIPT","effects":["WRITE_JSON"],"fields":["name","score","passed"]},{"id":"LEDGER","effects":["APPEND_JSONL"],"fields":["event","value"]},{"id":"HASHER","effects":["RETURN_SHA256"],"fields":["path"]}],"expected":"LEDGER"},
"MULTISTEP_PLANNING":{"initial":["RAW"],"goal":"VERIFIED","operators":[{"id":"NORMALIZE","requires":["RAW"],"provides":["NORMAL"]},{"id":"COMPILE","requires":["NORMAL"],"provides":["PROGRAM"]},{"id":"VERIFY","requires":["PROGRAM"],"provides":["VERIFIED"]},{"id":"DISTRACTOR","requires":["RAW"],"provides":["NOISE"]}],"expected":["NORMALIZE","COMPILE","VERIFY"]},
"EVENT_MEMORY":{"events":[{"op":"SET","key":"score","value":7},{"op":"INC","key":"score","value":5},{"op":"SET","key":"mode","value":"A"},{"op":"DEL","key":"mode"},{"op":"INC","key":"score","value":-3}],"query_key":"score","expected":9},
"UNKNOWN_DOMAIN_ADAPTATION":{"examples":[[-3,24],[-1,0],[2,9],[4,63]],"query":5,"expected":130},
"MISSING_INFORMATION_CONTROL":{"world_a_observation":{"token":"same"},"world_b_observation":{"token":"same"},"world_a_answer":"LEFT","world_b_answer":"RIGHT","expected_status":"ABSTAIN"}
}

def run_suite():
    rows=[]
    t=TASKS["SYMBOLIC_REASONING"];o=symbolic_reasoning(t);rows.append(("SYMBOLIC_REASONING",o==t["expected"],o))
    t=TASKS["PROGRAM_SYNTHESIS"];o=program_synthesis(t);rows.append(("PROGRAM_SYNTHESIS",o.get("answer")==t["expected"],o))
    t=TASKS["LEXICAL_SEMANTICS"];o=lexical_semantics(t);rows.append(("LEXICAL_SEMANTICS",o.get("roles")==t["expected"],o))
    t=TASKS["RASTER_VISION"];o=raster_vision(t);rows.append(("RASTER_VISION",o.get("count")==t["expected"]["count"] and o.get("tallest_index")==t["expected"]["tallest_index"],o))
    t=TASKS["TYPED_TOOL_SELECTION"];o=tool_selection(t);rows.append(("TYPED_TOOL_SELECTION",o.get("tool_id")==t["expected"],o))
    t=TASKS["MULTISTEP_PLANNING"];o=planning(t);rows.append(("MULTISTEP_PLANNING",o.get("plan")==t["expected"],o))
    t=TASKS["EVENT_MEMORY"];o=event_memory(t);rows.append(("EVENT_MEMORY",o.get("answer")==t["expected"],o))
    t=TASKS["UNKNOWN_DOMAIN_ADAPTATION"];o=unknown_domain(t);rows.append(("UNKNOWN_DOMAIN_ADAPTATION",o.get("answer")==t["expected"],o))
    t=TASKS["MISSING_INFORMATION_CONTROL"];o=missing_information_control(t);rows.append(("MISSING_INFORMATION_CONTROL",o.get("status")=="ABSTAIN" and o.get("reason")=="INFORMATION",o))
    return {"schema":SCHEMA,"passed":sum(int(x[1]) for x in rows),"total":len(rows),"all_pass":all(x[1] for x in rows),"rows":[{"id":i,"pass":p,"output":o} for i,p,o in rows],"target_adapted_persistent_bits":0}

if __name__=="__main__":
    import json;print(json.dumps(run_suite(),indent=2,sort_keys=True))
