"""Cross-capability zero-target-state substrate G0.

Frozen before the fresh cross-capability task suite. The runtime contains
generic algorithms only. It must not contain future task IDs, answers, formulas,
chart colors, generated instances, or expected capability IDs.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from collections import deque
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime import h100_jit_lexical_role_v1 as lexical
from canonical.runtime import h100_verified_capability_registry_v8 as registry
from canonical.runtime import h100_zero_learned_event_memory_v1 as eventmem

SCHEMA="PROJECT_BRAIN_H100_CROSSCAP_G0_V1"


class G0Error(ValueError):
    pass


# ---------- reasoning: generic finite CSP ----------

def _constraint_ok(c: Mapping[str,Any], env: Mapping[str,int]) -> bool:
    op=str(c.get("op") or "")
    vars_=list(c.get("vars") or [])
    if any(v not in env for v in vars_):
        return True
    vals=[env[v] for v in vars_]
    if op=="EQ":
        return len(vals)==2 and vals[0]==vals[1]
    if op=="NEQ":
        return len(vals)==2 and vals[0]!=vals[1]
    if op=="LT":
        return len(vals)==2 and vals[0]<vals[1]
    if op=="GT":
        return len(vals)==2 and vals[0]>vals[1]
    if op=="ALL_DIFF":
        return len(vals)==len(set(vals))
    if op=="SUM_EQ":
        return sum(vals)==int(c["value"])
    if op=="SUM_LT":
        return sum(vals)<int(c["value"])
    if op=="SUM_GT":
        return sum(vals)>int(c["value"])
    raise G0Error("CSP_CONSTRAINT_UNSUPPORTED:"+op)


def solve_finite_csp(spec: Mapping[str,Any]) -> dict[str,Any]:
    variables=[str(x) for x in spec.get("variables",[])]
    domains=spec.get("domains")
    constraints=list(spec.get("constraints") or [])
    if not variables or not isinstance(domains,Mapping):
        raise G0Error("CSP_SPEC_INVALID")
    doms=[]
    for v in variables:
        raw=domains.get(v)
        if not isinstance(raw,Sequence) or isinstance(raw,(str,bytes)) or not raw:
            raise G0Error("CSP_DOMAIN_INVALID:"+v)
        doms.append([int(x) for x in raw])
    sols=[]
    for values in itertools.product(*doms):
        env=dict(zip(variables,values))
        if all(_constraint_ok(c,env) for c in constraints):
            sols.append(env)
    return {"status":"UNIQUE" if len(sols)==1 else ("NONE" if not sols else "MULTIPLE"),"solutions":sols}


# ---------- coding: bounded generic unary-expression synthesis ----------

def _expr_value(expr:Any,x:int)->int:
    kind=expr[0]
    if kind=="x":
        return int(x)
    if kind=="c":
        return int(expr[1])
    if kind=="neg":
        return -_expr_value(expr[1],x)
    a=_expr_value(expr[1],x)
    b=_expr_value(expr[2],x)
    if kind=="add": return a+b
    if kind=="sub": return a-b
    if kind=="mul": return a*b
    raise G0Error("EXPR_UNKNOWN")


def _expr_key(expr:Any)->str:
    return json.dumps(expr,separators=(",",":"))


def _expr_source(expr:Any)->str:
    kind=expr[0]
    if kind=="x": return "x"
    if kind=="c": return str(expr[1])
    if kind=="neg": return f"(-{_expr_source(expr[1])})"
    op={"add":"+","sub":"-","mul":"*"}[kind]
    return f"({_expr_source(expr[1])}{op}{_expr_source(expr[2])})"


def synthesize_unary_integer_program(examples: Sequence[Mapping[str,int]], max_depth:int=3) -> dict[str,Any]:
    if not examples or max_depth<0:
        raise G0Error("SYNTH_SPEC_INVALID")
    xs=[int(r["x"]) for r in examples]
    ys=[int(r["y"]) for r in examples]
    base=[("x",)]+[("c",c) for c in range(-3,4)]
    levels=[base]
    seen={_expr_key(e) for e in base}
    candidates=list(base)
    for depth in range(1,max_depth+1):
        prev=[e for level in levels for e in level]
        new=[]
        for e in prev:
            n=("neg",e)
            k=_expr_key(n)
            if k not in seen:
                seen.add(k); new.append(n)
        for a in prev:
            for b in prev:
                for op in ("add","sub","mul"):
                    e=(op,a,b); k=_expr_key(e)
                    if k not in seen:
                        seen.add(k); new.append(e)
        levels.append(new); candidates.extend(new)
        hits=[]
        for e in candidates:
            try:
                if [_expr_value(e,x) for x in xs]==ys:
                    hits.append(e)
            except Exception:
                pass
        if hits:
            hits.sort(key=lambda e:(len(_expr_source(e)),_expr_source(e)))
            best=hits[0]
            return {"status":"PROGRAM_FOUND","expr":best,"source":f"def f(x): return {_expr_source(best)}","depth":depth}
    return {"status":"NO_PROGRAM","expr":None,"source":None,"depth":None}


# ---------- language ----------

def resolve_lexical_roles(clauses:Any, knowledge:Mapping[str,Any])->dict[str,Any]:
    return lexical.induce_roles(clauses,knowledge)


# ---------- vision: generic ASCII PPM + foreground components ----------

def parse_p3_ppm(text:str)->tuple[int,int,list[tuple[int,int,int]]]:
    if not isinstance(text,str):
        raise G0Error("PPM_TEXT_INVALID")
    toks=[]
    for line in text.splitlines():
        line=line.split("#",1)[0]
        toks.extend(line.split())
    if len(toks)<4 or toks[0]!="P3":
        raise G0Error("PPM_HEADER_INVALID")
    w,h,maxv=map(int,toks[1:4])
    if w<1 or h<1 or maxv<1:
        raise G0Error("PPM_DIMENSION_INVALID")
    nums=[int(x) for x in toks[4:]]
    if len(nums)!=w*h*3:
        raise G0Error("PPM_PIXEL_COUNT_INVALID")
    pix=[]
    for i in range(0,len(nums),3):
        rgb=tuple(nums[i:i+3])
        if any(v<0 or v>maxv for v in rgb):
            raise G0Error("PPM_PIXEL_RANGE_INVALID")
        pix.append(rgb)
    return w,h,pix


def ppm_foreground_components(text:str, white_threshold:float=0.93)->dict[str,Any]:
    w,h,pix=parse_p3_ppm(text)
    maxv=max(max(p) for p in pix) if pix else 255
    cutoff=maxv*white_threshold
    fg=[not (r>=cutoff and g>=cutoff and b>=cutoff) for r,g,b in pix]
    seen=[False]*(w*h)
    comps=[]
    for idx,on in enumerate(fg):
        if not on or seen[idx]: continue
        q=[idx]; seen[idx]=True; xs=[]; ys=[]
        while q:
            j=q.pop(); y,x=divmod(j,w); xs.append(x); ys.append(y)
            for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if 0<=nx<w and 0<=ny<h:
                    k=ny*w+nx
                    if fg[k] and not seen[k]:
                        seen[k]=True; q.append(k)
        comps.append({"area":len(xs),"bbox":[min(xs),min(ys),max(xs),max(ys)]})
    comps.sort(key=lambda c:(-c["area"],c["bbox"]))
    return {"width":w,"height":h,"components":comps}


# ---------- tool use: generic declared-contract selection ----------

def select_tool_by_contract(tool_packs:Sequence[Mapping[str,Any]], *, required_effect:str, required_keys:Sequence[str])->dict[str,Any]:
    hits=[]
    need=set(map(str,required_keys))
    for pack in tool_packs:
        effects=pack.get("effects") or pack.get("effect_ops") or []
        effect_text=json.dumps(effects,sort_keys=True)
        schema=pack.get("input_schema") or {}
        keys=set(map(str,schema.keys())) if isinstance(schema,Mapping) else set()
        if str(required_effect) in effect_text and need.issubset(keys):
            hits.append(pack)
    return {"status":"UNIQUE" if len(hits)==1 else ("NONE" if not hits else "MULTIPLE"),"matches":hits}


# ---------- planning: generic monotonic resource BFS ----------

def plan_resources(initial_resources:Sequence[str], goal_resource:str, operators:Sequence[Mapping[str,Any]], max_length:int=8)->dict[str,Any]:
    initial=frozenset(map(str,initial_resources)); goal=str(goal_resource)
    ops=sorted([dict(x) for x in operators],key=lambda x:str(x["operator_id"]))
    q=deque([(initial,tuple())]); seen={initial}; expanded=0
    while q:
        res,path=q.popleft(); expanded+=1
        if goal in res:
            return {"status":"PLAN_FOUND","plan":list(path),"expanded_states":expanded}
        if len(path)>=max_length: continue
        for op in ops:
            oid=str(op["operator_id"])
            req=set(map(str,op.get("requires",[]))); prov=set(map(str,op.get("provides",[])))
            if oid in path or not req.issubset(res): continue
            nxt=frozenset(set(res)|prov)
            if nxt==res or nxt in seen: continue
            seen.add(nxt); q.append((nxt,path+(oid,)))
    return {"status":"NO_PLAN","plan":None,"expanded_states":expanded}


# ---------- memory ----------

def replay_events(events:Iterable[Mapping[str,Any]], snapshot:Mapping[str,Any]|None=None)->dict[str,Any]:
    return eventmem.replay(events,snapshot)


# ---------- novel-domain adaptation ----------

def resolve_numeric_capability(rows:Sequence[Mapping[str,Any]])->dict[str,Any]:
    return registry.resolve_verified_capability(rows,target="y",input_name="x")


def substrate_snapshot()->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":"G0_FROZEN_GENERIC_SUBSTRATE",
        "target_adapted_persistent_bits_for_future_suite":0,
        "learned_target_bytes_for_future_suite":0,
        "generic_mechanisms":[
            "FINITE_CSP_SEARCH",
            "BOUNDED_INTEGER_PROGRAM_SYNTHESIS",
            "JIT_LEXICAL_ROLE_RESOLUTION",
            "ASCII_PPM_FOREGROUND_COMPONENTS",
            "DECLARED_EFFECT_CONTRACT_SELECTION",
            "MONOTONIC_RESOURCE_BFS",
            "HASH_CHAIN_EVENT_REPLAY",
            "VERIFIED_CAPABILITY_REGISTRY_V8_RESOLUTION",
        ],
    }
