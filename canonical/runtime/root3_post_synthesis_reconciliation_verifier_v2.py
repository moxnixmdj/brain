#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
CUT="canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V2.json"
BIND="canonical/governance/ROOT3_MATCHED_SUPERPORTFOLIO_MINIMUM_REALITY_BINDING_V2.json"
ROOTSTATE="canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"
RESIDUAL="canonical/governance/ROOT3_RESIDUAL_COMPRESSION_V1.json"

def blob(p:str)->str:
    b=(ROOT/p).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(p:str)->dict[str,Any]:
    x=json.loads((ROOT/p).read_text())
    assert isinstance(x,dict)
    return x

def evaluate()->dict[str,Any]:
    e=[]
    cut=load(CUT); bind=load(BIND); root=load(ROOTSTATE); res=load(RESIDUAL)
    part=root.get("current_residual_root_partition") or root.get("partition") or root.get("residual_partition") or {}
    r3=set(part.get("root3_only") or []) | set(part.get("root2_and_root3") or [])
    if (part.get("unknown_domain_root_transition") or {}).get("state")=="CLOSED__PROVED":
        r3.add("UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT")
    if len(r3)!=10: e.append("LIVE_ROOT3_COUNT_NOT_10")
    if "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR" in r3: e.append("SYNTHESIS_STILL_ROOT3")
    if cut.get("derivation",{}).get("live_root3_predicates")!=10: e.append("CUT_COUNT_DRIFT")
    if len(cut.get("minimum_event_classes") or [])!=3: e.append("EVENT_CLASS_COUNT_DRIFT")
    ids={x.get("predicate_id") for x in bind.get("matched_scope_targets") or [] if isinstance(x,dict)}
    if len(ids)!=7: e.append("SUPERPORTFOLIO_ROOT3_COUNT_NOT_7")
    if "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR" in ids: e.append("SYNTHESIS_STALE_IN_ROOT3_BINDING")
    if bind.get("execution_compression",{}).get("shared_future_superportfolio_wave_count")!=1: e.append("SUPERPORTFOLIO_WAVE_DRIFT")
    removed=bind.get("removed_from_root3") or []
    if not any(x.get("predicate_id")=="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR" for x in removed if isinstance(x,dict)):
        e.append("SYNTHESIS_REMOVAL_NOT_EXPLICIT")
    syn=[x for x in res.get("compressed_residuals") or [] if isinstance(x,dict) and x.get("predicate_id")=="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"]
    if len(syn)!=1 or syn[0].get("root_class")!="ROOT2" or syn[0].get("scope_relation_closed") is not True:
        e.append("SYNTHESIS_RESIDUAL_NOT_ROOT2_ONLY")
    for d in (cut,bind):
        if d.get("fresh_reality_authority") is not False: e.append("FRESH_REALITY_OVERCLAIM")
        if d.get("acceptance_credit_delta")!=0: e.append("ACCEPTANCE_CREDIT_OVERCLAIM")
    ok=not e
    return {
      "schema":"PROJECT_BRAIN_ROOT3_POST_SYNTHESIS_RECONCILIATION_VERIFIER_V2",
      "status":"PASS__10_ROOT3_PREDICATES__7_MATCHED_SCOPE_TARGETS__3_EVENT_CLASSES__ZERO_CREDIT" if ok else "FAIL_CLOSED",
      "pass":ok,
      "errors":sorted(set(e)),
      "live_root3_predicate_count":len(r3),
      "matched_scope_target_count":len(ids),
      "minimum_event_class_count":len(cut.get("minimum_event_classes") or []),
      "synthesis_root3":False if ok else None,
      "acceptance_credit_delta":0,
      "fresh_reality_authority":False,
    }

if __name__=="__main__":
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
