"""Mechanize finite adaptive-cover induction. Structural only; no terminal authority."""
from __future__ import annotations
from typing import Any, Mapping, Sequence
import math

SCHEMA="PROJECT_BRAIN_ADAPTIVE_COVER_INDUCTION_GATE_V1"

def _hex40(x): return isinstance(x,str) and len(x)==40 and all(c in "0123456789abcdef" for c in x)
def _receipt(r,*claims):
    return isinstance(r,Mapping) and isinstance(r.get("path"),str) and bool(r["path"].strip()) and _hex40(r.get("git_blob_sha")) and r.get("independent_verified") is True and r.get("exact_byte_bound") is True and r.get("conclusion")=="success" and all(r.get(c) is True for c in claims)
def _cost(x):
    if isinstance(x,bool) or not isinstance(x,(int,float)): return None
    x=float(x)
    return x if math.isfinite(x) and x>=0 else None
def _fail(reason,**detail):
    out={"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
         "alpha_gamma_totality_bound":False,"total_terminal_or_progress_cover_bound":False,
         "global_well_founded_rank_bound":False,"global_resource_potential_bound":False,
         "adaptive_cover_structurally_closed":False,"u_empty_authorized":False,
         "abc_closed_authorized":False,"terminal_authority":False,"terminal_credit_delta":0}
    if detail: out["detail"]=detail
    return out

