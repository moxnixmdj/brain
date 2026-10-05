"""Recursive current-byte Root3 C1 effect-carrier auditor V4."""
from __future__ import annotations
import ast, hashlib, json, sys
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_ROOT3_C1_EFFECT_CARRIER_AUDITOR_V4"
MANIFEST_SCHEMA="PROJECT_BRAIN_ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V4"

class C1V4Error(RuntimeError): pass

def git_blob_sha(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()

def _qname(node:ast.AST)->str|None:
    if isinstance(node,ast.Name): return node.id
    if isinstance(node,ast.Attribute):
        p=_qname(node.value)
        return None if p is None else p+"."+node.attr
    return None

def _module_to_local_path(root:Path,module:str)->Path|None:
    candidates=[]
    if module.startswith("canonical.runtime."):
        rel=module[len("canonical.runtime."):].replace(".","/")
        candidates.extend([
            root/"canonical"/"runtime"/(rel+".py"),
            root/"canonical"/"runtime"/rel/"__init__.py",
        ])
    top=module.split(".")[0]
    candidates.extend([
        root/"canonical"/"runtime"/(top+".py"),
        root/"canonical"/"runtime"/top/"__init__.py",
    ])
    for p in candidates:
        if p.is_file(): return p.resolve()
    return None

def _imports(tree:ast.Module)->set[str]:
    out=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module:
            out.add(node.module)
            for a in node.names:
                if a.name!="*":
                    out.add(node.module+"."+a.name)
    return out

def _calls(tree:ast.Module):
    out=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Call):
            q=_qname(node.func)
            if q: out.append((q,node))
    return out

def _literal_mode(node:ast.Call)->str|None:
    if len(node.args)>=2 and isinstance(node.args[1],ast.Constant) and isinstance(node.args[1].value,str):
        return node.args[1].value
    for kw in node.keywords:
        if kw.arg=="mode" and isinstance(kw.value,ast.Constant) and isinstance(kw.value.value,str):
            return kw.value.value
    return None

def _write_effect(q:str,node:ast.Call)->bool:
    if q.endswith((".write_text",".write_bytes",".mkdir",".unlink",".rename",".replace",".touch",".save",".rmdir")):
        return True
    if q in {
        "sqlite3.connect","xlsxwriter.Workbook","shutil.copy","shutil.copy2","shutil.copyfile",
        "shutil.copytree","shutil.move","shutil.rmtree","os.remove","os.unlink","os.rename",
        "os.replace","os.mkdir","os.makedirs","os.rmdir","os.removedirs",
    }: return True
    if q=="open" or q.endswith(".open") or q in {"tarfile.open","gzip.open","bz2.open","lzma.open","zipfile.ZipFile"}:
        mode=_literal_mode(node)
        return mode is not None and any(ch in mode for ch in "wax+")
    return False

def _seed_paths(root:Path,parent:dict[str,Any])->set[Path]:
    e=parent["expected_repo_dynamic_universe"]
    rels=set(e["fixed_loader_sites"].values())
    rels.update("canonical/runtime/"+x+".py" for x in e["literal_runtime_helpers"])
    rels.update("canonical/runtime/bound_capabilities/"+x+".py" for x in e["ordinary_adapter_modules"])
    rels.add(parent["subject"]["astra_runtime"]["path"])
    out=set()
    for rel in rels:
        p=(root/rel).resolve()
        if not p.is_file(): raise C1V4Error("SEED_FILE_MISSING:"+rel)
        out.add(p)
    return out

def _recursive_closure(root:Path,seeds:set[Path])->set[Path]:
    seen=set(); queue=list(seeds)
    while queue:
        p=queue.pop()
        if p in seen: continue
        seen.add(p)
        try: tree=ast.parse(p.read_text(encoding="utf-8"),filename=str(p))
        except Exception as exc: raise C1V4Error("AST_PARSE_FAILED:"+str(p.relative_to(root))) from exc
        for module in _imports(tree):
            local=_module_to_local_path(root,module)
            if local is not None and local not in seen: queue.append(local)
    return seen

