from __future__ import annotations
import hashlib,json
from pathlib import Path

R=Path(__file__).resolve().parents[2]
CELL="canonical/governance/V16_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_SELECTED_PROPERTY_CELL_20261007_V1.json"
EXP={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V15.json":"09f11461c7aa1ee7719409723726712f68d03da8",
 "canonical/governance/TERMINAL_NOW_V16_RESIDUAL_NORMALIZATION_20261007_V1.json":"8fb8c0b01d8834d39ca9de38cd79d57ac6f2e281",
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

def blob(p):
 b=(R/p).read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(p):
 x=json.loads((R/p).read_text())
 if not isinstance(x,dict): raise ValueError(p)
 return x

def find_rows(x):
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
 proof=load("canonical/governance/OPUS55_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_CEILING_LIFT_V2.json")
 scope=load("canonical/governance/SYNTHESIS_SCOPE_CERTIFICATE_V1.json")
 bind=load("canonical/governance/P3_SYNTHESIS_T1_T3_MULTIPLEX_TERMINAL_BINDING_V1.json")
 wave=load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json")
 clean=load("canonical/verification/TERMINAL_V3_DONOR_DELETION_CLEANROOM_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")
 own=load("canonical/verification/GLOBAL_OWNERSHIP_POSTCONDITIONS_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json")

 pc=proof.get("proof_composition",{})
 if not (pc.get("brain_required_claim_coverage_lower_bound")==1 and pc.get("admissible_metric_upper_bound")==1 and pc.get("verified_source_to_target_relation")=="SUPERSET" and pc.get("relation_independent") is True):
  e.append("COVERAGE_PROOF")
 if scope.get("verified") is not True or scope.get("independent") is not True or scope.get("scope_relation")!="PROVEN_STRONGER" or scope.get("coverage_complete") is not True:
  e.append("SCOPE_CERT")
 if bind.get("behavior_id")!=BEH or set(bind.get("portfolio_bindings",[]))!={"T1","T3"}:
  e.append("P3_BINDING")
 rows=find_rows(wave)
 if {x.get("case_id") for x in rows}!={T1,T3} or len(rows)!=2:
  e.append("TERMINAL_ROWS")
 else:
  for x in rows:
   if x.get("binding_blob")!="ad790afa864bd8f770c3d8a6e3ac901ed2843d26": e.append("ROW_BINDING")
   if not all(x.get(k) is True for k in ("direct_instrumentation_pass","load_bearing","parent_terminal_acceptance_pass")): e.append("ROW_PASS")
   if not all(x.get(k) is False for k in ("case_replaced","tuning_replay","result_to_runtime_feedback")): e.append("ROW_CONTAMINATION")
 if wave.get("package_commitment")!="5a347e796d124373b557424a51659e8bb69b854d09da0b407a5b30f109d9467a" or wave.get("execution_snapshot_commit")!="821712c059b139f3494723dca6e8d0fc82ee59a4":
  e.append("WAVE_IDENTITY")
 if clean.get("package_commitment")!=wave.get("package_commitment") or clean.get("execution_snapshot_commit")!=wave.get("execution_snapshot_commit"):
  e.append("CLEANROOM_IDENTITY")
 if not (clean.get("behavior_preserved") is True and clean.get("byte_identical_terminal_result") is True and clean.get("undeclared_dependency_count")==0 and clean.get("donor_identity_and_hash")==[]):
  e.append("CLEANROOM")
 counters=((own.get("result") or {}).get("counters") or {})
 if counters.get("donor_dependent_required_behaviors")!=0 or counters.get("unresolved_verifier_mutations")!=0 or counters.get("unresolved_composition_failures")!=0:
  e.append("OWNERSHIP_POSTCONDITIONS")

 sp=c.get("selected_property_cell",{})
 dom=c.get("dominance",{})
 eff=c.get("v16_effect",{})
 if not (sp.get("brain_lower_bound")==1.0 and sp.get("global_upper_bound")==1.0 and sp.get("scope_complete_for_this_property") is True):
  e.append("CELL_SEMANTICS")
 if dom.get("K_c_minus")!="EMPTY" or dom.get("target_identity_required") is not False or dom.get("target_score_required") is not False:
  e.append("CELL_DOMINANCE")
 if eff.get("remove_from_synthesis_residual")!="REQUIRED_CLAIM_COVERAGE" or eff.get("synthesis_family_closed") is not False or eff.get("abc_closed") is not False:
  e.append("CELL_EFFECT")
 req={"NO_CLAIM_ALL_USEFUL_SYNTHESIS_QUALITY_DIMENSIONS_ARE_NONINFERIOR","NO_CLAIM_SYNTHESIS_FAMILY_CLOSED","NO_CLAIM_GLOBAL_ABC_CLOSED","NO_CLAIM_GLOBAL_D_FINALITY_CLOSED"}
 if not req.issubset(set(c.get("hard_nonclaims",[]))): e.append("NONCLAIMS")
 if c.get("accounting",{}).get("terminal_credit_delta")!=0: e.append("CREDIT")

 return {
  "pass":not e,"errors":e,
  "selected_property_cell":"SYNTHESIS_TARGET_SCOPE_REQUIRED_CLAIM_COVERAGE_TOP_LAW",
  "K_c_minus_empty":not e,
  "target_information_required":False if not e else None,
  "same_package_donor_deletion_bound":not e,
  "synthesis_family_closed":False,
  "abc_closed":False,"d_finality_closed":False,"terminal":False,"terminal_credit_delta":0
 }

if __name__=="__main__":
 o=verify(); print(json.dumps(o,indent=2,sort_keys=True)); raise SystemExit(0 if o["pass"] else 1)
