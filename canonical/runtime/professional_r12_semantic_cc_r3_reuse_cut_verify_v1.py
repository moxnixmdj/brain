"""Verify the exact R12 semantic CC_R3 same-subject reuse cut."""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_SEMANTIC_CC_R3_REUSE_CUT_VERIFY_V1"
CUT="canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_REUSE_CUT_20261010_V1.json"
PINS={
 "decomposition":("canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_CONTRACT_DECOMPOSITION_20261010_V1.json","d83ded1689ec636a2cda60f7c7419dd69a61cbd5"),
 "frozen_claim":("canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261010_V1.json","5e7c198da31b901bb4f53c4fc15cee7d6298c114"),
 "same_subject":("canonical/verification/PROFESSIONAL_QUALITY_V7_12_OF_12_COMPOSITION_INDEPENDENT_VERIFY_20261010_V1.json","4ee02c41acf64b1f47ebadec55b6bb5453d676ba"),
 "identity":("canonical/verification/PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_VERIFY_20261010_V1.json","35a3ccf9ad454aa0318a4ed10edc065830c3874d"),
 "execution":("canonical/verification/PROFESSIONAL_QUALITY_R12_EXECUTION_PROPERTY_TRUTH_INDEPENDENT_VERIFY_20261010_V1.json","b2b9365ad4e7d34628d74f328507eecf01a13804"),
 "root_binding":("canonical/verification/PROFESSIONAL_QUALITY_R12_V7_ROOT_SUBJECT_BINDING_PUBLIC_VERIFY_20261010_V1.json","174bc362ff1f1b7935925c8d17e55d36288bdbad"),
}
CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
EXPECTED_IDS=[
 "R12C1_ASSUMPTION_GUARANTEE_COMPOSITION",
 "R12C2_SAME_SUBJECT_ROOT_CONJUNCTION",
 "R12C3_ABSTRACTION_SOUNDNESS",
 "R12C4_INDEPENDENT_DEFEATER_SEARCH",
 "R12C5_COVERAGE_ACCOUNTING",
 "R12C6_PROOF_SEARCH_HONESTY",
 "R12C7_META_CONTROLLER_FALSIFICATION",
 "R12C8_NONVACUITY",
]
PROVED={"R12C2_SAME_SUBJECT_ROOT_CONJUNCTION","R12C3_ABSTRACTION_SOUNDNESS"}

