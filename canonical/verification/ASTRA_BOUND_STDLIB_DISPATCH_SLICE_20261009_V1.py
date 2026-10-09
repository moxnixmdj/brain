"""Exact function slice extracted from canonical/runtime/astra_runtime.py.

Source Git blob: cbbaa444ec1a70b16593af3c39bfb270c7859d2c
This file is verification material only, not an executable runtime replacement.
"""
SOURCE_ASTRA_GIT_BLOB_SHA="cbbaa444ec1a70b16593af3c39bfb270c7859d2c"

def _load_bound_capability_registry():
    path=ROOT/"canonical"/"runtime"/"BOUND_CAPABILITY_REGISTRY_V1.json"
    data=readj(path)
    if data.get("schema")!="PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1":
        raise Blocker("BOUND_CAPABILITY_REGISTRY_INVALID")
    caps=data.get("capabilities")
    if not isinstance(caps,dict):
        raise Blocker("BOUND_CAPABILITY_REGISTRY_INVALID")
    return caps

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
    elif source.get("type")=="git_source_tree":
        dependency=_ensure_git_source_tree_dependency(source)
        call_args["_source_root"]=dependency.get("source_root")
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
        reason=str(result.get("reason") or result.get("error") or "").replace("\\n"," ")[:800]
        detail=_bounded_failure_result(result)
        message="ACTION_EXPECTATION_FAILED:"+field+":OBSERVED="+observed
        if reason:
            message+=":REASON="+reason
        message+=":RESULT="+detail
        raise Blocker(message)

