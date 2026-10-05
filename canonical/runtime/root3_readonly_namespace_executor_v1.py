from __future__ import annotations
import base64, json, os, pathlib, shutil, subprocess, sys
from collections.abc import Mapping
from typing import Any
from canonical.runtime.zero_ambient_namespace_launcher_v1 import run_confined, NamespaceConfinementError

SCHEMA="PROJECT_BRAIN_ROOT3_READONLY_NAMESPACE_EXECUTOR_V1"
ALLOWED_SITES={
 ("canonical/runtime/bound_capabilities/jq_query.py",41,"subprocess.run"),
 ("canonical/runtime/bound_capabilities/yq_yaml_json.py",21,"subprocess.run"),
 ("canonical/runtime/bound_capabilities/sqlite_verify_cli.py",66,"subprocess.run"),
 ("canonical/runtime/bound_capabilities/archive_verify_gnu_tar.py",32,"subprocess.run"),
 ("canonical/runtime/bound_capabilities/pdf_ocr_tesseract.py",44,"subprocess.run"),
}
_SHIM = r'''
import base64,json,os,subprocess,sys
argv=json.loads(sys.argv[1]); cwd=(sys.argv[2] or None); timeout=float(sys.argv[3])
p=subprocess.run(argv,cwd=cwd,text=False,capture_output=True,timeout=timeout)
payload={"returncode":p.returncode,"stdout_b64":base64.b64encode(p.stdout or b"").decode(),"stderr_b64":base64.b64encode(p.stderr or b"").decode()}
raw=(json.dumps(payload,sort_keys=True,separators=(",",":"))+"\n").encode()
fd=int(os.environ["PROJECT_BRAIN_BROKER_FD"]); os.write(fd,raw)
'''

class ReadOnlyNamespaceExecutorError(PermissionError): pass

def _site(ctx: Mapping[str,Any]):
    c=ctx.get("callsite") or {}
    return (str(c.get("module_path")),int(c.get("lineno",-1)),str(c.get("process_api")))

def _original_argv(ctx):
    args=ctx.get("args")
    if not isinstance(args,tuple) or len(args)!=1:
        raise ReadOnlyNamespaceExecutorError("EXACT_ONE_COMMAND_ARGUMENT_REQUIRED")
    raw=args[0]
    if not isinstance(raw,(list,tuple)) or not raw or not all(isinstance(x,(str,os.PathLike)) for x in raw):
        raise ReadOnlyNamespaceExecutorError("ARGV_LIST_REQUIRED")
    return [os.fspath(x) for x in raw]

def _choose_input_root(argv, cwd):
    if cwd:
        p=pathlib.Path(os.fspath(cwd)).resolve()
        if not p.is_dir(): raise ReadOnlyNamespaceExecutorError("CWD_MISSING")
        return p
    candidates=[]
    for a in argv[1:]:
        p=pathlib.Path(a)
        if p.is_absolute() and p.exists() and not str(p).startswith(("/usr/","/bin/","/lib/","/lib64/")):
            candidates.append(p.resolve())
    if not candidates:
        import tempfile
        return pathlib.Path(tempfile.mkdtemp(prefix="brain-readonly-empty-")).resolve()
    parents=[p if p.is_dir() else p.parent for p in candidates]
    common=pathlib.Path(os.path.commonpath([str(p) for p in parents])).resolve()
    if not common.is_dir(): common=common.parent
    return common

def _map_path_token(token, root):
    p=pathlib.Path(token)
    if p.is_absolute():
        rp=p.resolve()
        try: rel=rp.relative_to(root)
        except ValueError:
            return str(rp)
        return "/input" if str(rel)=="." else "/input/"+rel.as_posix()
    return token

