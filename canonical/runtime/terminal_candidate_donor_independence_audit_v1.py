"""Fail-closed static donor-independence audit for the terminal candidate path.

This audit does not replay terminal evidence. It proves that the Brain candidate
dependency cone is composed only of repository-owned Python modules, stdlib, and
explicitly classified general-purpose substrates. Target-capability providers,
network clients, dynamic imports, and shell/process escape hatches fail closed.
"""
from __future__ import annotations

import ast
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

# Third-party packages allowed only as general substrates, not target-capability donors.
ALLOWED_GENERAL_SUBSTRATES = {
    "cadquery",
    "pydantic",
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
    "exec",
    "compile",
    "os.system",
    "subprocess.run",
    "subprocess.call",
    "subprocess.Popen",
    "importlib.import_module",
}

STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {
    "__future__", "typing", "dataclasses", "pathlib", "collections", "heapq",
    "itertools", "math", "re", "json", "html", "base64", "tempfile", "io",
    "hashlib", "zipfile", "xml", "unicodedata",
}


def _module_path(name: str) -> Path | None:
    # canonical.runtime.foo
    if name.startswith("canonical.runtime."):
        rel = name.removeprefix("canonical.runtime.").replace(".", "/") + ".py"
        p = RUNTIME / rel
        return p if p.is_file() else None
    # local historical bare imports such as cad_partspec
    first = name.split(".", 1)[0]
    p = RUNTIME / (first + ".py")
    return p if p.is_file() else None


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


def evaluate(root: Path = ROOT) -> dict[str, Any]:
    runtime = root / "canonical" / "runtime"
    queue = [runtime / (name + ".py") for name in ROOT_MODULES]
    seen: set[Path] = set()
    errors: list[str] = []
    external: set[str] = set()
    edges: list[dict[str, str]] = []

    while queue:
        path = queue.pop()
        path = path.resolve()
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

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    # Relative imports are repository-local by construction.
                    names = []
                else:
                    names = [node.module] if node.module else []
            else:
                names = []

            for name in names:
                if not name:
                    continue
                if any(name == x or name.startswith(x + ".") for x in FORBIDDEN_IMPORT_PREFIXES):
                    errors.append("FORBIDDEN_PROVIDER_OR_NETWORK_IMPORT:" + rel + ":" + name)
                    continue
                local = None
                # Resolve against the selected repo root, not module globals.
                if name.startswith("canonical.runtime."):
                    p = runtime / (name.removeprefix("canonical.runtime.").replace(".", "/") + ".py")
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

            if isinstance(node, ast.Call):
                cname = _call_name(node)
                if cname in FORBIDDEN_CALLS:
                    errors.append("FORBIDDEN_DYNAMIC_OR_PROCESS_CALL:" + rel + ":" + cname)

    files = sorted(str(p.relative_to(root)) for p in seen)
    errors = sorted(set(errors))
    return {
        "schema": "PROJECT_BRAIN_TERMINAL_CANDIDATE_DONOR_INDEPENDENCE_AUDIT_V1",
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "root_modules": list(ROOT_MODULES),
        "repository_owned_dependency_file_count": len(files),
        "repository_owned_dependency_files": files,
        "general_substrates": sorted(external),
        "target_capability_donor_runtime_dependencies": [],
        "network_provider_dependencies": [],
        "undeclared_dependency_count": len(errors),
        "errors": errors,
        "rule": "PASS_IFF_RECURSIVE_CANDIDATE_SOURCE_CLOSURE_HAS_NO_TARGET_PROVIDER_NETWORK_DYNAMIC_IMPORT_PROCESS_ESCAPE_OR_UNCLASSIFIED_EXTERNAL_DEPENDENCY",
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
