"""Minimal Brain-owned SA-CCR credit-derivative kernel.

Mechanism harvested from ankitjha67/baselkit at
52293ef9dfd9d260a0e954460945a7356843d18d (Apache-2.0), restricted to the
credit-derivative path needed by the contracted SA-CCR residual.

Scope: linear credit single-name/index derivatives; supervisory duration,
adjusted notional, maturity factor, signed effective notional, CRE52.72
supervisory factors/correlations, entity aggregation, and credit add-on.
Options/CDO tranches and whole-netting-set RC/PFE are outside this narrow slice.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import math

SF_CREDIT_SINGLE={"AAA":0.0038,"AA":0.0038,"A":0.0042,"BBB":0.0054,"BB":0.0106,"B":0.0160,"CCC":0.0600}
SF_CREDIT_INDEX={"IG":0.0038,"SG":0.0106}
RHO_CREDIT_SINGLE=0.50
RHO_CREDIT_INDEX=0.80

@dataclass(frozen=True)
class CreditTrade:
    notional: float
    start: float
    end: float
    direction: int=1
    reference: str="default"
    credit_rating: str="BBB"
    is_index: bool=False
    margined_mpor: float|None=None

    def __post_init__(self):
        if self.notional < 0: raise ValueError("notional must be non-negative")
        if self.end < self.start: raise ValueError("end must be >= start")
        if self.direction not in (-1,1): raise ValueError("direction must be +/-1")
        rating=self.credit_rating.upper()
        allowed=SF_CREDIT_INDEX if self.is_index else SF_CREDIT_SINGLE
        if rating not in allowed: raise ValueError(f"unsupported credit rating: {rating}")

def supervisory_duration(start: float,end: float)->float:
    s=max(float(start),0.0)
    e=max(float(end),s+10.0/250.0)
    return (math.exp(-0.05*s)-math.exp(-0.05*e))/0.05

def adjusted_notional(t:CreditTrade)->float:
    return t.notional*supervisory_duration(t.start,t.end)

def maturity_factor(t:CreditTrade)->float:
    if t.margined_mpor is None:
        m=max(t.end-t.start,10.0/250.0)
        return math.sqrt(min(m,1.0))
    return 1.5*math.sqrt(max(t.margined_mpor,10.0/250.0))

def effective_notional(t:CreditTrade)->float:
    return float(t.direction)*adjusted_notional(t)*maturity_factor(t)

def supervisory_factor(t:CreditTrade)->float:
    rating=t.credit_rating.upper()
    return (SF_CREDIT_INDEX if t.is_index else SF_CREDIT_SINGLE)[rating]

def supervisory_correlation(t:CreditTrade)->float:
    return RHO_CREDIT_INDEX if t.is_index else RHO_CREDIT_SINGLE

def trace_trade(t:CreditTrade)->dict:
    sd=supervisory_duration(t.start,t.end)
    d=t.notional*sd
    delta=float(t.direction)
    mf=maturity_factor(t)
    eff=d*delta*mf
    sf=supervisory_factor(t)
    addon_k=sf*eff
    return {
        "trade":asdict(t),
        "supervisory_duration":sd,
        "adjusted_notional":d,
        "delta":delta,
        "maturity_factor":mf,
        "effective_notional":eff,
        "supervisory_factor":sf,
        "supervisory_correlation":supervisory_correlation(t),
        "directional_addon":addon_k,
    }

def credit_addon(trades:list[CreditTrade])->float:
    if not trades: raise ValueError("at least one credit trade required")
    entity_eff={}
    entity_sf={}
    entity_rho={}
    for t in trades:
        key=t.reference
        entity_eff[key]=entity_eff.get(key,0.0)+effective_notional(t)
        entity_sf[key]=supervisory_factor(t)
        entity_rho[key]=supervisory_correlation(t)
    systematic=0.0
    idiosyncratic=0.0
    for key,eff in entity_eff.items():
        addon_k=entity_sf[key]*eff
        rho=entity_rho[key]
        systematic+=rho*addon_k
        idiosyncratic+=(1-rho*rho)*addon_k*addon_k
    return math.sqrt(systematic*systematic+idiosyncratic)
