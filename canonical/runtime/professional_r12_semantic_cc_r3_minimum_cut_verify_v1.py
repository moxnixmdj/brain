"""Fail-closed validator for the R12 semantic CC_R3 three-obligation cut."""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_SEMANTIC_CC_R3_MINIMUM_CUT_VERIFY_V1"
CUT_PATH="canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_MINIMUM_IRREDUCIBLE_CUT_20261010_V1.json"
EXPECTED_CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
EXPECTED_OBLIGATIONS=(
 "R12_CC_R3_C1_EXACT_ASSUMPTION_GUARANTEE_DISCHARGE",
 "R12_CC_R3_C3_COMPONENT_ABSTRACTION_SUBSTITUTION_SOUNDNESS",
 "R12_CC_R3_STRONGER_MATERIAL_DEFEATER_TOTALITY",
)
EXPECTED_DO_NOT_REOPEN={
 "R12C2_SAME_SUBJECT_ROOT_CONJUNCTION",
 "R12C4_INDEPENDENT_DEFEATER_SEARCH",
 "R12C5_COVERAGE_ACCOUNTING",
 "R12C6_PROOF_SEARCH_HONESTY",
 "R12C7_META_CONTROLLER_FALSIFICATION",
 "R12C8_NONVACUITY",
 "R12_IDENTITY_SEMANTIC_CARRIER_FACTORIZATION",
 "R12_CC_R1_REALITY_CONTAINMENT",
 "R12_CC_R2_MISSION_SOUNDNESS",
}
BOUND_REFS={
 "predecessor_runtime":("canonical/runtime/professional_r12_semantic_cc_r3_evidence_cut_v1.py","df0a722b5cd0456b32b3ab1e4e4bb82a8896fe08"),
 "predecessor_verify":("canonical/verification/PROFESSIONAL_R12_SEMANTIC_CC_R3_EVIDENCE_CUT_VERIFY_20261010_V1.json","f0a4ab092d1ec5ae86c63e9a8f62117aa8ee6da1"),
 "old_interface_activation":("canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_ACTIVATION_V1.json","50e7b82c08a76c77c6d8859dc21d6782faa25edd"),
 "same_subject_verify":("canonical/verification/PROFESSIONAL_QUALITY_V7_12_OF_12_COMPOSITION_INDEPENDENT_VERIFY_20261010_V1.json","4ee02c41acf64b1f47ebadec55b6bb5453d676ba"),
 "identity_verify":("canonical/verification/PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_VERIFY_20261010_V1.json","35a3ccf9ad454aa0318a4ed10edc065830c3874d"),
 "quotient_verify":("canonical/verification/ACCEPTANCE_QUOTIENT_TRACE_REFINEMENT_WOLFRAM_VERIFICATION_20261005_V1.json","8ce9ee7f46cb313ef92182cf656db5310b648572"),
 "defeater_verify":("canonical/verification/PROFESSIONAL_QUALITY_80_DEFEATER_UVCK_REPLAY_VERIFY_20261009_V1.json","c054e9362ce382889e9cca62bdb69e11cea19644"),
 "root_theorem":("canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_V1.json","3d2c89502d94c045d04af04db4cdecc509a08dd8"),
}

def _blob(path:Path)->str:
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "open_obligation_count":0,"cc_r3_terminal_closure":False,
  "semantic_property_truth_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,**extra,
 }

