"""Independent prewave proof population for the frozen active SA-CCR credit contract.

Evaluator code intentionally does not import canonical.runtime.saccr_credit_kernel.
Candidate sees only the frozen contract inputs; all intermediate lineage and the
final add-on remain hidden oracle values.
"""
from __future__ import annotations
import math, random
from typing import Any, Mapping

SF_SINGLE={"AAA":0.0038,"AA":0.0038,"A":0.0042,"BBB":0.0054,"BB":0.0106,"B":0.0160,"CCC":0.0600}
SF_INDEX={"IG":0.0038,"SG":0.0106}

def _sd(s,e):
    s=max(float(s),0.0); e=max(float(e),s+10.0/250.0)
    return (math.exp(-0.05*s)-math.exp(-0.05*e))/0.05
def _mf(t):
    if t.get("margined_mpor") is None:
        return math.sqrt(min(max(float(t["end"])-float(t["start"]),10.0/250.0),1.0))
    return 1.5*math.sqrt(max(float(t["margined_mpor"]),10.0/250.0))
def _sf(t):
    return (SF_INDEX if t["is_index"] else SF_SINGLE)[str(t["credit_rating"]).upper()]
def _rho(t): return 0.80 if t["is_index"] else 0.50
def _trace(t):
    sd=_sd(t["start"],t["end"]); d=float(t["notional"])*sd
    delta=float(t["direction"]); mf=_mf(t); eff=d*delta*mf; sf=_sf(t)
    return {"supervisory_duration":sd,"adjusted_notional":d,"delta":delta,
            "maturity_factor":mf,"effective_notional":eff,"supervisory_factor":sf,
            "supervisory_correlation":_rho(t),"directional_addon":sf*eff}
def _addon(trades):
    eff={}; sf={}; rho={}
    for t in trades:
        k=t["reference"]; tr=_trace(t)
        eff[k]=eff.get(k,0.0)+tr["effective_notional"]; sf[k]=tr["supervisory_factor"]; rho[k]=tr["supervisory_correlation"]
    systematic=0.0; idio=0.0
    for k,v in eff.items():
        ak=sf[k]*v; systematic+=rho[k]*ak; idio+=(1-rho[k]*rho[k])*ak*ak
    return math.sqrt(systematic*systematic+idio)

def generate_case(seed:int)->dict[str,Any]:
    r=random.Random(seed); n=r.randint(2,9); refs=[f"E{i}" for i in range(r.randint(1,4))]
    trades=[]
    for _ in range(n):
        is_index=r.random()<0.28
        rating=r.choice(list(SF_INDEX if is_index else SF_SINGLE))
        start=round(r.uniform(0,4),5); end=round(start+r.uniform(0.02,9),5)
        trades.append({"notional":round(r.uniform(1e4,9e7),4),"start":start,"end":end,
            "direction":r.choice([-1,1]),"reference":r.choice(refs),"credit_rating":rating,
            "is_index":is_index,"margined_mpor":None if r.random()<0.55 else round(r.uniform(0.01,0.25),5)})
    return {"behavior_id":"SA_CCR_CREDIT_EFFECTIVE_NOTIONAL_AND_ADDON_001",
            "task":{"trades":trades},
            "_oracle":{"traces":[_trace(t) for t in trades],"credit_addon":_addon(trades)}}

def public_task(case): return {"behavior_id":case["behavior_id"],"task":case["task"]}

def _close(a,b,tol=1e-10):
    return math.isclose(float(a),float(b),rel_tol=tol,abs_tol=tol)
def score_case(case:Mapping[str,Any], candidate:Mapping[str,Any])->dict[str,Any]:
    traces=candidate.get("traces"); addon=candidate.get("credit_addon")
    if not isinstance(traces,list) or len(traces)!=len(case["_oracle"]["traces"]):
        return {"pass":False,"reason":"TRACE_SHAPE"}
    fields=("supervisory_duration","adjusted_notional","delta","maturity_factor","effective_notional",
            "supervisory_factor","supervisory_correlation","directional_addon")
    for i,(got,exp) in enumerate(zip(traces,case["_oracle"]["traces"])):
        if not isinstance(got,Mapping): return {"pass":False,"reason":f"TRACE_NOT_OBJECT:{i}"}
        for f in fields:
            if f not in got or not _close(got[f],exp[f]):
                return {"pass":False,"reason":f"LINEAGE_MISMATCH:{i}:{f}"}
    if addon is None or not _close(addon,case["_oracle"]["credit_addon"]):
        return {"pass":False,"reason":"ADDON_MISMATCH"}
    return {"pass":True,"reason":"PASS"}

def mutation_cases(case):
    task=case["task"]; out=[]
    for mutation in ("FLIP_DIRECTION","TOGGLE_MARGIN","CHANGE_RATING","REASSIGN_REFERENCE","TOGGLE_INDEX"):
        out.append({"id":mutation,"property":"LOAD_BEARING_INTERMEDIATE_OR_AGGREGATION_MUST_CHANGE_WHEN_APPLICABLE"})
    return out
