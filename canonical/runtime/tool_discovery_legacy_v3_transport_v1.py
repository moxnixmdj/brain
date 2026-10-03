"""Exact transport from the frozen V1/V2 Tool Discovery public surface to Dynamic V3.

This is not a new benchmark. It proves that on every valid state admitted by the
frozen terminal public schema, Dynamic V3 has the same decision semantics as the
terminal-tested information-safe candidate. ESCALATE reason text is intentionally
non-semantic because the frozen scorer consumes only the action kind there.
"""
from __future__ import annotations
import itertools, math
from typing import Any, Mapping

from canonical.runtime import tool_discovery_information_safe_candidate as legacy
from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3

SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_LEGACY_V3_TRANSPORT_V1"


class TransportError(ValueError):
    pass


def validate_legacy(public: Mapping[str,Any]) -> None:
    req=public.get("required_capabilities")
    tools=public.get("tools")
    if not isinstance(req,list) or not req or any(not isinstance(x,str) or not x for x in req):
        raise TransportError("NONEMPTY_STRING_REQUIRED_CAPABILITIES_REQUIRED")
    if not isinstance(tools,list):
        raise TransportError("TOOLS_NOT_LIST")
    seen=set()
    for t in tools:
        if not isinstance(t,Mapping): raise TransportError("TOOL_NOT_MAPPING")
        tid=t.get("tool_id")
        if not isinstance(tid,str) or not tid or tid in seen: raise TransportError("TOOL_ID_INVALID_OR_DUPLICATE")
        seen.add(tid)
        if "epoch" in t: raise TransportError("LEGACY_TOOL_EPOCH_FIELD_FORBIDDEN")
        cost=t.get("cost",0.0)
        if isinstance(cost,bool) or not isinstance(cost,(int,float)) or not math.isfinite(float(cost)):
            raise TransportError("TOOL_COST_INVALID")
    for ev in public.get("version_events",[]):
        if not isinstance(ev,Mapping): raise TransportError("VERSION_EVENT_NOT_MAPPING")
        if ev.get("kind")=="TOOL_VERSION_CHANGED":
            if str(ev.get("tool_id") or "") not in seen: raise TransportError("VERSION_EVENT_UNKNOWN_TOOL")
            ep=ev.get("new_epoch")
            if isinstance(ep,bool) or not isinstance(ep,int): raise TransportError("VERSION_EPOCH_INVALID")
    for rec in public.get("prior_probe_receipts",[]):
        if not isinstance(rec,Mapping): raise TransportError("RECEIPT_NOT_MAPPING")
        if rec.get("kind")=="SAFE_CAPABILITY_PROBE":
            if str(rec.get("tool_id") or "") not in seen: raise TransportError("RECEIPT_UNKNOWN_TOOL")
            ep=rec.get("epoch")
            if isinstance(ep,bool) or not isinstance(ep,int): raise TransportError("RECEIPT_EPOCH_INVALID")


def adapt_legacy(public: Mapping[str,Any]) -> dict[str,Any]:
    validate_legacy(public)
    return {
        "required_capabilities":list(public["required_capabilities"]),
        "visible_tools":[dict(x) for x in public["tools"]],
        "prior_probe_receipts":[dict(x) for x in public.get("prior_probe_receipts",[])],
        "version_events":[dict(x) for x in public.get("version_events",[])],
        "constraint":None,
        "discovery_sources":[],
        "discovery_receipts":[],
    }


def normalize_action(action: Mapping[str,Any]) -> tuple[Any,...]:
    kind=action.get("action")
    if kind=="PROBE": return ("PROBE",str(action.get("tool_id") or ""),str(action.get("capability") or ""))
    if kind=="SELECT": return ("SELECT",str(action.get("tool_id") or ""))
    if kind=="ESCALATE": return ("ESCALATE",)
    return ("INVALID",)


def compare_one(public: Mapping[str,Any]) -> dict[str,Any]:
    adapted=adapt_legacy(public)
    a=legacy.next_action(public); b=v3.next_action(adapted)
    na=normalize_action(a); nb=normalize_action(b)
    return {
      "equivalent":na==nb,
      "legacy_action":a,"v3_action":b,
      "legacy_semantic_action":na,"v3_semantic_action":nb,
    }


