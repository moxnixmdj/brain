"""Fail-closed pure consumer guard for field-scoped currentness.

A qualifying consumer is intentionally much smaller than general Python:
- module body contains only function definitions and optional string docstrings;
- no imports, attributes, classes, lambdas, loops, comprehensions, exceptions,
  async/generators, dynamic evaluation, mutation through subscripts/attributes,
  or unknown globals;
- calls target only a fixed safe-builtin allowlist or other statically verified
  local functions;
- the local call graph must be acyclic;
- execution receives only a plain JSON projection and a restricted builtins map.

This makes filesystem/network/process/ambient-repository access unavailable by
construction for this consumer class. It grants zero execution, promotion,
acceptance, ownership, capability, fresh-reality, or terminal authority.
"""
from __future__ import annotations

import ast
import hashlib
import json
from collections.abc import Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_PURE_PROJECTION_CONSUMER_GUARD_V1"
MAX_SOURCE_BYTES = 65_536
MAX_PROJECTION_BYTES = 1_000_000
MAX_AST_NODES = 5_000
MAX_FUNCTIONS = 64

SAFE_BUILTINS: dict[str, Any] = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "float": float,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "round": round,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
}

_ALLOWED_NODE_TYPES = {
    ast.Module,
    ast.FunctionDef,
    ast.arguments,
    ast.arg,
    ast.Return,
    ast.Assign,
    ast.If,
    ast.Pass,
    ast.Expr,
    ast.Name,
    ast.Constant,
    ast.Subscript,
    ast.Slice,
    ast.List,
    ast.Tuple,
    ast.Dict,
    ast.BinOp,
    ast.BoolOp,
    ast.UnaryOp,
    ast.Compare,
    ast.IfExp,
    ast.Call,
    ast.keyword,
    ast.JoinedStr,
    ast.FormattedValue,
    ast.Load,
    ast.Store,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.And,
    ast.Or,
    ast.Not,
    ast.USub,
    ast.UAdd,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.Is,
    ast.IsNot,
    ast.In,
    ast.NotIn,
}


