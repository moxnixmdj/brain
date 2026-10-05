from __future__ import annotations
import base64, json, os, pathlib, shutil, sys
from collections.abc import Mapping
from typing import Any

from canonical.runtime.zero_ambient_namespace_launcher_v1 import (
    canonical_policy,
    policy_sha256,
)

SCHEMA="PROJECT_BRAIN_ROOT3_NAMESPACE_RUN_PLAN_V1"
EFFECT_CLASS="READ_ONLY_DECLARED_QUERY"

ALLOWED_SITES={
 ("canonical/runtime/bound_capabilities/archive_verify_gnu_tar.py",32,"subprocess.run"),
 ("canonical/runtime/bound_capabilities/jq_query.py",41,"subprocess.run"),
 ("canonical/runtime/bound_capabilities/pdf_ocr_tesseract.py",44,"subprocess.run"),
 ("canonical/runtime/bound_capabilities/sqlite_verify_cli.py",66,"subprocess.run"),
 ("canonical/runtime/bound_capabilities/yq_yaml_json.py",21,"subprocess.run"),
}

_CAPTURE_SHIM=r"""
import base64,json,os,subprocess,sys
argv=json.loads(sys.argv[1])
cwd=sys.argv[2] or None
timeout=float(sys.argv[3])
p=subprocess.run(argv,cwd=cwd,text=False,capture_output=True,timeout=timeout)
payload={
 "returncode":p.returncode,
 "stdout_b64":base64.b64encode(p.stdout or b"").decode("ascii"),
 "stderr_b64":base64.b64encode(p.stderr or b"").decode("ascii"),
}
os.write(int(os.environ["PROJECT_BRAIN_BROKER_FD"]),(json.dumps(payload,sort_keys=True,separators=(",",":"))+"\n").encode())
"""

class NamespacePlanDenied(PermissionError):
    pass

def _site(context:Mapping[str,Any])->tuple[str,int,str]:
    c=context.get("callsite") or {}
    return (str(c.get("module_path")),int(c.get("lineno",-1)),str(c.get("process_api")))

def _argv(context:Mapping[str,Any])->list[str]:
    args=context.get("args")
    if not isinstance(args,tuple) or len(args)!=1:
        raise NamespacePlanDenied("EXACT_ONE_COMMAND_ARGUMENT_REQUIRED")
    raw=args[0]
    if not isinstance(raw,(list,tuple)) or not raw:
        raise NamespacePlanDenied("ARGV_LIST_REQUIRED")
    out=[]
    for item in raw:
        if not isinstance(item,(str,os.PathLike)):
            raise NamespacePlanDenied("ARGV_ELEMENT_TYPE_FORBIDDEN")
        out.append(os.fspath(item))
    return out

def _root(argv:list[str],cwd:Any)->pathlib.Path:
    if cwd is not None:
        root=pathlib.Path(os.fspath(cwd)).resolve()
        if not root.is_dir():
            raise NamespacePlanDenied("CWD_MISSING")
        return root
    candidates=[]
    for token in argv[1:]:
        p=pathlib.Path(token)
        if not p.is_absolute():
            continue
        rp=p.resolve()
        if str(rp).startswith(("/usr/","/bin/","/lib/","/lib64/")):
            continue
        candidates.append(rp if rp.is_dir() else rp.parent)
    if not candidates:
        raise NamespacePlanDenied("INPUT_ROOT_UNRESOLVED")
    root=pathlib.Path(os.path.commonpath([str(x) for x in candidates])).resolve()
    if not root.is_dir():
        raise NamespacePlanDenied("INPUT_ROOT_INVALID")
    return root

def _map_token(token:str,root:pathlib.Path)->str:
    p=pathlib.Path(token)
    if not p.is_absolute():
        return token
    rp=p.resolve()
    if str(rp).startswith(("/usr/","/bin/","/lib/","/lib64/")):
        return str(rp)
    try:
        rel=rp.relative_to(root)
    except ValueError as exc:
        raise NamespacePlanDenied("ABSOLUTE_PATH_OUTSIDE_INPUT_ROOT") from exc
    return "/input" if str(rel)=="." else "/input/"+rel.as_posix()

