"""Exact V9 -> V10 positive-route refinement verifier.

V10 preserves V9 execution and adds only a fail-closed fixed-verifier gate after
V9 has already produced a positive candidate. Therefore V10 cannot create a
positive route that V9 did not have; it can only reject a V9-positive route.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_V9_TO_V10_R12_POSITIVE_REFINEMENT_V1"
V9_PATH="canonical/runtime/professional_quality_p1_router_v9.py"
V9_BLOB="27f0df972a08a2497802865e46bdccdcb1c720ae"
V10_PATH="canonical/runtime/professional_quality_p1_router_v10.py"
V10_BLOB="480607e1575397504ac7170d74ddf8ad312f8ffc"
TRUSTED_PATH="canonical/runtime/professional_r12_trusted_local_totality_verifier_v1.py"
TRUSTED_BLOB="2778edd768c340b204580e625441278a4da114be"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V10_DECLARED_SYSTEM_SUBJECT_20261011_V1.json"
SUBJECT_BLOB="71333ce3c40ec8e500e05a6f6b92f425db771a11"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V10_FIXED_TRUSTED_R12_TOTALITY_SYSTEM_20261011_V1"
SUBJECT_SHA256="bb9dfcec9e006aebebcfa904ff6bf096aa01c62392f16f5915c2bf8e7fca1be5"

def _blob(p:Path)->str:
 d=p.read_bytes();return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _load(root:Path,rel:str,blob:str)->Path:
 p=root/rel
 if not p.is_file() or p.is_symlink() or _blob(p)!=blob: raise ValueError("PIN_INVALID:"+rel)
 return p

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 try:
  _load(root,V9_PATH,V9_BLOB);v10p=_load(root,V10_PATH,V10_BLOB);_load(root,TRUSTED_PATH,TRUSTED_BLOB)
  sp=_load(root,SUBJECT_PATH,SUBJECT_BLOB)
  subject=json.loads(sp.read_text(encoding="utf-8"))
 except Exception as exc:
  return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":type(exc).__name__+":"+str(exc),
          "positive_route_refinement_proved":False,"universal_fixed_verifier_gate_proved":False}
 if subject.get("subject_id")!=SUBJECT_ID or subject.get("subject_sha256")!=SUBJECT_SHA256:
  return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"SUBJECT_IDENTITY_MISMATCH",
          "positive_route_refinement_proved":False,"universal_fixed_verifier_gate_proved":False}
 text=v10p.read_text(encoding="utf-8")
 anchors=[
  "out=base.route(state,repo_root=root)",
  'if result.get("final_step_outcome")!="POSITIVE_CERTIFICATE" or result.get("positive_certification_authorized") is not True:',
  'return _fail("V10_UNTRUSTED_SEMANTIC_VERIFIER_REJECTED")',
  "local=trusted.verify_certificate(",
  'if local.get("pass") is not True or local.get("local_material_totality_verified") is not True:',
  'return _fail("V10_TRUSTED_LOCAL_TOTALITY_REJECTED"',
  'result["v10_trusted_local_totality_verified"]=True',
 ]
 missing=[a for a in anchors if a not in text]
 if missing:
  return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"CONTROL_FLOW_ANCHOR_MISSING",
          "missing":missing,"positive_route_refinement_proved":False,"universal_fixed_verifier_gate_proved":False}
 order=[text.index(a) for a in anchors]
 if order!=sorted(order):
  return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":"CONTROL_FLOW_ORDER_INVALID",
          "positive_route_refinement_proved":False,"universal_fixed_verifier_gate_proved":False}
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__V10_IS_FAIL_CLOSED_POSITIVE_ROUTE_REFINEMENT_OF_EXACT_V9",
  "v9_router_blob":V9_BLOB,"v10_router_blob":V10_BLOB,
  "v10_subject_id":SUBJECT_ID,"v10_subject_sha256":SUBJECT_SHA256,
  "positive_route_refinement_proved":True,
  "preexisting_v9_execution_preserved_before_new_gate":True,
  "v10_can_add_positive_route":False,
  "v10_can_only_preserve_or_reject_v9_positive_route":True,
  "universal_fixed_verifier_gate_proved":True,
  "trusted_local_totality_verifier_path":TRUSTED_PATH,
  "trusted_local_totality_verifier_blob":TRUSTED_BLOB,
  "cross_subject_property_authority_transport":False,
  "c8_nonvacuity_transport_proved":False,
  "quality_authority":False,"promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0}
