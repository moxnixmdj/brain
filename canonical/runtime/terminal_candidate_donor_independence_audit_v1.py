"""Fail-closed donor-independence audit for the frozen terminal candidate path.

The audit recursively classifies candidate imports and rejects target-capability
providers, network clients, process escape, dynamic imports, and unknown
third-party dependencies. The terminal CAD route contains deliberate local
compile/exec calls; these are admitted only when the exact independently frozen
terminal blobs match. Any byte change reopens the gate.
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "canonical" / "runtime"

ROOT_MODULES = (
    "saccr_credit_information_safe_candidate",
    "browser_state_information_safe_candidate",
    "delegation_whole_scope_candidate_v2",
    "tool_discovery_information_safe_candidate",
    "research_control_information_safe_candidate",
    "cad_t0_route_specific_candidate_v1",
    "contract_native_brain_candidate",
    "m0a_raw_source_brain_candidate_v2",
    "native_artifact_cross_format_candidate_v1",
)

# General-purpose substrates used by the exact frozen terminal route.
ALLOWED_GENERAL_SUBSTRATES = {
    "cadquery",
    "pydantic",
    "PIL",
    "pypdf",
}

FORBIDDEN_IMPORT_PREFIXES = (
    "anthropic",
    "openai",
    "huggingface_hub",
    "transformers",
    "requests",
    "httpx",
    "aiohttp",
    "socket",
    "urllib.request",
    "ollama",
    "vllm",
)

FORBIDDEN_CALLS = {
    "__import__",
    "eval",
    "os.system",
    "subprocess.run",
    "subprocess.call",
    "subprocess.Popen",
    "importlib.import_module",
}

# Dynamic CAD source execution is part of the proven terminal route. It is not
# generally authorized: only these exact content-addressed files may contain it.
REVIEWED_DYNAMIC_BLOBS = {
    "canonical/runtime/cad_partspec_generator.py":
        "89b4250fa85df8d02d51bcb513f035d102625056",
    "canonical/runtime/cad_t0_route_specific_candidate_v1.py":
        "aa32750b220a023617938b7be9476f6b3aac6704",
    "canonical/runtime/m1b_smooth_surface_compiler.py":
        "bd3824847f400e8088dc25a83674579f99345a30",
}

STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {
    "__future__", "typing", "dataclasses", "pathlib", "collections", "heapq",
    "itertools", "math", "re", "json", "html", "base64", "tempfile", "io",
    "hashlib", "zipfile", "xml", "unicodedata",
}


def _git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + bytes([0]) + data
    ).hexdigest()


def _call_name(node: ast.Call) -> str:
    fn = node.func
    if isinstance(fn, ast.Name):
        return fn.id
    parts: list[str] = []
    while isinstance(fn, ast.Attribute):
        parts.append(fn.attr)
        fn = fn.value
    if isinstance(fn, ast.Name):
        parts.append(fn.id)
    return ".".join(reversed(parts))


class _Scanner(ast.NodeVisitor):
    def __init__(self) -> None:
        self.function_stack: list[str] = []
        self.imports: list[str] = []
        self.calls: list[tuple[str | None, str]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_Import(self, node: ast.Import) -> Any:
        self.imports.extend(alias.name for alias in node.names)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        if node.level:
            self.generic_visit(node)
            return
        module = node.module or ""
        if module == "canonical.runtime":
            # "from canonical.runtime import foo" means a local foo module when
            # that module exists. Classify aliases individually.
            self.imports.extend(
                "canonical.runtime." + alias.name for alias in node.names
            )
        elif module:
            self.imports.append(module)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> Any:
        self.calls.append(
            (self.function_stack[-1] if self.function_stack else None,
             _call_name(node))
        )
        self.generic_visit(node)


def evaluate(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    runtime = root / "canonical" / "runtime"
    queue = [runtime / (name + ".py") for name in ROOT_MODULES]
    seen: set[Path] = set()
    errors: list[str] = []
    external: set[str] = set()
    edges: list[dict[str, str]] = []
    provider_dependencies: set[str] = set()
    network_dependencies: set[str] = set()
    reviewed_dynamic_calls: list[dict[str, str | None]] = []
    all_calls: list[tuple[str, str | None, str]] = []

    while queue:
        path = queue.pop().resolve()
        if path in seen:
            continue
        seen.add(path)
        if not path.is_file():
            errors.append("LOCAL_MODULE_MISSING:" + str(path.relative_to(root)))
            continue

        rel = str(path.relative_to(root))
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except Exception as exc:
            errors.append("AST_PARSE_FAILED:" + rel + ":" + type(exc).__name__)
            continue

        scanner = _Scanner()
        scanner.visit(tree)
        all_calls.extend((rel, fn, cname) for fn, cname in scanner.calls)

        for name in scanner.imports:
            if any(
                name == x or name.startswith(x + ".")
                for x in FORBIDDEN_IMPORT_PREFIXES
            ):
                if name.startswith(("requests", "httpx", "aiohttp", "socket", "urllib.request")):
                    network_dependencies.add(name)
                else:
                    provider_dependencies.add(name)
                errors.append(
                    "FORBIDDEN_PROVIDER_OR_NETWORK_IMPORT:" + rel + ":" + name
                )
                continue

            local: Path | None = None
            if name.startswith("canonical.runtime."):
                p = runtime / (
                    name.removeprefix("canonical.runtime.").replace(".", "/") + ".py"
                )
                if p.is_file():
                    local = p
            else:
                p = runtime / (name.split(".", 1)[0] + ".py")
                if p.is_file():
                    local = p

            if local is not None:
                edges.append({"from": rel, "to": str(local.relative_to(root))})
                queue.append(local)
                continue

            top = name.split(".", 1)[0]
            if top in STDLIB:
                continue
            if top in ALLOWED_GENERAL_SUBSTRATES:
                external.add(top)
                continue
            errors.append("UNCLASSIFIED_EXTERNAL_IMPORT:" + rel + ":" + name)

        for fn, cname in scanner.calls:
            if cname in FORBIDDEN_CALLS:
                errors.append(
                    "FORBIDDEN_DYNAMIC_OR_PROCESS_CALL:" + rel + ":" + cname
                )
            if cname in {"exec", "compile"}:
                expected = REVIEWED_DYNAMIC_BLOBS.get(rel)
                got = _git_blob(path)
                if expected is None or got != expected:
                    errors.append(
                        "UNREVIEWED_DYNAMIC_EXECUTION:" + rel + ":" + cname
                    )
                else:
                    reviewed_dynamic_calls.append({
                        "path": rel,
                        "function": fn,
                        "call": cname,
                        "blob_sha": got,
                    })

    # cad_partspec_generator.run_code contains a historical helper exec, but the
    # terminal candidate imports/calls generate_code only. Fail if any reachable
    # module calls run_code, including attribute calls ending in ".run_code".
    run_code_calls = [
        {"path": rel, "function": fn, "call": cname}
        for rel, fn, cname in all_calls
        if (cname == "run_code" or cname.endswith(".run_code"))
        and not (
            rel == "canonical/runtime/cad_partspec_generator.py"
            and fn == "run_code"
        )
    ]
    if run_code_calls:
        errors.append("CAD_PARTSPEC_RUN_CODE_REACHABLE_FROM_TERMINAL_CLOSURE")

    files = sorted(str(p.relative_to(root)) for p in seen)
    errors = sorted(set(errors))
    return {
        "schema": "PROJECT_BRAIN_TERMINAL_CANDIDATE_DONOR_INDEPENDENCE_AUDIT_V1",
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "root_modules": list(ROOT_MODULES),
        "repository_owned_dependency_file_count": len(files),
        "repository_owned_dependency_files": files,
        "dependency_edges": sorted(edges, key=lambda x: (x["from"], x["to"])),
        "general_substrates": sorted(external),
        "target_capability_donor_runtime_dependencies":
            sorted(provider_dependencies),
        "network_provider_dependencies": sorted(network_dependencies),
        "reviewed_dynamic_execution": reviewed_dynamic_calls,
        "cad_partspec_run_code_reachable": bool(run_code_calls),
        "undeclared_dependency_count": len(errors),
        "errors": errors,
        "rule": (
            "PASS_IFF_RECURSIVE_CANDIDATE_SOURCE_CLOSURE_HAS_NO_TARGET_PROVIDER_"
            "NETWORK_DYNAMIC_IMPORT_PROCESS_ESCAPE_OR_UNCLASSIFIED_EXTERNAL_DEPENDENCY__"
            "CAD_DYNAMIC_EXECUTION_ALLOWED_ONLY_ON_EXACT_TERMINAL_FROZEN_BLOBS__"
            "HISTORICAL_RUN_CODE_HELPER_MUST_BE_UNREACHABLE"
        ),
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
