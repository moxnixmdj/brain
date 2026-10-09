"""Decision-relative semantic policy-cover bridge V1.

Turns an independently authenticated finite semantic candidate partition into the
existing verified P3 robust policy-adequacy CEGAR problem. The bridge never
identifies the true semantic candidate. If one verified Brain-owned policy is
adequate for every candidate, ambiguity is decision-irrelevant. Otherwise P3 may
select the cheapest declared truthful one-bit discriminator.

This removes any requirement to construct complete terminal signatures merely
to prove a common action.
"""
from __future__ import annotations
from hashlib import sha1,sha256
import json
from pathlib import Path
from typing import Any,Mapping,Sequence

from canonical.runtime import p3_robust_policy_adequacy_cegar_v1 as p3

SCHEMA="PROJECT_BRAIN_SEMANTIC_POLICY_COVER_CONTROL_V1"
UNIVERSE_SCHEMA="PROJECT_BRAIN_SEMANTIC_CANDIDATE_UNIVERSE_CERTIFICATE_V1"
UNIVERSE_VERIFY_SCHEMA="PROJECT_BRAIN_SEMANTIC_CANDIDATE_UNIVERSE_INDEPENDENT_VERIFICATION_V1"
MAX_CANDIDATES=12
MAX_DISCRIMINATORS=128

def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)
def _sha(v:Any)->str:
    return sha256(_canon(v).encode()).hexdigest()
def _blob(path:Path)->str:
    raw=path.read_bytes(); return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def candidate_atom(cid:str)->str:
    return "SEMANTIC_CANDIDATE::"+cid
def _bound(root:Path,raw:Any,prefixes:tuple[str,...])->Path:
    s=str(raw or "").strip(); rel=Path(s)
    if not s or rel.is_absolute() or ".." in rel.parts or not any(s.startswith(x) for x in prefixes):
        raise ValueError("BOUND_PATH_INVALID")
    base=root.resolve(strict=True); path=base/rel
    resolved=path.resolve(strict=False)
    if not any(resolved.is_relative_to((base/x).resolve(strict=False)) for x in prefixes):
        raise ValueError("BOUND_PATH_ESCAPE")
    if not path.is_file() or path.is_symlink(): raise ValueError("BOUND_FILE_INVALID")
    return path
def _load(path:Path)->Mapping[str,Any]:
    out=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(out,Mapping): raise ValueError("BOUND_JSON_NOT_OBJECT")
    return out

def _authenticate_universe(root:Path,uid:str,candidates:list[str],binding:Any)->dict[str,Any]:
    if not isinstance(binding,Mapping): raise ValueError("CANDIDATE_UNIVERSE_BINDING_REQUIRED")
    cert=_bound(root,binding.get("certificate_path"),("canonical/governance/","canonical/verification/"))
    ver=_bound(root,binding.get("independent_verification_path"),("canonical/verification/",))
    cb=_blob(cert); vb=_blob(ver)
    if binding.get("certificate_blob_sha")!=cb: raise ValueError("CANDIDATE_UNIVERSE_CERTIFICATE_BLOB_DRIFT")
    if binding.get("independent_verification_blob_sha")!=vb: raise ValueError("CANDIDATE_UNIVERSE_VERIFICATION_BLOB_DRIFT")
    c=_load(cert); v=_load(ver)
    required={"schema":UNIVERSE_SCHEMA,"universe_id":uid,"candidate_ids_sha256":_sha(candidates),"candidate_count":len(candidates),"candidate_set_completeness_proved":True,"candidate_partition_exclusive_and_exhaustive_proved":True}
    if any(c.get(k)!=x for k,x in required.items()): raise ValueError("CANDIDATE_UNIVERSE_CERTIFICATE_INVALID")
    required={"schema":UNIVERSE_VERIFY_SCHEMA,"universe_id":uid,"subject_git_blob_sha":cb,"pass":True,"candidate_set_completeness_independently_verified":True,"candidate_partition_independently_verified":True}
    if any(v.get(k)!=x for k,x in required.items()): raise ValueError("CANDIDATE_UNIVERSE_VERIFICATION_INVALID")
    return {"universe_id":uid,"candidate_ids_sha256":_sha(candidates),"certificate_blob_sha":cb,"independent_verification_blob_sha":vb}

def _or_atoms(ids:list[str])->dict[str,Any]:
    rows=[{"op":"ATOM","id":candidate_atom(x)} for x in ids]
    if len(rows)==1:return rows[0]
    return {"op":"OR","args":rows}

def _base(status:str,passed:bool,**extra:Any)->dict[str,Any]:
    return {"schema":SCHEMA,"status":status,"pass":passed,"semantic_truth_authority":False,"observation_truth_authority":False,"execution_authority":False,"promotion_authority":False,"acceptance_authority":False,"terminal_authority":False,"terminal_credit_delta":0,**extra}

