#!/usr/bin/env python3
"""Pinned APT Python-library probe.

Verifies Ubuntu package metadata, installs the exact package version, discovers
importable Python modules from the package file list, and records bounded
module/class/function signatures. It does not execute a task-specific effect.
"""
from __future__ import annotations
import json,pathlib,re,subprocess,sys

class ProbeFailure(RuntimeError): pass

PKG_RE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9+._-]{0,127}$")

def _run(argv,timeout=30):
    return subprocess.run(argv,text=True,capture_output=True,timeout=timeout)

def _module_candidates(paths):
    mods=[]
    marker="/dist-packages/"
    for raw in paths:
        if marker not in raw:
            continue
        rel=raw.split(marker,1)[1].strip("/")
        if not rel or rel.startswith(("__pycache__/",".")):
            continue
        parts=rel.split("/")
        first=parts[0]
        if first.endswith(".py"):
            name=first[:-3]
            if name and name!="__init__" and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",name):
                mods.append(name)
        elif len(parts)>=2 and parts[1]=="__init__.py" and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",first):
            mods.append(first)
        elif len(parts)>=2 and parts[1].endswith(".py"):
            sub=parts[1][:-3]
            if sub!="__init__" and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",first) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",sub):
                mods.append(first+"."+sub)
    return list(dict.fromkeys(mods))[:40]

def _inspect_module(name):
    code=r'''
import importlib,inspect,json,sys
name=sys.argv[1]
try:
    mod=importlib.import_module(name)
except Exception as exc:
    print(json.dumps({"module":name,"import_ok":False,"error":type(exc).__name__+":"+str(exc)}))
    raise SystemExit(0)
out={"module":name,"import_ok":True,"functions":[],"classes":[]}
for attr in sorted(dir(mod)):
    if attr.startswith("_"):
        continue
    try: obj=getattr(mod,attr)
    except Exception: continue
    if inspect.isfunction(obj) or inspect.isbuiltin(obj):
        try: sig=str(inspect.signature(obj))
        except Exception: sig=None
        out["functions"].append({"name":attr,"signature":sig,"doc":(inspect.getdoc(obj) or "")[:800]})
    elif inspect.isclass(obj) and getattr(obj,"__module__","").startswith(name.split(".")[0]):
        methods=[]
        for mname in sorted(dir(obj)):
            if mname.startswith("_"):
                continue
            try: m=getattr(obj,mname)
            except Exception: continue
            if callable(m):
                try: sig=str(inspect.signature(m))
                except Exception: sig=None
                methods.append({"name":mname,"signature":sig,"doc":(inspect.getdoc(m) or "")[:500]})
        out["classes"].append({"name":attr,"methods":methods[:60],"doc":(inspect.getdoc(obj) or "")[:1000]})
out["functions"]=out["functions"][:80]
out["classes"]=out["classes"][:40]
print(json.dumps(out,sort_keys=True))
'''
    p=_run(["/usr/bin/python3","-c",code,name],timeout=20)
    if p.returncode!=0 or not p.stdout.strip():
        return {"module":name,"import_ok":False,"error":"INTROSPECTION_FAILED:"+p.stderr[-800:]}
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception as exc:
        return {"module":name,"import_ok":False,"error":"INTROSPECTION_JSON_INVALID:"+type(exc).__name__}

def probe(package,version,sha256,root):
    if not sys.platform.startswith("linux"):
        raise ProbeFailure("APT_PLATFORM_REQUIRED")
    if not PKG_RE.fullmatch(package or ""):
        raise ProbeFailure("APT_PACKAGE_INVALID")
    if not version or not re.fullmatch(r"[0-9a-f]{64}",sha256 or ""):
        raise ProbeFailure("APT_METADATA_INCOMPLETE")
    show=_run(["apt-cache","show",f"{package}={version}"])
    if show.returncode!=0:
        raise ProbeFailure("APT_METADATA_NOT_FOUND")
    found=None
    for line in show.stdout.splitlines():
        if line.startswith("SHA256:"):
            found=line.split(":",1)[1].strip().lower(); break
    if found!=sha256.lower():
        raise ProbeFailure("APT_HASH_MISMATCH")
    install=_run(["sudo","apt-get","install","-y","--no-install-recommends",f"{package}={version}"],timeout=240)
    if install.returncode!=0:
        raise ProbeFailure("APT_INSTALL_FAILED:"+install.stderr[-1000:])
    listed=_run(["dpkg","-L",package])
    if listed.returncode!=0:
        raise ProbeFailure("APT_FILE_LIST_FAILED")
    files=[x.strip() for x in listed.stdout.splitlines() if x.strip()]
    modules=_module_candidates(files)
    inspections=[_inspect_module(x) for x in modules]
    return {
      "schema":"PROJECT_BRAIN_APT_PYTHON_LIBRARY_PROBE_V1",
      "package":package,
      "version":version,
      "archive_sha256":sha256.lower(),
      "module_candidates":modules,
      "modules":inspections,
    }

if __name__=="__main__":
    if len(sys.argv)!=5:
        raise SystemExit("usage: apt_python_probe.py PACKAGE VERSION SHA256 OUTPUT_JSON")
    package,version,sha,out=sys.argv[1:]
    result=probe(package,version,sha,pathlib.Path.cwd())
    p=pathlib.Path(out); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,sort_keys=True))
