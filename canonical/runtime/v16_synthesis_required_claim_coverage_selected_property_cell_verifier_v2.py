from __future__ import annotations
import hashlib,json
from pathlib import Path

R=Path(__file__).resolve().parents[2]
CELL="canonical/governance/V16_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_SELECTED_PROPERTY_CELL_20261007_V2.json"
EXP={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V16.json":"c1bc4543860be08f9014f69a212ba2222d8dba7c",
 "canonical/governance/OPUS55_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_CEILING_LIFT_V2.json":"f2ef80facb39264b1e12b81e451eb4499a3b987f",
 "canonical/governance/SYNTHESIS_SCOPE_CERTIFICATE_V1.json":"dea9028f92f111ee3c8be71615fa4b02e8a8bfb6",
 "canonical/governance/P3_SYNTHESIS_T1_T3_MULTIPLEX_TERMINAL_BINDING_V1.json":"ad790afa864bd8f770c3d8a6e3ac901ed2843d26",
 "canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json":"bd86b4c53992b47a4a60b64a60ba03db9a442cfc",
 "canonical/verification/TERMINAL_V3_DONOR_DELETION_CLEANROOM_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"d3144bf0aa618b15ef594d24de54d55cbdb329fd",
 "canonical/verification/GLOBAL_OWNERSHIP_POSTCONDITIONS_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"e0dbd996c18bdb818693ab0d217d751594a03d0f",
}
T1="T1::EVIDENCE_TO_AUDIENCE_SYNTHESIS_001::aggregate::30"
T3="T3::EVIDENCE_TO_AUDIENCE_SYNTHESIS_001::aggregate::30"
BEH="EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"

def blob(path):
 b=(R/path).read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(path):
 x=json.loads((R/path).read_text())
 if not isinstance(x,dict): raise ValueError(path)
 return x

def rows(x):
 out=[]
 def walk(v):
  if isinstance(v,dict):
   if v.get("behavior_id")==BEH and v.get("case_id") in {T1,T3}: out.append(v)
   for z in v.values(): walk(z)
  elif isinstance(v,list):
   for z in v: walk(z)
 walk(x)
 return out

