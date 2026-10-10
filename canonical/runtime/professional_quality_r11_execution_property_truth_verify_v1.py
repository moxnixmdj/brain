"""R11 execution-leaf property-truth verifier V1.

Discharges the exact manifest acceptance for
PQ::R11_ADAPTIVE_INTEGRITY_SECURITY::EXECUTION by replaying positive,
near-miss, and adversarial behavior on the exact bound firewall/guard bytes.

This is intentionally one execution leaf only.  It does not prove general
prompt-injection/Goodhart/holdout closure, defeater-detection completeness,
the R11 semantic leaf, R11 root closure, professional quality, acceptance,
promotion, or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import evaluation_information_firewall_v1 as firewall
from canonical.runtime import professional_quality_r11_execution_guard_v1 as guard
from canonical.runtime import professional_quality_whole_leaf_domain_equivalence_v1 as domain
from canonical.runtime import professional_quality_whole_leaf_scope_batch_v1 as batch

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R11_EXECUTION_PROPERTY_TRUTH_VERIFY_V1"
LEAF_ID=guard.LEAF_ID
ROOT_ID=guard.ROOT_ID
CLAIM_ID=guard.CLAIM_ID
ACCEPTANCE=(
 "RUN_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_CASES_ON_EXACT_ARTIFACT_OR_RUNTIME_BYTES_"
 "AND_BIND_OBSERVED_OUTCOMES_TO_THE_ROOT_CONTRACT"
)

PINS={
 "manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 "profile":("canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json","f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"),
 "catalog":("canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json","8b92e5cf76f767054f55414b87014e03d43460b8"),
 "root_binding_verify":("canonical/verification/PROFESSIONAL_QUALITY_R11_V7_ROOT_SUBJECT_BINDING_PUBLIC_VERIFY_20261010_V1.json","7fa5857f6f15633172a6c46c7edcd33c2058bfc6"),
 "firewall_scoped_verify":("canonical/verification/PROFESSIONAL_QUALITY_R11_EVALUATION_FIREWALL_SCOPED_VERIFY_20261010_V1.json","346d369a811aa77af02be901a5b04458fb528667"),
 "scope_batch_verify":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json","4c2d40a262f18f34bb35f94b59660d60972d45ef"),
 "firewall_runtime":("canonical/runtime/evaluation_information_firewall_v1.py","11776f87f41c66802a28a417c344cccb394eb2aa"),
 "guard_runtime":("canonical/runtime/professional_quality_r11_execution_guard_v1.py","055402eea98861a57287dde25e2a28cdc2b692b1"),
 "domain_runtime":("canonical/runtime/professional_quality_whole_leaf_domain_equivalence_v1.py","76bf7e1a6f26ff3664ed8c355dff8a688b074159"),
 "batch_runtime":("canonical/runtime/professional_quality_whole_leaf_scope_batch_v1.py","82ab66c7852fc327821b23ff80dd46de3b81525c"),
}


def _blob(path:Path)->str:
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _load(path:Path)->dict[str,Any]:
 value=json.loads(path.read_text(encoding="utf-8"))
 if not isinstance(value,dict):
  raise ValueError("NOT_OBJECT")
 return value


def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,"claim_id":CLAIM_ID,
  "leaf_property_truth_authority":False,
  "detection_completeness_proved":False,
  "r11_semantic_leaf_closed":False,"r11_root_closed":False,
  "semantic_truth_authority":False,"execution_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
 }


def _leaf_acceptance(manifest:Mapping[str,Any])->str|None:
 for row in manifest.get("roots") or []:
  if not isinstance(row,Mapping) or row.get("root_id")!=ROOT_ID:
   continue
  leaf=row.get("execution_leaf")
  if isinstance(leaf,Mapping) and leaf.get("id")==LEAF_ID:
   value=leaf.get("acceptance")
   return value if isinstance(value,str) else None
 return None


def _post_exposure_state()->dict[str,Any]:
 return {
  "lane_id":"clean-r11",
  "task_identity_exposed":True,
  "clean_qualification_active":True,
  "revoked_capabilities":[],
 }


def _pre_exposure_state()->dict[str,Any]:
 return {
  "lane_id":"clean-r11",
  "task_identity_exposed":False,
  "clean_qualification_active":True,
  "revoked_capabilities":[],
 }


def _guard(
 profile:Mapping[str,Any],catalog:Mapping[str,Any],*,
 detected:tuple[str,...]=(),near:Mapping[str,bool]|None=None,
 unmapped:bool=False,claim_id:str=CLAIM_ID,
)->dict[str,Any]:
 return guard.evaluate(
  claim_id=claim_id,
  execution_profile=profile,
  defeater_catalog=catalog,
  detected_defeater_ids=detected,
  near_miss_signals=near or {},
  unmapped_material_false_certification_defeater=unmapped,
 )


def evaluate_documents(
 manifest:Mapping[str,Any],
 profile:Mapping[str,Any],
 catalog:Mapping[str,Any],
 root_binding_verify:Mapping[str,Any],
 firewall_scoped_verify:Mapping[str,Any],
 scope_batch_verify:Mapping[str,Any],
)->dict[str,Any]:
 observed_acceptance=_leaf_acceptance(manifest)
 if observed_acceptance!=ACCEPTANCE:
  return _fail("R11_EXECUTION_ACCEPTANCE_DRIFT",observed_acceptance=observed_acceptance)

 if root_binding_verify.get("root_subject_binding_authority") is not True:
  return _fail("R11_ROOT_SUBJECT_BINDING_NOT_AUTHORITATIVE")
 if (root_binding_verify.get("subject") or {}).get("id")!="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6":
  return _fail("R11_ROOT_SUBJECT_IDENTITY_DRIFT")

 if not str(firewall_scoped_verify.get("status") or "").startswith("PASS__"):
  return _fail("R11_FIREWALL_SCOPED_VERIFY_NOT_PASS")
 if (firewall_scoped_verify.get("current_state") or {}).get("global_leaf_credit") is not False:
  return _fail("R11_FIREWALL_SCOPED_VERIFY_OVERCLAIMS")

 if scope_batch_verify.get("independent_replay",{}).get("scope_complete_count")!=24:
  return _fail("WHOLE_LEAF_SCOPE_BATCH_NOT_COMPLETE")
 if scope_batch_verify.get("independent_replay",{}).get("property_truth_count")!=0:
  return _fail("WHOLE_LEAF_SCOPE_BATCH_PROPERTY_BOUNDARY_DRIFT")
 claim_scope=domain.build_claim_scope(manifest,LEAF_ID,epoch=batch.EPOCH)
 claim=claim_scope.get("claim") or {}
 if claim.get("claim_id")!=CLAIM_ID:
  return _fail("R11_SCOPE_BATCH_CLAIM_ID_DRIFT",observed_claim_id=claim.get("claim_id"))
 dv=domain.evaluate(manifest,claim_scope)
 if dv.get("pass") is not True or dv.get("whole_leaf_domain_equivalence_proved") is not True:
  return _fail("R11_WHOLE_LEAF_DOMAIN_EQUIVALENCE_REPLAY_FAILED")

 clean=_guard(profile,catalog)
 clean_ok=(
  clean.get("pass") is True
  and clean.get("status")=="PASS__R11_EXECUTION_GUARD_ELIGIBLE_FOR_SCOPED_CERTIFICATE_VERIFICATION"
  and clean.get("ordinary_certificate_path_allowed") is True
  and clean.get("whole_leaf_property_truth_proved") is not True
  and clean.get("quality_authority") is False
 )

 known={}
 for did in sorted(guard.KNOWN_R11_DEFEATERS):
  out=_guard(profile,catalog,detected=(did,))
  known[did]=(
   out.get("pass") is False
   and out.get("status")=="ABSTAIN_OR_ESCALATE__KNOWN_R11_DEFEATER_ACTIVE"
   and out.get("ordinary_certificate_path_allowed") is False
   and out.get("required_trigger") in set(profile.get("escalation_triggers") or [])
  )

 near={}
 for signal,trigger in sorted(guard.NEAR_MISS_TO_TRIGGER.items()):
  out=_guard(profile,catalog,near={signal:True})
  near[signal]=(
   out.get("pass") is False
   and out.get("status")=="ESCALATE__R11_NEAR_MISS_TRIGGER"
   and trigger in set(out.get("active_escalation_triggers") or [])
   and out.get("ordinary_certificate_path_allowed") is False
  )

 unknown=_guard(profile,catalog,detected=("C999_FRESH_SECURITY_ATTACK",))
 unknown_ok=(
  unknown.get("status")=="ESCALATE__UNMAPPED_DETECTED_DEFEATER"
  and unknown.get("required_trigger")==guard.GENERIC_TRIGGER
  and unknown.get("ordinary_certificate_path_allowed") is False
 )
 unmapped=_guard(profile,catalog,unmapped=True)
 unmapped_ok=(
  unmapped.get("status")=="ESCALATE__UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER"
  and unmapped.get("required_trigger")==guard.GENERIC_TRIGGER
  and unmapped.get("ordinary_certificate_path_allowed") is False
 )

 denied={}
 for cap in sorted(firewall.DISCOVERY):
  out=firewall.evaluate(_post_exposure_state(),cap)
  denied[cap]=(
   out.get("pass") is True
   and out.get("status")=="DENIED_FAIL_CLOSED"
   and out.get("request_allowed") is False
   and cap in set(out.get("revoked_capabilities") or [])
  )

 allowed={}
 for cap in sorted(firewall.POST_EXPOSURE_ALLOWED):
  out=firewall.evaluate(_post_exposure_state(),cap)
  allowed[cap]=(
   out.get("pass") is True
   and out.get("status")=="ALLOWED"
   and out.get("request_allowed") is True
  )

 pre_discovery={}
 for cap in sorted(firewall.DISCOVERY):
  out=firewall.evaluate(_pre_exposure_state(),cap)
  pre_discovery[cap]=(
   out.get("pass") is True
   and out.get("status")=="ALLOWED"
   and out.get("request_allowed") is True
  )

 unknown_cap=firewall.evaluate(_post_exposure_state(),"UNREGISTERED_DISCOVERY_POWER")
 unknown_cap_ok=(
  unknown_cap.get("pass") is False
  and "UNKNOWN_CAPABILITY" in set(unknown_cap.get("errors") or [])
  and unknown_cap.get("request_allowed") is False
 )

 prev=_post_exposure_state()
 reverse=deepcopy(prev); reverse["task_identity_exposed"]=False
 reverse_out=firewall.transition(prev,reverse)
 reverse_ok=(
  reverse_out.get("pass") is False
  and "IDENTITY_EXPOSURE_CANNOT_BE_REVERSED" in set(reverse_out.get("errors") or [])
 )

 deactivate=deepcopy(prev); deactivate["clean_qualification_active"]=False
 deactivate_out=firewall.transition(prev,deactivate)
 deactivate_ok=(
  deactivate_out.get("pass") is False
  and "CLEAN_LANE_CANNOT_REENABLE_DISCOVERY_BY_DEACTIVATION" in set(deactivate_out.get("errors") or [])
 )

 prev_with_revoked=deepcopy(prev)
 prev_with_revoked["revoked_capabilities"]=["DECLARED_TOOL"]
 restore=deepcopy(prev_with_revoked)
 restore["revoked_capabilities"]=[]
 restore_out=firewall.transition(prev_with_revoked,restore)
 restore_ok=(
  restore_out.get("pass") is False
  and "REVOKED_CAPABILITY_RESTORED" in set(restore_out.get("errors") or [])
 )

 invalid_results={}
 bad=deepcopy(prev); bad["task_identity_exposed"]="yes"
 invalid_results["NONBOOLEAN_IDENTITY"]=firewall.compile_state(bad).get("pass") is False
 bad=deepcopy(prev); bad["clean_qualification_active"]=1
 invalid_results["NONBOOLEAN_CLEAN_MODE"]=firewall.compile_state(bad).get("pass") is False
 bad=deepcopy(prev); bad["revoked_capabilities"]=["NOT_A_CAPABILITY"]
 invalid_results["INVALID_REVOKED_CAPABILITY"]=firewall.compile_state(bad).get("pass") is False

 checks={
  "CLEAN_GUARD_PATH_ELIGIBLE_WITHOUT_TRUTH_INFLATION":clean_ok,
  "ALL_14_KNOWN_R11_DEFEATERS_BLOCK_WHEN_DETECTED":all(known.values()) and len(known)==14,
  "ALL_5_R11_NEAR_MISS_CLASSES_ESCALATE":all(near.values()) and len(near)==5,
  "UNKNOWN_DETECTED_DEFEATER_ESCALATES":unknown_ok,
  "UNMAPPED_MATERIAL_FALSE_CERTIFICATION_ESCALATES":unmapped_ok,
  "ALL_5_DISCOVERY_CAPABILITIES_DENIED_POST_EXPOSURE":all(denied.values()) and len(denied)==5,
  "ALL_5_POST_EXPOSURE_ALLOWED_CAPABILITIES_REMAIN_ALLOWED":all(allowed.values()) and len(allowed)==5,
  "ALL_5_DISCOVERY_CAPABILITIES_ALLOWED_PRE_EXPOSURE":all(pre_discovery.values()) and len(pre_discovery)==5,
  "UNKNOWN_CAPABILITY_DENIES_FAIL_CLOSED":unknown_cap_ok,
  "IDENTITY_EXPOSURE_IRREVERSIBLE":reverse_ok,
  "CLEAN_MODE_DEACTIVATION_CANNOT_BYPASS_SAME_LANE":deactivate_ok,
  "REVOKED_CAPABILITY_CANNOT_BE_RESTORED":restore_ok,
  "MALFORMED_STATE_VARIANTS_FAIL_CLOSED":all(invalid_results.values()) and len(invalid_results)==3,
 }
 if not all(checks.values()):
  return _fail(
   "R11_EXECUTION_PROPERTY_CHALLENGE_FAILED",
   checks=checks,known_defeater_results=known,near_miss_results=near,
   post_exposure_denied=denied,post_exposure_allowed=allowed,
   pre_exposure_discovery=pre_discovery,invalid_state_results=invalid_results,
  )

 total=1+14+5+1+1+5+5+5+1+1+1+1+3
 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__R11_EXECUTION_MANIFEST_ACCEPTANCE_OBSERVED_ON_EXACT_BOUND_RUNTIME_BEHAVIOR__ONE_LEAF_PROPERTY_TRUTH_ONLY",
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,"claim_id":CLAIM_ID,
  "manifest_acceptance":ACCEPTANCE,
  "checks":checks,
  "observed_case_counts":{
   "clean_guard_positive":1,
   "known_adversarial":14,
   "near_miss":5,
   "unknown_detected":1,
   "unmapped_material":1,
   "post_exposure_discovery_denials":5,
   "post_exposure_allowed_capabilities":5,
   "pre_exposure_discovery_allowed":5,
   "unknown_capability":1,
   "identity_reversal":1,
   "same_lane_clean_deactivation":1,
   "revocation_restoration":1,
   "malformed_states":3,
   "total":total,
  },
  "leaf_property_truth_authority":True,
  "property_truth_basis":"MANIFEST_CASE_BASED_EXECUTION_ACCEPTANCE_ON_EXACT_BOUND_FIREWALL_AND_GUARD_BEHAVIOR",
  "detection_completeness_proved":False,
  "general_prompt_injection_closure_proved":False,
  "general_goodhart_closure_proved":False,
  "holdout_lifecycle_closure_proved":False,
  "cross_lane_security_generalization_proved":False,
  "r11_semantic_leaf_closed":False,"r11_root_closed":False,
  "semantic_truth_authority":False,"execution_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,
 }


def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 docs={}
 for key,(rel,expected) in PINS.items():
  p=root/rel
  if not p.is_file() or p.is_symlink():
   return _fail(key.upper()+"_MISSING")
  observed=_blob(p)
  if expected is not None and observed!=expected:
   return _fail(key.upper()+"_BLOB_STALE",observed_blob=observed)
  if key in {
   "manifest","profile","catalog","root_binding_verify",
   "firewall_scoped_verify","scope_batch_verify",
  }:
   try:
    docs[key]=_load(p)
   except Exception:
    return _fail(key.upper()+"_JSON_INVALID")
 return evaluate_documents(
  docs["manifest"],docs["profile"],docs["catalog"],docs["root_binding_verify"],
  docs["firewall_scoped_verify"],docs["scope_batch_verify"],
 )


if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
