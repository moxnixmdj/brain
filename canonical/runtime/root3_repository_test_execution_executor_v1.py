from __future__ import annotations
import base64, hashlib, json, locale, os, pathlib, subprocess, sys
from collections.abc import Callable, Mapping
from typing import Any
from canonical.runtime import root3_read_only_local_file_query_executor_v1 as conf

SCHEMA="PROJECT_BRAIN_ROOT3_REPOSITORY_TEST_EXECUTION_EXECUTOR_V1"
EFFECT_CLASS="BOUND_CHILD_CODE_EXECUTION"
PROFILE="REPOSITORY_TEST_EXECUTION"
FROZEN_TIMEOUT_S=180.0
SUPPORTED={
 ("canonical/runtime/astra_runtime.py",1215,"subprocess.run"),
 ("canonical/runtime/bound_capabilities/python_test_audit.py",50,"subprocess.run"),
}
_RUN_CODE='import runpy,sys; sys.path.insert(0,"/input"); p=sys.argv[1]; sys.argv=[p]; runpy.run_path(p,run_name="__main__")'

class RepositoryTestExecutionDenied(PermissionError): pass

def _key(context):
    if context.get("effect_class")!=EFFECT_CLASS: raise RepositoryTestExecutionDenied("EFFECT_CLASS_MISMATCH")
    c=context.get("callsite")
    if not isinstance(c,Mapping): raise RepositoryTestExecutionDenied("CALLSITE_MISSING")
    try: return (str(c.get("module_path") or ""),int(c.get("lineno") or 0),str(c.get("process_api") or ""))
    except Exception as exc: raise RepositoryTestExecutionDenied("CALLSITE_INVALID") from exc

def _root(value):
    try: p=pathlib.Path(os.fspath(value)).resolve()
    except Exception as exc: raise RepositoryTestExecutionDenied("REPO_ROOT_INVALID") from exc
    if not p.is_dir(): raise RepositoryTestExecutionDenied("REPO_ROOT_MISSING")
    return p

