#!/usr/bin/env python3
import argparse, ast, gzip, hashlib, importlib.util, json, os, pathlib, re, shlex, shutil, subprocess, sys, tempfile, time, urllib.parse, urllib.request
import importlib.metadata
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parents[2]
STATE_DIR=ROOT/"canonical"/"astra_runtime"/"state"
EVID_DIR=ROOT/"canonical"/"astra_runtime"/"evidence"

def utc(): return datetime.now(timezone.utc).isoformat()
def writej(p,x):
    p=pathlib.Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def readj(p): return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))

def context_results(state):
    latest={}
    for rec in state.get("history",[]):
        if rec.get("ok"):
            latest[rec["step_index"]]=rec["result"]
    for batch in state.get("rehydrations",[]):
        for rec in batch.get("steps",[]):
            if rec.get("ok"):
                latest[rec["step_index"]]=rec["result"]
    return [latest[i] for i in sorted(latest)]

def sha_file(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

class Blocker(RuntimeError):
    pass

def run_shell(step, prior_results=None):
    cmd=step["command"]
    env=os.environ.copy()
    for i, result in enumerate(prior_results or []):
        prefix=f"ASTRA_STEP_{i}_"
        env[prefix+"RESULT_JSON"]=json.dumps(result, sort_keys=True)
        if "body_excerpt" in result:
            env[prefix+"BODY"]=result["body_excerpt"]
        if "stdout" in result:
            env[prefix+"STDOUT"]=result["stdout"]
    t=time.monotonic()
    p=subprocess.run(cmd,shell=True,executable="/bin/bash",cwd=ROOT,text=True,capture_output=True,env=env)
    return {
      "adapter":"shell","command":cmd,"returncode":p.returncode,
      "stdout":p.stdout[-12000:],"stderr":p.stderr[-12000:],
      "duration_s":round(time.monotonic()-t,3)
    }

def run_http(step):
    req=urllib.request.Request(step["url"],headers={"User-Agent":"ProjectBrain-ASTRA_RUNTIME/1"})
    t=time.monotonic()
    with urllib.request.urlopen(req,timeout=step.get("timeout_s",20)) as r:
        raw=r.read(step.get("max_bytes",200000))
        body=gzip.decompress(raw) if r.headers.get("Content-Encoding","").lower()=="gzip" else raw
        return {
          "adapter":"http","url":r.geturl(),"status":r.status,
          "body_sha256":hashlib.sha256(body).hexdigest(),
          "body_excerpt":body[:12000].decode("utf-8","replace"),
          "duration_s":round(time.monotonic()-t,3)
        }

def _safe_repo_path(raw):
    value=str(raw or "").strip()
    # Planner sources sometimes express repository-root-relative paths as
    # "/canonical/...". Interpret that single leading slash as repository
    # root notation, but keep the resolve/parent check as the authority that
    # rejects traversal or any actual escape outside the checkout.
    if value.startswith("/"):
        value=value.lstrip("/")
    p=(ROOT/value).resolve()
    if p != ROOT.resolve() and ROOT.resolve() not in p.parents:
        raise Blocker("PATH_OUTSIDE_REPOSITORY")
    return p

def _load_bound_capability_registry():
    path=ROOT/"canonical"/"runtime"/"BOUND_CAPABILITY_REGISTRY_V1.json"
    data=readj(path)
    if data.get("schema")!="PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1":
        raise Blocker("BOUND_CAPABILITY_REGISTRY_INVALID")
    caps=data.get("capabilities")
    if not isinstance(caps,dict):
        raise Blocker("BOUND_CAPABILITY_REGISTRY_INVALID")
    return caps

def _ensure_pypi_dependency(source):
    name=str(source.get("project") or "").strip()
    version=str(source.get("version") or "").strip()
    filename=str(source.get("wheel_filename") or "").strip()
    expected=str(source.get("wheel_sha256") or "").strip().lower()
    metadata_url=str(source.get("metadata_url") or "").strip()
    if not all((name,version,filename,expected,metadata_url)):
        raise Blocker("BOUND_PYPI_SOURCE_INCOMPLETE")
    try:
        if importlib.metadata.version(name)==version:
            return {"status":"ALREADY_INSTALLED","project":name,"version":version}
    except importlib.metadata.PackageNotFoundError:
        pass
    req=urllib.request.Request(metadata_url,headers={"User-Agent":"ProjectBrain-BoundCapability/1"})
    with urllib.request.urlopen(req,timeout=20) as resp:
        meta=json.loads(resp.read(2000000).decode("utf-8"))
    matches=[u for u in meta.get("urls",[]) if u.get("filename")==filename]
    if len(matches)!=1:
        raise Blocker("BOUND_PYPI_WHEEL_NOT_UNIQUE")
    artifact=matches[0]
    metadata_sha=str((artifact.get("digests") or {}).get("sha256") or "").lower()
    if metadata_sha!=expected:
        raise Blocker("BOUND_PYPI_METADATA_HASH_MISMATCH")
    url=str(artifact.get("url") or "")
    if not url.startswith("https://"):
        raise Blocker("BOUND_PYPI_WHEEL_URL_INVALID")
    with urllib.request.urlopen(
        urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-BoundCapability/1"}),
        timeout=30
    ) as resp:
        raw=resp.read(12000000)
    actual=hashlib.sha256(raw).hexdigest()
    if actual!=expected:
        raise Blocker("BOUND_PYPI_WHEEL_HASH_MISMATCH")
    with tempfile.TemporaryDirectory(prefix="project-brain-cap-") as td:
        wheel=pathlib.Path(td)/filename
        wheel.write_bytes(raw)
        proc=subprocess.run(
            [sys.executable,"-m","pip","install","--disable-pip-version-check","--quiet","--no-deps",str(wheel)],
            cwd=ROOT,text=True,capture_output=True,timeout=120
        )
        if proc.returncode!=0:
            raise Blocker("BOUND_PYPI_INSTALL_FAILED:"+proc.stderr[-1200:])
    try:
        installed=importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError as e:
        raise Blocker("BOUND_PYPI_INSTALL_NOT_VISIBLE") from e
    if installed!=version:
        raise Blocker("BOUND_PYPI_INSTALLED_VERSION_MISMATCH:"+installed)
    return {"status":"INSTALLED_VERIFIED","project":name,"version":version,"wheel_sha256":actual}

def _ensure_local_dependency(source):
    typ=str(source.get("type") or "").strip()
    if typ=="python_stdlib":
        raw_modules=source.get("modules")
        if raw_modules is None:
            one=str(source.get("module") or "").strip()
            modules=[one] if one else []
        elif isinstance(raw_modules,list):
            modules=[str(x or "").strip() for x in raw_modules]
        else:
            raise Blocker("BOUND_PYTHON_STDLIB_MODULES_INVALID")
        modules=[m for m in modules if m]
        if not modules:
            raise Blocker("BOUND_PYTHON_STDLIB_MODULE_REQUIRED")
        if len(set(modules))!=len(modules):
            raise Blocker("BOUND_PYTHON_STDLIB_MODULES_DUPLICATE")
        verified=[]
        for module in modules:
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*",module):
                raise Blocker("BOUND_PYTHON_STDLIB_MODULE_INVALID:"+module)
            try:
                spec=importlib.util.find_spec(module)
            except Exception as exc:
                raise Blocker("BOUND_PYTHON_STDLIB_PROBE_FAILED:"+module+":"+type(exc).__name__) from exc
            if spec is None:
                raise Blocker("BOUND_PYTHON_STDLIB_MODULE_MISSING:"+module)
            verified.append(module)
        out={
          "status":"LOCAL_VERIFIED",
          "type":"python_stdlib",
          "modules":verified,
          "python_version":sys.version.split()[0],
        }
        if len(verified)==1:
            out["module"]=verified[0]
        return out
    if typ=="system_tool":
        exe=str(source.get("executable") or "").strip()
        if not exe or pathlib.Path(exe).name!=exe:
            raise Blocker("BOUND_SYSTEM_TOOL_EXECUTABLE_INVALID")
        resolved=shutil.which(exe)
        if not resolved:
            raise Blocker("BOUND_SYSTEM_TOOL_MISSING:"+exe)
        return {
          "status":"LOCAL_VERIFIED",
          "type":"system_tool",
          "executable":exe,
          "resolved_path":resolved,
        }
    raise Blocker("BOUND_CAPABILITY_SOURCE_UNSUPPORTED:"+typ)


def _ensure_apt_dependencies(source):
    if not sys.platform.startswith("linux"):
        raise Blocker("BOUND_APT_PLATFORM_UNSUPPORTED:"+sys.platform)
    packages=source.get("packages")
    if not isinstance(packages,list) or not packages:
        raise Blocker("BOUND_APT_PACKAGES_REQUIRED")
    requested=[]
    expected={}
    evidence=[]
    for pkg in packages:
        if not isinstance(pkg,dict):
            raise Blocker("BOUND_APT_PACKAGE_INVALID")
        name=str(pkg.get("name") or "").strip()
        version=str(pkg.get("version") or "").strip()
        sha=str(pkg.get("sha256") or "").strip().lower()
        if not name or not version or len(sha)!=64:
            raise Blocker("BOUND_APT_PACKAGE_METADATA_INCOMPLETE")
        show=subprocess.run(["apt-cache","show",f"{name}={version}"],text=True,capture_output=True,timeout=30)
        if show.returncode!=0:
            raise Blocker("BOUND_APT_METADATA_NOT_FOUND:"+name)
        found=None
        for line in show.stdout.splitlines():
            if line.startswith("SHA256:"):
                found=line.split(":",1)[1].strip().lower()
                break
        if found!=sha:
            raise Blocker("BOUND_APT_PACKAGE_HASH_MISMATCH:"+name)
        requested.append(f"{name}={version}")
        expected[name]=version
        evidence.append({"name":name,"version":version,"archive_sha256":sha})
    env=os.environ.copy()
    env["DEBIAN_FRONTEND"]="noninteractive"
    proc=subprocess.run(
        ["sudo","apt-get","install","-y","--no-install-recommends",*requested],
        cwd=ROOT,text=True,capture_output=True,timeout=240,env=env
    )
    if proc.returncode!=0:
        raise Blocker("BOUND_APT_INSTALL_FAILED:"+proc.stderr[-1600:])
    for name,version in expected.items():
        q=subprocess.run(["dpkg-query","-W","-f=$"+"{Version}",name],text=True,capture_output=True,timeout=30)
        if q.returncode!=0 or q.stdout.strip()!=version:
            raise Blocker("BOUND_APT_INSTALLED_VERSION_MISMATCH:"+name+":"+q.stdout.strip())
    return {"status":"INSTALLED_VERIFIED","origin":source.get("origin"),"packages":evidence}

def _invoke_bound_capability(args):
    cid=str(args.get("capability_id") or "").strip()
    if not cid:
        raise Blocker("BOUND_CAPABILITY_ID_REQUIRED")
    entry=_load_bound_capability_registry().get(cid)
    if not isinstance(entry,dict):
        raise Blocker("BOUND_CAPABILITY_UNKNOWN:"+cid)
    if float(entry.get("incremental_spend_usd",0))!=0:
        raise Blocker("BOUND_CAPABILITY_NONZERO_COST_REJECTED:"+cid)
    source=entry.get("source") or {}
    dependency=None
    if source.get("type")=="pypi":
        dependency=_ensure_pypi_dependency(source)
    elif source.get("type")=="apt":
        dependency=_ensure_apt_dependencies(source)
    elif source.get("type") in {"python_stdlib","system_tool"}:
        dependency=_ensure_local_dependency(source)
    elif source.get("type"):
        raise Blocker("BOUND_CAPABILITY_SOURCE_UNSUPPORTED:"+str(source.get("type")))
    module_name=str(entry.get("adapter_module") or "")
    if not module_name or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for ch in module_name):
        raise Blocker("BOUND_CAPABILITY_ADAPTER_INVALID")
    path=ROOT/"canonical"/"runtime"/"bound_capabilities"/(module_name+".py")
    if not path.is_file():
        raise Blocker("BOUND_CAPABILITY_ADAPTER_MISSING")
    spec=importlib.util.spec_from_file_location("project_brain_bound_"+module_name,path)
    if spec is None or spec.loader is None:
        raise Blocker("BOUND_CAPABILITY_ADAPTER_LOAD_FAILED")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    fn=getattr(module,str(entry.get("entrypoint") or "run"),None)
    if not callable(fn):
        raise Blocker("BOUND_CAPABILITY_ENTRYPOINT_MISSING")
    call_args=dict(args)
    call_args.pop("capability_id",None)
    result=fn(call_args,ROOT)
    if not isinstance(result,dict):
        raise Blocker("BOUND_CAPABILITY_RESULT_INVALID")
    result.setdefault("capability_id",cid)
    result["dependency"]=dependency
    return result

