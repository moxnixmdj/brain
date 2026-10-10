"""Trusted generic local-totality verifier for R12 positive routes.

This verifier proves only exact-run material-defeater totality. It never promotes a
single run to claim-wide CC_R3. Claim-wide CC_R3 comes from a universal
control-flow invariant: every positive route must pass this fixed verifier.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_v9_r12_reuse_closure_v1 as reuse

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_TRUSTED_LOCAL_TOTALITY_VERIFIER_V1"
R12_RECON_PATH="canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_TRUTH_RECONCILIATION_20261010_V3.json"
R12_RECON_BLOB="56a5f85e6133661dd7afbc8fc5041ad799f0736f"
REQUIRED=("semantic_property_claim_id","semantic_scope_claim_id","semantic_obligation","target_scope_semantics")

def _blob(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _safe(root:Path,ref:Any,prefix:str)->Path|None:
    if not isinstance(ref,Mapping): return None
    rel=ref.get("path"); expected=ref.get("git_blob_sha")
    if not isinstance(rel,str) or not rel.startswith(prefix) or rel.startswith("/"): return None
    p=Path(rel)
    if ".." in p.parts: return None
    full=(root/p).resolve()
    try: full.relative_to(root.resolve())
    except ValueError: return None
    if not full.is_file() or full.is_symlink(): return None
    if not isinstance(expected,str) or _blob(full)!=expected: return None
    return full

def _fail(reason:str)->dict[str,Any]:
    return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
            "local_material_totality_verified":False,"semantic_totality_verified":False,
            "semantic_truth_authority":False,"quality_authority":False,
            "acceptance_authority":False,"promotion_authority":False,
            "terminal_authority":False}

def verify_certificate(*,root:Path,certificate_path:Path,expected_binding:Mapping[str,Any])->dict[str,Any]:
    root=Path(root).resolve()
    try: cert=json.loads(Path(certificate_path).read_text(encoding="utf-8"))
    except Exception: return _fail("CERTIFICATE_JSON_INVALID")
    if not isinstance(cert,Mapping): return _fail("CERTIFICATE_NOT_OBJECT")
    for k in REQUIRED:
        if cert.get(k)!=expected_binding.get(k): return _fail("CERTIFICATE_BINDING_MISMATCH:"+k)
    problem_path=_safe(root,cert.get("policy_cover_problem_ref"),"canonical/evidence/")
    if problem_path is None: return _fail("POLICY_COVER_PROBLEM_REF_INVALID")
    iv_path=_safe(root,cert.get("policy_cover_verification_ref"),"canonical/verification/")
    if iv_path is None: return _fail("POLICY_COVER_VERIFICATION_REF_INVALID")
    r12_path=root/R12_RECON_PATH
    if not r12_path.is_file() or r12_path.is_symlink() or _blob(r12_path)!=R12_RECON_BLOB:
        return _fail("R12_RECONCILIATION_PIN_INVALID")
    try:
        problem=json.loads(problem_path.read_text(encoding="utf-8"))
        iv=json.loads(iv_path.read_text(encoding="utf-8"))
        r12=json.loads(r12_path.read_text(encoding="utf-8"))
    except Exception: return _fail("DEPENDENCY_JSON_INVALID")
    digest=hashlib.sha256(json.dumps(problem,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    if cert.get("policy_cover_problem_sha256")!=digest: return _fail("POLICY_COVER_PROBLEM_DIGEST_MISMATCH")
    out=reuse.evaluate_v9_totality_cover(problem,iv,r12_reconciliation=r12)
    if out.get("pass") is not True: return _fail("LOCAL_POLICY_COVER_REJECTED")
    if out.get("v9_bound_state_material_defeater_totality_proved") is not True:
        return _fail("LOCAL_MATERIAL_TOTALITY_NOT_PROVED")
    return {"schema":SCHEMA,"pass":True,
            "status":"PASS__TRUSTED_EXACT_RUN_R12_MATERIAL_TOTALITY",
            "local_material_totality_verified":True,
            "semantic_totality_verified":True,
            **{k:expected_binding[k] for k in REQUIRED},
            "proof_basis":"CONTENT_ADDRESSED_EXACT_RUN_POLICY_COVER",
            "semantic_truth_authority":False,"quality_authority":False,
            "acceptance_authority":False,"promotion_authority":False,
            "terminal_authority":False}
