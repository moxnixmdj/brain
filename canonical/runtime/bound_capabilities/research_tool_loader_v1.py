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


# Pure path arithmetic that research modules use to locate the repository: no I/O beyond
# ``resolve()`` reading symlinks, no writes, no network.
_PATH_ROOTS = frozenset({"Path(__file__)", "pathlib.Path(__file__)"})
_PATH_METHODS = frozenset({"resolve", "absolute"})
_PATH_ATTRS = frozenset({"parent", "parents", "name", "stem", "suffix"})
_PURE_LIBRARY_CALLS = frozenset({"re.compile", "logging.getLogger"})
_PURE_LIBRARY_ARGS = frozenset({"__name__", "re.I", "re.IGNORECASE", "re.M", "re.MULTILINE", "re.S", "re.DOTALL",
                                "re.X", "re.VERBOSE", "re.UNICODE", "re.ASCII"})


def _pure_value(node: ast.AST, names: frozenset[str] | set[str] = frozenset()) -> bool:
    """True when evaluating ``node`` at import time can do nothing but compute a value."""
    try:
        ast.literal_eval(node)
        return True
    except (ValueError, TypeError, SyntaxError, RecursionError):
        pass
    if isinstance(node, ast.Name):
        return node.id in names or node.id in ("__name__", "__file__")
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return all(_pure_value(e, names) for e in node.elts)
    if isinstance(node, ast.JoinedStr):
        return all(isinstance(v, ast.Constant) or (isinstance(v, ast.FormattedValue) and _pure_value(v.value, names)) for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.Add, ast.BitOr)):
        return _pure_value(node.left, names) and _pure_value(node.right, names)
    if isinstance(node, ast.Attribute):
        text = ast.unparse(node)
        return text in _PURE_LIBRARY_ARGS or (node.attr in _PATH_ATTRS and _pure_value(node.value, names))
    if isinstance(node, ast.Subscript):
        return _pure_value(node.value, names) and _pure_value(node.slice, names)
    if isinstance(node, ast.Call):
        func = ast.unparse(node.func)
        if func in _PATH_ROOTS or ast.unparse(node) in _PATH_ROOTS:
            return True
        if isinstance(node.func, ast.Attribute) and node.func.attr in _PATH_METHODS and not node.args and not node.keywords:
            return _pure_value(node.func.value, names)
        if func in _PURE_LIBRARY_CALLS:
            return all(_pure_value(a, names) for a in node.args) and not node.keywords
        return func in PURE_CONSTRUCTORS and all(_pure_value(a, names) for a in node.args) and not node.keywords
    return False


def import_time_effects(tree: ast.Module) -> list[str]:
    """Top-level statements that would execute something other than a definition."""
    effects = []
    pure_names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            pure_names.add(node.name)
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            pure_names.update((a.asname or a.name).split(".")[0] for a in node.names)
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        if isinstance(node, ast.If) and "__main__" in ast.unparse(node.test):
            continue
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None and _pure_value(node.value, pure_names):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            pure_names.update(t.id for t in targets if isinstance(t, ast.Name))
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
