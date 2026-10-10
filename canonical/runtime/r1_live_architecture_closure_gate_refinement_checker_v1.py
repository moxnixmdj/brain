from __future__ import annotations
import ast, importlib.util, json, tempfile
from copy import deepcopy
from hashlib import sha1, sha256
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_R1_LIVE_ARCHITECTURE_CLOSURE_GATE_REFINEMENT_CHECKER_V1"
SPEC_SCHEMA="PROJECT_BRAIN_R1_LIVE_ARCHITECTURE_CLOSURE_GATE_ABSTRACT_SPEC_V1"
RECEIPT_SCHEMA="PROJECT_BRAIN_R1_LIVE_ARCHITECTURE_CLOSURE_GATE_REFINEMENT_RECEIPT_V1"

def _blob(p:Path)->str:
    b=p.read_bytes(); return sha1(b"blob "+str(len(b)).encode()+bytes([0])+b).hexdigest()

def _fail(reason:str,**kw):
    return {"schema":RECEIPT_SCHEMA,"pass":False,"refinement_verified":False,
            "reason":reason,"terminal_authority":False,"terminal_credit_delta":0,**kw}

def _subject(spec:Mapping[str,Any],root:Path):
    s=spec.get("subject")
    if not isinstance(s,Mapping): return None,"SUBJECT_REQUIRED"
    try:
        p=(root/str(s["path"])).resolve(strict=True); p.relative_to(root.resolve())
    except Exception: return None,"SUBJECT_PATH_INVALID"
    if _blob(p)!=s.get("git_blob_sha"): return None,"SUBJECT_BLOB_DRIFT"
    return p,None

def _load(p:Path):
    n="_r1_refinement_"+sha256(str(p).encode()).hexdigest()[:12]
    sp=importlib.util.spec_from_file_location(n,p)
    if sp is None or sp.loader is None: raise RuntimeError("SUBJECT_IMPORT_FAILED")
    m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

def _prefix(n):
    if isinstance(n,ast.Constant) and isinstance(n.value,str): return n.value
    if isinstance(n,ast.BinOp) and isinstance(n.op,ast.Add): return _prefix(n.left)
    return None

def _surface(src:str):
    fixed=set(); families=set(); exc=set(); expfx=set()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n,ast.Call):
            a=n.func.attr if isinstance(n.func,ast.Attribute) else None
            if a=="append" and n.args:
                x=n.args[0]
                if isinstance(x,ast.Constant) and isinstance(x.value,str): fixed.add(x.value)
                else:
                    p=_prefix(x)
                    if p: families.add(p.rstrip(":"))
            elif a=="extend" and n.args and isinstance(n.args[0],ast.GeneratorExp):
                p=_prefix(n.args[0].elt)
                if p: families.add(p.rstrip(":"))
        elif isinstance(n,ast.Raise) and isinstance(n.exc,ast.Call) and n.exc.args:
            if isinstance(n.exc.func,ast.Name) and n.exc.func.id=="R1ClosureError":
                x=n.exc.args[0]
                if isinstance(x,ast.Constant) and isinstance(x.value,str): exc.add(x.value)
                else:
                    p=_prefix(x)
                    if p: expfx.add(p)
    return fixed,families,exc,expfx

def _j(p:Path,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,sort_keys=True)+"\n",encoding="utf-8")

