"""Executable semantic authority for R12 material-totality certificates.

A stored totality certificate or stored PASS receipt has zero semantic authority
unless a content-addressed semantic verifier is rerun over the exact certificate
and exact R12 binding and the independent receipt binds that rerun result.

This deliberately reuses the proven coverage-root semantic-receipt pattern.
It grants no quality, acceptance, promotion, or terminal authority.
"""
from __future__ import annotations
import hashlib, importlib.util, json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_TOTALITY_SEMANTIC_AUTHORITY_V1"
PROTOCOL="PROFESSIONAL_R12_TOTALITY_SEMANTIC_VERIFIER_V1"
RECEIPT_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_TOTALITY_SEMANTIC_INDEPENDENT_VERIFY_V1"
ALLOWED_PROOF_MODES=frozenset({"KERNEL_CHECKED","DECISION_PROCEDURE","MODEL_CHECKED","FORMAL_REDUCTION","INDEPENDENT_REPLAY"})
AUTHORITY_KEYS=("semantic_truth_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority")

def _blob(path:Path)->str:
 data=path.read_bytes()
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def _safe(root:Path,ref:Any,prefixes:tuple[str,...])->tuple[Path,str,str]|None:
 if not isinstance(ref,Mapping): return None
 rel=ref.get("path");expected=ref.get("git_blob_sha")
 if not isinstance(rel,str) or not rel or rel.startswith("/"): return None
 p=Path(rel)
 if ".." in p.parts or not any(rel.startswith(x) for x in prefixes): return None
 full=(root/p).resolve()
 try: full.relative_to(root.resolve())
 except ValueError: return None
 if not full.is_file() or full.is_symlink(): return None
 if not isinstance(expected,str) or not expected or _blob(full)!=expected:return None
 return full,rel,expected

def _fail(*errors:str)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":sorted(set(errors)),
  "semantic_totality_verified":False,"semantic_truth_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0}

def _run_verifier(*,verifier_path:Path,root:Path,certificate_path:Path,expected_binding:Mapping[str,Any])->Any:
 spec=importlib.util.spec_from_file_location("professional_r12_totality_semantic_verifier_runtime",verifier_path)
 if spec is None or spec.loader is None: raise RuntimeError("SEMANTIC_VERIFIER_LOAD_SPEC_FAILED")
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 fn=getattr(module,"verify_certificate",None)
 if not callable(fn): raise RuntimeError("SEMANTIC_VERIFIER_ENTRYPOINT_MISSING")
 return fn(root=root,certificate_path=certificate_path,expected_binding=dict(expected_binding))

