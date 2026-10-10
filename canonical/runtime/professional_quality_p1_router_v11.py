"""Professional P1 Router V11: all-semantic-claim trusted-totality firewall.

V11 is a strict fail-closed refinement of V10.  V10 executes first.  If V10
does not authorize a positive certificate, V11 cannot create one.  If V10 does
authorize a positive certificate, V11 requires an exact content-addressed
certificate for every frozen professional semantic claim returned by the
current verified V3 claim pack, and reruns one fixed trusted generic local
semantic-totality verifier for each claim.

Therefore a V11-positive route implies local semantic totality for all twelve
claim identities; missing or stale claim evidence can only remove a positive
route, never create one.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib, json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_p1_router_v10 as base
from canonical.runtime import professional_semantic_totality_claim_pack_v3 as claim_pack
from canonical.runtime import professional_trusted_local_semantic_totality_verifier_v1 as trusted

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_ROUTER_V11"
V11_SUBJECT_REF_KEY="declared_system_subject_v11"
SEMANTIC_BINDINGS_KEY="professional_semantic_totality_bindings"
V10_SUBJECT_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_V10_DECLARED_SYSTEM_SUBJECT_20261011_V1.json"
V10_SUBJECT_BLOB="71333ce3c40ec8e500e05a6f6b92f425db771a11"
TRUSTED_VERIFIER_PATH="canonical/runtime/professional_trusted_local_semantic_totality_verifier_v1.py"
TRUSTED_VERIFIER_BLOB="5af2d599fffcad16e78d862ee50b2c7d9013be8f"
V11_PATH="canonical/runtime/professional_quality_p1_router_v11.py"
SUBJECT_ID="PROFESSIONAL_QUALITY_P1_V11_ALL_SEMANTIC_TOTALITY_FIREWALL_SYSTEM_20261011_V1"

def _blob(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _digest(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":reason,
            "positive_certification_authorized":False,
            "v11_all_semantic_local_totality_verified":False,
            "semantic_truth_authority":False,"execution_authority":False,
            "quality_authority":False,"acceptance_authority":False,
            "promotion_authority":False,"terminal_authority":False,
            "terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

def _load_ref(root:Path,ref:Any,prefix:str)->tuple[Path|None,dict[str,Any]|None,str|None]:
    if not isinstance(ref,Mapping): return None,None,"REF_NOT_MAPPING"
    rel=ref.get("path"); expected=ref.get("git_blob_sha")
    if not isinstance(rel,str) or not rel.startswith(prefix) or rel.startswith("/"): return None,None,"REF_PATH_INVALID"
    p=Path(rel)
    if ".." in p.parts:return None,None,"REF_PATH_TRAVERSAL"
    full=(root/p).resolve()
    try: full.relative_to(root.resolve())
    except ValueError:return None,None,"REF_OUTSIDE_ROOT"
    if not full.is_file() or full.is_symlink():return None,None,"REF_FILE_MISSING"
    got=_blob(full)
    if not isinstance(expected,str) or got!=expected:return None,None,"REF_BLOB_MISMATCH"
    try:o=json.loads(full.read_text(encoding="utf-8"))
    except Exception:return None,None,"REF_JSON_INVALID"
    if not isinstance(o,dict):return None,None,"REF_NOT_OBJECT"
    return full,o,None

def _v11_subject_ok(ref:Any,*,root:Path)->dict[str,Any]:
    path,doc,err=_load_ref(root,ref,"canonical/governance/")
    if err:return {"pass":False,"reason":"V11_SUBJECT_"+err}
    assert path is not None and doc is not None
    if doc.get("subject_id")!=SUBJECT_ID:return {"pass":False,"reason":"V11_SUBJECT_ID_MISMATCH"}
    material=doc.get("system_material")
    if not isinstance(material,Mapping):return {"pass":False,"reason":"V11_SYSTEM_MATERIAL_MISSING"}
    if doc.get("subject_sha256")!=_digest(material):return {"pass":False,"reason":"V11_SUBJECT_SHA256_MISMATCH"}
    sup=doc.get("supersedes")
    if not isinstance(sup,Mapping) or sup.get("path")!=V10_SUBJECT_PATH or sup.get("git_blob_sha")!=V10_SUBJECT_BLOB:
        return {"pass":False,"reason":"V11_V10_PREDECESSOR_BINDING_INVALID"}
    p10=root/V10_SUBJECT_PATH
    if not p10.is_file() or p10.is_symlink() or _blob(p10)!=V10_SUBJECT_BLOB:
        return {"pass":False,"reason":"V11_V10_PREDECESSOR_NOT_CURRENT"}
    try:v10=json.loads(p10.read_text(encoding="utf-8"))
    except Exception:return {"pass":False,"reason":"V11_V10_SUBJECT_JSON_INVALID"}
    prior=(v10.get("system_material") or {}).get("components")
    comps=material.get("components")
    if not isinstance(prior,list) or not isinstance(comps,list):
        return {"pass":False,"reason":"V11_COMPONENTS_INVALID"}
    prior_map={x.get("path"):x.get("git_blob_sha") for x in prior if isinstance(x,Mapping)}
    cur_map={x.get("path"):x.get("git_blob_sha") for x in comps if isinstance(x,Mapping)}
    if any(cur_map.get(p)!=b for p,b in prior_map.items()):
        return {"pass":False,"reason":"V11_PREDECESSOR_COMPONENT_DRIFT"}
    if cur_map.get(TRUSTED_VERIFIER_PATH)!=TRUSTED_VERIFIER_BLOB:
        return {"pass":False,"reason":"V11_TRUSTED_VERIFIER_PIN_MISMATCH"}
    own_blob=_blob(root/V11_PATH)
    if cur_map.get(V11_PATH)!=own_blob:return {"pass":False,"reason":"V11_SELF_COMPONENT_PIN_MISMATCH"}
    expected_paths=set(prior_map)|{TRUSTED_VERIFIER_PATH,V11_PATH}
    if set(cur_map)!=expected_paths:return {"pass":False,"reason":"V11_COMPONENT_SET_NOT_EXACT"}
    return {"pass":True,"subject_id":SUBJECT_ID,"subject_sha256":doc["subject_sha256"],
            "subject_git_blob_sha":_blob(path),"component_count":len(cur_map)}

def _cert_path(root:Path,ref:Any)->Path|None:
    p,_,err=_load_ref(root,ref,"canonical/evidence/")
    return None if err else p

def route(state:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
    if not isinstance(state,Mapping):return _fail("STATE_NOT_OBJECT")
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    subject=_v11_subject_ok(state.get(V11_SUBJECT_REF_KEY),root=root)
    if subject.get("pass") is not True:return _fail("V11_DECLARED_SYSTEM_SUBJECT_INVALID",subject_verification=subject)

    out=base.route(state,repo_root=root)
    if not isinstance(out,Mapping):return _fail("V10_RESULT_NOT_OBJECT")
    result=deepcopy(dict(out));result["schema"]=SCHEMA
    if result.get("final_step_outcome")!="POSITIVE_CERTIFICATE" or result.get("positive_certification_authorized") is not True:
        result["v11_all_semantic_local_totality_verified"]=False
        return result

    pack=claim_pack.verify(repo_root=root)
    if pack.get("pass") is not True or pack.get("semantic_claim_count")!=12 or pack.get("unique_claim_id_count")!=12:
        return _fail("V11_CURRENT_SEMANTIC_CLAIM_PACK_INVALID",claim_pack=pack)
    rows=pack.get("claims") or []
    claims={}
    for row in rows:
        if not isinstance(row,Mapping) or not isinstance(row.get("frozen_claim"),Mapping):
            return _fail("V11_CLAIM_ROW_INVALID")
        cid=row["frozen_claim"].get("claim_id")
        if not isinstance(cid,str) or not cid:return _fail("V11_CLAIM_ID_INVALID")
        claims[cid]=row
    if len(claims)!=12:return _fail("V11_CLAIM_SET_NOT_12")

    bindings=state.get(SEMANTIC_BINDINGS_KEY)
    if not isinstance(bindings,Mapping):return _fail("V11_SEMANTIC_TOTALITY_BINDINGS_REQUIRED")
    if set(bindings)!=set(claims):
        return _fail("V11_SEMANTIC_CLAIM_BINDING_SET_MISMATCH",
                     missing_claim_ids=sorted(set(claims)-set(bindings)),
                     extra_claim_ids=sorted(set(bindings)-set(claims)))
    verdicts={}
    for cid in sorted(claims):
        item=bindings.get(cid)
        if not isinstance(item,Mapping):return _fail("V11_SEMANTIC_BINDING_NOT_OBJECT",claim_id=cid)
        cp=_cert_path(root,item.get("certificate"))
        if cp is None:return _fail("V11_SEMANTIC_CERTIFICATE_REF_INVALID",claim_id=cid)
        v=trusted.verify_certificate(root=root,certificate_path=cp,expected_claim_id=cid)
        if v.get("pass") is not True or v.get("local_material_totality_verified") is not True or v.get("semantic_acceptance_bound") is not True:
            return _fail("V11_SEMANTIC_LOCAL_TOTALITY_REJECTED",claim_id=cid,local_totality=v)
        verdicts[cid]={
          "leaf_id":claims[cid].get("leaf_id"),
          "local_material_totality_verified":True,
          "semantic_acceptance_bound":True,
          "policy_cover_result_sha256":v.get("policy_cover_result_sha256"),
        }

    result["v11_all_semantic_local_totality_verified"]=True
    result["v11_semantic_claim_count"]=12
    result["v11_semantic_claim_set_sha256"]=_digest(sorted(claims))
    result["v11_semantic_local_totality_verdicts"]=verdicts
    result["v11_universal_positive_route_invariant"]="EVERY_V11_POSITIVE_ROUTE_FIRST_PASSES_V10_AND_THEN_EXACT_FIXED_TRUSTED_LOCAL_TOTALITY_FOR_ALL_12_CURRENT_FROZEN_SEMANTIC_CLAIMS"
    result["semantic_truth_authority"]=False
    result["quality_authority"]=False
    result["acceptance_authority"]=False
    result["promotion_authority"]=False
    result["terminal_authority"]=False
    result["terminal_credit_delta"]=0
    result["incremental_spend_usd"]=0
    return result

def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return route(args or {},repo_root=root)