def evaluate(p:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(p,Mapping): return _fail("PAYLOAD_MAPPING_REQUIRED")
    initial=str(p.get("initial_state_id") or "").strip()
    if not initial: return _fail("INITIAL_STATE_REQUIRED")
    top=p.get("top_initialization")
    if not isinstance(top,Mapping): return _fail("TOP_INITIALIZATION_REQUIRED")
    if top.get("alpha_total_on_scope") is not True: return _fail("ALPHA_TOTALITY_UNPROVED")
    if top.get("true_context_preserved_in_gamma_top") is not True: return _fail("GAMMA_TOP_SOUNDNESS_UNPROVED")
    if not _receipt(top.get("receipt"),"alpha_total_on_scope","true_context_preserved_in_gamma_top"):
        return _fail("TOP_INITIALIZATION_RECEIPT_INVALID")

    rows=p.get("states")
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)) or not rows: return _fail("STATES_REQUIRED")
    states={}
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping): return _fail("STATE_NOT_MAPPING",index=i)
        sid=str(row.get("state_id") or "").strip()
        if not sid or sid in states: return _fail("STATE_ID_INVALID_OR_DUPLICATE",index=i,state_id=sid)
        states[sid]=row
    if initial not in states: return _fail("INITIAL_STATE_UNDECLARED",state_id=initial)

    edges={}; terminal_cost={}; terminal_policy={}
    for sid,row in states.items():
        if row.get("terminal") is True:
            pid=str(row.get("terminal_policy_id") or "").strip()
            c=_cost(row.get("terminal_cost_units"))
            if not pid: return _fail("TERMINAL_POLICY_REQUIRED",state_id=sid)
            if c is None: return _fail("TERMINAL_COST_INVALID",state_id=sid)
            if not _receipt(row.get("terminal_adequacy_receipt"),"policy_adequate_on_entire_concretization"):
                return _fail("TERMINAL_ADEQUACY_UNPROVED",state_id=sid)
            if not _receipt(row.get("terminal_safety_receipt"),"policy_safe_on_entire_concretization"):
                return _fail("TERMINAL_SAFETY_UNPROVED",state_id=sid)
            edges[sid]=[]; terminal_cost[sid]=c; terminal_policy[sid]=pid; continue

        if not str(row.get("refinement_policy_id") or "").strip(): return _fail("REFINEMENT_POLICY_REQUIRED",state_id=sid)
        if not _receipt(row.get("refinement_soundness_receipt"),"true_context_preserved_in_every_actual_successor"):
            return _fail("REFINEMENT_SOUNDNESS_UNPROVED",state_id=sid)
        if not _receipt(row.get("refinement_safety_receipt"),"refinement_safe_on_entire_concretization"):
            return _fail("REFINEMENT_SAFETY_UNPROVED",state_id=sid)
        if not _receipt(row.get("outcome_completeness_receipt"),"outcome_model_complete"):
            return _fail("OUTCOME_COMPLETENESS_UNPROVED",state_id=sid)
        outs=row.get("outcomes")
        if not isinstance(outs,Sequence) or isinstance(outs,(str,bytes)) or not outs: return _fail("OUTCOMES_REQUIRED",state_id=sid)
        seen=set(); e=[]
        for j,o in enumerate(outs):
            if not isinstance(o,Mapping): return _fail("OUTCOME_NOT_MAPPING",state_id=sid,index=j)
            oid=str(o.get("outcome_id") or "").strip(); dst=str(o.get("successor_state_id") or "").strip(); c=_cost(o.get("cost_units"))
            if not oid or oid in seen: return _fail("OUTCOME_ID_INVALID_OR_DUPLICATE",state_id=sid,outcome_id=oid)
            if dst not in states: return _fail("OUTCOME_SUCCESSOR_UNDECLARED",state_id=sid,outcome_id=oid,successor_state_id=dst)
            if c is None: return _fail("OUTCOME_COST_INVALID",state_id=sid,outcome_id=oid)
            seen.add(oid); e.append((dst,c,oid))
        edges[sid]=e

    reached=set()
    def mark(s):
        if s in reached:return
        reached.add(s)
        for d,_,_ in edges[s]: mark(d)
    mark(initial)

    visiting=set(); done=set(); order=[]; path=[]
    def dfs(s):
        if s in visiting:
            k=path.index(s) if s in path else 0
            return path[k:]+[s]
        if s in done:return None
        visiting.add(s);path.append(s)
        for d,_,_ in edges[s]:
            w=dfs(d)
            if w:return w
        path.pop();visiting.remove(s);done.add(s);order.append(s)
        return None
    cycle=dfs(initial)
    if cycle:return _fail("WELL_FOUNDED_RANK_IMPOSSIBLE_CYCLE",cycle=cycle)

    rank={}; budget={}
    for s in order:
        if not edges[s]:
            if s not in terminal_cost:return _fail("REACHED_DEAD_END_NONTERMINAL",state_id=s)
            rank[s]=0;budget[s]=terminal_cost[s]
        else:
            rank[s]=1+max(rank[d] for d,_,_ in edges[s])
            budget[s]=max(c+budget[d] for d,c,_ in edges[s])

    return {"schema":SCHEMA,"pass":True,"status":"PASS__FINITE_AUTHENTICATED_ADAPTIVE_COVER_INDUCTION_MECHANIZED",
            "initial_state_id":initial,"reached_state_count":len(reached),"declared_state_count":len(states),
            "unreachable_declared_state_ids":sorted(set(states)-reached),
            "derived_rank":{s:rank[s] for s in sorted(reached)},
            "derived_resource_potential_units":{s:budget[s] for s in sorted(reached)},
            "initial_worst_case_resource_bound_units":budget[initial],
            "terminal_policy_ids":{s:terminal_policy[s] for s in sorted(terminal_policy) if s in reached},
            "alpha_gamma_totality_bound":True,"total_terminal_or_progress_cover_bound":True,
            "global_well_founded_rank_bound":True,"global_resource_potential_bound":True,
            "adaptive_cover_structurally_closed":True,"u_empty_authorized":False,
            "abc_closed_authorized":False,"terminal_authority":False,"terminal_credit_delta":0,
            "boundary":"EXACT_FINITE_REACHED_MANIFEST_ONLY__A_SEPARATE_SCOPE_COMPLETE_PARAMETERIZED_BINDING_MUST_COVER_EVERY_REACHED_ABSTRACT_STATE_IN_S_TRACE_BEFORE_U_EMPTY"}
