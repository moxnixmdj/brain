"""Verify internal prewave binding for professional artifact planning."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
BIND="canonical/governance/PROFESSIONAL_ARTIFACT_INTERNAL_PREWAVE_BINDING_V1.json"
FILES={
 "candidate":"canonical/runtime/p2_p3_information_safe_candidate_v2.py",
 "information_safe_suite":"canonical/runtime/p2_p3_information_safe_proof_suites_v2.py",
 "preflight_receipt":"canonical/verification/P2_P3_INFORMATION_SAFE_PREFLIGHT_VERIFICATION_20261002_V1.json",
 "behavioral_registry":"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json",
 "population_protocol":"canonical/governance/GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json",
}
def sha(p:Path):
 d=p.read_bytes(); return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def verify(root:Path):
 b=json.loads((root/BIND).read_text()); e=[]
 for k,p in FILES.items():
  if sha(root/p)!=b["exact_blobs"][k]: e.append("BLOB_DRIFT:"+k)
 ib=b["information_boundary"]
 if ib["candidate_receives_hidden_oracle"] is not False: e.append("ORACLE_VISIBLE")
 if ib["candidate_receives_reference_solution"] is not False: e.append("REFERENCE_VISIBLE")
 if b["post_freeze_accounting"]["adaptive_case_selection"] is not False: e.append("ADAPTIVE_SELECTION")
 if b["post_freeze_accounting"]["case_replacement"] is not False: e.append("CASE_REPLACEMENT")
 if b["post_freeze_accounting"]["tuning_replay"] is not False: e.append("TUNING_REPLAY")
 if b.get("execution_authority") is not False or b.get("terminal_results_observed")!=0: e.append("PREWAVE_OVERCLAIM")
 if b["uncovered_scope_audit"].get("no_scope_inheritance") is not True: e.append("SCOPE_INHERITANCE")
 return {"status":"PASS" if not e else "FAIL_CLOSED","errors":sorted(set(e)),"execution_authority":False}
