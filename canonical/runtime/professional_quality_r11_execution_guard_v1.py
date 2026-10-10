"""Fail-closed execution guard for R11 adaptive integrity/security.

This guard is deliberately detection-conditional.  It enforces that any
detected canonical R11 defeater, security near-miss, or unmapped material
false-certification signal blocks the ordinary certificate path.  It does not
claim defeater-detection completeness or semantic/root closure.

Concrete clean-lane capability behavior is enforced by
evaluation_information_firewall_v1 and is challenged separately by the R11
execution property-truth verifier.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R11_EXECUTION_GUARD_V1"
ROOT_ID="R11_ADAPTIVE_INTEGRITY_SECURITY"
LEAF_ID="PQ::R11_ADAPTIVE_INTEGRITY_SECURITY::EXECUTION"
CLAIM_ID="5b8287c3bf317736eea75b61483b2b0349b4a2986fad547a6b301a3d6376b747"

KNOWN_R11_DEFEATERS=frozenset({
 "C10_SUBJECT_SWAP_AFTER_CERTIFICATION",
 "C19_ANCHOR_MEMORIZATION",
 "C53_PROMPT_INJECTION_JUDGE_CONTROL",
 "C54_OPTIMIZER_GOODHART_SELECTION",
 "C55_HOLDOUT_REUSE",
 "C56_ACQUIRED_EVALUATION_CONTAMINATION",
 "C57_EVALUATION_AWARE_BEHAVIOR",
 "C58_HARNESS_TAMPERING_OR_REWARD_GAMING",
 "C59_META_ROUTER_SELECTION_OVERFIT",
 "C67_STAKES_SIGNALING_JUDGE_LENIENCY",
 "C74_EXECUTION_FAILURE_FAIL_OPEN",
 "C76_SELECTIVE_EVIDENCE_PACKET",
 "C77_PROVENANCE_OR_RECEIPT_FORGERY",
 "C80_OPTIONAL_STOPPING_OR_REPEATED_TESTING",
})

ADAPTIVE_TRIGGER="ADAPTIVE_CONTAMINATION_OR_HOLDOUT_EXPOSURE"
GENERIC_TRIGGER="UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER"

DIRECT_ADAPTIVE_DEFEATERS=frozenset({
 "C19_ANCHOR_MEMORIZATION",
 "C54_OPTIMIZER_GOODHART_SELECTION",
 "C55_HOLDOUT_REUSE",
 "C56_ACQUIRED_EVALUATION_CONTAMINATION",
 "C57_EVALUATION_AWARE_BEHAVIOR",
 "C59_META_ROUTER_SELECTION_OVERFIT",
 "C80_OPTIONAL_STOPPING_OR_REPEATED_TESTING",
})

NEAR_MISS_TO_TRIGGER={
 "adaptive_contamination_or_holdout_exposure":ADAPTIVE_TRIGGER,
 "evaluation_awareness_or_anchor_recognition":ADAPTIVE_TRIGGER,
 "repeated_testing_or_holdout_reuse":ADAPTIVE_TRIGGER,
 "prompt_control_plane_or_harness_attack":GENERIC_TRIGGER,
 "provenance_evidence_or_fail_open_integrity_gap":GENERIC_TRIGGER,
}


def _catalog_r11_ids(catalog:Mapping[str,Any])->set[str]:
 rows=(catalog.get("defeaters") or catalog.get("attack_classes")
       or catalog.get("nodes") or catalog.get("challenges"))
 if not isinstance(rows,list):
  return set()
 out=set()
 for row in rows:
  if not isinstance(row,Mapping):
   continue
  roots=row.get("root_ids")
  if not isinstance(roots,list):
   roots=row.get("target_root_ids")
  if ROOT_ID in (roots or []):
   did=row.get("id")
   if isinstance(did,str) and did:
    out.add(did)
 return out


def _base(*,status:str,passed:bool,ordinary:bool=False,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"status":status,"pass":passed,
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,"claim_id":CLAIM_ID,
  "ordinary_certificate_path_allowed":ordinary,
  "detection_completeness_proved":False,
  "r11_semantic_leaf_closed":False,"r11_root_closed":False,
  "semantic_truth_authority":False,"execution_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,
  **extra,
 }


def evaluate(
 *,
 claim_id:str,
 execution_profile:Mapping[str,Any],
 defeater_catalog:Mapping[str,Any],
 detected_defeater_ids:Sequence[str]=(),
 near_miss_signals:Mapping[str,bool]|None=None,
 unmapped_material_false_certification_defeater:bool=False,
)->dict[str,Any]:
 if claim_id!=CLAIM_ID:
  return _base(status="FAIL_CLOSED",passed=False,reason="CLAIM_ID_MISMATCH")

 catalog_ids=_catalog_r11_ids(defeater_catalog)
 if catalog_ids!=set(KNOWN_R11_DEFEATERS):
  return _base(
   status="FAIL_CLOSED",passed=False,reason="R11_DEFEATER_CATALOG_DRIFT",
   missing_catalog_ids=sorted(set(KNOWN_R11_DEFEATERS)-catalog_ids),
   unexpected_catalog_ids=sorted(catalog_ids-set(KNOWN_R11_DEFEATERS)),
  )

 triggers=execution_profile.get("escalation_triggers")
 if not isinstance(triggers,list):
  return _base(status="FAIL_CLOSED",passed=False,reason="PROFILE_ESCALATION_TRIGGERS_INVALID")
 trigger_set={x for x in triggers if isinstance(x,str)}
 if ADAPTIVE_TRIGGER not in trigger_set or GENERIC_TRIGGER not in trigger_set:
  return _base(status="FAIL_CLOSED",passed=False,reason="R11_REQUIRED_PROFILE_TRIGGER_MISSING")

 if not isinstance(detected_defeater_ids,(list,tuple)):
  return _base(status="FAIL_CLOSED",passed=False,reason="DETECTED_DEFEATERS_INVALID")
 detected=[x for x in detected_defeater_ids if isinstance(x,str) and x]
 if len(detected)!=len(detected_defeater_ids):
  return _base(status="FAIL_CLOSED",passed=False,reason="DETECTED_DEFEATERS_INVALID")

 known=sorted(set(detected)&set(KNOWN_R11_DEFEATERS))
 unknown=sorted(set(detected)-set(KNOWN_R11_DEFEATERS))
 if known:
  required=(
   ADAPTIVE_TRIGGER
   if set(known).issubset(DIRECT_ADAPTIVE_DEFEATERS)
   else GENERIC_TRIGGER
  )
  return _base(
   status="ABSTAIN_OR_ESCALATE__KNOWN_R11_DEFEATER_ACTIVE",
   passed=False,ordinary=False,
   detected_known_r11_defeaters=known,
   required_trigger=required,
   active_escalation_triggers=[required],
  )
 if unknown:
  return _base(
   status="ESCALATE__UNMAPPED_DETECTED_DEFEATER",
   passed=False,ordinary=False,
   detected_unknown_defeaters=unknown,
   required_trigger=GENERIC_TRIGGER,
   active_escalation_triggers=[GENERIC_TRIGGER],
  )

 near=near_miss_signals or {}
 if not isinstance(near,Mapping):
  return _base(status="FAIL_CLOSED",passed=False,reason="NEAR_MISS_SIGNALS_INVALID")
 bad=[k for k,v in near.items() if k not in NEAR_MISS_TO_TRIGGER or not isinstance(v,bool)]
 if bad:
  return _base(status="FAIL_CLOSED",passed=False,reason="NEAR_MISS_SIGNALS_INVALID",invalid_keys=sorted(bad))
 active=sorted({
  NEAR_MISS_TO_TRIGGER[k]
  for k,v in near.items() if v is True
 })
 if active:
  if not set(active)<=trigger_set:
   return _base(status="FAIL_CLOSED",passed=False,reason="PROFILE_NEAR_MISS_TRIGGER_MISSING")
  return _base(
   status="ESCALATE__R11_NEAR_MISS_TRIGGER",
   passed=False,ordinary=False,
   active_escalation_triggers=active,
  )

 if unmapped_material_false_certification_defeater is not False:
  if unmapped_material_false_certification_defeater is not True:
   return _base(status="FAIL_CLOSED",passed=False,reason="UNMAPPED_MATERIAL_SIGNAL_INVALID")
  return _base(
   status="ESCALATE__UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER",
   passed=False,ordinary=False,
   required_trigger=GENERIC_TRIGGER,
   active_escalation_triggers=[GENERIC_TRIGGER],
  )

 return _base(
  status="PASS__R11_EXECUTION_GUARD_ELIGIBLE_FOR_SCOPED_CERTIFICATE_VERIFICATION",
  passed=True,ordinary=True,
  detected_known_r11_defeaters=[],
  active_escalation_triggers=[],
 )