def validate(doc:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root else ROOT
 if not isinstance(doc,Mapping): return _fail("CUT_NOT_OBJECT")
 claim=doc.get("claim") or {}
 if claim.get("claim_id")!=EXPECTED_CLAIM_ID:
  return _fail("CLAIM_ID_DRIFT")
 cut=doc.get("cut")
 if not isinstance(cut,list) or len(cut)!=3:
  return _fail("CUT_NOT_EXACT_THREE")
 ids=tuple(x.get("obligation_id") for x in cut if isinstance(x,Mapping))
 if ids!=EXPECTED_OBLIGATIONS:
  return _fail("CUT_OBLIGATION_ID_DRIFT",observed=list(ids))
 if (doc.get("minimality_claim") or {}).get("current_exact_open_obligation_count")!=3:
  return _fail("OPEN_COUNT_DRIFT")
 sched=doc.get("scheduler_effect") or {}
 if set(sched.get("do_not_reopen") or [])!=EXPECTED_DO_NOT_REOPEN:
  return _fail("SOLVED_SET_DRIFT")
 if tuple(sched.get("execute_only") or [])!=EXPECTED_OBLIGATIONS:
  return _fail("EXECUTE_ONLY_DRIFT")
 auth=doc.get("authority") or {}
 if any(auth.get(k) is not False for k in (
   "cc_r3_terminal_closure","semantic_property_truth_authority",
   "quality_authority","acceptance_authority","promotion_authority","terminal_authority"
 )):
  return _fail("UNAUTHORIZED_AUTHORITY")
 for name,(rel,expected) in BOUND_REFS.items():
  p=root/rel
  if not p.is_file() or p.is_symlink():
   return _fail("BOUND_REF_MISSING",ref=name,path=rel)
  actual=_blob(p)
  if actual!=expected:
   return _fail("BOUND_REF_STALE",ref=name,path=rel,expected=expected,observed=actual)

 predecessor=json.loads((root/BOUND_REFS["predecessor_verify"][0]).read_text())
 cut_state=predecessor.get("verified_cut") or {}
 if (
   cut_state.get("verified_clause_count")!=6
   or cut_state.get("partial_clause_count")!=2
   or cut_state.get("open_clause_count")!=0
  ):
  return _fail("PREDECESSOR_CLAUSE_CUT_DRIFT")
 if set(cut_state.get("partial_clause_ids") or [])!={"R12C1_ASSUMPTION_GUARANTEE_COMPOSITION","R12C3_ABSTRACTION_SOUNDNESS"}:
  return _fail("PREDECESSOR_PARTIAL_SET_DRIFT")
 if "NO_UNKNOWN_DEFEATER_COMPLETENESS" not in set(predecessor.get("hard_nonclaims") or []):
  return _fail("UNKNOWN_DEFEATER_BOUNDARY_LOST")

 # Every cut row must explicitly define proof shape, reuse insufficiency and shortcuts.
 for row in cut:
  if not isinstance(row,Mapping): return _fail("CUT_ROW_NOT_OBJECT")
  if not row.get("required_proof_shape"): return _fail("PROOF_SHAPE_MISSING",obligation_id=row.get("obligation_id"))
  if not row.get("existing_reuse"): return _fail("REUSE_ANALYSIS_MISSING",obligation_id=row.get("obligation_id"))
  if not row.get("forbidden_shortcuts"): return _fail("SHORTCUT_GUARD_MISSING",obligation_id=row.get("obligation_id"))
  if row.get("current_state") not in {"OPEN","OPEN_FROM_PARTIAL_EXISTING_EVIDENCE"}:
   return _fail("OBLIGATION_PREMATURELY_CLOSED",obligation_id=row.get("obligation_id"))

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__R12_CC_R3_EXACT_THREE_OBLIGATION_CUT__BOUND_EVIDENCE_CURRENT__ZERO_PROPERTY_CREDIT",
  "claim_id":EXPECTED_CLAIM_ID,
  "open_obligation_count":3,
  "open_obligation_ids":list(EXPECTED_OBLIGATIONS),
  "solved_or_do_not_reopen_count":len(EXPECTED_DO_NOT_REOPEN),
  "cc_r3_terminal_closure":False,
  "semantic_property_truth_authority":False,
  "terminal_authority":False,
  "terminal_credit_delta":0,
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root else ROOT
 p=root/CUT_PATH
 if not p.is_file() or p.is_symlink(): return _fail("CUT_FILE_MISSING")
 try: doc=json.loads(p.read_text(encoding="utf-8"))
 except Exception:return _fail("CUT_JSON_INVALID")
 return validate(doc,repo_root=root)

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