def verify():
 e=[]
 for p,h in EXP.items():
  q=R/p
  if not q.is_file(): e.append("MISSING:"+p)
  elif blob(p)!=h: e.append("DRIFT:"+p)

 c=load(CELL)
 auth=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V16.json")
 proof=load("canonical/governance/OPUS55_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_CEILING_LIFT_V2.json")
 scope=load("canonical/governance/SYNTHESIS_SCOPE_CERTIFICATE_V1.json")
 bind=load("canonical/governance/P3_SYNTHESIS_T1_T3_MULTIPLEX_TERMINAL_BINDING_V1.json")
 wave=load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json")
 clean=load("canonical/verification/TERMINAL_V3_DONOR_DELETION_CLEANROOM_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
 own=load("canonical/verification/GLOBAL_OWNERSHIP_POSTCONDITIONS_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")

 if auth.get("truth_repair",{}).get("fixed_authorized_opus55_target_interface_scope_superset_closed") is not True:
  e.append("AUTH_SCOPE")
 if auth.get("truth_repair",{}).get("terminal") is not False:
  e.append("AUTH_TERMINAL")

 pc=proof.get("proof_composition",{})
 if not (pc.get("brain_required_claim_coverage_lower_bound")==1 and pc.get("admissible_metric_upper_bound")==1 and pc.get("verified_source_to_target_relation")=="SUPERSET" and pc.get("relation_independent") is True):
  e.append("CEILING_PROOF")
 if set(proof.get("explicitly_not_proved",[]))!={"metric:matched_quality","matched_quality_noninferiority"}:
  e.append("PROOF_OVERCLAIM")

 if not (scope.get("verified") is True and scope.get("independent") is True and scope.get("scope_relation")=="PROVEN_STRONGER" and scope.get("coverage_complete") is True and scope.get("coverage_proof_verified") is True):
  e.append("SCOPE_CERT")
 if scope.get("target_scope_id")!="scope://opus55/SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR":
  e.append("SCOPE_TARGET")
 if scope.get("witness_scope_id")!="scope://brain/EVIDENCE_TO_AUDIENCE_SYNTHESIS_001/T1_T3_TERMINAL":
  e.append("SCOPE_WITNESS")

 if bind.get("behavior_id")!=BEH or set(bind.get("portfolio_bindings",[]))!={"T1","T3"}:
  e.append("P3_BINDING")

 rr=rows(wave)
 if len(rr)!=2 or {x.get("case_id") for x in rr}!={T1,T3}:
  e.append("TERMINAL_ROWS")
 else:
  for x in rr:
   if x.get("binding_blob")!="ad790afa864bd8f770c3d8a6e3ac901ed2843d26": e.append("ROW_BINDING")
   if not all(x.get(k) is True for k in ("direct_instrumentation_pass","load_bearing","parent_terminal_acceptance_pass")): e.append("ROW_PASS")
   if not all(x.get(k) is False for k in ("case_replaced","tuning_replay","result_to_runtime_feedback")): e.append("ROW_CONTAMINATION")

 package="5a347e796d124373b557424a51659e8bb69b854d09da0b407a5b30f109d9467a"
 snapshot="821712c059b139f3494723dca6e8d0fc82ee59a4"
 if wave.get("package_commitment")!=package or wave.get("execution_snapshot_commit")!=snapshot:
  e.append("WAVE_IDENTITY")
 if clean.get("package_commitment")!=package or clean.get("execution_snapshot_commit")!=snapshot:
  e.append("CLEANROOM_IDENTITY")
 if not (clean.get("behavior_preserved") is True and clean.get("byte_identical_terminal_result") is True and clean.get("undeclared_dependency_count")==0 and clean.get("donor_identity_and_hash")==[]):
  e.append("CLEANROOM")

 ctr=((own.get("result") or {}).get("counters") or {})
 if ctr.get("donor_dependent_required_behaviors")!=0 or ctr.get("unresolved_verifier_mutations")!=0 or ctr.get("unresolved_composition_failures")!=0:
  e.append("OWNERSHIP")

 sp=c.get("selected_property_cell",{})
 dom=c.get("dominance",{})
 con=c.get("consequence",{})
 if not (sp.get("brain_lower_bound")==1.0 and sp.get("global_upper_bound")==1.0 and sp.get("scope_complete_for_this_property") is True and sp.get("source_scope_relation")=="PROVEN_STRONGER"):
  e.append("CELL_SEMANTICS")
 if not (dom.get("K_c_minus")=="EMPTY" and dom.get("target_identity_required") is False and dom.get("target_score_required") is False and dom.get("target_information_consumed")==0):
  e.append("CELL_DOMINANCE")
 if con.get("remove_from_current_synthesis_residual")!="REQUIRED_CLAIM_COVERAGE" or con.get("synthesis_family_closed") is not False or con.get("complete_selected_context_ABC_closed") is not False or con.get("D_finality_closed") is not False:
  e.append("CELL_CONSEQUENCE")
 req={"NO_CLAIM_ALL_USEFUL_SYNTHESIS_QUALITY_DIMENSIONS_ARE_NONINFERIOR","NO_CLAIM_SYNTHESIS_FAMILY_CLOSED","NO_CLAIM_COMPLETE_SELECTED_CONTEXT_ABC_CLOSED","NO_CLAIM_D_FINALITY_CLOSED"}
 if not req.issubset(set(c.get("hard_nonclaims",[]))): e.append("NONCLAIMS")
 if c.get("accounting",{}).get("terminal_credit_delta")!=0: e.append("CREDIT")

 return {
  "pass":not e,"errors":e,
  "selected_property_cell":"SYNTHESIS_TARGET_SCOPE_REQUIRED_CLAIM_COVERAGE_TOP_LAW",
  "K_c_minus_empty":not e,
  "target_information_required":False if not e else None,
  "same_package_donor_deleted_route":not e,
  "synthesis_family_closed":False,
  "abc_closed":False,"d_finality_closed":False,"terminal":False,
  "terminal_credit_delta":0
 }

if __name__=="__main__":
 o=verify(); print(json.dumps(o,indent=2,sort_keys=True)); raise SystemExit(0 if o["pass"] else 1)
