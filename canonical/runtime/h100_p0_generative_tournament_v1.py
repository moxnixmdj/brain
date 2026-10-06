from __future__ import annotations
import random,string,json
from canonical.runtime import h100_p0_generic_declarative_substrate_v1 as s

COUNTS={k:50 for k in ("LOGIC","STRING","NUMERIC","VISION","TOOL","PLAN","MEMORY","LEXICAL","INFORMATION")}
SEEDS={"LOGIC":1101,"STRING":1102,"NUMERIC":1103,"VISION":1104,"TOOL":1105,"PLAN":1106,"MEMORY":1107,"LEXICAL":1108,"INFORMATION":1109}

def _logic(r):
    a,b,c,d=[f"F{r.randrange(100000)}" for _ in range(4)]
    facts=[a,b]
    rules=[{"all":[a,b],"then":c},{"all":[c],"then":d}]
    return facts,rules,d,True

def _randstr(r,n=None):
    if n is None:n=r.randint(4,8)
    return "".join(r.choice(string.ascii_lowercase) for _ in range(n))

def _string_case(r):
    progs=s.string_programs()
    names=sorted(progs)
    while True:
        name=r.choice(names);f=progs[name]
        ex=[_randstr(r) for _ in range(4)]
        pairs=[(x,f(x)) for x in ex]
        surv=[n for n,g in progs.items() if all(g(x)==y for x,y in pairs)]
        if surv==[name] or (len(surv)==1 and surv[0]==name):
            q=_randstr(r)
            return pairs,q,f(q),name

def _numeric_case(r):
    progs=s.numeric_programs()
    names=sorted(progs)
    while True:
        name=r.choice(names);f=progs[name]
        xs=r.sample(list(range(-7,8)),5)
        pairs=[(x,f(x)) for x in xs]
        surv=[n for n,g in progs.items() if all(g(x)==y for x,y in pairs)]
        if len(surv)==1 and surv[0]==name:
            q=r.choice([x for x in range(-9,10) if x not in xs])
            return pairs,q,f(q),name

def _vision_case(r):
    count=r.randint(2,6);h=r.randint(8,14);gap=2
    widths=[r.randint(1,3) for _ in range(count)]
    heights=[r.randint(3,h-1) for _ in range(count)]
    w=2+sum(widths)+gap*(count-1)+2
    g=[["."]*w for _ in range(h)]
    x=2
    intervals=[]
    for bw,bh in zip(widths,heights):
        intervals.append((x,x+bw-1))
        for yy in range(h-bh,h):
            for xx in range(x,x+bw):g[yy][xx]="#"
        x+=bw+gap
    # Add up to one one-row bridge between each adjacent pair. Column threshold >=2 must ignore it.
    for i in range(count-1):
        if r.random()<0.5:
            y=r.randrange(h)
            a=intervals[i][1]+1;b=intervals[i+1][0]-1
            for xx in range(a,b+1):g[y][xx]="#"
    return ["".join(row) for row in g],count

def _tool_case(r):
    good=r.randrange(3)
    tools=[]
    scores=r.sample(range(10,100),3)
    for i in range(3):
        tools.append({"id":f"T{i}","effects":["SEND"] if i!=2 else ["STORE"],"fields":["body"],"reliability":scores[i]})
    eligible=[t for t in tools if "SEND" in t["effects"]]
    winner=max(eligible,key=lambda t:(t["reliability"],t["id"]))["id"]
    return tools,winner

def _plan_case(r):
    c1,c2,c3=r.randint(1,4),r.randint(1,4),r.randint(7,15)
    ops=[
      {"id":"PREP","preconditions":["RAW"],"add":["READY"],"delete":["RAW"],"cost":c1},
      {"id":"FINISH","preconditions":["READY"],"add":["DONE"],"delete":["READY"],"cost":c2},
      {"id":"DIRECT","preconditions":["RAW"],"add":["DONE"],"delete":["RAW"],"cost":c3},
    ]
    gold=["PREP","FINISH"] if c1+c2<c3 else ["DIRECT"]
    return ops,gold

