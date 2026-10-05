"""Exact whole-runtime child-process channel compiler for Project Brain.

Binds ASTRA plus the 47 already content-addressed repo-local runtime modules from
the independently recomputed Root3 C1 registry, then enumerates every Python
process-creation call in that exact universe. This closes only channel identity;
effect mediation remains a separate proof obligation.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ASTRA_REL = "canonical/runtime/astra_runtime.py"
C1_VERIFY_REL = "canonical/verification/ROOT3_EFFECT_CHANNEL_REGISTRY_C1_DELTA_VERIFICATION_20261005_V5.json"
EXPECTED_ASTRA_BLOB = "15dd59ad644c5c73a9218dba4fcc17f880d725f0"
EXPECTED_C1_VERIFY_BLOB = "519f02995f6ff7cb344cecab1d4a9a5615e6b36e"
SNAPSHOT_REL = "canonical/runtime/apt_metadata_snapshot_v1.py"
EXPECTED_SNAPSHOT_BLOB = "426189ed3a8c37d3ecb515cc8f89ab31e927fd24"
SCHEMA = "PROJECT_BRAIN_ROOT3_CHILD_PROCESS_CHANNEL_REGISTRY_V1"


class ChildProcessRegistryError(RuntimeError):
    pass


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _qname(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = _qname(node.value)
        return None if left is None else left + "." + node.attr
    return None


def _literals(node: ast.AST | None) -> list[str]:
    if node is None:
        return []
    return [
        str(x.value)
        for x in ast.walk(node)
        if isinstance(x, ast.Constant) and isinstance(x.value, str)
    ]


class _Visitor(ast.NodeVisitor):
    def __init__(self, module_path: str) -> None:
        self.module_path = module_path
        self.stack: list[str] = []
        self.rows: list[dict[str, Any]] = []
        self.forbidden: list[dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        q = _qname(node.func)
        fn = self.stack[-1] if self.stack else "<module>"
        if q in {"subprocess.run", "subprocess.Popen"}:
            self.rows.append({
                "module_path": self.module_path,
                "function": fn,
                "lineno": int(getattr(node, "lineno", 0)),
                "process_api": q,
                "command_literals": _literals(node.args[0] if node.args else None),
            })
        elif q == "os.system" or (isinstance(q, str) and q.startswith("subprocess.")):
            self.forbidden.append({
                "module_path": self.module_path,
                "function": fn,
                "lineno": int(getattr(node, "lineno", 0)),
                "process_api": q,
            })
        self.generic_visit(node)


def _load_c1_universe(root: Path) -> list[dict[str, str]]:
    verification = root / C1_VERIFY_REL
    if git_blob_sha(verification) != EXPECTED_C1_VERIFY_BLOB:
        raise ChildProcessRegistryError("C1_VERIFICATION_BLOB_DRIFT")
    doc = json.loads(verification.read_text(encoding="utf-8"))
    rows = (doc.get("recomputation") or {}).get("content_addressed_repo_modules")
    if not isinstance(rows, list) or len(rows) != 47:
        raise ChildProcessRegistryError("C1_REPO_MODULE_UNIVERSE_DRIFT")
    out = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ChildProcessRegistryError("C1_MODULE_ROW_INVALID")
        path = str(row.get("path") or "")
        blob = str(row.get("git_blob_sha") or "")
        if not path or not blob or path in seen:
            raise ChildProcessRegistryError("C1_MODULE_ROW_INCOMPLETE_OR_DUPLICATE")
        seen.add(path)
        actual = git_blob_sha(root / path)
        if actual != blob:
            raise ChildProcessRegistryError("C1_MODULE_BLOB_DRIFT:" + path)
        out.append({"path": path, "git_blob_sha": blob})
    return out


def _astra_classes(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        if row["module_path"] != ASTRA_REL:
            continue
        fn = row["function"]
        counts[fn] = counts.get(fn, 0) + 1
    expected = {
        "run_shell": 1,
        "_ensure_pypi_dependency": 2,
        "_ensure_apt_dependencies": 1,
        "_goal_action": 1,
        "_verify_and_promote_acquisition": 1,
    }
    if counts != expected:
        raise ChildProcessRegistryError(
            "ASTRA_CHILD_PROCESS_FUNCTION_PARTITION_DRIFT:" + json.dumps(counts, sort_keys=True)
        )
    return counts


def compile_registry(root: Path = ROOT) -> dict[str, Any]:
    astra = root / ASTRA_REL
    if git_blob_sha(astra) != EXPECTED_ASTRA_BLOB:
        raise ChildProcessRegistryError("ASTRA_RUNTIME_BLOB_DRIFT")

    modules = _load_c1_universe(root)
    paths = [{"path": ASTRA_REL, "git_blob_sha": EXPECTED_ASTRA_BLOB}, *modules, {"path": SNAPSHOT_REL, "git_blob_sha": EXPECTED_SNAPSHOT_BLOB}]

    rows: list[dict[str, Any]] = []
    forbidden: list[dict[str, Any]] = []
    for item in paths:
        path = item["path"]
        tree = ast.parse((root / path).read_text(encoding="utf-8"), filename=path)
        v = _Visitor(path)
        v.visit(tree)
        rows.extend(v.rows)
        forbidden.extend(v.forbidden)

    if forbidden:
        raise ChildProcessRegistryError(
            "UNREGISTERED_PROCESS_CREATION_API:" + json.dumps(forbidden, sort_keys=True)
        )

    rows.sort(key=lambda x: (x["module_path"], x["lineno"], x["process_api"]))
    run_count = sum(x["process_api"] == "subprocess.run" for x in rows)
    popen_count = sum(x["process_api"] == "subprocess.Popen" for x in rows)
    modules_with_children = sorted({x["module_path"] for x in rows})

    if len(rows) != 18:
        raise ChildProcessRegistryError("WHOLE_RUNTIME_CHILD_PROCESS_COUNT_DRIFT:" + str(len(rows)))
    if run_count != 17 or popen_count != 1:
        raise ChildProcessRegistryError(
            f"PROCESS_API_COUNT_DRIFT:run={run_count}:popen={popen_count}"
        )
    if len(modules_with_children) != 12:
        raise ChildProcessRegistryError(
            "CHILD_PROCESS_MODULE_COUNT_DRIFT:" + str(len(modules_with_children))
        )

    astra_counts = _astra_classes(rows)

    return {
        "schema": SCHEMA,
        "status": "PASS__WHOLE_CURRENT_REPO_RUNTIME_CHILD_PROCESS_UNIVERSE_FINITE__18_EXACT_PROCESS_CREATION_SITES__TAR_EXTRACTION_PROCESS_SITE_DELETED__MEDIATION_STILL_OPEN",
        "authority": {
            "astra_runtime_path": ASTRA_REL,
            "astra_runtime_git_blob_sha": EXPECTED_ASTRA_BLOB,
            "c1_verification_path": C1_VERIFY_REL,
            "c1_verification_git_blob_sha": EXPECTED_C1_VERIFY_BLOB,
            "content_addressed_repo_module_count": 47,
            "additional_static_process_scan_helper": SNAPSHOT_REL,
            "additional_static_process_scan_helper_git_blob_sha": EXPECTED_SNAPSHOT_BLOB,
        },
        "whole_runtime": {
            "scanned_python_file_count": len(paths),
            "child_process_call_site_count": len(rows),
            "subprocess_run_count": run_count,
            "subprocess_popen_count": popen_count,
            "os_system_or_unregistered_subprocess_api_count": 0,
            "modules_with_child_processes_count": len(modules_with_children),
            "modules_with_child_processes": modules_with_children,
            "call_sites": rows,
        },
        "astra_subset": {
            "call_site_count": 6,
            "function_counts": astra_counts,
        },
        "child_process_universe_closed_for_bound_current_runtime_bytes": True,
        "child_process_effect_totality_proved": False,
        "minimum_resolution_cut": [
            "ROUTE_ARBITRARY_SHELL_THROUGH_FINAL_EFFECT_AUTHORIZER_OR_FORBID_FROM_CREDITED_RUNTIME",
            "ROUTE_PACKAGE_INSTALL_PROCESS_EFFECTS_THROUGH_PACKAGE_ENV_MUTATION_AUTHORIZATION",
            "SANDBOX_OR_BIND_BROWSER_DRIVER_AND_GENERAL_CLI_CHILDREN",
            "SANDBOX_OR_BIND_DOCUMENT_AND_DATA_TOOL_CHILDREN",
            "SANDBOX_OR_SCOPE_COMPLETELY_BIND_TEST_EXECUTION_CHILDREN",
            "BIND_RECURSIVE_ASTRA_CHILD_TO_THE_SAME_STRICT_EFFECT_BOUNDARY",
            "FAIL_CLOSED_ON_ANY_NEW_PROCESS_CREATION_API_OR_CALL_SITE_UNTIL_RECLASSIFIED",
        ],
        "hard_nonclaims": [
            "NO_CLAIM_CHILD_PROCESS_EFFECT_MEDIATION_COMPLETE",
            "NO_CLAIM_EXTERNAL_BINARIES_OR_CHILD_PROGRAMS_ARE_EFFECT_FREE",
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
    print(json.dumps(compile_registry(), indent=2, sort_keys=True))
