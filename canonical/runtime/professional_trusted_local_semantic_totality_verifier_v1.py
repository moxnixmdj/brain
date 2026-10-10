"""Generic trusted exact-run semantic-totality verifier for professional semantic claims.

This generalizes the sound R12 repair without transporting any root certificate
across claim IDs.  The verifier re-derives the current frozen claim from the
verified V3 claim pack, binds one exact-run policy-relevant world model to that
claim, requires every policy-adequacy receipt used by the policy-cover solver to
explicitly attest the exact semantic acceptance for the same claim, and then
runs the existing observable policy-cover decision procedure.

It proves exact-run local totality only.  Claim-wide CC_R3 must be obtained
separately by proving that *every* positive route is forced through this exact
verifier for the corresponding claim.
"""
from __future__ import annotations

import hashlib, json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import observable_policy_cover_totality_gate_v1 as cover
from canonical.runtime import professional_semantic_totality_claim_pack_v3 as claim_pack

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_TRUSTED_LOCAL_SEMANTIC_TOTALITY_VERIFIER_V1"
REQUIRED_ACCEPTANCE="DOMAIN_SPECIFIC_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_AND_ALL_ROOT_RELEVANT_DEFEATERS_RESOLVED_WITH_TYPED_EVIDENCE"

def _blob(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _digest(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

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

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
            "local_material_totality_verified":False,
            "semantic_acceptance_bound":False,
            "claim_wide_cc_r3_proved":False,
            "semantic_truth_authority":False,"quality_authority":False,
            "acceptance_authority":False,"promotion_authority":False,
            "terminal_authority":False,"terminal_credit_delta":0,**extra}

def _claim_row(root:Path,claim_id:str)->tuple[dict[str,Any]|None,dict[str,Any]]:
    pack=claim_pack.verify(repo_root=root)
    if pack.get("pass") is not True:
        return None,_fail("CURRENT_SEMANTIC_CLAIM_PACK_NOT_PASS",claim_pack=pack)
    rows=[x for x in pack.get("claims") or [] if isinstance(x,Mapping)
          and isinstance(x.get("frozen_claim"),Mapping)
          and x["frozen_claim"].get("claim_id")==claim_id]
    if len(rows)!=1:
        return None,_fail("CLAIM_ID_NOT_UNIQUE_CURRENT_SEMANTIC_CLAIM",claim_id=claim_id,match_count=len(rows))
    return dict(rows[0]),{}

def verify_certificate(*,root:Path,certificate_path:Path,expected_claim_id:str)->dict[str,Any]:
    root=Path(root).resolve()
    row,err=_claim_row(root,expected_claim_id)
    if row is None: return err
    claim=row["frozen_claim"]; target=row.get("target_predicate") or {}
    if target.get("acceptance")!=REQUIRED_ACCEPTANCE:
        return _fail("CLAIM_ACCEPTANCE_DRIFT",claim_id=expected_claim_id)
    try: cert=json.loads(Path(certificate_path).read_text(encoding="utf-8"))
    except Exception: return _fail("CERTIFICATE_JSON_INVALID",claim_id=expected_claim_id)
    if not isinstance(cert,Mapping): return _fail("CERTIFICATE_NOT_OBJECT",claim_id=expected_claim_id)
    exact={
      "semantic_property_claim_id":claim["claim_id"],
      "semantic_scope_claim_id":row.get("whole_leaf_scope_claim_id"),
      "semantic_obligation":target.get("obligation"),
      "target_scope_semantics":target.get("acceptance"),
      "real_exact_run":True,
      "content_addressed":True,
    }
    for k,v in exact.items():
        if cert.get(k)!=v: return _fail("CERTIFICATE_BINDING_MISMATCH:"+k,claim_id=expected_claim_id)
    pp=_safe(root,cert.get("policy_cover_problem_ref"),"canonical/evidence/")
    vp=_safe(root,cert.get("policy_cover_verification_ref"),"canonical/verification/")
    if pp is None:return _fail("POLICY_COVER_PROBLEM_REF_INVALID",claim_id=expected_claim_id)
    if vp is None:return _fail("POLICY_COVER_VERIFICATION_REF_INVALID",claim_id=expected_claim_id)
    try:
        problem=json.loads(pp.read_text(encoding="utf-8"))
        iv=json.loads(vp.read_text(encoding="utf-8"))
    except Exception:return _fail("BOUND_JSON_INVALID",claim_id=expected_claim_id)
    for k,v in exact.items():
        if problem.get(k)!=v:return _fail("PROBLEM_BINDING_MISMATCH:"+k,claim_id=expected_claim_id)
    cp=problem.get("policy_cover_problem")
    if not isinstance(cp,Mapping):return _fail("POLICY_COVER_PROBLEM_REQUIRED",claim_id=expected_claim_id)
    wc=cp.get("world_set_completeness_receipt")
    if not isinstance(wc,Mapping) or wc.get("semantic_claim_id")!=expected_claim_id or wc.get("claim_scoped_world_set_complete") is not True:
        return _fail("WORLD_SET_COMPLETENESS_NOT_CLAIM_BOUND",claim_id=expected_claim_id)
    for pol in cp.get("policies") or []:
        if not isinstance(pol,Mapping):return _fail("POLICY_NOT_MAPPING",claim_id=expected_claim_id)
        ar=pol.get("adequacy_receipt")
        if not isinstance(ar,Mapping):return _fail("POLICY_ADEQUACY_RECEIPT_REQUIRED",claim_id=expected_claim_id)
        if ar.get("semantic_claim_id")!=expected_claim_id:
            return _fail("POLICY_ADEQUACY_CLAIM_MISMATCH",claim_id=expected_claim_id)
        if ar.get("semantic_acceptance_satisfied_on_every_listed_world") is not True:
            return _fail("POLICY_SEMANTIC_ACCEPTANCE_NOT_PROVED",claim_id=expected_claim_id)
        if ar.get("semantic_acceptance_sha256")!=hashlib.sha256(REQUIRED_ACCEPTANCE.encode()).hexdigest():
            return _fail("POLICY_SEMANTIC_ACCEPTANCE_HASH_MISMATCH",claim_id=expected_claim_id)
    verdict=cover.evaluate(cp)
    if verdict.get("pass") is not True or verdict.get("bound_state_totality_proved") is not True:
        return _fail("POLICY_COVER_TOTALITY_NOT_PROVED",claim_id=expected_claim_id,policy_cover_verdict=verdict)
    pd=_digest(problem)
    req={
      "pass":True,"independent_verified":True,"problem_sha256":pd,
      "semantic_property_claim_id":expected_claim_id,
      "semantic_scope_claim_id":row.get("whole_leaf_scope_claim_id"),
      "policy_relevant_world_set_complete":True,"policy_cover_replay_pass":True,
    }
    for k,v in req.items():
        if iv.get(k)!=v:return _fail("INDEPENDENT_VERIFY_MISMATCH:"+k,claim_id=expected_claim_id)
    if not isinstance(iv.get("independent_verifier_id"),str) or not iv.get("independent_verifier_id"):
        return _fail("INDEPENDENT_VERIFIER_ID_REQUIRED",claim_id=expected_claim_id)
    if cert.get("policy_cover_problem_sha256")!=pd:
        return _fail("PROBLEM_DIGEST_MISMATCH",claim_id=expected_claim_id)
    return {"schema":SCHEMA,"pass":True,
      "status":"PASS__TRUSTED_EXACT_RUN_SEMANTIC_TOTALITY",
      "claim_id":expected_claim_id,"leaf_id":row.get("leaf_id"),
      "scope_claim_id":row.get("whole_leaf_scope_claim_id"),
      "semantic_acceptance_bound":True,
      "local_material_totality_verified":True,
      "policy_cover_result_sha256":_digest(verdict),
      "claim_wide_cc_r3_proved":False,
      "proof_basis":"CONTENT_ADDRESSED_CLAIM_BOUND_EXACT_RUN_POLICY_COVER",
      "semantic_truth_authority":False,"quality_authority":False,
      "acceptance_authority":False,"promotion_authority":False,
      "terminal_authority":False,"terminal_credit_delta":0}
