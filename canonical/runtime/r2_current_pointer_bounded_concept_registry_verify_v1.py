from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_R2_CURRENT_POINTER_BOUNDED_CONCEPT_RECONCILE_VERIFY_V1"
ROOT=Path(__file__).resolve().parents[2]
POINTER="canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
EXPECTED={
 "canonical/governance/R2_FINANCE_BOUNDED_CONCEPT_REGISTRY_ACTIVATION_20261009_V1.json":"75e24b019afc9037df4bd89d92c1178a6ce9841b",
 "canonical/runtime/finance_bounded_concept_registry_v1.py":"53910611bfee595a6579630f975b3ce816bf23e9",
 "canonical/runtime/finance_bounded_concept_registry_verify_v1.py":"2da499510a6344b90a93cc65855dc3f480c3f809",
 "canonical/verification/R2_FINANCE_BOUNDED_CONCEPT_REGISTRY_VERIFY_20261009_V2.json":"9236b1e14cf8ff3434a8a55b6b31b03e29b20b36",
}

def _blob(path:Path)->str:
 raw=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def evaluate(repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 errors=[]
 for rel,want in EXPECTED.items():
  p=root/rel
  if not p.is_file():
   errors.append("MISSING:"+rel); continue
  got=_blob(p)
  if got!=want:
   errors.append("DRIFT:"+rel+":"+got)
 p=root/POINTER
 if not p.is_file():
  errors.append("POINTER_MISSING")
  doc={}
 else:
  try: doc=json.loads(p.read_text(encoding="utf-8"))
  except Exception as exc:
   errors.append("POINTER_JSON_INVALID:"+type(exc).__name__); doc={}
 status=str(doc.get("status") or "")
 if "__V46__" not in status:
  errors.append("POINTER_VERSION_NOT_V46")
 if "ONE_PRIMARY_FINANCE_SEMANTIC_RESIDUAL_REMAINS" not in status:
  errors.append("FINANCE_RESIDUAL_NOT_PRESERVED")
 if doc.get("global_open_world_closure_claimed") is not False:
  errors.append("GLOBAL_OPEN_WORLD_CLOSURE_MUST_REMAIN_FALSE")
 if doc.get("control_mechanism_status")!="CLOSED__TOTAL_FAIL_CLOSED_ADEQUACY_OR_ABSTAIN_CONTROL":
  errors.append("CONTROL_MECHANISM_STATUS_DRIFT")

 reg=doc.get("bounded_finance_concept_registry")
 if not isinstance(reg,dict):
  errors.append("BOUNDED_REGISTRY_SECTION_MISSING")
 else:
  expected_fields={
   "activation_git_blob_sha":EXPECTED["canonical/governance/R2_FINANCE_BOUNDED_CONCEPT_REGISTRY_ACTIVATION_20261009_V1.json"],
   "producer_git_blob_sha":EXPECTED["canonical/runtime/finance_bounded_concept_registry_v1.py"],
   "independent_verifier_git_blob_sha":EXPECTED["canonical/runtime/finance_bounded_concept_registry_verify_v1.py"],
   "verification_git_blob_sha":EXPECTED["canonical/verification/R2_FINANCE_BOUNDED_CONCEPT_REGISTRY_VERIFY_20261009_V2.json"],
   "open_world_finance_ontology_complete":False,
  }
  for key,want in expected_fields.items():
   if reg.get(key)!=want:
    errors.append("REGISTRY_FIELD_MISMATCH:"+key)
  if reg.get("wake_condition_satisfied")!="NEW_AUTHENTICATED_BOUNDED_CONCEPT_REGISTRY_WITH_SCOPE_COMPLETENESS_AND_CONCEPT_SEMANTICS_BOUND_TO_EXACT_BYTES":
   errors.append("WAKE_CONDITION_BINDING_MISMATCH")

 policy=doc.get("fixed_point_information_policy")
 if not isinstance(policy,dict) or policy.get("bounded_finance_concept_registry_auto_verified") is not True:
  errors.append("INFORMATION_POLICY_NOT_UPDATED")
 if isinstance(policy,dict) and policy.get("bounded_finance_concept_registry_open_world_ontology_complete") is not False:
  errors.append("INFORMATION_POLICY_OPEN_WORLD_FALSE_REQUIRED")

 remaining=str(doc.get("remaining_problem_class") or "")
 if "FINANCE_RESIDUAL_NOW_EXCLUDES_EXACT_SOURCE_EXPLICIT_DEFINITION_OR_ALIAS_CHAINS" not in remaining:
  errors.append("REMAINING_FRONTIER_NOT_SHRUNK")
 for required in (
  "AMBIGUOUS_OR_IMPLICIT_COREFERENCE",
  "OEWN_SENSE_CASES",
  "OPEN_WORLD_ONTOLOGY_MAPPING",
  "STRONGER_EXTERNAL_FACT_AUTHENTICATION",
  "OPEN_WORLD_NOT_CLOSED",
 ):
  if required not in remaining:
   errors.append("REMAINING_FRONTIER_MISSING:"+required)

 return {
  "schema":SCHEMA,
  "pass":not errors,
  "status":"PASS__R2_CURRENT_POINTER_BOUNDED_CONCEPT_REGISTRY_RECONCILED__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
  "errors":errors,
  "bounded_registry_coverage_live":not errors,
  "finance_residual_still_open":not errors,
  "global_open_world_closure_claimed":False,
  "terminal_authority":False,
  "terminal_credit_delta":0,
 }

if __name__=="__main__":
 print(json.dumps(evaluate(),indent=2,sort_keys=True))
