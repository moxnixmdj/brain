"""Information-safe proof population for the frozen SA-CCR credit contract.

The candidate sees only structured contract inputs. All expected intermediates
and final aggregation remain in _oracle. This module does not import the Brain
candidate kernel.
"""
from __future__ import annotations
import math
import random
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_SACCR_CREDIT_INFORMATION_SAFE_PROOF_V1"
SINGLE={"AAA":0.0038,"AA":0.0038,"A":0.0042,"BBB":0.0054,"BB":0.0106,"B":0.0160,"CCC":0.0600}
INDEX={"IG":0.0038,"SG":0.0106}

def _sd(start: float, end: float) -> float:
    s = max(float(start), 0.0)
    e = max(float(end), s + 0.04)
    return (math.exp(-0.05*s)-math.exp(-0.05*e))/0.05

def _mf(row: Mapping[str, Any]) -> float:
    mpor=row["margined_mpor"]
    if mpor is None:
        residual=max(float(row["end"])-float(row["start"]),0.04)
        return math.sqrt(min(residual,1.0))
    return 1.5*math.sqrt(max(float(mpor),0.04))

def _trace(row: Mapping[str, Any]) -> dict[str, float]:
    sd=_sd(row["start"],row["end"])
    adj=float(row["notional"])*sd
    delta=float(row["direction"])
    mf=_mf(row)
    if row["is_index"]:
        sf=INDEX[str(row["credit_rating"]).upper()]
        rho=0.80
    else:
        sf=SINGLE[str(row["credit_rating"]).upper()]
        rho=0.50
    eff=adj*delta*mf
    return {
        "supervisory_duration":sd,
        "adjusted_notional":adj,
        "delta":delta,
        "maturity_factor":mf,
        "effective_notional":eff,
        "supervisory_factor":sf,
        "supervisory_correlation":rho,
        "directional_addon":sf*eff,
    }

def _addon(rows: list[Mapping[str, Any]], traces: list[Mapping[str, float]]) -> float:
    groups: dict[str, dict[str, float]]={}
    for row,tr in zip(rows,traces):
        key=str(row["reference"])
        g=groups.setdefault(key,{
            "effective_notional":0.0,
            "sf":float(tr["supervisory_factor"]),
            "rho":float(tr["supervisory_correlation"]),
        })
        if not math.isclose(g["sf"],float(tr["supervisory_factor"]),rel_tol=0,abs_tol=0):
            raise ValueError("REFERENCE_ENTITY_MIXED_SUPERVISORY_FACTOR")
        if not math.isclose(g["rho"],float(tr["supervisory_correlation"]),rel_tol=0,abs_tol=0):
            raise ValueError("REFERENCE_ENTITY_MIXED_CORRELATION")
        g["effective_notional"] += float(tr["effective_notional"])
    systematic=sum(g["rho"]*g["sf"]*g["effective_notional"] for g in groups.values())
    idio=sum((1.0-g["rho"]**2)*(g["sf"]*g["effective_notional"])**2 for g in groups.values())
    return math.sqrt(systematic**2+idio)

def generate_case(seed: int) -> dict[str, Any]:
    if not isinstance(seed,int) or isinstance(seed,bool):
        raise ValueError("SEED_MUST_BE_INTEGER")
    r=random.Random(seed)
    nref=r.randint(2,5)
    entities=[]
    for j in range(nref):
        is_index = (j == 1) if j < 2 else bool(r.getrandbits(1))
        table=INDEX if is_index else SINGLE
        entities.append((f"E{j}",is_index,r.choice(sorted(table))))
    rows=[]
    ntrades=r.randint(max(4,nref),10)
    for i in range(ntrades):
        ref,is_index,rating=entities[i % nref if i < nref else r.randrange(nref)]
        start=round(r.uniform(-0.5,2.5),6)
        end=round(start+r.uniform(0.001,7.0),6)
        rows.append({
            "notional":round(r.uniform(1_000.0,30_000_000.0),4),
            "start":start,
            "end":end,
            "direction":-1 if i % 3 == 0 else 1,
            "reference":ref,
            "credit_rating":rating,
            "is_index":is_index,
            "margined_mpor":None if i % 2 == 0 else round(r.uniform(0.01,0.25),6),
        })
    traces=[_trace(x) for x in rows]
    oracle={"trade_traces":traces,"credit_addon":_addon(rows,traces)}
    return {
        "schema":SCHEMA,
        "behavior_id":"SA_CCR_CREDIT_EFFECTIVE_NOTIONAL_AND_ADDON_001",
        "seed":seed,
        "task":{"trades":rows},
        "_oracle":oracle,
    }

def public_task(case: Mapping[str, Any]) -> dict[str, Any]:
    return {k:v for k,v in case.items() if k != "_oracle"}

def _close(a: Any, b: Any) -> bool:
    return isinstance(a,(int,float)) and not isinstance(a,bool) and math.isclose(
        float(a),float(b),rel_tol=1e-11,abs_tol=1e-9
    )

def score_case(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(candidate,Mapping) or candidate.get("status") != "OK":
        return {"pass":False,"reason":"CANDIDATE_STATUS_INVALID"}
    expected=case["_oracle"]
    got=candidate.get("trade_traces")
    if not isinstance(got,list) or len(got) != len(expected["trade_traces"]):
        return {"pass":False,"reason":"TRACE_COUNT_MISMATCH"}
    fields=tuple(expected["trade_traces"][0])
    for i,(e,g) in enumerate(zip(expected["trade_traces"],got)):
        if not isinstance(g,Mapping):
            return {"pass":False,"reason":f"TRACE_{i}_NOT_OBJECT"}
        for key in fields:
            if not _close(g.get(key),e[key]):
                return {"pass":False,"reason":f"TRACE_{i}_{key}_MISMATCH"}
    if not _close(candidate.get("credit_addon"),expected["credit_addon"]):
        return {"pass":False,"reason":"CREDIT_ADDON_MISMATCH"}
    return {"pass":True,"reason":"PASS"}