def _base(m):
    for p in (m.FABRIC_PATH,m.INVOKER_PATH,m.SUBRUNTIME_PATH):
        if not Path(p).is_file(): raise RuntimeError("LOAD_BEARING_FILE_MISSING:"+str(p))
    fb,ib,sb=map(m._git_blob_sha,(m.FABRIC_PATH,m.INVOKER_PATH,m.SUBRUNTIME_PATH))
    return {
      "engines":dict(m.REQUIRED_ENGINE_BINDINGS),
      "surfaces":sorted(m.REQUIRED_SUBRUNTIME_SURFACES),
      "ownership":{"pass":True,"live_owned_equals_fabric_reachable":True,"live_owned_capability_count":3},
      "invocation":{"pass":True,"missing_capability_count":0,"capability_count":3,"supported_capability_count":3},
      "activation":{"status":"ACTIVE_SUBORDINATE_EXECUTION_RUNTIME",
        "public_entrypoint":m.EXPECTED_PUBLIC_ENTRYPOINT,
        "canonical_public_entrypoint":m.EXPECTED_PUBLIC_ENTRYPOINT,
        "subruntime_entrypoint":m.EXPECTED_SUBRUNTIME_ENTRYPOINT,
        "role":"SUBORDINATE_EXECUTION_RUNTIME__R3_REUSE_REPAIR_AND_COMPATIBILITY_CARRIER",
        "invariants":sorted(m.REQUIRED_ACTIVATION_INVARIANTS)},
      "authority":{"live_capability_ownership_20261008_v1":{
        "r1_structural_closure":True,"canonical_public_entrypoint":m.EXPECTED_PUBLIC_ENTRYPOINT,
        "subordinate_runtime_public_authority":False,
        "unified_fabric":{"git_blob_sha":fb},"invoker":{"git_blob_sha":ib},
        "subordinate_runtime":{"git_blob_sha":sb}},
        "r1_universal_live_capability_invocation_20261008_v1":{
        "unified_fabric":{"git_blob_sha":fb},"runtime":{"git_blob_sha":ib},
        "missing_invocation_contract_count":0}},
      "public":m.EXPECTED_PUBLIC_ENTRYPOINT,"sub":m.EXPECTED_SUBRUNTIME_ENTRYPOINT}

def _run(m,s):
    with tempfile.TemporaryDirectory() as td:
        r=Path(td); a=r/"a.json"; u=r/"u.json"; _j(a,s["activation"]); _j(u,s["authority"])
        return m.evaluate(s["engines"],ownership=s["ownership"],invocation=s["invocation"],
          subruntime_surfaces=s["surfaces"],canonical_public_entrypoint=s["public"],
          subordinate_runtime_entrypoint=s["sub"],activation_path=a,authority_path=u)

def _path_set(s,path,value):
    x=s
    for k in path[:-1]: x=x[k]
    x[path[-1]]=value

def _target(m,spec,target,mutation):
    s=_base(m); mutation(s); o=_run(m,s)
    fp=spec["failure_projection"]
    return all(o.get(k)==v for k,v in fp.items()) and target in o.get("errors",[]),o

