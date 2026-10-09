"""Conditional non-widening theorem for Astra's python_stdlib bound dispatch.

Scope is deliberately narrow:
- exact current source slice extracted from one Astra blob;
- registry row is separately content-bound;
- theorem applies only when source.type == python_stdlib;
- member adapter semantics remain a separate theorem.

It does not certify apt/npm/PyPI/system-tool branches.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_BOUND_STDLIB_DISPATCH_NONWIDENING_AUDIT_V1"
SLICE="canonical/verification/ASTRA_BOUND_STDLIB_DISPATCH_SLICE_20261009_V1.py"
EXPECTED_ASTRA_GIT_BLOB_SHA="cbbaa444ec1a70b16593af3c39bfb270c7859d2c"

class StdlibDispatchAuditError(ValueError):
    pass

def _name(node: ast.AST) -> str:
    if isinstance(node,ast.Name):
        return node.id
    if isinstance(node,ast.Attribute):
        left=_name(node.value)
        return (left+"." if left else "")+node.attr
    return ""

def _func(tree: ast.Module,name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name==name:
            return node
    raise StdlibDispatchAuditError("FUNCTION_MISSING:"+name)

def _src(text: str,node: ast.AST) -> str:
    return ast.get_source_segment(text,node) or ""

def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def audit(repo_root: str|Path) -> dict[str,Any]:
    root=Path(repo_root).resolve()
    path=(root/SLICE).resolve()
    if root not in path.parents or not path.is_file():
        raise StdlibDispatchAuditError("SLICE_MISSING")
    raw=path.read_bytes()
    text=raw.decode("utf-8")
    tree=ast.parse(text,filename=SLICE)

    declared=None
    for node in tree.body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id=="SOURCE_ASTRA_GIT_BLOB_SHA":
                    if isinstance(node.value,ast.Constant) and isinstance(node.value.value,str):
                        declared=node.value.value
    if declared!=EXPECTED_ASTRA_GIT_BLOB_SHA:
        raise StdlibDispatchAuditError("SOURCE_ASTRA_BLOB_BINDING_MISMATCH")

    load=_func(tree,"_load_bound_capability_registry")
    render=_func(tree,"_render_bound_template")
    local=_func(tree,"_ensure_local_dependency")
    invoke=_func(tree,"_invoke_bound_capability")
    expect=_func(tree,"_verify_action_expectation")

    load_src=_src(text,load)
    render_src=_src(text,render)
    local_src=_src(text,local)
    invoke_src=_src(text,invoke)
    expect_src=_src(text,expect)

    required_load=[
        'ROOT/"canonical"/"runtime"/"BOUND_CAPABILITY_REGISTRY_V1.json"',
        'PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1',
    ]
    for token in required_load:
        if token not in load_src:
            raise StdlibDispatchAuditError("REGISTRY_BINDING_GUARD_MISSING:"+token)

    if 'typ=="python_stdlib"' not in local_src:
        raise StdlibDispatchAuditError("PYTHON_STDLIB_BRANCH_MISSING")
    if "importlib.util.find_spec(module)" not in local_src:
        raise StdlibDispatchAuditError("STDLIB_IMPORTABILITY_PROBE_MISSING")
    if 'status":"LOCAL_VERIFIED"' not in local_src or '"type":"python_stdlib"' not in local_src:
        raise StdlibDispatchAuditError("STDLIB_LOCAL_VERIFIED_RECEIPT_MISSING")

    local_calls=[_name(n.func) for n in ast.walk(local) if isinstance(n,ast.Call)]
    forbidden_local_prefixes=(
        "urllib.","socket.","subprocess.","requests.","httpx.","aiohttp.",
        "os.system","os.popen","eval","exec","compile","__import__"
    )
    bad_local=sorted({c for c in local_calls if any(c.startswith(p) for p in forbidden_local_prefixes)})
    if bad_local:
        raise StdlibDispatchAuditError("STDLIB_BRANCH_AUTHORITY_WIDENING:"+",".join(bad_local))

    if 'source.get("type") in {"python_stdlib","system_tool"}' not in invoke_src:
        raise StdlibDispatchAuditError("LOCAL_SOURCE_DISPATCH_BRANCH_MISSING")
    if "dependency=_ensure_local_dependency(source)" not in invoke_src:
        raise StdlibDispatchAuditError("LOCAL_SOURCE_NOT_ROUTED_TO_LOCAL_DEPENDENCY_CHECK")
    if 'module_name=str(entry.get("adapter_module") or "")' not in invoke_src:
        raise StdlibDispatchAuditError("ADAPTER_ID_NOT_REGISTRY_BOUND")
    if 'any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for ch in module_name)' not in invoke_src:
        raise StdlibDispatchAuditError("ADAPTER_NAME_SANITIZER_MISSING")
    if 'ROOT/"canonical"/"runtime"/"bound_capabilities"/(module_name+".py")' not in invoke_src:
        raise StdlibDispatchAuditError("ADAPTER_PATH_NOT_FIXED_TO_BOUND_CAPABILITIES")
    if 'importlib.util.spec_from_file_location("project_brain_bound_"+module_name,path)' not in invoke_src:
        raise StdlibDispatchAuditError("ADAPTER_DYNAMIC_LOAD_NOT_FIXED_TO_SANITIZED_PATH")

    invoke_calls=[_name(n.func) for n in ast.walk(invoke) if isinstance(n,ast.Call)]
    adapter_entry_calls=sum(1 for c in invoke_calls if c=="fn")
    if adapter_entry_calls!=1:
        raise StdlibDispatchAuditError("ADAPTER_ENTRYPOINT_CALL_COUNT_NOT_ONE")

    # The template renderer and expectation checker must themselves remain free
    # of external process/network authority.
    safe_funcs={"_render_bound_template":render,"_verify_action_expectation":expect}
    forbidden_shared=(
        "urllib.","socket.","subprocess.","requests.","httpx.","aiohttp.",
        "os.system","os.popen","eval","exec","compile","__import__",
        "importlib.import_module"
    )
    bad_shared=[]
    for label,node in safe_funcs.items():
        for call in ast.walk(node):
            if isinstance(call,ast.Call):
                name=_name(call.func)
                if any(name.startswith(p) for p in forbidden_shared):
                    bad_shared.append(label+":"+name)
    if bad_shared:
        raise StdlibDispatchAuditError("SHARED_GUARD_AUTHORITY_WIDENING:"+",".join(sorted(set(bad_shared))))

    # Exact fail-closed obligations around the selected member.
    required_invoke=[
        "BOUND_CAPABILITY_ID_REQUIRED",
        "BOUND_CAPABILITY_UNKNOWN",
        "BOUND_CAPABILITY_NONZERO_COST_REJECTED",
        "BOUND_CAPABILITY_ADAPTER_INVALID",
        "BOUND_CAPABILITY_ADAPTER_MISSING",
        "BOUND_CAPABILITY_ADAPTER_LOAD_FAILED",
        "BOUND_CAPABILITY_ENTRYPOINT_MISSING",
        "BOUND_CAPABILITY_RESULT_INVALID",
    ]
    missing=[x for x in required_invoke if x not in invoke_src]
    if missing:
        raise StdlibDispatchAuditError("FAIL_CLOSED_GUARD_MISSING:"+",".join(missing))

    return {
        "schema":SCHEMA,
        "status":"PASS__PYTHON_STDLIB_DISPATCH_NONWIDENING",
        "pass":True,
        "source_astra_git_blob_sha":declared,
        "slice_path":SLICE,
        "slice_sha256":_sha256(raw),
        "stdlib_local_calls":sorted(set(local_calls)),
        "adapter_entrypoint_call_count":adapter_entry_calls,
        "conditional_scope":"ONLY_REGISTRY_ROWS_WITH_SOURCE_TYPE_PYTHON_STDLIB",
        "authority_claim":"PYTHON_STDLIB_DISPATCH_ADDS_NO_NETWORK_OR_PROCESS_DONOR_CHANNEL_BEFORE_THE_MEMBER_ADAPTER",
        "registry_row_content_binding_required":True,
        "member_material_theorem_required":True,
        "wrapper_nonwidening_theorem_required":True,
        "execution_authority":False,
        "promotion_authority":False,
        "ownership_credit_delta":0,
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    import json
    out=audit(Path(__file__).resolve().parents[2])
    print(json.dumps(out,sort_keys=True))
