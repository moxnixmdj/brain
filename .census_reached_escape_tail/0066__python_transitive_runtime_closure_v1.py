from __future__ import annotations

import argparse
import ast
import hashlib
import json
from collections import deque
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "PROJECT_BRAIN_PYTHON_TRANSITIVE_RUNTIME_CLOSURE_V1"
RUNTIME_PREFIX = "canonical.runtime"


class ClosureError(ValueError):
    pass


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _safe_rel(path: str) -> str:
    if not isinstance(path, str) or not path.strip():
        raise ClosureError("PATH_REQUIRED")
    p = Path(path)
    if p.is_absolute() or ".." in p.parts:
        raise ClosureError("PATH_OUTSIDE_REPOSITORY:" + path)
    value = p.as_posix()
    if not value.startswith("canonical/runtime/") or not value.endswith(".py"):
        raise ClosureError("RUNTIME_PYTHON_PATH_REQUIRED:" + value)
    return value


def _module_candidates(module: str) -> tuple[str, str]:
    suffix = module.replace(".", "/")
    return suffix + ".py", suffix + "/__init__.py"


def _resolve_module(repo_root: Path, module: str) -> str | None:
    if not (module == RUNTIME_PREFIX or module.startswith(RUNTIME_PREFIX + ".")):
        return None
    for candidate in _module_candidates(module):
        if (repo_root / candidate).is_file():
            return candidate
    return None


def _module_for_path(path: str) -> str:
    value = path[:-3].replace("/", ".")
    if value.endswith(".__init__"):
        value = value[: -len(".__init__")]
    return value


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return (parent + "." if parent else "") + node.attr
    return None


def _discover(repo_root: Path, path: str) -> tuple[list[str], list[str]]:
    raw = (repo_root / path).read_bytes()
    try:
        tree = ast.parse(raw.decode("utf-8"), filename=path)
    except Exception as exc:
        raise ClosureError("AST_PARSE_FAIL:" + path + ":" + type(exc).__name__) from exc

    current_module = _module_for_path(path)
    current_package = current_module.rsplit(".", 1)[0]
    deps: set[str] = set()
    unresolved_dynamic: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                resolved = _resolve_module(repo_root, alias.name)
                if resolved:
                    deps.add(resolved)

        elif isinstance(node, ast.ImportFrom):
            if node.level:
                package_parts = current_package.split(".")
                if node.level > len(package_parts):
                    raise ClosureError("RELATIVE_IMPORT_ESCAPES_PACKAGE:" + path)
                base_parts = package_parts[: len(package_parts) - node.level + 1]
                if node.module:
                    base_parts.extend(node.module.split("."))
                base_module = ".".join(base_parts)
            else:
                base_module = node.module or ""

            resolved_base = _resolve_module(repo_root, base_module)
            if resolved_base:
                deps.add(resolved_base)

            # Handles "from canonical.runtime import foo" and package imports.
            for alias in node.names:
                child_module = (base_module + "." + alias.name).strip(".")
                resolved_child = _resolve_module(repo_root, child_module)
                if resolved_child:
                    deps.add(resolved_child)

        elif isinstance(node, ast.Call):
            name = _call_name(node.func)
            if name in {"importlib.import_module", "__import__"}:
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    target = node.args[0].value
                    resolved = _resolve_module(repo_root, target)
                    if resolved:
                        deps.add(resolved)
                    elif target == RUNTIME_PREFIX or target.startswith(RUNTIME_PREFIX + "."):
                        raise ClosureError("DYNAMIC_LOCAL_MODULE_MISSING:" + path + ":" + target)
                else:
                    unresolved_dynamic.add(path + ":" + str(name))

    deps.discard(path)
    return sorted(deps), sorted(unresolved_dynamic)


def compute_closure(repo_root: str | Path, root_paths: Iterable[str]) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    roots = [_safe_rel(x) for x in root_paths]
    if not roots:
        raise ClosureError("ROOTS_EMPTY")
    if len(set(roots)) != len(roots):
        raise ClosureError("ROOTS_DUPLICATE")
    for path in roots:
        if not (root / path).is_file():
            raise ClosureError("ROOT_MISSING:" + path)

    queue = deque(roots)
    visited: set[str] = set()
    edges: dict[str, list[str]] = {}
    unresolved_dynamic: set[str] = set()

    while queue:
        path = queue.popleft()
        if path in visited:
            continue
        visited.add(path)
        deps, dynamic = _discover(root, path)
        edges[path] = deps
        unresolved_dynamic.update(dynamic)
        for dep in deps:
            if dep not in visited:
                queue.append(dep)

    files = []
    for path in sorted(visited):
        data = (root / path).read_bytes()
        files.append(
            {
                "path": path,
                "git_blob_sha": git_blob_sha(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
                "is_root": path in roots,
            }
        )

    return {
        "schema": SCHEMA,
        "status": "PASS__TRANSITIVE_RUNTIME_CLOSURE_COMPUTED" if not unresolved_dynamic else "BLOCKED__UNRESOLVED_DYNAMIC_IMPORT",
        "pass": not unresolved_dynamic,
        "roots": roots,
        "closure_file_count": len(files),
        "files": files,
        "edges": {k: edges[k] for k in sorted(edges)},
        "unresolved_dynamic_imports": sorted(unresolved_dynamic),
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }


def verify_carrier(
    repo_root: str | Path,
    carrier_root: str | Path,
    root_paths: Iterable[str],
) -> dict[str, Any]:
    closure = compute_closure(repo_root, root_paths)
    if closure.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "status": "BLOCKED__SOURCE_CLOSURE_UNRESOLVED",
            "pass": False,
            "closure": closure,
            "terminal_authority": False,
            "acceptance_credit_delta": 0,
            "terminal_credit_delta": 0,
        }

    carrier = Path(carrier_root).resolve()
    missing: list[str] = []
    mismatched: list[dict[str, str]] = []
    for row in closure["files"]:
        path = row["path"]
        target = carrier / path
        if not target.is_file():
            missing.append(path)
            continue
        actual = git_blob_sha(target.read_bytes())
        if actual != row["git_blob_sha"]:
            mismatched.append(
                {
                    "path": path,
                    "expected_git_blob_sha": row["git_blob_sha"],
                    "actual_git_blob_sha": actual,
                }
            )

    ok = not missing and not mismatched
    return {
        "schema": SCHEMA,
        "status": "PASS__CARRIER_CONTAINS_EXACT_TRANSITIVE_RUNTIME_CLOSURE" if ok else "FAIL_CLOSED__CARRIER_RUNTIME_CLOSURE_INCOMPLETE_OR_MUTATED",
        "pass": ok,
        "closure": closure,
        "missing_paths": sorted(missing),
        "mismatched": sorted(mismatched, key=lambda x: x["path"]),
        "carrier_execution_authority": ok,
        "benchmark_execution_authority": False,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--carrier-root")
    parser.add_argument("--root", action="append", required=True)
    args = parser.parse_args()

    if args.carrier_root:
        out = verify_carrier(args.repo_root, args.carrier_root, args.root)
    else:
        out = compute_closure(args.repo_root, args.root)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
