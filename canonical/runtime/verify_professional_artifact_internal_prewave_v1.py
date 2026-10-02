"""Verify internal prewave binding for professional artifact planning.

The verifier fails closed if the binding drops any unresolved professional-artifact
quality dimension from the canonical P2/P3 scope-equivalence audit. Public-bar
coverage may not silently inherit or erase uncovered scope.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path

BIND="canonical/governance/PROFESSIONAL_ARTIFACT_INTERNAL_PREWAVE_BINDING_V1.json"
AUDIT="canonical/governance/P2_P3_SCOPE_EQUIVALENCE_AUDIT_V1.json"
BEHAVIOR="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
FILES={
 "candidate":"canonical/runtime/p2_p3_information_safe_candidate_v2.py",
 "information_safe_suite":"canonical/runtime/p2_p3_information_safe_proof_suites_v2.py",
 "preflight_receipt":"canonical/verification/P2_P3_INFORMATION_SAFE_PREFLIGHT_VERIFICATION_20261002_V1.json",
 "behavioral_registry":"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json",
 "population_protocol":"canonical/governance/GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json",
 "scope_equivalence_audit":AUDIT,
}

def sha(p:Path):
 d=p.read_bytes()
 return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _professional_audit_row(root:Path):
 a=json.loads((root/AUDIT).read_text())
 rows=[x for x in a.get("contracts",[]) if isinstance(x,dict) and x.get("behavior_id")==BEHAVIOR]
 if len(rows)!=1:
  raise ValueError("PROFESSIONAL_AUDIT_ROW_COUNT")
 return rows[0]

def verify(root:Path):
 b=json.loads((root/BIND).read_text()); e=[]
 for k,p in FILES.items():
  if sha(root/p)!=b["exact_blobs"].get(k): e.append("BLOB_DRIFT:"+k)
 ib=b["information_boundary"]
 if ib["candidate_receives_hidden_oracle"] is not False: e.append("ORACLE_VISIBLE")
 if ib["candidate_receives_reference_solution"] is not False: e.append("REFERENCE_VISIBLE")
 if b["post_freeze_accounting"]["adaptive_case_selection"] is not False: e.append("ADAPTIVE_SELECTION")
 if b["post_freeze_accounting"]["case_replacement"] is not False: e.append("CASE_REPLACEMENT")
 if b["post_freeze_accounting"]["tuning_replay"] is not False: e.append("TUNING_REPLAY")
 if b.get("execution_authority") is not False or b.get("terminal_results_observed")!=0: e.append("PREWAVE_OVERCLAIM")

 u=b.get("uncovered_scope_audit") or {}
 if u.get("no_scope_inheritance") is not True: e.append("SCOPE_INHERITANCE")
 if u.get("audit_source")!=AUDIT: e.append("AUDIT_SOURCE_NOT_EXACT")
 try:
  row=_professional_audit_row(root)
  expected=row.get("unresolved_required_dimensions")
  bound=u.get("authoritative_unresolved_dimensions")
  if not isinstance(expected,list) or not expected or any(not isinstance(x,str) or not x for x in expected):
   e.append("AUTHORITATIVE_RESIDUAL_INVALID")
  elif len(expected)!=len(set(expected)):
   e.append("AUTHORITATIVE_RESIDUAL_DUPLICATE")
  if not isinstance(bound,list) or not bound or any(not isinstance(x,str) or not x for x in bound):
   e.append("BOUND_RESIDUAL_INVALID")
  elif len(bound)!=len(set(bound)):
   e.append("BOUND_RESIDUAL_DUPLICATE")
  elif sorted(bound)!=sorted(expected):
   e.append("UNCOVERED_SCOPE_RESIDUAL_MISMATCH")
  if row.get("scope_equivalent_now") is not False:
   e.append("AUTHORITATIVE_AUDIT_NO_LONGER_UNCOVERED")
  if u.get("authoritative_scope_equivalent_now") is not False:
   e.append("BINDING_SCOPE_EQUIVALENCE_FLAG_INVALID")
 except Exception as exc:
  e.append("AUDIT_READ_ERROR:"+type(exc).__name__)

 return {"status":"PASS" if not e else "FAIL_CLOSED","errors":sorted(set(e)),"execution_authority":False}
