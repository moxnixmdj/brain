"""Transitive local call-graph effect compiler for Astra goal actions.

Candidate-only proof support. This compiler recursively follows top-level local
function calls reachable from each _goal_action branch and classifies ambient
effect sinks. It fails closed on unresolved dynamic call targets.

It does NOT prove third-party/library purity, runtime enforcement, semantic
completeness, or universal no-bypass by itself.
"""
from __future__ import annotations

import ast
import hashlib
import pathlib
from typing import Any

SCHEMA = "PROJECT_BRAIN_GOAL_ACTION_TRANSITIVE_EFFECT_COMPILER_V1"
ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNTIME_REL = "canonical/runtime/astra_runtime.py"
EXPECTED_RUNTIME_BLOB = "b7efc08e64a483e9a759c181a4f9a1cf29e47a9a"

SAFE_BUILTINS = {
    "abs","all","any","bool","bytes","dict","enumerate","float","int","isinstance",
    "len","list","max","min","range","repr","reversed","round","set","sorted","str",
    "sum","tuple","zip",
}
SAFE_MODULE_PREFIXES = {
    "base64","hashlib","html","json","re","shlex","urllib.parse",
}
SAFE_METHODS = {
    "append","clear","copy","decode","encode","endswith","extend","get","items",
    "join","keys","lower","lstrip","pop","replace","rsplit","setdefault","sort",
    "split","startswith","strip","update","upper","values",
}
SINK_CALLS = {
    "subprocess.run": "PROCESS",
    "subprocess.Popen": "PROCESS",
    "subprocess.check_call": "PROCESS",
    "subprocess.check_output": "PROCESS",
    "os.system": "PROCESS",
    "os.fork": "PROCESS",
    "urllib.request.urlopen": "NETWORK_OR_EXTERNAL",
}
LOCAL_GATEWAY_CALLS = {
    "_external_tool_bridge": "NETWORK_OR_EXTERNAL",
    "run_http": "NETWORK_OR_EXTERNAL",
    "_invoke_bound_capability": "BOUND_CAPABILITY_DYNAMIC",
    "_ensure_pypi_dependency": "PACKAGE_INSTALL",
    "_ensure_npm_dependency": "PACKAGE_INSTALL",
    "_ensure_apt_dependencies": "PACKAGE_INSTALL",
    "_ensure_git_source_tree_dependency": "PACKAGE_INSTALL",
}
PATH_READ_METHODS = {
    "read_text","read_bytes","rglob","glob","exists","is_file","is_dir","iterdir",
}
PATH_WRITE_METHODS = {
    "write_text","write_bytes","mkdir","unlink","rename","replace","touch",
}
SHUTIL_WRITES = {
    "shutil.copy","shutil.copy2","shutil.move","shutil.rmtree","shutil.copytree",
}

def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()

