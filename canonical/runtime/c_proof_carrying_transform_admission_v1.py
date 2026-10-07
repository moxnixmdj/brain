from __future__ import annotations
import hashlib,json
from pathlib import Path

class AdmissionError(ValueError): pass

def git_blob_sha(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load_bound(root:Path,spec:dict,label:str)->dict:
    p=(root/str(spec.get("path") or "")).resolve()
    try: p.relative_to(root.resolve())
    except ValueError: raise AdmissionError(label+"_PATH_ESCAPE")
    want=str(spec.get("git_blob_sha") or "")
    if len(want)!=40 or not p.exists(): raise AdmissionError(label+"_BINDING_INVALID")
    if git_blob_sha(p)!=want: raise AdmissionError(label+"_BLOB_MISMATCH")
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise AdmissionError(label+"_OBJECT_REQUIRED")
    return x

def _true(x:dict,key:str,label:str):
    if x.get(key) is not True: raise AdmissionError(label+"_"+key.upper()+"_NOT_TRUE")

def verify_edge(root:Path,cert:dict)->dict:
    src=load_bound(root,cert["source_state"],"SOURCE_STATE")
    dst=load_bound(root,cert["target_state"],"TARGET_STATE")
    tr=load_bound(root,cert["transform"],"TRANSFORM")
    er=load_bound(root,cert["evaluator_registry"],"EVALUATOR_REGISTRY")
    hr=load_bound(root,cert["hard_constraint_registry"],"HARD_CONSTRAINT_REGISTRY")
    for x,label in ((src,"SOURCE_STATE"),(dst,"TARGET_STATE")):
        _true(x,"scope_complete",label); _true(x,"independent_or_objective",label)
    _true(tr,"exact_transform_bound","TRANSFORM"); _true(tr,"independent_or_objective","TRANSFORM")
    _true(er,"scope_complete","EVALUATOR_REGISTRY"); _true(er,"independent_or_objective","EVALUATOR_REGISTRY")
    _true(hr,"scope_complete","HARD_CONSTRAINT_REGISTRY"); _true(hr,"independent_or_objective","HARD_CONSTRAINT_REGISTRY")
    evals=list(map(str,er.get("evaluators") or []))
    hards=list(map(str,hr.get("hard_constraints") or []))
    pulls=cert.get("pullbacks")
    pre=cert.get("hard_constraint_preimages")
    if not isinstance(pulls,dict) or set(pulls)!=set(evals): raise AdmissionError("PULLBACK_SET_MISMATCH")
    if not isinstance(pre,dict) or set(pre)!=set(hards): raise AdmissionError("HARD_PREIMAGE_SET_MISMATCH")
    for eid in evals:
        x=load_bound(root,pulls[eid],"PULLBACK_"+eid)
        _true(x,"proved","PULLBACK_"+eid); _true(x,"scope_complete","PULLBACK_"+eid); _true(x,"independent_or_objective","PULLBACK_"+eid)
        if str(x.get("target_evaluator_id"))!=eid: raise AdmissionError("PULLBACK_TARGET_ID_MISMATCH:"+eid)
    for hid in hards:
        x=load_bound(root,pre[hid],"HARD_PREIMAGE_"+hid)
        _true(x,"proved","HARD_PREIMAGE_"+hid); _true(x,"scope_complete","HARD_PREIMAGE_"+hid); _true(x,"independent_or_objective","HARD_PREIMAGE_"+hid)
        if str(x.get("hard_constraint_id"))!=hid: raise AdmissionError("HARD_PREIMAGE_ID_MISMATCH:"+hid)
    return {"pass":True,"evaluator_count":len(evals),"hard_constraint_count":len(hards),"terminal_credit_delta":0}

def verify_route(root:Path,route_cert:dict)->dict:
    reg=load_bound(root,route_cert["edge_registry"],"EDGE_REGISTRY")
    _true(reg,"scope_complete","EDGE_REGISTRY"); _true(reg,"independent_or_objective","EDGE_REGISTRY")
    edges=list(map(str,reg.get("load_bearing_edges") or []))
    certs=route_cert.get("edge_certificates")
    if not isinstance(certs,dict) or set(certs)!=set(edges): raise AdmissionError("EDGE_CERTIFICATE_SET_MISMATCH")
    out={e:verify_edge(root,certs[e]) for e in edges}
    return {"pass":True,"edge_count":len(edges),"edges":out,"terminal_credit_delta":0}
