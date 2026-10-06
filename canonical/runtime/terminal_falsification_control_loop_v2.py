from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, Mapping, Sequence

LANE_ORDER={"UNIVERSE_AUTHORITY":0,"EFFECT_CLOSURE":1,"CONDITION_TRANSFER":2,"PERFORMANCE_WITNESS":3,"OWNERSHIP":4}
LIVE_STATUSES={"ACTIVE","SURVIVED_NONEXHAUSTIVE","SURVIVED_EXHAUSTIVE","PROVED"}

@dataclass(frozen=True)
class ClaimVerdict:
    claim_id:str
    lane:str
    effective_status:str
    proof_credit:int
    blocked_by:Sequence[str]
    reason:str

@dataclass(frozen=True)
class ControlLoopResult:
    terminal_ready:bool
    universe_complete:bool
    proof_credit_delta:int
    ordered_claim_ids:Sequence[str]
    dead_claim_ids:Sequence[str]
    unrepaired_dead_claim_ids:Sequence[str]
    blocked_claim_ids:Sequence[str]
    verdicts:Sequence[Dict[str,Any]]

def _sha1(v:Any)->bool:
    return isinstance(v,str) and len(v)==40 and all(c in "0123456789abcdef" for c in v)

def _binding(v:Any)->bool:
    return isinstance(v,Mapping) and isinstance(v.get("path"),str) and bool(v["path"].strip()) and _sha1(v.get("git_blob_sha"))

def _proof_credit(c:Mapping[str,Any])->int:
    if c.get("status")!="PROVED": return 0
    r=c.get("proof_receipts")
    return int(isinstance(r,list) and bool(r) and all(_binding(x) for x in r))

def _validate(c:Mapping[str,Any])->None:
    for k in ("id","lane","status","cost_units","target_truth_obligations"):
        if k not in c: raise ValueError("missing claim field: "+k)
    if c["lane"] not in LANE_ORDER: raise ValueError("unknown lane")
    if c["status"] not in LIVE_STATUSES|{"FALSIFIED","BLOCKED"}: raise ValueError("unknown status")
    if not isinstance(c["cost_units"],int) or c["cost_units"]<=0: raise ValueError("bad cost")
    if not isinstance(c["target_truth_obligations"],list): raise ValueError("bad targets")
    n=c.get("target_truth_obligation_count",len(set(c["target_truth_obligations"])))
    if not isinstance(n,int) or n<len(set(c["target_truth_obligations"])) or n<=0: raise ValueError("bad target count")

def _successors(claims):
    out={}
    for c in claims:
        p=c.get("successor_of")
        if p: out.setdefault(p,[]).append(c)
    return out

def _live_successor(pid,smap):
    return any(c.get("status") in LIVE_STATUSES for c in smap.get(pid,()))

def _dependency_blockers(c,by_id):
    return [d for d in c.get("depends_on",[]) if d not in by_id or _proof_credit(by_id[d])!=1]

def _priority(c):
    n=c.get("target_truth_obligation_count",len(set(c.get("target_truth_obligations",[]))))
    return (0 if c["lane"]=="UNIVERSE_AUTHORITY" else 1,-n/c["cost_units"],LANE_ORDER[c["lane"]],c["cost_units"],c["id"])

def compile_control_loop(state:Mapping[str,Any])->ControlLoopResult:
    claims=list(state.get("claims",[]))
    if not claims: raise ValueError("claims must be non-empty")
    for c in claims: _validate(c)
    by_id={c["id"]:c for c in claims}
    if len(by_id)!=len(claims): raise ValueError("duplicate ids")
    smap=_successors(claims)
    universe=[c["id"] for c in claims if c["lane"]=="UNIVERSE_AUTHORITY"]
    if not universe: raise ValueError("universe claim required")

    verdicts=[]; sched=[]; dead=[]; unrepaired=[]; blocked=[]
    for c in claims:
        cid=c["id"]
        if c["status"]=="FALSIFIED":
            dead.append(cid); repaired=_live_successor(cid,smap)
            if not repaired: unrepaired.append(cid)
            verdicts.append(ClaimVerdict(cid,c["lane"],"DEAD_REPAIRED_BY_SUCCESSOR" if repaired else "DEAD_UNREPAIRED",0,(),"FALSIFIED_ROUTE_REPAIRED" if repaired else "FALSIFIED_ROUTE_UNREPAIRED"))
            continue
        deps=_dependency_blockers(c,by_id)
        if deps:
            blocked.append(cid)
            verdicts.append(ClaimVerdict(cid,c["lane"],"BLOCKED",0,tuple(deps),"DEPENDENCY_NOT_PROVED_WITH_CONTENT_ADDRESSED_RECEIPTS"))
            continue
        credit=_proof_credit(c)
        reason="LIVE_CLAIM"
        if c["status"] in {"SURVIVED_NONEXHAUSTIVE","SURVIVED_EXHAUSTIVE"}: reason="SURVIVAL_IS_ZERO_PROOF_CREDIT"
        if c["status"]=="PROVED" and not credit: reason="PROVED_LABEL_WITHOUT_VALID_RECEIPTS_IS_ZERO_CREDIT"
        verdicts.append(ClaimVerdict(cid,c["lane"],c["status"],credit,(),reason))
        if c["status"]!="PROVED": sched.append(c)

    sched.sort(key=_priority)
    universe_complete=any(_proof_credit(by_id[x])==1 for x in universe)
    known=state.get("known_open_truth_obligations")
    if not isinstance(known,int) or known<0: raise ValueError("bad known open count")
    unresolved=any(v.lane!="UNIVERSE_AUTHORITY" and v.effective_status not in {"PROVED","DEAD_REPAIRED_BY_SUCCESSOR"} for v in verdicts)
    terminal=universe_complete and known==0 and not unresolved and not blocked and not unrepaired
    return ControlLoopResult(terminal,universe_complete,0,tuple(c["id"] for c in sched),tuple(dead),tuple(unrepaired),tuple(blocked),tuple(asdict(v) for v in verdicts))