def build(context:Mapping[str,Any])->dict[str,Any]:
    if str(context.get("effect_class"))!=EFFECT_CLASS:
        raise NamespacePlanDenied("WRONG_EFFECT_CLASS")
    if str(context.get("api"))!="subprocess.run":
        raise NamespacePlanDenied("ONLY_SUBPROCESS_RUN_SUPPORTED")
    site=_site(context)
    if site not in ALLOWED_SITES:
        raise NamespacePlanDenied("READONLY_SITE_NOT_ADMITTED:"+repr(site))

    kwargs=dict(context.get("kwargs") or {})
    allowed={"cwd","text","universal_newlines","capture_output","timeout","encoding","errors","check","bufsize","close_fds","shell","env","input","stdin","stdout","stderr"}
    unknown=set(kwargs)-allowed
    if unknown:
        raise NamespacePlanDenied("UNCLASSIFIED_KWARGS:"+",".join(sorted(unknown)))
    if kwargs.get("shell"):
        raise NamespacePlanDenied("SHELL_FORBIDDEN")
    if kwargs.get("env") is not None or kwargs.get("input") is not None:
        raise NamespacePlanDenied("CUSTOM_ENV_OR_INPUT_FORBIDDEN")
    if kwargs.get("stdin") is not None or kwargs.get("stdout") is not None or kwargs.get("stderr") is not None:
        raise NamespacePlanDenied("EXPLICIT_STDIO_FORBIDDEN")
    if kwargs.get("capture_output") is not True:
        raise NamespacePlanDenied("CAPTURE_OUTPUT_REQUIRED")
    if kwargs.get("bufsize") not in (None,-1):
        raise NamespacePlanDenied("BUFSIZE_NONDEFAULT_FORBIDDEN")
    if kwargs.get("close_fds") not in (None,True):
        raise NamespacePlanDenied("CLOSE_FDS_FALSE_FORBIDDEN")

    argv=_argv(context)
    raw_exe=argv[0]
    exe=raw_exe if os.path.isabs(raw_exe) else shutil.which(raw_exe)
    if not exe:
        raise NamespacePlanDenied("EXECUTABLE_NOT_FOUND")
    exe=str(pathlib.Path(exe).resolve())
    if not exe.startswith(("/usr/","/bin/")):
        raise NamespacePlanDenied("EXECUTABLE_OUTSIDE_READONLY_SYSTEM_MOUNTS")

    root=_root(argv,kwargs.get("cwd"))
    mapped=[exe]+[_map_token(x,root) for x in argv[1:]]
    mapped_cwd="/input" if kwargs.get("cwd") is not None else ""

    timeout=float(kwargs.get("timeout") or 60)
    if not (0 < timeout <= 300):
        raise NamespacePlanDenied("TIMEOUT_OUT_OF_RANGE")

    if os.geteuid()==0:
        raise NamespacePlanDenied("ROOT_PARENT_REQUIRES_EXPLICIT_NONROOT_IDENTITY")

    py=shutil.which("python3") or sys.executable
    py=str(pathlib.Path(py).resolve())
    if not py.startswith(("/usr/","/bin/")):
        raise NamespacePlanDenied("PYTHON_OUTSIDE_READONLY_SYSTEM_MOUNTS")

    policy=canonical_policy({
      "argv":[py,"-c",_CAPTURE_SHIM,json.dumps(mapped,separators=(",",":")),mapped_cwd,str(timeout)],
      "input_dir":str(root),
      "env":{},
      "host_uid":os.geteuid(),
      "host_gid":os.getegid(),
      "limits":{
        "pids":32,
        "memory_mb":512,
        "cpu_seconds":min(max(int(timeout),1),300),
        "wallclock_s":min(int(timeout)+5,305),
        "scratch_mb":64,
        "max_file_mb":16,
        "nofile":64,
        "broker_max_bytes":8_000_000,
      },
    })

    return {
      "schema":SCHEMA,
      "effect_class":EFFECT_CLASS,
      "api":"subprocess.run",
      "policy":policy,
      "policy_sha256":policy_sha256(policy),
      "original_argv":argv,
      "text":bool(kwargs.get("text") or kwargs.get("universal_newlines")),
      "encoding":kwargs.get("encoding"),
      "errors":kwargs.get("errors"),
      "check":bool(kwargs.get("check")),
    }