def _fixed():
    B="f"*40
    return {
      "PUBLIC_ENTRYPOINT_DRIFT":lambda s:_path_set(s,["public"],"bad"),
      "SUBRUNTIME_ENTRYPOINT_DRIFT":lambda s:_path_set(s,["sub"],"bad"),
      "LIVE_OWNERSHIP_NOT_CLOSED":lambda s:_path_set(s,["ownership","pass"],False),
      "LIVE_OWNED_NOT_FABRIC_REACHABLE":lambda s:_path_set(s,["ownership","live_owned_equals_fabric_reachable"],False),
      "UNIVERSAL_INVOCATION_COVERAGE_NOT_CLOSED":lambda s:_path_set(s,["invocation","pass"],False),
      "UNIVERSAL_INVOCATION_CONTRACTS_MISSING":lambda s:_path_set(s,["invocation","missing_capability_count"],1),
      "OWNERSHIP_INVOCATION_COUNT_DIVERGENCE":lambda s:_path_set(s,["invocation","capability_count"],4),
      "ACTIVATION_STATUS_DRIFT":lambda s:_path_set(s,["activation","status"],"bad"),
      "ACTIVATION_PUBLIC_ENTRYPOINT_DRIFT":lambda s:_path_set(s,["activation","public_entrypoint"],"bad"),
      "ACTIVATION_CANONICAL_PUBLIC_ENTRYPOINT_DRIFT":lambda s:_path_set(s,["activation","canonical_public_entrypoint"],"bad"),
      "ACTIVATION_SUBRUNTIME_ENTRYPOINT_DRIFT":lambda s:_path_set(s,["activation","subruntime_entrypoint"],"bad"),
      "ACTIVATION_SUBRUNTIME_ROLE_DRIFT":lambda s:_path_set(s,["activation","role"],"bad"),
      "AUTHORITY_R1_CLOSURE_NOT_TRUE":lambda s:_path_set(s,["authority","live_capability_ownership_20261008_v1","r1_structural_closure"],False),
      "AUTHORITY_PUBLIC_ENTRYPOINT_DRIFT":lambda s:_path_set(s,["authority","live_capability_ownership_20261008_v1","canonical_public_entrypoint"],"bad"),
      "AUTHORITY_SUBRUNTIME_PUBLIC_AUTHORITY_DRIFT":lambda s:_path_set(s,["authority","live_capability_ownership_20261008_v1","subordinate_runtime_public_authority"],True),
      "AUTHORITY_FABRIC_BLOB_DRIFT":lambda s:_path_set(s,["authority","live_capability_ownership_20261008_v1","unified_fabric","git_blob_sha"],B),
      "AUTHORITY_INVOKER_BLOB_DRIFT":lambda s:_path_set(s,["authority","live_capability_ownership_20261008_v1","invoker","git_blob_sha"],B),
      "AUTHORITY_SUBRUNTIME_BLOB_DRIFT":lambda s:_path_set(s,["authority","live_capability_ownership_20261008_v1","subordinate_runtime","git_blob_sha"],B),
      "INVOCATION_AUTHORITY_FABRIC_BLOB_DRIFT":lambda s:_path_set(s,["authority","r1_universal_live_capability_invocation_20261008_v1","unified_fabric","git_blob_sha"],B),
      "INVOCATION_AUTHORITY_INVOKER_BLOB_DRIFT":lambda s:_path_set(s,["authority","r1_universal_live_capability_invocation_20261008_v1","runtime","git_blob_sha"],B),
      "INVOCATION_AUTHORITY_MISSING_CONTRACTS":lambda s:_path_set(s,["authority","r1_universal_live_capability_invocation_20261008_v1","missing_invocation_contract_count"],1),
      "AUTHORITY_LIVE_OWNERSHIP_NODE_MISSING":lambda s:s["authority"].pop("live_capability_ownership_20261008_v1"),
      "AUTHORITY_UNIVERSAL_INVOCATION_NODE_MISSING":lambda s:s["authority"].pop("r1_universal_live_capability_invocation_20261008_v1")}

def _exceptions(m):
    rows=[]; b=_base(m)
    try:
        m.evaluate([],ownership=b["ownership"],invocation=b["invocation"],
          subruntime_surfaces=b["surfaces"],canonical_public_entrypoint=b["public"],
          subordinate_runtime_entrypoint=b["sub"])
    except m.R1ClosureError as e:
        if str(e)!="ENGINE_DESCRIPTORS_NOT_OBJECT": return False,rows
        rows.append({"case":"ENGINE_DESCRIPTORS_NOT_OBJECT"})
    else: return False,rows
    for kind in ("ACTIVATION_JSON_NOT_OBJECT","AUTHORITY_JSON_NOT_OBJECT"):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); a=r/"a.json"; u=r/"u.json"
            if kind=="ACTIVATION_JSON_NOT_OBJECT":
                a.write_text("[]\n"); _j(u,b["authority"])
            else:
                _j(a,b["activation"]); u.write_text("[]\n")
            try:
                m.evaluate(b["engines"],ownership=b["ownership"],invocation=b["invocation"],
                  subruntime_surfaces=b["surfaces"],canonical_public_entrypoint=b["public"],
                  subordinate_runtime_entrypoint=b["sub"],activation_path=a,authority_path=u)
            except m.R1ClosureError as e:
                if not str(e).startswith("JSON_NOT_OBJECT:"): return False,rows
                rows.append({"case":kind})
            else: return False,rows
    return True,rows