def _verify_action_expectation(action,result):
    expect=action.get("expect")
    if expect is None:
        return
    if not isinstance(expect,dict):
        raise Blocker("ACTION_EXPECTATION_INVALID")
    field=str(expect.get("field") or "").strip()
    if not field:
        raise Blocker("ACTION_EXPECTATION_FIELD_REQUIRED")
    value=result.get(field)
    typ=expect.get("type","field_nonempty")
    if typ=="field_nonempty":
        ok=value not in (None,"",[],{})
    elif typ=="field_contains":
        ok=str(expect.get("value","")) in str(value or "")
    elif typ=="field_equals":
        ok=value==expect.get("value")
    else:
        raise Blocker("ACTION_EXPECTATION_TYPE_UNKNOWN:"+str(typ))
    if not ok:
        observed=json.dumps(value,ensure_ascii=False,sort_keys=True) if isinstance(value,(dict,list)) else repr(value)
        observed=observed.replace("\\n"," ")[:800]
        raise Blocker("ACTION_EXPECTATION_FAILED:"+field+":OBSERVED="+observed)

def _resolve_result_refs(value, trace):
    if isinstance(value,dict):
        if set(value.keys())=={"$result"}:
            spec=value["$result"]
            if not isinstance(spec,dict):
                raise Blocker("RESULT_REFERENCE_INVALID")
            cycle=int(spec.get("cycle",-1))
            if cycle<0 or cycle>=len(trace):
                raise Blocker("RESULT_REFERENCE_CYCLE_INVALID:"+str(cycle))
            current=trace[cycle].get("result")
            field=str(spec.get("field") or "").strip()
            if field:
                for part in field.split("."):
                    if not isinstance(current,dict) or part not in current:
                        raise Blocker("RESULT_REFERENCE_FIELD_MISSING:"+field)
                    current=current[part]
            return current
        return {k:_resolve_result_refs(v,trace) for k,v in value.items()}
    if isinstance(value,list):
        return [_resolve_result_refs(v,trace) for v in value]
    return value


