"""Fail-closed verifier for the synthesis required-claim-coverage ceiling lift."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
CAND=ROOT/"canonical/governance/OPUS55_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_CEILING_LIFT_V1.json"
SUITES=ROOT/"canonical/governance/CONTRACT_NATIVE_ABSOLUTE_PROOF_SUITES_V1.json"
WAVE=ROOT/"canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"
POST=ROOT/"canonical/verification/TERMINAL_V3_POSTWAVE_CONTRACT_AND_FAMILY_REDUCTION_20261002_V1.json"
TARGETS=ROOT/"canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_CANDIDATE_V1.json"
BIND=ROOT/"canonical/verification/OPUS55_SYNTHESIS_WITNESS_TARGET_BINDING_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
RESID=ROOT/"canonical/verification/OPUS55_SYNTHESIS_IMPLICATION_RESIDUAL_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"

BEHAVIOR="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
TARGET="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"
METRIC="required_claim_coverage_noninferiority"

def load(p): return json.loads(p.read_text(encoding="utf-8"))
def sha(p):
 b=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def fail(*e):
 return {"schema":"PROJECT_BRAIN_OPUS55_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_CEILING_LIFT_VERDICT_V1","status":"FAIL_CLOSED","pass":False,"errors":sorted(set(e)),"capability_credit_delta":0,"family_credit_delta":0,"new_reality_units_consumed":0}

def evaluate(cand:Mapping[str,Any],suites:Mapping[str,Any],wave:Mapping[str,Any],post:Mapping[str,Any],targets:Mapping[str,Any],bind:Mapping[str,Any],resid:Mapping[str,Any],shas:Mapping[str,str]):
 e=[]
 auth=cand.get("authority",{})
 exp={
 "native_absolute_suite":("canonical/governance/CONTRACT_NATIVE_ABSOLUTE_PROOF_SUITES_V1.json",shas["suites"]),
 "terminal_wave":("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json",shas["wave"]),
 "postwave_reduction":("canonical/verification/TERMINAL_V3_POSTWAVE_CONTRACT_AND_FAMILY_REDUCTION_20261002_V1.json",shas["post"]),
 "target_normalization":("canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_CANDIDATE_V1.json",shas["targets"]),
 "synthesis_atom_binding_verification":("canonical/verification/OPUS55_SYNTHESIS_WITNESS_TARGET_BINDING_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",shas["bind"]),
 "synthesis_residual_verification":("canonical/verification/OPUS55_SYNTHESIS_IMPLICATION_RESIDUAL_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",shas["resid"])}
 for k,(p,s) in exp.items():
  r=auth.get(k)
  if not isinstance(r,Mapping) or r.get("path")!=p or r.get("git_blob_sha")!=s: e.append("AUTHORITY_MISMATCH:"+k)

 suite=next((x for x in suites.get("suites",[]) if isinstance(x,Mapping) and x.get("behavior_id")==BEHAVIOR),None)
 if not isinstance(suite,Mapping): e.append("P3_SUITE_MISSING")
 else:
  if "100_PERCENT_REQUIRED_CLAIM_COVERAGE" not in suite.get("oracle",[]): e.append("COVERAGE_CEILING_ORACLE_MISSING")
  if suite.get("terminal_acceptance")!="ALL_HIDDEN_SUPPORT_GRAPH_AND_FORMAT_ORACLES_PASS__CRITICAL_MUTATION_KILL_RATE_100_PERCENT": e.append("TERMINAL_ACCEPTANCE_LITERAL_MISMATCH")

 t=next((x for x in targets.get("targets",[]) if isinstance(x,Mapping) and x.get("predicate_id")==TARGET),None)
 req=None
 if isinstance(t,Mapping):
  req=next((x for x in t.get("metric_requirements",[]) if isinstance(x,Mapping) and x.get("metric")==METRIC),None)
 if not isinstance(req,Mapping) or req.get("direction")!="higher" or req.get("threshold")!=0: e.append("TARGET_METRIC_REQUIREMENT_MISMATCH")

 # Scope firewall: a global metric ceiling does not transport a Brain lower bound
 # from one evaluated population to another. The source performance population must
 # independently cover the frozen matched target population.
 sf=cand.get("scope_firewall")
 if not isinstance(sf,Mapping):
  e.append("SOURCE_TARGET_SCOPE_FIREWALL_MISSING")
 else:
  relation=sf.get("verified_source_to_target_relation")
  if relation not in {"EXACT","SUPERSET"}:
   e.append("SOURCE_SCOPE_NOT_PROVED_EXACT_OR_SUPERSET_OF_TARGET_SCOPE")
  if sf.get("independent_verification") is not True or not isinstance(sf.get("verification_receipt"),str) or not sf.get("verification_receipt"):
   e.append("SOURCE_TARGET_SCOPE_RELATION_NOT_INDEPENDENTLY_VERIFIED")

 parent=wave.get("reduction_input",{}).get("wave",{}).get("parent_portfolio_receipts",{})
 for tier in ("T1","T3"):
  hits=[x for x in parent.get(tier,[]) if isinstance(x,Mapping) and x.get("behavior_id")==BEHAVIOR]
  if len(hits)!=1: e.append(tier+"_RECEIPT_COUNT"); continue
  x=hits[0]
  if any(x.get(k) is not True for k in ("load_bearing","direct_instrumentation_pass","parent_terminal_acceptance_pass")): e.append(tier+"_PASS_REQUIREMENTS")
  if any(x.get(k) is not False for k in ("case_replaced","result_to_runtime_feedback","tuning_replay")): e.append(tier+"_CONTAMINATION")

 if BEHAVIOR not in post.get("contract_verdict",{}).get("passed_contracts",[]): e.append("POSTWAVE_CONTRACT_PASS_MISSING")
 if bind.get("public_runner",{}).get("conclusion")!="success" or bind.get("proved_atom_count")!=7: e.append("ATOM_BINDING_RECEIPT_INVALID")
 if resid.get("public_runner",{}).get("conclusion")!="success" or METRIC not in resid.get("result",{}).get("missing_metric_bounds",[]): e.append("RESIDUAL_RECEIPT_INVALID")

 p=cand.get("proof",{})
 if p.get("frozen_oracle_literal")!="100_PERCENT_REQUIRED_CLAIM_COVERAGE": e.append("CANDIDATE_ORACLE_MISMATCH")
 if p.get("brain_required_claim_coverage_lower_bound")!=1.0 or p.get("admissible_metric_upper_bound")!=1.0: e.append("CEILING_NUMBERS_MISMATCH")
 if p.get("brain_minus_comparator_lower_bound")!=0.0 or p.get("target_direction")!="higher" or p.get("target_threshold")!=0.0: e.append("DERIVED_BOUND_MISMATCH")
 if cand.get("derived_metric_bounds")!={METRIC:{"lower":0.0,"derivation":"ABSOLUTE_CEILING_DOMINANCE"}}: e.append("DERIVED_METRIC_BOUND_SHAPE_MISMATCH")
 if set(cand.get("explicitly_not_proved",[]))!={"metric:matched_quality","matched_quality_noninferiority"}: e.append("MATCHED_QUALITY_EXCLUSION_MISSING")

 if e: return fail(*e)
 return {"schema":"PROJECT_BRAIN_OPUS55_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_CEILING_LIFT_VERDICT_V1","status":"PASS__REQUIRED_CLAIM_COVERAGE_NONINFERIORITY_COMPARATOR_ELIMINATED_BY_100_PERCENT_CEILING__ZERO_CREDIT","pass":True,"metric":METRIC,"brain_lower_bound":1.0,"comparator_upper_bound":1.0,"brain_minus_comparator_lower_bound":0.0,"remaining_unproved":["metric:matched_quality","matched_quality_noninferiority"],"new_reality_units_consumed":0,"capability_credit_delta":0,"family_credit_delta":0}

def main():
 out=evaluate(load(CAND),load(SUITES),load(WAVE),load(POST),load(TARGETS),load(BIND),load(RESID),{"suites":sha(SUITES),"wave":sha(WAVE),"post":sha(POST),"targets":sha(TARGETS),"bind":sha(BIND),"resid":sha(RESID)})
 print(json.dumps(out,indent=2,sort_keys=True)); return 0 if out["pass"] else 1
if __name__=="__main__": raise SystemExit(main())
