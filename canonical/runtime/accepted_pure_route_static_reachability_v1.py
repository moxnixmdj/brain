from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROUTES = {
    "accepted.delegation": {
        "path": "canonical/runtime/delegation_whole_scope_candidate_v2.py",
        "git_blob_sha": "f1a93ee66d90093de61dc17c6ebf2e24073df522",
        "scope": "ENTIRE_MODULE",
    },
    "accepted.recovery": {
        "path": "canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py",
        "git_blob_sha": "28940387bd6c11671035ad9201e37bba13fd9bc9",
        "scope": "ENTIRE_MODULE",
    },
    "accepted.tool_discovery": {
        "path": "canonical/runtime/tool_discovery_information_safe_candidate.py",
        "git_blob_sha": "64c02edd568d95ec5ed54b7b8122183ce5b82e17",
        "scope": "ENTIRE_MODULE",
    },
    "accepted.exact_symbolic": {
        "path": "canonical/obsolescence/run_exact_symbolic_v1.py",
        "git_blob_sha": "8f6f04fee00664b26ddf1a45a65698399c7ca6c3",
        "scope": "SELECTED_ENTRY",
        "entry": "run_task",
    },
}
UNSAFE_IMPORT_ROOTS = {
    "subprocess", "socket", "requests", "urllib", "http", "ctypes",
    "multiprocessing", "shutil", "ftplib", "telnetlib",
}
FORBIDDEN_CALL_EXACT = {
    "open", "os.open", "os.remove", "os.unlink", "os.rename", "os.replace",
    "os.mkdir", "os.makedirs", "os.rmdir", "os.removedirs", "os.system",
    "subprocess.run", "subprocess.Popen", "subprocess.call",
    "subprocess.check_call", "subprocess.check_output",
    "socket.connect", "socket.bind", "socket.create_connection",
    "importlib.import_module", "__import__", "eval", "exec",
}
FORBIDDEN_ATTR_SUFFIXES = {
    ".write_text", ".write_bytes", ".unlink", ".rename", ".replace",
    ".mkdir", ".rmdir", ".chmod", ".chown", ".symlink", ".link",
    ".connect", ".bind",
}
FORBIDDEN_PREFIXES = (
    "requests.", "urllib.request.", "http.client.", "ctypes.",
    "os.exec", "os.spawn",
)

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def dotted(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = dotted(node.value)
        return (left + "." + node.attr) if left else node.attr
    return None

def imported_roots(tree: ast.AST) -> set[str]:
    out=set()
    for n in tree.body:
        if isinstance(n, ast.Import):
            out.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module:
            out.add(n.module.split(".")[0])
    return out

def forbidden_call(name: str) -> bool:
    if name in FORBIDDEN_CALL_EXACT:
        return True
    if any(name.endswith(s) for s in FORBIDDEN_ATTR_SUFFIXES):
        return True
    if any(name.startswith(p) for p in FORBIDDEN_PREFIXES):
        return True
    return False

def function_defs(tree: ast.AST) -> dict[str, ast.AST]:
    return {
        n.name:n for n in tree.body
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))
    }

def reachable_functions(tree: ast.AST, entry: str) -> tuple[set[str], list[str]]:
    defs=function_defs(tree)
    if entry not in defs:
        return set(), ["ENTRY_MISSING:"+entry]
    seen=set()
    stack=[entry]
    errors=[]
    while stack:
        name=stack.pop()
        if name in seen:
            continue
        seen.add(name)
        fn=defs[name]
        for n in ast.walk(fn):
            if not isinstance(n,ast.Call):
                continue
            call=dotted(n.func)
            if call and forbidden_call(call):
                errors.append("MATERIAL_CALL:"+name+":"+call)
            if isinstance(n.func,ast.Name) and n.func.id in defs and n.func.id not in seen:
                stack.append(n.func.id)
    return seen,errors

def scan_entire_module(tree: ast.AST) -> list[str]:
    errors=[]
    unsafe=sorted(imported_roots(tree) & UNSAFE_IMPORT_ROOTS)
    if unsafe:
        errors.append("UNSAFE_IMPORT_ROOTS:"+",".join(unsafe))
    for n in ast.walk(tree):
        if isinstance(n,ast.Call):
            call=dotted(n.func)
            if call and forbidden_call(call):
                errors.append("MATERIAL_CALL:"+call)
    return sorted(set(errors))

def evaluate(root: Path = ROOT) -> dict:
    results={}
    errors=[]
    for route_id,spec in ROUTES.items():
        path=root/spec["path"]
        data=path.read_bytes()
        sha=git_blob_sha(data)
        route_errors=[]
        if sha != spec["git_blob_sha"]:
            route_errors.append("BLOB_DRIFT:"+sha)
        tree=ast.parse(data.decode("utf-8"),filename=spec["path"])
        if spec["scope"]=="ENTIRE_MODULE":
            route_errors.extend(scan_entire_module(tree))
            reachable="ALL_FUNCTIONS_AND_TOP_LEVEL"
        else:
            unsafe=sorted(imported_roots(tree) & UNSAFE_IMPORT_ROOTS)
            if unsafe:
                route_errors.append("UNSAFE_IMPORT_ROOTS:"+",".join(unsafe))
            reachable,reach_errors=reachable_functions(tree,spec["entry"])
            route_errors.extend(reach_errors)
            reachable=sorted(reachable)
        results[route_id]={
            "path":spec["path"],
            "git_blob_sha":sha,
            "scope":spec["scope"],
            "selected_entry":spec.get("entry"),
            "reachable_local_functions":reachable,
            "material_effect_ids":[],
            "errors":route_errors,
            "pass":not route_errors,
        }
        errors.extend(route_id+":"+e for e in route_errors)
    return {
        "schema":"PROJECT_BRAIN_ACCEPTED_PURE_ROUTE_STATIC_REACHABILITY_V1",
        "status":"PASS__FOUR_ACCEPTED_SELECTED_ROUTES_STATICALLY_EFFECT_FREE" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "errors":errors,
        "routes":results,
        "material_effect_ids":[],
        "scope_rule":"ENTIRE_MODULE_FOR_DELEGATION_RECOVERY_TOOL_DISCOVERY__TRANSITIVE_LOCAL_CALL_CLOSURE_FROM_RUN_TASK_FOR_EXACT_SYMBOLIC",
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
