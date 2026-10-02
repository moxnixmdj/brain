"""Fail-closed verifier for the predeclared composite P1 proof role split."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_P1_COMPOSITE_PROOF_ROLE_RECONCILIATION_VERDICT_V1"
BEHAVIOR="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
V4_CHECKS={
 "FAILURE_MECHANISM_CLASSIFICATION_SUPPORTED_BY_VISIBLE_RECEIPTS",
 "NONIDENTIFIABLE_OR_CAUSALLY_EQUIVALENT_CASE_DOES_NOT_FORCE_UNIQUE_CAUSE",
 "AUTHORITY_SCOPE_TOOL_STATE_PROVENANCE_AND_DEPENDENCY_FAILURE_CLASSES_ARE_LOAD_BEARING_WHEN_PRESENT",
 "MULTISTEP_OR_DELAYED_CAUSAL_INTERACTIONS_ARE_NOT_REDUCED_TO_FIRST_VISIBLE_SYMPTOM"}
TERM_CHECKS={
 "EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_LOCALIZATION_MATCHES_HIDDEN_INTERVENTION_ORACLE",
 "NOMINATED_REPAIR_IS_FALSIFIABLE",
 "NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME_WHEN_CAUSE_IS_IDENTIFIABLE",
 "SYMPTOM_ONLY_OR_COMPETING_REPAIR_DOES_NOT_RECEIVE_CAUSAL_CREDIT"}
V4_MUT={
 "IGNORE_VIOLATED_AUTHORITY_OR_INVARIANT","FORCE_UNIQUE_CAUSE_ON_NONIDENTIFIABLE_TRACE",
 "DROP_CAUSAL_PREDECESSOR_IN_MULTI_STEP_CHAIN","SWAP_TOOL_OR_AUTHORITY_FAILURE_CLASS",
 "DROP_PROVENANCE_OR_DEPENDENCY_EDGE","UNFALSIFIABLE_DIAGNOSIS"}
TERM_MUT={"SELECT_DOWNSTREAM_SYMPTOM","SELECT_LATER_CORRELATED_STEP","REPAIR_TARGET_WITH_NO_RESCUE"}

def load(rel:str): return json.loads((ROOT/rel).read_text())

def _receipt(wave:Mapping[str,Any], tier:str):
 rows=wave.get("reduction_input",{}).get("wave",{}).get("parent_portfolio_receipts",{}).get(tier,[])
 hits=[x for x in rows if isinstance(x,Mapping) and x.get("behavior_id")==BEHAVIOR]
 return hits[0] if len(hits)==1 else None

def evaluate(binding:Mapping[str,Any], v4:Mapping[str,Any], wave:Mapping[str,Any],
             audit:Mapping[str,Any], candidate:Mapping[str,Any])->dict[str,Any]:
 e=[]
 ev=binding.get("evaluator",{})
 role=ev.get("typed_cross_domain_scope_role")
 if role!="CROSS_DOMAIN_MECHANISM_CAUSAL_PATTERN_INFORMATION_SAFE_PREFLIGHT__TERMINAL_RESCUE_JUDGMENT_REMAINS_INSIDE_FROZEN_T0_T2_OBSERVATIONS":
  e.append("COMPOSITE_ROLE_NOT_PREDECLARED")
 if ev.get("typed_cross_domain_independent_preflight")!="canonical/verification/TRAJECTORY_TYPED_IR_V4_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":
  e.append("V4_PREFLIGHT_NOT_BOUND")
 checks=set(ev.get("required_checks",[])); muts=set(ev.get("required_mutations",[]))
 pr=candidate.get("proof_roles",{}); mr=candidate.get("mutation_roles",{})
 vc=set(pr.get("V4_TYPED_CROSS_DOMAIN_PREFLIGHT",[])); tc=set(pr.get("T0_T2_TERMINAL_INTERVENTION_RESCUE",[]))
 vm=set(mr.get("V4_TYPED_CROSS_DOMAIN_PREFLIGHT",[])); tm=set(mr.get("T0_T2_TERMINAL_INTERVENTION_RESCUE",[]))
 if vc!=V4_CHECKS or tc!=TERM_CHECKS or vc&tc or vc|tc!=checks: e.append("CHECK_PARTITION_INVALID")
 if vm!=V4_MUT or tm!=TERM_MUT or vm&tm or vm|tm!=muts: e.append("MUTATION_PARTITION_INVALID")
 if v4.get("status")!="INDEPENDENT_PASS__EXACT_IMPORTED_PUBLIC_RUNNER_BYTES__168_TYPED_CROSS_DOMAIN_CASE_MATRIX__ZERO_TERMINAL_RESULTS__ZERO_CAPABILITY_CREDIT":
  e.append("V4_INDEPENDENT_PREFLIGHT_NOT_PASS")
 vv=v4.get("verified",{})
 if vv.get("cross_product_case_count")!=168 or vv.get("hidden_oracle_not_candidate_visible") is not True:
  e.append("V4_SCOPE_OR_INFORMATION_GATE_DRIFT")
 if set(vv.get("normalized_domains",[]))!={"BROWSER","FILESYSTEM","TOOL_API","ARTIFACT","RESEARCH","CODE"}:
  e.append("V4_DOMAIN_SCOPE_DRIFT")
 if audit.get("audit_valid") is not True or audit.get("scope_mismatch_proved") is not True:
  e.append("NARROW_TERMINAL_AUDIT_NOT_PRESERVED")
 total=0
 for tier in ("T0","T2"):
  r=_receipt(wave,tier)
  if r is None: e.append("TERMINAL_RECEIPT_MISSING:"+tier); continue
  if any(r.get(k) is not True for k in ("load_bearing","direct_instrumentation_pass","parent_terminal_acceptance_pass")):
   e.append("TERMINAL_RECEIPT_NOT_PASS:"+tier)
  if any(r.get(k) is not False for k in ("case_replaced","tuning_replay","result_to_runtime_feedback")):
   e.append("TERMINAL_RECEIPT_CONTAMINATED:"+tier)
  try: total+=int(str(r.get("case_id")).rsplit("::",1)[-1])
  except Exception: e.append("TERMINAL_CASE_COUNT_INVALID:"+tier)
 if total!=60: e.append("TERMINAL_CASE_COUNT_NOT_60")
 return {"schema":SCHEMA,
  "status":"PASS__PREDECLARED_COMPOSITE_P1_ROLE_PARTITION_COVERS_ALL_FROZEN_CHECKS_AND_MUTATIONS__ZERO_CREDIT" if not e else "FAIL_CLOSED",
  "pass":not e,"errors":sorted(set(e)),"required_check_count":len(checks),"required_mutation_count":len(muts),
  "v4_check_count":len(vc),"terminal_check_count":len(tc),"terminal_case_count":total,
  "narrow_terminal_scope_audit_preserved":audit.get("scope_mismatch_proved") is True,
  "whole_p1_restoration_candidate":not e,"quarantine_resolved":False,
  "recovery_acceptance_transport_authorized":False,"new_reality_units_consumed":0,
  "capability_credit_delta":0,"family_credit_delta":0,"execution_authority":False,"promotion_authority":False}

def main():
 out=evaluate(
  load("canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"),
  load("canonical/verification/TRAJECTORY_TYPED_IR_V4_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
  load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"),
  __import__("canonical.runtime.p1_terminal_execution_scope_audit_v1",fromlist=["evaluate"]).evaluate(),
  load("canonical/governance/P1_COMPOSITE_PROOF_ROLE_RECONCILIATION_V1.json"))
 print(json.dumps(out,indent=2,sort_keys=True)); return 0 if out["pass"] else 1
if __name__=="__main__": raise SystemExit(main())
