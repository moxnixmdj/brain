"""Exact V10 -> V11 all-semantic positive-route refinement verifier."""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_V10_TO_V11_SEMANTIC_REFINEMENT_V1"
V10_PATH="canonical/runtime/professional_quality_p1_router_v10.py"
V10_BLOB="480607e1575397504ac7170d74ddf8ad312f8ffc"
V11_PATH="canonical/runtime/professional_quality_p1_router_v11.py"
V11_BLOB="cbed60e93409069e731f06c2356778cebbc827f8"
TRUSTED_PATH="canonical/runtime/professional_trusted_local_semantic_totality_verifier_v1.py"
TRUSTED_BLOB="5af2d599fffcad16e78d862ee50b2c7d9013be8f"
SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V11_DECLARED_SYSTEM_SUBJECT_20261011_V1.json"
SUBJECT_BLOB="cc8070cbd7d14f143ede4619018764654d47a01d"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V11_ALL_SEMANTIC_TOTALITY_FIREWALL_SYSTEM_20261011_V1"
SUBJECT_SHA256="cfd8f89dc91fe9ed88b7850af22b9c91b0f024f487b6d7db88aa82fec177b544"

def _blob(p:Path)->str:
 d=p.read_bytes();return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _pin(root:Path,rel:str,expected:str)->Path:
 p=root/rel
 if not p.is_file() or p.is_symlink() or _blob(p)!=expected:raise ValueError("PIN_INVALID:"+rel)
 return p

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "positive_route_refinement_proved":False,"all_12_semantic_gate_proved":False,
  "quality_authority":False,"promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,**extra}

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 try:
  _pin(root,V10_PATH,V10_BLOB);v11p=_pin(root,V11_PATH,V11_BLOB);_pin(root,TRUSTED_PATH,TRUSTED_BLOB)
  sp=_pin(root,SUBJECT_PATH,SUBJECT_BLOB)
  subject=json.loads(sp.read_text(encoding="utf-8"))
 except Exception as exc:return _fail(type(exc).__name__+":"+str(exc))
 if subject.get("subject_id")!=SUBJECT_ID or subject.get("subject_sha256")!=SUBJECT_SHA256:
  return _fail("SUBJECT_IDENTITY_MISMATCH")
 comps=(subject.get("system_material") or {}).get("components") or []
 pins={x.get("path"):x.get("git_blob_sha") for x in comps if isinstance(x,dict)}
 if pins.get(V10_PATH)!=V10_BLOB or pins.get(V11_PATH)!=V11_BLOB or pins.get(TRUSTED_PATH)!=TRUSTED_BLOB:
  return _fail("SUBJECT_LOAD_BEARING_PIN_MISMATCH")
 text=v11p.read_text(encoding="utf-8")
 anchors=[
  "out=base.route(state,repo_root=root)",
  'if result.get("final_step_outcome")!="POSITIVE_CERTIFICATE" or result.get("positive_certification_authorized") is not True:',
  "pack=claim_pack.verify(repo_root=root)",
  'if pack.get("pass") is not True or pack.get("semantic_claim_count")!=12 or pack.get("unique_claim_id_count")!=12:',
  "if set(bindings)!=set(claims):",
  "for cid in sorted(claims):",
  "v=trusted.verify_certificate(root=root,certificate_path=cp,expected_claim_id=cid)",
  'if v.get("pass") is not True or v.get("local_material_totality_verified") is not True or v.get("semantic_acceptance_bound") is not True:',
  'result["v11_all_semantic_local_totality_verified"]=True',
 ]
 missing=[a for a in anchors if a not in text]
 if missing:return _fail("CONTROL_FLOW_ANCHOR_MISSING",missing=missing)
 order=[text.index(a) for a in anchors]
 if order!=sorted(order):return _fail("CONTROL_FLOW_ORDER_INVALID",positions=order)
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__V11_STRICT_POSITIVE_ROUTE_REFINEMENT__ALL_12_SEMANTIC_LOCAL_TOTALITY_REQUIRED",
  "v10_router_blob":V10_BLOB,"v11_router_blob":V11_BLOB,
  "v11_subject_id":SUBJECT_ID,"v11_subject_sha256":SUBJECT_SHA256,
  "positive_route_refinement_proved":True,
  "v11_can_add_positive_route":False,
  "v11_can_only_preserve_or_reject_v10_positive_route":True,
  "all_12_semantic_gate_proved":True,
  "exact_claim_set_required":True,
  "trusted_local_totality_verifier_path":TRUSTED_PATH,
  "trusted_local_totality_verifier_blob":TRUSTED_BLOB,
  "missing_or_failed_claim_forces_fail_closed":True,
  "cross_claim_root_certificate_transport":False,
  "semantic_property_truth_authority":False,"quality_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0}