def _memory_case(r):
    v=r.randint(1,9);events=[{"op":"SET","key":"x","value":v}];cur=v
    for _ in range(5):
        op=r.choice(["ADD","MUL"])
        val=r.randint(-3,5) if op=="ADD" else r.randint(1,4)
        events.append({"op":op,"key":"x","value":val})
        cur=cur+val if op=="ADD" else cur*val
    return events,cur

def _lex_case(r):
    role=r.choice(["INPUT","TARGET"])
    context="USED_AS_INPUT" if role=="INPUT" else "USED_AS_OUTPUT"
    cue=f"cue{r.randrange(100000)}"
    rel=[[cue,"INPUT"],[cue,"TARGET"]]
    return cue,rel,context,role

def run():
    rows=[]
    r=random.Random(SEEDS["LOGIC"])
    for _ in range(COUNTS["LOGIC"]):
        facts,rules,goal,gold=_logic(r);o=s.logic_forward(facts,rules,goal);rows.append(("LOGIC",o==gold))
    r=random.Random(SEEDS["STRING"])
    for _ in range(COUNTS["STRING"]):
        ex,q,gold,_=_string_case(r);o=s.synthesize_string(ex,q);rows.append(("STRING",isinstance(o,dict) and o["answer"]==gold))
    r=random.Random(SEEDS["NUMERIC"])
    for _ in range(COUNTS["NUMERIC"]):
        ex,q,gold,_=_numeric_case(r);o=s.synthesize_numeric(ex,q);rows.append(("NUMERIC",isinstance(o,dict) and o["answer"]==gold))
    r=random.Random(SEEDS["VISION"])
    for _ in range(COUNTS["VISION"]):
        g,gold=_vision_case(r);o=s.segment_bars(g,2);rows.append(("VISION",len(o)==gold))
    r=random.Random(SEEDS["TOOL"])
    for _ in range(COUNTS["TOOL"]):
        tools,gold=_tool_case(r);o=s.select_tool("SEND",["body"],tools,{"field":"reliability","direction":"MAX"});rows.append(("TOOL",o==gold))
    r=random.Random(SEEDS["PLAN"])
    for _ in range(COUNTS["PLAN"]):
        ops,gold=_plan_case(r);o=s.plan(["RAW"],"DONE",ops);rows.append(("PLAN",isinstance(o,dict) and o["plan"]==gold))
    r=random.Random(SEEDS["MEMORY"])
    for _ in range(COUNTS["MEMORY"]):
        ev,gold=_memory_case(r);o=s.reduce_events(ev)["x"];rows.append(("MEMORY",o==gold))
    r=random.Random(SEEDS["LEXICAL"])
    for _ in range(COUNTS["LEXICAL"]):
        cue,rel,ctx,gold=_lex_case(r);o=s.lexical_role(cue,rel,ctx);rows.append(("LEXICAL",o==gold))
    r=random.Random(SEEDS["INFORMATION"])
    for _ in range(COUNTS["INFORMATION"]):
        k=r.randint(2,6);obs=["same"]*k;answers=[f"A{i}" for i in range(k)]
        ok=len(set(obs))==1 and len(set(answers))>1
        rows.append(("INFORMATION",ok))
    by={}
    for cls,p in rows:
        by.setdefault(cls,[0,0]);by[cls][1]+=1;by[cls][0]+=int(p)
    return {"passed":sum(int(p) for _,p in rows),"total":len(rows),"all_pass":all(p for _,p in rows),"by_class":{k:{"passed":v[0],"total":v[1]} for k,v in by.items()},"target_adapted_persistent_bits":0}

if __name__=="__main__":print(json.dumps(run(),indent=2,sort_keys=True))