def audit(repo_root:str|Path,manifest_rel:str)->dict[str,Any]:
    root=Path(repo_root).resolve()
    manifest_path=(root/manifest_rel).resolve()
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema")!=MANIFEST_SCHEMA: raise C1V4Error("MANIFEST_SCHEMA_INVALID")
    parent_info=manifest["parent"]; parent_path=(root/parent_info["path"]).resolve(); parent_raw=parent_path.read_bytes()
    if git_blob_sha(parent_raw)!=parent_info["git_blob_sha"]: raise C1V4Error("PARENT_BLOB_DRIFT")
    parent=json.loads(parent_raw.decode("utf-8"))
    reg_info=manifest["bound_registry"]; reg_path=(root/reg_info["path"]).resolve(); reg_raw=reg_path.read_bytes()
    if git_blob_sha(reg_raw)!=reg_info["git_blob_sha"]: raise C1V4Error("REGISTRY_BLOB_DRIFT")
    registry=json.loads(reg_raw.decode("utf-8"))

    closure=_recursive_closure(root,_seed_paths(root,parent))
    declared=manifest.get("declared") or {}
    network_decl=set(declared.get("network_modules") or [])
    child_decl=set(declared.get("child_process_modules") or [])
    write_decl=set(declared.get("local_filesystem_write_modules") or [])
    third_decl={k:set(v) for k,v in (declared.get("inprocess_third_party_imports") or {}).items()}

    network=set(); child=set(); writes=set(); third={}; dynamic=set(); blobs={}
    stdlib=set(getattr(sys,"stdlib_module_names",set()))
    local_top={p.stem for p in (root/"canonical"/"runtime").glob("*.py")}

    for p in sorted(closure):
        rel=p.relative_to(root).as_posix(); raw=p.read_bytes(); blobs[rel]=git_blob_sha(raw)
        tree=ast.parse(raw.decode("utf-8"),filename=rel)
        external=set()
        for module in _imports(tree):
            top=module.split(".")[0]
            if top in stdlib or top=="canonical" or top in local_top: continue
            if _module_to_local_path(root,module) is not None: continue
            external.add(top)
        if external: third[rel]=external
        for q,node in _calls(tree):
            if q in {"urllib.request.urlopen","socket.socket","socket.create_connection","socket.getaddrinfo","requests.get","requests.post","requests.request","httpx.get","httpx.post","httpx.request"} or q.startswith("urllib3."):
                network.add(rel)
            if q in {"subprocess.run","subprocess.Popen","subprocess.call","subprocess.check_call","subprocess.check_output","os.system","os.popen"} or q.startswith("os.exec") or q.startswith("os.spawn"):
                child.add(rel)
            if _write_effect(q,node): writes.add(rel)
            if q=="importlib.import_module": dynamic.add(rel)

    errors=[]
    for label,obs,dec in [("NETWORK",network,network_decl),("CHILD_PROCESS",child,child_decl),("LOCAL_WRITE",writes,write_decl)]:
        if obs-dec: errors.append("UNDECLARED_"+label+":"+",".join(sorted(obs-dec)))
        if dec-obs: errors.append("STALE_DECLARED_"+label+":"+",".join(sorted(dec-obs)))

    for rel in sorted(set(third)|set(third_decl)):
        obs=third.get(rel,set()); dec=third_decl.get(rel,set())
        if obs!=dec:
            errors.append("THIRD_PARTY_IMPORT_SET_MISMATCH:"+rel+":OBS="+",".join(sorted(obs))+":DECL="+",".join(sorted(dec)))

    registry_dynamic=set((declared.get("registry_constrained_dynamic_imports") or {}).keys())
    untrusted_dynamic=set((declared.get("untrusted_dynamic_import_modules") or {}).keys())
    allowed_dynamic=registry_dynamic|untrusted_dynamic
    if dynamic-allowed_dynamic: errors.append("UNCLASSIFIED_DYNAMIC_IMPORT:"+",".join(sorted(dynamic-allowed_dynamic)))
    if allowed_dynamic-dynamic: errors.append("STALE_DYNAMIC_IMPORT_DECLARATION:"+",".join(sorted(allowed_dynamic-dynamic)))

    caps=registry.get("capabilities",{})
    for rel,rows in (declared.get("registry_constrained_dynamic_imports") or {}).items():
        for row in rows:
            adapter=row["adapter_module"]; expected=(row["module"],row["factory"]); matched=[]
            for cid,entry in caps.items():
                if entry.get("adapter_module")!=adapter: continue
                args=(entry.get("action_template") or {}).get("args") or {}
                matched.append((cid,args.get("module"),args.get("factory")))
            if not matched: errors.append("DYNAMIC_ADAPTER_UNUSED:"+adapter)
            for cid,module,factory in matched:
                if (module,factory)!=expected: errors.append("DYNAMIC_IMPORT_REGISTRY_MISMATCH:"+cid)

    return {
        "schema":SCHEMA,
        "status":"PASS__CURRENT_BYTE_RECURSIVE_CARRIER_CLASSIFICATION" if not errors else "FAIL_CLOSED__CURRENT_BYTE_CARRIER_MISMATCH",
        "pass":not errors,
        "repo_local_import_closure_file_count":len(closure),
        "closure_git_blobs":dict(sorted(blobs.items())),
        "network_modules_observed":sorted(network),
        "child_process_modules_observed":sorted(child),
        "local_filesystem_write_modules_observed":sorted(writes),
        "inprocess_third_party_imports_observed":{k:sorted(v) for k,v in sorted(third.items())},
        "dynamic_import_modules_observed":sorted(dynamic),
        "errors":errors,
        "c1_scope_complete":False,
        "acceptance_credit_delta":0,
        "fresh_reality_authority":False,
        "promotion_authority":False,
    }

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("--repo-root",default="."); ap.add_argument("--manifest",default="canonical/governance/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V4.json")
    ns=ap.parse_args()
    try:
        out=audit(ns.repo_root,ns.manifest); print(json.dumps(out,indent=2,sort_keys=True)); raise SystemExit(0 if out["pass"] else 2)
    except Exception as exc:
        print(json.dumps({"schema":SCHEMA,"status":"FAIL_CLOSED__AUDITOR_ERROR","pass":False,"error":type(exc).__name__+":"+str(exc),"acceptance_credit_delta":0},indent=2,sort_keys=True)); raise SystemExit(3)