def verify(spec:Mapping[str,Any],*,repo_root:str|Path):
    try:
        if not isinstance(spec,Mapping) or spec.get("schema")!=SPEC_SCHEMA: return _fail("SPEC_SCHEMA_INVALID")
        root=Path(repo_root).resolve(); p,e=_subject(spec,root)
        if e or p is None:return _fail(e or "SUBJECT_INVALID")
        fixed,fams,exc,expfx=_surface(p.read_text())
        if fixed!=set(spec["fixed_error_classes"]): return _fail("FIXED_ERROR_CENSUS_MISMATCH")
        if fams!=set(spec["parameterized_error_families"]): return _fail("PARAMETERIZED_ERROR_FAMILY_CENSUS_MISMATCH")
        if exc!=set(spec["expected_exception_classes"]["fixed"]): return _fail("FIXED_EXCEPTION_CENSUS_MISMATCH")
        if expfx!=set(spec["expected_exception_classes"]["prefixes"]): return _fail("EXCEPTION_PREFIX_CENSUS_MISMATCH")
        m=_load(p)
        if dict(m.REQUIRED_ENGINE_BINDINGS)!=dict(spec["required_engine_bindings"]): return _fail("ENGINE_CONSTANT_MISMATCH")
        if set(m.REQUIRED_SUBRUNTIME_SURFACES)!=set(spec["required_subruntime_surfaces"]): return _fail("SURFACE_CONSTANT_MISMATCH")
        if set(m.REQUIRED_ACTIVATION_INVARIANTS)!=set(spec["required_activation_invariants"]): return _fail("INVARIANT_CONSTANT_MISMATCH")
        o=_run(m,_base(m)); sp=spec["success_projection"]
        if any(o.get(k)!=v for k,v in sp.items()) or not all(o["capability_lifecycle"].values()):
            return _fail("SUCCESS_PROJECTION_MISMATCH",observed=o)
        rows=[{"case":"CURRENT_SUCCESS"}]; observed=set()
        for target,mut in _fixed().items():
            ok,out=_target(m,spec,target,mut)
            if not ok:return _fail("FIXED_WITNESS_FAILED:"+target,observed=out)
            observed.update(out["errors"]); rows.append({"case":target})
        if not set(spec["fixed_error_classes"]).issubset(observed):
            return _fail("FIXED_ERROR_NOT_WITNESSED",missing=sorted(set(spec["fixed_error_classes"])-observed))
        for mode in sorted(m.REQUIRED_ENGINE_BINDINGS):
            target="ENGINE_BINDING_DRIFT:"+mode
            ok,out=_target(m,spec,target,lambda s,mode=mode:_path_set(s,["engines",mode],"bad"))
            if not ok:return _fail("ENGINE_WITNESS_FAILED:"+mode,observed=out)
            rows.append({"case":target})
        for surface in sorted(m.REQUIRED_SUBRUNTIME_SURFACES):
            target="SUBRUNTIME_SURFACE_MISSING:"+surface
            ok,out=_target(m,spec,target,lambda s,surface=surface:s.__setitem__("surfaces",[x for x in s["surfaces"] if x!=surface]))
            if not ok:return _fail("SURFACE_WITNESS_FAILED:"+surface,observed=out)
            rows.append({"case":target})
        for inv in sorted(m.REQUIRED_ACTIVATION_INVARIANTS):
            target="ACTIVATION_INVARIANT_MISSING:"+inv
            ok,out=_target(m,spec,target,lambda s,inv=inv:_path_set(s,["activation","invariants"],[x for x in s["activation"]["invariants"] if x!=inv]))
            if not ok:return _fail("INVARIANT_WITNESS_FAILED:"+inv,observed=out)
            rows.append({"case":target})
        exok,exrows=_exceptions(m)
        if not exok:return _fail("EXCEPTION_WITNESS_FAILED",witness_detail=exrows)
        material={"subject":spec["subject"],"rows":rows,"exception_rows":exrows,"root_assumptions":spec["root_assumptions"]}
        return {"schema":RECEIPT_SCHEMA,"pass":True,"refinement_verified":True,
          "assurance_level":"STATIC_ERROR_FAMILY_CENSUS_PLUS_MEMBER_COMPLETE_WITNESS_EXECUTION",
          "subject":deepcopy(dict(spec["subject"])),"branch_witness_count":len(rows),
          "exception_witness_count":len(exrows),"witness_count":len(rows)+len(exrows),
          "receipt_sha256":sha256(json.dumps(material,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
          "repository_wide_refinement":False,"transitive_dependency_refinement":False,
          "downstream_capability_semantics_proved":False,"terminal_authority":False,"terminal_credit_delta":0}
    except Exception as x:return _fail("CHECKER_EXCEPTION:"+type(x).__name__+":"+str(x))
