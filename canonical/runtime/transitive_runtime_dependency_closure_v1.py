from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Iterable

SCHEMA = "PROJECT_BRAIN_TRANSITIVE_RUNTIME_DEPENDENCY_CLOSURE_V1"


class DependencyClosureError(ValueError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _module_candidates(repo_root: Path, module: str) -> tuple[Path, Path]:
    rel = Path(*module.split("."))
    return repo_root / (str(rel) + ".py"), repo_root / rel / "__init__.py"


def _module_exists_as_namespace(repo_root: Path, module: str) -> bool:
    return (repo_root / Path(*module.split("."))).is_dir()


def _current_package(repo_root: Path, path: Path) -> list[str]:
    rel = path.relative_to(repo_root)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        return parts[:-1]
    parts[-1] = Path(parts[-1]).stem
    return parts[:-1]


def _resolve_import_modules(repo_root: Path, path: Path, tree: ast.AST) -> set[str]:
    package = _current_package(repo_root, path)
    modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "canonical" or alias.name.startswith("canonical."):
                    modules.add(alias.name)

        elif isinstance(node, ast.ImportFrom):
            if node.level:
                if node.level - 1 > len(package):
                    raise DependencyClosureError(f"RELATIVE_IMPORT_ESCAPES_ROOT:{path}")
                base_parts = package[: len(package) - (node.level - 1)]
                if node.module:
                    base_parts += node.module.split(".")
                base = ".".join(base_parts)
            else:
                base = node.module or ""

            if not (base == "canonical" or base.startswith("canonical.")):
                continue

            modules.add(base)
            for alias in node.names:
                if alias.name == "*":
                    continue
                child = base + "." + alias.name if base else alias.name
                py, init_py = _module_candidates(repo_root, child)
                if py.exists() or init_py.exists() or _module_exists_as_namespace(repo_root, child):
                    modules.add(child)

    return modules


def compute_closure(repo_root: Path, entries: Iterable[str]) -> dict:
    repo_root = repo_root.resolve()
    entry_paths = [repo_root / e for e in entries]
    if not entry_paths:
        return {
            "schema": SCHEMA,
            "pass": False,
            "classification": "INVALID_ENTRIES",
            "errors": ["NO_ENTRIES"],
            "terminal_credit": False,
        }

    missing_entries = [str(p.relative_to(repo_root)) for p in entry_paths if not p.is_file()]
    if missing_entries:
        return {
            "schema": SCHEMA,
            "pass": False,
            "classification": "ENTRY_MISSING",
            "errors": sorted(missing_entries),
            "terminal_credit": False,
        }

    queue = list(entry_paths)
    visited: set[Path] = set()
    unresolved: set[str] = set()

    while queue:
        path = queue.pop()
        path = path.resolve()
        if repo_root not in path.parents and path != repo_root:
            raise DependencyClosureError(f"PATH_OUTSIDE_REPO:{path}")
        visited.add(path)

        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError) as exc:
            return {
                "schema": SCHEMA,
                "pass": False,
                "classification": "PARSE_FAILURE",
                "errors": [f"{path.relative_to(repo_root)}:{exc.__class__.__name__}"],
                "terminal_credit": False,
            }

        try:
            modules = _resolve_import_modules(repo_root, path, tree)
        except DependencyClosureError as exc:
            return {
                "schema": SCHEMA,
                "pass": False,
                "classification": "IMPORT_RESOLUTION_FAILURE",
                "errors": [str(exc)],
                "terminal_credit": False,
            }

        for module in modules:
            py, init_py = _module_candidates(repo_root, module)
            if py.is_file():
                if py.resolve() not in visited:
                    queue.append(py)
            elif init_py.is_file():
                if init_py.resolve() not in visited:
                    queue.append(init_py)
            elif _module_exists_as_namespace(repo_root, module):
                continue
            else:
                unresolved.add(module)

    files = []
    for path in sorted(visited, key=lambda p: str(p.relative_to(repo_root))):
        rel = str(path.relative_to(repo_root)).replace("\\", "/")
        files.append({
            "path": rel,
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        })

    if unresolved:
        return {
            "schema": SCHEMA,
            "pass": False,
            "classification": "TRANSITIVE_DEPENDENCY_MISSING",
            "unresolved_canonical_modules": sorted(unresolved),
            "files": files,
            "terminal_credit": False,
        }

    digest_payload = json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "schema": SCHEMA,
        "pass": True,
        "classification": "CLOSED_TRANSITIVE_PYTHON_DEPENDENCY_SET",
        "files": files,
        "file_count": len(files),
        "closure_sha256": hashlib.sha256(digest_payload).hexdigest(),
        "carrier_rule": "OVERLAY_EXACTLY_THIS_CONTENT_ADDRESSED_SET_BEFORE_TASK_EXPOSURE",
        "independent_verification_required": True,
        "terminal_credit": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo_root", type=Path)
    parser.add_argument("entries", nargs="+")
    args = parser.parse_args()
    out = compute_closure(args.repo_root, args.entries)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