def solve(problem:Mapping[str,Any],*,repo_root:str|Path)->dict[str,Any]:
    old=p3.ROOT
    try:
        if not isinstance(problem,Mapping): raise ValueError("PROBLEM_MAPPING_REQUIRED")
        root=Path(repo_root).resolve(strict=True)
        uid=str(problem.get("universe_id") or "").strip()
        raw=problem.get("candidate_ids")
        if not uid or not isinstance(raw,Sequence) or isinstance(raw,(str,bytes)) or not raw or len(raw)>MAX_CANDIDATES:
            raise ValueError("UNIVERSE_ID_OR_CANDIDATES_INVALID")
        candidates=sorted(str(x).strip() for x in raw)
        if any(not x for x in candidates) or len(candidates)!=len(set(candidates)):
            raise ValueError("CANDIDATE_IDS_INVALID_OR_DUPLICATE")
        auth=_authenticate_universe(root,uid,candidates,problem.get("candidate_universe_binding"))
        basis=[candidate_atom(x) for x in candidates]
        xor={"op":"XOR","args":[{"op":"ATOM","id":x} for x in basis]}
        raw_disc=problem.get("discriminators",[])
        if not isinstance(raw_disc,Sequence) or isinstance(raw_disc,(str,bytes)) or len(raw_disc)>MAX_DISCRIMINATORS:
            raise ValueError("DISCRIMINATORS_INVALID")
        discriminators=[]
        cset=set(candidates)
        for i,row in enumerate(raw_disc):
            if not isinstance(row,Mapping): raise ValueError("DISCRIMINATOR_NOT_OBJECT:"+str(i))
            did=str(row.get("discriminator_id") or "").strip()
            true_ids=row.get("true_candidate_ids"); cost=row.get("cost_units")
            if not did or not isinstance(true_ids,Sequence) or isinstance(true_ids,(str,bytes)):
                raise ValueError("DISCRIMINATOR_INVALID:"+str(i))
            true_ids=sorted(str(x) for x in true_ids)
            if not true_ids or set(true_ids)==cset or not set(true_ids).issubset(cset):
                raise ValueError("DISCRIMINATOR_PARTITION_INVALID:"+did)
            if isinstance(cost,bool) or not isinstance(cost,(int,float)) or cost<0:
                raise ValueError("DISCRIMINATOR_COST_INVALID:"+did)
            discriminators.append({"discriminator_id":did,"formula":_or_atoms(true_ids),"cost_units":float(cost)})
        p3.ROOT=root
        out=p3.solve({
            "decision_basis":basis,
            "formal_source_constraints":[xor],
            "proposed_refinements":[xor],
            "policy_conditions":problem.get("policy_conditions"),
            "policy_adequacy_bindings":problem.get("policy_adequacy_bindings"),
            "discriminators":discriminators,
        })
        status=str(out.get("status") or "")
        if out.get("pass") is True and out.get("common_policy_certified") is True:
            return _base("PASS__COMMON_VERIFIED_POLICY_COVERS_ALL_SEMANTIC_CANDIDATES",True,selected_policy_id=out.get("selected_policy_id"),common_policy_ids=list(out.get("certified_common_policies") or []),candidate_count=len(candidates),candidate_universe_authenticated=True,candidate_universe_authority=auth,policy_adequacy_authority=True,semantic_identity_required=False,terminal_signature_required=False,p3_result=out)
        if status=="FAIL_CLOSED":
            return _base("FAIL_CLOSED__SEMANTIC_POLICY_COVER_AUTHORITY_OR_COVER_INVALID",False,candidate_count=len(candidates),candidate_universe_authenticated=True,candidate_universe_authority=auth,semantic_identity_required=False,terminal_signature_required=False,reason=out.get("reason"),p3_result=out)
        if status=="UNRESOLVED__MINIMUM_ONE_STEP_POLICY_CHANGING_DISCRIMINATOR_SELECTED":
            selected=out.get("selected_discriminator") or {}
            return _base("OPEN__MINIMUM_POLICY_CHANGING_SEMANTIC_DISCRIMINATOR_SELECTED",False,next_observation_id=selected.get("discriminator_id"),minimum_information_cost_units=selected.get("cost_units"),candidate_count=len(candidates),candidate_universe_authenticated=True,candidate_universe_authority=auth,policy_adequacy_authority=False,semantic_identity_required=False,terminal_signature_required=False,truthful_observation_required=True,p3_result=out)
        return _base("OPEN__SEMANTIC_POLICY_COVER_NOT_YET_CLOSED",False,candidate_count=len(candidates),candidate_universe_authenticated=True,candidate_universe_authority=auth,semantic_identity_required=False,terminal_signature_required=False,next_required_effect=out.get("next_required_effect") or out.get("reason") or status,p3_result=out)
    except Exception as exc:
        return _base("FAIL_CLOSED",False,reason=type(exc).__name__+":"+str(exc),policy_adequacy_authority=False)
    finally:
        p3.ROOT=old
