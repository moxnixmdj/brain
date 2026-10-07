from __future__ import annotations
import hashlib, json
from pathlib import Path

R = Path(__file__).resolve().parents[2]
M = "canonical/governance/V16_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V6.json"
EXP = {
 "canonical/governance/TERMINAL_NOW_V19_LIVE_RECONCILIATION_20261007_V1.json":"c1b8f0a4c57cb298f40b474173bca089cccc727e",
 "canonical/governance/V16_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V5.json":"6b389699903b63f1350dd922064888e74201f687",
 "canonical/governance/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_SELECTED_PROPERTY_CELL_20261007_V1.json":"28692768a21e95b51e847417cf5ba2343587e4aa",
 "canonical/verification/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_WOLFRAM_VERIFICATION_20261007_V1.json":"aefee446782989518c9794db1e73909bd3c4f55c",
 "canonical/governance/V16_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_SELECTED_PROPERTY_CELL_20261007_V1.json":"7b2cb008f34082ae0aa4be78f2444287cf6022b2",
 "canonical/runtime/v16_synthesis_required_claim_coverage_selected_property_cell_verifier_v1.py":"0ae99fc4e09126f2018e54fc38e4cbfa9c28f2e7",
}
ADD={
 "PROFESSIONAL_ARTIFACT_T1_FROZEN_30_ZERO_UNSUPPORTED_MATERIAL_CONTENT",
 "SYNTHESIS_TARGET_SCOPE_REQUIRED_CLAIM_COVERAGE_TOP_LAW",
}

def sha(rel):
 b=(R/rel).read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(rel):
 return json.loads((R/rel).read_text())

def verify():
 e=[]
 for p,h in EXP.items():
  if not (R/p).is_file(): e.append("MISSING:"+p)
  elif sha(p)!=h: e.append("DRIFT:"+p)

 v5=load("canonical/governance/V16_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V5.json")
 m=load(M)
 if v5.get("reconciliation",{}).get("known_sound_region_certificate_count")!=12: e.append("V5_COUNT")
 old={
  v5.get("parallel_delta_A",{}).get("exact_added_region"),
  v5.get("parallel_delta_B",{}).get("exact_added_region"),
 }
 added={x.get("id") for x in m.get("added_certificates",[])}
 if added!=ADD or len(m.get("added_certificates",[]))!=2: e.append("ADD_SET")
 if old & added: e.append("DELTA_ALIAS")

 p=load("canonical/governance/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_SELECTED_PROPERTY_CELL_20261007_V1.json")
 pv=load("canonical/verification/V14_PROFESSIONAL_ARTIFACT_UNSUPPORTED_CONTENT_WOLFRAM_VERIFICATION_20261007_V1.json")
 pc=p.get("selected_property_cell",{})
 if not (pc.get("population_complete") is True and pc.get("brain_value")==1 and pc.get("top_value")==1): e.append("PROF_TOP")
 if pv.get("wolfram_result") is not True: e.append("PROF_VERIFY")

 s=load("canonical/governance/V16_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_SELECTED_PROPERTY_CELL_20261007_V1.json")
 sc=s.get("selected_property_cell",{})
 sd=s.get("dominance",{})
 if not (sc.get("scope_complete_for_this_property") is True and sc.get("brain_lower_bound")==1 and sc.get("global_upper_bound")==1): e.append("SYNTH_TOP")
 if sd.get("K_c_minus")!="EMPTY" or s.get("v16_effect",{}).get("add_to_D_B")!="SYNTHESIS_TARGET_SCOPE_REQUIRED_CLAIM_COVERAGE_TOP_LAW": e.append("SYNTH_DB")

 rec=m.get("reconciliation",{})
 if rec.get("inherited_certificate_count")!=12 or rec.get("added_certificate_count")!=2 or rec.get("known_sound_region_certificate_count")!=14: e.append("COUNT")
 if rec.get("fresh_target_reality_consumed")!=0: e.append("FRESH_REALITY")
 if m.get("accounting",{}).get("terminal_credit_delta")!=0: e.append("CREDIT")

 live=load("canonical/governance/TERMINAL_NOW_V19_LIVE_RECONCILIATION_20261007_V1.json")
 if live.get("reconciled_truth",{}).get("terminal") is not False: e.append("LIVE_TERMINAL_DRIFT")
 return {"pass":not e,"errors":e,"known_sound_region_certificate_count":14 if not e else None,
         "fresh_target_reality_consumed":0,"terminal":False,"terminal_credit_delta":0}

if __name__=="__main__":
 o=verify(); print(json.dumps(o,indent=2,sort_keys=True)); raise SystemExit(0 if o["pass"] else 1)