def _goal_action(action):
    typ=action.get("type")
    args=action.get("args") or {}
    if typ=="list_tree":
        base=_safe_repo_path(args.get("prefix",""))
        if not base.exists(): return {"type":typ,"error":"PATH_NOT_FOUND","path":str(args.get("prefix",""))}
        items=[]
        if base.is_file():
            items=[str(base.relative_to(ROOT))]
        else:
            for p in sorted(base.rglob("*")):
                if p.is_file():
                    items.append(str(p.relative_to(ROOT)))
                    if len(items)>=80: break
        return {"type":typ,"items":items,"truncated":len(items)>=80}
    if typ=="read_file":
        p=_safe_repo_path(args.get("path",""))
        if not p.is_file(): return {"type":typ,"error":"FILE_NOT_FOUND","path":str(args.get("path",""))}
        text=p.read_text(encoding="utf-8",errors="replace")
        return {"type":typ,"path":str(p.relative_to(ROOT)),"content":text[:6000],"truncated":len(text)>6000}
    if typ=="search_text":
        q=str(args.get("query",""))
        if not q: return {"type":typ,"error":"EMPTY_QUERY"}
        hits=[]
        for p in sorted((ROOT/"canonical").rglob("*")):
            if not p.is_file() or p.suffix.lower() not in {".json",".md",".py",".txt",".yml",".yaml"}: continue
            try: text=p.read_text(encoding="utf-8",errors="replace")
            except Exception: continue
            if q.lower() in text.lower():
                hits.append(str(p.relative_to(ROOT)))
                if len(hits)>=80: break
        return {"type":typ,"query":q,"hits":hits,"truncated":len(hits)>=80}
    if typ=="assert_file_exists":
        p=_safe_repo_path(args.get("path",""))
        return {
          "type":typ,
          "path":str(p.relative_to(ROOT)) if p.exists() else str(args.get("path","")),
          "exists":p.is_file(),
          "verified":p.is_file(),
          "sha256":sha_file(p) if p.is_file() else None,
        }
    if typ=="assert_python_test_audit_zero":
        audit_path=_safe_repo_path(args.get("audit_path",""))
        if not audit_path.is_file():
            return {"type":typ,"verified":False,"error":"PYTHON_TEST_AUDIT_MISSING"}
        try:
            audit=json.loads(audit_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"type":typ,"verified":False,"error":"PYTHON_TEST_AUDIT_JSON_INVALID:"+type(exc).__name__}
        totals=audit.get("totals") or {}
        ok=(
            audit.get("schema")=="PROJECT_BRAIN_PYTHON_TEST_AUDIT_V1"
            and int(totals.get("files",0))>0
            and int(totals.get("failed",-1))==0
            and int(totals.get("errors",-1))==0
            and int(totals.get("tests",0))==(
                int(totals.get("passed",0))+int(totals.get("skipped",0))
            )
        )
        return {
          "type":typ,"verified":ok,
          "audit_path":str(audit_path.relative_to(ROOT)),
          "totals":totals,
          "audit_sha256":sha_file(audit_path),
        }
    if typ=="assert_python_test_audit_supported_by_fresh_execution":
        audit_path=_safe_repo_path(args.get("audit_path",""))
        source_root=_safe_repo_path(args.get("source_root",""))
        pattern=str(args.get("pattern") or "test_*.py")
        if not audit_path.is_file() or not source_root.is_dir():
            return {"type":typ,"verified":False,"error":"PYTHON_TEST_AUDIT_SOURCE_MISSING"}
        try:
            audit=json.loads(audit_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"type":typ,"verified":False,"error":"PYTHON_TEST_AUDIT_JSON_INVALID:"+type(exc).__name__}
        files=sorted(p for p in source_root.glob(pattern) if p.is_file())
        reported={str(x.get("path")):x for x in audit.get("records") or [] if isinstance(x,dict)}
        expected_paths={str(p.relative_to(ROOT)).replace("\\","/") for p in files}
        errors=[]
        if set(reported)!=expected_paths:
            errors.append("file_coverage_mismatch")
        totals={"files":0,"tests":0,"passed":0,"failed":0,"errors":0,"skipped":0}
        for p in files:
            rel=str(p.relative_to(ROOT)).replace("\\","/")
            try:
                proc=subprocess.run(
                    [sys.executable,str(p)],cwd=ROOT,text=True,capture_output=True,timeout=180
                )
            except Exception as exc:
                errors.append("execution:"+rel+":"+type(exc).__name__)
                continue
            combined=(proc.stdout or "")+"\n"+(proc.stderr or "")
            m=re.search(r"Ran\s+(\d+)\s+tests?\s+in\s+[0-9.]+s",combined)
            if not m:
                errors.append("summary_missing:"+rel)
                continue
            ran=int(m.group(1))
            skipped=0
            ok_match=re.search(r"OK\s*\(([^)]*)\)",combined)
            if ok_match:
                sm=re.search(r"skipped=(\d+)",ok_match.group(1))
                if sm:
                    skipped=int(sm.group(1))
            if proc.returncode!=0:
                errors.append("nonzero:"+rel+":"+str(proc.returncode))
            rec=reported.get(rel) or {}
            if (
                int(rec.get("exit_code",-1))!=0
                or int(rec.get("tests",-1))!=ran
                or int(rec.get("failed",-1))!=0
                or int(rec.get("errors",-1))!=0
                or int(rec.get("skipped",-1))!=skipped
                or str(rec.get("sha256") or "")!=sha_file(p)
            ):
                errors.append("record_mismatch:"+rel)
            totals["files"]+=1
            totals["tests"]+=ran
            totals["passed"]+=max(0,ran-skipped)
            totals["skipped"]+=skipped
        if audit.get("totals")!=totals:
            errors.append("totals_mismatch")
        return {
          "type":typ,"verified":not errors,
          "audit_path":str(audit_path.relative_to(ROOT)),
          "source_root":str(source_root.relative_to(ROOT)),
          "pattern":pattern,
          "totals":totals,
          "errors":errors,
          "audit_sha256":sha_file(audit_path),
        }
    if typ=="assert_python_source_audit_supported_by_source":
        audit_path=_safe_repo_path(args.get("audit_path",""))
        source_root=_safe_repo_path(args.get("source_root",""))
        if not audit_path.is_file() or not source_root.is_dir():
            return {"type":typ,"verified":False,"error":"PYTHON_SOURCE_AUDIT_SOURCE_MISSING"}
        try:
            audit=json.loads(audit_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"type":typ,"verified":False,"error":"PYTHON_SOURCE_AUDIT_JSON_INVALID:"+type(exc).__name__}
        if audit.get("schema")!="PROJECT_BRAIN_PYTHON_SOURCE_AUDIT_V1":
            return {"type":typ,"verified":False,"error":"PYTHON_SOURCE_AUDIT_SCHEMA_INVALID"}
        actual={}
        imports=set()
        total_functions=0
        total_classes=0
        errors=[]
        for p in sorted(source_root.rglob("*.py")):
            if not p.is_file():
                continue
            raw=p.read_bytes()
            rel=str(p.relative_to(ROOT)).replace("\\","/")
            try:
                tree=ast.parse(raw.decode("utf-8"),filename=str(p))
            except Exception as exc:
                errors.append("parse:"+rel+":"+type(exc).__name__)
                continue
            funcs=sorted(n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)))
            classes=sorted(n.name for n in tree.body if isinstance(n,ast.ClassDef))
            mods=set()
            for n in tree.body:
                if isinstance(n,ast.Import):
                    mods.update(a.name.split(".")[0] for a in n.names)
                elif isinstance(n,ast.ImportFrom) and n.module:
                    mods.add(n.module.split(".")[0])
            actual[rel]={
              "sha256":hashlib.sha256(raw).hexdigest(),
              "imports":sorted(mods),
              "functions":funcs,
              "classes":classes,
            }
            imports.update(mods)
            total_functions+=len(funcs)
            total_classes+=len(classes)
        reported={}
        for item in audit.get("files") or []:
            if not isinstance(item,dict) or not item.get("path"):
                errors.append("invalid_record")
                continue
            reported[str(item["path"])]={
              "sha256":item.get("sha256"),
              "imports":sorted(item.get("imports") or []),
              "functions":sorted(item.get("functions") or []),
              "classes":sorted(item.get("classes") or []),
            }
        if reported!=actual:
            errors.append("records_mismatch")
        expected_totals={
          "files":len(actual),
          "functions":total_functions,
          "classes":total_classes,
          "distinct_imported_modules":len(imports),
        }
        if audit.get("totals")!=expected_totals:
            errors.append("totals_mismatch")
        if sorted(audit.get("distinct_imported_modules") or [])!=sorted(imports):
            errors.append("imports_total_mismatch")
        return {
          "type":typ,
          "verified":not errors,
          "audit_path":str(audit_path.relative_to(ROOT)),
          "source_root":str(source_root.relative_to(ROOT)),
          "file_count":len(actual),
          "function_count":total_functions,
          "class_count":total_classes,
          "distinct_imported_module_count":len(imports),
          "errors":errors,
          "audit_sha256":sha_file(audit_path),
        }
    if typ=="assert_workflow_audit_supported_by_source":
        audit_path=_safe_repo_path(args.get("audit_path",""))
        yaml_path=_safe_repo_path(args.get("yaml_path",""))
        if not audit_path.is_file() or not yaml_path.is_file():
            return {
              "type":typ,"verified":False,"error":"WORKFLOW_AUDIT_SOURCE_MISSING",
              "audit_path":str(args.get("audit_path","")),
              "yaml_path":str(args.get("yaml_path","")),
            }
        try:
            audit=json.loads(audit_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"type":typ,"verified":False,"error":"WORKFLOW_AUDIT_JSON_INVALID:"+type(exc).__name__}
        raw=yaml_path.read_text(encoding="utf-8")
        missing=[]
        if audit.get("schema")!="PROJECT_BRAIN_GITHUB_WORKFLOW_AUDIT_V1":
            missing.append("schema")
        name=str(audit.get("name") or "")
        if not name or not re.search(r"(?m)^name:\s*"+re.escape(name)+r"\s*$",raw):
            missing.append("name:"+name)
        triggers=list(audit.get("trigger_names") or [])
        if not triggers:
            missing.append("trigger_names:empty")
        for item in triggers:
            value=str(item)
            if not re.search(r"(?m)^  "+re.escape(value)+r":(?:\s*|\s+.*)$",raw):
                missing.append("trigger:"+value)
        for value in audit.get("push_branches") or []:
            if str(value) not in raw:
                missing.append("push_branch:"+str(value))
        for value in audit.get("push_paths") or []:
            if str(value) not in raw:
                missing.append("push_path:"+str(value))
        for value in audit.get("workflow_dispatch_input_names") or []:
            if not re.search(r"(?m)^\s{4,}"+re.escape(str(value))+r":\s*$",raw):
                missing.append("dispatch_input:"+str(value))
        permissions=audit.get("permissions") or {}
        if not isinstance(permissions,dict):
            missing.append("permissions:not_object")
            permissions={}
        for key,value in permissions.items():
            if not re.search(
                r"(?m)^\s{2}"+re.escape(str(key))+r":\s*"+re.escape(str(value))+r"\s*$",raw
            ):
                missing.append("permission:"+str(key)+"="+str(value))
        jobs=list(audit.get("jobs") or [])
        if not jobs:
            missing.append("jobs:empty")
        uses_count=0
        for job in jobs:
            if not isinstance(job,dict):
                missing.append("job:not_object")
                continue
            jid=str(job.get("id") or "")
            if not jid or not re.search(r"(?m)^  "+re.escape(jid)+r":\s*$",raw):
                missing.append("job_id:"+jid)
            runner=job.get("runner_label")
            if runner is None or not re.search(
                r"(?m)^\s{4}runs-on:\s*"+re.escape(str(runner))+r"\s*$",raw
            ):
                missing.append("runner:"+jid+":"+str(runner))
            timeout=job.get("timeout_minutes")
            if timeout is not None and not re.search(
                r"(?m)^\s{4}timeout-minutes:\s*"+re.escape(str(timeout))+r"\s*$",raw
            ):
                missing.append("timeout:"+jid+":"+str(timeout))
            for step_name in job.get("step_names") or []:
                if not re.search(
                    r"(?m)^\s*-\s+name:\s*"+re.escape(str(step_name))+r"\s*$",raw
                ):
                    missing.append("step_name:"+jid+":"+str(step_name))
            for ref in job.get("uses") or []:
                uses_count+=1
                if not re.search(
                    r"(?m)^\s*-?\s*uses:\s*"+re.escape(str(ref))+r"\s*$",raw
                ):
                    missing.append("uses:"+jid+":"+str(ref))
        return {
          "type":typ,
          "verified":not missing,
          "audit_path":str(audit_path.relative_to(ROOT)),
          "yaml_path":str(yaml_path.relative_to(ROOT)),
          "job_count":len(jobs),
          "uses_count":uses_count,
          "missing_support":missing,
          "audit_sha256":sha_file(audit_path),
          "source_sha256":sha_file(yaml_path),
        }
    if typ=="invoke_capability_fanout":
        source=_safe_repo_path(args.get("source_path",""))
        output_dir=_safe_repo_path(args.get("output_dir",""))
        manifest_path=_safe_repo_path(args.get("manifest_path",""))
        if not source.is_file():
            return {"type":typ,"output_verified":False,"error":"FANOUT_SOURCE_MISSING"}
        wrapper=json.loads(source.read_text(encoding="utf-8"))
        items=json.loads(str(wrapper.get("observed_text") or ""))
        if not isinstance(items,list) or len(items)>100:
            return {"type":typ,"output_verified":False,"error":"FANOUT_SOURCE_INVALID"}
        value_field=str(args.get("value_field") or "")
        threshold=int(args.get("max_length") or 0)
        output_dir.mkdir(parents=True,exist_ok=True)
        manifest=[]
        for item in items:
            item_id=str(item.get("id"))
            value=str(item.get(value_field) or "")
            use_match=len(value)<=threshold
            template=args.get("match_action") if use_match else args.get("other_action")
            kind=str(args.get("match_kind") if use_match else args.get("other_kind"))
            out=str((output_dir/(item_id+".png")).relative_to(ROOT))
            def subst(v):
                if isinstance(v,str):
                    if v=="__ITEM_VALUE__": return value
                    if v=="__ITEM_OUTPUT_PATH__": return out
                    return v
                if isinstance(v,list): return [subst(x) for x in v]
                if isinstance(v,dict): return {k:subst(x) for k,x in v.items()}
                return v
            inner=subst((template or {}).get("args") or {})
            result=_invoke_bound_capability(inner)
            if not result.get("output_verified"):
                return {"type":typ,"output_verified":False,"error":"FANOUT_ITEM_FAILED","id":item_id}
            manifest.append({"id":item.get("id"),value_field:item.get(value_field),"capability_kind":kind,"artifact_path":out})
        manifest_path.parent.mkdir(parents=True,exist_ok=True)
        manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        return {"type":typ,"output_verified":True,"item_count":len(manifest),"manifest_path":str(manifest_path.relative_to(ROOT))}
    if typ=="assert_runtime_fanout_decodes":
        source=_safe_repo_path(args.get("source_path",""))
        manifest_path=_safe_repo_path(args.get("manifest_path",""))
        if not source.is_file() or not manifest_path.is_file():
            return {"type":typ,"verified":False,"error":"FANOUT_VERIFY_SOURCE_MISSING"}
        wrapper=json.loads(source.read_text(encoding="utf-8"))
        items=json.loads(str(wrapper.get("observed_text") or ""))
        manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
        value_field=str(args.get("value_field") or "")
        threshold=int(args.get("max_length") or 0)
        match_kind=str(args.get("match_kind") or "")
        other_kind=str(args.get("other_kind") or "")
        if not isinstance(items,list) or not isinstance(manifest,list):
            return {"type":typ,"verified":False,"error":"FANOUT_VERIFY_INVALID"}
        by_id={str(x.get("id")):x for x in manifest if isinstance(x,dict) and "id" in x}
        failures=[]
        if len(items)!=len(manifest) or len(by_id)!=len(manifest):
            failures.append({"error":"CARDINALITY_MISMATCH"})
        for item in items:
            item_id=str(item.get("id"))
            value=str(item.get(value_field) or "")
            rec=by_id.get(item_id)
            expected_kind=match_kind if len(value)<=threshold else other_kind
            if rec is None or rec.get("capability_kind")!=expected_kind or str(rec.get(value_field) or "")!=value:
                failures.append({"id":item_id,"error":"MANIFEST_MISMATCH"})
                continue
            path=str(rec.get("artifact_path") or "")
            decoded=_invoke_bound_capability({
              "capability_id":"image.code.decode.zbarimg",
              "argv":["zbarimg","--quiet","--raw",path],
              "timeout_s":60,
            })
            if str(decoded.get("stdout") or "").strip()!=value:
                failures.append({"id":item_id,"error":"DECODE_MISMATCH"})
        return {"type":typ,"verified":not failures,"source_count":len(items),"manifest_count":len(manifest),"failures":failures[:20]}
    if typ=="assert_runtime_selected_code_decodes":
        source=_safe_repo_path(args.get("source_path",""))
        if not source.is_file():
            return {"type":typ,"verified":False,"error":"RUNTIME_VALUE_SOURCE_MISSING"}
        try:
            wrapper=json.loads(source.read_text(encoding="utf-8"))
            observed=json.loads(str(wrapper.get("observed_text") or ""))
        except Exception as exc:
            return {"type":typ,"verified":False,"error":"RUNTIME_VALUE_SOURCE_INVALID:"+type(exc).__name__}
        value=str(observed.get(str(args.get("value_key") or "")) or "")
        chars=set(str(args.get("match_chars") or "").lower())
        match_path=str(args.get("match_path") or "")
        other_path=str(args.get("other_path") or "")
        if not value or not chars or not match_path or not other_path:
            return {"type":typ,"verified":False,"error":"RUNTIME_VERIFY_SPEC_INVALID"}
        branch="match" if value[0].lower() in chars else "other"
        selected_path=match_path if branch=="match" else other_path
        decoded=_invoke_bound_capability({
          "capability_id":"image.code.decode.zbarimg",
          "argv":["zbarimg","--quiet","--raw",selected_path],
          "timeout_s":60,
        })
        observed_payload=str(decoded.get("stdout") or "").strip()
        return {
          "type":typ,
          "verified":observed_payload==value,
          "branch":branch,
          "selected_path":selected_path,
          "observed_value":value,
          "decoded_value":observed_payload,
          "decoder_capability":"image.code.decode.zbarimg",
        }
    if typ=="assert_collection_length_bucket":
        source=_safe_repo_path(args.get("source_path",""))
        output=_safe_repo_path(args.get("output_path",""))
        if not source.is_file() or not output.is_file():
            return {"type":typ,"verified":False,"error":"COLLECTION_SOURCE_MISSING"}
        try:
            src_wrap=json.loads(source.read_text(encoding="utf-8"))
            src=json.loads(str(src_wrap.get("observed_text") or ""))
            out=json.loads(output.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"type":typ,"verified":False,"error":"COLLECTION_JSON_INVALID:"+type(exc).__name__}
        copy_fields=[str(x) for x in (args.get("copy_fields") or [])]
        measured=str(args.get("measured_field") or "")
        label_field=str(args.get("label_field") or "bucket")
        threshold=int(args.get("max_length") or 0)
        short_label=str(args.get("short_label") or "")
        long_label=str(args.get("long_label") or "")
        if not isinstance(src,list) or not isinstance(out,list) or not copy_fields or not measured or threshold<0:
            return {"type":typ,"verified":False,"error":"COLLECTION_SPEC_INVALID"}
        if len(src)!=len(out):
            return {"type":typ,"verified":False,"error":"COLLECTION_LENGTH_MISMATCH","source_count":len(src),"output_count":len(out)}
        failures=[]
        for idx,(s,o) in enumerate(zip(src,out)):
            if not isinstance(s,dict) or not isinstance(o,dict):
                failures.append({"index":idx,"error":"RECORD_NOT_OBJECT"})
                continue
            copied=all(o.get(f)==s.get(f) for f in copy_fields)
            raw=str(s.get(measured) or "")
            expected=short_label if len(raw)<=threshold else long_label
            if not copied or o.get(label_field)!=expected:
                failures.append({"index":idx,"expected":expected,"observed":o.get(label_field),"copied":copied})
        return {
          "type":typ,
          "verified":not failures,
          "source_count":len(src),
          "output_count":len(out),
          "failures":failures[:20],
        }
    if typ=="assert_hex_prefix_bucket":
        source=_safe_repo_path(args.get("source_path",""))
        classified=_safe_repo_path(args.get("classification_path",""))
        if not source.is_file() or not classified.is_file():
            return {"type":typ,"verified":False,"error":"CONDITIONAL_SOURCE_MISSING"}
        try:
            src=json.loads(source.read_text(encoding="utf-8"))
            out=json.loads(classified.read_text(encoding="utf-8"))
            observed=json.loads(str(src.get("observed_text") or ""))
        except Exception as exc:
            return {"type":typ,"verified":False,"error":"CONDITIONAL_JSON_INVALID:"+type(exc).__name__}
        value=str(observed.get(str(args.get("source_key") or "uuid")) or "")
        claimed_value=str(out.get(str(args.get("output_value_field") or "uuid")) or "")
        claimed_bucket=str(out.get(str(args.get("bucket_field") or "bucket")) or "")
        low_chars=set(str(args.get("low_chars") or "01234567").lower())
        expected="LOW" if value and value[0].lower() in low_chars else "HIGH"
        return {
          "type":typ,
          "verified":bool(value and claimed_value==value and claimed_bucket==expected),
          "observed_value":value,
          "claimed_value":claimed_value,
          "claimed_bucket":claimed_bucket,
          "expected_bucket":expected,
        }
    if typ=="assert_json_fields_equal":
        p=_safe_repo_path(args.get("path",""))
        if not p.is_file():
            return {"type":typ,"verified":False,"error":"FILE_NOT_FOUND","path":str(args.get("path",""))}
        try:
            data=json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"type":typ,"verified":False,"error":"JSON_PARSE_FAILED:"+type(exc).__name__}
        def get_field(field):
            cur=data
            for part in str(field).split("."):
                if not isinstance(cur,dict) or part not in cur:
                    raise KeyError(field)
                cur=cur[part]
            return cur
        fields=list(args.get("fields") or [])
        true_fields=list(args.get("true_fields") or [])
        try:
            values={f:get_field(f) for f in fields}
            true_values={f:get_field(f) for f in true_fields}
        except KeyError as exc:
            return {"type":typ,"verified":False,"error":"JSON_FIELD_MISSING:"+str(exc)}
        nonempty=all(v not in (None,"") for v in values.values())
        equal=(len(set(json.dumps(v,sort_keys=True) for v in values.values()))<=1) if values else True
        truths=all(v is True for v in true_values.values())
        return {
          "type":typ,
          "path":str(p.relative_to(ROOT)),
          "fields":values,
          "true_fields":true_values,
          "all_equal":equal,
          "all_nonempty":nonempty,
          "all_true":truths,
          "verified":bool(equal and nonempty and truths),
        }
    if typ=="project_browser_result_json":
        source=_safe_repo_path(args.get("source_path",""))
        output=_safe_repo_path(args.get("output_path",""))
        if not source.is_file():
            return {"type":typ,"error":"SOURCE_JSON_NOT_FOUND","path":str(args.get("source_path",""))}
        try:
            data=json.loads(source.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"type":typ,"error":"SOURCE_JSON_INVALID:"+type(exc).__name__}
        collection=str(args.get("collection") or "").strip()
        record_id=str(args.get("record_id") or "").strip()
        if not collection or not record_id:
            return {"type":typ,"error":"COLLECTION_AND_RECORD_ID_REQUIRED"}
        constants=args.get("constants") or {}
        fields=args.get("fields") or []
        if not isinstance(constants,dict) or not isinstance(fields,list) or not fields:
            return {"type":typ,"error":"PROJECTION_SPEC_INVALID"}

        bag={}
        final_url=data.get("final_url")
        if final_url not in (None,""):
            bag["final_url"]=final_url
        for item in data.get("action_trace") or []:
            if not isinstance(item,dict):
                continue
            action=item.get("action") or {}
            observed=item.get("result") or {}
            if not isinstance(action,dict) or not isinstance(observed,dict):
                continue
            value=observed.get("value")
            if str(action.get("type") or "")=="check" and observed.get("checked") is True:
                value=observed.get("value") or action.get("target")
            if value is None:
                continue
            aliases=[]
            for raw_key in (action.get("target"),observed.get("name")):
                if not raw_key:
                    continue
                key="_".join(re.findall(r"[A-Za-z0-9]+",str(raw_key).lower()))
                if key and key not in aliases:
                    aliases.append(key)
            for key in aliases:
                bag[key]=value

        record=dict(constants)
        missing=[]
        for raw_field in fields:
            field=str(raw_field)
            if field in record:
                continue
            if field in bag:
                record[field]=bag[field]
                continue
            missing.append(field)
        if missing:
            return {"type":typ,"error":"PROJECTION_FIELDS_MISSING:"+json.dumps(missing,sort_keys=True),"available_fields":sorted(bag)}
        payload={collection:{record_id:record}}
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        raw=output.read_bytes()
        return {
          "type":typ,
          "source_path":str(source.relative_to(ROOT)),
          "output_path":str(output.relative_to(ROOT)),
          "collection":collection,
          "record_id":record_id,
          "fields":sorted(record),
          "record":record,
          "output_sha256":hashlib.sha256(raw).hexdigest(),
          "output_bytes":len(raw),
          "verified":True,
        }

    if typ=="http_get":
        url=str(args.get("url",""))
        if not url.startswith(("https://","http://")): return {"type":typ,"error":"UNSUPPORTED_URL"}
        return run_http({"url":url,"timeout_s":20,"max_bytes":60000})
    if typ=="invoke_capability_by_runtime_value":
        source=_safe_repo_path(args.get("source_path",""))
        if not source.is_file():
            return {"type":typ,"output_verified":False,"error":"RUNTIME_VALUE_SOURCE_MISSING"}
        try:
            wrapper=json.loads(source.read_text(encoding="utf-8"))
            observed=json.loads(str(wrapper.get("observed_text") or ""))
        except Exception as exc:
            return {"type":typ,"output_verified":False,"error":"RUNTIME_VALUE_SOURCE_INVALID:"+type(exc).__name__}
        value=str(observed.get(str(args.get("value_key") or "")) or "")
        chars=set(str(args.get("match_chars") or "").lower())
        if not value or not chars:
            return {"type":typ,"output_verified":False,"error":"RUNTIME_VALUE_CONDITION_INVALID"}
        branch="match" if value[0].lower() in chars else "other"
        selected=args.get(branch+"_action")
        if not isinstance(selected,dict) or selected.get("type")!="invoke_capability":
            return {"type":typ,"output_verified":False,"error":"RUNTIME_BRANCH_ACTION_INVALID"}
        def subst(v):
            if isinstance(v,str):
                return value if v=="__RUNTIME_VALUE__" else v
            if isinstance(v,list):
                return [subst(x) for x in v]
            if isinstance(v,dict):
                return {k:subst(x) for k,x in v.items()}
            return v
        inner_args=subst(selected.get("args") or {})
        result=_invoke_bound_capability(inner_args)
        return {
          "type":typ,
          "branch":branch,
          "observed_value":value,
          "selected_capability":inner_args.get("capability_id"),
          "selected_output_path":inner_args.get("output_path"),
          "selected_result":result,
          "output_verified":bool(result.get("output_verified")),
        }
    if typ=="invoke_capability":
        return _invoke_bound_capability(args)
    if typ=="assert_text_contains_json_keys":
        text=str(args.get("text") or "")
        p=_safe_repo_path(args.get("json_path",""))
        if not p.is_file():
            return {"type":typ,"error":"JSON_SOURCE_NOT_FOUND"}
        try:
            data=json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"type":typ,"error":"JSON_SOURCE_INVALID:"+type(exc).__name__}
        current=data
        collection_path=args.get("collection_path") or []
        if not isinstance(collection_path,list):
            return {"type":typ,"error":"COLLECTION_PATH_INVALID"}
        for part in collection_path:
            if not isinstance(current,dict) or str(part) not in current:
                return {"type":typ,"error":"COLLECTION_PATH_NOT_FOUND"}
            current=current[str(part)]
        if not isinstance(current,dict):
            return {"type":typ,"error":"JSON_KEY_COLLECTION_NOT_OBJECT"}
        expected=sorted(str(k) for k in current.keys())
        mode=str(args.get("normalization") or "exact")
        if mode=="alnum_upper":
            norm=lambda x: re.sub(r"[^A-Z0-9]+","",str(x).upper())
            observed=norm(text)
            missing=[key for key in expected if norm(key) not in observed]
        elif mode=="exact":
            missing=[key for key in expected if key not in text]
        else:
            return {"type":typ,"error":"NORMALIZATION_MODE_UNKNOWN"}
        return {
          "type":typ,
          "verified":not missing,
          "expected_key_count":len(expected),
          "expected_keys":expected,
          "missing_keys":missing,
          "json_path":str(p.relative_to(ROOT)),
          "normalization":mode,
        }
    if typ=="finish":
        return {"type":typ,"summary":str(args.get("summary",""))[:12000]}
    raise Blocker("GOAL_ACTION_NOT_ALLOWED:"+str(typ))

