"""Load one symbol from a repository research tool without running import-time side effects.

Many research scripts do real work at module level (copy trees, ``rmtree`` absolute paths).
Importing them to reuse a helper would execute that work.  This loader parses the file first
and refuses to import it unless every top-level statement is a definition, an import, a
docstring, a ``__main__`` guard, or an assignment whose value is a literal or a call to a
small allowlist of pure constructors.  The source path must stay inside the repository.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import pathlib
import sys
from typing import Any

PURE_CONSTRUCTORS = frozenset({"Symbol", "Path", "pathlib.Path", "re.compile", "frozenset", "set", "tuple"})


class ResearchToolUnsafe(RuntimeError):
    pass


def _pure_value(node: ast.AST) -> bool:
    try:
        ast.literal_eval(node)
        return True
    except (ValueError, TypeError, SyntaxError, RecursionError):
        pass
    if isinstance(node, ast.Call):
        return ast.unparse(node.func) in PURE_CONSTRUCTORS and all(_pure_value(a) for a in node.args) and not node.keywords
    return False


def import_time_effects(tree: ast.Module) -> list[str]:
    """Top-level statements that would execute something other than a definition."""
    effects = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        if isinstance(node, ast.If) and "__main__" in ast.unparse(node.test):
            continue
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None and _pure_value(node.value):
            continue
        effects.append("line %d: %s" % (getattr(node, "lineno", 0), ast.unparse(node).splitlines()[0][:80]))
    return effects


def resolve(root: Any, rel: str) -> pathlib.Path:
    base = pathlib.Path(root).resolve()
    path = (base / rel).resolve()
    if base not in path.parents or path.suffix != ".py" or not path.is_file():
        raise ResearchToolUnsafe("RESEARCH_TOOL_PATH_INVALID:" + rel)
    return path


def safe_repo_path(root: Any, raw: Any) -> pathlib.Path:
    """An adapter input/output path: repository-relative and never escaping the repository."""
    base = pathlib.Path(root).resolve()
    text = str(raw or "").strip()
    if not text:
        raise RuntimeError("PATH_REQUIRED")
    path = (base / text).resolve()
    if path != base and base not in path.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return path


def source_sha256(root: Any, rel: str) -> str:
    return hashlib.sha256(resolve(root, rel).read_bytes()).hexdigest()


def load_symbol(root: Any, rel: str, name: str) -> Any:
    path = resolve(root, rel)
    effects = import_time_effects(ast.parse(path.read_text(encoding="utf-8")))
    if effects:
        raise ResearchToolUnsafe("RESEARCH_TOOL_IMPORT_TIME_EFFECTS:" + rel + ":" + effects[0])
    module_name = "project_brain_research_tool_" + hashlib.sha256(str(path).encode()).hexdigest()[:16]
    module = sys.modules.get(module_name)
    if module is None:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ResearchToolUnsafe("RESEARCH_TOOL_LOAD_FAILED:" + rel)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(module_name, None)
            raise
    value = getattr(module, name, None)
    if value is None:
        raise ResearchToolUnsafe("RESEARCH_TOOL_SYMBOL_MISSING:" + rel + ":" + name)
    return value
