#!/usr/bin/env python3
import argparse, ast, gzip, hashlib, importlib.util, json, os, pathlib, re, shlex, shutil, subprocess, sys, tempfile, time, urllib.parse, urllib.request
import importlib.metadata
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parents[2]

def _load_runtime_helper(module_name):
    path=ROOT/"canonical"/"runtime"/(str(module_name)+".py")
    if not path.is_file():
        raise Blocker("RUNTIME_HELPER_MISSING:"+str(module_name))
    spec=importlib.util.spec_from_file_location("project_brain_runtime_helper_"+str(module_name),path)
    if spec is None or spec.loader is None:
        raise Blocker("RUNTIME_HELPER_LOAD_FAILED:"+str(module_name))
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module
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

def _normalized_project_name(value):
    return re.sub(r"[-_.]+","-",str(value or "").strip()).lower()


def _verified_pypi_wheel_bytes(record):
    name=str(record.get("project") or "").strip()
    version=str(record.get("version") or "").strip()
    filename=str(record.get("filename") or "").strip()
    expected=str(record.get("sha256") or "").strip().lower()
    metadata_url=str(record.get("metadata_url") or "").strip()
    declared_url=str(record.get("url") or "").strip()
    if not all((name,version,filename,expected,metadata_url,declared_url)):
        raise Blocker("BOUND_PYPI_CLOSURE_RECORD_INCOMPLETE")
    if not re.fullmatch(r"[0-9a-f]{64}",expected):
        raise Blocker("BOUND_PYPI_CLOSURE_HASH_INVALID:"+name)
    req=urllib.request.Request(metadata_url,headers={"User-Agent":"ProjectBrain-BoundCapability/1"})
    with urllib.request.urlopen(req,timeout=20) as resp:
        meta=json.loads(resp.read(3000000).decode("utf-8"))
    matches=[u for u in meta.get("urls",[]) if str(u.get("filename") or "")==filename]
    if len(matches)!=1:
        raise Blocker("BOUND_PYPI_CLOSURE_WHEEL_NOT_UNIQUE:"+name)
    artifact=matches[0]
    metadata_sha=str((artifact.get("digests") or {}).get("sha256") or "").lower()
    url=str(artifact.get("url") or "")
    if metadata_sha!=expected:
        raise Blocker("BOUND_PYPI_CLOSURE_METADATA_HASH_MISMATCH:"+name)
    if url!=declared_url or not url.startswith("https://"):
        raise Blocker("BOUND_PYPI_CLOSURE_URL_MISMATCH:"+name)
    with urllib.request.urlopen(
        urllib.request.Request(url,headers={"User-Agent":"ProjectBrain-BoundCapability/1"}),
        timeout=45
    ) as resp:
        raw=resp.read(50000000)
    actual=hashlib.sha256(raw).hexdigest()
    if actual!=expected:
        raise Blocker("BOUND_PYPI_CLOSURE_WHEEL_HASH_MISMATCH:"+name)
    return raw