def _extract_json_object(text):
    text=str(text).strip()
    try: return json.loads(text)
    except Exception: pass
    a=text.find("{"); b=text.rfind("}")
    if a<0 or b<a: raise Blocker("PLANNER_NO_JSON")
    return json.loads(text[a:b+1])

def _planner_post(prompt, timeout_s=20):
    if os.environ.get("ASTRA_DISABLE_MODEL_PLANNER","").strip().lower() in {"1","true","yes","on"}:
        raise Blocker("MODEL_PLANNER_DISABLED_BY_POLICY")
    endpoint="https://text.pollinations.ai/"
    models=("openai-fast","openai","mistral")
    errors=[]
    for model in models:
        body=json.dumps({
          "messages":[{"role":"user","content":prompt}],
          "model":model,
          "jsonMode":True
        }).encode("utf-8")
        req=urllib.request.Request(
          endpoint,
          data=body,
          headers={"Content-Type":"application/json","User-Agent":"ProjectBrain/1.0"},
          method="POST"
        )
        t=time.monotonic()
        try:
            with urllib.request.urlopen(req,timeout=timeout_s) as r:
                raw=r.read(30000).decode("utf-8","replace")
            return {"text":raw,"model":model,"duration_s":round(time.monotonic()-t,3),"errors":errors}
        except Exception as e:
            errors.append({"model":model,"error":type(e).__name__+":"+str(e),"duration_s":round(time.monotonic()-t,3)})
    raise Blocker("PLANNER_ALL_ROUTES_FAILED:"+json.dumps(errors,sort_keys=True)[:1800])