class PureProjectionConsumerError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _docstring_expr(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _simple_assign_targets(node: ast.Assign) -> list[str]:
    out: list[str] = []
    for target in node.targets:
        if not isinstance(target, ast.Name):
            raise PureProjectionConsumerError(
                "ASSIGN_TARGET_MUST_BE_LOCAL_NAME"
            )
        out.append(target.id)
    return out


def _function_names(tree: ast.Module) -> set[str]:
    names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    if len(names) > MAX_FUNCTIONS:
        raise PureProjectionConsumerError("TOO_MANY_FUNCTIONS")
    if any("__" in name for name in names):
        raise PureProjectionConsumerError("DUNDER_FUNCTION_NAME_FORBIDDEN")
    return names


def _validate_module_shape(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    funcs: dict[str, ast.FunctionDef] = {}
    for i, node in enumerate(tree.body):
        if _docstring_expr(node) and i == 0:
            continue
        if not isinstance(node, ast.FunctionDef):
            raise PureProjectionConsumerError(
                "MODULE_BODY_MUST_CONTAIN_ONLY_FUNCTIONS"
            )
        if node.name in funcs:
            raise PureProjectionConsumerError(
                "DUPLICATE_FUNCTION:" + node.name
            )
        if (
            node.decorator_list
            or node.returns is not None
            or node.type_comment is not None
            or node.args.vararg is not None
            or node.args.kwarg is not None
            or node.args.kwonlyargs
            or node.args.defaults
            or node.args.kw_defaults
            or any(arg.annotation is not None for arg in node.args.args)
            or node.args.posonlyargs
        ):
            raise PureProjectionConsumerError(
                "FUNCTION_SIGNATURE_OUTSIDE_PURE_SUBSET:" + node.name
            )
        if len(node.args.args) > 8:
            raise PureProjectionConsumerError(
                "TOO_MANY_FUNCTION_ARGUMENTS:" + node.name
            )
        funcs[node.name] = node

    if "evaluate" not in funcs:
        raise PureProjectionConsumerError("EVALUATE_ENTRY_REQUIRED")
    entry = funcs["evaluate"]
    if [x.arg for x in entry.args.args] != ["projection"]:
        raise PureProjectionConsumerError(
            "EVALUATE_SIGNATURE_MUST_BE_EVALUATE_PROJECTION"
        )
    return funcs


def _assigned_names(fn: ast.FunctionDef) -> set[str]:
    out = {arg.arg for arg in fn.args.args}
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            out.update(_simple_assign_targets(node))
    return out


def _validate_function(
    fn: ast.FunctionDef,
    *,
    local_functions: set[str],
) -> set[str]:
    if any("__" in arg.arg for arg in fn.args.args):
        raise PureProjectionConsumerError(
            "DUNDER_ARGUMENT_FORBIDDEN:" + fn.name
        )

    assigned = _assigned_names(fn)
    if any("__" in name for name in assigned):
        raise PureProjectionConsumerError(
            "DUNDER_LOCAL_NAME_FORBIDDEN:" + fn.name
        )

    calls: set[str] = set()
    body_nodes = list(ast.walk(fn))
    for node in body_nodes:
        if type(node) not in _ALLOWED_NODE_TYPES:
            raise PureProjectionConsumerError(
                "AST_NODE_FORBIDDEN:"
                + fn.name
                + ":"
                + type(node).__name__
            )

        if isinstance(node, ast.Expr) and not _docstring_expr(node):
            raise PureProjectionConsumerError(
                "EXPRESSION_STATEMENT_FORBIDDEN:" + fn.name
            )

        if isinstance(node, ast.Name):
            if "__" in node.id:
                raise PureProjectionConsumerError(
                    "DUNDER_NAME_FORBIDDEN:" + fn.name + ":" + node.id
                )
            if isinstance(node.ctx, ast.Load):
                allowed = (
                    node.id in assigned
                    or node.id in local_functions
                    or node.id in SAFE_BUILTINS
                )
                if not allowed:
                    raise PureProjectionConsumerError(
                        "UNKNOWN_GLOBAL_NAME:" + fn.name + ":" + node.id
                    )

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise PureProjectionConsumerError(
                    "CALL_TARGET_MUST_BE_NAME:" + fn.name
                )
            target = node.func.id
            if target not in SAFE_BUILTINS and target not in local_functions:
                raise PureProjectionConsumerError(
                    "CALL_TARGET_FORBIDDEN:" + fn.name + ":" + target
                )
            if any(keyword.arg is None for keyword in node.keywords):
                raise PureProjectionConsumerError(
                    "KWARG_EXPANSION_FORBIDDEN:" + fn.name
                )
            if target in local_functions:
                calls.add(target)

        if isinstance(node, ast.Assign):
            _simple_assign_targets(node)

    return calls


def _assert_acyclic(graph: Mapping[str, set[str]]) -> None:
    visiting: set[str] = set()
    done: set[str] = set()

    def visit(name: str) -> None:
        if name in done:
            return
        if name in visiting:
            raise PureProjectionConsumerError(
                "LOCAL_CALL_GRAPH_CYCLE:" + name
            )
        visiting.add(name)
        for child in graph.get(name, set()):
            visit(child)
        visiting.remove(name)
        done.add(name)

    for name in sorted(graph):
        visit(name)


def verify_source(source: str) -> dict[str, Any]:
    if not isinstance(source, str) or not source:
        raise PureProjectionConsumerError("CONSUMER_SOURCE_REQUIRED")
    raw = source.encode("utf-8")
    if len(raw) > MAX_SOURCE_BYTES:
        raise PureProjectionConsumerError("CONSUMER_SOURCE_TOO_LARGE")

    try:
        tree = ast.parse(source, filename="<pure-projection-consumer>")
    except SyntaxError as exc:
        raise PureProjectionConsumerError(
            "CONSUMER_SYNTAX_ERROR:" + str(exc)
        ) from exc

    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_AST_NODES:
        raise PureProjectionConsumerError("CONSUMER_AST_TOO_LARGE")

    funcs = _validate_module_shape(tree)
    function_names = _function_names(tree)
    graph = {
        name: _validate_function(fn, local_functions=function_names)
        for name, fn in funcs.items()
    }
    _assert_acyclic(graph)

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__PURE_PROJECTION_CONSUMER_STATIC_GUARD",
        "consumer_source_sha256": _sha256(raw),
        "ast_node_count": len(nodes),
        "function_count": len(funcs),
        "local_call_graph": {
            name: sorted(children)
            for name, children in sorted(graph.items())
        },
        "imports_allowed": False,
        "attribute_access_allowed": False,
        "ambient_io_calls_allowed": False,
        "dynamic_evaluation_allowed": False,
        "loops_or_comprehensions_allowed": False,
        "recursion_allowed": False,
        "execution_authority": False,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }


def evaluate_pure_consumer(
    *,
    source: str,
    projection: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        verification = verify_source(source)
        if not isinstance(projection, Mapping):
            raise PureProjectionConsumerError("PROJECTION_MAPPING_REQUIRED")
        projection_bytes = _canon(projection)
        if len(projection_bytes) > MAX_PROJECTION_BYTES:
            raise PureProjectionConsumerError("PROJECTION_TOO_LARGE")

        tree = ast.parse(source, filename="<pure-projection-consumer>")
        code = compile(tree, "<pure-projection-consumer>", "exec")
        namespace: dict[str, Any] = {
            "__builtins__": dict(SAFE_BUILTINS),
        }
        exec(code, namespace, namespace)
        entry = namespace.get("evaluate")
        if not callable(entry):
            raise PureProjectionConsumerError("EVALUATE_ENTRY_NOT_CALLABLE")

        result = entry(json.loads(projection_bytes.decode("utf-8")))
        if not isinstance(result, Mapping):
            raise PureProjectionConsumerError(
                "CONSUMER_RESULT_MUST_BE_MAPPING"
            )
        result_bytes = _canon(dict(result))

        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__PURE_PROJECTION_CONSUMER_EXECUTION",
            "consumer_source_sha256": verification["consumer_source_sha256"],
            "projection_sha256": _sha256(projection_bytes),
            "consumer_result_sha256": _sha256(result_bytes),
            "consumer_result": dict(result),
            "static_verification": verification,
            "ambient_repository_access_available": False,
            "filesystem_access_available": False,
            "network_access_available": False,
            "process_access_available": False,
            "execution_authority": False,
            "promotion_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "terminal_credit_delta": 0,
            "rule": (
                "PURE_CONSUMER_CAN_OBSERVE_ONLY_PLAIN_JSON_PROJECTION_AND_"
                "FIXED_SAFE_BUILTINS"
            ),
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "error": type(exc).__name__ + ":" + str(exc),
            "ambient_repository_access_available": None,
            "filesystem_access_available": None,
            "network_access_available": None,
            "process_access_available": None,
            "execution_authority": False,
            "promotion_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "terminal_credit_delta": 0,
        }
