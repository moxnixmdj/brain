"""Constructive counterexample search for the frozen R12 whole-leaf semantic predicate.

Uses the already-authenticated real V9 professional task, preserves its exact
run-context inputs, removes only the load-bearing professional proof bindings,
and requires V9 to abstain. If the frozen whole-leaf scope truly has no filters
or exclusions and the claim requires all material semantic/defeater premises
resolved on every admissible input, this is a constructive counterexample to
that over-strong universal predicate.

This does not close R12. It authorizes only specification repair if all pinned
premises validate.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_p1_router_v9 as v9
from canonical.runtime import professional_quality_p1_router_v8 as v8
from canonical.runtime import professional_step_binding_authority_v1 as sb

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_WHOLE_LEAF_COUNTEREXAMPLE_V1"
CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
SCOPE_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V9_DECLARED_SYSTEM_SUBJECT_20261010_V8.json"
SUBJECT_BLOB="2ff32e4bb78e63635244c86d47fa369d7ba53900"
PINS={
 "claim":("canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261010_V2.json","7b26ddba501358d42d6fa342efd27d389bb30654"),
 "r1":("canonical/governance/COVERAGE_CC_R1_PROFESSIONAL_R12_SEMANTIC_CERTIFICATE_20261010_V2.json","f7182bc43bfc48f4e019a0186534e14bd5374419"),
 "r2":("canonical/governance/COVERAGE_CC_R2_PROFESSIONAL_R12_SEMANTIC_CERTIFICATE_20261010_V2.json","8fc8057152ba26cd91643ec75d8853d421b59cba"),
 "domain":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_DOMAIN_EQUIVALENCE_V1_INDEPENDENT_VERIFY_20261010_V1.json","b6b826d1658d8a2c88ea80260ee667e86ae99394"),
 "scope":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json","4c2d40a262f18f34bb35f94b59660d60972d45ef"),
 "replay":("canonical/verification/V9_REAL_R12_SECOND_CARRIER_REPLAY_VERIFY_20261011_V1.json","93fd0bcb6ec271df53fd9694cc3dc242a185aab0"),
 "r3_evidence":("canonical/evidence/PROFESSIONAL_QUALITY_R3_V7_EXACT_REALIZATION_INSTANCE_20261010_V1.json","13e7e58b3621b3cabb7abdebe23689f3a72678d2"),
}

GOAL="Replace the single visible token OLD314159 with NEW314159 in the exact DOCX, preserving all unrelated package structure and audience-visible layout outside the localized edit."
DECISION_PAYLOAD={
 "context_id":"PQ_R12_V9_REAL_DOCX_20261010_V1",
 "professional_target_instance":{
  "objective":"Apply exactly one bounded visible text replacement OLD314159 -> NEW314159.",
  "audience":"A document reader viewing the rendered DOCX.",
  "source_evidence":{
   "source_docx_sha256":"1db684b36a66b59f5a8a748036f21a9b7b4e4ff83db6904adfa34137089eb94e",
   "source_token":"OLD314159","source_token_count":1,
   "fresh_render_report":"fresh_render_report.json",
  },
  "artifact_type":"docx",
  "constraints":[
   "Exactly one OLD314159 occurrence exists in the source and is replaced by NEW314159.",
   "No unrelated ZIP member bytes may change.",
   "The output must remain a valid nonempty DOCX.",
   "The rendered visible change must remain localized to the edited token region.",
  ],
  "current_draft_or_render":{
   "source_docx_sha256":"1db684b36a66b59f5a8a748036f21a9b7b4e4ff83db6904adfa34137089eb94e",
   "source_png_sha256":"314dc1a10dd9242046d082ab38c826912e9c8a5c143a96d0e2a3e13c80264f94",
  },
 }
}
ARTIFACT_PATHS=["output.docx"]
PROFILE="BRAIN_PROFESSIONAL_OOXML_SANITY_V1"
TRIGGERS=[]

def _blob(p:Path)->str:
 raw=p.read_bytes();return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "constructive_counterexample_proved":False,"original_universal_predicate_falsified":False,
  "specification_repair_authorized":False,"semantic_property_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

def _load(root:Path,key:str)->dict[str,Any]:
 rel,expected=PINS[key];p=root/rel
 if not p.is_file() or p.is_symlink():raise ValueError("PIN_MISSING:"+key)
 got=_blob(p)
 if got!=expected:raise ValueError("PIN_BLOB_DRIFT:"+key+":"+got)
 o=json.loads(p.read_text())
 if not isinstance(o,dict):raise ValueError("PIN_NOT_OBJECT:"+key)
 return o

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 try:
  claim=_load(root,"claim");r1=_load(root,"r1");r2=_load(root,"r2")
  domain=_load(root,"domain");scope=_load(root,"scope");replay=_load(root,"replay");r3=_load(root,"r3_evidence")
 except Exception as exc:return _fail(type(exc).__name__+":"+str(exc))

 if claim.get("claim_id")!=CLAIM_ID or claim.get("whole_leaf_scope_claim_id")!=SCOPE_ID:
  return _fail("CLAIM_IDENTITY_DRIFT")
 target=claim.get("target_predicate") or {}
 if target.get("quantification")!="FOR_ALL_ADMISSIBLE_INPUTS_IN_VERIFIED_WHOLE_LEAF_SCOPE":
  return _fail("TARGET_NOT_UNIVERSAL_WHOLE_LEAF")
 acceptance=target.get("acceptance")
 if acceptance!="DOMAIN_SPECIFIC_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_AND_ALL_ROOT_RELEVANT_DEFEATERS_RESOLVED_WITH_TYPED_EVIDENCE":
  return _fail("TARGET_PREDICATE_DRIFT")

 if r1.get("claim_id")!=CLAIM_ID or r1.get("whole_leaf_scope_claim_id")!=SCOPE_ID:
  return _fail("R1_CLAIM_BINDING_DRIFT")
 bplus=r1.get("b_plus_model") or {}
 if bplus.get("admissibility")!="EXACT_WHOLE_ADMISSIBLE_LEAF_DOMAIN__NO_FILTERS__NO_EXCLUSIONS":
  return _fail("WHOLE_LEAF_FILTER_OR_EXCLUSION_PRESENT")
 theorem=r1.get("theorem") or {}
 if theorem.get("b_real_subseteq_b_plus") is not True:return _fail("R1_REALITY_CONTAINMENT_NOT_PROVED")

 if not str(domain.get("status") or "").startswith("PASS__") or (domain.get("independent_replay") or {}).get("real_manifest_passed")!=24:
  return _fail("WHOLE_DOMAIN_EQUIVALENCE_NOT_VERIFIED")
 if not str(scope.get("status") or "").startswith("PASS__") or (scope.get("independent_replay") or {}).get("scope_complete_count")!=24:
  return _fail("WHOLE_SCOPE_NOT_VERIFIED")

 terms=r2.get("claim_scoped_terms") or {}
 unresolved=terms.get("unresolved_binding")
 if not isinstance(unresolved,str) or "BLOCKS_POSITIVE_CERTIFICATION" not in unresolved or "ABSTENTION" not in unresolved:
  return _fail("R2_UNRESOLVED_ABSTENTION_RULE_MISSING")
 if (r2.get("theorem") or {}).get("g_minus_subseteq_g_real") is not True:
  return _fail("R2_MISSION_SOUNDNESS_NOT_PROVED")

 truth=replay.get("truth") or {}
 reproduced=replay.get("reproduced_result") or {}
 if truth.get("real_v9_positive_execution_observed") is not True or reproduced.get("pass")!="ROUTE__P1_ORDINARY":
  return _fail("REAL_V9_TASK_NOT_AUTHENTICATED")
 if (r3.get("behavior_id")!=v8.BEHAVIOR_ID or
     (r3.get("artifacts") or {}).get("source_docx_sha256")!=(replay.get("exact_replayed_artifacts") or {}).get("source_docx_sha256") or
     (r3.get("artifacts") or {}).get("output_docx_sha256")!=(replay.get("exact_replayed_artifacts") or {}).get("output_docx_sha256")):
  return _fail("REAL_TASK_EVIDENCE_CHAIN_MISMATCH")

 run_context=sb.run_context_digest(goal=GOAL,decision_payload=DECISION_PAYLOAD,
  artifact_paths=ARTIFACT_PATHS,hard_defect_profile_id=PROFILE,detected_triggers=TRIGGERS)
 if run_context!=reproduced.get("run_context_sha256"):
  return _fail("REAL_TASK_RUN_CONTEXT_RECONSTRUCTION_MISMATCH",observed=run_context,expected=reproduced.get("run_context_sha256"))

 state={
  "declared_system_subject":{"path":SUBJECT_PATH,"git_blob_sha":SUBJECT_BLOB},
  "goal":GOAL,"decision_payload":DECISION_PAYLOAD,"artifact_paths":ARTIFACT_PATHS,
  "hard_defect_profile_id":PROFILE,"detected_triggers":TRIGGERS,
 }
 out=v9.route(state,repo_root=root)
 if out.get("status")!="ABSTAIN__P1_VERIFIED_STEP_BINDINGS_REQUIRED":
  return _fail("MISSING_EVIDENCE_STATE_DID_NOT_ABSTAIN",router_result=out)
 if out.get("positive_certification_authorized") is not False:
  return _fail("MISSING_EVIDENCE_STATE_POSITIVE_AUTHORITY")
 if out.get("blocking_reason")!="PROFESSIONAL_STEP_BINDINGS_REQUIRED":
  return _fail("MISSING_EVIDENCE_BLOCKING_REASON_DRIFT",router_result=out)

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__CONSTRUCTIVE_ADMISSIBLE_R12_INPUT_WITH_UNRESOLVED_TYPED_EVIDENCE__CURRENT_UNIVERSAL_ADEQUACY_PREDICATE_FALSIFIED__SPEC_REPAIR_REQUIRED",
  "claim_id":CLAIM_ID,"scope_claim_id":SCOPE_ID,
  "real_task_run_context_sha256":run_context,
  "same_real_task_evidence_chain_verified":True,
  "whole_leaf_no_filters_or_exclusions_verified":True,
  "r2_unresolved_material_premise_abstention_rule_verified":True,
  "observed_router_status":out.get("status"),
  "observed_blocking_reason":out.get("blocking_reason"),
  "constructive_counterexample_proved":True,
  "original_universal_predicate_falsified":True,
  "specification_repair_authorized":True,
  "recommended_repaired_predicate":"FOR_ALL_ADMISSIBLE_INPUTS__IF_CLAIM_SEMANTICS_SCOPE_UNCERTAINTY_AND_ALL_DECISION_RELEVANT_DEFEATERS_ARE_RESOLVED_WITH_TYPED_EVIDENCE_THEN_POSITIVE_CERTIFICATION_MAY_BE_AUTHORIZED__OTHERWISE_EXPLICIT_FAIL_CLOSED_ABSTENTION_WITH_MINIMUM_BLOCKING_CUT__PLUS_NONVACUOUS_REAL_POSITIVE_ROUTE",
  "new_primitive_required":False,
  "semantic_property_truth_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,
 }
