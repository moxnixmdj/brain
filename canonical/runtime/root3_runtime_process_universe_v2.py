"""Conservative whole-runtime Python process universe compiler for Root3 V2.

This compiler deliberately scans every Python file under canonical/runtime,
rather than a hand-selected reachability subset. It discovers direct process
creation APIs with import-alias resolution, content-addresses every file, and
fails closed on unsupported process channels or dynamic ambiguity.

It grants no effect authority and no acceptance credit.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_REL = Path("canonical/runtime")
SCHEMA = "PROJECT_BRAIN_ROOT3_RUNTIME_PROCESS_UNIVERSE_V2"

# Source-level APIs that can be intercepted by installing wrappers on exactly
# subprocess.run and subprocess.Popen before runtime modules are imported.
INTERCEPTABLE = {
    "subprocess.run": "subprocess.run",
    "subprocess.Popen": "subprocess.Popen",
    "subprocess.call": "subprocess.Popen",
    "subprocess.check_call": "subprocess.Popen",
    "subprocess.check_output": "subprocess.run",
    "subprocess.getoutput": "subprocess.run",
    "subprocess.getstatusoutput": "subprocess.run",
}

# Known process/control APIs that are not reducible to the two subprocess
# attributes. Presence of any such call keeps the two-chokepoint proof open.
UNMEDIATED_EXACT = {
    "os.system",
    "os.popen",
    "os.fork",
    "os.forkpty",
    "os.posix_spawn",
    "os.posix_spawnp",
    "asyncio.create_subprocess_exec",
    "asyncio.create_subprocess_shell",
    "multiprocessing.Process",
    "concurrent.futures.ProcessPoolExecutor",
    "pty.spawn",
}
UNMEDIATED_PREFIXES = ("os.spawn", "os.exec")

PROCESS_MODULE_ROOTS = {
    "subprocess",
    "os",
    "asyncio",
    "multiprocessing",
    "concurrent",
    "pty",
}


class ProcessUniverseError(RuntimeError):
    pass


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _aliases(tree: ast.Module) -> dict[str, str]:
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    out[alias.asname] = alias.name
                else:
                    top = alias.name.split(".")[0]
                    out[top] = top
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                if alias.name == "*":
                    continue
                out[alias.asname or alias.name] = node.module + "." + alias.name
    return out


def _qname(node: ast.AST, aliases: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        left = _qname(node.value, aliases)
        return None if left is None else left + "." + node.attr
    return None


def _target_names(node: ast.AST) -> list[str]:
    out: list[str] = []
    for item in ast.walk(node):
        if isinstance(item, ast.Name):
            out.append(item.id)
    return out


def _function_name(stack: list[str]) -> str:
    return stack[-1] if stack else "<module>"


class _Visitor(ast.NodeVisitor):
    def __init__(self, rel: str, aliases: dict[str, str]) -> None:
        self.rel = rel
        self.aliases = aliases
        self.stack: list[str] = []
        self.sites: list[dict[str, Any]] = []
        self.unmediated: list[dict[str, Any]] = []
        self.rebindings: list[dict[str, Any]] = []
        self.declared_chokepoint_rebindings: list[dict[str, Any]] = []
        self.dynamic_process_refs: list[dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.stack.append(node.name)
        self._check_args(node.args, node.lineno)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.stack.append(node.name)
        self._check_args(node.args, node.lineno)
        self.generic_visit(node)
        self.stack.pop()

    def _check_args(self, args: ast.arguments, lineno: int) -> None:
        names = [
            x.arg
            for x in [
                *args.posonlyargs,
                *args.args,
                *args.kwonlyargs,
                *([args.vararg] if args.vararg else []),
                *([args.kwarg] if args.kwarg else []),
            ]
        ]
        for name in names:
            bound = self.aliases.get(name)
            if bound and bound.split(".")[0] in PROCESS_MODULE_ROOTS:
                self.rebindings.append({
                    "module_path": self.rel,
                    "lineno": lineno,
                    "kind": "PROCESS_IMPORT_SHADOWED_BY_ARGUMENT",
                    "name": name,
                    "bound_import": bound,
                })

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._check_rebinding(target, node.value, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._check_rebinding(node.target, node.value, node.lineno)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._check_rebinding(node.target, node.value, node.lineno)
        self.generic_visit(node)

    def _check_rebinding(
        self, target: ast.AST, value: ast.AST | None, lineno: int
    ) -> None:
        if isinstance(target, ast.Name):
            bound = self.aliases.get(target.id)
            if bound and bound.split(".")[0] in PROCESS_MODULE_ROOTS:
                self.rebindings.append({
                    "module_path": self.rel,
                    "lineno": lineno,
                    "kind": "PROCESS_IMPORT_LOCAL_REBINDING",
                    "name": target.id,
                    "bound_import": bound,
                })
            return

        q = _qname(target, self.aliases)
        if q not in {"subprocess.run", "subprocess.Popen"}:
            return
        assigned = _qname(value, self.aliases) if value is not None else None
        mediator_name = Path(self.rel).name
        allowed = {
            ("subprocess.run", "_guarded_run"),
            ("subprocess.run", "_ORIGINAL_RUN"),
            ("subprocess.Popen", "_guarded_popen"),
            ("subprocess.Popen", "_ORIGINAL_POPEN"),
        }
        row = {
            "module_path": self.rel,
            "lineno": lineno,
            "target": q,
            "assigned": assigned,
        }
        if (
            mediator_name.startswith("root3_subprocess_mediator_v")
            and (q, assigned) in allowed
        ):
            self.declared_chokepoint_rebindings.append({
                **row,
                "kind": "DECLARED_ROOT3_CHOKEPOINT_INSTALL_OR_RESTORE",
            })
        else:
            self.rebindings.append({
                **row,
                "kind": "UNDECLARED_SUBPROCESS_CHOKEPOINT_REBINDING",
            })

    def visit_Call(self, node: ast.Call) -> None:
        q = _qname(node.func, self.aliases)

        if q in INTERCEPTABLE:
            self.sites.append({
                "module_path": self.rel,
                "function": _function_name(self.stack),
                "lineno": int(node.lineno),
                "source_api": q,
                "interception_api": INTERCEPTABLE[q],
            })
            self.generic_visit(node)
            return

        if (
            q in UNMEDIATED_EXACT
            or (
                isinstance(q, str)
                and any(q.startswith(prefix) for prefix in UNMEDIATED_PREFIXES)
            )
        ):
            self.unmediated.append({
                "module_path": self.rel,
                "function": _function_name(self.stack),
                "lineno": int(node.lineno),
                "source_api": q,
            })
            self.generic_visit(node)
            return

        # Resolve getattr(subprocess, "run") and equivalent literal reflection.
        if isinstance(node.func, ast.Call):
            inner_q = _qname(node.func.func, self.aliases)
            if inner_q in {"getattr", "builtins.getattr"} and len(node.func.args) >= 2:
                base = _qname(node.func.args[0], self.aliases)
                name = node.func.args[1]
                if (
                    base
                    and isinstance(name, ast.Constant)
                    and isinstance(name.value, str)
                ):
                    candidate = base + "." + name.value
                    if candidate in INTERCEPTABLE:
                        self.sites.append({
                            "module_path": self.rel,
                            "function": _function_name(self.stack),
                            "lineno": int(node.lineno),
                            "source_api": candidate,
                            "interception_api": INTERCEPTABLE[candidate],
                            "reflection": "LITERAL_GETATTR",
                        })
                        self.generic_visit(node)
                        return
                    if candidate in UNMEDIATED_EXACT or any(
                        candidate.startswith(prefix)
                        for prefix in UNMEDIATED_PREFIXES
                    ):
                        self.unmediated.append({
                            "module_path": self.rel,
                            "function": _function_name(self.stack),
                            "lineno": int(node.lineno),
                            "source_api": candidate,
                            "reflection": "LITERAL_GETATTR",
                        })
                        self.generic_visit(node)
                        return

        # Dynamic import of process modules is not silently accepted.
        if q in {"__import__", "builtins.__import__", "importlib.import_module"}:
            if node.args and isinstance(node.args[0], ast.Constant):
                value = node.args[0].value
                if isinstance(value, str) and value.split(".")[0] in PROCESS_MODULE_ROOTS:
                    self.dynamic_process_refs.append({
                        "module_path": self.rel,
                        "function": _function_name(self.stack),
                        "lineno": int(node.lineno),
                        "kind": "DYNAMIC_PROCESS_MODULE_IMPORT",
                        "module": value,
                    })

        self.generic_visit(node)


def compile_universe(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    runtime = (root / RUNTIME_REL).resolve()
    if not runtime.is_dir():
        raise ProcessUniverseError("RUNTIME_DIRECTORY_MISSING")

    files = sorted(runtime.rglob("*.py"))
    if not files:
        raise ProcessUniverseError("RUNTIME_PYTHON_UNIVERSE_EMPTY")

    file_rows: list[dict[str, Any]] = []
    sites: list[dict[str, Any]] = []
    unmediated: list[dict[str, Any]] = []
    rebindings: list[dict[str, Any]] = []
    dynamic_refs: list[dict[str, Any]] = []
    declared_chokepoint_rebindings: list[dict[str, Any]] = []
    parse_failures: list[dict[str, Any]] = []

    for path in files:
        rel = path.relative_to(root).as_posix()
        raw = path.read_bytes()
        blob = git_blob_sha(raw)
        row = {"path": rel, "git_blob_sha": blob, "bytes": len(raw)}
        try:
            text = raw.decode("utf-8")
            tree = ast.parse(text, filename=rel)
        except (UnicodeDecodeError, SyntaxError) as exc:
            row["parse_status"] = "STANDARD_PYTHON_NONEXECUTABLE"
            row["parse_error"] = type(exc).__name__ + ":" + str(exc)
            parse_failures.append({
                "module_path": rel,
                "git_blob_sha": blob,
                "error": row["parse_error"],
            })
            file_rows.append(row)
            continue

        row["parse_status"] = "PARSEABLE"
        aliases = _aliases(tree)
        visitor = _Visitor(rel, aliases)
        visitor.visit(tree)
        sites.extend(visitor.sites)
        unmediated.extend(visitor.unmediated)
        rebindings.extend(visitor.rebindings)
        declared_chokepoint_rebindings.extend(
            visitor.declared_chokepoint_rebindings
        )
        dynamic_refs.extend(visitor.dynamic_process_refs)
        file_rows.append(row)

    key_seen: set[tuple[str, int, str]] = set()
    normalized_sites: list[dict[str, Any]] = []
    for row in sorted(
        sites,
        key=lambda x: (x["module_path"], x["lineno"], x["source_api"]),
    ):
        key = (row["module_path"], row["lineno"], row["source_api"])
        if key in key_seen:
            raise ProcessUniverseError("DUPLICATE_PROCESS_SITE:" + repr(key))
        key_seen.add(key)
        normalized_sites.append(row)

    # Multiple source APIs on one source line may normalize to the same global
    # interception key. That would make frame-based mediation ambiguous.
    intercept_seen: dict[tuple[str, int, str], str] = {}
    collisions: list[dict[str, Any]] = []
    for row in normalized_sites:
        key = (
            row["module_path"],
            row["lineno"],
            row["interception_api"],
        )
        previous = intercept_seen.get(key)
        if previous is not None and previous != row["source_api"]:
            collisions.append({
                "module_path": key[0],
                "lineno": key[1],
                "interception_api": key[2],
                "source_apis": sorted({previous, row["source_api"]}),
            })
        intercept_seen[key] = row["source_api"]

    universe_material = {
        "files": file_rows,
        "sites": normalized_sites,
        "parse_failures": parse_failures,
        "unmediated": sorted(
            unmediated,
            key=lambda x: (x["module_path"], x["lineno"], x["source_api"]),
        ),
        "rebindings": sorted(
            rebindings,
            key=lambda x: (x["module_path"], x["lineno"], x["kind"]),
        ),
        "declared_chokepoint_rebindings": sorted(
            declared_chokepoint_rebindings,
            key=lambda x: (x["module_path"], x["lineno"], x["target"]),
        ),
        "dynamic_process_refs": sorted(
            dynamic_refs,
            key=lambda x: (x["module_path"], x["lineno"], x["kind"]),
        ),
        "interception_collisions": collisions,
    }
    digest = _sha(universe_material)

    two_chokepoint_preconditions = (
        not unmediated
        and not rebindings
        and not dynamic_refs
        and not collisions
    )

    source_counts: dict[str, int] = {}
    intercept_counts: dict[str, int] = {}
    for row in normalized_sites:
        source_counts[row["source_api"]] = source_counts.get(row["source_api"], 0) + 1
        api = row["interception_api"]
        intercept_counts[api] = intercept_counts.get(api, 0) + 1

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__WHOLE_CANONICAL_RUNTIME_PYTHON_SUPERSET_ENUMERATED__"
            "TWO_SUBPROCESS_CHOKEPOINT_PRECONDITIONS_PASS__ZERO_CREDIT"
            if two_chokepoint_preconditions
            else
            "OPEN__WHOLE_CANONICAL_RUNTIME_PYTHON_SUPERSET_ENUMERATED__"
            "UNMEDIATED_OR_AMBIGUOUS_PROCESS_SURFACE_PRESENT__ZERO_CREDIT"
        ),
        "runtime_root": RUNTIME_REL.as_posix(),
        "python_file_count": len(files),
        "parseable_file_count": len(files) - len(parse_failures),
        "standard_python_nonexecutable_file_count": len(parse_failures),
        "standard_python_nonexecutable_files": parse_failures,
        "direct_process_source_site_count": len(normalized_sites),
        "source_api_counts": dict(sorted(source_counts.items())),
        "interception_api_counts": dict(sorted(intercept_counts.items())),
        "process_sites": normalized_sites,
        "unmediated_process_sites": universe_material["unmediated"],
        "process_import_rebindings": universe_material["rebindings"],
        "declared_chokepoint_rebindings": universe_material[
            "declared_chokepoint_rebindings"
        ],
        "dynamic_process_module_refs": universe_material["dynamic_process_refs"],
        "interception_key_collisions": collisions,
        "whole_runtime_python_universe_sha256": digest,
        "minimum_direct_python_mediation_chokepoints": (
            ["subprocess.run", "subprocess.Popen"]
            if two_chokepoint_preconditions
            else []
        ),
        "two_chokepoint_preconditions_proved_for_parseable_runtime_python": (
            two_chokepoint_preconditions
        ),
        "syntax_invalid_files_execute_under_standard_python": False,
        "dynamic_source_transformation_totality_proved": False,
        "native_extension_process_creation_totality_proved": False,
        "child_internal_effect_totality_proved": False,
        "hard_nonclaims": [
            "NO_CLAIM_PARSE_FAILURE_BYTES_CANNOT_BE_TRANSFORMED_AND_EXECUTED_BY_A_SEPARATE_AUTHORIZED_PROGRAM",
            "NO_CLAIM_NATIVE_EXTENSIONS_CANNOT_CREATE_PROCESSES",
            "NO_CLAIM_CHILD_PROGRAM_INTERNAL_EFFECTS_ARE_SAFE",
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
    print(json.dumps(compile_universe(), indent=2, sort_keys=True))
