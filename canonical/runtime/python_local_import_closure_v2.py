"""Content-addressed transitive closure for Brain-local Python imports.

Given a Python entrypoint under a repository root, recursively resolve every
statically imported canonical.* module that exists in the repository and bind
the exact Git blob SHA of each file.

This is deliberately fail-closed for unresolved Brain-local imports and dynamic
imports. Standard-library, third-party, native, and runtime-configuration
dependencies remain separate proof obligations.
"""
from __future__ import annotations

import ast
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_PYTHON_LOCAL_IMPORT_CLOSURE_V2"


def _git_blob(data: bytes) -> str:
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _inside(root: Path, path: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _module_name(root: Path, path: Path) -> str:
    rel = path.relative_to(root)
    parts = list(rel.parts)
    if not parts or path.suffix != ".py":
        raise ValueError("ENTRYPOINT_NOT_PYTHON")
    parts[-1] = parts[-1][:-3]
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _resolve_module(root: Path, module: str) -> Path | None:
    if not module or not module.startswith("canonical"):
        return None
    base = root.joinpath(*module.split("."))
    py = base.with_suffix(".py")
    init = base / "__init__.py"
    if py.is_file():
        return py
    if init.is_file():
        return init
    return None


def _is_namespace_package(root: Path, module: str) -> bool:
    if not module or not module.startswith("canonical"):
        return False
    base = root.joinpath(*module.split("."))
    return base.is_dir() and not (base / "__init__.py").is_file()


def _relative_module(current_module: str, level: int, module: str | None) -> str:
    package = current_module.split(".")[:-1]
    if level < 1 or level > len(package) + 1:
        raise ValueError("RELATIVE_IMPORT_LEVEL_INVALID")
    prefix = package[: len(package) - level + 1]
    if module:
        prefix.extend(module.split("."))
    return ".".join(prefix)


def _imports(root: Path, path: Path) -> tuple[set[Path], list[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    current = _module_name(root, path)
    deps: set[Path] = set()
    errors: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            dynamic = (
                isinstance(fn, ast.Name) and fn.id in {"__import__", "import_module"}
            ) or (
                isinstance(fn, ast.Attribute)
                and isinstance(fn.value, ast.Name)
                and fn.value.id == "importlib"
                and fn.attr == "import_module"
            )
            if dynamic:
                errors.append(
                    f"DYNAMIC_IMPORT_UNSUPPORTED:{path.relative_to(root).as_posix()}:{node.lineno}"
                )

        elif isinstance(node, ast.Import):
            for alias in node.names:
                if not alias.name.startswith("canonical"):
                    continue
                resolved = _resolve_module(root, alias.name)
                if resolved is None:
                    errors.append("LOCAL_IMPORT_UNRESOLVED:" + alias.name)
                else:
                    deps.add(resolved)

        elif isinstance(node, ast.ImportFrom):
            try:
                base = (
                    _relative_module(current, node.level, node.module)
                    if node.level
                    else (node.module or "")
                )
            except ValueError as exc:
                errors.append(
                    f"{exc}:{path.relative_to(root).as_posix()}:{node.lineno}"
                )
                continue

            if not base.startswith("canonical"):
                continue

            resolved = _resolve_module(root, base)
            namespace_base = _is_namespace_package(root, base)
            if resolved is not None:
                deps.add(resolved)
            elif node.module and not namespace_base:
                errors.append("LOCAL_IMPORT_UNRESOLVED:" + base)

            for alias in node.names:
                if alias.name == "*":
                    continue
                child = base + "." + alias.name if base else alias.name
                child_path = _resolve_module(root, child)
                if child_path is not None:
                    deps.add(child_path)

    return deps, errors


def compute(entrypoint: str | Path, *, repo_root: str | Path) -> dict[str, Any]:
    try:
        root = Path(repo_root).resolve()
        raw = Path(entrypoint)
        entry = (root / raw).resolve() if not raw.is_absolute() else raw.resolve()
        if not _inside(root, entry):
            raise ValueError("ENTRYPOINT_OUTSIDE_REPOSITORY")
        if not entry.is_file() or entry.suffix != ".py":
            raise ValueError("ENTRYPOINT_MISSING_OR_NOT_PYTHON")

        queue = [entry]
        seen: set[Path] = set()
        errors: list[str] = []

        while queue:
            path = queue.pop()
            if path in seen:
                continue
            if not _inside(root, path):
                errors.append("DEPENDENCY_OUTSIDE_REPOSITORY:" + str(path))
                continue
            seen.add(path)
            deps, local_errors = _imports(root, path)
            errors.extend(local_errors)
            for dep in sorted(deps):
                if dep not in seen:
                    queue.append(dep)

        if errors:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "pass": False,
                "errors": sorted(set(errors)),
                "terminal_authority": False,
            }

        rows = []
        for path in sorted(seen):
            data = path.read_bytes()
            rows.append({
                "path": path.relative_to(root).as_posix(),
                "git_blob_sha": _git_blob(data),
                "size": len(data),
            })

        return {
            "schema": SCHEMA,
            "status": "PASS__BRAIN_LOCAL_PYTHON_IMPORT_CLOSURE_BOUND",
            "pass": True,
            "entrypoint": entry.relative_to(root).as_posix(),
            "dependency_count": len(rows),
            "dependencies": rows,
            "closure_sha256": sha256(_canon(rows).encode("utf-8")).hexdigest(),
            "third_party_environment_bound": False,
            "terminal_authority": False,
            "boundary": (
                "BINDS_STATIC_BRAIN_LOCAL_PYTHON_IMPORT_BYTES_ONLY;"
                "STANDARD_LIBRARY_THIRD_PARTY_NATIVE_AND_RUNTIME_CONFIGURATION_DEPENDENCIES_REMAIN_SEPARATE"
            ),
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "terminal_authority": False,
        }
