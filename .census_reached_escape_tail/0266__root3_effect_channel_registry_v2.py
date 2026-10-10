"""Root3 C1 compiler for the finite repo-local execution-module universe.

This compiler is deliberately narrower than a whole-runtime effect-totality proof.
It proves that the current ASTRA repo-local dynamic-loading surface is finite,
content-addressed, and partitioned into:
  1. fixed repo-local loader sites,
  2. literal runtime-helper modules,
  3. registry-selected ordinary adapter modules,
  4. registry-declared runtime-native actions that execute directly through
     _goal_action and therefore do not require adapter files.

It leaves non-repo dependency effects, native-extension internal effects,
child-process internal effects, and external-tool-bridge process effects open.
No Root3 or acceptance credit is produced.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Any

OUTPUT_SCHEMA="PROJECT_BRAIN_ROOT3_EFFECT_CHANNEL_REGISTRY_C1_OUTPUT_V2"
MANIFEST_SCHEMA="PROJECT_BRAIN_ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V2"


class RegistryError(ValueError):
    pass


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()


def file_blob(path: Path) -> str:
    return git_blob_sha(path.read_bytes())


def _safe_module(value: Any, label: str) -> str:
    if not isinstance(value,str) or not re.fullmatch(r"[A-Za-z0-9_]+",value):
        raise RegistryError(label+"_INVALID")
    return value


def _qualified_name(node: ast.AST) -> str | None:
    if isinstance(node,ast.Name):
        return node.id
    if isinstance(node,ast.Attribute):
        p=_qualified_name(node.value)
        return None if p is None else p+"."+node.attr
    return None


class _CallSiteVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.stack: list[str] = []
        self.spec_sites: list[str] = []
        self.runtime_helper_args: list[str] = []

    def visit_FunctionDef(self,node: ast.FunctionDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self,node: ast.AsyncFunctionDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_Call(self,node: ast.Call) -> None:
        q=_qualified_name(node.func)
        fn=self.stack[-1] if self.stack else "<module>"
        if q=="importlib.util.spec_from_file_location":
            self.spec_sites.append(fn)
        if q=="_load_runtime_helper":
            if (
                len(node.args)!=1
                or not isinstance(node.args[0],ast.Constant)
                or not isinstance(node.args[0].value,str)
            ):
                raise RegistryError(
                    "NONLITERAL_RUNTIME_HELPER_CALL_AT_LINE:"
                    +str(getattr(node,"lineno",0))
                )
            self.runtime_helper_args.append(
                _safe_module(node.args[0].value,"RUNTIME_HELPER")
            )
        self.generic_visit(node)


def _find_function(tree: ast.Module,name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name==name:
            return node
    raise RegistryError("FUNCTION_MISSING:"+name)


def _string_constants(node: ast.AST) -> set[str]:
    return {
        str(x.value)
        for x in ast.walk(node)
        if isinstance(x,ast.Constant) and isinstance(x.value,str)
    }


def _goal_action_types(tree: ast.Module) -> set[str]:
    fn=_find_function(tree,"_goal_action")
    out=set()
    for node in ast.walk(fn):
        if not isinstance(node,ast.Compare) or len(node.ops)!=1 or len(node.comparators)!=1:
            continue
        if not isinstance(node.left,ast.Name) or node.left.id!="typ":
            continue
        if not isinstance(node.ops[0],ast.Eq):
            continue
        c=node.comparators[0]
        if isinstance(c,ast.Constant) and isinstance(c.value,str):
            out.add(c.value)
    return out


def _controller_allowed_types(tree: ast.Module) -> set[str]:
    fn=_find_function(tree,"_run_model_independent_goal")
    for node in ast.walk(fn):
        if not isinstance(node,(ast.Assign,ast.AnnAssign)):
            continue
        targets=node.targets if isinstance(node,ast.Assign) else [node.target]
        if not any(isinstance(t,ast.Name) and t.id=="allowed_types" for t in targets):
            continue
        value=node.value
        if isinstance(value,(ast.Set,ast.List,ast.Tuple)):
            vals=[]
            for x in value.elts:
                if not isinstance(x,ast.Constant) or not isinstance(x.value,str):
                    raise RegistryError("CONTROLLER_ALLOWED_TYPES_NONLITERAL")
                vals.append(x.value)
            return set(vals)
    raise RegistryError("CONTROLLER_ALLOWED_TYPES_NOT_FOUND")


def compile_registry(repo_root: str | Path, manifest_path: str | Path) -> dict[str,Any]:
    root=Path(repo_root).resolve()
    mp=(root/manifest_path).resolve()
    manifest=json.loads(mp.read_text(encoding="utf-8"))
    if manifest.get("schema")!=MANIFEST_SCHEMA:
        raise RegistryError("MANIFEST_SCHEMA_INVALID")

    subj=manifest["subject"]
    astra_rel=subj["astra_runtime"]["path"]
    reg_rel=subj["bound_capability_registry"]["path"]
    astra=(root/astra_rel).resolve()
    reg=(root/reg_rel).resolve()
    astra_blob=file_blob(astra)
    reg_blob=file_blob(reg)
    if astra_blob!=subj["astra_runtime"]["git_blob_sha"]:
        raise RegistryError("ASTRA_RUNTIME_BLOB_DRIFT")
    if reg_blob!=subj["bound_capability_registry"]["git_blob_sha"]:
        raise RegistryError("BOUND_CAPABILITY_REGISTRY_BLOB_DRIFT")

    tree=ast.parse(astra.read_text(encoding="utf-8"),filename=str(astra))
    visitor=_CallSiteVisitor()
    visitor.visit(tree)

    expected_sites=sorted(manifest["expected_repo_dynamic_universe"]["spec_loader_site_functions"])
    if sorted(visitor.spec_sites)!=expected_sites:
        raise RegistryError("SPEC_LOADER_SITE_SET_DRIFT")

    expected_helpers=sorted(manifest["expected_repo_dynamic_universe"]["literal_runtime_helpers"])
    helpers=sorted(set(visitor.runtime_helper_args))
    if helpers!=expected_helpers:
        raise RegistryError("RUNTIME_HELPER_SET_DRIFT")

    # The fixed sites are bound both by exact ASTRA bytes and by an expected
    # .py basename occurring in the responsible loader function.
    fixed_sites=manifest["expected_repo_dynamic_universe"]["fixed_loader_sites"]
    if not isinstance(fixed_sites,dict):
        raise RegistryError("FIXED_LOADER_SITES_INVALID")
    for fn_name,rel in sorted(fixed_sites.items()):
        fn=_find_function(tree,fn_name)
        basename=Path(rel).name
        if basename not in _string_constants(fn):
            raise RegistryError("FIXED_LOADER_PATH_LITERAL_MISSING:"+fn_name)

    goal_actions=_goal_action_types(tree)
    allowed_actions=_controller_allowed_types(tree)

    registry=json.loads(reg.read_text(encoding="utf-8"))
    caps=registry.get("capabilities")
    if not isinstance(caps,dict):
        raise RegistryError("CAPABILITY_REGISTRY_INVALID")

    regular_adapters=set()
    native_rows=[]
    source_types=set()

    for cid,entry in sorted(caps.items()):
        if not isinstance(entry,dict):
            raise RegistryError("CAPABILITY_ENTRY_INVALID:"+str(cid))
        source=entry.get("source") or {}
        stype=str(source.get("type") or "")
        if stype:
            source_types.add(stype)

        if stype=="runtime_native":
            action_type=str(source.get("action_type") or "")
            runtime_path=str(source.get("runtime_path") or "")
            template=entry.get("action_template") or {}
            if runtime_path!=astra_rel:
                raise RegistryError("RUNTIME_NATIVE_RUNTIME_PATH_MISMATCH:"+cid)
            if template.get("type")!=action_type or not action_type:
                raise RegistryError("RUNTIME_NATIVE_ACTION_TEMPLATE_MISMATCH:"+cid)
            if entry.get("adapter_module")!="runtime_native_action":
                raise RegistryError("RUNTIME_NATIVE_MARKER_MISMATCH:"+cid)
            if action_type not in goal_actions:
                raise RegistryError("RUNTIME_NATIVE_GOAL_ACTION_MISSING:"+cid)
            if action_type not in allowed_actions:
                raise RegistryError("RUNTIME_NATIVE_CONTROLLER_ACTION_NOT_ALLOWED:"+cid)
            native_rows.append({
                "capability_id":cid,
                "action_type":action_type,
                "runtime_path":runtime_path,
                "execution_class":"DIRECT_GOAL_ACTION",
            })
            continue

        module=_safe_module(entry.get("adapter_module"),"ADAPTER_MODULE")
        regular_adapters.add(module)
        if str(entry.get("entrypoint") or "run")!="run":
            raise RegistryError("NONDEFAULT_BOUND_ENTRYPOINT:"+cid)

    expected_adapters=sorted(
        manifest["expected_repo_dynamic_universe"]["ordinary_adapter_modules"]
    )
    adapters=sorted(regular_adapters)
    if adapters!=expected_adapters:
        raise RegistryError("ORDINARY_ADAPTER_SET_DRIFT")

    expected_native=sorted(
        manifest["expected_repo_dynamic_universe"]["runtime_native_actions"],
        key=lambda x:x["capability_id"],
    )
    if sorted(native_rows,key=lambda x:x["capability_id"])!=expected_native:
        raise RegistryError("RUNTIME_NATIVE_SET_DRIFT")

    paths=set(str(x) for x in fixed_sites.values())
    paths.update("canonical/runtime/"+x+".py" for x in helpers)
    paths.update(
        "canonical/runtime/bound_capabilities/"+x+".py" for x in adapters
    )
    content_addressed=[]
    missing=[]
    for rel in sorted(paths):
        p=(root/rel).resolve()
        if not p.is_file():
            missing.append(rel)
            continue
        content_addressed.append({"path":rel,"git_blob_sha":file_blob(p)})
    if missing:
        raise RegistryError("REGISTERED_REPO_MODULE_MISSING:"+",".join(missing))

    nonrepo=sorted(
        x for x in source_types
        if x not in {"python_stdlib","runtime_native"}
    )

    return {
        "schema":OUTPUT_SCHEMA,
        "status":"REPO_LOCAL_DYNAMIC_EXECUTION_UNIVERSE_CLOSED__C1_OVERALL_OPEN_ON_NONREPO_NATIVE_CHILD_EFFECT_TOTALITY",
        "astra_runtime_git_blob_sha":astra_blob,
        "bound_capability_registry_git_blob_sha":reg_blob,
        "spec_loader_site_count":len(visitor.spec_sites),
        "spec_loader_site_functions":sorted(visitor.spec_sites),
        "literal_runtime_helpers":helpers,
        "bound_capability_count":len(caps),
        "ordinary_adapter_module_count":len(adapters),
        "runtime_native_action_count":len(native_rows),
        "runtime_native_actions":native_rows,
        "registered_repo_module_count":len(content_addressed),
        "registered_repo_modules":content_addressed,
        "bound_source_types":sorted(source_types),
        "nonrepo_dependency_source_types":nonrepo,
        "repo_local_dynamic_execution_universe_closed":True,
        "runtime_native_direct_action_universe_closed":True,
        "explicit_invoke_capability_on_runtime_native_entries":"FAILS_CLOSED_BY_CURRENT_INVOKER_SOURCE_TYPE_REJECTION__NOT_A_MATERIAL_EFFECT_BYPASS",
        "third_party_dependency_effect_totality_proved":False,
        "native_extension_effect_totality_proved":False,
        "child_process_effect_totality_proved":False,
        "external_tool_bridge_other_process_effect_totality_proved":False,
        "c1_channel_registry_scope_complete":False,
        "remaining_c1_residuals":[
            "NONREPO_DEPENDENCY_EFFECT_SURFACE",
            "NATIVE_EXTENSION_INTERNAL_EFFECTS",
            "CHILD_PROCESS_INTERNAL_EFFECTS",
            "EXTERNAL_TOOL_BRIDGE_OTHER_PROCESS_EFFECTS",
        ],
        "hard_nonclaims":[
            "NO_CLAIM_WHOLE_RUNTIME_EFFECT_TOTALITY",
            "NO_CLAIM_NATIVE_OR_CHILD_PROCESS_EFFECTS_ARE_MEDIATED",
            "NO_ROOT3_PREDICATE_CLOSED",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
        "acceptance_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
    }


if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=".")
    ap.add_argument(
        "--manifest",
        default="canonical/governance/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V2.json",
    )
    ns=ap.parse_args()
    print(json.dumps(compile_registry(ns.repo_root,ns.manifest),indent=2,sort_keys=True))
