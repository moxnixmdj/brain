from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime import professional_quality_same_subject_composition_gate_v3 as gate
from canonical.runtime import professional_quality_root_binding_compat_v1 as compat

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_V7_REAL_12_OF_12_COMPOSITION_VERIFY_V1"
WORKLIST="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_SAME_SUBJECT_ROOT_BINDING_WORKLIST_20261010_V18.json"
WORKLIST_BLOB="0d6efbd19f1b7d30853234a0e1f2633b52539f76"
REGISTRY="canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json"
REGISTRY_BLOB="b9ddf7cbe7fbfad0e81fe068a0c19b48703b5aba"
SCOPED_VERIFY="canonical/verification/PROFESSIONAL_QUALITY_R4_SEMANTIC_SCOPED_INTEGRATION_VERIFY_20261010_V1.json"
SCOPED_VERIFY_BLOB="664c22bfdfc51ea4058e4e2d3c3efe9d8def907b"
GATE_RUNTIME="canonical/runtime/professional_quality_same_subject_composition_gate_v3.py"
GATE_RUNTIME_BLOB="ddbe6ec92fef405b8909a161ef9acd685ec7317b"
GATE_ADAPTER_VERIFY="canonical/verification/PROFESSIONAL_QUALITY_SAME_SUBJECT_GATE_V3_RECEIPT_ADAPTER_PUBLIC_VERIFY_20261010_V1.json"
GATE_ADAPTER_VERIFY_BLOB="79910bf40700ddf000630a7169566fef91e6c939"
SID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SSH="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
SKIND="DECLARED_SYSTEM"

def _blob(p:Path)->str:
 d=p.read_bytes();return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def _read(root:Path,p:str,h:str):
 q=(root/p).resolve()
 try:q.relative_to(root.resolve())
 except ValueError:return None
 if not q.is_file() or q.is_symlink() or _blob(q)!=h:return None
 try:o=json.loads(q.read_text(encoding="utf-8"))
 except Exception:return None
 return o if isinstance(o,dict) else None
def _fail(r:str,**x):
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":r,
 "composition_admissible":False,"professional_quality_closed":False,
 "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
 "terminal_authority":False,"terminal_credit_delta":0,**x}

def verify(*,repo_root:str|Path|None=None):
 root=Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[2]
 if _blob(root/GATE_RUNTIME)!=GATE_RUNTIME_BLOB:return _fail("GATE_RUNTIME_BLOB_DRIFT")
 ok,nf=gate._normal_form_ok(root)
 if not ok:return _fail("NORMAL_FORM_SAME_SUBJECT_LAW_UNAVAILABLE",normal_form=nf)
 adapter=_read(root,GATE_ADAPTER_VERIFY,GATE_ADAPTER_VERIFY_BLOB)
 if not adapter:return _fail("GATE_ADAPTER_RECEIPT_INVALID")
 pr=adapter.get("public_runner") or {}
 if adapter.get("status","").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__") is not True or pr.get("conclusion")!="success":return _fail("GATE_ADAPTER_NOT_INDEPENDENTLY_VERIFIED")
 if ((adapter.get("runtime") or {}).get("git_blob_sha"))!=GATE_RUNTIME_BLOB:return _fail("GATE_ADAPTER_RUNTIME_MISMATCH")

 reg=_read(root,REGISTRY,REGISTRY_BLOB);sv=_read(root,SCOPED_VERIFY,SCOPED_VERIFY_BLOB)
 if not reg or not sv:return _fail("SCOPED_EVIDENCE_BINDING_INVALID")
 entries=reg.get("entries")
 if not isinstance(entries,list):return _fail("SCOPED_REGISTRY_ENTRIES_INVALID")
 roots={x.get("root_id") for x in entries if isinstance(x,Mapping)}
 if roots!=set(gate.EXPECTED_ROOTS):return _fail("SCOPED_ROOT_COVER_INCOMPLETE",root_ids=sorted(str(x) for x in roots))
 if sv.get("pass") is not True:return _fail("SCOPED_EVIDENCE_VERIFICATION_NOT_PASS")
 if (sv.get("exact_blobs") or {}).get("scoped_registry")!=REGISTRY_BLOB:return _fail("SCOPED_EVIDENCE_REGISTRY_MISMATCH")
 if (sv.get("composition") or {}).get("resulting_scoped_capability_count")!=21:return _fail("SCOPED_CAPABILITY_COUNT_INVALID")

 wl=_read(root,WORKLIST,WORKLIST_BLOB)
 if not wl:return _fail("WORKLIST_INVALID")
 if wl.get("verified_root_subject_binding_count")!=12 or wl.get("composition_admissible") is not False:return _fail("WORKLIST_AUTHORITY_STATE_INVALID")
 rows=wl.get("roots")
 if not isinstance(rows,list) or len(rows)!=12:return _fail("WORKLIST_ROOT_SET_INVALID")
 row_ids={x.get("root_id") for x in rows if isinstance(x,Mapping)}
 if row_ids!=set(gate.EXPECTED_ROOTS):return _fail("WORKLIST_ROOT_COVER_INVALID")

 subject_keys=set(); verified=[]
 for row in rows:
  rid=row.get("root_id")
  br=row.get("binding") or {};vr=row.get("verification") or {}
  bd=_read(root,br.get("path",""),br.get("git_blob_sha",""))
  vd=_read(root,vr.get("path",""),vr.get("git_blob_sha",""))
  if bd is None or vd is None:return _fail("ROOT_RECEIPT_BYTES_INVALID",root_id=rid)
  if bd.get("root_id")!=rid:return _fail("ROOT_BINDING_ID_MISMATCH",root_id=rid)
  norm=compat.normalize(bd)
  if norm.get("pass") is not True:return _fail(norm.get("reason","ROOT_BINDING_COMPAT_FAILED"),root_id=rid)
  kind=norm.get("subject_kind");sid=norm.get("subject_id");sha=norm.get("subject_sha256")
  err=gate._verification_receipt_error(root_id=rid,verification=vd,binding_blob=br.get("git_blob_sha"),subject_kind=kind,subject_id=sid,subject_sha=sha)
  if err is not None:return _fail(err,root_id=rid)
  subject_keys.add((kind,sid,sha));verified.append(rid)
 if subject_keys!={(SKIND,SID,SSH)}:return _fail("ROOT_SUBJECT_BINDINGS_NOT_IDENTICAL",subject_tuples=sorted(map(str,subject_keys)))
 if len(verified)!=12:return _fail("VERIFIED_ROOT_TOTAL_INVALID")

 return {"schema":SCHEMA,"pass":True,"status":"PASS__REAL_V7_12_OF_12_SAME_SUBJECT_COMPOSITION_ADMISSIBLE",
 "composition_admissible":True,"professional_quality_closed":False,
 "subject_kind":SKIND,"subject_id":SID,"subject_sha256":SSH,
 "verified_root_subject_binding_count":12,"scoped_root_count":12,"scoped_capability_count":21,
 "semantic_truth_authority":False,"execution_authority":False,"quality_authority":False,
 "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
 "terminal_credit_delta":0,"incremental_spend_usd":0}

if __name__=="__main__":print(json.dumps(verify(),indent=2,sort_keys=True))
