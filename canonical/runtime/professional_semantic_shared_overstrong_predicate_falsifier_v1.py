"""Batch falsifier for the 12 overstrong professional semantic success predicates.

All twelve current professional semantic leaves share the same generic
acceptance formula and whole-admissible-input universal quantification. The
independently verified R12 two-world counterexample supplies one admissible
professional input on which that generic acceptance formula is false while the
mission-correct action is fail-closed abstention with zero progress credit.

Because the target predicate text is identical across all twelve semantic
leaves and their whole-leaf domains have no filters/exclusions, the same input
falsifies the shared universal-success predicate shape for every semantic leaf.

This does NOT prove the repaired semantic leaves. It proves the existing shared
universal-success specification is not a valid mandatory correctness gate and
must be split into:
1. universal certification safety; and
2. separate positive-adequacy coverage/capability evidence.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_semantic_totality_claim_pack_v3 as pack_v3
from canonical.runtime import professional_r12_overstrong_predicate_counterexample_v1 as r12_ce

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_SHARED_OVERSTRONG_PREDICATE_FALSIFIER_V1"
EXPECTED_ACCEPTANCE="DOMAIN_SPECIFIC_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_AND_ALL_ROOT_RELEVANT_DEFEATERS_RESOLVED_WITH_TYPED_EVIDENCE"
EXPECTED_QUANTIFIER="FOR_ALL_ADMISSIBLE_INPUTS_IN_VERIFIED_WHOLE_LEAF_SCOPE"
PINS={
 "manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 "counterexample_verify":("canonical/verification/PROFESSIONAL_R12_OVERSTRONG_PREDICATE_COUNTEREXAMPLE_INDEPENDENT_VERIFY_20261011_V1.json","e9e945cb31be117de8c0634391ebbc724d31c26d"),
 "mission":("canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json","13c470645b037bbb46245c687dd35197b420d51a"),
}

def _blob(p:Path)->str:
 d=p.read_bytes();return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _load(root:Path,key:str)->dict[str,Any]:
 rel,expected=PINS[key];p=root/rel
 if not p.is_file() or p.is_symlink():raise ValueError("PIN_MISSING:"+key)
 got=_blob(p)
 if got!=expected:raise ValueError("PIN_BLOB_DRIFT:"+key+":"+got)
 o=json.loads(p.read_text(encoding="utf-8"))
 if not isinstance(o,dict):raise ValueError("PIN_NOT_OBJECT:"+key)
 return o

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "semantic_leaf_count":0,"overstrong_predicate_falsified_count":0,
  "all_12_existing_universal_success_predicates_falsified":False,
  "repaired_semantic_property_truth_proved_count":0,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

def evaluate(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 try:
  manifest=_load(root,"manifest");cev=_load(root,"counterexample_verify");mission=_load(root,"mission")
 except Exception as exc:return _fail(type(exc).__name__+":"+str(exc))
 if mission.get("correctness_rule")!="FAIL_CLOSED_NO_PROGRESS_CREDIT_WITHOUT_SOUND_VERIFICATION":
  return _fail("MISSION_CORRECTNESS_RULE_DRIFT")
 if not str(cev.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE"):
  return _fail("R12_COUNTEREXAMPLE_NOT_INDEPENDENT_PASS")
 truth=cev.get("truth") or {}
 for k in ("counterexample_admissible","visible_information_identical","hypothesis_set_complete",
           "authorized_observation_library_complete","safe_fail_closed_policy_exists",
           "mission_correct_abstention","stronger_universal_predicate_falsified"):
  if truth.get(k) is not True:return _fail("COUNTEREXAMPLE_PREMISE_MISSING:"+k)
 if truth.get("common_positive_semantic_resolution_policy_exists") is not False:
  return _fail("COUNTEREXAMPLE_COMMON_POSITIVE_POLICY_BOUNDARY_DRIFT")

 pack=pack_v3.verify(repo_root=root)
 if pack.get("pass") is not True or pack.get("semantic_claim_count")!=12:
  return _fail("CURRENT_V3_SEMANTIC_CLAIM_PACK_NOT_PASS",pack_reason=pack.get("reason"))
 claims=pack.get("claims")
 if not isinstance(claims,list) or len(claims)!=12:return _fail("CURRENT_V3_CLAIM_SET_INVALID")

 roots=manifest.get("roots")
 if not isinstance(roots,list) or len(roots)!=12:return _fail("MANIFEST_ROOT_SET_INVALID")
 semantic_by_leaf={}
 for row in roots:
  if not isinstance(row,Mapping):return _fail("MANIFEST_ROOT_ROW_INVALID")
  leaf=row.get("semantic_leaf")
  if not isinstance(leaf,Mapping):return _fail("MANIFEST_SEMANTIC_LEAF_MISSING")
  semantic_by_leaf[leaf.get("id")]=leaf

 rows=[]
 for claim in claims:
  if not isinstance(claim,Mapping):return _fail("SEMANTIC_CLAIM_ROW_INVALID")
  leaf_id=claim.get("leaf_id")
  target=claim.get("target_predicate")
  semantics=claim.get("semantics")
  frozen=claim.get("frozen_claim")
  leaf=semantic_by_leaf.get(leaf_id)
  if not isinstance(leaf,Mapping):return _fail("CLAIM_LEAF_NOT_IN_MANIFEST:"+str(leaf_id))
  if not isinstance(target,Mapping) or not isinstance(semantics,Mapping) or not isinstance(frozen,Mapping):
   return _fail("CLAIM_SEMANTICS_SHAPE_INVALID:"+str(leaf_id))
  if leaf.get("acceptance")!=EXPECTED_ACCEPTANCE:return _fail("MANIFEST_ACCEPTANCE_NOT_SHARED:"+str(leaf_id))
  if target.get("acceptance")!=EXPECTED_ACCEPTANCE:return _fail("CLAIM_ACCEPTANCE_NOT_SHARED:"+str(leaf_id))
  if target.get("quantification")!=EXPECTED_QUANTIFIER:return _fail("CLAIM_NOT_WHOLE_DOMAIN_UNIVERSAL:"+str(leaf_id))
  if semantics.get("false_when")!="EXISTS_ADMISSIBLE_INPUT_IN_WHOLE_LEAF_SCOPE_FOR_WHICH_THE_ACCEPTANCE_PROPERTY_FAILS":
   return _fail("CLAIM_FALSE_CONDITION_DRIFT:"+str(leaf_id))
  if frozen.get("claim_kind")!="PROPERTY_CERTIFICATE":return _fail("CLAIM_KIND_DRIFT:"+str(leaf_id))
  rows.append({
   "leaf_id":leaf_id,"root_id":claim.get("root_id"),
   "claim_id":frozen.get("claim_id"),
   "shared_acceptance":True,"whole_domain_universal":True,
   "falsified_by_shared_constructive_counterexample":True,
   "repaired_property_truth_proved":False,
  })

 leaf_ids=[r["leaf_id"] for r in rows]
 if len(set(leaf_ids))!=12:return _fail("SEMANTIC_LEAF_IDENTITIES_NOT_UNIQUE")
 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__ALL_12_CURRENT_PROFESSIONAL_SEMANTIC_UNIVERSAL_SUCCESS_PREDICATES_SHARE_ONE_FALSIFIED_OVERSTRONG_SPECIFICATION__TRUTH_REPAIR_REQUIRED",
  "semantic_leaf_count":12,
  "overstrong_predicate_falsified_count":12,
  "all_12_existing_universal_success_predicates_falsified":True,
  "shared_acceptance":EXPECTED_ACCEPTANCE,
  "shared_quantifier":EXPECTED_QUANTIFIER,
  "counterexample_receipt_path":PINS["counterexample_verify"][0],
  "semantic_leaves":sorted(rows,key=lambda x:x["leaf_id"]),
  "mission_correctness_preserved":True,
  "required_repair":{
   "universal_safety":"FOR_EACH_ADMISSIBLE_INPUT__POSITIVE_PROPERTY_OR_PROGRESS_CREDIT_ONLY_AFTER_SOUND_SCOPE_MATCHED_TYPED_VERIFICATION__OTHERWISE_FAIL_CLOSED_WITH_EXPLICIT_BLOCKER_AND_ZERO_POSITIVE_CREDIT",
   "positive_adequacy":"TRACK_AND_IMPROVE_WHICH_ADMISSIBLE_INPUTS_CAN_BE_POSITIVELY_RESOLVED__PROVE_OR_MEASURE_SCOPE_COMPLETE_COVERAGE_ONLY_WHEN_THE_TARGET_SCOPE_IS_FINITE_OR_HAS_A_SOUND_UNIVERSAL_CONSTRUCTION",
   "separation_rule":"DO_NOT_TREAT_UNRESOLVABLE_OR_INFORMATION_THEORETICALLY_EXTERNAL_INPUTS_AS_CORRECTNESS_FAILURES_WHEN_FAIL_CLOSED_ABSTENTION_IS_MISSION_CORRECT__DO_NOT_TREAT_ABSTENTION_AS_CAPABILITY_SUCCESS_EITHER",
  },
  "repaired_semantic_property_truth_proved_count":0,
  "property_credit_delta":0,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,
  "hard_nonclaims":[
   "NO_REPAIRED_SEMANTIC_LEAF_PROPERTY_TRUTH_GRANTED",
   "NO_POSITIVE_ADEQUACY_COVERAGE_INCREASE_CLAIMED",
   "NO_QUALITY_ACCEPTANCE_PROMOTION_OR_TERMINAL_AUTHORITY"
  ],
 }

if __name__=="__main__":
 print(json.dumps(evaluate(),indent=2,sort_keys=True))