def validate(*,root:Path,certificate_ref:Mapping[str,Any],semantic_verifier_ref:Mapping[str,Any],
             independent_verification_ref:Mapping[str,Any],expected_binding:Mapping[str,Any])->dict[str,Any]:
 root=root.resolve()
 required=("semantic_property_claim_id","semantic_scope_claim_id","semantic_obligation","target_scope_semantics")
 if not isinstance(expected_binding,Mapping):return _fail("EXPECTED_BINDING_NOT_MAPPING")
 if any(not isinstance(expected_binding.get(k),str) or not expected_binding.get(k) for k in required):
  return _fail("EXPECTED_BINDING_INCOMPLETE")
 resolved={}
 for label,ref,prefixes in (
  ("certificate",certificate_ref,("canonical/governance/","canonical/evidence/","canonical/verification/")),
  ("semantic_verifier",semantic_verifier_ref,("canonical/runtime/","canonical/verification/")),
  ("independent_verification",independent_verification_ref,("canonical/verification/",)),
 ):
  x=_safe(root,ref,prefixes)
  if x is None:return _fail(label.upper()+"_REF_OR_BLOB_INVALID")
  resolved[label]=x
 cert_path,cert_rel,cert_blob=resolved["certificate"]
 verifier_path,verifier_rel,verifier_blob=resolved["semantic_verifier"]
 receipt_path,receipt_rel,receipt_blob=resolved["independent_verification"]
 try:cert=json.loads(cert_path.read_text(encoding="utf-8"))
 except Exception:return _fail("CERTIFICATE_JSON_INVALID")
 if not isinstance(cert,Mapping):return _fail("CERTIFICATE_NOT_OBJECT")
 for k in required:
  if cert.get(k)!=expected_binding.get(k):return _fail("CERTIFICATE_BINDING_MISMATCH:"+k)
 for k in AUTHORITY_KEYS:
  if cert.get(k) is not False:return _fail("CERTIFICATE_AUTHORITY_OVERCLAIM:"+k)
 try:
  rerun=_run_verifier(verifier_path=verifier_path,root=root,certificate_path=cert_path,expected_binding=expected_binding)
 except Exception as exc:return _fail("SEMANTIC_VERIFIER_EXCEPTION:"+type(exc).__name__+":"+str(exc))
 if not isinstance(rerun,Mapping):return _fail("SEMANTIC_VERIFIER_RESULT_NOT_OBJECT")
 if rerun.get("pass") is not True:return _fail("SEMANTIC_VERIFIER_REJECTED_CERTIFICATE")
 if rerun.get("semantic_totality_verified") is not True:return _fail("SEMANTIC_VERIFIER_TOTALITY_NOT_PROVED")
 for k in required:
  if rerun.get(k)!=expected_binding.get(k):return _fail("SEMANTIC_VERIFIER_BINDING_MISMATCH:"+k)
 if any(rerun.get(k) is not False for k in AUTHORITY_KEYS):return _fail("SEMANTIC_VERIFIER_AUTHORITY_OVERCLAIM")
 result_sha=hashlib.sha256(json.dumps(rerun,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
 try:receipt=json.loads(receipt_path.read_text(encoding="utf-8"))
 except Exception:return _fail("INDEPENDENT_RECEIPT_JSON_INVALID")
 if not isinstance(receipt,Mapping):return _fail("INDEPENDENT_RECEIPT_NOT_OBJECT")
 checks=(
  (receipt.get("schema")==RECEIPT_SCHEMA,"RECEIPT_SCHEMA_INVALID"),
  (receipt.get("verifier_protocol")==PROTOCOL,"RECEIPT_PROTOCOL_INVALID"),
  (receipt.get("pass") is True,"RECEIPT_PASS_NOT_TRUE"),
  (receipt.get("independent") is True,"RECEIPT_NOT_INDEPENDENT"),
  (receipt.get("semantic_claim_verified") is True,"RECEIPT_SEMANTIC_CLAIM_NOT_VERIFIED"),
  (receipt.get("proof_mode") in ALLOWED_PROOF_MODES,"RECEIPT_PROOF_MODE_INVALID"),
  (receipt.get("verifier_result_sha256")==result_sha,"RECEIPT_RERUN_RESULT_MISMATCH"),
  (receipt.get("terminal_credit_delta",0)==0,"RECEIPT_TERMINAL_CREDIT_NONZERO"),
  (receipt.get("errors")==[],"RECEIPT_ERRORS_NONEMPTY"),
 )
 errors=[e for ok,e in checks if not ok]
 for k in required:
  if receipt.get(k)!=expected_binding.get(k):errors.append("RECEIPT_BINDING_MISMATCH:"+k)
 rc=receipt.get("certificate") or {};rv=receipt.get("semantic_verifier") or {}
 if rc.get("path")!=cert_rel or rc.get("git_blob_sha")!=cert_blob:errors.append("RECEIPT_CERTIFICATE_BINDING_MISMATCH")
 if rv.get("path")!=verifier_rel or rv.get("git_blob_sha")!=verifier_blob:errors.append("RECEIPT_VERIFIER_BINDING_MISMATCH")
 if errors:return _fail(*errors)
 return {"schema":SCHEMA,"pass":True,"status":"PASS__EXECUTABLE_R12_TOTALITY_SEMANTIC_VERIFICATION",
  "semantic_totality_verified":True,**{k:expected_binding[k] for k in required},
  "certificate_path":cert_rel,"certificate_git_blob_sha":cert_blob,
  "semantic_verifier_path":verifier_rel,"semantic_verifier_git_blob_sha":verifier_blob,
  "independent_verification_path":receipt_rel,"independent_verification_git_blob_sha":receipt_blob,
  "verifier_result_sha256":result_sha,"proof_mode":receipt.get("proof_mode"),
  "semantic_truth_authority":False,"quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}
