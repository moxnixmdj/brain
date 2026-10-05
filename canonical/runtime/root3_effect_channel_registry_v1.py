"""Compile the finite repo-local dynamic module universe for the Root3 channel mincut.

C1 is only partially discharged by this compiler. It proves that the current
ASTRA runtime's explicit spec_from_file_location module-loading surface is
finite and registry-bound on exact source bytes. It deliberately leaves effects
originating inside non-repo dependencies, native extensions and child
processes open.

No acceptance or Root3 credit is produced.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_ROOT3_EFFECT_CHANNEL_REGISTRY_C1_OUTPUT_V1"


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
        parent=_qualified_name(node.value)
        return None if parent is None else parent+"."+node.attr
    return None


def _runtime_helper_calls(tree: ast.AST) -> list[str]:
    out=[]
    for node in ast.walk(tree):
        if not isinstance(node,ast.Call):
            continue
        if _qualified_name(node.func)!="_load_runtime_helper":
            continue
        if len(node.args)!=1 or not isinstance(node.args[0],ast.Constant) or not isinstance(node.args[0].value,str):
            raise RegistryError(f"NONLITERAL_RUNTIME_HELPER_CALL_AT_LINE:{getattr(node,'lineno',0)}")
        out.append(_safe_module(node.args[0].value,"RUNTIME_HELPER"))
    return sorted(set(out))


def _spec_loader_count(tree: ast.AST) -> int:
    return sum(
        1 for node in ast.walk(tree)
        if isinstance(node,ast.Call)
        and _qualified_name(node.func)=="importlib.util.spec_from_file_location"
    )


def compile_registry(repo_root: str | Path, manifest_path: str | Path) -> dict[str,Any]:
    root=Path(repo_root).resolve()
    manifest_file=(root/manifest_path).resolve()
    manifest=json.loads(manifest_file.read_text(encoding="utf-8"))

    if manifest.get("schema")!="PROJECT_BRAIN_ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V1":
        raise RegistryError("MANIFEST_SCHEMA_INVALID")

    astra_path=(root/manifest["subject"]["astra_runtime"]["path"]).resolve()
    registry_path=(root/manifest["subject"]["bound_capability_registry"]["path"]).resolve()

    astra_blob=file_blob(astra_path)
    registry_blob=file_blob(registry_path)
    if astra_blob!=manifest["subject"]["astra_runtime"]["git_blob_sha"]:
        raise RegistryError("ASTRA_RUNTIME_BLOB_DRIFT")
    if registry_blob!=manifest["subject"]["bound_capability_registry"]["git_blob_sha"]:
        raise RegistryError("BOUND_CAPABILITY_REGISTRY_BLOB_DRIFT")

    tree=ast.parse(astra_path.read_text(encoding="utf-8"),filename=str(astra_path))
    helper_modules=_runtime_helper_calls(tree)
    spec_count=_spec_loader_count(tree)

    expected_helpers=sorted(manifest["expected_repo_dynamic_universe"]["literal_runtime_helpers"])
    if helper_modules!=expected_helpers:
        raise RegistryError("RUNTIME_HELPER_SET_DRIFT")
    if spec_count!=manifest["expected_repo_dynamic_universe"]["spec_from_file_location_call_count"]:
        raise RegistryError("SPEC_LOADER_CALL_COUNT_DRIFT")

    registry=json.loads(registry_path.read_text(encoding="utf-8"))
    caps=registry.get("capabilities")
    if not isinstance(caps,dict):
        raise RegistryError("CAPABILITY_REGISTRY_INVALID")

    adapter_modules=set()
    source_types=set()
    nondefault_entrypoints=[]
    for cid,entry in sorted(caps.items()):
        if not isinstance(entry,dict):
            raise RegistryError("CAPABILITY_ENTRY_INVALID:"+str(cid))
        module=_safe_module(entry.get("adapter_module"),"ADAPTER_MODULE")
        adapter_modules.add(module)
        ep=str(entry.get("entrypoint") or "run")
        if ep!="run":
            nondefault_entrypoints.append({"capability_id":cid,"entrypoint":ep})
        source=entry.get("source") or {}
        if source.get("type"):
            source_types.add(str(source["type"]))

    adapters=sorted(adapter_modules)
    if adapters!=sorted(manifest["expected_repo_dynamic_universe"]["bound_adapter_modules"]):
        raise RegistryError("BOUND_ADAPTER_SET_DRIFT")
    if nondefault_entrypoints:
        raise RegistryError("NONDEFAULT_BOUND_ENTRYPOINTS_PRESENT")

    paths=set(manifest["expected_repo_dynamic_universe"]["fixed_repo_loader_paths"])
    paths.update("canonical/runtime/"+x+".py" for x in helper_modules)
    paths.update("canonical/runtime/bound_capabilities/"+x+".py" for x in adapters)

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
        if x not in {"python_stdlib"}
    )

    return {
        "schema":SCHEMA,
        "status":"REPO_DYNAMIC_MODULE_UNIVERSE_CLOSED__C1_OVERALL_OPEN_ON_NONREPO_EFFECT_TOTALITY",
        "astra_runtime_git_blob_sha":astra_blob,
        "bound_capability_registry_git_blob_sha":registry_blob,
        "spec_from_file_location_call_count":spec_count,
        "literal_runtime_helpers":helper_modules,
        "bound_capability_count":len(caps),
        "bound_adapter_module_count":len(adapters),
        "registered_repo_module_count":len(content_addressed),
        "registered_repo_modules":content_addressed,
        "bound_source_types":sorted(source_types),
        "nonrepo_dependency_source_types":nonrepo,
        "repo_dynamic_module_universe_closed":True,
        "third_party_dependency_effect_totality_proved":False,
        "native_extension_effect_totality_proved":False,
        "child_process_effect_totality_proved":False,
        "c1_channel_registry_scope_complete":False,
        "remaining_c1_residuals":[
            "NONREPO_DEPENDENCY_EFFECT_SURFACE",
            "NATIVE_EXTENSION_INTERNAL_EFFECTS",
            "CHILD_PROCESS_INTERNAL_EFFECTS",
            "EXTERNAL_TOOL_BRIDGE_OTHER_PROCESS_EFFECTS",
        ],
        "hard_nonclaims":[
            "NO_CLAIM_REPOSITORY_WIDE_EFFECT_TOTALITY",
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
        default="canonical/governance/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V1.json",
    )
    ns=ap.parse_args()
    print(json.dumps(compile_registry(ns.repo_root,ns.manifest),indent=2,sort_keys=True))