def _controller_actions(step, mission):
    actions=step.get("controller_actions")
    ref=step.get("controller_actions_ref")
    if actions is None and ref:
        actions=mission.get(ref)
    if actions is None:
        return None
    if not isinstance(actions,list) or not actions:
        raise Blocker("MODEL_INDEPENDENT_CONTROLLER_ACTIONS_INVALID")
    limit=max(1,min(int(step.get("max_controller_actions",16)),64))
    if len(actions)>limit:
        raise Blocker("MODEL_INDEPENDENT_CONTROLLER_ACTION_LIMIT")
    return actions

def _run_model_independent_goal(step, mission, goal):
    actions=_controller_actions(step, mission)
    if actions is None:
        return None
    allowed_types={
      "read_file","list_tree","search_text","http_get","invoke_capability","invoke_capability_by_runtime_value","invoke_capability_fanout",
      "project_browser_result_json","assert_hex_prefix_bucket","assert_collection_length_bucket","assert_runtime_selected_code_decodes",
      "assert_text_contains_json_keys","assert_file_exists","assert_json_fields_equal",
      "assert_workflow_audit_supported_by_source","assert_python_source_audit_supported_by_source",
      "assert_python_test_audit_zero","assert_python_test_audit_supported_by_fresh_execution",
      "finish"
    }
    trace=[]
    for cycle, raw_action in enumerate(actions):
        if not isinstance(raw_action,dict):
            raise Blocker("MODEL_INDEPENDENT_CONTROLLER_ACTION_NOT_OBJECT")
        action=_resolve_result_refs(dict(raw_action),trace)
        typ=action.get("type")
        if typ not in allowed_types:
            raise Blocker("MODEL_INDEPENDENT_CONTROLLER_ACTION_REJECTED:"+str(typ))
        if not isinstance(action.get("args",{}),dict):
            raise Blocker("MODEL_INDEPENDENT_CONTROLLER_ARGS_INVALID")
        action.setdefault("args",{})
        result=_goal_action(action)
        if isinstance(result,dict) and result.get("error"):
            raise Blocker("MODEL_INDEPENDENT_ACTION_ERROR:"+str(result.get("error")))
        _verify_action_expectation(action,result)
        trace.append({"cycle":cycle,"plan":action,"result":result})
        if typ=="finish":
            summary=result.get("summary","")
            if not summary.strip():
                raise Blocker("MODEL_INDEPENDENT_CONTROLLER_EMPTY_FINISH")
            return {
              "adapter":"goal","returncode":0,
              "stdout":summary,
              "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
              "planner_source":None,
              "planner_transport":None,
              "planner_model_last":None,
              "cycles":cycle+1,"trace":trace,
              "final_summary":summary
            }
    raise Blocker("MODEL_INDEPENDENT_CONTROLLER_PLAN_WITHOUT_FINISH")

