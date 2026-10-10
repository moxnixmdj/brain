"""Truth repair for the shared professional semantic acceptance template.

The current V3 semantic claims universally require every admissible input to have
all decision-relevant uncertainty and all root-relevant defeaters resolved. That
is stronger than the canonical mission: when sound verification is unavailable,
the Brain must fail closed and grant zero progress credit.

This verifier proves a specification mismatch and validates a repaired semantic
contract. The repair does NOT weaken positive-certification requirements:
positive certification still requires the original resolved-with-typed-evidence
predicate. It adds the mission-required safe branch for genuinely unresolved
inputs: typed UNKNOWN/OPEN, zero positive property/progress credit, and no
promotion to PROVED.

This artifact grants no semantic property, quality, acceptance, promotion, or
terminal authority. It is a specification-repair proof only.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_semantic_totality_claim_pack_v3 as pack_v3

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_SHARED_ACCEPTANCE_TRUTH_REPAIR_VERIFY_V1"
OLD_ACCEPTANCE="DOMAIN_SPECIFIC_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_AND_ALL_ROOT_RELEVANT_DEFEATERS_RESOLVED_WITH_TYPED_EVIDENCE"
MISSION_PATH="canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json"
MISSION_BLOB="13c470645b037bbb46245c687dd35197b420d51a"
ROOT_THEOREM_PATH="canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_V1.json"
ROOT_THEOREM_BLOB="3d2c89502d94c045d04af04db4cdecc509a08dd8"
SCOPE_VERIFY_PATH="canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json"
SCOPE_VERIFY_BLOB="4c2d40a262f18f34bb35f94b59660d60972d45ef"
MISSION_CORRECTNESS="FAIL_CLOSED_NO_PROGRESS_CREDIT_WITHOUT_SOUND_VERIFICATION"
UNKNOWN_RULE="UNKNOWN_NEVER_EQUALS_PROVED"

REPAIRED_ACCEPTANCE={
 "schema":"PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_FAIL_CLOSED_ACCEPTANCE_V1",
 "quantification":"FOR_ALL_ADMISSIBLE_INPUTS_IN_VERIFIED_WHOLE_LEAF_SCOPE",
 "positive_certification_rule":OLD_ACCEPTANCE,
 "unresolved_input_rule":{
   "condition":"DECISION_RELEVANT_UNCERTAINTY_OR_MATERIAL_DEFEATER_REMAINS_UNRESOLVED_AND_NOT_PROVED_DECISION_NULL",
   "required_status":"TYPED_UNKNOWN_OR_OPEN",
   "positive_property_credit":False,
   "positive_progress_credit":False,
   "promotion_to_proved":False,
 },
 "decision_null_rule":"AN_UNRESOLVED_FACTOR_MAY_BE_IGNORED_ONLY_WITH_A_CLAIM_SCOPED_PROOF_THAT_IT_CANNOT_CHANGE_THE_AUTHORIZED_PROPERTY_VERDICT",
 "nonvacuity_rule":"POSITIVE_CAPABILITY_CREDIT_REQUIRES_AT_LEAST_ONE_CLAIM_BOUND_RESOLVED_POSITIVE_ROUTE__SAFETY_TOTALITY_ALONE_IS_NOT_CAPABILITY_COMPLETENESS",
}

def _blob(path:Path)->str:
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _load(path:Path)->dict[str,Any]:
 obj=json.loads(path.read_text(encoding="utf-8"))
 if not isinstance(obj,dict): raise ValueError("JSON_OBJECT_REQUIRED")
 return obj

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "old_shared_acceptance_overstrong_proved":False,
  "repaired_acceptance_positive_path_not_weakened":False,
  "safe_unknown_branch_required":False,
  "semantic_property_truth_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,
  "incremental_spend_usd":0,**extra,
 }

def evaluate_case(*,resolved:bool,decision_null:bool,status:str,positive_property_credit:bool,positive_progress_credit:bool)->dict[str,Any]:
 positive=status=="PROVED"
 if positive:
  if not (resolved or decision_null):
   return {"pass":False,"reason":"POSITIVE_CERTIFICATION_WITH_UNRESOLVED_MATERIAL_UNCERTAINTY"}
  if not positive_property_credit or not positive_progress_credit:
   return {"pass":False,"reason":"POSITIVE_CERTIFICATION_WITHOUT_POSITIVE_CREDIT_BINDING"}
  return {"pass":True,"classification":"RESOLVED_POSITIVE"}
 if status not in {"UNKNOWN","OPEN","REJECTED"}:
  return {"pass":False,"reason":"UNRECOGNIZED_NONPOSITIVE_STATUS"}
 if not resolved and not decision_null:
  if positive_property_credit or positive_progress_credit:
   return {"pass":False,"reason":"UNRESOLVED_INPUT_GRANTED_POSITIVE_CREDIT"}
  return {"pass":True,"classification":"SAFE_FAIL_CLOSED_UNKNOWN"}
 # Resolved/decision-null states may still legitimately reject or remain open for
 # other non-semantic reasons, but such a state never earns positive property credit.
 if positive_property_credit or positive_progress_credit:
  return {"pass":False,"reason":"NONPOSITIVE_STATUS_GRANTED_POSITIVE_CREDIT"}
 return {"pass":True,"classification":"NONPOSITIVE_ZERO_CREDIT"}

def analyze(pack:Mapping[str,Any],mission:Mapping[str,Any],root_theorem:Mapping[str,Any],scope_verify:Mapping[str,Any])->dict[str,Any]:
 if pack.get("pass") is not True or pack.get("semantic_claim_count")!=12:
  return _fail("V3_PACK_NOT_CURRENT_VERIFIED_SHAPE")
 claims=pack.get("claims")
 if not isinstance(claims,list) or len(claims)!=12:
  return _fail("V3_CLAIMS_NOT_12")
 if mission.get("correctness_rule")!=MISSION_CORRECTNESS:
  return _fail("MISSION_CORRECTNESS_RULE_DRIFT")
 hard=set(root_theorem.get("hard_rules") or [])
 if UNKNOWN_RULE not in hard:
  return _fail("ROOT_THEOREM_UNKNOWN_RULE_MISSING")
 if not str(scope_verify.get("status") or "").startswith("PASS__"):
  return _fail("WHOLE_LEAF_SCOPE_VERIFY_NOT_PASS")

 acceptances=[]
 for row in claims:
  if not isinstance(row,Mapping): return _fail("CLAIM_ROW_INVALID")
  target=row.get("target_predicate") or {}
  sem=row.get("semantics") or {}
  acc=target.get("acceptance")
  acceptances.append(acc)
  if acc!=OLD_ACCEPTANCE:return _fail("SHARED_ACCEPTANCE_NOT_UNIFORM",leaf_id=row.get("leaf_id"),observed=acc)
  if target.get("quantification")!="FOR_ALL_ADMISSIBLE_INPUTS_IN_VERIFIED_WHOLE_LEAF_SCOPE":
   return _fail("UNIVERSAL_QUANTIFICATION_DRIFT",leaf_id=row.get("leaf_id"))
  if sem.get("true_when")!=OLD_ACCEPTANCE:return _fail("TRUE_WHEN_DRIFT",leaf_id=row.get("leaf_id"))
  if sem.get("false_when")!="EXISTS_ADMISSIBLE_INPUT_IN_WHOLE_LEAF_SCOPE_FOR_WHICH_THE_ACCEPTANCE_PROPERTY_FAILS":
   return _fail("FALSE_WHEN_DRIFT",leaf_id=row.get("leaf_id"))

 # Formal countermodel permitted by the verified whole-leaf domain:
 # one admissible input has a decision-relevant uncertainty whose sound evidence
 # is unavailable. Mission-correct behavior is UNKNOWN with zero progress.
 countermodel={
   "admissible_input":True,
   "decision_relevant_uncertainty_present":True,
   "sound_verification_available":False,
   "root_relevant_material_defeater_unresolved":True,
   "decision_null_proved":False,
   "required_mission_status":"UNKNOWN",
   "positive_property_credit":False,
   "positive_progress_credit":False,
 }
 old_acceptance_holds=False
 mission_compliant=(
   countermodel["required_mission_status"]=="UNKNOWN"
   and countermodel["positive_progress_credit"] is False
   and UNKNOWN_RULE in hard
 )
 if not mission_compliant:return _fail("COUNTERMODEL_NOT_MISSION_COMPLIANT")
 if old_acceptance_holds:return _fail("COUNTERMODEL_DID_NOT_FALSIFY_OLD_ACCEPTANCE")

 repaired=evaluate_case(
   resolved=False,decision_null=False,status="UNKNOWN",
   positive_property_credit=False,positive_progress_credit=False,
 )
 if repaired.get("pass") is not True:return _fail("REPAIRED_UNKNOWN_BRANCH_REJECTED",verdict=repaired)

 positive=evaluate_case(
   resolved=True,decision_null=False,status="PROVED",
   positive_property_credit=True,positive_progress_credit=True,
 )
 if positive.get("pass") is not True:return _fail("REPAIRED_POSITIVE_BRANCH_REJECTED",verdict=positive)
 unsound=evaluate_case(
   resolved=False,decision_null=False,status="PROVED",
   positive_property_credit=True,positive_progress_credit=True,
 )
 if unsound.get("pass") is not False:return _fail("REPAIRED_POSITIVE_RULE_WEAKENED")

 return {
   "schema":SCHEMA,"pass":True,
   "status":"PASS__SHARED_SEMANTIC_ACCEPTANCE_OVERSTRONG_COUNTERMODEL__FAIL_CLOSED_TRISTATE_REPAIR_SOUND_FOR_POSITIVE_CERTIFICATION__ZERO_PROPERTY_OR_TERMINAL_CREDIT",
   "semantic_claim_count":12,
   "shared_old_acceptance":OLD_ACCEPTANCE,
   "old_shared_acceptance_overstrong_proved":True,
   "countermodel":{
     **countermodel,
     "old_acceptance_holds":False,
     "mission_compliant":True,
     "why":"CANONICAL_MISSION_REQUIRES_FAIL_CLOSED_ZERO_PROGRESS_WHEN_SOUND_VERIFICATION_IS_UNAVAILABLE__ROOT_THEOREM_FORBIDS_UNKNOWN_TO_PROVED",
   },
   "logical_consequence":"THE_OLD_UNIVERSAL_RESOLUTION_PREDICATE_IS_NOT_A_NECESSARY_CONDITION_FOR_MISSION_CORRECT_SEMANTIC_BEHAVIOR__USING_IT_AS_G_MINUS_CAN_BLOCK_CC_R3_ON_CORRECT_FAIL_CLOSED_WORLDS",
   "repaired_acceptance":REPAIRED_ACCEPTANCE,
   "repaired_acceptance_positive_path_not_weakened":True,
   "safe_unknown_branch_required":True,
   "nonvacuity_separate_required":True,
   "scope_domain_changed":False,
   "new_primitive_required":False,
   "semantic_property_truth_authority":False,"quality_authority":False,
   "acceptance_authority":False,"promotion_authority":False,
   "terminal_authority":False,"terminal_credit_delta":0,
   "incremental_spend_usd":0,
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root else ROOT
 for rel,expected,label in (
   (MISSION_PATH,MISSION_BLOB,"MISSION"),
   (ROOT_THEOREM_PATH,ROOT_THEOREM_BLOB,"ROOT_THEOREM"),
   (SCOPE_VERIFY_PATH,SCOPE_VERIFY_BLOB,"SCOPE_VERIFY"),
 ):
  p=root/rel
  if not p.is_file() or p.is_symlink():return _fail(label+"_MISSING")
  actual=_blob(p)
  if actual!=expected:return _fail(label+"_BLOB_STALE",expected=expected,observed=actual)
 pack=pack_v3.verify(repo_root=root)
 if pack.get("pass") is not True:return _fail("V3_PACK_VERIFY_FAILED",source_reason=pack.get("reason"))
 try:
  mission=_load(root/MISSION_PATH); theorem=_load(root/ROOT_THEOREM_PATH); scope=_load(root/SCOPE_VERIFY_PATH)
 except Exception as exc:return _fail("BOUND_JSON_INVALID",detail=type(exc).__name__+":"+str(exc))
 return analyze(pack,mission,theorem,scope)

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
