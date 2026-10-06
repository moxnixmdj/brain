"""G1 generic repair layer created after adversarial V2.

G1 is target-adapted relative to V2 and therefore gets no zero-state credit on
V2. It must be frozen before V3 and validated on fresh tasks.
"""
from __future__ import annotations

import itertools, json, math
from collections import deque
from fractions import Fraction
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_crosscap_g0_v1 as g0

SCHEMA="PROJECT_BRAIN_H100_CROSSCAP_G1_V1"
class G1Error(ValueError): pass


def solve_reasoning(task:Mapping[str,Any])->dict[str,Any]:
    spec=json.loads(json.dumps(task["spec"]))
    extra=task.get("side_constraints") or []
    spec.setdefault("constraints",[]).extend(extra)
    return g0.solve_finite_csp(spec)


def _poly_eval(coeff,x):
    total=Fraction(0)
    p=Fraction(1)
    xx=Fraction(int(x))
    for c in coeff:
        total+=c*p; p*=xx
    return total


def _solve_linear_fraction(a,b):
    n=len(a)
    m=[[Fraction(x) for x in a[i]]+[Fraction(b[i])] for i in range(n)]
    for col in range(n):
        pivot=next((r for r in range(col,n) if m[r][col]!=0),None)
        if pivot is None: return None
        m[col],m[pivot]=m[pivot],m[col]
        d=m[col][col]; m[col]=[x/d for x in m[col]]
        for r in range(n):
            if r==col: continue
            f=m[r][col]
            if f: m[r]=[x-f*y for x,y in zip(m[r],m[col])]
    return [m[i][-1] for i in range(n)]


def synthesize_polynomial(examples:Sequence[Mapping[str,int]], max_degree:int=3)->dict[str,Any]:
    xs=[int(r["x"]) for r in examples]; ys=[int(r["y"]) for r in examples]
    if len(set(xs))!=len(xs) or not xs: raise G1Error("POLY_EXAMPLES_INVALID")
    for deg in range(max_degree+1):
        if len(xs)<deg+1: continue
        sel=list(range(deg+1))
        a=[[Fraction(xs[i])**j for j in range(deg+1)] for i in sel]
        b=[Fraction(ys[i]) for i in sel]
        coeff=_solve_linear_fraction(a,b)
        if coeff is None: continue
        if all(_poly_eval(coeff,x)==Fraction(y) for x,y in zip(xs,ys)):
            def fmt(q):
                return str(q.numerator) if q.denominator==1 else f"({q.numerator}/{q.denominator})"
            terms=[]
            for j,c in enumerate(coeff):
                if c==0: continue
                cs=fmt(c)
                terms.append(cs if j==0 else (f"{cs}*x" if j==1 else f"{cs}*(x**{j})"))
            expr=" + ".join(terms) if terms else "0"
            return {"status":"PROGRAM_FOUND","degree":deg,"coefficients":[[c.numerator,c.denominator] for c in coeff],"source":"def f(x): return "+expr}
    return {"status":"NO_PROGRAM","degree":None,"coefficients":None,"source":None}


def predict_polynomial(result:Mapping[str,Any],x:int):
    coeff=[Fraction(n,d) for n,d in result["coefficients"]]
    q=_poly_eval(coeff,int(x))
    return q.numerator if q.denominator==1 else float(q)


def ppm_color_components(text:str)->dict[str,Any]:
    w,h,pix=g0.parse_p3_ppm(text)
    maxv=max(max(p) for p in pix)
    cutoff=maxv*0.93
    active=[not all(v>=cutoff for v in p) for p in pix]
    seen=[False]*(w*h); comps=[]
    for idx,on in enumerate(active):
        if not on or seen[idx]: continue
        color=pix[idx]; q=[idx]; seen[idx]=True; xs=[]; ys=[]
        while q:
            j=q.pop(); y,x=divmod(j,w); xs.append(x); ys.append(y)
            for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if 0<=nx<w and 0<=ny<h:
                    k=ny*w+nx
                    if active[k] and not seen[k] and pix[k]==color:
                        seen[k]=True; q.append(k)
        comps.append({"color":list(color),"area":len(xs),"bbox":[min(xs),min(ys),max(xs),max(ys)]})
    comps.sort(key=lambda c:(c["color"],c["bbox"]))
    return {"width":w,"height":h,"components":comps}


def select_tool(task:Mapping[str,Any])->dict[str,Any]:
    base=g0.select_tool_by_contract(task["tool_packs"],required_effect=str(task["required_effect"]),required_keys=task["required_keys"])
    matches=list(base["matches"])
    metadata=task.get("metadata_requirements")
    if metadata is None and "purpose" in task: metadata={"purpose":task["purpose"]}
    if isinstance(metadata,Mapping):
        matches=[p for p in matches if all(p.get(k)==v for k,v in metadata.items())]
    return {"status":"UNIQUE" if len(matches)==1 else ("NONE" if not matches else "MULTIPLE"),"matches":matches}