def _capability_problem(step, mission):
    problem=step.get("capability_problem")
    ref=step.get("capability_problem_ref")
    if problem is None and ref:
        problem=mission.get(ref)
    if problem is None:
        return None
    if not isinstance(problem,dict):
        raise Blocker("CAPABILITY_PROBLEM_INVALID")
    return problem

def _load_capability_planner():
    path=pathlib.Path(__file__).resolve().with_name("capability_planner.py")
    spec=importlib.util.spec_from_file_location("project_brain_capability_planner",path)
    if spec is None or spec.loader is None:
        raise Blocker("CAPABILITY_PLANNER_LOAD_FAILED")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

def _load_capability_discovery():
    path=pathlib.Path(__file__).resolve().with_name("capability_discovery.py")
    spec=importlib.util.spec_from_file_location("project_brain_capability_discovery",path)
    if spec is None or spec.loader is None:
        raise Blocker("CAPABILITY_DISCOVERY_LOAD_FAILED")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

def _load_goal_compiler():
    path=pathlib.Path(__file__).resolve().with_name("goal_compiler.py")
    spec=importlib.util.spec_from_file_location("project_brain_goal_compiler",path)
    if spec is None or spec.loader is None:
        raise Blocker("GOAL_COMPILER_LOAD_FAILED")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module

def _load_auto_apt_cli_acquisition():
    path=pathlib.Path(__file__).resolve().with_name("auto_apt_cli_acquisition.py")
    spec=importlib.util.spec_from_file_location("project_brain_auto_apt_cli_acquisition",path)
    if spec is None or spec.loader is None:
        raise Blocker("AUTO_APT_CLI_ACQUISITION_LOAD_FAILED")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    runtime_dir=str(path.parent)
    added=runtime_dir not in sys.path
    if added:
        sys.path.insert(0,runtime_dir)
    try:
        spec.loader.exec_module(module)
    finally:
        if added:
            try:
                sys.path.remove(runtime_dir)
            except ValueError:
                pass
    return module

def _compile_plain_goal(goal):
    compiler=_load_goal_compiler()
    try:
        return compiler.compile_goal(goal,_load_bound_capability_registry(),ROOT)
    except Exception as e:
        code=getattr(e,"code",type(e).__name__)
        detail=str(getattr(e,"detail","") or "")
        suffix=(":"+detail) if detail else ""
        raise Blocker("GOAL_COMPILATION_FAILED:"+str(code)+suffix) from e

def _discover_unreachable_effects(mission, error):
    detail=str(getattr(error,"detail","") or "")
    effects=[x.strip() for x in detail.split(",") if x.strip()]
    if not effects:
        effects=["unknown.capability"]
    discovery=_load_capability_discovery()
    results=[]
    for effect in effects[:8]:
        results.append(discovery.search_all(effect,limit_per_source=8))
    evidence={
      "schema":"PROJECT_BRAIN_CAPABILITY_ACQUISITION_GAP_V1",
      "mission_id":mission.get("mission_id"),
      "planner_failure_code":getattr(error,"code",type(error).__name__),
      "unreachable_effects":effects,
      "discovery_sources":["OFFICIAL_MCP_REGISTRY"],
      "results":results,
      "binding_performed":False,
      "policy":"DISCOVERY_ONLY__BINDING_REQUIRES_SEPARATE_ZERO_COST_SECURITY_AND_EFFECT_VERIFICATION",
      "observed_at_utc":utc()
    }
    mid=str(mission.get("mission_id") or "UNKNOWN")
    path=EVID_DIR/f"{mid}__CAPABILITY_ACQUISITION_GAP.json"
    writej(path,evidence)
    return path,evidence

def _render_bound_template(value, inputs):
    if isinstance(value,dict):
        return {k:_render_bound_template(v,inputs) for k,v in value.items()}
    if isinstance(value,list):
        return [_render_bound_template(v,inputs) for v in value]
    if isinstance(value,str):
        if value.startswith("${input.") and value.endswith("}") and value.count("${")==1:
            key=value[len("${input."):-1]
            if key not in inputs:
                raise Blocker("BOUND_CAPABILITY_INPUT_MISSING:"+key)
            return inputs[key]
        out=value
        for key,val in inputs.items():
            out=out.replace("${input."+str(key)+"}",str(val))
        if "${input." in out:
            raise Blocker("BOUND_CAPABILITY_INPUT_MISSING")
        return out
    return value

def _inherit_verified_capabilities(problem):
    enriched=json.loads(json.dumps(problem))
    caps=enriched.setdefault("capabilities",[])
    if not isinstance(caps,list):
        raise Blocker("CAPABILITIES_INVALID")
    existing={str(x.get("id")) for x in caps if isinstance(x,dict)}
    inputs=enriched.get("inputs") or {}
    if not isinstance(inputs,dict):
        raise Blocker("CAPABILITY_INPUTS_INVALID")
    inherited=[]
    for cid,entry in sorted(_load_bound_capability_registry().items()):
        if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
            continue
        if cid in existing:
            continue
        platforms=entry.get("platforms")
        if isinstance(platforms,list) and platforms:
            current="linux" if sys.platform.startswith("linux") else ("windows" if sys.platform.startswith("win") else sys.platform)
            if current not in platforms:
                continue
        template=entry.get("action_template")
        if not isinstance(template,dict):
            continue
        try:
            action=_render_bound_template(template,inputs)
        except Blocker:
            continue
        cap={
          "id":cid,
          "requires":list(entry.get("requires") or []),
          "provides":list(entry.get("provides") or []),
          "cost":float(entry.get("cost",1)),
          "action":action
        }
        caps.append(cap)
        inherited.append(cid)
    enriched["_inherited_bound_capabilities"]=inherited
    return enriched

def _run_capability_planned_goal(step, mission, goal):
    problem=_capability_problem(step, mission)
    if problem is None:
        return None
    problem=_inherit_verified_capabilities(problem)
    planner=_load_capability_planner()
    try:
        planned=planner.plan_actions(problem)
    except Exception as e:
        if getattr(e,"code",None)=="UNREACHABLE_TARGET_EFFECTS":
            path,evidence=_discover_unreachable_effects(mission,e)
            top=[]
            for result in evidence.get("results",[]):
                for candidate in result.get("candidates",[])[:3]:
                    top.append({
                      "name":candidate.get("name"),
                      "score":candidate.get("score"),
                      "zero_cost_eligible":candidate.get("zero_cost_eligible")
                    })
            detail=json.dumps({
              "evidence_path":str(path.relative_to(ROOT)),
              "top_candidates":top[:8]
            },sort_keys=True)
            raise Blocker("CAPABILITY_ACQUISITION_REQUIRED:"+detail) from e
        raise Blocker("CAPABILITY_PLANNING_FAILED:"+type(e).__name__+":"+str(e)) from e
    derived=dict(step)
    derived.pop("capability_problem",None)
    derived.pop("capability_problem_ref",None)
    derived["controller_actions"]=planned["actions"]
    derived["max_controller_actions"]=max(
        int(step.get("max_controller_actions",16)),
        len(planned["actions"])
    )
    result=_run_model_independent_goal(derived,mission,goal)
    if result is None:
        raise Blocker("CAPABILITY_PLAN_EXECUTION_MISSING")
    result["planning_mode"]="DETERMINISTIC_CAPABILITY_GRAPH"
    result["capability_plan"]=planned["planning"]
    result["inherited_bound_capabilities"]=problem.get("_inherited_bound_capabilities",[])
    return result

