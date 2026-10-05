"""Root3 mediator V3: pure class planning plus mediator-owned confined carrier."""
from __future__ import annotations
import base64, contextvars, hashlib, json, os, re, subprocess, threading
from collections.abc import Callable, Mapping
from typing import Any

from canonical.runtime import root3_subprocess_mediator_v1 as v1
from canonical.runtime import zero_ambient_namespace_launcher_v1 as ns
from canonical.runtime.root3_subprocess_callsite_classifier_v1 import (
    RuntimeCallsiteClassificationError,
    detect_effect_class,
)
from canonical.runtime.root3_subprocess_effect_class_registry_v1 import CLASSES
from canonical.runtime.root3_readonly_namespace_plan_v1 import (
    SCHEMA as NAMESPACE_PLAN_SCHEMA,
)

SCHEMA="PROJECT_BRAIN_ROOT3_SUBPROCESS_MEDIATOR_REQUEST_V2"
SHA256_RE=re.compile(r"^[0-9a-f]{64}$")

_ORIGINAL_RUN=subprocess.run
_ORIGINAL_POPEN=subprocess.Popen
_LOCK=threading.RLock()
_IN_AUTHORIZATION:contextvars.ContextVar[bool]=contextvars.ContextVar("root3_v3_auth",default=False)
_IN_PLANNER:contextvars.ContextVar[bool]=contextvars.ContextVar("root3_v3_planner",default=False)
_AUTHORIZER:Callable[[Mapping[str,Any]],Mapping[str,Any]]|None=None
_AUTHORITY_ID:str|None=None
_CLASS_PLANNERS:dict[str,Callable[[Mapping[str,Any]],Mapping[str,Any]]]={}
_INSTALLED=False

class ProcessEffectDenied(PermissionError): pass
class MediatorStateError(RuntimeError): pass

