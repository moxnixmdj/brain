"""Content-addressed child-process census for the current Root3 C1 execution universe.

This proves only that process-spawn call sites inside the exact registered
repository execution universe are finite and enumerable. It does not claim
anything about the internal effects of the spawned programs.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_ROOT3_CHILD_PROCESS_CENSUS_OUTPUT_V1"
C1_SCHEMA="PROJECT_BRAIN_ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V2"

PROCESS_APIS={
    "subprocess.run","subprocess.Popen","subprocess.call",
    "subprocess.check_call","subprocess.check_output",
    "os.system","os.popen",
    "os.spawnl","os.spawnle","os.spawnlp","os.spawnlpe",
    "os.spawnv","os.spawnve","os.spawnvp","os.spawnvpe",
    "multiprocessing.Process",
    "asyncio.create_subprocess_exec","asyncio.create_subprocess_shell",
}


class CensusError(ValueError):
    pass


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()


def _qname(node: ast.AST) -> str | None:
    if isinstance(node,ast.Name):
        return node.id
    if isinstance(node,ast.Attribute):
        p=_qname(node.value)
        return None if p is None else p+"."+node.attr
    return None


def _imports(tree: ast.Module) -> dict[str,str]:
    aliases={}
    for n in tree.body:
        if isinstance(n,ast.Import):
            for a in n.names:
                aliases[a.asname or a.name.split(".")[0]]=a.name
        elif isinstance(n,ast.ImportFrom) and n.module:
            for a in n.names:
                if a.name=="*":
                    continue
                aliases[a.asname or a.name]=n.module+"."+a.name
    return aliases


def _canonical_call(node: ast.Call, aliases: dict[str,str]) -> str | None:
    q=_qname(node.func)
    if q is None:
        return None
    head=q.split(".",1)[0]
    if head in aliases:
        mapped=aliases[head]
        rest=q[len(head):]
        return mapped+rest
    return q


class Visitor(ast.NodeVisitor):
    def __init__(self,aliases: dict[str,str]):
        self.aliases=aliases
        self.stack=[]
        self.rows=[]

    def visit_FunctionDef(self,node: ast.FunctionDef):
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self,node: ast.AsyncFunctionDef):
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_Call(self,node: ast.Call):
        q=_canonical_call(node,self.aliases)
        if q in PROCESS_APIS:
            shell=False
            for kw in node.keywords:
                if kw.arg=="shell" and isinstance(kw.value,ast.Constant):
                    shell=bool(kw.value.value)
            arg0=ast.unparse(node.args[0]) if node.args else None
            self.rows.append({
                "line":int(getattr(node,"lineno",0)),
                "function":self.stack[-1] if self.stack else "<module>",
                "api":q,
                "first_argument_expression":arg0,
                "shell_true":shell,
            })
        self.generic_visit(node)


def _execution_paths(manifest: dict[str,Any]) -> list[str]:
    u=manifest["expected_repo_dynamic_universe"]
    paths={"canonical/runtime/astra_runtime.py"}
    paths.update(str(x) for x in u["fixed_loader_sites"].values())
    paths.update("canonical/runtime/"+str(x)+".py" for x in u["literal_runtime_helpers"])
    paths.update(
        "canonical/runtime/bound_capabilities/"+str(x)+".py"
        for x in u["ordinary_adapter_modules"]
    )
    return sorted(paths)


def compile_census(repo_root: str | Path, manifest_path: str | Path) -> dict[str,Any]:
    root=Path(repo_root).resolve()
    mp=(root/manifest_path).resolve()
    manifest=json.loads(mp.read_text(encoding="utf-8"))
    if manifest.get("schema")!=C1_SCHEMA:
        raise CensusError("C1_MANIFEST_SCHEMA_INVALID")

    paths=_execution_paths(manifest)
    modules=[]
    sites=[]
    missing=[]
    for rel in paths:
        p=(root/rel).resolve()
        if not p.is_file():
            missing.append(rel)
            continue
        raw=p.read_bytes()
        try:
            tree=ast.parse(raw.decode("utf-8"),filename=str(p))
        except Exception as exc:
            raise CensusError("PARSE_FAILED:"+rel+":"+type(exc).__name__) from exc
        v=Visitor(_imports(tree))
        v.visit(tree)
        blob=git_blob_sha(raw)
        modules.append({"path":rel,"git_blob_sha":blob,"spawn_site_count":len(v.rows)})
        for row in v.rows:
            sites.append({"path":rel,**row})
    if missing:
        raise CensusError("REGISTERED_EXECUTION_MODULE_MISSING:"+",".join(missing))

    sites=sorted(sites,key=lambda x:(x["path"],x["line"],x["api"]))
    return {
        "schema":SCHEMA,
        "status":"CURRENT_REGISTERED_CHILD_PROCESS_SPAWN_UNIVERSE_FINITE__CHILD_INTERNAL_EFFECTS_STILL_OPEN",
        "registered_execution_module_count":len(modules),
        "spawn_site_count":len(sites),
        "spawn_apis":sorted(set(x["api"] for x in sites)),
        "shell_true_site_count":sum(1 for x in sites if x["shell_true"]),
        "modules":modules,
        "spawn_sites":sites,
        "registered_execution_universe_fully_parsed":True,
        "child_process_internal_effect_totality_proved":False,
        "c1_child_process_scope_complete":False,
        "remaining_residual":"ROUTE_OR_SANDBOX_EACH_CONTENT_ADDRESSED_SPAWN_SITE_THROUGH_A_TRUTH_PRESERVING_EFFECT_CARRIER",
        "hard_nonclaims":[
            "NO_CLAIM_CHILD_PROCESS_INTERNAL_EFFECTS_ARE_MEDIATED",
            "NO_CLAIM_PROCESS_ARGUMENTS_ARE_ALL_STATIC",
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
    ap.add_argument(
        "--manifest",
        default="canonical/governance/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_CANDIDATE_V2.json",
    )
    ns=ap.parse_args()
    print(json.dumps(compile_census(ns.repo_root,ns.manifest),indent=2,sort_keys=True))