def _qualname(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _qualname(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None

def _goal_action_branches(tree: ast.Module) -> dict[str, list[ast.stmt]]:
    fn = next(
        (n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
         and n.name == "_goal_action"),
        None,
    )
    if fn is None:
        raise ValueError("GOAL_ACTION_FUNCTION_MISSING")
    out: dict[str, list[ast.stmt]] = {}
    for stmt in fn.body:
        if not isinstance(stmt, ast.If):
            continue
        test = stmt.test
        if not isinstance(test, ast.Compare) or len(test.ops) != 1 or len(test.comparators) != 1:
            continue
        left, right = test.left, test.comparators[0]
        if not isinstance(test.ops[0], ast.Eq):
            continue
        if isinstance(left, ast.Name) and left.id == "typ" and isinstance(right, ast.Constant) and isinstance(right.value, str):
            action_type = right.value
        elif isinstance(right, ast.Name) and right.id == "typ" and isinstance(left, ast.Constant) and isinstance(left.value, str):
            action_type = left.value
        else:
            continue
        if action_type in out:
            raise ValueError("DUPLICATE_ACTION_TYPE:" + action_type)
        out[action_type] = stmt.body
    if not out:
        raise ValueError("NO_ACTION_BRANCHES_FOUND")
    return out

def _top_level_functions(tree: ast.Module) -> dict[str, ast.AST]:
    return {
        n.name: n
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

class _EffectVisitor(ast.NodeVisitor):
    def __init__(self, local_functions: set[str]) -> None:
        self.local_functions = local_functions
        self.local_calls: set[str] = set()
        self.channels: set[str] = set()
        self.unresolved_calls: set[str] = set()

    def visit_Call(self, node: ast.Call) -> Any:
        q = _qualname(node.func)
        if q in SINK_CALLS:
            self.channels.add(SINK_CALLS[q])
        elif q in LOCAL_GATEWAY_CALLS:
            self.channels.add(LOCAL_GATEWAY_CALLS[q])
            if q in self.local_functions:
                self.local_calls.add(q)
        elif q in self.local_functions:
            self.local_calls.add(q)
        elif q in SHUTIL_WRITES:
            self.channels.add("HOST_WRITE")
        elif isinstance(node.func, ast.Attribute):
            method = node.func.attr
            if method in PATH_READ_METHODS:
                self.channels.add("HOST_READ")
            elif method in PATH_WRITE_METHODS:
                self.channels.add("HOST_WRITE")
            elif method in SAFE_METHODS:
                pass
            elif q and any(q == p or q.startswith(p + ".") for p in SAFE_MODULE_PREFIXES):
                pass
            else:
                self.unresolved_calls.add(q or "<dynamic_attribute_call>")
        elif isinstance(node.func, ast.Name):
            if node.func.id in SAFE_BUILTINS:
                pass
            else:
                self.unresolved_calls.add(node.func.id)
        else:
            self.unresolved_calls.add("<dynamic_call_target>")
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        q = _qualname(node.value)
        if q == "os.environ":
            self.channels.add("HOST_ENV")
        self.generic_visit(node)

def _summarize_nodes(nodes: list[ast.stmt], local_functions: dict[str, ast.AST]) -> dict[str, Any]:
    pending: list[tuple[str, list[ast.stmt]]] = [("<action>", nodes)]
    seen: set[str] = set()
    channels: set[str] = set()
    unresolved: set[str] = set()
    traversed: list[str] = []
    while pending:
        name, body = pending.pop()
        if name != "<action>":
            if name in seen:
                continue
            seen.add(name)
            traversed.append(name)
        visitor = _EffectVisitor(set(local_functions))
        for node in body:
            visitor.visit(node)
        channels.update(visitor.channels)
        unresolved.update(visitor.unresolved_calls)
        for callee in sorted(visitor.local_calls):
            fn = local_functions.get(callee)
            if fn is not None and callee not in seen:
                pending.append((callee, list(fn.body)))
    return {
        "channels": sorted(channels),
        "unresolved_calls": sorted(unresolved),
        "traversed_local_functions": sorted(traversed),
        "transitively_closed_over_local_functions": not unresolved,
    }

def compile_effects(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    functions = _top_level_functions(tree)
    branches = _goal_action_branches(tree)
    rows = []
    for action_type, body in branches.items():
        summary = _summarize_nodes(body, functions)
        rows.append({
            "action_type": action_type,
            **summary,
            "status": (
                "LOCAL_TRANSITIVE_CLOSED"
                if summary["transitively_closed_over_local_functions"]
                else "OPEN_UNRESOLVED_CALLS"
            ),
        })
    counts: dict[str, int] = {}
    for row in rows:
        for channel in row["channels"]:
            counts[channel] = counts.get(channel, 0) + 1
    closed = [r for r in rows if r["status"] == "LOCAL_TRANSITIVE_CLOSED"]
    open_rows = [r for r in rows if r["status"] != "LOCAL_TRANSITIVE_CLOSED"]
    return {
        "schema": SCHEMA,
        "status": "PASS__LOCAL_TRANSITIVE_EFFECT_SURFACE_COMPILED",
        "action_count": len(rows),
        "local_transitive_closed_count": len(closed),
        "open_unresolved_call_count": len(open_rows),
        "channel_counts": counts,
        "rows": rows,
        "scope": "LOCAL_TOP_LEVEL_FUNCTION_CALL_GRAPH_ONLY",
        "hard_nonclaims": [
            "NO_THIRD_PARTY_OR_STDLIB_SEMANTIC_PURITY_PROOF",
            "NO_RUNTIME_GATEWAY_ENFORCEMENT_PROOF",
            "NO_DYNAMIC_DISPATCH_TOTALITY_PROOF",
            "NO_UNIVERSAL_NO_BYPASS_CREDIT",
        ],
        "no_bypass_credit": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }

def evaluate(root: pathlib.Path = ROOT) -> dict[str, Any]:
    path = root / RUNTIME_REL
    if not path.is_file():
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__RUNTIME_MISSING",
            "errors": ["RUNTIME_MISSING"],
            "acceptance_credit_delta": 0,
            "terminal_credit_delta": 0,
        }
    raw = path.read_bytes()
    got = _git_blob_sha(raw)
    if got != EXPECTED_RUNTIME_BLOB:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__RUNTIME_BLOB_DRIFT",
            "errors": ["RUNTIME_BLOB_DRIFT:" + got],
            "expected_git_blob_sha": EXPECTED_RUNTIME_BLOB,
            "acceptance_credit_delta": 0,
            "terminal_credit_delta": 0,
        }
    out = compile_effects(raw.decode("utf-8"))
    out["runtime_path"] = RUNTIME_REL
    out["runtime_git_blob_sha"] = got
    return out

if __name__ == "__main__":
    import json
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