def _prepare(context,repo_root=None):
    key=_key(context)
    if key not in SUPPORTED: raise RepositoryTestExecutionDenied("REPOSITORY_TEST_CALLSITE_NOT_SUPPORTED:"+repr(key))
    args=context.get("args")
    if not isinstance(args,(list,tuple)) or len(args)!=1: raise RepositoryTestExecutionDenied("COMMAND_POSITIONAL_SHAPE_INVALID")
    cmd=args[0]
    if not isinstance(cmd,(list,tuple)) or len(cmd)!=2: raise RepositoryTestExecutionDenied("PYTHON_TEST_ARGV_SHAPE_INVALID")
    kwargs=dict(context.get("kwargs") or {})
    if set(kwargs)!={"cwd","text","capture_output","timeout"}: raise RepositoryTestExecutionDenied("PYTHON_TEST_KWARGS_NOT_EXACT")
    if kwargs.get("text") is not True or kwargs.get("capture_output") is not True: raise RepositoryTestExecutionDenied("PYTHON_TEST_TEXT_CAPTURE_REQUIRED")
    try: timeout=float(kwargs.get("timeout"))
    except Exception as exc: raise RepositoryTestExecutionDenied("TIMEOUT_INVALID") from exc
    if timeout!=FROZEN_TIMEOUT_S: raise RepositoryTestExecutionDenied("TIMEOUT_NOT_FROZEN_180")
    root=_root(repo_root if repo_root is not None else kwargs.get("cwd"))
    try: cwd=pathlib.Path(os.fspath(kwargs.get("cwd"))).resolve()
    except Exception as exc: raise RepositoryTestExecutionDenied("CWD_INVALID") from exc
    if cwd!=root: raise RepositoryTestExecutionDenied("CWD_NOT_REPOSITORY_ROOT")
    try:
        requested=pathlib.Path(os.fspath(cmd[0])).resolve()
        python=pathlib.Path(sys.executable).resolve()
    except Exception as exc: raise RepositoryTestExecutionDenied("PYTHON_EXECUTABLE_INVALID") from exc
    if requested!=python: raise RepositoryTestExecutionDenied("PYTHON_EXECUTABLE_DRIFT")
    if not (str(python).startswith("/usr/") or str(python).startswith("/bin/")): raise RepositoryTestExecutionDenied("PYTHON_EXECUTABLE_NOT_SYSTEM_BOUND")
    try:
        target=pathlib.Path(os.fspath(cmd[1])).resolve()
        rel=target.relative_to(root)
    except Exception as exc: raise RepositoryTestExecutionDenied("TEST_PATH_OUTSIDE_REPOSITORY") from exc
    if target.suffix!=".py" or not target.is_file() or target.is_symlink(): raise RepositoryTestExecutionDenied("TEST_TARGET_NOT_REGULAR_PYTHON_FILE")
    test_sha=hashlib.sha256(target.read_bytes()).hexdigest()
    inner=[str(python),"-I","-c",_RUN_CODE,"/input/"+rel.as_posix()]
    spec={"argv":inner,"cwd":"/input","timeout":FROZEN_TIMEOUT_S}
    encoded=base64.urlsafe_b64encode(json.dumps(spec,sort_keys=True,separators=(",",":")).encode()).decode("ascii")
    policy={
      "argv":[str(python),"-I","-c",conf._WRAPPER,encoded],
      "input_dir":str(root),
      "limits":{"pids":64,"memory_mb":2048,"cpu_seconds":181,"wallclock_s":190,"scratch_mb":256,"max_file_mb":64,"nofile":128,"broker_max_bytes":8000000},
    }
    return {"profile":PROFILE,"callsite_key":key,"original_argv":[os.fspath(x) for x in cmd],"kwargs":kwargs,"policy":policy,"timeout":timeout,"test_sha256":test_sha,"encoded_spec":encoded,"target_path":str(target)}

def _completed(prepared,result):
    if hashlib.sha256(pathlib.Path(prepared["target_path"]).read_bytes()).hexdigest()!=prepared["test_sha256"]:
        raise RepositoryTestExecutionDenied("TEST_BYTES_DRIFT_AFTER_EXECUTION")
    try:
        stdout_b=base64.b64decode(result.get("stdout_b64") or "",validate=True)
        stderr_b=base64.b64decode(result.get("stderr_b64") or "",validate=True)
    except Exception as exc: raise RepositoryTestExecutionDenied("BROKER_STDIO_ENCODING_INVALID") from exc
    enc=locale.getpreferredencoding(False) or "utf-8"
    stdout=stdout_b.decode(enc,errors="replace"); stderr=stderr_b.decode(enc,errors="replace")
    if result.get("timed_out") is True:
        raise subprocess.TimeoutExpired(prepared["original_argv"],prepared["timeout"],output=stdout,stderr=stderr)
    rc=result.get("returncode")
    if isinstance(rc,bool) or not isinstance(rc,int): raise RepositoryTestExecutionDenied("BROKER_RETURNCODE_INVALID")
    return subprocess.CompletedProcess(args=prepared["original_argv"],returncode=rc,stdout=stdout,stderr=stderr)

def make_executor(*,popen_impl:Callable[...,Any],repo_root):
    if not callable(popen_impl): raise TypeError("POPEN_IMPL_NOT_CALLABLE")
    root=_root(repo_root)
    def execute(context):
        prepared=_prepare(context,root)
        try: result=conf._run_confined_with_popen(prepared["policy"],popen_impl)
        except Exception as exc:
            raise RepositoryTestExecutionDenied("REPOSITORY_TEST_CONFINEMENT_FAILED:"+type(exc).__name__+":"+str(exc)) from exc
        if not isinstance(result,Mapping): raise RepositoryTestExecutionDenied("CONFINEMENT_RESULT_INVALID")
        return _completed(prepared,result)
    return execute
