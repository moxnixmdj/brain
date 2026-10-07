from __future__ import annotations
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[2]
CASE="T1::PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001::aggregate::30"
BEH="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
EXP={
"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V14.json":"d9bd211b2557ac45331f6fe0c4347392f4cd7a95",
"canonical/governance/ARTIFACT_PROFESSIONAL_RESIDUAL_REDUCTION_20261007_V1.json":"afaf6e9c4dfe13873b732d49a468329fc9510ffe",
"canonical/governance/P2_PROFESSIONAL_QUALITY_T1_MULTIPLEX_TERMINAL_BINDING_V1.json":"8d5888a8299d1b8addd629be01fe9a6dc46b1a7d",
"canonical/runtime/p2_p3_information_safe_proof_suites_v2.py":"9d3d9bb837a98a7f78b5794cec0c0ae88bb32860",
"canonical/verification/P2_P3_INFORMATION_SAFE_PREFLIGHT_VERIFICATION_20261002_V1.json":"11a7212c3b54ed130212b3a7d4f4e4386bc590f5",
"canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json":"bd86b4c53992b47a4a60b64a60ba03db9a442cfc",
}
def blob(p):
 b=(R/p).read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p):return json.loads((R/p).read_text())
def rows(x):
 out=[]
 def w(v):
  if isinstance(v,dict):
   if v.get("case_id")==CASE and v.get("behavior_id")==BEH: out.append(v)
   for z in v.values(): w(z)
  elif isinstance(v,list):
   for z in v:w(z)
 w(x);return out
def verify():
 e=[]
 for p,h in EXP.items():
  if blob(p)!=h:e.append("DRIFT:"+p)
 wave=load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json")
 rr=rows(wave)
 if len(rr)!=1:e.append("ROW_COUNT")
 else:
  q=rr[0]
  if not all(q.get(k) is True for k in ("direct_instrumentation_pass","load_bearing","parent_terminal_acceptance_pass")):e.append("ROW_PASS")
  if not all(q.get(k) is False for k in ("case_replaced","tuning_replay","result_to_runtime_feedback")):e.append("ROW_CONTAMINATION")
 pre=load("canonical/verification/P2_P3_INFORMATION_SAFE_PREFLIGHT_VERIFICATION_20261002_V1.json")
 if (pre.get("adjudication") or {}).get("P2_"+BEH)!="PREQUALIFICATION_INFORMATION_BOUNDARY_PASS":e.append("INFO_BOUNDARY")
 src=(R/"canonical/runtime/p2_p3_information_safe_proof_suites_v2.py").read_text()
 for token in ("for subset in combinations(edits,n)",'"selected_edits":list(best[1])','tuple(sorted(selected))==tuple(sorted(oracle["selected_edits"]))'):
  if token not in src:e.append("SEMANTIC:"+token)
 return {"pass":not e,"errors":e,"selected_cell_case_count":30 if not e else None,"top_law_selected_cell_candidate":not e,"whole_professional_scope_closed":False,"terminal":False,"terminal_credit_delta":0}
if __name__=="__main__":
 o=verify();print(json.dumps(o,sort_keys=True));raise SystemExit(0 if o["pass"] else 1)