def _decode_capture(raw: bytes, *, text: bool, encoding, errors):
    try: rec=json.loads(raw.decode("utf-8").strip())
    except Exception as exc: raise ReadOnlyNamespaceExecutorError("BROKER_CAPTURE_INVALID") from exc
    out=base64.b64decode(rec["stdout_b64"]); err=base64.b64decode(rec["stderr_b64"])
    if text:
        enc=encoding or "utf-8"; er=errors or "strict"
        out=out.decode(enc,errors=er); err=err.decode(enc,errors=er)
    return subprocess.CompletedProcess(args=None,returncode=int(rec["returncode"]),stdout=out,stderr=err)

def execute(context: Mapping[str,Any]):
    if str(context.get("effect_class"))!="READ_ONLY_DECLARED_QUERY":
        raise ReadOnlyNamespaceExecutorError("WRONG_EFFECT_CLASS")
    site=_site(context)
    if site not in ALLOWED_SITES:
        raise ReadOnlyNamespaceExecutorError("READONLY_SITE_NOT_YET_ADMITTED:"+repr(site))
    if str(context.get("api"))!="subprocess.run":
        raise ReadOnlyNamespaceExecutorError("POPEN_STREAMING_NOT_YET_ADMITTED")
    kw=dict(context.get("kwargs") or {})
    if kw.get("shell"): raise ReadOnlyNamespaceExecutorError("SHELL_FORBIDDEN")
    if kw.get("env") is not None or kw.get("input") is not None:
        raise ReadOnlyNamespaceExecutorError("CUSTOM_ENV_OR_STDIN_INPUT_FORBIDDEN")
    if not bool(kw.get("capture_output")):
        raise ReadOnlyNamespaceExecutorError("CAPTURE_OUTPUT_REQUIRED")
    if kw.get("stdin") is not None or kw.get("stdout") is not None or kw.get("stderr") is not None:
        raise ReadOnlyNamespaceExecutorError("EXPLICIT_STDIO_NOT_SUPPORTED")
    argv=_original_argv(context)
    exe=argv[0]
    resolved=shutil.which(exe) if not os.path.isabs(exe) else exe
    if not resolved: raise ReadOnlyNamespaceExecutorError("EXECUTABLE_NOT_FOUND:"+exe)
    resolved=str(pathlib.Path(resolved).resolve())
    if not resolved.startswith(("/usr/","/bin/")):
        raise ReadOnlyNamespaceExecutorError("EXECUTABLE_OUTSIDE_SYSTEM_READONLY_MOUNTS")
    root=_choose_input_root(argv,kw.get("cwd"))
    mapped=[resolved]+[_map_path_token(x,root) for x in argv[1:]]
    mapped_cwd="/input" if kw.get("cwd") is not None else ""
    timeout=float(kw.get("timeout") or 60)
    if timeout<=0 or timeout>300: raise ReadOnlyNamespaceExecutorError("TIMEOUT_OUT_OF_RANGE")
    py=shutil.which("python3") or sys.executable
    policy={"argv":[py,"-c",_SHIM,json.dumps(mapped,separators=(",",":")),mapped_cwd,str(timeout)],
            "input_dir":str(root),"env":{},"limits":{"wallclock_s":min(int(timeout)+5,305),"cpu_seconds":min(max(int(timeout),1),300),"memory_mb":512,"scratch_mb":64,"max_file_mb":16,"pids":32,"nofile":64,"broker_max_bytes":8_000_000}}
    result=run_confined(policy)
    if result.get("status")!="CHILD_EXITED":
        raise ReadOnlyNamespaceExecutorError("CONFINED_CHILD_STATUS:"+str(result.get("status")))
    cp=_decode_capture(result.get("broker_payload") or b"",text=bool(kw.get("text") or kw.get("universal_newlines")),encoding=kw.get("encoding"),errors=kw.get("errors"))
    cp.args=argv
    if kw.get("check") and cp.returncode!=0:
        raise subprocess.CalledProcessError(cp.returncode,argv,output=cp.stdout,stderr=cp.stderr)
    return cp