def _ensure_pypi_dependency(source):
    name=str(source.get("project") or "").strip()
    version=str(source.get("version") or "").strip()
    if not name or not version:
        raise Blocker("BOUND_PYPI_SOURCE_INCOMPLETE")

    closure=source.get("dependency_closure")
    if closure is None:
        # Backward compatibility for already-promoted single-wheel bindings.
        filename=str(source.get("wheel_filename") or "").strip()
        expected=str(source.get("wheel_sha256") or "").strip().lower()
        metadata_url=str(source.get("metadata_url") or "").strip()
        if not all((filename,expected,metadata_url)):
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

    if not isinstance(closure,dict) or closure.get("schema")!="PROJECT_BRAIN_PYPI_WHEEL_CLOSURE_V1":
        raise Blocker("BOUND_PYPI_CLOSURE_INVALID")
    wheels=closure.get("wheels")
    if not isinstance(wheels,list) or not wheels or len(wheels)>32:
        raise Blocker("BOUND_PYPI_CLOSURE_WHEELS_INVALID")
    if _normalized_project_name(closure.get("root_project"))!=_normalized_project_name(name):
        raise Blocker("BOUND_PYPI_CLOSURE_ROOT_PROJECT_MISMATCH")
    if str(closure.get("root_version") or "")!=version:
        raise Blocker("BOUND_PYPI_CLOSURE_ROOT_VERSION_MISMATCH")
    supplied_sha=str(closure.get("closure_sha256") or "")
    canonical=dict(closure)
    canonical.pop("closure_sha256",None)
    computed_sha=hashlib.sha256(
        json.dumps(canonical,sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()
    if not re.fullmatch(r"[0-9a-f]{64}",supplied_sha) or supplied_sha!=computed_sha:
        raise Blocker("BOUND_PYPI_CLOSURE_LOCK_HASH_MISMATCH")

    expected_versions={}
    for record in wheels:
        if not isinstance(record,dict):
            raise Blocker("BOUND_PYPI_CLOSURE_RECORD_INVALID")
        project=str(record.get("project") or "").strip()
        wheel_version=str(record.get("version") or "").strip()
        key=_normalized_project_name(project)
        if not key or not wheel_version:
            raise Blocker("BOUND_PYPI_CLOSURE_IDENTITY_INVALID")
        if key in expected_versions and expected_versions[key]!=wheel_version:
            raise Blocker("BOUND_PYPI_CLOSURE_VERSION_CONFLICT:"+project)
        expected_versions[key]=wheel_version

    already=True
    for record in wheels:
        project=str(record.get("project") or "")
        expected_version=str(record.get("version") or "")
        try:
            installed=importlib.metadata.version(project)
        except importlib.metadata.PackageNotFoundError:
            already=False
            break
        if installed!=expected_version:
            already=False
            break
    if already:
        return {
          "status":"ALREADY_INSTALLED",
          "project":name,"version":version,
          "dependency_wheel_count":len(wheels),
          "closure_sha256":supplied_sha,
        }

    with tempfile.TemporaryDirectory(prefix="project-brain-pypi-closure-") as td:
        wheelhouse=pathlib.Path(td)/"wheelhouse"
        wheelhouse.mkdir()
        total_bytes=0
        local_wheels=[]
        for record in wheels:
            raw=_verified_pypi_wheel_bytes(record)
            total_bytes+=len(raw)
            if total_bytes>160000000:
                raise Blocker("BOUND_PYPI_CLOSURE_BYTES_LIMIT")
            p=wheelhouse/str(record.get("filename"))
            p.write_bytes(raw)
            local_wheels.append(p)
        proc=subprocess.run(
            [
              sys.executable,"-m","pip","install",
              "--disable-pip-version-check","--quiet",
              "--no-index","--no-deps",
              *[str(p) for p in local_wheels],
            ],
            cwd=ROOT,text=True,capture_output=True,timeout=240
        )
        if proc.returncode!=0:
            raise Blocker("BOUND_PYPI_CLOSURE_INSTALL_FAILED:"+proc.stderr[-1800:])

    mismatches=[]
    for record in wheels:
        project=str(record.get("project") or "")
        expected_version=str(record.get("version") or "")
        try:
            installed=importlib.metadata.version(project)
        except importlib.metadata.PackageNotFoundError:
            mismatches.append({"project":project,"expected":expected_version,"observed":None})
            continue
        if installed!=expected_version:
            mismatches.append({"project":project,"expected":expected_version,"observed":installed})
    if mismatches:
        raise Blocker("BOUND_PYPI_CLOSURE_INSTALLED_VERSION_MISMATCH:"+json.dumps(mismatches,sort_keys=True)[:1400])
    return {
      "status":"INSTALLED_VERIFIED",
      "project":name,"version":version,
      "dependency_wheel_count":len(wheels),
      "closure_sha256":supplied_sha,
      "wheels":[
        {"project":x.get("project"),"version":x.get("version"),"filename":x.get("filename"),"sha256":x.get("sha256")}
        for x in wheels
      ],
    }


def _ensure_npm_dependency(source):
    npm_package_utils=_load_runtime_helper("npm_package_utils")
    package=str(source.get("package") or "").strip()
    version=str(source.get("version") or "").strip()
    metadata_url=str(source.get("metadata_url") or "").strip()
    tarball_url=str(source.get("tarball_url") or "").strip()
    integrity=str(source.get("integrity") or "").strip()
    if not all((package,version,metadata_url,tarball_url,integrity)):
        raise Blocker("BOUND_NPM_SOURCE_INCOMPLETE")
    if int(source.get("dependency_count") or 0)!=0:
        raise Blocker("BOUND_NPM_DEPENDENCY_CLOSURE_UNSUPPORTED")
    if not shutil.which("node"):
        raise Blocker("BOUND_NPM_NODE_RUNTIME_MISSING")
    try:
        fetched=npm_package_utils.fetch_verified_tarball(
            package,version,tarball_url,integrity,timeout_s=30,max_bytes=30_000_000
        )
    except Exception as exc:
        raise Blocker("BOUND_NPM_TARBALL_VERIFICATION_FAILED:"+type(exc).__name__+":"+str(exc)) from exc
    if str(fetched.get("metadata_url") or "")!=metadata_url:
        raise Blocker("BOUND_NPM_METADATA_URL_MISMATCH")
    expected_digest=str(source.get("integrity_digest_hex") or "").lower()
    if expected_digest and str(fetched.get("digest_hex") or "").lower()!=expected_digest:
        raise Blocker("BOUND_NPM_INTEGRITY_DIGEST_MISMATCH")
    cache=ROOT/"canonical"/"astra_runtime"/"tmp"/"npm_bound"/npm_package_utils.cache_key(package,version,integrity)
    package_root=cache/"package"
    marker=cache/"BOUND_NPM_PACKAGE.json"
    expected_marker={
      "package":package,"version":version,"integrity":integrity,
      "digest_hex":fetched.get("digest_hex"),"algorithm":fetched.get("algorithm"),
    }
    if marker.is_file() and package_root.is_dir():
        try:
            observed=json.loads(marker.read_text(encoding="utf-8"))
        except Exception:
            observed=None
        if observed==expected_marker and (package_root/"package.json").is_file():
            return {
              "status":"ALREADY_MATERIALIZED","package":package,"version":version,
              "package_root":str(package_root),"integrity":integrity,
              "digest_hex":fetched.get("digest_hex"),
            }
    if cache.exists():
        shutil.rmtree(cache)
    package_root.mkdir(parents=True,exist_ok=True)
    try:
        extracted=npm_package_utils.safe_extract_package(fetched["raw"],package_root)
        npm_package_utils.validate_zero_dependency_package(extracted["package_json"])
    except Exception as exc:
        if cache.exists(): shutil.rmtree(cache)
        raise Blocker("BOUND_NPM_EXTRACTION_FAILED:"+type(exc).__name__+":"+str(exc)) from exc
    marker.parent.mkdir(parents=True,exist_ok=True)
    marker.write_text(json.dumps(expected_marker,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return {
      "status":"MATERIALIZED_VERIFIED","package":package,"version":version,
      "package_root":str(package_root),"integrity":integrity,
      "digest_hex":fetched.get("digest_hex"),
    }


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
    call_args=dict(args)
    call_args.pop("capability_id",None)
    dependency=None
    if source.get("type")=="pypi":
        dependency=_ensure_pypi_dependency(source)
    elif source.get("type")=="npm":
        dependency=_ensure_npm_dependency(source)
        call_args["_package_root"]=dependency.get("package_root")
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
    if typ=="write_json_records":
        output=_safe_repo_path(args.get("output_path",""))
        fields=args.get("fields")
        records=args.get("records")
        if (
            not isinstance(fields,list) or not fields
            or len(fields)>64
            or any(not isinstance(x,str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",x) for x in fields)
            or len(set(fields))!=len(fields)
            or not isinstance(records,list)
            or len(records)>10000
        ):
            return {"type":typ,"verified":False,"error":"JSON_RECORD_SPEC_INVALID"}
        normalized=[]
        for record in records:
            if not isinstance(record,dict) or set(record)!=set(fields):
                return {"type":typ,"verified":False,"error":"JSON_RECORD_FIELDS_MISMATCH"}
            normalized.append({field:record[field] for field in fields})
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(normalized,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        raw=output.read_bytes()
        reread=json.loads(raw.decode("utf-8"))
        return {
          "type":typ,
          "verified":reread==normalized,
          "output_path":str(output.relative_to(ROOT)),
          "record_count":len(normalized),
          "fields":fields,
          "output_sha256":hashlib.sha256(raw).hexdigest(),
          "output_bytes":len(raw),
        }

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
    if typ=="invoke_capability_until":
        template=args.get("action")
        attempts_dir=_safe_repo_path(args.get("attempts_dir",""))
        result_path=_safe_repo_path(args.get("result_path",""))
        max_attempts=int(args.get("max_attempts") or 0)
        value_key=str(args.get("value_key") or "")
        match_chars=set(str(args.get("match_chars") or "").lower())
        if (
            not isinstance(template,dict) or template.get("type")!="invoke_capability"
            or not isinstance(template.get("args"),dict)
            or max_attempts<1 or max_attempts>64
            or not value_key or not match_chars
        ):
            return {"type":typ,"output_verified":False,"error":"BOUNDED_LOOP_SPEC_INVALID"}
        attempts_dir.mkdir(parents=True,exist_ok=True)
        trace=[]
        matched=False
        selected_uuid=None
        selected_attempt=None

        def subst(v,attempt_json,attempt_png):
            if isinstance(v,str):
                if v=="__ATTEMPT_RESULT_PATH__": return attempt_json
                if v=="__ATTEMPT_SCREENSHOT_PATH__": return attempt_png
                return v
            if isinstance(v,list): return [subst(x,attempt_json,attempt_png) for x in v]
            if isinstance(v,dict): return {k:subst(x,attempt_json,attempt_png) for k,x in v.items()}
            return v

        for attempt in range(1,max_attempts+1):
            attempt_json=str((attempts_dir/(str(attempt)+".json")).relative_to(ROOT))
            attempt_png=str((attempts_dir/(str(attempt)+".png")).relative_to(ROOT))
            rendered=subst(template,attempt_json,attempt_png)
            try:
                result=_invoke_bound_capability(rendered.get("args") or {})
                _verify_action_expectation(rendered,result)
                wrapper=json.loads(_safe_repo_path(attempt_json).read_text(encoding="utf-8"))
                observed=json.loads(str(wrapper.get("observed_text") or ""))
                value=str(observed.get(value_key) or "")
            except Exception as exc:
                return {
                  "type":typ,"output_verified":False,
                  "error":"BOUNDED_LOOP_ATTEMPT_FAILED",
                  "attempt":attempt,"detail":type(exc).__name__+":"+str(exc),
                }
            is_match=bool(value and value[0].lower() in match_chars)
            trace.append({"attempt":attempt,"value":value,"matched":is_match,"result_path":attempt_json})
            if is_match:
                matched=True
                selected_uuid=value
                selected_attempt=attempt
                break

        summary={
          "status":"MATCHED" if matched else "EXHAUSTED",
          "attempts":len(trace),
          "matched":matched,
          "selected_uuid":selected_uuid,
          "selected_attempt":selected_attempt,
        }
        result_path.parent.mkdir(parents=True,exist_ok=True)
        result_path.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        return {
          "type":typ,"output_verified":True,
          **summary,
          "result_path":str(result_path.relative_to(ROOT)),
          "attempts_dir":str(attempts_dir.relative_to(ROOT)),
          "trace":trace,
        }

    if typ=="assert_runtime_bounded_loop_trace":
        attempts_dir=_safe_repo_path(args.get("attempts_dir",""))
        result_path=_safe_repo_path(args.get("result_path",""))
        max_attempts=int(args.get("max_attempts") or 0)
        value_key=str(args.get("value_key") or "")
        match_chars=set(str(args.get("match_chars") or "").lower())
        if not attempts_dir.is_dir() or not result_path.is_file() or max_attempts<1:
            return {"type":typ,"verified":False,"error":"BOUNDED_LOOP_VERIFY_SOURCE_MISSING"}
        try:
            summary=json.loads(result_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"type":typ,"verified":False,"error":"BOUNDED_LOOP_RESULT_INVALID:"+type(exc).__name__}
        failures=[]
        observed=[]
        numeric=[]
        for p in attempts_dir.glob("*.json"):
            if p.stem.isdigit():
                numeric.append((int(p.stem),p))
        numeric.sort()
        if not numeric:
            failures.append("NO_ATTEMPTS")
        indexes=[i for i,_ in numeric]
        if indexes and indexes!=list(range(1,max(indexes)+1)):
            failures.append("ATTEMPT_SEQUENCE_HAS_GAPS")
        if len(numeric)>max_attempts:
            failures.append("MAX_ATTEMPTS_EXCEEDED")
        first_match=None
        for i,p in numeric:
            try:
                wrapper=json.loads(p.read_text(encoding="utf-8"))
                payload=json.loads(str(wrapper.get("observed_text") or ""))
                value=str(payload.get(value_key) or "")
            except Exception:
                failures.append("ATTEMPT_JSON_INVALID:"+str(i))
                continue
            matched=bool(value and value[0].lower() in match_chars)
            observed.append({"attempt":i,"value":value,"matched":matched})
            if matched and first_match is None:
                first_match=(i,value)
        expected_attempts=first_match[0] if first_match else max_attempts
        expected_matched=first_match is not None
        expected_status="MATCHED" if expected_matched else "EXHAUSTED"
        if len(numeric)!=expected_attempts:
            failures.append("STOPPING_POINT_MISMATCH")
        if int(summary.get("attempts") or -1)!=expected_attempts:
            failures.append("RESULT_ATTEMPT_COUNT_MISMATCH")
        if bool(summary.get("matched"))!=expected_matched:
            failures.append("RESULT_MATCHED_MISMATCH")
        if str(summary.get("status") or "")!=expected_status:
            failures.append("RESULT_STATUS_MISMATCH")
        if expected_matched:
            if summary.get("selected_attempt")!=first_match[0]:
                failures.append("SELECTED_ATTEMPT_MISMATCH")
            if str(summary.get("selected_uuid") or "")!=first_match[1]:
                failures.append("SELECTED_UUID_MISMATCH")
        else:
            if summary.get("selected_attempt") is not None or summary.get("selected_uuid") is not None:
                failures.append("EXHAUSTED_SELECTION_NOT_NULL")
        return {
          "type":typ,"verified":not failures,
          "failures":failures,
          "observed_attempts":observed,
          "first_match":first_match,
          "expected_status":expected_status,
          "expected_attempts":expected_attempts,
        }

    if typ=="invoke_capability_fallback":
        primary=args.get("primary_action")
        fallback=args.get("fallback_action")
        primary_condition=args.get("primary_postcondition")
        fallback_condition=args.get("fallback_postcondition")
        decision_path=_safe_repo_path(args.get("decision_path",""))
        if (
            not isinstance(primary,dict) or primary.get("type")!="invoke_capability"
            or not isinstance(fallback,dict) or fallback.get("type")!="invoke_capability"
            or not isinstance(primary_condition,dict)
            or not isinstance(fallback_condition,dict)
        ):
            return {"type":typ,"output_verified":False,"error":"FALLBACK_SPEC_INVALID"}

        def run_nested(action):
            result=_invoke_bound_capability((action.get("args") or {}))
            _verify_action_expectation(action,result)
            return result

        def eval_condition(spec):
            ctype=str(spec.get("type") or "")
            if ctype!="json_observed_text_nonempty_array":
                raise RuntimeError("FALLBACK_POSTCONDITION_UNSUPPORTED:"+ctype)
            path=_safe_repo_path(spec.get("path",""))
            if not path.is_file():
                return {"ok":False,"item_count":0,"error":"POSTCONDITION_PATH_MISSING"}
            try:
                wrapper=json.loads(path.read_text(encoding="utf-8"))
                payload=json.loads(str(wrapper.get("observed_text") or ""))
            except Exception as exc:
                return {"ok":False,"item_count":0,"error":"POSTCONDITION_JSON_INVALID:"+type(exc).__name__}
            ok=isinstance(payload,list) and len(payload)>0
            return {"ok":ok,"item_count":len(payload) if isinstance(payload,list) else 0}

        primary_result=None
        primary_error=None
        try:
            primary_result=run_nested(primary)
            primary_eval=eval_condition(primary_condition)
        except Exception as exc:
            primary_error=type(exc).__name__+":"+str(exc)
            primary_eval={"ok":False,"item_count":0,"error":"PRIMARY_ACTION_FAILED"}

        used_fallback=not bool(primary_eval.get("ok"))
        fallback_result=None
        if used_fallback:
            try:
                fallback_result=run_nested(fallback)
                final_eval=eval_condition(fallback_condition)
            except Exception as exc:
                return {
                  "type":typ,"output_verified":False,
                  "error":"FALLBACK_ACTION_FAILED",
                  "detail":type(exc).__name__+":"+str(exc),
                  "primary_error":primary_error,
                }
            final_result=fallback_result
        else:
            final_eval=primary_eval
            final_result=primary_result

        if not final_eval.get("ok"):
            return {
              "type":typ,"output_verified":False,
              "error":"FALLBACK_POSTCONDITION_FAILED",
              "used_fallback":used_fallback,
              "primary_evaluation":primary_eval,
              "final_evaluation":final_eval,
            }

        primary_url=str((primary.get("args") or {}).get("url") or "")
        fallback_url=str((fallback.get("args") or {}).get("url") or "")
        final_url=str((final_result or {}).get("final_url") or (fallback_url if used_fallback else primary_url))
        decision={
          "primary_url":primary_url,
          "fallback_url":fallback_url,
          "used_fallback":used_fallback,
          "final_url":final_url,
          "item_count":int(final_eval.get("item_count") or 0),
        }
        decision_path.parent.mkdir(parents=True,exist_ok=True)
        decision_path.write_text(json.dumps(decision,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        return {
          "type":typ,"output_verified":True,
          **decision,
          "decision_path":str(decision_path.relative_to(ROOT)),
          "primary_evaluation":primary_eval,
          "final_evaluation":final_eval,
        }

    if typ=="assert_runtime_fallback_decision":
        primary_path=_safe_repo_path(args.get("primary_path",""))
        fallback_path=_safe_repo_path(args.get("fallback_path",""))
        decision_path=_safe_repo_path(args.get("decision_path",""))
        if not primary_path.is_file() or not fallback_path.is_file() or not decision_path.is_file():
            return {"type":typ,"verified":False,"error":"FALLBACK_VERIFY_SOURCE_MISSING"}
        def payload(path):
            wrapper=json.loads(path.read_text(encoding="utf-8"))
            return json.loads(str(wrapper.get("observed_text") or ""))
        try:
            primary_payload=payload(primary_path)
            fallback_payload=payload(fallback_path)
            decision=json.loads(decision_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"type":typ,"verified":False,"error":"FALLBACK_VERIFY_JSON_INVALID:"+type(exc).__name__}
        primary_ok=isinstance(primary_payload,list) and len(primary_payload)>0
        fallback_ok=isinstance(fallback_payload,list) and len(fallback_payload)>0
        expected_fallback=not primary_ok
        expected_count=len(fallback_payload) if expected_fallback and isinstance(fallback_payload,list) else (
            len(primary_payload) if isinstance(primary_payload,list) else 0
        )
        expected_url=str(args.get("fallback_url") if expected_fallback else args.get("primary_url"))
        failures=[]
        if expected_fallback and not fallback_ok:
            failures.append("FALLBACK_NOT_NONEMPTY_ARRAY")
        if bool(decision.get("used_fallback"))!=expected_fallback:
            failures.append("USED_FALLBACK_MISMATCH")
        if str(decision.get("final_url") or "")!=expected_url:
            failures.append("FINAL_URL_MISMATCH")
        if int(decision.get("item_count") or -1)!=expected_count:
            failures.append("ITEM_COUNT_MISMATCH")
        if str(decision.get("primary_url") or "")!=str(args.get("primary_url") or ""):
            failures.append("PRIMARY_URL_MISMATCH")
        if str(decision.get("fallback_url") or "")!=str(args.get("fallback_url") or ""):
            failures.append("FALLBACK_URL_MISMATCH")
        return {
          "type":typ,"verified":not failures,
          "failures":failures,
          "primary_nonempty_array":primary_ok,
          "fallback_nonempty_array":fallback_ok,
          "expected_used_fallback":expected_fallback,
          "expected_item_count":expected_count,
        }

    if typ=="invoke_capability_fanout":
        source=_safe_repo_path(args.get("source_path",""))
        manifest_path=_safe_repo_path(args.get("manifest_path",""))
        if not source.is_file():
            return {"type":typ,"output_verified":False,"error":"FANOUT_SOURCE_MISSING"}
        wrapper=json.loads(source.read_text(encoding="utf-8"))
        items=json.loads(str(wrapper.get("observed_text") or ""))
        if not isinstance(items,list) or len(items)>100 or any(not isinstance(x,dict) for x in items):
            return {"type":typ,"output_verified":False,"error":"FANOUT_SOURCE_INVALID"}

        # Per-item fallback mode: each runtime item owns its primary attempt,
        # semantic validation, fallback, and final record. One failed primary
        # therefore cannot abort unrelated items.
        item_fallback=args.get("item_fallback")
        if item_fallback is not None:
            copy_fields=args.get("copy_fields") or ["id"]
            output_dir_raw=str(args.get("output_dir") or "")
            artifact_field=str(args.get("artifact_field") or "artifact_path")
            used_field=str(args.get("used_fallback_field") or "used_fallback")
            kind_field=str(args.get("artifact_kind_field") or "artifact_kind")
            if (
                not isinstance(item_fallback,dict)
                or not output_dir_raw
                or not isinstance(copy_fields,list) or not copy_fields
                or any(not isinstance(x,str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",x) for x in copy_fields)
                or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",artifact_field)
                or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",used_field)
                or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",kind_field)
            ):
                return {"type":typ,"output_verified":False,"error":"FANOUT_ITEM_FALLBACK_SPEC_INVALID"}
            primary=item_fallback.get("primary_action")
            fallback=item_fallback.get("fallback_action")
            validation=item_fallback.get("primary_validation")
            if (
                not isinstance(primary,dict) or primary.get("type")!="invoke_capability"
                or not isinstance(fallback,dict) or fallback.get("type")!="invoke_capability"
                or not isinstance(validation,dict)
                or validation.get("type")!="decoded_equals_source_field"
            ):
                return {"type":typ,"output_verified":False,"error":"FANOUT_ITEM_FALLBACK_ACTION_INVALID"}
            expected_field=str(validation.get("expected_source_field") or "")
            decoder=str(validation.get("decoder_capability") or "image.code.decode.zbarimg")
            primary_kind=str(item_fallback.get("primary_kind") or "PRIMARY")
            fallback_kind=str(item_fallback.get("fallback_kind") or "FALLBACK")
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",expected_field):
                return {"type":typ,"output_verified":False,"error":"FANOUT_ITEM_FALLBACK_EXPECTED_FIELD_INVALID"}

            output_dir=_safe_repo_path(output_dir_raw)
            attempt_dir=output_dir/".primary_attempts"
            output_dir.mkdir(parents=True,exist_ok=True)
            attempt_dir.mkdir(parents=True,exist_ok=True)

            def subst_item(v,item,item_id,out):
                if isinstance(v,str):
                    if v=="__ITEM_OUTPUT_PATH__":
                        return out
                    if v=="__ITEM_ID__":
                        return item_id
                    m=re.fullmatch(r"__ITEM_FIELD_([A-Za-z_][A-Za-z0-9_]*)__",v)
                    if m:
                        return item.get(m.group(1))
                    return v
                if isinstance(v,list):
                    return [subst_item(x,item,item_id,out) for x in v]
                if isinstance(v,dict):
                    return {k:subst_item(x,item,item_id,out) for k,x in v.items()}
                return v

            def invoke_nested(template,item,item_id,out):
                rendered=subst_item(template,item,item_id,out)
                result=_invoke_bound_capability(rendered.get("args") or {})
                _verify_action_expectation(rendered,result)
                return result

            manifest=[]
            fallback_count=0
            primary_valid_count=0
            for item in items:
                item_id=str(item.get("id"))
                if not item_id:
                    return {"type":typ,"output_verified":False,"error":"FANOUT_ITEM_ID_MISSING"}
                expected=str(item.get(expected_field) or "")
                final_out=str((output_dir/(item_id+".png")).relative_to(ROOT))
                primary_out=str((attempt_dir/(item_id+".png")).relative_to(ROOT))
                primary_valid=False
                primary_error=None
                try:
                    invoke_nested(primary,item,item_id,primary_out)
                    decoded=_invoke_bound_capability({
                      "capability_id":decoder,
                      "argv":["zbarimg","--quiet","--raw",primary_out],
                      "timeout_s":60,
                    })
                    primary_valid=str(decoded.get("stdout") or "").strip()==expected
                except Exception as exc:
                    primary_error=type(exc).__name__+":"+str(exc)
                    primary_valid=False

                if primary_valid:
                    primary_valid_count+=1
                    src=_safe_repo_path(primary_out)
                    dst=_safe_repo_path(final_out)
                    if dst.exists():
                        dst.unlink()
                    src.replace(dst)
                    used_fallback=False
                    kind=primary_kind
                else:
                    fallback_count+=1
                    try:
                        dst=_safe_repo_path(final_out)
                        if dst.exists():
                            dst.unlink()
                        invoke_nested(fallback,item,item_id,final_out)
                        decoded=_invoke_bound_capability({
                          "capability_id":decoder,
                          "argv":["zbarimg","--quiet","--raw",final_out],
                          "timeout_s":60,
                        })
                        if str(decoded.get("stdout") or "").strip()!=expected:
                            return {
                              "type":typ,"output_verified":False,
                              "error":"FANOUT_ITEM_FALLBACK_VALIDATION_FAILED",
                              "id":item_id,
                            }
                    except Exception as exc:
                        return {
                          "type":typ,"output_verified":False,
                          "error":"FANOUT_ITEM_FALLBACK_FAILED",
                          "id":item_id,
                          "detail":type(exc).__name__+":"+str(exc),
                          "primary_error":primary_error,
                        }
                    used_fallback=True
                    kind=fallback_kind

                rec={field:item.get(field) for field in copy_fields}
                rec[used_field]=used_fallback
                rec[kind_field]=kind
                rec[artifact_field]=final_out
                manifest.append(rec)

            manifest_path.parent.mkdir(parents=True,exist_ok=True)
            manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
            return {
              "type":typ,"output_verified":True,
              "item_count":len(manifest),
              "fallback_count":fallback_count,
              "primary_valid_count":primary_valid_count,
              "manifest_path":str(manifest_path.relative_to(ROOT)),
            }

        # Generic mode: execute an arbitrary bounded list of already-verified
        # capability action templates for every runtime-discovered item.
        item_actions=args.get("item_actions")
        if item_actions is not None:
            if (
                not isinstance(item_actions,list) or not item_actions
                or len(item_actions)>8
                or any(not isinstance(x,dict) for x in item_actions)
            ):
                return {"type":typ,"output_verified":False,"error":"FANOUT_ITEM_ACTIONS_INVALID"}
            copy_fields=args.get("copy_fields") or ["id"]
            if (
                not isinstance(copy_fields,list) or not copy_fields
                or len(copy_fields)>32
                or any(not isinstance(x,str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",x) for x in copy_fields)
            ):
                return {"type":typ,"output_verified":False,"error":"FANOUT_COPY_FIELDS_INVALID"}
            manifest=[]
            for item in items:
                item_id=str(item.get("id"))
                if not item_id:
                    return {"type":typ,"output_verified":False,"error":"FANOUT_ITEM_ID_MISSING"}
                rec={field:item.get(field) for field in copy_fields}
                for spec in item_actions:
                    artifact_field=str(spec.get("artifact_field") or "")
                    output_dir_raw=str(spec.get("output_dir") or "")
                    extension=str(spec.get("extension") or ".png")
                    template=spec.get("action")
                    if (
                        not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",artifact_field)
                        or not output_dir_raw
                        or not re.fullmatch(r"\.[A-Za-z0-9]{1,10}",extension)
                        or not isinstance(template,dict)
                        or template.get("type")!="invoke_capability"
                        or not isinstance(template.get("args"),dict)
                    ):
                        return {"type":typ,"output_verified":False,"error":"FANOUT_ITEM_ACTION_SPEC_INVALID","id":item_id}
                    output_dir=_safe_repo_path(output_dir_raw)
                    output_dir.mkdir(parents=True,exist_ok=True)
                    out=str((output_dir/(item_id+extension)).relative_to(ROOT))
                    def subst(v):
                        if isinstance(v,str):
                            if v=="__ITEM_OUTPUT_PATH__":
                                return out
                            if v=="__ITEM_ID__":
                                return item_id
                            m=re.fullmatch(r"__ITEM_FIELD_([A-Za-z_][A-Za-z0-9_]*)__",v)
                            if m:
                                return item.get(m.group(1))
                            return v
                        if isinstance(v,list):
                            return [subst(x) for x in v]
                        if isinstance(v,dict):
                            return {k:subst(x) for k,x in v.items()}
                        return v
                    rendered=subst(template)
                    result=_invoke_bound_capability(rendered.get("args") or {})
                    try:
                        _verify_action_expectation(rendered,result)
                    except Exception as exc:
                        return {
                          "type":typ,"output_verified":False,
                          "error":"FANOUT_ITEM_ACTION_FAILED",
                          "id":item_id,"artifact_field":artifact_field,
                          "detail":type(exc).__name__+":"+str(exc),
                        }
                    rec[artifact_field]=out
                manifest.append(rec)
            manifest_path.parent.mkdir(parents=True,exist_ok=True)
            manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
            return {
              "type":typ,"output_verified":True,
              "item_count":len(manifest),
              "actions_per_item":len(item_actions),
              "manifest_path":str(manifest_path.relative_to(ROOT)),
            }

        # Legacy conditional mode remains supported for already-verified plans.
        output_dir=_safe_repo_path(args.get("output_dir",""))
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
    if typ=="assert_runtime_per_item_fallback_decodes":
        source=_safe_repo_path(args.get("source_path",""))
        manifest_path=_safe_repo_path(args.get("manifest_path",""))
        if not source.is_file() or not manifest_path.is_file():
            return {"type":typ,"verified":False,"error":"PER_ITEM_FALLBACK_VERIFY_SOURCE_MISSING"}
        try:
            wrapper=json.loads(source.read_text(encoding="utf-8"))
            items=json.loads(str(wrapper.get("observed_text") or ""))
            manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"type":typ,"verified":False,"error":"PER_ITEM_FALLBACK_VERIFY_JSON_INVALID:"+type(exc).__name__}
        expected_field=str(args.get("expected_source_field") or "")
        primary_field=str(args.get("primary_source_field") or "")
        artifact_field=str(args.get("artifact_field") or "artifact_path")
        used_field=str(args.get("used_fallback_field") or "used_fallback")
        kind_field=str(args.get("artifact_kind_field") or "artifact_kind")
        fallback_kind=str(args.get("fallback_kind") or "FALLBACK")
        decoder=str(args.get("decoder_capability") or "image.code.decode.zbarimg")
        if not isinstance(items,list) or not isinstance(manifest,list):
            return {"type":typ,"verified":False,"error":"PER_ITEM_FALLBACK_VERIFY_INVALID"}
        by_id={str(x.get("id")):x for x in manifest if isinstance(x,dict) and "id" in x}
        failures=[]
        if len(items)!=len(manifest) or len(by_id)!=len(manifest):
            failures.append({"error":"CARDINALITY_MISMATCH"})
        for item in items:
            item_id=str(item.get("id"))
            rec=by_id.get(item_id)
            if rec is None:
                failures.append({"id":item_id,"error":"MANIFEST_RECORD_MISSING"})
                continue
            expected=str(item.get(expected_field) or "")
            primary_value=str(item.get(primary_field) or "")
            if primary_value==expected:
                failures.append({"id":item_id,"error":"PRIMARY_WAS_EXPECTED_TO_FAIL_VALIDATION"})
            if rec.get(expected_field)!=item.get(expected_field) or rec.get(primary_field)!=item.get(primary_field):
                failures.append({"id":item_id,"error":"MANIFEST_SOURCE_FIELD_MISMATCH"})
            if rec.get(used_field) is not True:
                failures.append({"id":item_id,"error":"FALLBACK_FLAG_FALSE"})
            if str(rec.get(kind_field) or "")!=fallback_kind:
                failures.append({"id":item_id,"error":"FALLBACK_KIND_MISMATCH"})
            path=str(rec.get(artifact_field) or "")
            if not path:
                failures.append({"id":item_id,"error":"FINAL_ARTIFACT_PATH_MISSING"})
                continue
            try:
                decoded=_invoke_bound_capability({
                  "capability_id":decoder,
                  "argv":["zbarimg","--quiet","--raw",path],
                  "timeout_s":60,
                })
            except Exception as exc:
                failures.append({"id":item_id,"error":"FINAL_DECODE_FAILED","detail":type(exc).__name__})
                continue
            if str(decoded.get("stdout") or "").strip()!=expected:
                failures.append({"id":item_id,"error":"FINAL_DECODE_MISMATCH"})
        return {
          "type":typ,"verified":not failures,
          "source_count":len(items),"manifest_count":len(manifest),
          "failures":failures[:20],
        }

    if typ=="assert_runtime_fanout_artifacts_decode":
        source=_safe_repo_path(args.get("source_path",""))
        manifest_path=_safe_repo_path(args.get("manifest_path",""))
        if not source.is_file() or not manifest_path.is_file():
            return {"type":typ,"verified":False,"error":"FANOUT_VERIFY_SOURCE_MISSING"}
        wrapper=json.loads(source.read_text(encoding="utf-8"))
        items=json.loads(str(wrapper.get("observed_text") or ""))
        manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
        checks=args.get("checks") or []
        copy_fields=args.get("copy_fields") or ["id"]
        decoder=str(args.get("decoder_capability") or "image.code.decode.zbarimg")
        if (
            not isinstance(items,list) or not isinstance(manifest,list)
            or not isinstance(checks,list) or not checks
            or any(not isinstance(x,dict) for x in checks)
        ):
            return {"type":typ,"verified":False,"error":"FANOUT_VERIFY_INVALID"}
        by_id={str(x.get("id")):x for x in manifest if isinstance(x,dict) and "id" in x}
        failures=[]
        if len(items)!=len(manifest) or len(by_id)!=len(manifest):
            failures.append({"error":"CARDINALITY_MISMATCH"})
        for item in items:
            item_id=str(item.get("id"))
            rec=by_id.get(item_id)
            if rec is None:
                failures.append({"id":item_id,"error":"MANIFEST_RECORD_MISSING"})
                continue
            for field in copy_fields:
                if rec.get(field)!=item.get(field):
                    failures.append({"id":item_id,"error":"COPIED_FIELD_MISMATCH","field":field})
            for check in checks:
                source_field=str(check.get("source_field") or "")
                artifact_field=str(check.get("artifact_field") or "")
                expected=str(item.get(source_field) or "")
                path=str(rec.get(artifact_field) or "")
                if not expected or not path:
                    failures.append({"id":item_id,"error":"ARTIFACT_CHECK_INPUT_MISSING","artifact_field":artifact_field})
                    continue
                decoded=_invoke_bound_capability({
                  "capability_id":decoder,
                  "argv":["zbarimg","--quiet","--raw",path],
                  "timeout_s":60,
                })
                if str(decoded.get("stdout") or "").strip()!=expected:
                    failures.append({
                      "id":item_id,"error":"DECODE_MISMATCH",
                      "artifact_field":artifact_field,"source_field":source_field,
                    })
        return {
          "type":typ,"verified":not failures,
          "source_count":len(items),"manifest_count":len(manifest),
          "checks_per_item":len(checks),"failures":failures[:20],
        }
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
    if typ=="derive_grouped_records":
        dimension_path=_safe_repo_path(args.get("dimension_path",""))
        fact_path=_safe_repo_path(args.get("fact_path",""))
        output_path=_safe_repo_path(args.get("output_path",""))
        dimension_key=str(args.get("dimension_key") or "")
        fact_key=str(args.get("fact_key") or "")
        output_id_field=str(args.get("output_id_field") or "")
        copy_fields=list(args.get("copy_fields") or [])
        metrics=list(args.get("metrics") or [])
        derived=list(args.get("derived") or [])
        field_re=r"^[A-Za-z_][A-Za-z0-9_]*$"
        if (
            not dimension_path.is_file() or not fact_path.is_file()
            or not dimension_key or not fact_key or not output_id_field
            or not re.fullmatch(field_re,output_id_field)
            or any(not isinstance(x,str) or not re.fullmatch(field_re,x) for x in copy_fields)
            or any(not isinstance(x,dict) for x in metrics+derived)
        ):
            return {"type":typ,"output_verified":False,"error":"GROUP_DERIVE_SPEC_INVALID"}

        def observed_array(path):
            wrapper=json.loads(path.read_text(encoding="utf-8"))
            data=json.loads(str(wrapper.get("observed_text") or ""))
            if not isinstance(data,list) or any(not isinstance(x,dict) for x in data):
                raise RuntimeError("GROUP_DERIVE_SOURCE_NOT_OBJECT_ARRAY")
            return data

        try:
            dimensions=observed_array(dimension_path)
            facts=observed_array(fact_path)
        except Exception as exc:
            return {"type":typ,"output_verified":False,"error":"GROUP_DERIVE_SOURCE_INVALID:"+type(exc).__name__+":"+str(exc)}

        dim_index={}
        groups={}
        for row in dimensions:
            if dimension_key not in row:
                return {"type":typ,"output_verified":False,"error":"GROUP_DERIVE_DIMENSION_KEY_MISSING"}
            token=json.dumps(row.get(dimension_key),sort_keys=True)
            if token in dim_index:
                return {"type":typ,"output_verified":False,"error":"GROUP_DERIVE_DIMENSION_KEY_DUPLICATE","key":row.get(dimension_key)}
            dim_index[token]=row
            groups[token]=[]

        unmatched=[]
        for fact in facts:
            if fact_key not in fact:
                return {"type":typ,"output_verified":False,"error":"GROUP_DERIVE_FACT_KEY_MISSING"}
            token=json.dumps(fact.get(fact_key),sort_keys=True)
            if token not in groups:
                unmatched.append(fact.get(fact_key))
                continue
            groups[token].append(fact)
        if unmatched:
            return {"type":typ,"output_verified":False,"error":"GROUP_DERIVE_UNMATCHED_FACTS","keys":unmatched[:20]}

        def metric_value(spec,related):
            name=str(spec.get("name") or "")
            op=str(spec.get("op") or "")
            if not re.fullmatch(field_re,name):
                raise RuntimeError("GROUP_DERIVE_METRIC_NAME_INVALID")
            if op=="count":
                return len(related)
            if op=="count_where":
                where=spec.get("where") or {}
                if not isinstance(where,dict) or not where:
                    raise RuntimeError("GROUP_DERIVE_WHERE_INVALID")
                return sum(1 for row in related if all(row.get(str(k))==v for k,v in where.items()))
            if op=="sum":
                field=str(spec.get("field") or "")
                if not re.fullmatch(field_re,field):
                    raise RuntimeError("GROUP_DERIVE_SUM_FIELD_INVALID")
                total=0
                for row in related:
                    if field not in row:
                        raise RuntimeError("GROUP_DERIVE_SUM_FIELD_MISSING:"+field)
                    value=row[field]
                    if isinstance(value,bool) or not isinstance(value,(int,float)):
                        raise RuntimeError("GROUP_DERIVE_SUM_VALUE_NONNUMERIC:"+field)
                    total+=value
                return total
            raise RuntimeError("GROUP_DERIVE_METRIC_OP_UNSUPPORTED:"+op)

        summary=[]
        try:
            for dim in dimensions:
                token=json.dumps(dim.get(dimension_key),sort_keys=True)
                rec={output_id_field:dim.get(dimension_key)}
                for field in copy_fields:
                    if field not in dim:
                        raise RuntimeError("GROUP_DERIVE_COPY_FIELD_MISSING:"+field)
                    rec[field]=dim[field]
                for spec in metrics:
                    rec[str(spec.get("name"))]=metric_value(spec,groups[token])
                for spec in derived:
                    name=str(spec.get("name") or "")
                    op=str(spec.get("op") or "")
                    if not re.fullmatch(field_re,name):
                        raise RuntimeError("GROUP_DERIVE_DERIVED_NAME_INVALID")
                    if op!="divide":
                        raise RuntimeError("GROUP_DERIVE_DERIVED_OP_UNSUPPORTED:"+op)
                    numerator=str(spec.get("numerator") or "")
                    denominator=str(spec.get("denominator") or "")
                    if numerator not in rec or denominator not in rec:
                        raise RuntimeError("GROUP_DERIVE_DERIVED_INPUT_MISSING")
                    den=rec[denominator]
                    if not isinstance(den,(int,float)) or den==0:
                        raise RuntimeError("GROUP_DERIVE_DIVIDE_BY_ZERO_OR_NONNUMERIC")
                    num=rec[numerator]
                    if not isinstance(num,(int,float)):
                        raise RuntimeError("GROUP_DERIVE_NUMERATOR_NONNUMERIC")
                    rec[name]=num/den
                summary.append(rec)
        except Exception as exc:
            return {"type":typ,"output_verified":False,"error":type(exc).__name__+":"+str(exc)}

        output_path.parent.mkdir(parents=True,exist_ok=True)
        output_path.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        return {
          "type":typ,"output_verified":True,
          "dimension_count":len(dimensions),"fact_count":len(facts),
          "summary_count":len(summary),
          "output_path":str(output_path.relative_to(ROOT)),
        }

    if typ=="assert_grouped_derived_records":
        dimension_path=_safe_repo_path(args.get("dimension_path",""))
        fact_path=_safe_repo_path(args.get("fact_path",""))
        summary_path=_safe_repo_path(args.get("summary_path",""))
        dimension_key=str(args.get("dimension_key") or "")
        fact_key=str(args.get("fact_key") or "")
        output_id_field=str(args.get("output_id_field") or "")
        copy_fields=list(args.get("copy_fields") or [])
        metrics=list(args.get("metrics") or [])
        derived=list(args.get("derived") or [])
        if not dimension_path.is_file() or not fact_path.is_file() or not summary_path.is_file():
            return {"type":typ,"verified":False,"error":"GROUP_DERIVE_VERIFY_SOURCE_MISSING"}
        try:
            dw=json.loads(dimension_path.read_text(encoding="utf-8"))
            fw=json.loads(fact_path.read_text(encoding="utf-8"))
            dimensions=json.loads(str(dw.get("observed_text") or ""))
            facts=json.loads(str(fw.get("observed_text") or ""))
            summary=json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"type":typ,"verified":False,"error":"GROUP_DERIVE_VERIFY_JSON_INVALID:"+type(exc).__name__}
        if not isinstance(dimensions,list) or not isinstance(facts,list) or not isinstance(summary,list):
            return {"type":typ,"verified":False,"error":"GROUP_DERIVE_VERIFY_NOT_ARRAY"}
        failures=[]
        by_id={}
        for rec in summary:
            if not isinstance(rec,dict) or output_id_field not in rec:
                failures.append("SUMMARY_RECORD_INVALID")
                continue
            token=json.dumps(rec.get(output_id_field),sort_keys=True)
            if token in by_id:
                failures.append("SUMMARY_DUPLICATE_ID")
            by_id[token]=rec
        if len(summary)!=len(dimensions):
            failures.append("SUMMARY_CARDINALITY_MISMATCH")
        groups={}
        for dim in dimensions:
            if not isinstance(dim,dict) or dimension_key not in dim:
                failures.append("DIMENSION_KEY_MISSING")
                continue
            groups[json.dumps(dim.get(dimension_key),sort_keys=True)]=[]
        for fact in facts:
            if not isinstance(fact,dict) or fact_key not in fact:
                failures.append("FACT_KEY_MISSING")
                continue
            token=json.dumps(fact.get(fact_key),sort_keys=True)
            if token not in groups:
                failures.append("UNMATCHED_FACT")
                continue
            groups[token].append(fact)
        for dim in dimensions:
            if not isinstance(dim,dict) or dimension_key not in dim:
                continue
            token=json.dumps(dim.get(dimension_key),sort_keys=True)
            rec=by_id.get(token)
            if rec is None:
                failures.append("SUMMARY_RECORD_MISSING")
                continue
            for field in copy_fields:
                if rec.get(field)!=dim.get(field):
                    failures.append("COPY_FIELD_MISMATCH:"+field)
            expected={}
            for spec in metrics:
                name=str(spec.get("name") or "")
                op=str(spec.get("op") or "")
                related=groups.get(token,[])
                if op=="count":
                    expected[name]=len(related)
                elif op=="count_where":
                    where=spec.get("where") or {}
                    expected[name]=sum(1 for row in related if all(row.get(str(k))==v for k,v in where.items()))
                elif op=="sum":
                    field=str(spec.get("field") or "")
                    values=[]
                    invalid=False
                    for row in related:
                        if field not in row:
                            failures.append("SUM_FIELD_MISSING:"+field)
                            invalid=True
                            break
                        value=row[field]
                        if isinstance(value,bool) or not isinstance(value,(int,float)):
                            failures.append("SUM_VALUE_NONNUMERIC:"+field)
                            invalid=True
                            break
                        values.append(value)
                    if not invalid:
                        expected[name]=sum(values)
                else:
                    failures.append("METRIC_OP_UNSUPPORTED:"+op)
            for spec in derived:
                name=str(spec.get("name") or "")
                if str(spec.get("op") or "")!="divide":
                    failures.append("DERIVED_OP_UNSUPPORTED")
                    continue
                num=expected.get(str(spec.get("numerator") or ""),rec.get(str(spec.get("numerator") or "")))
                den=expected.get(str(spec.get("denominator") or ""),rec.get(str(spec.get("denominator") or "")))
                if not isinstance(num,(int,float)) or not isinstance(den,(int,float)) or den==0:
                    failures.append("DERIVED_INPUT_INVALID")
                    continue
                expected[name]=num/den
            for name,value in expected.items():
                if rec.get(name)!=value:
                    failures.append("DERIVED_VALUE_MISMATCH:"+name)
        return {
          "type":typ,"verified":not failures,
          "dimension_count":len(dimensions),"fact_count":len(facts),"summary_count":len(summary),
          "failures":failures[:40],
        }

    if typ=="select_ranked_record":
        source_path=_safe_repo_path(args.get("source_path",""))
        output_path=_safe_repo_path(args.get("output_path",""))
        order_by=list(args.get("order_by") or [])
        output_fields=list(args.get("output_fields") or [])
        try:
            limit=int(args.get("limit") or 1)
        except Exception:
            limit=0
        if not source_path.is_file() or not order_by or not output_fields or limit<1 or limit>1000:
            return {"type":typ,"output_verified":False,"error":"RANK_SELECT_SPEC_INVALID"}
        try:
            rows=json.loads(source_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"type":typ,"output_verified":False,"error":"RANK_SELECT_SOURCE_INVALID:"+type(exc).__name__}
        if not isinstance(rows,list) or not rows or any(not isinstance(x,dict) for x in rows):
            return {"type":typ,"output_verified":False,"error":"RANK_SELECT_SOURCE_NOT_OBJECT_ARRAY"}
        if limit>len(rows):
            return {"type":typ,"output_verified":False,"error":"RANK_SELECT_LIMIT_EXCEEDS_SOURCE","limit":limit,"source_count":len(rows)}
        def better(candidate,current):
            for spec in order_by:
                field=str(spec.get("field") or "")
                direction=str(spec.get("direction") or "").lower()
                if field not in candidate or field not in current or direction not in {"asc","desc"}:
                    raise RuntimeError("RANK_SELECT_ORDER_INVALID")
                a,b=candidate[field],current[field]
                if a==b:
                    continue
                try:
                    return a>b if direction=="desc" else a<b
                except Exception as exc:
                    raise RuntimeError("RANK_SELECT_VALUES_NOT_COMPARABLE:"+field) from exc
            return False
        try:
            ranked=[]
            for row in rows:
                inserted=False
                for idx,current in enumerate(ranked):
                    if better(row,current):
                        ranked.insert(idx,row)
                        inserted=True
                        break
                if not inserted:
                    ranked.append(row)
            selected_rows=ranked[:limit]
            projected=[{field:row[field] for field in output_fields} for row in selected_rows]
            payload=projected[0] if limit==1 else projected
        except Exception as exc:
            return {"type":typ,"output_verified":False,"error":type(exc).__name__+":"+str(exc)}
        output_path.parent.mkdir(parents=True,exist_ok=True)
        output_path.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        result={"type":typ,"output_verified":True,"source_count":len(rows),"limit":limit,"output_path":str(output_path.relative_to(ROOT))}
        if limit==1:
            result["record"]=payload
        else:
            result["records"]=payload
        return result

    if typ=="assert_ranked_record":
        source_path=_safe_repo_path(args.get("source_path",""))
        selected_path=_safe_repo_path(args.get("selected_path",""))
        order_by=list(args.get("order_by") or [])
        output_fields=list(args.get("output_fields") or [])
        try:
            limit=int(args.get("limit") or 1)
        except Exception:
            limit=0
        if not source_path.is_file() or not selected_path.is_file() or not order_by or not output_fields or limit<1 or limit>1000:
            return {"type":typ,"verified":False,"error":"RANK_VERIFY_SPEC_INVALID"}
        try:
            rows=json.loads(source_path.read_text(encoding="utf-8"))
            selected=json.loads(selected_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"type":typ,"verified":False,"error":"RANK_VERIFY_JSON_INVALID:"+type(exc).__name__}
        expected_shape=dict if limit==1 else list
        if not isinstance(rows,list) or not rows or not isinstance(selected,expected_shape):
            return {"type":typ,"verified":False,"error":"RANK_VERIFY_SHAPE_INVALID"}
        if limit>len(rows):
            return {"type":typ,"verified":False,"error":"RANK_VERIFY_LIMIT_EXCEEDS_SOURCE"}
        def precedes(candidate,current):
            for spec in order_by:
                field=str(spec.get("field") or "")
                direction=str(spec.get("direction") or "").lower()
                if field not in candidate or field not in current or direction not in {"asc","desc"}:
                    raise RuntimeError("RANK_VERIFY_ORDER_INVALID")
                a,b=candidate[field],current[field]
                if a==b:
                    continue
                try:
                    return a>b if direction=="desc" else a<b
                except Exception as exc:
                    raise RuntimeError("RANK_VERIFY_VALUES_NOT_COMPARABLE:"+field) from exc
            return False
        try:
            ranked=[]
            for row in rows:
                inserted=False
                for idx,current in enumerate(ranked):
                    if precedes(row,current):
                        ranked.insert(idx,row)
                        inserted=True
                        break
                if not inserted:
                    ranked.append(row)
            projected=[{field:row[field] for field in output_fields} for row in ranked[:limit]]
            expected=projected[0] if limit==1 else projected
        except Exception as exc:
            return {"type":typ,"verified":False,"error":type(exc).__name__+":"+str(exc)}
        return {
          "type":typ,"verified":selected==expected,
          "source_count":len(rows),"limit":limit,"expected":expected,"observed":selected,
        }

    if typ=="aggregate_runtime_json_arrays":
        dimension_path=_safe_repo_path(args.get("dimension_path",""))
        fact_path=_safe_repo_path(args.get("fact_path",""))
        output_path=_safe_repo_path(args.get("output_path",""))
        dimension_key=str(args.get("dimension_key") or "")
        fact_key=str(args.get("fact_key") or "")
        output_id_field=str(args.get("output_id_field") or "")
        count_field=str(args.get("count_field") or "")
        copy_fields=list(args.get("copy_fields") or [])
        if (
            not dimension_path.is_file() or not fact_path.is_file()
            or not dimension_key or not fact_key or not output_id_field or not count_field
            or any(not isinstance(x,str) for x in copy_fields)
        ):
            return {"type":typ,"output_verified":False,"error":"RUNTIME_REDUCE_SPEC_INVALID"}

        def observed_array(path):
            wrapper=json.loads(path.read_text(encoding="utf-8"))
            data=json.loads(str(wrapper.get("observed_text") or ""))
            if not isinstance(data,list) or any(not isinstance(x,dict) for x in data):
                raise RuntimeError("RUNTIME_REDUCE_SOURCE_NOT_OBJECT_ARRAY")
            return data

        try:
            dimensions=observed_array(dimension_path)
            facts=observed_array(fact_path)
        except Exception as exc:
            return {"type":typ,"output_verified":False,"error":"RUNTIME_REDUCE_SOURCE_INVALID:"+type(exc).__name__+":"+str(exc)}

        index={}
        counts={}
        for row in dimensions:
            key=row.get(dimension_key)
            if key is None:
                return {"type":typ,"output_verified":False,"error":"RUNTIME_REDUCE_DIMENSION_KEY_MISSING"}
            token=json.dumps(key,sort_keys=True)
            if token in index:
                return {"type":typ,"output_verified":False,"error":"RUNTIME_REDUCE_DIMENSION_KEY_DUPLICATE","key":key}
            index[token]=row
            counts[token]=0

        unmatched=[]
        for row in facts:
            if fact_key not in row:
                return {"type":typ,"output_verified":False,"error":"RUNTIME_REDUCE_FACT_KEY_MISSING"}
            token=json.dumps(row.get(fact_key),sort_keys=True)
            if token not in counts:
                unmatched.append(row.get(fact_key))
                continue
            counts[token]+=1
        if unmatched:
            return {"type":typ,"output_verified":False,"error":"RUNTIME_REDUCE_UNMATCHED_FACTS","keys":unmatched[:20]}

        summary=[]
        for row in dimensions:
            token=json.dumps(row.get(dimension_key),sort_keys=True)
            rec={output_id_field:row.get(dimension_key)}
            for field in copy_fields:
                if field not in row:
                    return {"type":typ,"output_verified":False,"error":"RUNTIME_REDUCE_COPY_FIELD_MISSING","field":field}
                rec[field]=row[field]
            rec[count_field]=counts[token]
            summary.append(rec)

        if sum(counts.values())!=len(facts):
            return {"type":typ,"output_verified":False,"error":"RUNTIME_REDUCE_COUNT_SUM_MISMATCH"}
        output_path.parent.mkdir(parents=True,exist_ok=True)
        output_path.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        return {
          "type":typ,"output_verified":True,
          "dimension_count":len(dimensions),"fact_count":len(facts),
          "summary_count":len(summary),"count_sum":sum(counts.values()),
          "output_path":str(output_path.relative_to(ROOT)),
        }

    if typ=="assert_runtime_json_aggregate":
        dimension_path=_safe_repo_path(args.get("dimension_path",""))
        fact_path=_safe_repo_path(args.get("fact_path",""))
        summary_path=_safe_repo_path(args.get("summary_path",""))
        dimension_key=str(args.get("dimension_key") or "")
        fact_key=str(args.get("fact_key") or "")
        output_id_field=str(args.get("output_id_field") or "")
        count_field=str(args.get("count_field") or "")
        copy_fields=list(args.get("copy_fields") or [])
        if not dimension_path.is_file() or not fact_path.is_file() or not summary_path.is_file():
            return {"type":typ,"verified":False,"error":"RUNTIME_REDUCE_VERIFY_SOURCE_MISSING"}
        try:
            dw=json.loads(dimension_path.read_text(encoding="utf-8"))
            fw=json.loads(fact_path.read_text(encoding="utf-8"))
            dimensions=json.loads(str(dw.get("observed_text") or ""))
            facts=json.loads(str(fw.get("observed_text") or ""))
            summary=json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"type":typ,"verified":False,"error":"RUNTIME_REDUCE_VERIFY_JSON_INVALID:"+type(exc).__name__}
        failures=[]
        if not isinstance(dimensions,list) or not isinstance(facts,list) or not isinstance(summary,list):
            return {"type":typ,"verified":False,"error":"RUNTIME_REDUCE_VERIFY_NOT_ARRAY"}
        by_id={}
        for rec in summary:
            if not isinstance(rec,dict) or output_id_field not in rec:
                failures.append("SUMMARY_RECORD_INVALID")
                continue
            token=json.dumps(rec.get(output_id_field),sort_keys=True)
            if token in by_id:
                failures.append("SUMMARY_DUPLICATE_ID")
            by_id[token]=rec
        if len(summary)!=len(dimensions):
            failures.append("SUMMARY_CARDINALITY_MISMATCH")
        fact_counts={}
        for fact in facts:
            if not isinstance(fact,dict) or fact_key not in fact:
                failures.append("FACT_KEY_MISSING")
                continue
            token=json.dumps(fact.get(fact_key),sort_keys=True)
            fact_counts[token]=fact_counts.get(token,0)+1
        total=0
        for dim in dimensions:
            if not isinstance(dim,dict) or dimension_key not in dim:
                failures.append("DIMENSION_KEY_MISSING")
                continue
            token=json.dumps(dim.get(dimension_key),sort_keys=True)
            rec=by_id.get(token)
            if rec is None:
                failures.append("SUMMARY_RECORD_MISSING")
                continue
            for field in copy_fields:
                if rec.get(field)!=dim.get(field):
                    failures.append("COPY_FIELD_MISMATCH:"+field)
            expected=fact_counts.get(token,0)
            if rec.get(count_field)!=expected:
                failures.append("COUNT_MISMATCH")
            total+=expected
        if total!=len(facts):
            failures.append("COUNT_SUM_MISMATCH")
        if any(token not in {json.dumps(d.get(dimension_key),sort_keys=True) for d in dimensions if isinstance(d,dict)} for token in fact_counts):
            failures.append("UNMATCHED_FACTS")
        return {
          "type":typ,"verified":not failures,
          "dimension_count":len(dimensions),"fact_count":len(facts),
          "summary_count":len(summary),"count_sum":total,
          "failures":failures[:30],
        }

    if typ=="join_runtime_json_arrays":
        left_path=_safe_repo_path(args.get("left_path",""))
        right_path=_safe_repo_path(args.get("right_path",""))
        output_path=_safe_repo_path(args.get("output_path",""))
        left_key=str(args.get("left_key") or "")
        right_key=str(args.get("right_key") or "")
        left_entity=str(args.get("left_entity") or "left")
        right_entity=str(args.get("right_entity") or "right")
        output_fields=list(args.get("output_fields") or [])
        if (
            not left_path.is_file() or not right_path.is_file()
            or not left_key or not right_key
            or not output_fields
            or any(not isinstance(x,str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",x) for x in output_fields)
        ):
            return {"type":typ,"output_verified":False,"error":"RUNTIME_JOIN_SPEC_INVALID"}

        def observed_array(path):
            wrapper=json.loads(path.read_text(encoding="utf-8"))
            data=json.loads(str(wrapper.get("observed_text") or ""))
            if not isinstance(data,list) or any(not isinstance(x,dict) for x in data):
                raise RuntimeError("RUNTIME_JOIN_SOURCE_NOT_OBJECT_ARRAY")
            return data

        try:
            left=observed_array(left_path)
            right=observed_array(right_path)
        except Exception as exc:
            return {"type":typ,"output_verified":False,"error":"RUNTIME_JOIN_SOURCE_INVALID:"+type(exc).__name__+":"+str(exc)}

        index={}
        for row in left:
            key=row.get(left_key)
            token=json.dumps(key,sort_keys=True)
            if key is None:
                return {"type":typ,"output_verified":False,"error":"RUNTIME_JOIN_LEFT_KEY_MISSING"}
            if token in index:
                return {"type":typ,"output_verified":False,"error":"RUNTIME_JOIN_LEFT_KEY_NOT_UNIQUE","key":key}
            index[token]=row

        def norm(x):
            return re.sub(r"[^a-z0-9]+","",str(x).lower())

        def value_for(out,left_row,right_row):
            n=norm(out)
            if n==norm(right_entity+" id") or n==norm(right_entity+"_id"):
                if "id" not in right_row:
                    raise KeyError(out)
                return right_row["id"]
            if n==norm(left_entity+" id") or n==norm(left_entity+"_id"):
                # Prefer the observed foreign key when it semantically names
                # the left entity; otherwise use the matched left primary key.
                if norm(right_key)==norm(left_entity+" id"):
                    return right_row[right_key]
                return left_row[left_key]
            candidates=[]
            for side,row in (("left",left_row),("right",right_row)):
                for k,v in row.items():
                    if norm(k)==n:
                        candidates.append((side,k,v))
            if len(candidates)!=1:
                raise KeyError(out)
            return candidates[0][2]

        joined=[]
        unmatched=[]
        try:
            for right_row in right:
                if right_key not in right_row:
                    raise RuntimeError("RUNTIME_JOIN_RIGHT_KEY_MISSING")
                token=json.dumps(right_row.get(right_key),sort_keys=True)
                left_row=index.get(token)
                if left_row is None:
                    unmatched.append(right_row.get(right_key))
                    continue
                joined.append({field:value_for(field,left_row,right_row) for field in output_fields})
        except Exception as exc:
            return {"type":typ,"output_verified":False,"error":"RUNTIME_JOIN_PROJECTION_FAILED:"+type(exc).__name__+":"+str(exc)}
        if unmatched:
            return {"type":typ,"output_verified":False,"error":"RUNTIME_JOIN_UNMATCHED_RIGHT","unmatched":unmatched[:20]}
        if len(joined)!=len(right):
            return {"type":typ,"output_verified":False,"error":"RUNTIME_JOIN_CARDINALITY_MISMATCH"}

        output_path.parent.mkdir(parents=True,exist_ok=True)
        output_path.write_text(json.dumps(joined,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        raw=output_path.read_bytes()
        return {
          "type":typ,"output_verified":True,
          "left_count":len(left),"right_count":len(right),"joined_count":len(joined),
          "output_path":str(output_path.relative_to(ROOT)),
          "output_sha256":hashlib.sha256(raw).hexdigest(),
          "left_key":left_key,"right_key":right_key,
          "output_fields":output_fields,
        }

    if typ=="assert_runtime_json_join":
        left_path=_safe_repo_path(args.get("left_path",""))
        right_path=_safe_repo_path(args.get("right_path",""))
        joined_path=_safe_repo_path(args.get("joined_path",""))
        left_key=str(args.get("left_key") or "")
        right_key=str(args.get("right_key") or "")
        left_entity=str(args.get("left_entity") or "left")
        right_entity=str(args.get("right_entity") or "right")
        output_fields=list(args.get("output_fields") or [])
        if not left_path.is_file() or not right_path.is_file() or not joined_path.is_file():
            return {"type":typ,"verified":False,"error":"RUNTIME_JOIN_VERIFY_SOURCE_MISSING"}

        def arr(path,wrapped=False):
            obj=json.loads(path.read_text(encoding="utf-8"))
            if wrapped:
                obj=json.loads(str(obj.get("observed_text") or ""))
            if not isinstance(obj,list) or any(not isinstance(x,dict) for x in obj):
                raise RuntimeError("NOT_OBJECT_ARRAY")
            return obj

        try:
            left=arr(left_path,True)
            right=arr(right_path,True)
            joined=arr(joined_path,False)
        except Exception as exc:
            return {"type":typ,"verified":False,"error":"RUNTIME_JOIN_VERIFY_JSON_INVALID:"+type(exc).__name__}

        failures=[]
        left_index={}
        for row in left:
            if left_key not in row:
                failures.append({"error":"LEFT_KEY_MISSING"})
                continue
            token=json.dumps(row[left_key],sort_keys=True)
            if token in left_index:
                failures.append({"error":"LEFT_KEY_DUPLICATE","key":row[left_key]})
            left_index[token]=row

        if len(joined)!=len(right):
            failures.append({"error":"JOINED_CARDINALITY_MISMATCH","right":len(right),"joined":len(joined)})

        def norm(x):
            return re.sub(r"[^a-z0-9]+","",str(x).lower())

        for idx,right_row in enumerate(right):
            if idx>=len(joined):
                break
            out=joined[idx]
            if set(out.keys())!=set(output_fields):
                failures.append({"index":idx,"error":"OUTPUT_FIELDS_MISMATCH"})
                continue
            if right_key not in right_row:
                failures.append({"index":idx,"error":"RIGHT_KEY_MISSING"})
                continue
            left_row=left_index.get(json.dumps(right_row[right_key],sort_keys=True))
            if left_row is None:
                failures.append({"index":idx,"error":"UNMATCHED_RIGHT"})
                continue
            for field in output_fields:
                n=norm(field)
                if n==norm(right_entity+" id"):
                    expected=right_row.get("id")
                elif n==norm(left_entity+" id"):
                    expected=right_row.get(right_key) if norm(right_key)==norm(left_entity+" id") else left_row.get(left_key)
                else:
                    candidates=[]
                    for row in (left_row,right_row):
                        for k,v in row.items():
                            if norm(k)==n:
                                candidates.append(v)
                    if len(candidates)!=1:
                        failures.append({"index":idx,"field":field,"error":"VERIFY_FIELD_AMBIGUOUS"})
                        continue
                    expected=candidates[0]
                if out.get(field)!=expected:
                    failures.append({"index":idx,"field":field,"error":"VALUE_MISMATCH"})
        return {
          "type":typ,"verified":not failures,
          "left_count":len(left),"right_count":len(right),"joined_count":len(joined),
          "failures":failures[:30],
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
    if typ=="verify_with_independent_pypi_codec":
        fmt=str(args.get("format") or "").strip()
        json_path=str(args.get("json_path") or "").strip()
        binary_path=str(args.get("binary_path") or "").strip()
        producer_project=str(args.get("producer_project") or "").strip()
        producer_capability_id=str(args.get("producer_capability_id") or "").strip()
        if not all((fmt,json_path,binary_path,producer_project,producer_capability_id)):
            return {"type":typ,"verified":False,"error":"INDEPENDENT_CODEC_VERIFIER_ARGS_INCOMPLETE"}
        import independent_pypi_codec_verifier
        evidence=independent_pypi_codec_verifier.verify(
            fmt,json_path,binary_path,producer_project,ROOT
        )
        return {
          "type":typ,
          "verified":bool(evidence.get("verified")),
          "producer_capability_id":producer_capability_id,
          "producer_project":producer_project,
          "verifier_project":evidence.get("verifier_project"),
          "verifier_version":evidence.get("verifier_version"),
          "producer_independent":bool(evidence.get("producer_independent")),
          "dependency_independent":bool(evidence.get("dependency_independent")),
          "format":fmt,
          "module":evidence.get("module"),
          "decode_callable":evidence.get("decode_callable"),
          "decode_kwargs":evidence.get("decode_kwargs"),
          "unwrap_key":evidence.get("unwrap_key"),
          "dependency_closure":evidence.get("dependency_closure"),
          "attempt_count":evidence.get("attempt_count"),
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

def _controller_checkpoint_path(step,mission,plan_sha=None):
    raw_mid=mission.get("mission_id")
    if raw_mid:
        mid=re.sub(r"[^A-Za-z0-9_.-]+","_",str(raw_mid))
    else:
        digest=str(plan_sha or "")
        if len(digest)!=64:
            raise Blocker("ANONYMOUS_CONTROLLER_PLAN_HASH_REQUIRED")
        mid="ANON_"+digest[:16]
    sid=re.sub(r"[^A-Za-z0-9_.-]+","_",str(step.get("id") or step.get("step_id") or "goal"))
    return STATE_DIR/f"{mid}__{sid}__CONTROLLER_CHECKPOINT.json"


def _controller_plan_sha256(actions):
    raw=json.dumps(actions,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _controller_checkpoint_record_valid(record):
    if not isinstance(record,dict):
        return False
    action=record.get("plan")
    result=record.get("result")
    if not isinstance(action,dict) or not isinstance(result,dict):
        return False
    typ=str(action.get("type") or "")
    if typ=="finish":
        return True

    checks=[]
    for path_key,hash_key in (
        ("output_path","output_sha256"),
        ("screenshot_path","screenshot_sha256"),
        ("xlsx_path","xlsx_sha256"),
    ):
        raw=result.get(path_key)
        if isinstance(raw,str) and raw:
            checks.append((raw,result.get(hash_key)))

    # Some adapters report durable paths without hashes. Existence is still
    # required before trusting a checkpointed effect.
    for path_key in ("result_path","manifest_path","decision_path"):
        raw=result.get(path_key)
        if isinstance(raw,str) and raw and not any(x[0]==raw for x in checks):
            checks.append((raw,None))

    if typ=="assert_file_exists":
        raw=(action.get("args") or {}).get("path")
        if isinstance(raw,str) and raw:
            checks.append((raw,result.get("sha256")))

    for raw,expected_hash in checks:
        try:
            p=_safe_repo_path(raw)
        except Exception:
            return False
        if not p.is_file():
            return False
        if isinstance(expected_hash,str) and expected_hash:
            try:
                if sha_file(p)!=expected_hash:
                    return False
            except Exception:
                return False
    return True


def _validated_checkpoint_prefix(completed):
    for index,record in enumerate(completed):
        if not _controller_checkpoint_record_valid(record):
            return completed[:index],index
    return completed,None


def _load_controller_checkpoint(step,mission,actions):
    plan_sha=_controller_plan_sha256(actions)
    path=_controller_checkpoint_path(step,mission,plan_sha=plan_sha)
    if not path.is_file():
        return path,{
          "schema":"PROJECT_BRAIN_CONTROLLER_CHECKPOINT_V1",
          "mission_id":mission.get("mission_id"),
          "step_id":step.get("id") or step.get("step_id") or "goal",
          "plan_sha256":plan_sha,
          "status":"IN_PROGRESS",
          "completed_actions":[],
          "next_action_index":0,
          "resume_count":0,
          "test_interrupt_injected":False,
          "created_at_utc":utc(),
          "updated_at_utc":utc(),
        },False
    data=readj(path)
    if data.get("schema")!="PROJECT_BRAIN_CONTROLLER_CHECKPOINT_V1":
        raise Blocker("CONTROLLER_CHECKPOINT_SCHEMA_INVALID")
    if data.get("plan_sha256")!=plan_sha:
        raise Blocker("CONTROLLER_CHECKPOINT_PLAN_HASH_MISMATCH")
    completed=data.get("completed_actions")
    if not isinstance(completed,list) or len(completed)>len(actions):
        raise Blocker("CONTROLLER_CHECKPOINT_TRACE_INVALID")
    expected=list(range(len(completed)))
    observed=[x.get("cycle") for x in completed if isinstance(x,dict)]
    if observed!=expected:
        raise Blocker("CONTROLLER_CHECKPOINT_SEQUENCE_INVALID")
    valid_prefix,rewound_from=_validated_checkpoint_prefix(completed)
    if rewound_from is not None:
        data["completed_actions"]=valid_prefix
        data["rewind_count"]=int(data.get("rewind_count") or 0)+1
        data["last_rewound_from_action_index"]=rewound_from
        data["last_rewind_reason"]="DURABLE_EFFECT_INVALID_OR_MISSING"
    data["resume_count"]=int(data.get("resume_count") or 0)+1
    data["next_action_index"]=len(data.get("completed_actions") or [])
    data["updated_at_utc"]=utc()
    writej(path,data)
    return path,data,True


def _write_controller_checkpoint(path,data,trace,status="IN_PROGRESS"):
    data=dict(data)
    data["completed_actions"]=trace
    data["next_action_index"]=len(trace)
    data["status"]=status
    data["updated_at_utc"]=utc()
    writej(path,data)
    return data


def _run_model_independent_goal(step, mission, goal):
    actions=_controller_actions(step, mission)
    if actions is None:
        return None
    allowed_types={
      "read_file","list_tree","search_text","http_get","write_json_records","invoke_capability","invoke_capability_by_runtime_value","invoke_capability_fanout","invoke_capability_fallback","invoke_capability_until","verify_with_independent_pypi_codec",
      "project_browser_result_json","join_runtime_json_arrays","assert_runtime_json_join","aggregate_runtime_json_arrays","assert_runtime_json_aggregate","derive_grouped_records","assert_grouped_derived_records","select_ranked_record","assert_ranked_record","assert_hex_prefix_bucket","assert_collection_length_bucket","assert_runtime_selected_code_decodes",
      "assert_text_contains_json_keys","assert_file_exists","assert_json_fields_equal","assert_runtime_fanout_decodes","assert_runtime_fanout_artifacts_decode","assert_runtime_per_item_fallback_decodes","assert_runtime_fallback_decision","assert_runtime_bounded_loop_trace",
      "assert_workflow_audit_supported_by_source","assert_python_source_audit_supported_by_source",
      "assert_python_test_audit_zero","assert_python_test_audit_supported_by_fresh_execution",
      "finish"
    }
    checkpoint_path,checkpoint,resumed=_load_controller_checkpoint(step,mission,actions)
    trace=list(checkpoint.get("completed_actions") or [])
    start_cycle=len(trace)
    for cycle in range(start_cycle,len(actions)):
        raw_action=actions[cycle]
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
        checkpoint=_write_controller_checkpoint(checkpoint_path,checkpoint,trace)
        interrupt_after=step.get("interrupt_after_controller_actions_once")
        if interrupt_after is not None:
            limit=int(interrupt_after)
            if limit<1 or limit>len(actions):
                raise Blocker("CONTROLLER_TEST_INTERRUPT_LIMIT_INVALID")
            if len(trace)==limit and not checkpoint.get("test_interrupt_injected"):
                checkpoint["test_interrupt_injected"]=True
                checkpoint=_write_controller_checkpoint(checkpoint_path,checkpoint,trace)
                raise Blocker("CONTROLLER_CHECKPOINT_TEST_INTERRUPTION")
        if typ=="finish":
            summary=result.get("summary","")
            if not summary.strip():
                raise Blocker("MODEL_INDEPENDENT_CONTROLLER_EMPTY_FINISH")
            checkpoint=_write_controller_checkpoint(checkpoint_path,checkpoint,trace,status="COMPLETE")
            return {
              "adapter":"goal","returncode":0,
              "stdout":summary,
              "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
              "planner_source":None,
              "planner_transport":None,
              "planner_model_last":None,
              "cycles":len(trace),"trace":trace,
              "final_summary":summary,
              "controller_checkpoint":{
                "path":str(checkpoint_path.relative_to(ROOT)),
                "plan_sha256":checkpoint.get("plan_sha256"),
                "resumed":bool(resumed),
                "resume_count":int(checkpoint.get("resume_count") or 0),
                "resumed_from_action_index":start_cycle,
                "rewind_count":int(checkpoint.get("rewind_count") or 0),
                "last_rewound_from_action_index":checkpoint.get("last_rewound_from_action_index"),
              }
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

def _load_auto_capability_acquisition():
    path=pathlib.Path(__file__).resolve().with_name("auto_capability_acquisition.py")
    spec=importlib.util.spec_from_file_location("project_brain_auto_capability_acquisition",path)
    if spec is None or spec.loader is None:
        raise Blocker("AUTO_CAPABILITY_ACQUISITION_LOAD_FAILED")
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

def _classify_plain_goal_gap(text):
    value=str(text or "").strip()
    lower=value.lower()
    if not value:
        return "UNKNOWN"
    if (
        re.match(r"^(?:for\s+every|for\s+each)\b",lower)
        or " at runtime" in lower
        or re.search(r"\botherwise\b",lower)
        or re.search(r"\b(?:repeatedly|retry|retries|attempts?|until)\b",lower)
        or re.match(r"^(?:after\s+each|finish\s+when|continue\s+until)\b",lower)
    ):
        return "CONTROL_OR_FANOUT"
    if re.match(r"^if\b",lower) or re.search(r"\bthen\b",lower):
        return "CONTROL_FLOW"
    if (
        re.match(r"^(?:finally\s+)?independently\b",lower)
        or re.match(r"^(?:verify|reread|reopen|assert|check)\b",lower)
        or re.search(r"\bindependently\s+(?:verify|decode|reread|reopen|check)\b",lower)
    ):
        return "VERIFICATION"
    if (
        "from that result" in lower
        or "using that result" in lower
        or "from the previous result" in lower
        or "from the live result" in lower
        or "using both live results" in lower
        or "from these two live datasets" in lower
        or "from both live datasets" in lower
        or (
            re.search(r"\b(?:join|merge|combine)\b",lower)
            and re.search(r"\b(?:live|result|source|collection|records?)\b",lower)
        )
    ):
        return "CAUSAL_COMPOSITION"
    return "CAPABILITY_CANDIDATE"


def _write_goal_gap_classification(mission, subgoal, gap_class, compile_error):
    mid=str(mission.get("mission_id") or "UNKNOWN")
    path=EVID_DIR/f"{mid}__GOAL_GAP_CLASSIFICATION.json"
    evidence={
      "schema":"PROJECT_BRAIN_GOAL_GAP_CLASSIFICATION_V1",
      "mission_id":mid,
      "subgoal":str(subgoal or ""),
      "gap_class":gap_class,
      "capability_acquisition_allowed":gap_class=="CAPABILITY_CANDIDATE",
      "compile_error":str(compile_error),
      "policy":"ONLY_CAPABILITY_CANDIDATE_MAY_TRIGGER_EXTERNAL_CAPABILITY_ACQUISITION",
      "observed_at_utc":utc(),
    }
    writej(path,evidence)
    return path,evidence


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
            gap_class=_classify_plain_goal_gap(acquisition_goal)
            gap_path,gap_evidence=_write_goal_gap_classification(
                mission,acquisition_goal,gap_class,error_text
            )
            if gap_class!="CAPABILITY_CANDIDATE":
                raise Blocker(
                    "GOAL_ARCHITECTURAL_GAP:"+json.dumps({
                      "gap_class":gap_class,
                      "subgoal":acquisition_goal,
                      "evidence_path":str(gap_path.relative_to(ROOT)),
                      "capability_acquisition_attempted":False,
                    },sort_keys=True)
                ) from e
            mid=str(mission.get("mission_id") or "UNKNOWN")
            ep=EVID_DIR/f"{mid}__PLAIN_GOAL_CAPABILITY_DISCOVERY.json"
            auto=_load_auto_capability_acquisition()

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
        controller_actions=compiled.get("controller_actions")
        if controller_actions is not None:
            if (
                not isinstance(controller_actions,list)
                or not controller_actions
                or not all(isinstance(action,dict) for action in controller_actions)
            ):
                raise Blocker("COMPILED_CONTROLLER_ACTIONS_INVALID")
            derived=dict(step)
            derived["controller_actions"]=controller_actions
            derived["max_controller_actions"]=max(
                int(step.get("max_controller_actions",16)),
                len(controller_actions)
            )
            compiled_result=_run_model_independent_goal(derived,mission,goal)
            if compiled_result is None:
                raise Blocker("COMPILED_CONTROLLER_PLAN_EXECUTION_MISSING")
            compiled_result["planning_mode"]=str(
                compiled.get("compiler_mode") or "COMPILED_CONTROLLER_ACTION_PLAN"
            )
            compiled_result["goal_compilation"]={
              "compiler_mode":compiled.get("compiler_mode"),
              "clauses":compiled.get("clauses"),
              "compiled_parts":compiled.get("compiled_parts"),
            }
            return compiled_result

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
