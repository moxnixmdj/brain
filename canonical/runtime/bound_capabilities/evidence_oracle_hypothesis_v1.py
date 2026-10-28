#!/usr/bin/env python3
"""Bounded Hypothesis checks for a safe subset of Python contract functions.

Only a single, pure, unary numeric return expression and its ``pre:``/``post:``
contract expressions are interpreted. Supplied source is never imported,
compiled, or executed. Unsupported code and unavailable Hypothesis fail
closed. A clean bounded sample is not a proof of contract correctness.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import operator
import pathlib
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_EVIDENCE_ORACLE_HYPOTHESIS_V1"
CAPABILITY_ID = "evidence.oracle.hypothesis_property.v1"
PROVIDES = ["evidence.property_test.verified"]
REQUIRES: list[str] = ["python.source.file.available"]

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg, ast.Not: operator.not_}
_COMPARE = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
            ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge}
_CALL = {"abs": abs, "min": min, "max": max}
_CONTRACT = re.compile(r"^\s*(?:-\s*)?(pre|post)(?:condition)?\s*:\s*(.+)$", re.I)


class _Unsupported(ValueError):
    pass


class _Counterexample(Exception):
    pass


def _number(value: Any) -> int | float | bool:
    if type(value) not in (int, float, bool) or abs(value) > 10**18 or not math.isfinite(value):
        raise _Unsupported("VALUE_OUTSIDE_NUMERIC_LIMITS")
    return value


def _validate(node: ast.AST, names: set[str]) -> None:
    """Validate before interpretation; no attribute access, indexing, or user calls."""
    if len(list(ast.walk(node))) > 256:
        raise _Unsupported("EXPRESSION_TOO_LARGE")
    def visit(n: ast.AST) -> None:
        if isinstance(n, ast.Constant):
            _number(n.value)
        elif isinstance(n, ast.Name) and n.id in names:
            return
        elif isinstance(n, ast.BinOp) and type(n.op) in _BIN:
            visit(n.left); visit(n.right)
        elif isinstance(n, ast.UnaryOp) and type(n.op) in _UNARY:
            visit(n.operand)
        elif isinstance(n, ast.BoolOp) and isinstance(n.op, (ast.And, ast.Or)):
            for item in n.values: visit(item)
        elif isinstance(n, ast.Compare) and all(type(op) in _COMPARE for op in n.ops):
            visit(n.left)
            for item in n.comparators: visit(item)
        elif isinstance(n, ast.IfExp):
            visit(n.test); visit(n.body); visit(n.orelse)
        elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
              and n.func.id in _CALL and not n.keywords and 1 <= len(n.args) <= 4
              and (n.func.id != "abs" or len(n.args) == 1)):
            for item in n.args: visit(item)
        else:
            raise _Unsupported("UNSUPPORTED_EXPRESSION:" + type(n).__name__)
    visit(node)


def _interpret(node: ast.AST, env: dict[str, int | float | bool]) -> int | float | bool:
    if isinstance(node, ast.Constant):
        return _number(node.value)
    if isinstance(node, ast.Name):
        return _number(env[node.id])
    if isinstance(node, ast.BinOp):
        return _number(_BIN[type(node.op)](_interpret(node.left, env), _interpret(node.right, env)))
    if isinstance(node, ast.UnaryOp):
        return _number(_UNARY[type(node.op)](_interpret(node.operand, env)))
    if isinstance(node, ast.BoolOp):
        value = _interpret(node.values[0], env)
        for item in node.values[1:]:
            if (isinstance(node.op, ast.And) and not value) or (isinstance(node.op, ast.Or) and value):
                break
            value = _interpret(item, env)
        return value
    if isinstance(node, ast.Compare):
        left = _interpret(node.left, env)
        for op, item in zip(node.ops, node.comparators):
            right = _interpret(item, env)
            if not _COMPARE[type(op)](left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.IfExp):
        return _interpret(node.body if _interpret(node.test, env) else node.orelse, env)
    if isinstance(node, ast.Call):
        return _number(_CALL[node.func.id](*[_interpret(arg, env) for arg in node.args]))
    raise _Unsupported("UNSUPPORTED_EXPRESSION:" + type(node).__name__)


def _parse(source: str) -> tuple[str, ast.AST, list[ast.AST], list[tuple[str, ast.AST]]]:
    if not source or len(source.encode("utf-8")) > 65536:
        raise _Unsupported("NO_SOURCE_OR_SOURCE_TOO_LARGE")
    try:
        module = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise _Unsupported("SYNTAX_ERROR") from exc
    body = list(module.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body.pop(0)
    if len(body) != 1 or not isinstance(body[0], ast.FunctionDef):
        raise _Unsupported("REQUIRES_SINGLE_PURE_FUNCTION")
    fn = body[0]
    positional = list(fn.args.posonlyargs) + list(fn.args.args)
    if (len(positional) != 1 or fn.args.vararg or fn.args.kwarg or fn.args.kwonlyargs
            or fn.args.defaults or fn.decorator_list):
        raise _Unsupported("REQUIRES_UNARY_UNDECORATED_FUNCTION")
    arg = positional[0].arg
    if arg in {"_", "result", "__return__", *_CALL}:
        raise _Unsupported("RESERVED_ARGUMENT_NAME")
    for annotation in (positional[0].annotation, fn.returns):
        if annotation is not None and not (isinstance(annotation, ast.Name) and annotation.id in {"int", "float"}):
            raise _Unsupported("UNSUPPORTED_ANNOTATION")
    fn_body = list(fn.body)
    doc = ast.get_docstring(fn) or ""
    if doc:
        fn_body.pop(0)
    if len(fn_body) != 1 or not isinstance(fn_body[0], ast.Return) or fn_body[0].value is None:
        raise _Unsupported("REQUIRES_SINGLE_RETURN_EXPRESSION")
    expression = fn_body[0].value
    _validate(expression, {arg})
    pre: list[ast.AST] = []
    post: list[tuple[str, ast.AST]] = []
    for line in doc.splitlines():
        match = _CONTRACT.match(line)
        if not match:
            continue
        text = match.group(2).strip()
        try:
            contract = ast.parse(text, mode="eval").body
        except (SyntaxError, ValueError, RecursionError) as exc:
            raise _Unsupported("INVALID_CONTRACT_EXPRESSION") from exc
        is_pre = match.group(1).lower() == "pre"
        _validate(contract, {arg} if is_pre else {arg, "_", "result", "__return__"})
        if is_pre:
            pre.append(contract)
        else:
            post.append((text, contract))
    if not post:
        raise _Unsupported("NO_DECLARED_POSTCONDITION")
    return arg, expression, pre, post


def _check(source: str) -> dict[str, Any]:
    try:
        import hypothesis
        from hypothesis import HealthCheck, given, settings, strategies as st
    except ImportError:
        return {"status": "HYPOTHESIS_UNAVAILABLE", "hypothesis_available": False,
                "checked": 0, "violations": []}
    try:
        arg, expression, pre, post = _parse(source)
    except (_Unsupported, RecursionError) as exc:
        return {"status": "UNSUPPORTED_SOURCE", "reason": str(exc),
                "hypothesis_available": True, "checked": 0, "violations": []}

    checked = 0
    witness: dict[str, Any] = {}

    @settings(max_examples=50, derandomize=True, deadline=None, database=None,
              suppress_health_check=[HealthCheck.filter_too_much])
    @given(st.integers(min_value=-1000, max_value=1000))
    def probe(value: int) -> None:
        nonlocal checked, witness
        env = {arg: value}
        for condition in pre:
            try:
                accepted = bool(_interpret(condition, env))
            except (ArithmeticError, ValueError, TypeError) as exc:
                raise _Unsupported("PRECONDITION_UNEVALUABLE:" + type(exc).__name__) from exc
            hypothesis.assume(accepted)
        checked += 1
        try:
            returned = _interpret(expression, env)
        except _Unsupported:
            raise
        except (ArithmeticError, ValueError, TypeError) as exc:
            # A postcondition constrains a returned value, not which exceptions
            # the program may raise; exception contracts are not supported.
            raise _Unsupported("FUNCTION_EXPRESSION_RAISED:" + type(exc).__name__) from exc
        env.update({"_": returned, "result": returned, "__return__": returned})
        for text, condition in post:
            try:
                holds = bool(_interpret(condition, env))
            except _Unsupported:
                raise
            except (ArithmeticError, ValueError, TypeError) as exc:
                raise _Unsupported("POSTCONDITION_UNEVALUABLE:" + type(exc).__name__) from exc
            if not holds:
                witness = {"input": value, "post": text, "returned": returned}
                raise _Counterexample()

    try:
        probe()
        status = "NO_COUNTEREXAMPLE_IN_SAMPLE" if checked else "NO_INPUTS_CHECKED"
    except _Counterexample:
        status = "CONTRACT_VIOLATION_FOUND"
    except hypothesis.errors.Unsatisfiable:
        status = "NO_INPUTS_SATISFY_PRECONDITIONS"
    except (_Unsupported, RecursionError) as exc:
        return {"status": "UNSUPPORTED_EVALUATION", "reason": str(exc),
                "hypothesis_available": True, "checked": checked, "violations": []}
    return {"status": status, "hypothesis_available": True, "checked": checked,
            "violations": [witness] if status == "CONTRACT_VIOLATION_FOUND" else [],
            "input_range": [-1000, 1000], "max_examples": 50}


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = (repo / str(args.get("output_path") or "canonical/tmp_evidence_hypothesis.json")).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if output.is_file() and (output.suffix == ".py" or output.stat().st_nlink > 1):
        raise RuntimeError("OUTPUT_OVERLAPS_INPUT")
    source = args.get("source")
    source_path = args.get("source_path")
    if source_path:
        path = (repo / str(source_path)).resolve()
        if path == repo or repo not in path.parents:
            raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
        if path == output or (path.exists() and output.exists() and path.samefile(output)):
            raise RuntimeError("OUTPUT_OVERLAPS_INPUT")
        if source is None:
            source = path.read_text(encoding="utf-8")
    if not isinstance(source, str):
        source = ""
    result = _check(source)
    verified = result["status"] == "NO_COUNTEREXAMPLE_IN_SAMPLE" and result["checked"] > 0
    artifact = {"schema": SCHEMA, "capability_id": CAPABILITY_ID,
                "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                **result, "proves_absence": False, "verified": verified,
                "model_dependency_count": 0, "incremental_spend_usd": 0}
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    return {"adapter": "evidence_oracle_hypothesis_v1", "output_path": str(output.relative_to(repo)),
            "output_sha256": hashlib.sha256(raw).hexdigest(), "output_verified": output.read_bytes() == raw,
            **{key: value for key, value in artifact.items() if key not in {"schema", "capability_id"}}}
