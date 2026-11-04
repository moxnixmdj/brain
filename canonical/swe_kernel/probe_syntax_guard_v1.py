"""Conservative syntax gate for the local input-sensitivity probe.

This is a deliberately incomplete Python subset, not a general Python sandbox or
an independent carrier qualification. The probe runs only with literal inputs;
source that can import, inspect frames, access attributes, use arbitrary calls,
install definition-time hooks or execute module-level statements is declined.
The existing namespace remains necessary for resource limits and isolation.
"""
from __future__ import annotations

import ast
import builtins

MAX_SOURCE_BYTES = 400_000
MAX_NODES = 12_000
MAX_LITERAL_SIZE = 4096

# Language constructs and bounded, side-effect-free builtins, not a mapping
# from error types to repairs. Anything outside the subset is an abstention.
_ALLOWED = {
    ast.Module, ast.FunctionDef, ast.arguments, ast.arg,
    ast.Expr, ast.Return, ast.Assign, ast.AnnAssign, ast.AugAssign,
    ast.If, ast.While, ast.For, ast.Break, ast.Continue, ast.Pass,
    ast.Name, ast.Load, ast.Store, ast.Constant,
    ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp,
    ast.List, ast.Tuple, ast.Set, ast.Dict, ast.Subscript, ast.Slice,
    ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.comprehension,
    ast.Call, ast.keyword,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.UAdd, ast.USub, ast.Not, ast.And, ast.Or,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Is, ast.IsNot,
    ast.In, ast.NotIn,
}
_SAFE_CALLS = frozenset({"abs", "len", "max", "min", "range", "sum", "zip"})
_BUILTINS = frozenset(dir(builtins))


def probe_source_supported(source: str) -> tuple[bool, str]:
    """Check the whole module without importing or executing it.

    This only removes known high-risk language features. It cannot prove an
    arbitrary Python interpreter or the namespace carrier safe.
    """
    if not isinstance(source, str) or len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        return False, "source size"
    try:
        tree = ast.parse(source)
        nodes = list(ast.walk(tree))
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return False, "parse"
    if len(nodes) > MAX_NODES:
        return False, "node budget"
    for top in tree.body:
        if isinstance(top, ast.FunctionDef):
            continue
        if isinstance(top, ast.Expr) and isinstance(top.value, ast.Constant) and isinstance(top.value.value, str):
            continue
        return False, "module side effect or unsupported definition"
    for node in nodes:
        if type(node) not in _ALLOWED:
            return False, f"unsupported syntax {type(node).__name__}"
        if isinstance(node, ast.FunctionDef):
            args = node.args
            all_args = (*args.posonlyargs, *args.args, *args.kwonlyargs,
                        *([args.vararg] if args.vararg else []),
                        *([args.kwarg] if args.kwarg else []))
            if ("__" in node.name or node.name in _SAFE_CALLS or node.decorator_list or args.defaults or
                    any(d is not None for d in args.kw_defaults) or node.returns is not None or
                    any(a.annotation is not None or "__" in a.arg or a.arg in _SAFE_CALLS for a in all_args)):
                return False, "definition-time hooks or private name"
        if isinstance(node, ast.AnnAssign):
            return False, "annotation"
        if isinstance(node, ast.Name):
            if "__" in node.id:
                return False, "private name"
            # Unsafe builtins cannot be laundered through an apparently safe
            # call, e.g. min([eval]) assigned to a name such as zip.
            if isinstance(node.ctx, ast.Load) and node.id in _BUILTINS and node.id not in _SAFE_CALLS:
                return False, "unsupported builtin"
            if isinstance(node.ctx, ast.Store) and node.id in _SAFE_CALLS:
                return False, "shadowed builtin"
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _SAFE_CALLS:
                return False, "unsupported call"
            # Safe builtins such as min/max accept callable `key=` arguments;
            # do not execute indirect or keyword-selected callbacks.
            if node.keywords:
                return False, "keyword call"
        if isinstance(node, ast.Constant):
            value = node.value
            if not (value is None or type(value) in (bool, int, float, str, bytes)):
                return False, "unsupported literal"
            if isinstance(value, (str, bytes)) and len(value) > MAX_LITERAL_SIZE:
                return False, "literal size"
            if type(value) is int and value.bit_length() > 256:
                return False, "numeric literal size"
    return True, "supported restricted syntax"


def simple_probe_name(expression: str) -> bool:
    """A test call target must be a direct non-private name, not Python code."""
    try:
        node = ast.parse(expression, mode="eval").body
    except (SyntaxError, ValueError, TypeError, RecursionError):
        return False
    return isinstance(node, ast.Name) and "__" not in node.id