def _canon(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()

def _sha(value:Any)->str:
    return hashlib.sha256(_canon(value)).hexdigest()

def _request(api:str,args:tuple[Any,...],kwargs:Mapping[str,Any],callsite:Mapping[str,Any])->dict[str,Any]:
    base=v1._request(api,args,kwargs)
    core=dict(base); core.pop("request_sha256",None)
    core["schema"]=SCHEMA
    core["callsite"]={
      "module_path":str(callsite["module_path"]),
      "lineno":int(callsite["lineno"]),
      "process_api":str(callsite["process_api"]),
      "function":str(callsite["function"]),
      "effect_class":str(callsite["effect_class"]),
      "registry_site_count":int(callsite["registry_site_count"]),
      "runtime_join":str(callsite["runtime_join"]),
    }
    return {**core,"request_sha256":_sha(core)}

def _classify(api:str)->dict[str,Any]:
    try:
        return detect_effect_class(api)
    except RuntimeCallsiteClassificationError as exc:
        raise ProcessEffectDenied("SUBPROCESS_CALLSITE_CLASSIFICATION_DENIED:"+str(exc)) from exc

def _authorize(api:str,args:tuple[Any,...],kwargs:Mapping[str,Any])->dict[str,Any]:
    if _IN_AUTHORIZATION.get():
        raise ProcessEffectDenied("SUBPROCESS_EFFECT_DURING_AUTHORIZATION_FORBIDDEN")
    if _IN_PLANNER.get():
        raise ProcessEffectDenied("SUBPROCESS_EFFECT_DURING_CLASS_PLANNER_FORBIDDEN")
    if _AUTHORIZER is None or _AUTHORITY_ID is None:
        raise ProcessEffectDenied("SUBPROCESS_MEDIATOR_AUTHORIZER_NOT_BOUND")
    callsite=_classify(api)
    effect_class=str(callsite["effect_class"])
    if effect_class not in CLASSES:
        raise ProcessEffectDenied("SUBPROCESS_EFFECT_CLASS_UNKNOWN:"+effect_class)
    request=_request(api,args,kwargs,callsite)
    token=_IN_AUTHORIZATION.set(True)
    try:
        verdict=_AUTHORIZER(request)
    finally:
        _IN_AUTHORIZATION.reset(token)
    if not isinstance(verdict,Mapping) or verdict.get("allowed") is not True:
        reason=verdict.get("reason") if isinstance(verdict,Mapping) else "INVALID_VERDICT"
        raise ProcessEffectDenied("SUBPROCESS_EFFECT_DENIED:"+str(reason or "UNSPECIFIED"))
    digest=str(verdict.get("authorization_sha256") or "")
    if not SHA256_RE.fullmatch(digest):
        raise ProcessEffectDenied("SUBPROCESS_AUTHORIZATION_DIGEST_INVALID")
    return {
      "authority_id":_AUTHORITY_ID,
      "request":request,
      "authorization_sha256":digest,
      "callsite":callsite,
      "effect_class":effect_class,
    }

def _argv(args:tuple[Any,...])->list[str]:
    if len(args)!=1 or not isinstance(args[0],(list,tuple)):
        raise ProcessEffectDenied("PLAN_ORIGINAL_ARGV_BINDING_INVALID")
    out=[]
    for x in args[0]:
        if not isinstance(x,(str,os.PathLike)):
            raise ProcessEffectDenied("PLAN_ORIGINAL_ARGV_BINDING_INVALID")
        out.append(os.fspath(x))
    return out

def _validate_plan(context:Mapping[str,Any],plan:Mapping[str,Any])->dict[str,Any]:
    keys={"schema","effect_class","api","policy","policy_sha256","original_argv","text","encoding","errors","check"}
    if not isinstance(plan,Mapping) or set(plan)!=keys:
        raise ProcessEffectDenied("NAMESPACE_PLAN_FIELDS_INVALID")
    if plan.get("schema")!=NAMESPACE_PLAN_SCHEMA:
        raise ProcessEffectDenied("NAMESPACE_PLAN_SCHEMA_INVALID")
    if plan.get("effect_class")!=context["effect_class"]:
        raise ProcessEffectDenied("NAMESPACE_PLAN_CLASS_MISMATCH")
    if plan.get("api")!=context["api"] or context["api"]!="subprocess.run":
        raise ProcessEffectDenied("NAMESPACE_PLAN_API_MISMATCH")
    if list(plan.get("original_argv") or [])!=_argv(context["args"]):
        raise ProcessEffectDenied("NAMESPACE_PLAN_ARGV_MISMATCH")
    policy=plan.get("policy")
    try:
        digest=ns.policy_sha256(policy)
    except Exception as exc:
        raise ProcessEffectDenied("NAMESPACE_PLAN_POLICY_INVALID:"+type(exc).__name__) from exc
    if digest!=plan.get("policy_sha256"):
        raise ProcessEffectDenied("NAMESPACE_PLAN_POLICY_HASH_MISMATCH")
    if not isinstance(plan.get("text"),bool) or not isinstance(plan.get("check"),bool):
        raise ProcessEffectDenied("NAMESPACE_PLAN_RESULT_MODE_INVALID")
    for k in ("encoding","errors"):
        if plan.get(k) is not None and not isinstance(plan.get(k),str):
            raise ProcessEffectDenied("NAMESPACE_PLAN_RESULT_CODEC_INVALID")
    return dict(plan)

def _complete_run(plan:Mapping[str,Any],result:Mapping[str,Any])->subprocess.CompletedProcess:
    if not isinstance(result,Mapping) or result.get("status")!="CHILD_EXITED":
        raise ProcessEffectDenied("NAMESPACE_CARRIER_NOT_CLEAN_EXIT:"+str(result.get("status") if isinstance(result,Mapping) else "INVALID"))
    raw=result.get("broker_payload")
    if not isinstance(raw,(bytes,bytearray)):
        raise ProcessEffectDenied("NAMESPACE_BROKER_PAYLOAD_INVALID")
    try:
        rec=json.loads(bytes(raw).decode("utf-8").strip())
        if set(rec)!={"returncode","stdout_b64","stderr_b64"}:
            raise ValueError("fields")
        stdout=base64.b64decode(rec["stdout_b64"],validate=True)
        stderr=base64.b64decode(rec["stderr_b64"],validate=True)
        rc=int(rec["returncode"])
    except Exception as exc:
        raise ProcessEffectDenied("NAMESPACE_BROKER_CAPTURE_INVALID") from exc
    if plan["text"]:
        enc=plan.get("encoding") or "utf-8"
        err=plan.get("errors") or "strict"
        stdout=stdout.decode(enc,errors=err)
        stderr=stderr.decode(enc,errors=err)
    argv=list(plan["original_argv"])
    cp=subprocess.CompletedProcess(args=argv,returncode=rc,stdout=stdout,stderr=stderr)
    if plan["check"] and rc!=0:
        raise subprocess.CalledProcessError(rc,argv,output=stdout,stderr=stderr)
    return cp

def _execute(api:str,args:tuple[Any,...],kwargs:Mapping[str,Any]):
    authorization=_authorize(api,args,kwargs)
    effect_class=authorization["effect_class"]
    planner=_CLASS_PLANNERS.get(effect_class)
    if planner is None:
        raise ProcessEffectDenied("PROCESS_EFFECT_CLASS_PLANNER_NOT_BOUND:"+effect_class)
    context={
      "api":api,
      "args":args,
      "kwargs":dict(kwargs),
      "authorization":authorization,
      "callsite":authorization["callsite"],
      "effect_class":effect_class,
    }
    token=_IN_PLANNER.set(True)
    try:
        plan=planner(context)
    finally:
        _IN_PLANNER.reset(token)
    plan=_validate_plan(context,plan)
    result=ns._run_confined(plan["policy"],popen_impl=_ORIGINAL_POPEN)
    return _complete_run(plan,result)

def _guarded_run(*args:Any,**kwargs:Any):
    return _execute("subprocess.run",args,kwargs)

def _guarded_popen(*args:Any,**kwargs:Any):
    return _execute("subprocess.Popen",args,kwargs)

def install(authorizer:Callable[[Mapping[str,Any]],Mapping[str,Any]],*,authority_id:str,class_planners:Mapping[str,Callable[[Mapping[str,Any]],Mapping[str,Any]]]|None=None)->dict[str,Any]:
    global _AUTHORIZER,_AUTHORITY_ID,_CLASS_PLANNERS,_INSTALLED
    if not callable(authorizer):
        raise MediatorStateError("SUBPROCESS_AUTHORIZER_NOT_CALLABLE")
    if not isinstance(authority_id,str) or not authority_id.strip():
        raise MediatorStateError("SUBPROCESS_AUTHORITY_ID_INVALID")
    raw=dict(class_planners or {})
    unknown=set(raw)-CLASSES
    if unknown:
        raise MediatorStateError("UNKNOWN_EFFECT_CLASS_PLANNER:"+",".join(sorted(unknown)))
    for name,planner in raw.items():
        if not callable(planner):
            raise MediatorStateError("EFFECT_CLASS_PLANNER_NOT_CALLABLE:"+name)
    with _LOCK:
        if _INSTALLED:
            if _AUTHORIZER is authorizer and _AUTHORITY_ID==authority_id.strip() and _CLASS_PLANNERS==raw:
                return status()
            raise MediatorStateError("SUBPROCESS_MEDIATOR_ALREADY_INSTALLED")
        if subprocess.run is not _ORIGINAL_RUN or subprocess.Popen is not _ORIGINAL_POPEN:
            raise MediatorStateError("SUBPROCESS_PREEXISTING_MONKEYPATCH")
        _AUTHORIZER=authorizer
        _AUTHORITY_ID=authority_id.strip()
        _CLASS_PLANNERS=raw
        subprocess.run=_guarded_run
        subprocess.Popen=_guarded_popen
        _INSTALLED=True
        return status()

def uninstall()->dict[str,Any]:
    global _AUTHORIZER,_AUTHORITY_ID,_CLASS_PLANNERS,_INSTALLED
    with _LOCK:
        if not _INSTALLED:
            return status()
        if subprocess.run is not _guarded_run or subprocess.Popen is not _guarded_popen:
            raise MediatorStateError("SUBPROCESS_GUARD_REPLACED")
        subprocess.run=_ORIGINAL_RUN
        subprocess.Popen=_ORIGINAL_POPEN
        _AUTHORIZER=None
        _AUTHORITY_ID=None
        _CLASS_PLANNERS={}
        _INSTALLED=False
        return status()

def status()->dict[str,Any]:
    return {
      "installed":bool(_INSTALLED),
      "run_guard_active":subprocess.run is _guarded_run,
      "popen_guard_active":subprocess.Popen is _guarded_popen,
      "authority_id":_AUTHORITY_ID,
      "bound_effect_class_planners":sorted(_CLASS_PLANNERS),
      "unbound_effect_classes":sorted(CLASSES-set(_CLASS_PLANNERS)),
      "strict_mode_when_installed":"EXACT_CLASS_AUTHORIZATION_PLUS_PURE_PLAN_PLUS_MEDIATOR_OWNED_CONFINED_CARRIER_OR_DENY",
    }
