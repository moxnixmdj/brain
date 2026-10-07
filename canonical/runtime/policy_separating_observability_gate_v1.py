"""Policy-separating observability gate.

This gate mechanizes the remaining sufficient condition behind escape-progress
totality. A nonterminal finite policy-region state progresses when at least one
authenticated discriminator has:
  * a complete finite outcome alphabet,
  * a sound outcome-to-successor mapping,
  * every reachable outcome preserving the true region,
  * every reachable outcome mapping to a strict nonempty subset of the source
    policy-region set,
  * independent safety/truth/resource receipts.

The gate does not prove that every possible context is represented by the
manifest. It certifies only the declared states and returns exact uncovered
states when no authenticated separator exists.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence
import math

SCHEMA="PROJECT_BRAIN_POLICY_SEPARATING_OBSERVABILITY_GATE_V1"

def _hex40(x:Any)->bool:
    return isinstance(x,str) and len(x)==40 and all(c in "0123456789abcdef" for c in x)

def _receipt(r:Any,*claims:str)->bool:
    return (
        isinstance(r,Mapping)
        and isinstance(r.get("path"),str) and bool(r["path"].strip())
        and _hex40(r.get("git_blob_sha"))
        and r.get("independent_verified") is True
        and r.get("exact_byte_bound") is True
        and r.get("conclusion")=="success"
        and all(r.get(c) is True for c in claims)
    )

def _cost(v:Any):
    if isinstance(v,bool) or not isinstance(v,(int,float)):
        return None
    x=float(v)
    return x if math.isfinite(x) and x>=0 else None

def _fail(reason:str,**detail:Any)->dict[str,Any]:
    out={
        "schema":SCHEMA,
        "pass":False,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "declared_state_progress_totality":False,
        "uncovered_state_ids":[],
        "terminal_authority":False,
        "u_empty_authorized":False,
        "terminal_credit_delta":0,
    }
    if detail:
        out["detail"]=detail
    return out

def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")

    states=payload.get("states")
    if not isinstance(states,Sequence) or isinstance(states,(str,bytes)) or not states:
        return _fail("STATES_REQUIRED")

    state_map={}
    for i,row in enumerate(states):
        if not isinstance(row,Mapping):
            return _fail("STATE_NOT_MAPPING",index=i)
        sid=str(row.get("state_id") or "").strip()
        if not sid or sid in state_map:
            return _fail("STATE_ID_INVALID_OR_DUPLICATE",index=i,state_id=sid)
        regions=row.get("policy_region_ids")
        if not isinstance(regions,Sequence) or isinstance(regions,(str,bytes)) or not regions:
            return _fail("POLICY_REGIONS_REQUIRED",state_id=sid)
        rids=[str(x).strip() for x in regions]
        if any(not x for x in rids) or len(rids)!=len(set(rids)):
            return _fail("POLICY_REGION_ID_INVALID_OR_DUPLICATE",state_id=sid)
        state_map[sid]={**row,"_regions":frozenset(rids)}

    uncovered=[]
    selected={}
    terminal_states=[]

    for sid,row in state_map.items():
        regions=row["_regions"]

        terminal=row.get("terminal")
        if terminal is True:
            if not str(row.get("terminal_policy_id") or "").strip():
                return _fail("TERMINAL_POLICY_REQUIRED",state_id=sid)
            if not _receipt(row.get("terminal_adequacy_receipt"),"policy_adequate_on_entire_region_set"):
                return _fail("TERMINAL_ADEQUACY_UNPROVED",state_id=sid)
            if not _receipt(row.get("terminal_safety_receipt"),"policy_safe_on_entire_region_set"):
                return _fail("TERMINAL_SAFETY_UNPROVED",state_id=sid)
            terminal_states.append(sid)
            continue
        if terminal is not False:
            return _fail("TERMINAL_FLAG_MUST_BE_LITERAL_BOOL",state_id=sid)

        discs=row.get("discriminators")
        if not isinstance(discs,Sequence) or isinstance(discs,(str,bytes)):
            return _fail("DISCRIMINATORS_INVALID",state_id=sid)

        valid=[]
        for j,d in enumerate(discs):
            if not isinstance(d,Mapping):
                return _fail("DISCRIMINATOR_NOT_MAPPING",state_id=sid,index=j)
            did=str(d.get("discriminator_id") or "").strip()
            if not did:
                return _fail("DISCRIMINATOR_ID_REQUIRED",state_id=sid,index=j)
            if _cost(d.get("resource_cost_units")) is None:
                return _fail("DISCRIMINATOR_RESOURCE_COST_INVALID",state_id=sid,discriminator_id=did)
            if not _receipt(d.get("truth_soundness_receipt"),"truthful_selected_discriminator"):
                continue
            if not _receipt(d.get("safety_receipt"),"safe_on_entire_source_region_set"):
                continue
            if not _receipt(d.get("outcome_completeness_receipt"),"finite_outcome_alphabet_complete"):
                continue

            outcomes=d.get("outcomes")
            if not isinstance(outcomes,Sequence) or isinstance(outcomes,(str,bytes)) or len(outcomes)<2:
                continue
            seen=set()
            proper=True
            normalized=[]
            for o in outcomes:
                if not isinstance(o,Mapping):
                    proper=False; break
                oid=str(o.get("outcome_id") or "").strip()
                if not oid or oid in seen:
                    proper=False; break
                seen.add(oid)
                succ=o.get("successor_policy_region_ids")
                if not isinstance(succ,Sequence) or isinstance(succ,(str,bytes)) or not succ:
                    proper=False; break
                ss=frozenset(str(x).strip() for x in succ)
                if any(not x for x in ss):
                    proper=False; break
                if not ss < regions:
                    proper=False; break
                if o.get("true_region_preserved") is not True:
                    proper=False; break
                normalized.append({"outcome_id":oid,"successor_policy_region_ids":sorted(ss)})
            if proper:
                valid.append({
                    "discriminator_id":did,
                    "resource_cost_units":float(d["resource_cost_units"]),
                    "outcomes":normalized,
                })

        if not valid:
            uncovered.append(sid)
            continue
        valid.sort(key=lambda x:(x["resource_cost_units"],x["discriminator_id"]))
        selected[sid]=valid[0]

    if uncovered:
        return {
            "schema":SCHEMA,
            "pass":False,
            "status":"UNRESOLVED__DECLARED_PROGRESS_TOTALITY_HAS_OBSERVABILITY_GAPS",
            "declared_state_count":len(state_map),
            "terminal_state_ids":sorted(terminal_states),
            "selected_discriminators":selected,
            "uncovered_state_ids":sorted(uncovered),
            "declared_state_progress_totality":False,
            "terminal_authority":False,
            "u_empty_authorized":False,
            "terminal_credit_delta":0,
            "boundary":"EACH_UNCOVERED_STATE_NEEDS_EITHER_ONE_AUTHENTICATED_COMMON_ADEQUATE_POLICY_OR_ONE_AUTHENTICATED_SAFE_TRUTHFUL_COMPLETE_FINITE_STRICT_SEPARATOR",
        }

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__DECLARED_ESCAPE_PROGRESS_TOTALITY_BY_POLICY_SEPARATING_OBSERVABILITY",
        "declared_state_count":len(state_map),
        "terminal_state_ids":sorted(terminal_states),
        "selected_discriminators":selected,
        "uncovered_state_ids":[],
        "declared_state_progress_totality":True,
        "terminal_authority":False,
        "u_empty_authorized":False,
        "terminal_credit_delta":0,
        "boundary":"DECLARED_MANIFEST_ONLY__GLOBAL_U_CLOSURE_STILL_REQUIRES_A_SCOPE_COMPLETE_BINDING_FROM_S_TRACE_TO_THE_DECLARED_ABSTRACT_STATE_FAMILY",
    }
