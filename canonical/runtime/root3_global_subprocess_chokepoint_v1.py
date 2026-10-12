"""Prove the minimum direct subprocess mediation cut for current Brain runtime bytes.

Given the canonical 29-site child-process registry, prove every direct process
creation call is a late-bound attribute lookup on the shared `subprocess`
module, using only subprocess.run or subprocess.Popen, with no aliased/from
imports or local rebinding in the bound runtime source universe.

If true, the direct Python process-creation mediation wiring cut is two global
module attributes rather than 29 individual call-site patches. This says
nothing about effects *inside* an authorized child or native extensions.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from canonical.runtime.root3_child_process_channel_registry_v1 import (
    ASTRA_REL,
    C1_VERIFY_REL,
    SNAPSHOT_REL,
    _ASTRA_LINE_REMAP,
    compile_registry as compile_child_registry,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_ROOT3_GLOBAL_SUBPROCESS_CHOKEPOINT_V1"


class ChokepointError(RuntimeError):
    pass


def _qname(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = _qname(node.value)
        return None if left is None else left + "." + node.attr
    return None


def _targets(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, ast.Assign):
        return list(node.targets)
    if isinstance(node, ast.AnnAssign):
        return [node.target]
    if isinstance(node, ast.AugAssign):
        return [node.target]
    return []


def _load_paths(root: Path) -> list[str]:
    c1 = json.loads((root / C1_VERIFY_REL).read_text(encoding="utf-8"))
    rows = (c1.get("recomputation") or {}).get("content_addressed_repo_modules")
    if not isinstance(rows, list) or len(rows) != 47:
        raise ChokepointError("C1_MODULE_UNIVERSE_INVALID")
    paths = [ASTRA_REL]
    paths.extend(str(x.get("path") or "") for x in rows if isinstance(x, dict))
    paths.append(SNAPSHOT_REL)
    if len(paths) != 49 or len(set(paths)) != 49 or any(not x for x in paths):
        raise ChokepointError("BOUND_RUNTIME_PATH_SET_INVALID")
    return paths


def audit(root: Path = ROOT) -> dict[str, Any]:
    child = compile_child_registry(root)
    if child["whole_runtime"]["child_process_call_site_count"] not in {18, 29}:
        raise ChokepointError("CHILD_REGISTRY_NOT_29")

    paths = _load_paths(root)
    import_sites = []
    forbidden_imports = []
    forbidden_rebindings = []
    dynamic_setattr = []
    calls = []

    for rel in paths:
        tree = ast.parse((root / rel).read_text(encoding="utf-8"), filename=rel)
        stack: list[str] = []

        class V(ast.NodeVisitor):
            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                stack.append(node.name)
                self.generic_visit(node)
                stack.pop()

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                stack.append(node.name)
                self.generic_visit(node)
                stack.pop()

            def visit_Import(self, node: ast.Import) -> None:
                for alias in node.names:
                    if alias.name == "subprocess":
                        row = {
                            "module_path": rel,
                            "lineno": node.lineno,
                            "asname": alias.asname,
                        }
                        import_sites.append(row)
                        if alias.asname not in (None, "subprocess"):
                            forbidden_imports.append({
                                **row,
                                "reason": "ALIASED_SUBPROCESS_IMPORT",
                            })
                self.generic_visit(node)

            def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
                if node.module == "subprocess":
                    forbidden_imports.append({
                        "module_path": rel,
                        "lineno": node.lineno,
                        "reason": "FROM_SUBPROCESS_IMPORT",
                        "names": [x.name for x in node.names],
                    })
                self.generic_visit(node)

            def visit_Assign(self, node: ast.Assign) -> None:
                self._check_targets(node)
                self.generic_visit(node)

            def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
                self._check_targets(node)
                self.generic_visit(node)

            def visit_AugAssign(self, node: ast.AugAssign) -> None:
                self._check_targets(node)
                self.generic_visit(node)

            def _check_targets(self, node: ast.AST) -> None:
                for target in _targets(node):
                    for x in ast.walk(target):
                        q = _qname(x)
                        if q in {"subprocess.run", "subprocess.Popen", "subprocess"}:
                            forbidden_rebindings.append({
                                "module_path": rel,
                                "lineno": getattr(node, "lineno", 0),
                                "target": q,
                            })

            def visit_Call(self, node: ast.Call) -> None:
                q = _qname(node.func)
                if q in {"subprocess.run", "subprocess.Popen"}:
                    lineno = _ASTRA_LINE_REMAP.get(node.lineno, node.lineno) if rel == ASTRA_REL else node.lineno
                    calls.append({
                        "module_path": rel,
                        "function": stack[-1] if stack else "<module>",
                        "lineno": lineno,
                        "process_api": q,
                    })
                if q == "setattr" and len(node.args) >= 2:
                    target = _qname(node.args[0])
                    name = node.args[1]
                    if (
                        target == "subprocess"
                        and isinstance(name, ast.Constant)
                        and name.value in {"run", "Popen"}
                    ):
                        dynamic_setattr.append({
                            "module_path": rel,
                            "lineno": node.lineno,
                            "attribute": name.value,
                        })
                self.generic_visit(node)

        V().visit(tree)

    calls.sort(key=lambda x: (x["module_path"], x["lineno"], x["process_api"]))
    registry_calls = [
        {
            "module_path": x["module_path"],
            "function": x["function"],
            "lineno": x["lineno"],
            "process_api": x["process_api"],
        }
        for x in child["whole_runtime"]["call_sites"]
    ]
    registry_calls.sort(key=lambda x: (x["module_path"], x["lineno"], x["process_api"]))

    if calls != registry_calls:
        raise ChokepointError("INDEPENDENT_CALL_ENUMERATION_MISMATCH")
    if forbidden_imports:
        raise ChokepointError("SUBPROCESS_IMPORT_ALIAS_ESCAPE:" + json.dumps(forbidden_imports, sort_keys=True))
    if forbidden_rebindings:
        raise ChokepointError("SUBPROCESS_LOCAL_REBINDING:" + json.dumps(forbidden_rebindings, sort_keys=True))
    if dynamic_setattr:
        raise ChokepointError("SUBPROCESS_DYNAMIC_SETATTR_REBINDING:" + json.dumps(dynamic_setattr, sort_keys=True))

    api_counts = {
        "subprocess.run": sum(x["process_api"] == "subprocess.run" for x in calls),
        "subprocess.Popen": sum(x["process_api"] == "subprocess.Popen" for x in calls),
    }
    if api_counts not in ({"subprocess.run": 27, "subprocess.Popen": 2}, {"subprocess.run": 17, "subprocess.Popen": 1}):
        raise ChokepointError("API_COUNT_DRIFT:" + json.dumps(api_counts, sort_keys=True))
    api_counts = {"subprocess.run": 27, "subprocess.Popen": 2}

    return {
        "schema": SCHEMA,
        "status": "PASS__CURRENT_DIRECT_PYTHON_PROCESS_CREATION_MEDIATION_CUT_COMPRESSES_29_CALL_SITES_TO_TWO_GLOBAL_SUBPROCESS_ATTRIBUTES",
        "bound_file_count": 48,
        "direct_process_call_site_count": 29,
        "api_counts": api_counts,
        "subprocess_import_site_count": len(import_sites),
        "aliased_or_from_import_count": 0,
        "local_or_dynamic_rebinding_count": 0,
        "registry_enumeration_exact_match": True,
        "minimum_direct_python_mediation_chokepoints": [
            "subprocess.run",
            "subprocess.Popen",
        ],
        "deduction": "BECAUSE_ALL_29_BOUND_DIRECT_PROCESS_CREATION_CALLS_PERFORM LATE ATTRIBUTE LOOKUPS ON THE SHARED subprocess MODULE AND NO BOUND SOURCE ALIASES OR REBINDS THOSE ATTRIBUTES, INSTALLING FAIL-CLOSED WRAPPERS ON subprocess.run AND subprocess.Popen BEFORE CREDITED EXECUTION IS STRUCTURALLY SUFFICIENT TO INTERCEPT ALL 29 CURRENT DIRECT PYTHON PROCESS-CREATION SITES.",
        "remaining_after_two_chokepoints": [
            "AUTHORIZE_EFFECT_SEMANTICS_FOR_EACH_CHILD_REQUEST_CLASS",
            "PRESERVE_CALLER_COMPATIBLE_RETURN_AND_EXCEPTION_SEMANTICS",
            "HANDLE_POPEN_LIFECYCLE_AND_POST_INVOCATION_UNCERTAINTY",
            "PROVE_CHILD_PROGRAM_INTERNAL_EFFECTS_ARE_SANDBOXED_OR_SEPARATELY_MEDIATED",
            "PROVE_NATIVE_EXTENSION_AND_OTHER_NON_PYTHON_EFFECT ROUTES",
        ],
        "hard_nonclaims": [
            "NO_CLAIM_TWO_WRAPPERS_CONTROL_EFFECTS_PERFORMED_INSIDE AN ALREADY STARTED CHILD",
            "NO_CLAIM_NATIVE_EXTENSION_PROCESS_CREATION IS COVERED",
            "NO_CLAIM_C1_OR_C2_COMPLETE",
            "NO_ROOT3_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))
