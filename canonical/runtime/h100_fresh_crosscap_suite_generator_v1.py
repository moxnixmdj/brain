"""Generate the frozen fresh cross-capability suite after G0 freeze."""
from __future__ import annotations
import hashlib, json, math, random
from pathlib import Path

SEEDS={"REASONING":731001,"CODING":731002,"LANGUAGE":731003,"VISION":731004,"TOOL_USE":731005,"PLANNING":731006,"MEMORY":731007,"NOVEL_DOMAIN":731008}

def canon(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha(x):
    return hashlib.sha256(canon(x).encode()).hexdigest()

def make_event(seq,op,key,value,prev):
    body={"seq":seq,"op":op,"key":key,"value":value if op=="SET" else None,"prev_hash":prev}
    return {**body,"event_hash":sha(body)}

def apply_chain(x,seq):
    v=float(x)
    for op in seq:
        if op=="square": v=v*v
        elif op=="log1p_abs": v=math.log1p(abs(v))
        elif op=="sqrt_abs": v=math.sqrt(abs(v))
        elif op=="sat": v=v/(1+abs(v))
        else: raise ValueError(op)
    return v

def ppm_task(rng,idx):
    w,h=24,18
    img=[[(255,255,255) for _ in range(w)] for _ in range(h)]
    slots=[(1,1,9,7),(13,1,22,7),(1,10,9,16),(13,10,22,16)]
    count=3+(idx%2)
    rects=[]
    palette=[(20,40,180),(180,30,60),(20,150,70),(120,40,160)]
    for si in range(count):
        x0,y0,x1,y1=slots[si]
        rw=rng.randint(2,max(2,x1-x0-1)); rh=rng.randint(2,max(2,y1-y0-1))
        sx=rng.randint(x0,x1-rw); sy=rng.randint(y0,y1-rh)
        color=palette[(si+idx)%len(palette)]
        for y in range(sy,sy+rh):
            for x in range(sx,sx+rw): img[y][x]=color
        rects.append({"area":rw*rh,"bbox":[sx,sy,sx+rw-1,sy+rh-1]})
    nums=[]
    for row in img:
        for p in row: nums.extend(p)
    ppm="P3\n%d %d\n255\n%s\n"%(w,h," ".join(map(str,nums)))
    expected={"component_count":count,"areas":sorted(r["area"] for r in rects),"bboxes":sorted(r["bbox"] for r in rects)}
    return {"ppm":ppm},expected

def build():
    tasks=[]; answers=[]

    rng=random.Random(SEEDS["REASONING"])
    for i in range(2):
        vars_=["a","b","c","d"]; order=vars_[:]; rng.shuffle(order)
        spec={"variables":vars_,"domains":{v:[1,2,3,4] for v in vars_},"constraints":[{"op":"ALL_DIFF","vars":vars_},{"op":"SUM_EQ","vars":vars_,"value":10}]}
        for left,right in zip(order,order[1:]): spec["constraints"].append({"op":"LT","vars":[left,right]})
        solution={v:order.index(v)+1 for v in vars_}
        tid=f"R{i+1}"
        tasks.append({"id":tid,"kind":"REASONING","spec":spec})
        answers.append({"id":tid,"compare_fields":["status","solutions"],"expected":{"status":"UNIQUE","solutions":[solution]}})

    rng=random.Random(SEEDS["CODING"])
    for i in range(2):
        c=rng.choice([-3,-2,-1,1,2,3])
        examples=[{"x":x,"y":x*x+c} for x in (-3,-2,-1,0,1,2,3)]
        queries=[4,5]
        tid=f"C{i+1}"
        tasks.append({"id":tid,"kind":"CODING","examples":examples,"queries":queries,"max_depth":2})
        answers.append({"id":tid,"compare_fields":["status","predictions"],"expected":{"status":"PROGRAM_FOUND","predictions":[x*x+c for x in queries]}})

    rng=random.Random(SEEDS["LANGUAGE"])
    syll=["za","tor","vek","lun","mir","qal","sen","dra"]
    for i in range(2):
        cue_in="".join(rng.sample(syll,2))+str(i)
        cue_out="".join(rng.sample(syll,2))+str(i+7)
        clauses=[{"cue":cue_in,"fields":["feature"]},{"cue":cue_out,"fields":["label"]}]
        knowledge={"anchors":{"input":"input","target":"output"},"edges":[[cue_in,"predictor"],["predictor","input"],[cue_out,"response"],["response","output"]]}
        tid=f"L{i+1}"
        tasks.append({"id":tid,"kind":"LANGUAGE","clauses":clauses,"knowledge":knowledge})
        answers.append({"id":tid,"compare_fields":["status","inputs","target"],"expected":{"status":"ROLES_IDENTIFIED","inputs":["feature"],"target":"label"}})

    rng=random.Random(SEEDS["VISION"])
    for i in range(2):
        payload,expected=ppm_task(rng,i)
        tid=f"V{i+1}"
        tasks.append({"id":tid,"kind":"VISION",**payload})
        answers.append({"id":tid,"compare_fields":["component_count","areas","bboxes"],"expected":expected})

    rng=random.Random(SEEDS["TOOL_USE"])
    packs=[
      {"tool_id":"JSON_RECEIPT_WRITER_V1","input_schema":{"name":"string","score":"float","passed":"bool"},"effects":[["WRITE_JSON","receipts/result.json"],["RETURN_SHA256","receipts/result.json"]]},
      {"tool_id":"JSONL_LEDGER_APPEND_V1","input_schema":{"event":"string","value":"int"},"effects":[["APPEND_JSONL","ledger/events.jsonl"],["RETURN_SHA256","ledger/events.jsonl"]]},
      {"tool_id":"TEXT_NOTE_WRITER_V1","input_schema":{"title":"string","body":"string"},"effects":[["WRITE_TEXT","notes/note.txt"]]}
    ]
    for i,(effect,keys,want) in enumerate([
      ("WRITE_JSON",["name","score"],"JSON_RECEIPT_WRITER_V1"),
      ("APPEND_JSONL",["event","value"],"JSONL_LEDGER_APPEND_V1")
    ],1):
        shuffled=packs[:]; rng.shuffle(shuffled)
        tid=f"T{i}"
        tasks.append({"id":tid,"kind":"TOOL_USE","tool_packs":shuffled,"required_effect":effect,"required_keys":keys})
        answers.append({"id":tid,"compare_fields":["status","tool_ids"],"expected":{"status":"UNIQUE","tool_ids":[want]}})

    rng=random.Random(SEEDS["PLANNING"])
    for i in range(2):
        mids=[f"r{i}_{j}_{rng.randrange(1000,9999)}" for j in range(4)]
        ops=[
          {"operator_id":f"op{i}_1","requires":["start"],"provides":[mids[0]]},
          {"operator_id":f"op{i}_2","requires":[mids[0]],"provides":[mids[1]]},
          {"operator_id":f"op{i}_3","requires":[mids[1]],"provides":["goal"]},
          {"operator_id":f"decoy{i}_a","requires":["missing"],"provides":["goal"]},
          {"operator_id":f"decoy{i}_b","requires":["start"],"provides":[mids[2]]}
        ]; rng.shuffle(ops)
        want=[f"op{i}_1",f"op{i}_2",f"op{i}_3"]
        tid=f"P{i+1}"
        tasks.append({"id":tid,"kind":"PLANNING","initial_resources":["start"],"goal_resource":"goal","operators":ops,"max_length":6})
        answers.append({"id":tid,"compare_fields":["status","plan"],"expected":{"status":"PLAN_FOUND","plan":want}})

    rng=random.Random(SEEDS["MEMORY"])
    for i in range(2):
        prev="0"*64; events=[]; state={}
        keys=["alpha","beta","gamma"]
        for seq in range(1,9):
            key=rng.choice(keys)
            if seq>2 and rng.random()<0.25:
                op="DELETE"; value=None; state.pop(key,None)
            else:
                op="SET"; value=rng.randrange(10,1000); state[key]=value
            ev=make_event(seq,op,key,value,prev); events.append(ev); prev=ev["event_hash"]
        tid=f"M{i+1}"
        tasks.append({"id":tid,"kind":"MEMORY","events":events})
        answers.append({"id":tid,"compare_fields":["state","last_seq","last_event_hash"],"expected":{"state":state,"last_seq":8,"last_event_hash":prev}})

    rng=random.Random(SEEDS["NOVEL_DOMAIN"])
    seqs=[
      ("CAP_AFFINE_CHAIN_SQUARE_LOG_SQRT_SAT_V1",["square","log1p_abs","sqrt_abs","sat"]),
      ("CAP_AFFINE_CHAIN_SAT_SQUARE_LOG_SQRT_V1",["sat","square","log1p_abs","sqrt_abs"]),
      ("CAP_AFFINE_CHAIN_LOG_SAT_SQRT_LOG_V1",["log1p_abs","sat","sqrt_abs","log1p_abs"])
    ]
    xs=[-4,-3.5,-3,-2.5,-2,-1.5,-1,-0.6,-0.2,0,0.4,0.8,1,1.5,2,2.5,3,3.5,4]
    for i in range(2):
        cid,seq=rng.choice(seqs)
        a=rng.uniform(-1.1,1.1); b=rng.uniform(-0.45,0.45); c=rng.choice([-1,1])*rng.uniform(0.4,1.5)
        rows=[{"x":x,"y":a+b*x+c*apply_chain(x,seq)} for x in xs]
        queries=[-4.5,4.5]
        preds=[a+b*x+c*apply_chain(x,seq) for x in queries]
        tid=f"N{i+1}"
        tasks.append({"id":tid,"kind":"NOVEL_DOMAIN","rows":rows,"queries":queries})
        answers.append({"id":tid,"compare_fields":["status","capability_id","predictions"],"expected":{"status":"LIBRARY_HIT__VERIFY_BEFORE_USE","capability_id":cid,"predictions":preds}})

    public={"schema":"PROJECT_BRAIN_H100_FRESH_CROSSCAP_PUBLIC_TASKS_V1","tasks":tasks}
    private={"schema":"PROJECT_BRAIN_H100_FRESH_CROSSCAP_ANSWERS_V1","answers":answers}
    return public,private

def main():
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("--tasks",required=True); ap.add_argument("--answers",required=True)
    a=ap.parse_args(); public,private=build()
    Path(a.tasks).write_text(json.dumps(public,indent=2,sort_keys=True)+"\n")
    Path(a.answers).write_text(json.dumps(private,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"tasks":len(public["tasks"]),"public_sha256":hashlib.sha256(Path(a.tasks).read_bytes()).hexdigest(),"answers_sha256":hashlib.sha256(Path(a.answers).read_bytes()).hexdigest()},sort_keys=True))
if __name__=="__main__": main()
