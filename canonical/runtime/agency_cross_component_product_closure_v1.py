from __future__ import annotations
from collections import defaultdict

SCHEMA="BRAIN_AGENCY_CROSS_COMPONENT_PRODUCT_CLOSURE_V1"
DIMS={
 "multi-step planning with at least three distinct tool/action types",
 "state change after actions requiring replanning",
 "long-horizon state retention",
 "tool failure/recovery",
 "subtask dependency and fan-in",
 "minimal-oversight completion",
}
METRICS={"terminal_task_success","invalid_action_rate","unrecovered_failure_rate","duplicate_or_conflicting_work_rate"}

def _set(v,name):
 if not isinstance(v,list): raise ValueError(name+"_NOT_LIST")
 out=set()
 for x in v:
  if not isinstance(x,str) or not x: raise ValueError(name+"_INVALID_ITEM")
  if x in out: raise ValueError(name+"_DUPLICATE:"+x)
  out.add(x)
 return out

def verify_product(spec):
 errors=[]
 try:
  if _set(spec.get("covered_dimensions",[]),"DIMENSIONS")!=DIMS: errors.append("DIMENSION_COVERAGE_MISMATCH")
  if _set(spec.get("covered_metrics",[]),"METRICS")!=METRICS: errors.append("METRIC_COVERAGE_MISMATCH")
  ident=spec.get("identity") or {}
  identity=tuple(str(ident.get(k) or "") for k in ("agent_id","task_id","mission_id"))
  if any(not x for x in identity): errors.append("IDENTITY_INCOMPLETE")
  facts=_set(spec.get("initial_facts",[]),"INITIAL_FACTS")
  target=_set(spec.get("target_facts",[]),"TARGET_FACTS")
  caps=spec.get("resource_capacities") or {}
  if spec.get("recovery_scope_complete_for_declared_failures") is not True: errors.append("RECOVERY_SCOPE_NOT_COMPLETE")
  if spec.get("fail_closed_before_next_material_action") is not True: errors.append("FAIL_CLOSED_GATE_MISSING")
  if spec.get("current_receipt_replan_required") is not True: errors.append("CURRENT_RECEIPT_REPLAN_GATE_MISSING")
  stages=spec.get("stages")
  if not isinstance(stages,list) or not stages: raise ValueError("STAGES_REQUIRED")
  evidence_owner={}; current_version=0; ids=set(); action_types=set(); wave_writes=defaultdict(lambda:defaultdict(int)); seen_failure=False
  for row in stages:
   sid=str(row.get("id") or "")
   if not sid or sid in ids: errors.append("STAGE_ID_INVALID_OR_DUPLICATE:"+sid); continue
   ids.add(sid)
   action_type=str(row.get("action_type") or "")
   if action_type: action_types.add(action_type)
   else: errors.append("ACTION_TYPE_MISSING:"+sid)
   req=_set(row.get("requires",[]),"REQUIRES_"+sid)
   provides=_set(row.get("provides",[]),"PROVIDES_"+sid)
   writes=_set(row.get("writes",[]),"WRITES_"+sid)
   evidence=_set(row.get("evidence",[]),"EVIDENCE_"+sid)
   if row.get("reads_state_version")!=current_version: errors.append("STALE_STATE_READ:"+sid)
   if not req.issubset(facts): errors.append("MISSING_REQUIRED_FACT:"+sid)
   checkpoint=row.get("checkpoint")
   if checkpoint is not None:
    got=tuple(str(checkpoint.get(k) or "") for k in ("agent_id","task_id","mission_id"))
    if got!=identity: errors.append("CHECKPOINT_IDENTITY_DRIFT:"+sid)
    if checkpoint.get("revalidated_current_context") is not True: errors.append("CHECKPOINT_CONTEXT_NOT_REVALIDATED:"+sid)
   wave=row.get("wave",0)
   if not isinstance(wave,int) or wave<0: errors.append("WAVE_INVALID:"+sid); wave=0
   for res in writes: wave_writes[wave][res]+=1
   outcome=row.get("outcome")
   if outcome=="FAIL":
    seen_failure=True
    rec=row.get("recovery")
    if not isinstance(rec,dict): errors.append("FAILED_STAGE_WITHOUT_RECOVERY:"+sid); continue
    if rec.get("status")!="RESTORED": errors.append("RECOVERY_NOT_RESTORED:"+sid)
    if rec.get("invariants_restored") is not True: errors.append("RECOVERY_INVARIANTS_NOT_RESTORED:"+sid)
    rv=rec.get("state_version")
    if not isinstance(rv,int) or rv<=current_version: errors.append("RECOVERY_STATE_VERSION_NOT_ADVANCED:"+sid)
    else: current_version=rv
    if rec.get("replanned_from_current_receipt") is not True: errors.append("RECOVERY_NOT_REPLANNED_FROM_CURRENT_RECEIPT:"+sid)
    continue
   if outcome!="PASS": errors.append("OUTCOME_INVALID:"+sid); continue
   nv=row.get("emits_state_version")
   if not isinstance(nv,int) or nv<current_version: errors.append("STATE_VERSION_INVALID:"+sid)
   else: current_version=nv
   facts.update(provides)
   for ev in evidence:
    if ev in evidence_owner and evidence_owner[ev]!=sid: errors.append("EVIDENCE_OWNER_CONFLICT:"+ev)
    else: evidence_owner[ev]=sid
  for wave,usage in wave_writes.items():
   for res,count in usage.items():
    cap=caps.get(res,1)
    if not isinstance(cap,int) or cap<1: errors.append("RESOURCE_CAPACITY_INVALID:"+res)
    elif count>cap: errors.append(f"RESOURCE_WRITE_CONFLICT:{wave}:{res}")
  if len(action_types)<3: errors.append("LESS_THAN_THREE_DISTINCT_ACTION_TYPES")
  if not target.issubset(facts): errors.append("TARGET_FACTS_NOT_REACHED")
  required_ev=_set(spec.get("required_terminal_evidence",[]),"REQUIRED_TERMINAL_EVIDENCE")
  if not required_ev.issubset(set(evidence_owner)): errors.append("TERMINAL_FANIN_EVIDENCE_MISSING")
  ok=not errors
  return {"schema":SCHEMA,"pass":ok,"status":"PASS__FINITE_EXPLICIT_AGENCY_PRODUCT_INTERACTION_CLOSURE" if ok else "FAIL_CLOSED","errors":errors,"interaction_invariant_preserved":ok,"terminal_task_success":ok,"invalid_action_rate_zero_by_admission":ok,"unrecovered_failure_rate_zero_by_recovery_gate":ok,"duplicate_or_conflicting_work_rate_zero_by_ownership_and_capacity_gate":ok,"failure_recovery_exercised":seen_failure,"terminal_credit_delta":0}
 except Exception as exc:
  return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":[type(exc).__name__+":"+str(exc)],"terminal_credit_delta":0}
