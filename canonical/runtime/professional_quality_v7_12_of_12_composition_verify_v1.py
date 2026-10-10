from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime import professional_quality_same_subject_composition_gate_v4 as gate

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_V7_12_OF_12_COMPOSITION_VERIFY_V1"
MANIFEST="canonical/governance/PROFESSIONAL_QUALITY_V7_12_OF_12_COMPOSITION_INPUT_20261010_V1.json"
MANIFEST_BLOB="25ed911c9c71860fb359091749dc8fd1212a7bd8"
GATE_PATH="canonical/runtime/professional_quality_same_subject_composition_gate_v4.py"
GATE_BLOB="7b65c61f951339a445ef3735a7dbdd34e7a218f2"
GATE_PUBLIC_VERIFY="canonical/verification/PROFESSIONAL_QUALITY_SAME_SUBJECT_GATE_V3_RECEIPT_ADAPTER_PUBLIC_VERIFY_20261010_V1.json"
GATE_PUBLIC_VERIFY_BLOB="79910bf40700ddf000630a7169566fef91e6c939"
SUBJECT_KIND="DECLARED_SYSTEM"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA256="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"

def _blob(p:Path)->str:
 d=p.read_bytes();return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def _read(root:Path,path:str,sha:str):
 p=(root/path).resolve()
 try:p.relative_to(root.resolve())
 except ValueError:return None
 if not p.is_file() or p.is_symlink() or _blob(p)!=sha:return None
 try:d=json.loads(p.read_text(encoding="utf-8"))
 except Exception:return None
 return d if isinstance(d,dict) else None
def _fail(reason:str,**extra:Any):
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
 "composition_admissible":False,"professional_quality_closed":False,
 "semantic_truth_authority":False,"execution_authority":False,"quality_authority":False,
 "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
 "terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

def evaluate_rows(rows:list[dict[str,Any]],*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 return gate.evaluate({"root_subject_bindings":rows},repo_root=root)

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 manifest=_read(root,MANIFEST,MANIFEST_BLOB)
 if manifest is None:return _fail("MANIFEST_BYTES_INVALID")
 if _blob(root/GATE_PATH)!=GATE_BLOB:return _fail("GATE_RUNTIME_BLOB_DRIFT")
 pv=_read(root,GATE_PUBLIC_VERIFY,GATE_PUBLIC_VERIFY_BLOB)
 if pv is None:return _fail("GATE_PUBLIC_VERIFICATION_BYTES_INVALID")
 pr=pv.get("public_runner") or {}
 if pr.get("conclusion")!="success" or pr.get("receipt_normalizer_tests_step")!="success":return _fail("GATE_PUBLIC_VERIFICATION_NOT_PASS")
 if (manifest.get("subject_kind"),manifest.get("subject_id"),manifest.get("subject_sha256"))!=(SUBJECT_KIND,SUBJECT_ID,SUBJECT_SHA256):return _fail("MANIFEST_SUBJECT_TUPLE_INVALID")
 if manifest.get("required_root_count")!=12:return _fail("MANIFEST_ROOT_COUNT_INVALID")
 for f in ("composition_admissible","professional_quality_closed","quality_authority","terminal_authority"):
  if manifest.get(f) is not False:return _fail("MANIFEST_SELF_AUTHORITY_FORBIDDEN:"+f)
 rows=manifest.get("root_subject_bindings")
 if not isinstance(rows,list) or len(rows)!=12:return _fail("MANIFEST_ROOT_BINDINGS_INVALID")
 out=evaluate_rows(rows,repo_root=root)
 if out.get("pass") is not True or out.get("status")!="PASS__SAME_SUBJECT_ROOT_COMPOSITION_ADMISSIBLE":return _fail("COMPOSITION_GATE_NOT_PASS",gate_result=out)
 if out.get("verified_root_subject_binding_count")!=12:return _fail("COMPOSITION_VERIFIED_ROOT_COUNT_INVALID")
 sub=out.get("composed_subject") or {}
 if (sub.get("subject_kind"),sub.get("subject_id"),sub.get("subject_sha256"))!=(SUBJECT_KIND,SUBJECT_ID,SUBJECT_SHA256):return _fail("COMPOSED_SUBJECT_TUPLE_INVALID")
 if out.get("composition_admissible") is not True:return _fail("COMPOSITION_ADMISSIBILITY_MISSING")
 for f in ("professional_quality_closed","semantic_truth_authority","execution_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
  if out.get(f) is not False:return _fail("COMPOSITION_AUTHORITY_OVERCLAIM:"+f)
 return {"schema":SCHEMA,"pass":True,"status":"PASS__V7_12_OF_12_SAME_SUBJECT_COMPOSITION_ADMISSIBLE",
 "subject_kind":SUBJECT_KIND,"subject_id":SUBJECT_ID,"subject_sha256":SUBJECT_SHA256,
 "verified_root_subject_binding_count":12,"composition_admissible":True,
 "professional_quality_closed":False,"semantic_truth_authority":False,"execution_authority":False,
 "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
 "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}

if __name__=="__main__":print(json.dumps(verify(),indent=2,sort_keys=True))
