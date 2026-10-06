from __future__ import annotations
from collections import deque
import math,string

class P0SubstrateError(ValueError): pass

def logic_forward(facts,rules,goal):
    known=set(facts)
    changed=True
    while changed:
        changed=False
        for r in rules:
            if set(r["all"]).issubset(known) and r["then"] not in known:
                known.add(r["then"]);changed=True
    return goal in known

def plan(initial,goal,operators):
    start=frozenset(initial);q=deque([(start,[],0)]);best={start:0}
    solutions=[]
    while q:
        state,path,cost=q.popleft()
        if goal in state:
            solutions.append((cost,path));continue
        for op in operators:
            if set(op.get("preconditions",op.get("requires",[]))).issubset(state):
                ns=set(state)
                ns-=set(op.get("delete",[]))
                ns|=set(op.get("add",op.get("provides",[])))
                fs=frozenset(ns);nc=cost+int(op.get("cost",1))
                if nc<best.get(fs,10**18):
                    best[fs]=nc;q.append((fs,path+[op["id"]],nc))
    if not solutions:return None
    solutions.sort(key=lambda z:(z[0],len(z[1]),z[1]))
    return {"cost":solutions[0][0],"plan":solutions[0][1]}

def reduce_events(events):
    state={}
    for e in events:
        op=e["op"];k=e["key"]
        if op=="SET":state[k]=e["value"]
        elif op in ("ADD","INC"):state[k]=state.get(k,0)+e["value"]
        elif op=="MUL":state[k]=state.get(k,0)*e["value"]
        elif op in ("DEL","DELETE"):state.pop(k,None)
        else:raise P0SubstrateError("UNKNOWN_EVENT_OP")
    return state

def select_tool(required_effect,required_fields,tools,objective=None):
    m=[t for t in tools if required_effect in t["effects"] and set(required_fields).issubset(set(t["fields"]))]
    if not m:return None
    if objective:
        key=objective["field"];direction=objective.get("direction","MIN")
        vals=[t for t in m if key in t]
        if not vals:return None
        vals.sort(key=lambda t:(t[key],t["id"]),reverse=(direction=="MAX"))
        return vals[0]["id"]
    return m[0]["id"] if len(m)==1 else None

def lexical_role(cue,relations,context=None):
    g={}
    for a,b in relations:g.setdefault(a,[]).append(b)
    def reach(goal):
        q=deque([cue]);seen={cue}
        while q:
            x=q.popleft()
            if x==goal:return True
            for y in g.get(x,[]):
                if y not in seen:seen.add(y);q.append(y)
        return False
    inp,tgt=reach("INPUT"),reach("TARGET")
    if inp^tgt:return "INPUT" if inp else "TARGET"
    if context in ("USED_AS_INPUT","INPUT"):return "INPUT"
    if context in ("USED_AS_OUTPUT","TARGET"):return "TARGET"
    return None

def segment_bars(grid,min_height=2):
    h=len(grid);w=len(grid[0])
    col=[sum(1 for y in range(h) if grid[y][x]=="#") for x in range(w)]
    # A bar column must persist vertically; one-row bridges are ignored.
    on=[v>=min_height for v in col]
    ints=[];s=None
    for i,b in enumerate(on+[False]):
        if b and s is None:s=i
        elif not b and s is not None:
            ints.append((s,i-1));s=None
    return ints

def _shift(s,k):
    lo=string.ascii_lowercase
    out=[]
    for ch in s:
        if ch in lo:out.append(lo[(lo.index(ch)+k)%26])
        else:out.append(ch)
    return "".join(out)

def string_programs():
    p={"REVERSE":lambda s:s[::-1],"SORT":lambda s:"".join(sorted(s))}
    for k in range(-3,4):
        if k:p[f"SHIFT_{k}"]=lambda s,k=k:_shift(s,k)
    for k in range(1,4):
        p[f"ROTATE_LEFT_{k}"]=lambda s,k=k:s[k:]+s[:k]
        p[f"ROTATE_RIGHT_{k}"]=lambda s,k=k:s[-k:]+s[:-k]
    return p

def synthesize_string(examples,query):
    surv=[(n,f) for n,f in string_programs().items() if all(f(x)==y for x,y in examples)]
    if len(surv)!=1:return None
    n,f=surv[0];return {"program":n,"answer":f(query)}

def numeric_programs():
    out={}
    for a in range(-3,4):
      for b in range(-3,4):
        for power in (1,2,3):
          if a==0:continue
          out[f"{a}*X^{power}+{b}"]=lambda x,a=a,b=b,power=power:a*(x**power)+b
    return out

def synthesize_numeric(examples,query):
    surv=[(n,f) for n,f in numeric_programs().items() if all(f(x)==y for x,y in examples)]
    if len(surv)!=1:return None
    n,f=surv[0];return {"program":n,"answer":f(query)}