def run_goal(step, mission):
    goal=mission.get(step.get("goal_ref","goal"), mission.get("goal"))
    if isinstance(goal,(dict,list)): goal=json.dumps(goal,sort_keys=True)
    goal=str(goal or "").strip()
    if not goal: raise Blocker("GOAL_REQUIRED")
    capability_result=_run_capability_planned_goal(step, mission, goal)
    if capability_result is not None:
        return capability_result
    direct=_run_model_independent_goal(step, mission, goal)
    if direct is not None:
        return direct
    # No hand-authored capability graph or action plan: attempt a bounded,
    # deterministic compilation against capabilities already verified in Brain.
    # Unknown/ambiguous goals fail closed rather than silently becoming guesses.
    try:
        compiled=_compile_plain_goal(goal)
    except Blocker as e:
        error_text=str(e)
        acquisition_goal=goal
        unresolved_marker="GOAL_COMPILATION_FAILED:GOAL_COMPILATION_SUBGOAL_UNRESOLVED:"
        is_no_match="GOAL_COMPILATION_FAILED:GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH" in error_text
        is_unresolved_subgoal=unresolved_marker in error_text
        optional_planner=bool(step.get("allow_optional_model_planner",False))
        if is_unresolved_subgoal and not optional_planner:
            raw=error_text.split(unresolved_marker,1)[1]
            try:
                acquisition_goal=str(json.loads(raw).get("subgoal") or "").strip()
            except Exception:
                acquisition_goal=""
            if not acquisition_goal:
                raise
        if (is_no_match or is_unresolved_subgoal) and not optional_planner:
            mid=str(mission.get("mission_id") or "UNKNOWN")
            ep=EVID_DIR/f"{mid}__PLAIN_GOAL_CAPABILITY_DISCOVERY.json"
            auto=_load_auto_apt_cli_acquisition()

            # Fast path: try a bounded role-conditioned supplier acquisition
            # before paying for broad federated discovery.
            targeted_error=None
            try:
                dispatch=auto.dispatch(
                    acquisition_goal,
                    mid,
                    str(mission.get("_runtime_mission_path") or ""),
                    ROOT,
                    discovery=None
                )
            except Exception as ae:
                targeted_error=type(ae).__name__+":"+str(ae)
            else:
                evidence={
                  "schema":"PROJECT_BRAIN_PLAIN_GOAL_CAPABILITY_DISCOVERY_V1",
                  "mission_id":mid,
                  "goal":acquisition_goal,
                  "source":"TARGETED_AUTO_ACQUISITION",
                  "result":None,
                  "binding_performed":False,
                  "auto_acquisition":dispatch,
                  "status":"AUTO_ACQUISITION_DISPATCHED",
                  "observed_at_utc":utc()
                }
                writej(ep,evidence)
                raise Blocker("CAPABILITY_ACQUISITION_DISPATCHED:"+json.dumps(dispatch,sort_keys=True)) from e

            # Fallback only after the targeted route fails.
            discovery=_load_capability_discovery()
            result=discovery.search_all(acquisition_goal,limit_per_source=30)
            evidence={
              "schema":"PROJECT_BRAIN_PLAIN_GOAL_CAPABILITY_DISCOVERY_V1",
              "mission_id":mid,
              "goal":goal,
              "source":"FEDERATED_CAPABILITY_DISCOVERY_FALLBACK",
              "targeted_acquisition_error":targeted_error,
              "result":result,
              "binding_performed":False,
              "observed_at_utc":utc()
            }
            dispatch=None
            dispatch_error=None
            try:
                dispatch=auto.dispatch(
                    acquisition_goal,
                    mid,
                    str(mission.get("_runtime_mission_path") or ""),
                    ROOT,
                    discovery=result
                )
            except Exception as ae:
                dispatch_error=type(ae).__name__+":"+str(ae)
                evidence["auto_acquisition"]={"status":"NOT_DISPATCHED","error":dispatch_error}
            else:
                evidence["auto_acquisition"]=dispatch
                evidence["status"]="AUTO_ACQUISITION_DISPATCHED"
            writej(ep,evidence)
            if dispatch is not None:
                raise Blocker("CAPABILITY_ACQUISITION_DISPATCHED:"+json.dumps(dispatch,sort_keys=True)) from e
            top=[{
              "name":x.get("name"),"score":x.get("score"),
              "zero_cost_eligible":x.get("zero_cost_eligible"),
              "required_secret_count":x.get("required_secret_count"),
              "integration_friction":x.get("integration_friction")
            } for x in result.get("candidates",[])[:8]]
            raise Blocker("CAPABILITY_ACQUISITION_REQUIRED:"+json.dumps({
              "evidence_path":str(ep.relative_to(ROOT)),
              "top_candidates":top,
              "targeted_acquisition_error":targeted_error,
              "auto_acquisition_error":dispatch_error
            },sort_keys=True)) from e
        if not step.get("allow_optional_model_planner",False):
            raise
    else:
        if compiled.get("compiler_mode")=="DETERMINISTIC_COMPOUND_ACTION_PLAN":
            derived=dict(step)
            derived["controller_actions"]=compiled.get("controller_actions")
            derived["max_controller_actions"]=max(
                int(step.get("max_controller_actions",16)),
                len(compiled.get("controller_actions") or [])
            )
            compound_result=_run_model_independent_goal(derived,mission,goal)
            if compound_result is None:
                raise Blocker("COMPOUND_GOAL_PLAN_EXECUTION_MISSING")
            compound_result["planning_mode"]="DETERMINISTIC_COMPOUND_ACTION_PLAN"
            compound_result["goal_compilation"]={
              "compiler_mode":compiled.get("compiler_mode"),
              "clauses":compiled.get("clauses"),
              "compiled_parts":compiled.get("compiled_parts"),
            }
            return compound_result

        derived=dict(step)
        derived["capability_problem"]=compiled
        capability_result=_run_capability_planned_goal(derived, mission, goal)
        if capability_result is None:
            raise Blocker("GOAL_COMPILER_PLAN_EXECUTION_MISSING")
        capability_result["goal_compilation"]={
          "compiler_mode":compiled.get("compiler_mode"),
          "selected_capability":compiled.get("selected_capability"),
          "score":compiled.get("score"),
          "match_evidence":compiled.get("match_evidence"),
          "inputs":compiled.get("inputs"),
          "target_effects":compiled.get("target_effects"),
        }
        return capability_result
    if not step.get("allow_optional_model_planner",False):
        raise Blocker("MODEL_INDEPENDENT_CONTROLLER_PLAN_REQUIRED")
    observations=[]
    trace=[]
    max_cycles=max(1,min(int(step.get("max_cycles",6)),8))
    allowed="read_file(path), list_tree(prefix), search_text(query), http_get(url), finish(summary)"
    for cycle in range(max_cycles):
        compact=[]
        for item in observations[-6:]:
            a=item.get("action",{})
            r=item.get("result",{})
            rr=dict(r) if isinstance(r,dict) else {"value":str(r)}
            if isinstance(rr.get("items"),list):
                rr["items"]=rr["items"][:40]
            if isinstance(rr.get("hits"),list):
                rr["hits"]=rr["hits"][:30]
            if isinstance(rr.get("content"),str):
                rr["content"]=rr["content"][:2500]
            if isinstance(rr.get("body_excerpt"),str):
                rr["body_excerpt"]=rr["body_excerpt"][:2500]
            compact.append({"action":a,"result":rr})
        obs=json.dumps(compact,sort_keys=True)[:5000]
        prompt=(
          "You are an OPTIONAL planning source, not the controller. "
          "DO NOT invoke tools or function calls. DO NOT return tool_calls. Emit JSON text only. "
          "Goal: "+goal+"\nAllowed action types: "+allowed+". "
          "Choose the smallest next evidence action only. No writes, no shell, no secrets. "
          "If evidence is sufficient, use finish. Return exactly this schema: "
          '{"actions":[{"type":"...","args":{},"why":"..."}],"stop_after_evidence":true}. '
          "Observations so far: "+obs
        )
        planned=_planner_post(prompt, timeout_s=20)
        obj=_extract_json_object(planned.get("text",""))
        action=obj.get("action")
        if not isinstance(action,dict):
            actions=obj.get("actions")
            if isinstance(actions,list) and actions and isinstance(actions[0],dict):
                action=actions[0]
        if not isinstance(action,dict) and isinstance(obj.get("next_action"),dict):
            action=obj["next_action"]
        if not isinstance(action,dict):
            tc=obj.get("tool_calls")
            if isinstance(tc,list) and tc and isinstance(tc[0],dict):
                call=tc[0]
                fn=call.get("function") if isinstance(call.get("function"),dict) else call
                name=fn.get("name")
                raw_args=fn.get("arguments",{})
                if isinstance(raw_args,str):
                    try: raw_args=json.loads(raw_args)
                    except Exception: raw_args={}
                if isinstance(name,str) and isinstance(raw_args,dict):
                    action={"type":name,"args":raw_args,"why":str(obj.get("reasoning","tool_call"))}
        if not isinstance(action,dict) and isinstance(obj.get("type"),str):
            action=obj
        if not isinstance(action,dict) and isinstance(obj.get("reasoning"),str) and obj["reasoning"].strip():
            normalize_prompt=(
              "Convert this planner intent into ONE allowed action. Return JSON text only, no reasoning, no tool_calls. "
              "Allowed action types: "+allowed+". Schema exactly: "
              '{"actions":[{"type":"...","args":{},"why":"normalized planner intent"}]}. '
              "Planner intent: "+obj["reasoning"][:5000]
            )
            normalized=_planner_post(normalize_prompt, timeout_s=20)
            nobj=_extract_json_object(normalized.get("text",""))
            na=nobj.get("action")
            if not isinstance(na,dict):
                nas=nobj.get("actions")
                if isinstance(nas,list) and nas and isinstance(nas[0],dict):
                    na=nas[0]
            if isinstance(na,dict):
                action=na
        if not isinstance(action,dict):
            diag=json.dumps(obj,sort_keys=True)[:2200].replace("\n"," ")
            raise Blocker("PLANNER_ACTION_MISSING_OBJECT:"+diag)
        typ=action.get("type")
        # Some optional planner providers return a free-form `commentary`
        # pseudo-action even when instructed to emit one typed action. Treat
        # that as untrusted intent and normalize it through the same bounded
        # second-pass path already used for free-form reasoning. The runtime
        # still executes only its existing allowlisted action types.
        if typ=="commentary":
            args=action.get("args") if isinstance(action.get("args"),dict) else {}
            intent=""
            for key in ("text","content","message","commentary","value"):
                if isinstance(args.get(key),str) and args[key].strip():
                    intent=args[key].strip(); break
            if not intent and isinstance(action.get("why"),str):
                intent=action["why"].strip()
            if not intent:
                intent=json.dumps(action,sort_keys=True)[:5000]
            normalize_prompt=(
              "Convert this planner commentary into ONE allowed action. Return JSON text only, no reasoning, no tool_calls. "
              "Allowed action types: "+allowed+". Schema exactly: "
              '{"actions":[{"type":"...","args":{},"why":"normalized planner commentary"}]}. '
              "Planner commentary: "+intent[:5000]
            )
            normalized=_planner_post(normalize_prompt, timeout_s=20)
            nobj=_extract_json_object(normalized.get("text",""))
            na=nobj.get("action")
            if not isinstance(na,dict):
                nas=nobj.get("actions")
                if isinstance(nas,list) and nas and isinstance(nas[0],dict):
                    na=nas[0]
            if not isinstance(na,dict):
                raise Blocker("PLANNER_COMMENTARY_NORMALIZATION_FAILED")
            action=na
            typ=action.get("type")
        allowed_types={"read_file","list_tree","search_text","http_get","finish"}
        if isinstance(typ,str) and "." in typ:
            suffix=typ.rsplit(".",1)[-1]
            if suffix in allowed_types:
                typ=suffix
                action=dict(action)
                action["type"]=suffix
        if typ not in allowed_types:
            raise Blocker("PLANNER_ACTION_REJECTED:"+str(typ))
        if not isinstance(action.get("args"),dict): raise Blocker("PLANNER_ARGS_INVALID")
        result=_goal_action(action)
        trace.append({"cycle":cycle,"plan":action,"result":result})
        if typ=="finish":
            summary=result.get("summary","")
            if not summary.strip(): raise Blocker("PLANNER_EMPTY_FINISH")
            return {
              "adapter":"goal","returncode":0,
              "stdout":summary,
              "controller_mode":"OPTIONAL_MODEL_ADVISORY",
              "planner_source":"https://text.pollinations.ai/",
              "planner_transport":"POST_BOUNDED_FAILOVER",
              "planner_model_last":planned.get("model"),
              "cycles":cycle+1,"trace":trace,
              "final_summary":summary
            }
        observations.append({"action":action,"result":result})
    raise Blocker("GOAL_MAX_CYCLES_WITHOUT_FINISH")

