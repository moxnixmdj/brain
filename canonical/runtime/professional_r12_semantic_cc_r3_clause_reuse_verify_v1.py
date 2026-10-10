"""Verify the reuse classification for the frozen R12 semantic CC_R3 cut.

This verifier deliberately distinguishes:
1. support for each of the eight textual root-contract clauses; from
2. the stronger whole-leaf target predicate.

Eight-of-eight root-contract support is NOT CC_R3 terminal closure. The target
still requires material-defeater totality and a nonvacuous positive semantic
certificate.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_SEMANTIC_CC_R3_CLAUSE_REUSE_VERIFY_V1"
CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
CLASS="canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_CLAUSE_REUSE_CLASSIFICATION_20261010_V1.json"
DECOMP="canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_CONTRACT_DECOMPOSITION_20261010_V1.json"
EXPECTED_CLAUSES=[
"R12C1_ASSUMPTION_GUARANTEE_COMPOSITION","R12C2_SAME_SUBJECT_ROOT_CONJUNCTION",
"R12C3_ABSTRACTION_SOUNDNESS","R12C4_INDEPENDENT_DEFEATER_SEARCH",
"R12C5_COVERAGE_ACCOUNTING","R12C6_PROOF_SEARCH_HONESTY",
"R12C7_META_CONTROLLER_FALSIFICATION","R12C8_NONVACUITY",
]
PINS={
"decomposition":(DECOMP,"d83ded1689ec636a2cda60f7c7419dd69a61cbd5"),
"frozen_claim":("canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261010_V1.json","5e7c198da31b901bb4f53c4fc15cee7d6298c114"),
"cc_r1":("canonical/verification/COVERAGE_CC_R1_PROFESSIONAL_R12_SEMANTIC_VERIFY_20261010_V1.json","65ccb4b108e144400383fcee4491396558a35e65"),
"cc_r2":("canonical/verification/COVERAGE_CC_R2_PROFESSIONAL_R12_SEMANTIC_VERIFY_20261010_V1.json","97b843c23b0dba80dbf5030f31ee4fb02cd162a7"),
"same_subject_composition":("canonical/verification/PROFESSIONAL_QUALITY_V7_12_OF_12_COMPOSITION_INDEPENDENT_VERIFY_20261010_V1.json","4ee02c41acf64b1f47ebadec55b6bb5453d676ba"),
"r12_root_binding":("canonical/verification/PROFESSIONAL_QUALITY_R12_V7_ROOT_SUBJECT_BINDING_PUBLIC_VERIFY_20261010_V1.json","174bc362ff1f1b7935925c8d17e55d36288bdbad"),
"uvck_current_generation":("canonical/verification/UVCK_V2_CURRENT_GENERATION_INDEPENDENT_REPLAY_VERIFY_20261009_V1.json","81f7f070233b6aa1c4b491949a4c3e7aedfafd10"),
"defeater_order":("canonical/verification/UVCK_V2_DEFEATER_ORDER_VERIFY_20261009_V1.json","1c3428b10a1205e928a87f41a7c16a8a3d17b7ca"),
"known_defeaters":("canonical/verification/PROFESSIONAL_QUALITY_80_DEFEATER_UVCK_REPLAY_VERIFY_20261009_V1.json","c054e9362ce382889e9cca62bdb69e11cea19644"),
"whole_domain":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_DOMAIN_EQUIVALENCE_V1_INDEPENDENT_VERIFY_20261010_V1.json","b6b826d1658d8a2c88ea80260ee667e86ae99394"),
"scope_batch":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json","4c2d40a262f18f34bb35f94b59660d60972d45ef"),
"identity_carrier":("canonical/verification/PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_VERIFY_20261010_V1.json","35a3ccf9ad454aa0318a4ed10edc065830c3874d"),
"leaf_registry":("canonical/verification/PROFESSIONAL_QUALITY_LEAF_REGISTRY_PROPERTY_TRUTH_VERIFY_20261010_V2.json","bdde7b52793272623773b07bf774c0a74c6be7af"),
"r12_execution_property":("canonical/verification/PROFESSIONAL_QUALITY_R12_EXECUTION_PROPERTY_TRUTH_INDEPENDENT_VERIFY_20261010_V1.json","b2b9365ad4e7d34628d74f328507eecf01a13804"),
}

def blob(p:Path)->str:
 b=p.read_bytes();return sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load_bound(root:Path,path:str,sha:str)->dict[str,Any]|None:
 p=(root/path).resolve()
 try:p.relative_to(root.resolve())
 except ValueError:return None
 if not p.is_file() or p.is_symlink() or blob(p)!=sha:return None
 try:d=json.loads(p.read_text())
 except Exception:return None
 return d if isinstance(d,dict) else None
def fail(reason:str,**x:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
 "claim_id":CLAIM_ID,"cc_r3_terminal_closure":False,
 "semantic_property_truth_authority":False,"terminal_authority":False,
 "terminal_credit_delta":0,**x}

def evaluate_documents(c:Mapping[str,Any],d:Mapping[str,Any],e:Mapping[str,Mapping[str,Any]])->dict[str,Any]:
 errors=[]
 if c.get("claim_id")!=CLAIM_ID or d.get("claim_id")!=CLAIM_ID:errors.append("CLAIM_ID_DRIFT")
 drows=d.get("clauses")
 if not isinstance(drows,list) or [x.get("id") for x in drows if isinstance(x,Mapping)]!=EXPECTED_CLAUSES:
  errors.append("DECOMPOSITION_CLAUSE_SET_DRIFT")
 rows=c.get("clause_rows")
 if not isinstance(rows,list) or len(rows)!=8:errors.append("CLASSIFICATION_CLAUSE_COUNT_DRIFT");rows=[]
 ids=[x.get("id") for x in rows if isinstance(x,Mapping)]
 if ids!=EXPECTED_CLAUSES:errors.append("CLASSIFICATION_CLAUSE_SEQUENCE_DRIFT")
 if any(x.get("global_claim") is not False for x in rows if isinstance(x,Mapping)):errors.append("CLAUSE_GLOBAL_OVERCLAIM")
 if c.get("root_contract_clause_count")!=8 or c.get("root_contract_reuse_supported_count")!=8:errors.append("ROOT_CONTRACT_REUSE_COUNT_DRIFT")

 # Current evidence must still support each bounded reuse assertion.
 if not str(e["cc_r1"].get("status") or "").startswith("PASS__INDEPENDENT_SPRITE"):errors.append("CC_R1_NOT_VERIFIED")
 if not str(e["cc_r2"].get("status") or "").startswith("PASS__INDEPENDENT_SPRITE"):errors.append("CC_R2_NOT_VERIFIED")
 comp=e["same_subject_composition"]; rep=comp.get("replay") or {}
 if not str(comp.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE_EXACT_V4_12_OF_12") or rep.get("exact_root_binding_count")!=12:
  errors.append("SAME_SUBJECT_COMPOSITION_NOT_VERIFIED")
 rb=e["r12_root_binding"]
 if not str(rb.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__") or rb.get("root_subject_binding_authority") is not True:
  errors.append("R12_ROOT_BINDING_NOT_VERIFIED")
 if "NO_UNKNOWN_DEFEATER_COMPLETENESS" not in set(rb.get("hard_nonclaims") or []):errors.append("R12_UNKNOWN_DEFEATER_NONCLAIM_MISSING")
 uv=e["uvck_current_generation"];ur=uv.get("replay") or {}
 if ur.get("tests_run")!=18 or ur.get("tests_passed")!=18:errors.append("UVCK_CURRENTGEN_REPLAY_DRIFT")
 order=e["defeater_order"];orr=order.get("replay") or {}
 if orr.get("tests_run")!=11 or orr.get("failures")!=0 or orr.get("errors")!=0:errors.append("DEFEATER_ORDER_REPLAY_DRIFT")
 kd=e["known_defeaters"]
 if "ALL_80_DECLARED_KNOWN_ATTACK_CLASSES_BIND_TO_EXISTING_12_ROOT_ASSURANCE_ONTOLOGY" not in set(kd.get("proved") or []):
  errors.append("KNOWN_DEFEATER_BINDING_UNPROVED")
 if "NO_ADVERSARIAL_COMPLETENESS_OF_UNKNOWN_ATTACKS" not in set(kd.get("hard_nonclaims") or []):
  errors.append("KNOWN_DEFEATER_UNIVERSE_OVERCLAIM")
 if "80_OF_80_KNOWN_DEFEATERS_BOUND" not in str(kd.get("status") or ""):errors.append("KNOWN_DEFEATER_COUNT_DRIFT")
 wd=e["whole_domain"];wdr=wd.get("independent_replay") or {}
 if wdr.get("real_manifest_passed")!=24 or wdr.get("unique_claim_id_count")!=24:errors.append("WHOLE_DOMAIN_DRIFT")
 sb=e["scope_batch"];sbr=sb.get("independent_replay") or {}
 if sbr.get("scope_complete_count")!=24 or sbr.get("property_truth_count")!=0:errors.append("SCOPE_BATCH_DRIFT")
 ic=e["identity_carrier"]
 if ic.get("universal_factorization_proved_count")!=12 or (ic.get("theorem") or {}).get("semantic_information_loss") is not False:
  errors.append("IDENTITY_CARRIER_DRIFT")
 lr=e["leaf_registry"];lrr=lr.get("independent_replay") or {}
 if lrr.get("verified_leaf_count")!=4 or lrr.get("open_leaf_count")!=20:errors.append("COVERAGE_ACCOUNTING_DRIFT")
 ex=e["r12_execution_property"];exr=ex.get("independent_replay") or {};counts=exr.get("observed_case_counts") or {}
 if counts.get("positive")!=2 or counts.get("total")!=24:errors.append("R12_EXECUTION_NONVACUITY_WITNESS_DRIFT")
 if "NO_R12_SEMANTIC_LEAF_CLOSURE" not in set(ex.get("hard_nonclaims") or []):errors.append("EXECUTION_TO_SEMANTIC_OVERCLAIM")

 t=c.get("stronger_target_predicate") or {};res=t.get("required_residuals")
 if not isinstance(res,list) or [x.get("id") for x in res if isinstance(x,Mapping)]!=[
  "R12T1_MATERIAL_DEFEATER_TOTALITY","R12T2_SEMANTIC_POSITIVE_ROUTE_NONVACUITY"]:
  errors.append("TARGET_RESIDUAL_SET_DRIFT")
 if t.get("minimum_semantic_research_cut")!=["R12T1_MATERIAL_DEFEATER_TOTALITY"]:errors.append("MINIMUM_RESEARCH_CUT_DRIFT")
 if t.get("cc_r3_terminal_closure_proved") is not False or t.get("r12_semantic_property_truth_proved") is not False:
  errors.append("TARGET_PREMATURE_CLOSURE")
 kt=c.get("key_truths") or {}
 if kt.get("known_defeater_count_verified")!=80 or kt.get("known_defeater_universe_complete") is not False:
  errors.append("DEFEATER_COMPLETENESS_TRUTH_DRIFT")
 if kt.get("semantic_positive_certificate_count")!=0:errors.append("SEMANTIC_POSITIVE_CERTIFICATE_OVERCLAIM")
 if c.get("new_primitive_required") is not False:errors.append("UNPROVED_NEW_PRIMITIVE_CLAIM")
 if c.get("semantic_property_truth_authority") is not False or c.get("terminal_authority") is not False:
  errors.append("AUTHORITY_OVERCLAIM")
 if errors:return fail("R12_CC_R3_REUSE_CLASSIFICATION_INVALID",errors=sorted(set(errors)))
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__EIGHT_OF_EIGHT_ROOT_CONTRACT_CLAUSES_REUSE_SUPPORTED__STRONGER_TARGET_REDUCED_TO_MATERIAL_DEFEATER_TOTALITY_THEN_SEMANTIC_NONVACUITY",
  "claim_id":CLAIM_ID,"root_contract_clause_count":8,"root_contract_reuse_supported_count":8,
  "minimum_semantic_research_cut":["R12T1_MATERIAL_DEFEATER_TOTALITY"],
  "constructive_followup":["R12T2_SEMANTIC_POSITIVE_ROUTE_NONVACUITY"],
  "known_defeater_count_verified":80,"known_defeater_universe_complete":False,
  "cc_r3_terminal_closure":False,"semantic_property_truth_authority":False,
  "new_primitive_required":False,"terminal_authority":False,"terminal_credit_delta":0,"errors":[]}

def evaluate(*,root:Path|None=None)->dict[str,Any]:
 root=(root or ROOT).resolve()
 cp=root/CLASS
 if not cp.is_file():return fail("CLASSIFICATION_MISSING")
 try:c=json.loads(cp.read_text())
 except Exception:return fail("CLASSIFICATION_JSON_INVALID")
 d=load_bound(root,*PINS["decomposition"])
 if d is None:return fail("DECOMPOSITION_BYTES_INVALID")
 evidence={}
 for key,(path,sha) in PINS.items():
  if key=="decomposition":continue
  x=load_bound(root,path,sha)
  if x is None:return fail("EVIDENCE_BYTES_INVALID:"+key)
  evidence[key]=x
 return evaluate_documents(c,d,evidence)
if __name__=="__main__":
 out=evaluate();print(json.dumps(out,indent=2,sort_keys=True));raise SystemExit(0 if out["pass"] else 1)
