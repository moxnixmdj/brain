"""Build the minimal V10 declared-system successor from exact V9.

V10 preserves V9 material except:
- removes fixed-pack semantic binder V2;
- adds claim-parameterized semantic binder V3;
- adds truth-repaired professional leaf manifest V2 as explicit semantic contract.
The legacy V1 manifest remains only for existing execution-receipt compatibility.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha1,sha256
import json
from pathlib import Path
from typing import Any,Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_V10_SUBJECT_BUILDER_V1"
SOURCE_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V9_DECLARED_SYSTEM_SUBJECT_20261010_V8.json"
SOURCE_BLOB="2ff32e4bb78e63635244c86d47fa369d7ba53900"
OLD_BINDER_PATH="canonical/runtime/professional_quality_leaf_binder_v2.py"
OLD_BINDER_BLOB="96dedf3641009b08a2e21a8be376459f7ae06a58"
NEW_BINDER_PATH="canonical/runtime/professional_quality_semantic_admission_binder_v3.py"
NEW_BINDER_BLOB="327b6d5d1c4b9b17273980aa12055de43d052528"
V2_MANIFEST_PATH="canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261011_V2.json"
V2_MANIFEST_BLOB="8ae72d7d44047ac9dec1b014c34a44f9933f0215"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V10_PARAMETERIZED_SEMANTIC_ADMISSION_SYSTEM_20261011_V9"

def _blob(p:Path)->str:
 d=p.read_bytes();return sha1(f"blob {len(d)}\0".encode()+d).hexdigest()
def _canon(v:Any)->bytes:
 return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "subject_authority":False,"semantic_truth_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

def build(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root else ROOT
 pins=((SOURCE_PATH,SOURCE_BLOB),(NEW_BINDER_PATH,NEW_BINDER_BLOB),(V2_MANIFEST_PATH,V2_MANIFEST_BLOB))
 for rel,sha in pins:
  p=root/rel
  if not p.is_file() or p.is_symlink():return _fail("PIN_MISSING:"+rel)
  if _blob(p)!=sha:return _fail("PIN_STALE:"+rel,observed=_blob(p))
 try:src=json.loads((root/SOURCE_PATH).read_text())
 except Exception:return _fail("SOURCE_JSON_INVALID")
 if src.get("subject_id")!="PROFESSIONAL_QUALITY_P1_V9_EXECUTABLE_TOTALITY_SEMANTICS_SYSTEM_20261010_V8":
  return _fail("SOURCE_SUBJECT_ID_DRIFT")
 material=deepcopy(src.get("system_material"))
 if not isinstance(material,dict):return _fail("SOURCE_MATERIAL_INVALID")
 comps=material.get("components")
 if not isinstance(comps,list):return _fail("SOURCE_COMPONENTS_INVALID")
 old=[x for x in comps if isinstance(x,Mapping) and x.get("path")==OLD_BINDER_PATH]
 if len(old)!=1 or old[0].get("git_blob_sha")!=OLD_BINDER_BLOB:return _fail("OLD_BINDER_BINDING_DRIFT")
 comps=[dict(x) for x in comps if x.get("path")!=OLD_BINDER_PATH]
 comps.append({"path":NEW_BINDER_PATH,"git_blob_sha":NEW_BINDER_BLOB})
 if not any(x.get("path")==V2_MANIFEST_PATH for x in comps):
  comps.append({"path":V2_MANIFEST_PATH,"git_blob_sha":V2_MANIFEST_BLOB})
 material["components"]=comps
 digest=sha256(_canon(material)).hexdigest()
 return {
  "schema":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_DECLARED_SYSTEM_SUBJECT_V2",
  "date":"2026-10-11",
  "status":"CONTENT_ADDRESSED_DECLARED_SYSTEM_SUBJECT__V10_PARAMETERIZED_SEMANTIC_ADMISSION__TRUTH_REPAIRED_V2_CONTRACT__NOT_LIVE_DEFAULT__ZERO_QUALITY_AUTHORITY",
  "source_main_commit":"b677086527f8c712c22246c4422d81f36a352b44",
  "subject_kind":"DECLARED_SYSTEM","subject_id":SUBJECT_ID,"subject_sha256":digest,
  "subject_hash_rule":"SHA256_OF_RFC8259_JSON_CANONICALIZED_BY_SORTED_KEYS_NO_WHITESPACE_UTF8_OVER_SYSTEM_MATERIAL_OBJECT",
  "system_material":material,
  "supersedes":{"path":SOURCE_PATH,"git_blob_sha":SOURCE_BLOB,
   "reason":"V9_SEMANTIC_BINDER_IMPORTS_FIXED_HISTORICAL_CLAIM_PACK__V10_REPLACES_ONLY_THAT_BINDER_WITH_CLAIM_PARAMETERIZED_FAIL_CLOSED_ADMISSION_AND_ADDS_TRUTH_REPAIRED_V2_SEMANTIC_CONTRACT"},
  "dependency_closure":{"inherited_v9_subject":{"path":SOURCE_PATH,"git_blob_sha":SOURCE_BLOB,
    "inherited_component_count":len(src["system_material"]["components"])},
   "semantic_admission_authority":{"binder":{"path":NEW_BINDER_PATH,"git_blob_sha":NEW_BINDER_BLOB},
    "semantic_contract":{"path":V2_MANIFEST_PATH,"git_blob_sha":V2_MANIFEST_BLOB},
    "claim_pack_hardcoded":False,"exact_current_claim_required":True,
    "four_root_totality_and_r4_required":True,"content_addressed_basis_required":True}},
  "identity_semantics":{"exact_component_set_frozen":True,
   "component_inclusion_does_not_imply_root_satisfaction":True,
   "scoped_evidence_inclusion_does_not_transport_scope":True,
   "root_subject_binding_requires_independent_verification":True,
   "global_subject_identity_authority":False},
  "semantic_contract_authority":{"active_manifest_path":V2_MANIFEST_PATH,
   "legacy_v1_manifest_role":"EXECUTION_RECEIPT_COMPATIBILITY_ONLY__ZERO_SEMANTIC_AUTHORITY",
   "semantic_binder_path":NEW_BINDER_PATH},
  "candidate_generation":True,"live_default":False,
  "intended_use":"V10_PROOF_BOUND_PROFESSIONAL_EXECUTION_WITH_CLAIM_PARAMETERIZED_FAIL_CLOSED_SEMANTIC_ADMISSION",
  "hard_nonclaims":["NO_SEMANTIC_LEAF_PROPERTY_TRUTH_FROM_SUBJECT_CONSTRUCTION",
   "NO_CLAIM_ANY_POSITIVE_SEMANTIC_RECEIPT_ALREADY_EXISTS_FOR_V10",
   "NO_GLOBAL_LEAF_OR_ROOT_CLOSURE","NO_LIVE_DEFAULT_PROMOTION",
   "NO_QUALITY_ACCEPTANCE_PROMOTION_OR_TERMINAL_AUTHORITY"],
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,
  "builder":{"schema":SCHEMA,"pass":True,"removed_component_count":1,"added_component_count":2,
   "net_component_delta":1,"fixed_pack_dependency_removed":True}
 }