def execute_step(step, prior_results=None, mission=None):
    adapter=step["adapter"]
    if adapter=="shell":
        return run_shell(step, prior_results)
    if adapter=="http":
        return run_http(step)
    if adapter=="goal":
        return run_goal(step, mission or {})
    raise Blocker("MISSING_ADAPTER:"+adapter)

def verify(step,result):
    v=step.get("verify",{})
    # A content/file predicate cannot erase process failure. Earlier runtime
    # versions incorrectly allowed non-zero shell commands to pass whenever a
    # marker string or file happened to exist.
    if "returncode" in result and result.get("returncode") != 0 and not v.get("allow_nonzero_returncode",False):
        return False
    typ=v.get("type","returncode_zero")
    if typ=="returncode_zero":
        return result.get("returncode")==0
    if typ=="stdout_contains":
        return v["text"] in result.get("stdout","")
    if typ=="file_exists":
        return (ROOT/v["path"]).exists()
    if typ=="json_field_equals":
        x=readj(ROOT/v["path"])
        cur=x
        for k in v["field"].split("."): cur=cur[k]
        return cur==v["value"]
    if typ=="http_status":
        return result.get("status")==v["value"]
    raise Blocker("UNKNOWN_VERIFIER:"+typ)

def main():
    STATE_DIR.mkdir(parents=True,exist_ok=True)
    EVID_DIR.mkdir(parents=True,exist_ok=True)
    ap=argparse.ArgumentParser()
    ap.add_argument("mission")
    a=ap.parse_args()
    mission_path=(ROOT/a.mission).resolve()
    if ROOT.resolve() not in mission_path.parents:
        raise Blocker("MISSION_PATH_OUTSIDE_ROOT")
    mission=readj(mission_path)
    mid=mission["mission_id"]
    mission_sha256=sha_file(mission_path)
    mission["_runtime_mission_path"]=a.mission
    state_path=STATE_DIR/f"{mid}.json"
    state=readj(state_path) if state_path.exists() else {
      "schema":"PROJECT_BRAIN_ASTRA_RUNTIME_STATE_V1",
      "mission_id":mid,"mission_path":a.mission,"mission_sha256":mission_sha256,
      "runtime_id":"ASTRA_RUNTIME_V1_SHARED",
      "status":"RUNNING","next_step":0,"history":[],"created_at_utc":utc()
    }
    if state.get("mission_id") != mid:
        raise Blocker("STATE_MISSION_ID_MISMATCH")
    if state.get("mission_path", a.mission) != a.mission:
        raise Blocker("STATE_MISSION_PATH_MISMATCH")
    prior_mission_sha256=state.get("mission_sha256")
    if (
        state.get("status")=="COMPLETE"
        and prior_mission_sha256
        and prior_mission_sha256!=mission_sha256
    ):
        blocker={
          "schema":"PROJECT_BRAIN_ASTRA_RUNTIME_BLOCKER_V1",
          "mission_id":mid,
          "phase":"MISSION_IDENTITY",
          "error":"COMPLETE_MISSION_HASH_DRIFT_REQUIRES_NEW_MISSION_ID",
          "completed_mission_sha256":prior_mission_sha256,
          "current_mission_sha256":mission_sha256,
          "observed_at_utc":utc()
        }
        writej(EVID_DIR/f"{mid}__MISSION_DRIFT_BLOCKER.json",blocker)
        print(json.dumps(blocker))
        return 5
    state["mission_path"]=a.mission
    state["mission_sha256"]=mission_sha256
    # A durable checkpoint can outlive its executor, while filesystem/process
    # effects often cannot. Rehydrate explicitly marked prior steps before
    # resuming the first unfinished causal step on a fresh invocation.
    if state["next_step"] > 0:
        rehydrated=[]
        for j, prior in enumerate(mission["steps"][:state["next_step"]]):
            if not prior.get("replay_on_resume", False):
                continue
            try:
                result=execute_step(prior, context_results(state), mission)
                ok=verify(prior,result)
            except Exception as e:
                blocker={
                  "schema":"PROJECT_BRAIN_ASTRA_RUNTIME_BLOCKER_V1",
                  "mission_id":mid,"step_index":j,"step_id":prior["id"],
                  "adapter":prior["adapter"],
                  "phase":"REHYDRATION",
                  "error":type(e).__name__+":"+str(e),
                  "observed_at_utc":utc()
                }
                writej(EVID_DIR/f"{mid}__BLOCKER.json",blocker)
                state["status"]="BLOCKED"; state["blocker"]=blocker; state["updated_at_utc"]=utc()
                writej(state_path,state)
                print(json.dumps(blocker)); return 3
            rec={"step_index":j,"step_id":prior["id"],"ok":bool(ok),"result":result,
                 "rehydration":True,"completed_at_utc":utc()}
            rehydrated.append(rec)
            if not ok:
                blocker={
                  "schema":"PROJECT_BRAIN_ASTRA_RUNTIME_BLOCKER_V1",
                  "mission_id":mid,"step_index":j,"step_id":prior["id"],
                  "adapter":prior["adapter"],"phase":"REHYDRATION",
                  "error":"VERIFICATION_FAILED","result":result,"observed_at_utc":utc()
                }
                writej(EVID_DIR/f"{mid}__BLOCKER.json",blocker)
                state["status"]="BLOCKED"; state["blocker"]=blocker; state["updated_at_utc"]=utc()
                writej(state_path,state)
                print(json.dumps(blocker)); return 4
        if rehydrated:
            state.setdefault("rehydrations",[]).append({
              "at_utc":utc(),"before_step":state["next_step"],"steps":rehydrated
            })
            state["updated_at_utc"]=utc()
            writej(state_path,state)

    for i in range(state["next_step"],len(mission["steps"])):
        step=mission["steps"][i]
        adapter=step["adapter"]
        try:
            result=execute_step(step, context_results(state), mission)
            ok=verify(step,result)
        except Exception as e:
            blocker={
              "schema":"PROJECT_BRAIN_ASTRA_RUNTIME_BLOCKER_V1",
              "mission_id":mid,"step_index":i,"step_id":step["id"],
              "adapter":adapter,"error":type(e).__name__+":"+str(e),
              "observed_at_utc":utc()
            }
            writej(EVID_DIR/f"{mid}__BLOCKER.json",blocker)
            state["status"]="BLOCKED"; state["blocker"]=blocker; state["updated_at_utc"]=utc()
            writej(state_path,state)
            print(json.dumps(blocker)); return 3
        rec={"step_index":i,"step_id":step["id"],"ok":bool(ok),"result":result,"completed_at_utc":utc()}
        state["history"].append(rec)
        if not ok:
            blocker={
              "schema":"PROJECT_BRAIN_ASTRA_RUNTIME_BLOCKER_V1",
              "mission_id":mid,"step_index":i,"step_id":step["id"],
              "adapter":adapter,"error":"VERIFICATION_FAILED",
              "result":result,"observed_at_utc":utc()
            }
            writej(EVID_DIR/f"{mid}__BLOCKER.json",blocker)
            state["status"]="BLOCKED"; state["blocker"]=blocker; state["updated_at_utc"]=utc()
            writej(state_path,state)
            print(json.dumps(blocker)); return 4
        state["next_step"]=i+1
        # A previously blocked mission may later succeed after a verified
        # repair/replay. Do not leave the obsolete blocker looking like live
        # state once forward progress has been re-established.
        state.pop("blocker",None)
        state["status"]="RUNNING"
        state["updated_at_utc"]=utc()
        writej(state_path,state)
    state.pop("blocker",None)
    state["status"]="COMPLETE"; state["completed_at_utc"]=utc()
    writej(state_path,state)
    receipt={
      "schema":"PROJECT_BRAIN_ASTRA_RUNTIME_RECEIPT_V1",
      "mission_id":mid,"mission_path":a.mission,"mission_sha256":mission_sha256,
      "runtime_id":"ASTRA_RUNTIME_V1_SHARED",
      "status":"COMPLETE","steps_completed":len(state["history"]),
      "state_sha256":sha_file(state_path),"completed_at_utc":utc()
    }
    writej(EVID_DIR/f"{mid}__RECEIPT.json",receipt)
    print(json.dumps(receipt)); return 0

if __name__=="__main__":
    raise SystemExit(main())
