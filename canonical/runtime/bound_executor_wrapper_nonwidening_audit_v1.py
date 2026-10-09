"""Static non-widening audit for the promoted bound-capability wrapper.

This proves a narrow theorem only: the wrapper itself does not introduce an
independent capability-execution authority beyond the exact registry-selected
Astra bound invocation, and successful execution remains guarded by expectation
checking plus independent trace verification.

It deliberately does NOT prove the delegated Astra source-type branch or any
member adapter. Those remain separate D-final obligations.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_BOUND_EXECUTOR_WRAPPER_NONWIDENING_AUDIT_V1"
WRAPPER="canonical/runtime/verified_bound_capability_execution_adapter_v1.py"

FORBIDDEN_IMPORT_ROOTS={
    "socket","subprocess","urllib","http","requests","httpx","aiohttp",
    "ftplib","telnetlib","ssl","asyncio","multiprocessing"
}
FORBIDDEN_CALLS={
    "eval","exec","compile","__import__","os.system","os.popen",
    "subprocess.run","subprocess.call","subprocess.Popen",
    "importlib.import_module","importlib.util.spec_from_file_location",
}
ALLOWED_EXTERNAL_CALL_PREFIXES={
    "astra_runtime._render_bound_template",
    "astra_runtime._invoke_bound_capability",
    "astra_runtime._verify_action_expectation",
    "verify_execution",
    "plan_actions",
}


class WrapperAuditError(ValueError):
    pass


def _name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left=_name(node.value)
        return (left+"." if left else "")+node.attr
    return ""


def _function(tree: ast.Module,name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name==name:
            return node
    raise WrapperAuditError("FUNCTION_MISSING:"+name)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def audit(repo_root: str|Path) -> dict[str,Any]:
    root=Path(repo_root).resolve()
    path=(root/WRAPPER).resolve()
    if root not in path.parents or not path.is_file():
        raise WrapperAuditError("WRAPPER_MISSING")
    raw=path.read_bytes()
    tree=ast.parse(raw.decode("utf-8"),filename=WRAPPER)

    forbidden_imports=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_IMPORT_ROOTS:
                    forbidden_imports.append(alias.name)
        elif isinstance(node,ast.ImportFrom):
            mod=str(node.module or "")
            if mod.split(".")[0] in FORBIDDEN_IMPORT_ROOTS:
                forbidden_imports.append(mod)

    forbidden_calls=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Call):
            name=_name(node.func)
            if name in FORBIDDEN_CALLS:
                forbidden_calls.append(name)

    execute=_function(tree,"execute")
    prepare=_function(tree,"prepare")
    inspect_fn=_function(tree,"inspect")

    execute_calls=[_name(n.func) for n in ast.walk(execute) if isinstance(n,ast.Call)]
    prepare_calls=[_name(n.func) for n in ast.walk(prepare) if isinstance(n,ast.Call)]
    inspect_calls=[_name(n.func) for n in ast.walk(inspect_fn) if isinstance(n,ast.Call)]

    operative=[x for x in execute_calls if x.startswith("astra_runtime.")]
    if operative.count("astra_runtime._invoke_bound_capability")!=1:
        raise WrapperAuditError("OPERATIVE_DELEGATE_COUNT_NOT_ONE")
    unexpected_operatives=sorted(set(operative)-{
        "astra_runtime._invoke_bound_capability",
        "astra_runtime._verify_action_expectation",
    })
    if unexpected_operatives:
        raise WrapperAuditError("UNEXPECTED_EXECUTE_ASTRA_CALL:"+",".join(unexpected_operatives))
    if execute_calls.count("astra_runtime._verify_action_expectation")!=1:
        raise WrapperAuditError("EXPECTATION_CHECK_COUNT_NOT_ONE")
    if execute_calls.count("verify_execution")!=1:
        raise WrapperAuditError("INDEPENDENT_TRACE_VERIFY_COUNT_NOT_ONE")
    if execute_calls.count("plan_actions")!=1:
        raise WrapperAuditError("PLAN_ACTIONS_COUNT_NOT_ONE")
    if prepare_calls.count("astra_runtime._render_bound_template")!=1:
        raise WrapperAuditError("TEMPLATE_RENDER_COUNT_NOT_ONE")
    if prepare_calls.count("inspect")!=1:
        raise WrapperAuditError("PREPARE_INSPECT_COUNT_NOT_ONE")
    if execute_calls.count("inspect")!=1:
        raise WrapperAuditError("EXECUTE_REINSPECT_COUNT_NOT_ONE")

    # Registry drift guards must exist in successful execute path.
    source=ast.get_source_segment(raw.decode("utf-8"),execute) or ""
    required_tokens=[
        "REGISTRY_FILE_CHANGED_AFTER_PREPARATION",
        "REGISTRY_ENTRY_CHANGED_AFTER_PREPARATION",
        "RENDERED_ACTION_CHANGED_AFTER_PREPARATION",
        "BOUND_CAPABILITY_EXECUTION_TRACE_NOT_VERIFIED",
    ]
    missing=[t for t in required_tokens if t not in source]
    if missing:
        raise WrapperAuditError("REQUIRED_FAIL_CLOSED_GUARD_MISSING:"+",".join(missing))

    errors=[]
    if forbidden_imports:
        errors.append("FORBIDDEN_IMPORT:"+",".join(sorted(set(forbidden_imports))))
    if forbidden_calls:
        errors.append("FORBIDDEN_CALL:"+",".join(sorted(set(forbidden_calls))))

    passed=not errors
    return {
        "schema":SCHEMA,
        "status":"PASS__WRAPPER_NONWIDENING" if passed else "FAIL_CLOSED",
        "pass":passed,
        "wrapper_path":WRAPPER,
        "wrapper_git_blob_sha":hashlib.sha1(
            b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw
        ).hexdigest(),
        "wrapper_sha256":_sha256(raw),
        "forbidden_imports":sorted(set(forbidden_imports)),
        "forbidden_calls":sorted(set(forbidden_calls)),
        "execute_astra_calls":operative,
        "execute_plan_actions_count":execute_calls.count("plan_actions"),
        "execute_independent_trace_verify_count":execute_calls.count("verify_execution"),
        "prepare_template_render_count":prepare_calls.count("astra_runtime._render_bound_template"),
        "prepare_inspect_count":prepare_calls.count("inspect"),
        "execute_reinspect_count":execute_calls.count("inspect"),
        "single_operative_delegate":"astra_runtime._invoke_bound_capability",
        "authority_claim":"WRAPPER_ITSELF_DOES_NOT_ADD_AN_INDEPENDENT_EXECUTION_CHANNEL",
        "delegated_source_type_theorem_required":True,
        "member_material_theorem_required":True,
        "errors":errors,
        "execution_authority":False,
        "promotion_authority":False,
        "ownership_credit_delta":0,
        "terminal_credit_delta":0,
    }


if __name__=="__main__":
    import json,sys
    out=audit(Path(__file__).resolve().parents[2])
    print(json.dumps(out,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