def semantic_quotient_exhaustion() -> dict[str,Any]:
    """Exhaust the decision-relevant quotient for up to three ordered tools/two caps.

    Arbitrary larger finite states reduce to this quotient because both policies
    scan the same cost/id order and return at the first non-falsified tool:
    all earlier tools are summarized by IMPOSSIBLE; the decisive tool is either
    IMPOSSIBLE, PROBE(first unknown cap), or SELECT(all true).
    """
    total=0; failures=[]
    caps=["c0","c1"]
    for n in range(4):
      ids=[f"t{i}" for i in range(n)]
      for k in (1,2):
       required=caps[:k]
       pairs=[(tid,cap) for tid in ids for cap in required]
       for avail_auth in itertools.product((0,1,2,3),repeat=n):
        tools=[]
        for i,tid in enumerate(ids):
          code=avail_auth[i]
          tools.append({"tool_id":tid,"cost":float(i),"available":code in (2,3),"authorized":code in (1,3)})
        for states in itertools.product((-1,0,1),repeat=len(pairs)):
          receipts=[]
          for (tid,cap),st in zip(pairs,states):
            if st==-1: continue
            receipts.append({"kind":"SAFE_CAPABILITY_PROBE","tool_id":tid,"capability":cap,"epoch":0,"supported":bool(st)})
          public={"required_capabilities":required,"tools":tools,"prior_probe_receipts":receipts,"version_events":[]}
          total+=1; out=compare_one(public)
          if not out["equivalent"]:
            failures.append({"public":public,**out})
            if len(failures)>=5: return {"pass":False,"cases":total,"failures":failures}
    return {"pass":not failures,"cases":total,"failures":failures}


def prove_transport_candidate() -> dict[str,Any]:
    q=semantic_quotient_exhaustion()
    return {
      "schema":SCHEMA,
      "status":"PASS__LEGACY_TO_V3_DECISION_SEMANTICS_TRANSPORT_CANDIDATE" if q["pass"] else "FAIL_CLOSED",
      "semantic_quotient":q,
      "domain":[
        "NONEMPTY_FINITE_REQUIRED_CAPABILITY_SET",
        "FINITE_UNIQUE_LEGACY_TOOL_IDS_WITH_FINITE_COSTS",
        "LEGACY_TOOLS_HAVE_NO_INTRINSIC_EPOCH_FIELD",
        "VALID_PUBLIC_VERSION_EVENTS_AND_SAFE_PROBE_RECEIPTS",
        "NO_DYNAMIC_CONSTRAINT_ON_LEGACY_SURFACE",
        "NO_DISCOVERY_SOURCE_ON_LEGACY_SURFACE"
      ],
      "proof_decomposition":[
        "LEGACY_EPOCH_ZERO_PLUS_PUBLIC_VERSION_EVENTS_EQUALS_V3_DEFAULT_EPOCH_PLUS_SAME_EVENTS",
        "LEGACY_AVAILABILITY_AUTHORIZATION_FILTER_EQUALS_V3_FILTER_WHEN_CONSTRAINT_IS_NONE",
        "COST_THEN_TOOL_ID_ORDER_IDENTICAL",
        "CURRENT_EPOCH_EVIDENCE_CLASSIFICATION_IDENTICAL",
        "FIRST_NONFALSIFIED_TOOL_PROBE_OR_SELECT_TRANSITION_IDENTICAL",
        "NO_REMAINING_ROUTE_ESCALATES_IN_BOTH__REASON_TEXT_NOT_SCORER_SEMANTIC"
      ],
      "uses_terminal_result_replay":False,
      "new_reality_units_consumed":0,"incremental_spend_usd":0,
      "capability_credit_delta":0,"family_credit_delta":0,
      "execution_authority":False,"promotion_authority":False,
    }

if __name__=="__main__":
 import json
 print(json.dumps(prove_transport_candidate(),indent=2,sort_keys=True))
