"""R10 execution-leaf property-truth verifier V1.

This verifier discharges the exact manifest acceptance for
PQ::R10_ANALYSIS_DECISION::EXECUTION:

  RUN_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_CASES_ON_EXACT_ARTIFACT_OR_RUNTIME_BYTES_AND_BIND_OBSERVED_OUTCOMES_TO_THE_ROOT_CONTRACT

It recomputes the current R10 execution guard and structural proof-slot behavior
over a fixed challenge matrix. It does NOT prove R10 semantic sufficiency,
defeater-detection completeness, R10 root closure, professional quality,
acceptance, promotion, or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_r10_execution_guard_v1 as guard
from canonical.runtime import professional_quality_r10_proof_slot_verifier_v1 as slots

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R10_EXECUTION_PROPERTY_TRUTH_VERIFY_V1"
LEAF_ID="PQ::R10_ANALYSIS_DECISION::EXECUTION"
ROOT_ID="R10_ANALYSIS_DECISION"
CLAIM_ID=guard.CLAIM_ID
ACCEPTANCE=(
 "RUN_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_CASES_ON_EXACT_ARTIFACT_OR_RUNTIME_BYTES_"
 "AND_BIND_OBSERVED_OUTCOMES_TO_THE_ROOT_CONTRACT"
)

PINS={
 "manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 "profile":("canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json","f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"),
 "catalog":("canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json","8b92e5cf76f767054f55414b87014e03d43460b8"),
 "constitution":("canonical/governance/PROFESSIONAL_QUALITY_R10_DECISION_CONSTITUTION_20261010_V1.json","a087db2645b03e589965d50eb51d32a3049dc2fe"),
 "scope_gate_verify":("canonical/verification/PROFESSIONAL_QUALITY_R10_EXECUTION_WHOLE_LEAF_V2_GATE_VERIFY_20261010_V1.json","afeeac2ffcdf2f858b5560299396fe450193e5df"),
 "guard_runtime":("canonical/runtime/professional_quality_r10_execution_guard_v1.py","83ae7bc81660bd4be7f66b9454de5d007c0db959"),
 "proof_slot_runtime":("canonical/runtime/professional_quality_r10_proof_slot_verifier_v1.py","04957e2e385f8169e7d8aff5b0e1f2009e848666"),
}
_HEX=set("0123456789abcdef")

def _blob(path:Path)->str:
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _load(path:Path)->dict[str,Any]:
 value=json.loads(path.read_text(encoding="utf-8"))
 if not isinstance(value,dict): raise ValueError("NOT_OBJECT")
 return value

def _sha64(ch:str)->str:
 return ch*64

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,"claim_id":CLAIM_ID,
  "leaf_property_truth_authority":False,
  "detection_completeness_proved":False,
  "r10_semantic_leaf_closed":False,"r10_root_closed":False,
  "semantic_truth_authority":False,"execution_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
 }

def _leaf_acceptance(manifest:Mapping[str,Any])->str|None:
 for row in manifest.get("roots") or []:
  if not isinstance(row,Mapping) or row.get("root_id")!=ROOT_ID: continue
  leaf=row.get("execution_leaf")
  if isinstance(leaf,Mapping) and leaf.get("id")==LEAF_ID:
   value=leaf.get("acceptance")
   return value if isinstance(value,str) else None
 return None

def _decision_contract()->dict[str,Any]:
 return {
  "schema":guard.DECISION_SCHEMA,
  "pass":True,
  "reduction_mode":"LOSSLESS_IDENTITY__NO_UNVERIFIED_OMISSION",
  "omitted_evidence":[],
  "source_contract_sha256":_sha64("a"),
  "representation_sha256":_sha64("b"),
 }

def _minimum_contract()->dict[str,Any]:
 return {
  "schema":guard.MINIMUM_INFORMATION_SCHEMA,
  "requests":[{
    "blocker":"MISSING_FACT",
    "broad_acquisition_forbidden_without_minimality_proof":True,
    "proof_or_existing_receipt_precedes_new_reality":True,
  }],
 }

def _clean_context()->dict[str,Any]:
 return {
  "target":{
   "target_spec_sha256":_sha64("1"),
   "hard_constraints_sha256":_sha64("2"),
   "freeze_receipt_sha256":_sha64("3"),
  },
  "uncertainty_claims":[{
   "id":"u1","type":"MODEL_UNCERTAINTY","source_type":"MODEL_UNCERTAINTY",
  }],
  "decision_policy":{
   "aggregation_mode":"PARETO_ONLY",
   "risk_threshold_required":False,
   "precommit_receipt_sha256":_sha64("4"),
  },
  "veto_constraints":[{
   "id":"hard-no-fabrication","noncompensatory":True,"satisfied":True,
  }],
  "analysis_models":[
   {"id":"m1","decision":"candidate-a"},
   {"id":"m2","decision":"candidate-a"},
  ],
  "evidence_packet":{
   "declared_evidence_ids":["e1","e2"],
   "included_evidence_ids":["e1","e2"],
   "omissions":[],
   "packet_sha256":_sha64("5"),
   "declared_basis_sha256":_sha64("6"),
  },
  "stopping_rule":{
   "rule_sha256":_sha64("7"),
   "precommit_receipt_sha256":_sha64("8"),
   "frozen_before_outcome_reveal":True,
  },
  "quality_claim":{"claim_level":"RELATIVE_OR_SCOPED"},
 }

def _guard(
 profile:Mapping[str,Any],catalog:Mapping[str,Any],constitution:Mapping[str,Any],*,
 decision:Mapping[str,Any]|None=None,minimum:Mapping[str,Any]|None=None,
 context:Mapping[str,Any]|None=None,detected:tuple[str,...]=(),
 near:Mapping[str,bool]|None=None,unmapped:bool=False,claim_id:str=CLAIM_ID,
)->dict[str,Any]:
 return guard.evaluate(
  claim_id=claim_id,
  decision_contract=decision or _decision_contract(),
  minimum_information_contract=minimum or _minimum_contract(),
  execution_profile=profile,
  defeater_catalog=catalog,
  detected_defeater_ids=detected,
  near_miss_signals=near or {},
  constitution=constitution,
  case_context=context or _clean_context(),
  unmapped_material_false_certification_defeater=unmapped,
 )

def _slot_mutations()->dict[str,tuple[dict[str,Any],dict[str,Any],dict[str,Any]]]:
 decision=_decision_contract(); minimum=_minimum_contract(); base=_clean_context()
 out={}
 c=deepcopy(base);c["target"]["freeze_receipt_sha256"]=None
 out["target_and_hard_constraints_frozen"]=(deepcopy(decision),deepcopy(minimum),c)
 d=deepcopy(decision);d["representation_sha256"]=None
 out["decision_state_lossless"]=(d,deepcopy(minimum),deepcopy(base))
 c=deepcopy(base);c["uncertainty_claims"][0]["type"]="UNTYPED_UNKNOWN"
 out["uncertainty_semantics_typed"]=(deepcopy(decision),deepcopy(minimum),c)
 c=deepcopy(base);c["decision_policy"]["precommit_receipt_sha256"]=None
 out["aggregation_and_risk_policy_precommitted"]=(deepcopy(decision),deepcopy(minimum),c)
 c=deepcopy(base);c["veto_constraints"][0]["satisfied"]=False
 out["veto_constraints_preserved"]=(deepcopy(decision),deepcopy(minimum),c)
 c=deepcopy(base);c["analysis_models"][1]["decision"]="candidate-b"
 out["model_or_analysis_multiplicity_resolved_or_escalated"]=(deepcopy(decision),deepcopy(minimum),c)
 c=deepcopy(base);c["evidence_packet"]["included_evidence_ids"]=["e1"]
 out["evidence_packet_complete"]=(deepcopy(decision),deepcopy(minimum),c)
 c=deepcopy(base);c["stopping_rule"]["precommit_receipt_sha256"]=None
 out["stopping_rule_precommitted"]=(deepcopy(decision),deepcopy(minimum),c)
 c=deepcopy(base);c["quality_claim"]={"claim_level":"ABSOLUTE_PROFESSIONAL_EXCELLENCE"}
 out["absolute_floor_not_inferred_from_weak_baseline"]=(deepcopy(decision),deepcopy(minimum),c)
 return out

def evaluate_documents(
 manifest:Mapping[str,Any],profile:Mapping[str,Any],catalog:Mapping[str,Any],
 constitution:Mapping[str,Any],scope_gate_verify:Mapping[str,Any],
)->dict[str,Any]:
 if _leaf_acceptance(manifest)!=ACCEPTANCE:
  return _fail("R10_EXECUTION_ACCEPTANCE_DRIFT",observed_acceptance=_leaf_acceptance(manifest))
 if scope_gate_verify.get("leaf_id")!=LEAF_ID or scope_gate_verify.get("claim_id")!=CLAIM_ID:
  return _fail("R10_SCOPE_GATE_IDENTITY_MISMATCH")
 if not str(scope_gate_verify.get("status") or "").startswith("PASS__"):
  return _fail("R10_SCOPE_GATE_NOT_PASS")
 consequence=scope_gate_verify.get("consequence") or {}
 if consequence.get("whole_leaf_domain_equivalence_proved") is not True or consequence.get("whole_leaf_scope_complete") is not True:
  return _fail("R10_WHOLE_LEAF_SCOPE_NOT_COMPLETE")
 if consequence.get("property_truth_ready") is not True or consequence.get("leaf_property_truth_authority") is not False:
  return _fail("R10_PROPERTY_READINESS_BOUNDARY_INVALID")

 positive=_guard(profile,catalog,constitution)
 positive_ok=(
  positive.get("pass") is True
  and positive.get("status")=="PASS__R10_EXECUTION_GUARD_ELIGIBLE_FOR_SCOPED_CERTIFICATE_VERIFICATION"
  and positive.get("ordinary_certificate_path_allowed") is True
  and len(positive.get("proof_slots_satisfied") or [])==len(slots.REQUIRED_SLOTS)
  and positive.get("whole_leaf_property_truth_proved") is False
  and positive.get("quality_authority") is False
 )

 known={}
 for did in sorted(guard.KNOWN_R10_DEFEATERS):
  out=_guard(profile,catalog,constitution,detected=(did,))
  known[did]=(
   out.get("pass") is False
   and out.get("status")=="ABSTAIN_OR_ESCALATE__KNOWN_R10_DEFEATER_ACTIVE"
   and out.get("ordinary_certificate_path_allowed") is False
  )

 near={}
 for signal,trigger in sorted(guard.NEAR_MISS_TO_TRIGGER.items()):
  out=_guard(profile,catalog,constitution,near={signal:True})
  near[signal]=(
   out.get("pass") is False
   and out.get("status")=="ESCALATE__R10_NEAR_MISS_TRIGGER"
   and trigger in set(out.get("active_escalation_triggers") or [])
   and out.get("ordinary_certificate_path_allowed") is False
  )

 unknown=_guard(profile,catalog,constitution,detected=("C999_FRESH_DECISION_ATTACK",))
 unknown_ok=(
  unknown.get("status")=="ESCALATE__UNMAPPED_DETECTED_DEFEATER"
  and unknown.get("required_trigger")=="UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER"
  and unknown.get("ordinary_certificate_path_allowed") is False
 )
 unmapped=_guard(profile,catalog,constitution,unmapped=True)
 unmapped_ok=(
  unmapped.get("status")=="ESCALATE__UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER"
  and unmapped.get("ordinary_certificate_path_allowed") is False
 )

 slot_results={}
 for name,(decision,minimum,context) in _slot_mutations().items():
  out=slots.evaluate(
   claim_id=CLAIM_ID,constitution=constitution,decision_contract=decision,
   minimum_information_contract=minimum,case_context=context,
  )
  slot_results[name]=(
   out.get("pass") is False
   and out.get("status")=="OPEN__R10_STRUCTURAL_PROOF_SLOT_REQUIRED"
   and name in set(out.get("missing_slots") or [])
  )

 lossy=deepcopy(_decision_contract());lossy["reduction_mode"]="UNVERIFIED_SUMMARY"
 lossy_out=_guard(profile,catalog,constitution,decision=lossy)
 omitted=deepcopy(_decision_contract());omitted["omitted_evidence"]=["TAIL_RISK"]
 omitted_out=_guard(profile,catalog,constitution,decision=omitted)
 broad=deepcopy(_minimum_contract());broad["requests"][0]["broad_acquisition_forbidden_without_minimality_proof"]=False
 broad_out=_guard(profile,catalog,constitution,minimum=broad)
 claim_out=_guard(profile,catalog,constitution,claim_id="0"*64)
 unsafe_contract_checks={
  "LOSSY_DECISION_REJECTED":lossy_out.get("reason")=="DECISION_CONTRACT_NOT_LOSSLESS",
  "OMITTED_DECISION_EVIDENCE_REJECTED":omitted_out.get("reason")=="DECISION_CONTRACT_OMITS_EVIDENCE",
  "BROAD_ACQUISITION_WEAKENING_REJECTED":broad_out.get("reason")=="MINIMUM_INFORMATION_BROAD_ACQUISITION_NOT_FORBIDDEN",
  "CLAIM_SUBSTITUTION_REJECTED":claim_out.get("reason")=="CLAIM_ID_MISMATCH",
 }

 checks={
  "POSITIVE_CLEAN_PATH_BOUND_TO_ROOT_CONTRACT":positive_ok,
  "ALL_17_KNOWN_R10_DEFEATERS_BLOCK":all(known.values()) and len(known)==17,
  "ALL_5_NEAR_MISS_CLASSES_ESCALATE":all(near.values()) and len(near)==5,
  "UNKNOWN_DETECTED_DEFEATER_ESCALATES":unknown_ok,
  "UNMAPPED_MATERIAL_FALSE_CERTIFICATION_ESCALATES":unmapped_ok,
  "ALL_9_STRUCTURAL_PROOF_SLOTS_FAIL_CLOSED_WHEN_MISSING":all(slot_results.values()) and len(slot_results)==9,
  "UNSAFE_CONTRACT_VARIANTS_FAIL_CLOSED":all(unsafe_contract_checks.values()),
 }
 if not all(checks.values()):
  return _fail(
   "R10_EXECUTION_PROPERTY_CHALLENGE_FAILED",
   checks=checks,known_defeater_results=known,near_miss_results=near,
   proof_slot_results=slot_results,unsafe_contract_checks=unsafe_contract_checks,
  )

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__R10_EXECUTION_MANIFEST_ACCEPTANCE_OBSERVED_ON_EXACT_BOUND_RUNTIME_BEHAVIOR__ONE_LEAF_PROPERTY_TRUTH_ONLY",
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,"claim_id":CLAIM_ID,
  "manifest_acceptance":ACCEPTANCE,
  "checks":checks,
  "observed_case_counts":{
   "positive":1,"known_adversarial":17,"near_miss":5,
   "unknown_detected":1,"unmapped_material":1,"missing_structural_slots":9,
   "unsafe_contract_variants":4,
   "total":38,
  },
  "leaf_property_truth_authority":True,
  "property_truth_basis":"MANIFEST_CASE_BASED_EXECUTION_ACCEPTANCE_ON_EXACT_BOUND_RUNTIME_BEHAVIOR",
  "detection_completeness_proved":False,
  "r10_semantic_leaf_closed":False,
  "r10_root_closed":False,
  "semantic_truth_authority":False,
  "execution_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 docs={}
 for key,(rel,expected) in PINS.items():
  p=root/rel
  if not p.is_file() or p.is_symlink(): return _fail(key.upper()+"_MISSING")
  if _blob(p)!=expected: return _fail(key.upper()+"_BLOB_STALE",observed_blob=_blob(p))
  if key in {"manifest","profile","catalog","constitution","scope_gate_verify"}:
   try: docs[key]=_load(p)
   except Exception: return _fail(key.upper()+"_JSON_INVALID")
 return evaluate_documents(
  docs["manifest"],docs["profile"],docs["catalog"],docs["constitution"],docs["scope_gate_verify"]
 )

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
