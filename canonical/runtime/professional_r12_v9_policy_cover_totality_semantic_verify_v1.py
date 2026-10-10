"""Executable semantic verifier for a V9 R12 policy-cover totality certificate.

This is the claim-scoped bridge from the already-verified observable-policy-cover
and generator-closure machinery into V9's executable semantic firewall.

It proves material-defeater totality only. It never mints C8/nonvacuity,
property truth, quality, acceptance, promotion, or terminal authority.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_v9_r12_reuse_closure_v1 as reuse

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_V9_POLICY_COVER_TOTALITY_SEMANTIC_VERIFIER_V1"
CERT_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_V9_POLICY_COVER_TOTALITY_CERTIFICATE_V1"
CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
CLAIM_PATH="canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261010_V2.json"
CLAIM_BLOB="7b26ddba501358d42d6fa342efd27d389bb30654"
AUTH_KEYS=("semantic_truth_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority")


def _blob(path:Path)->str:
    raw=path.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _fail(reason:str, expected:Mapping[str,Any]|None=None)->dict[str,Any]:
    out={"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
         "semantic_totality_verified":False,**{k:False for k in AUTH_KEYS}}
    if isinstance(expected,Mapping):
        for k in ("semantic_property_claim_id","semantic_scope_claim_id","semantic_obligation","target_scope_semantics"):
            if isinstance(expected.get(k),str): out[k]=expected[k]
    out["terminal_credit_delta"]=0;out["incremental_spend_usd"]=0
    return out


def _ref(root:Path, ref:Any, prefixes:tuple[str,...])->Path|None:
    if not isinstance(ref,Mapping): return None
    rel=ref.get("path"); expected=ref.get("git_blob_sha")
    if not isinstance(rel,str) or not rel or rel.startswith("/") or ".." in Path(rel).parts:return None
    if not any(rel.startswith(p) for p in prefixes):return None
    full=(root/rel).resolve()
    try: full.relative_to(root.resolve())
    except ValueError:return None
    if not full.is_file() or full.is_symlink():return None
    if not isinstance(expected,str) or _blob(full)!=expected:return None
    return full


def verify_certificate(*,root:Path,certificate_path:Path,expected_binding:Mapping[str,Any])->dict[str,Any]:
    root=root.resolve()
    try: cert=json.loads(certificate_path.read_text(encoding="utf-8"))
    except Exception:return _fail("CERTIFICATE_JSON_INVALID",expected_binding)
    if not isinstance(cert,Mapping) or cert.get("schema")!=CERT_SCHEMA:
        return _fail("CERTIFICATE_SCHEMA_INVALID",expected_binding)
    for k in ("semantic_property_claim_id","semantic_scope_claim_id","semantic_obligation","target_scope_semantics"):
        if cert.get(k)!=expected_binding.get(k):return _fail("BINDING_MISMATCH:"+k,expected_binding)
    if cert.get("claim_id")!=CLAIM_ID:return _fail("STABLE_CLAIM_ID_MISMATCH",expected_binding)
    if cert.get("v9_subject_id")!=reuse.V9_SUBJECT_ID or cert.get("v9_subject_sha256")!=reuse.V9_SUBJECT_SHA256:
        return _fail("V9_SUBJECT_MISMATCH",expected_binding)
    if cert.get("real_exact_run") is not True or cert.get("content_addressed") is not True:
        return _fail("REAL_CONTENT_ADDRESSED_CERTIFICATE_REQUIRED",expected_binding)
    if any(cert.get(k) is not False for k in AUTH_KEYS):
        return _fail("CERTIFICATE_AUTHORITY_OVERCLAIM",expected_binding)

    claim_ref=cert.get("active_claim") or {}
    if claim_ref.get("path")!=CLAIM_PATH or claim_ref.get("git_blob_sha")!=CLAIM_BLOB:
        return _fail("ACTIVE_CLAIM_REF_MISMATCH",expected_binding)
    claim_path=_ref(root,claim_ref,("canonical/governance/",))
    if claim_path is None:return _fail("ACTIVE_CLAIM_REF_INVALID",expected_binding)
    try: claim=json.loads(claim_path.read_text(encoding="utf-8"))
    except Exception:return _fail("ACTIVE_CLAIM_JSON_INVALID",expected_binding)
    if claim.get("claim_id")!=CLAIM_ID:return _fail("ACTIVE_CLAIM_BYTES_MISMATCH",expected_binding)

    problem_path=_ref(root,cert.get("policy_cover_problem_ref"),("canonical/evidence/","canonical/verification/"))
    verify_path=_ref(root,cert.get("independent_cover_verification_ref"),("canonical/verification/",))
    recon_path=_ref(root,cert.get("r12_reconciliation_ref"),("canonical/governance/",))
    if problem_path is None:return _fail("POLICY_COVER_PROBLEM_REF_INVALID",expected_binding)
    if verify_path is None:return _fail("INDEPENDENT_COVER_VERIFICATION_REF_INVALID",expected_binding)
    if recon_path is None:return _fail("R12_RECONCILIATION_REF_INVALID",expected_binding)
    try:
        problem=json.loads(problem_path.read_text(encoding="utf-8"))
        independent=json.loads(verify_path.read_text(encoding="utf-8"))
        reconciliation=json.loads(recon_path.read_text(encoding="utf-8"))
    except Exception:return _fail("REFERENCED_JSON_INVALID",expected_binding)

    out=reuse.evaluate_v9_totality_cover(problem,independent,r12_reconciliation=reconciliation)
    if out.get("pass") is not True:return _fail("V9_POLICY_COVER_REJECTED:"+str(out.get("reason") or "UNKNOWN"),expected_binding)
    if out.get("v9_material_defeater_totality_proved") is not True or out.get("cc_r3_terminal_closure_proved") is not True:
        return _fail("V9_POLICY_COVER_TOTALITY_NOT_PROVED",expected_binding)
    if out.get("v9_c8_nonvacuity_proved") is not False:
        return _fail("C8_MUST_REMAIN_SEPARATE",expected_binding)

    return {"schema":SCHEMA,"pass":True,
      "status":"PASS__EXECUTABLE_V9_POLICY_COVER_MATERIAL_TOTALITY__C8_SEPARATE",
      "semantic_totality_verified":True,
      **{k:expected_binding[k] for k in ("semantic_property_claim_id","semantic_scope_claim_id","semantic_obligation","target_scope_semantics")},
      "claim_id":CLAIM_ID,"v9_subject_id":reuse.V9_SUBJECT_ID,"v9_subject_sha256":reuse.V9_SUBJECT_SHA256,
      "cc_r3_material_totality_proved":True,"c8_nonvacuity_proved":False,
      **{k:False for k in AUTH_KEYS},"terminal_credit_delta":0,"incremental_spend_usd":0}