def _blob(path:Path)->str:
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _load(path:Path)->dict[str,Any]:
 value=json.loads(path.read_text(encoding="utf-8"))
 if not isinstance(value,dict): raise ValueError("NOT_OBJECT")
 return value

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
 "proved_by_reuse_count":0,"open_root_contract_clause_count":8,
 "cc_r3_terminal_closure_proved":False,"semantic_property_truth_authority":False,
 "terminal_authority":False,"terminal_credit_delta":0,**extra}

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 try:
  cut=_load(root/CUT)
  docs={}
  for key,(rel,expected) in PINS.items():
   p=root/rel
   if not p.is_file() or p.is_symlink(): return _fail(key.upper()+"_MISSING")
   actual=_blob(p)
   if actual!=expected:return _fail(key.upper()+"_BLOB_DRIFT",observed_blob=actual)
   docs[key]=_load(p)
 except Exception as exc:
  return _fail(type(exc).__name__+":"+str(exc))

 if cut.get("claim_id")!=CLAIM_ID:return _fail("CUT_CLAIM_ID_DRIFT")
 decomp=docs["decomposition"]
 if decomp.get("claim_id")!=CLAIM_ID:return _fail("DECOMPOSITION_CLAIM_ID_DRIFT")
 rows=decomp.get("clauses")
 if not isinstance(rows,list) or [r.get("id") for r in rows if isinstance(r,Mapping)]!=EXPECTED_IDS:
  return _fail("DECOMPOSITION_CLAUSE_DRIFT")

 claim=docs["frozen_claim"]
 subject=claim.get("subject") or {}
 if subject.get("subject_id")!=SUBJECT_ID or subject.get("subject_sha256")!=SUBJECT_SHA:
  return _fail("FROZEN_SUBJECT_DRIFT")

 same=docs["same_subject"]
 cs= same.get("composed_subject") or {}
 if (
  same.get("composition_admissible") is not True
  or same.get("verified_root_subject_binding_count")!=12
  or cs.get("subject_id")!=SUBJECT_ID
  or cs.get("subject_sha256")!=SUBJECT_SHA
 ):
  return _fail("C2_SAME_SUBJECT_REUSE_NOT_PROVED")

 identity=docs["identity"]
 theorem=identity.get("theorem") or {}
 replay=identity.get("independent_replay") or {}
 if (
  theorem.get("projection")!="PI_C_IS_IDENTITY_ON_COMPLETE_FROZEN_CLAIM_WORLD_STATE"
  or theorem.get("semantic_information_loss") is not False
  or replay.get("r12_claim_id")!=CLAIM_ID
  or identity.get("universal_factorization_proved_count")!=12
 ):
  return _fail("C3_IDENTITY_ABSTRACTION_REUSE_NOT_PROVED")

 execution=docs["execution"]
 replay=execution.get("independent_replay") or {}
 counts=replay.get("observed_case_counts") or {}
 if (
  counts.get("positive")!=2
  or execution.get("r12_semantic_leaf_closed") is not False
  or execution.get("unknown_defeater_completeness_proved") is not False
 ):
  return _fail("C8_BOUNDARY_DRIFT")

 root_binding=docs["root_binding"]
 if root_binding.get("unknown_defeater_completeness_proved") is not False:
  return _fail("STRONGER_DEFEATER_RESIDUAL_DRIFT")

 reuse=cut.get("clause_reuse")
 if not isinstance(reuse,list) or len(reuse)!=8:return _fail("CUT_ROWS_INVALID")
 by_id={r.get("id"):r for r in reuse if isinstance(r,Mapping)}
 if set(by_id)!=set(EXPECTED_IDS):return _fail("CUT_IDS_INVALID")
 observed={cid for cid,row in by_id.items() if row.get("state")=="PROVED_BY_REUSE"}
 if observed!=PROVED:return _fail("CUT_PROVED_SET_OVER_OR_UNDERCLAIM",observed=sorted(observed))
 if any(by_id[cid].get("state")!="OPEN" for cid in set(EXPECTED_IDS)-PROVED):
  return _fail("CUT_OPEN_SET_OVERCLAIM")

 stronger=cut.get("stronger_target_predicate_residual") or {}
 if (
  stronger.get("state")!="OPEN"
  or stronger.get("unknown_defeater_completeness_proved") is not False
  or stronger.get("not_counted_as_one_of_the_eight_root_contract_clauses") is not True
 ):
  return _fail("STRONGER_TARGET_RESIDUAL_OVERCLAIM")

 derived=cut.get("derived") or {}
 if (
  derived.get("exact_clause_count")!=8
  or derived.get("proved_by_reuse_count")!=2
  or derived.get("open_root_contract_clause_count")!=6
  or derived.get("cc_r3_terminal_closure_proved") is not False
 ):
  return _fail("DERIVED_COUNTS_INVALID")

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__R12_CC_R3_EXACT_REUSE_CUT__2_OF_8_DISCHARGED__6_ROOT_CLAUSES_PLUS_STRONGER_DEFEATER_RESIDUAL_OPEN",
  "claim_id":CLAIM_ID,
  "proved_by_reuse_clause_ids":sorted(PROVED),
  "open_root_contract_clause_ids":sorted(set(EXPECTED_IDS)-PROVED),
  "proved_by_reuse_count":2,"open_root_contract_clause_count":6,
  "stronger_material_defeater_obligation_open":True,
  "unknown_defeater_completeness_proved":False,
  "cc_r3_terminal_closure_proved":False,
  "semantic_property_truth_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,
 }

if __name__=="__main__":
 out=verify();print(json.dumps(out,indent=2,sort_keys=True));raise SystemExit(0 if out["pass"] else 1)