def plan_nonmonotonic(task:Mapping[str,Any])->dict[str,Any]:
    initial=frozenset(map(str,task["initial_resources"]))
    required=set(map(str,task.get("required_final_resources") or [task["goal_resource"]]))
    ops=sorted([dict(x) for x in task["operators"]],key=lambda x:str(x["operator_id"]))
    maxlen=int(task.get("max_length",8))
    q=deque([(initial,tuple())]); seen={initial}; expanded=0
    while q:
        state,path=q.popleft(); expanded+=1
        if required.issubset(state):
            return {"status":"PLAN_FOUND","plan":list(path),"expanded_states":expanded}
        if len(path)>=maxlen: continue
        for op in ops:
            req=set(map(str,op.get("requires",[])))
            if not req.issubset(state): continue
            nxt=set(state)
            nxt.difference_update(map(str,op.get("removes",[])))
            nxt.update(map(str,op.get("provides",[])))
            fn=frozenset(nxt)
            if fn in seen: continue
            seen.add(fn); q.append((fn,path+(str(op["operator_id"]),)))
    return {"status":"NO_PLAN","plan":None,"expanded_states":expanded}


def query_history(events:Sequence[Mapping[str,Any]], query:Mapping[str,Any])->Any:
    op=str(query["op"]); key=str(query["key"])
    vals=[e.get("value") for e in events if e.get("op")=="SET" and str(e.get("key"))==key]
    if op=="MAX_SEEN": return max(vals) if vals else None
    if op=="MIN_SEEN": return min(vals) if vals else None
    if op=="COUNT_SET": return len(vals)
    if op=="LAST_VALUE": return vals[-1] if vals else None
    raise G1Error("HISTORY_QUERY_UNSUPPORTED")


BASES={
 "EXP_NEG_ABS":lambda x:math.exp(-abs(x)),
 "EXP_NEG_SQUARE":lambda x:math.exp(-(x*x)),
 "SIN":lambda x:math.sin(x),
 "COS":lambda x:math.cos(x),
 "TANH":lambda x:math.tanh(x),
 "RECIP_1_ABS":lambda x:1.0/(1.0+abs(x)),
 "SQRT_ABS":lambda x:math.sqrt(abs(x)),
 "LOG1P_ABS":lambda x:math.log1p(abs(x)),
 "SAT":lambda x:x/(1.0+abs(x)),
 "SQUARE":lambda x:x*x,
 "CUBE":lambda x:x*x*x,
}


def _solve3_float(a,b):
    m=[list(map(float,a[i]))+[float(b[i])] for i in range(3)]
    for c in range(3):
        p=max(range(c,3),key=lambda r:abs(m[r][c]))
        if abs(m[p][c])<1e-12: return None
        m[c],m[p]=m[p],m[c]
        d=m[c][c]; m[c]=[v/d for v in m[c]]
        for r in range(3):
            if r==c: continue
            f=m[r][c]; m[r]=[x-f*y for x,y in zip(m[r],m[c])]
    return [m[i][-1] for i in range(3)]


def _fit_basis(xs,ys,fn):
    cols=[[1.0]*len(xs),list(xs),[fn(x) for x in xs]]
    xtx=[[sum(cols[i][k]*cols[j][k] for k in range(len(xs))) for j in range(3)] for i in range(3)]
    xty=[sum(cols[i][k]*ys[k] for k in range(len(xs))) for i in range(3)]
    for i in range(3): xtx[i][i]+=1e-14
    c=_solve3_float(xtx,xty)
    if c is None: return None
    pred=[c[0]+c[1]*x+c[2]*fn(x) for x in xs]
    mean=sum(ys)/len(ys); spread=math.sqrt(sum((y-mean)**2 for y in ys)/len(ys))
    scale=max(spread,max(abs(y) for y in ys)*1e-9,1e-12)
    err=math.sqrt(sum((a-b)**2 for a,b in zip(ys,pred))/len(ys))/scale
    return c,err


def resolve_generic_numeric(rows:Sequence[Mapping[str,Any]], threshold:float=1e-8)->dict[str,Any]:
    base=g0.resolve_numeric_capability(rows)
    if base.get("status")=="LIBRARY_HIT__VERIFY_BEFORE_USE":
        return {"status":"CAPABILITY_HIT__VERIFY_BEFORE_USE","route":"G0_REGISTRY","resolution":base}
    xs=[float(r["x"]) for r in rows]; ys=[float(r["y"]) for r in rows]
    hits=[]
    for name,fn in BASES.items():
        z=_fit_basis(xs,ys,fn)
        if z is not None and z[1]<=threshold: hits.append((z[1],name,z[0]))
    if not hits: return {"status":"CAPABILITY_MISS","route":None}
    hits.sort(key=lambda x:(x[0],x[1]))
    err,name,c=hits[0]
    return {"status":"CAPABILITY_HIT__VERIFY_BEFORE_USE","route":"G1_ANALYTIC_BASIS","basis":name,"coefficients":c,"train_nrmse":err}


def predict_generic_numeric(resolution:Mapping[str,Any],x:float)->float:
    if resolution.get("route")=="G0_REGISTRY":
        from canonical.runtime import h100_verified_capability_registry_v8 as registry
        return float(registry.predict(resolution["resolution"],{"x":float(x)}))
    if resolution.get("route")=="G1_ANALYTIC_BASIS":
        c=list(map(float,resolution["coefficients"])); fn=BASES[str(resolution["basis"])]
        return c[0]+c[1]*float(x)+c[2]*fn(float(x))
    raise G1Error("NUMERIC_RESOLUTION_INVALID")
