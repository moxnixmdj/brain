"""Static Root3 census for the external-tool information bridge.

This compiler proves only the repository-side request interface:
* every _external_tool_bridge call uses a literal kind;
* the kind set is frozen;
* the current urlopen bridge rejects non-GET or body-bearing requests before
  either the bridge or raw urllib fallback can execute.

It does not prove the internal behavior of an independently running external
bridge process.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_ROOT3_EXTERNAL_BRIDGE_INFO_ONLY_OUTPUT_V1"
EXPECTED_KINDS={
    "http_get",
    "urlopen",
    "planner",
    "package_name_search",
    "python_source_tree",
    "pypi_wheel_closure",
}


class BridgeSurfaceError(ValueError):
    pass


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()


def _qualified(node: ast.AST) -> str | None:
    if isinstance(node,ast.Name):
        return node.id
    if isinstance(node,ast.Attribute):
        p=_qualified(node.value)
        return None if p is None else p+"."+node.attr
    return None


def compile_surface(repo_root: str | Path, expected_astra_blob: str) -> dict[str,Any]:
    root=Path(repo_root).resolve()
    p=root/"canonical/runtime/astra_runtime.py"
    raw=p.read_bytes()
    blob=git_blob_sha(raw)
    if blob!=expected_astra_blob:
        raise BridgeSurfaceError("ASTRA_BLOB_DRIFT")

    source=raw.decode("utf-8")
    tree=ast.parse(source,filename=str(p))
    kinds=[]
    nonliteral=[]
    for node in ast.walk(tree):
        if not isinstance(node,ast.Call):
            continue
        if _qualified(node.func)!="_external_tool_bridge":
            continue
        if not node.args:
            nonliteral.append(getattr(node,"lineno",0))
            continue
        first=node.args[0]
        if not isinstance(first,ast.Constant) or not isinstance(first.value,str):
            nonliteral.append(getattr(node,"lineno",0))
            continue
        kinds.append(first.value)

    if nonliteral:
        raise BridgeSurfaceError("NONLITERAL_BRIDGE_KIND:"+",".join(map(str,nonliteral)))
    if set(kinds)!=EXPECTED_KINDS:
        raise BridgeSurfaceError("BRIDGE_KIND_SET_DRIFT:"+repr(sorted(set(kinds))))

    guard='if method != "GET" or data is not None:'
    denial='EXTERNAL_URLOPEN_INFORMATION_ONLY_METHOD_FORBIDDEN'
    if guard not in source or denial not in source:
        raise BridgeSurfaceError("URLOPEN_INFORMATION_ONLY_GUARD_MISSING")

    auth_start=source.find("def _authorize_external_information")
    auth_end=source.find("\ndef ",auth_start+5)
    auth=source[auth_start:auth_end if auth_end!=-1 else len(source)]
    for kind in EXPECTED_KINDS:
        if repr(kind) not in auth and ('"'+kind+'"') not in auth:
            raise BridgeSurfaceError("AUTHORIZATION_KIND_NOT_BOUND:"+kind)

    return {
        "schema":SCHEMA,
        "status":"REPOSITORY_BRIDGE_REQUEST_INTERFACE_INFORMATION_ONLY__EXTERNAL_PROCESS_INTERNAL_EFFECTS_STILL_OPEN",
        "astra_runtime_git_blob_sha":blob,
        "bridge_call_count":len(kinds),
        "bridge_kinds":sorted(set(kinds)),
        "all_bridge_kinds_literal":True,
        "urlopen_bodyless_get_only":True,
        "mutating_urlopen_request_rejected_before_transport":True,
        "external_process_internal_effect_totality_proved":False,
        "c1_external_bridge_scope_complete":False,
        "remaining_residual":"INDEPENDENT_EXTERNAL_BRIDGE_PROCESS_INTERNAL_EFFECTS_OR_EXPLICIT_TRUST_BOUNDARY",
        "hard_nonclaims":[
            "NO_CLAIM_EXTERNAL_BRIDGE_PROCESS_INTERNAL_EFFECTS_ARE_MEDIATED",
            "NO_CLAIM_FULL_C1_SCOPE_COMPLETENESS",
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
    ap.add_argument("--astra-blob",required=True)
    ns=ap.parse_args()
    print(json.dumps(compile_surface(ns.repo_root,ns.astra_blob),indent=2,sort_keys=True))
