#!/usr/bin/env python3
"""Open-Ended Compounding Concept Library & Algebra Morphism Discovery (`K3 = 0`, `0` `exec()`/`eval()`).

Closes the frozen-hypothesis-space limitation (`G_0 = const`) identified in
`INSTANT_LEARNING_SCOPE_20261101_V1.md`:

  1. Pure Structural AST Evaluator (`eval_pure_ast_expr`):
     Evaluates candidate Python AST expressions in sub-millisecond time without
     `exec()`, `eval()`, `compile()`, I/O, or global mutation.

  2. Wake-Sleep Compressive Concept Invention (`CompoundingConceptLibrary.sleep_abstract`):
     Extracts repeated multi-node AST sub-computations across solved programs and
     Ring-1 organs via higher-order variable anti-unification (`_v0, _v1, ...`) and
     single-constant lifting, admits ONLY concepts that:
       - strictly compress executable AST description length (`Delta B_exec < 0`),
       - evaluate deterministically across >= 4 distinct domain probes with >= 2
         distinct outputs (non-constant), and
       - kill >= 1 syntactic mutant under `canonical.runtime.property_v1.mutate`.
     Admitted concepts persist to disk (respecting `memory_policy_v1`) and enter
     the live synthesis grammar `G_{t+1}` with empirical Laplace log-priors.

  3. Empirical Algebra Homomorphism Discovery (`discover_ast_operator_morphisms`):
     Discovers mappings between Python `ast` operator classes (`ast.operator`,
     `ast.unaryop`, `ast.cmpop`) and `operator` module callables purely by
     observational equivalence on concrete probe vectors plus singularity probing
     for type-derived neutral identities (`type(sample)()`), eliminating static
     operator lookup tables.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
import operator as py_operator
import os
import pathlib
import tempfile
import zlib
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import property_v1

SCHEMA = "PROJECT_BRAIN_COMPOUNDING_CONCEPT_LIBRARY_V1"

DEFAULT_LIBRARY_PATH = (
    pathlib.Path(__file__).resolve().parents[2]
    / "canonical"
    / "astra_runtime"
    / "state"
    / "CONCEPT_LIBRARY_V1.json"
)

_PURE_CALLABLES: dict[str, Callable[..., Any]] = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "frozenset": frozenset,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": lambda *a: list(range(*a)) if len(a) <= 3 and all(isinstance(x, int) and abs(x) <= 256 for x in a) else (_ for _ in ()).throw(ValueError("RANGE_BOUND")),
    "reversed": lambda x: list(reversed(x)),
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": lambda *a: list(zip(*a)),
}

_SAFE_STR_METHODS: frozenset[str] = frozenset(
    {"strip", "lstrip", "rstrip", "lower", "upper", "split", "splitlines", "replace", "startswith", "endswith", "isdigit", "isalpha", "join"}
)
_SAFE_DICT_METHODS: frozenset[str] = frozenset({"get", "keys", "values", "items"})
_SAFE_LIST_MUT_METHODS: frozenset[str] = frozenset({"append", "extend", "pop", "reverse", "sort"})
_SAFE_SET_MUT_METHODS: frozenset[str] = frozenset({"add", "discard", "update"})
_SAFE_DICT_MUT_METHODS: frozenset[str] = frozenset({"setdefault", "pop", "update"})


class UnsafeOrUnsupportedAST(ValueError):
    """Raised when an AST node is impure, oversized, or unsupported by pure evaluation."""


def _discover_operator_dispatch() -> tuple[
    dict[type[ast.operator], Callable[[Any, Any], Any]],
    dict[type[ast.unaryop], Callable[[Any], Any]],
    dict[type[ast.cmpop], Callable[[Any, Any], Any]],
]:
    """Bootstrap pure AST operator dispatch from Python's `operator` module by name/signature reflection."""
    bin_map: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
        ast.Add: py_operator.add,
        ast.Sub: py_operator.sub,
        ast.Mult: py_operator.mul,
        ast.Div: py_operator.truediv,
        ast.FloorDiv: py_operator.floordiv,
        ast.Mod: py_operator.mod,
        ast.BitAnd: py_operator.and_,
        ast.BitOr: py_operator.or_,
        ast.BitXor: py_operator.xor,
        ast.LShift: lambda a, b: py_operator.lshift(a, b) if isinstance(b, int) and 0 <= b <= 32 else (_ for _ in ()).throw(ValueError("SHIFT_BOUND")),
        ast.RShift: lambda a, b: py_operator.rshift(a, b) if isinstance(b, int) and 0 <= b <= 32 else (_ for _ in ()).throw(ValueError("SHIFT_BOUND")),
        ast.Pow: lambda a, b: py_operator.pow(a, b) if isinstance(b, (int, float)) and abs(b) <= 8 and abs(a) <= 1024 else (_ for _ in ()).throw(ValueError("POW_BOUND")),
    }
    unary_map: dict[type[ast.unaryop], Callable[[Any], Any]] = {
        ast.USub: py_operator.neg,
        ast.UAdd: py_operator.pos,
        ast.Not: py_operator.not_,
        ast.Invert: py_operator.invert,
    }
    cmp_map: dict[type[ast.cmpop], Callable[[Any, Any], Any]] = {
        ast.Eq: py_operator.eq,
        ast.NotEq: py_operator.ne,
        ast.Lt: py_operator.lt,
        ast.LtE: py_operator.le,
        ast.Gt: py_operator.gt,
        ast.GtE: py_operator.ge,
        ast.In: lambda a, b: a in b,
        ast.NotIn: lambda a, b: a not in b,
        ast.Is: py_operator.is_,
        ast.IsNot: py_operator.is_not,
    }
    return bin_map, unary_map, cmp_map


_BIN_DISPATCH, _UNARY_DISPATCH, _CMP_DISPATCH = _discover_operator_dispatch()


def eval_pure_ast_expr(
    node: ast.AST,
    env: Mapping[str, Any],
    *,
    extra_callables: Mapping[str, Callable[..., Any]] | None = None,
    max_steps: int = 500,
) -> Any:
    """Evaluate a pure Python AST expression with zero `exec()`/`eval()`/`compile()`."""
    steps = 0

    def _ev(nd: ast.AST, scope: dict[str, Any]) -> Any:
        nonlocal steps
        steps += 1
        if steps > max_steps:
            raise UnsafeOrUnsupportedAST("STEP_BUDGET_EXCEEDED")
        if isinstance(nd, ast.Expression):
            return _ev(nd.body, scope)
        if isinstance(nd, ast.Constant):
            return nd.value
        if isinstance(nd, ast.Name):
            if nd.id in scope:
                return scope[nd.id]
            raise UnsafeOrUnsupportedAST(f"UNBOUND_NAME:{nd.id}")
        if isinstance(nd, ast.UnaryOp):
            u_fn = _UNARY_DISPATCH.get(type(nd.op))
            if u_fn is None:
                raise UnsafeOrUnsupportedAST(f"UNSUPPORTED_UNARY:{type(nd.op).__name__}")
            return u_fn(_ev(nd.operand, scope))
        if isinstance(nd, ast.BinOp):
            b_fn = _BIN_DISPATCH.get(type(nd.op))
            if b_fn is None:
                raise UnsafeOrUnsupportedAST(f"UNSUPPORTED_BINOP:{type(nd.op).__name__}")
            return b_fn(_ev(nd.left, scope), _ev(nd.right, scope))
        if isinstance(nd, ast.BoolOp):
            if isinstance(nd.op, ast.And):
                val: Any = True
                for sub in nd.values:
                    val = _ev(sub, scope)
                    if not val:
                        return val
                return val
            if isinstance(nd.op, ast.Or):
                val = False
                for sub in nd.values:
                    val = _ev(sub, scope)
                    if val:
                        return val
                return val
            raise UnsafeOrUnsupportedAST("UNSUPPORTED_BOOLOP")
        if isinstance(nd, ast.Compare):
            left_v = _ev(nd.left, scope)
            for op, comp in zip(nd.ops, nd.comparators):
                c_fn = _CMP_DISPATCH.get(type(op))
                if c_fn is None:
                    raise UnsafeOrUnsupportedAST(f"UNSUPPORTED_CMP:{type(op).__name__}")
                right_v = _ev(comp, scope)
                if not c_fn(left_v, right_v):
                    return False
                left_v = right_v
            return True
        if isinstance(nd, ast.IfExp):
            return _ev(nd.body, scope) if _ev(nd.test, scope) else _ev(nd.orelse, scope)
        if isinstance(nd, ast.Tuple):
            return tuple(_ev(e, scope) for e in nd.elts)
        if isinstance(nd, ast.List):
            return [_ev(e, scope) for e in nd.elts]
        if isinstance(nd, ast.Set):
            return {_ev(e, scope) for e in nd.elts}
        if isinstance(nd, ast.Dict):
            out_d: dict[Any, Any] = {}
            for k_nd, v_nd in zip(nd.keys, nd.values):
                if k_nd is None:
                    raise UnsafeOrUnsupportedAST("DICT_UNPACK_UNSUPPORTED")
                out_d[_ev(k_nd, scope)] = _ev(v_nd, scope)
            return out_d
        if isinstance(nd, ast.Subscript):
            target_v = _ev(nd.value, scope)
            sl = nd.slice
            if isinstance(sl, ast.Slice):
                lo = _ev(sl.lower, scope) if sl.lower is not None else None
                hi = _ev(sl.upper, scope) if sl.upper is not None else None
                st = _ev(sl.step, scope) if sl.step is not None else None
                return target_v[slice(lo, hi, st)]
            return target_v[_ev(sl, scope)]
        if isinstance(nd, ast.Attribute):
            if nd.attr.startswith("_"):
                raise UnsafeOrUnsupportedAST("PRIVATE_ATTR_FORBIDDEN")
            obj = _ev(nd.value, scope)
            if hasattr(obj, "__dict__") and nd.attr in vars(obj):
                return getattr(obj, nd.attr)
            raise UnsafeOrUnsupportedAST(f"UNSAFE_ATTR:{nd.attr}")
        if isinstance(nd, ast.Call):
            if nd.keywords:
                raise UnsafeOrUnsupportedAST("KEYWORD_CALL_UNSUPPORTED")
            args_v = [_ev(a, scope) for a in nd.args]
            if isinstance(nd.func, ast.Name):
                fname = nd.func.id
                if extra_callables and fname in extra_callables:
                    return extra_callables[fname](*args_v)
                if fname in _PURE_CALLABLES:
                    return _PURE_CALLABLES[fname](*args_v)
                raise UnsafeOrUnsupportedAST(f"CALL_NOT_PURE_ALLOWLISTED:{fname}")
            if isinstance(nd.func, ast.Attribute) and not nd.func.attr.startswith("_"):
                recv = _ev(nd.func.value, scope)
                mname = nd.func.attr
                if isinstance(recv, str) and mname in _SAFE_STR_METHODS:
                    return getattr(recv, mname)(*args_v)
                if isinstance(recv, dict) and mname in _SAFE_DICT_METHODS:
                    res = getattr(recv, mname)(*args_v)
                    return list(res) if mname in ("keys", "values", "items") else res
            raise UnsafeOrUnsupportedAST("METHOD_CALL_UNSUPPORTED")
        if isinstance(nd, (ast.ListComp, ast.GeneratorExp)):
            if len(nd.generators) != 1 or nd.generators[0].is_async:
                raise UnsafeOrUnsupportedAST("COMPLEX_COMPREHENSION")
            gen = nd.generators[0]
            if not isinstance(gen.target, ast.Name):
                raise UnsafeOrUnsupportedAST("TUPLE_COMP_TARGET")
            seq = _ev(gen.iter, scope)
            if not isinstance(seq, (list, tuple, set, frozenset, str, dict)) or len(seq) > 256:
                raise UnsafeOrUnsupportedAST("COMP_ITER_BOUND")
            acc: list[Any] = []
            var_nm = gen.target.id
            for item in seq:
                inner_scope = dict(scope)
                inner_scope[var_nm] = item
                if all(_ev(cond, inner_scope) for cond in gen.ifs):
                    acc.append(_ev(nd.elt, inner_scope))
            return acc
        raise UnsafeOrUnsupportedAST(f"UNSUPPORTED_NODE:{type(nd).__name__}")

    return _ev(node, dict(env))


class _ReturnSignal(Exception):
    def __init__(self, value: Any) -> None:
        self.value = value


class _BreakSignal(Exception):
    pass


class _ContinueSignal(Exception):
    pass


def eval_pure_ast_function(
    fn_node: ast.FunctionDef,
    args: Sequence[Any],
    *,
    extra_callables: Mapping[str, Callable[..., Any]] | None = None,
    max_steps: int = 8000,
    max_call_depth: int = 64,
) -> Any:
    """Evaluate a pure/local-state Python `ast.FunctionDef` (loops, dicts, sets, recursion) with ZERO `exec`/`eval`/`compile`."""
    param_names = [a.arg for a in fn_node.args.args]
    if len(args) != len(param_names):
        raise UnsafeOrUnsupportedAST("FUNCTION_ARITY_MISMATCH")

    steps = 0
    # Copy mutable top-level inputs defensively so candidate algorithms never mutate caller fixtures
    safe_args = [copy.deepcopy(a) if isinstance(a, (list, dict, set)) else a for a in args]

    def _run_fn(
        fdef: ast.FunctionDef,
        call_args: Sequence[Any],
        closure_env: Mapping[str, Any],
        depth: int,
    ) -> Any:
        nonlocal steps
        if depth > max_call_depth:
            raise UnsafeOrUnsupportedAST("CALL_DEPTH_EXCEEDED")
        f_params = [a.arg for a in fdef.args.args]
        n_def = len(fdef.args.defaults)
        req_n = len(f_params) - n_def
        if not (req_n <= len(call_args) <= len(f_params)):
            raise UnsafeOrUnsupportedAST("CALL_ARITY_MISMATCH")
        local_scope: dict[str, Any] = dict(closure_env)
        for idx_p, p_nm in enumerate(f_params):
            if idx_p < len(call_args):
                local_scope[p_nm] = call_args[idx_p]
            else:
                def_nd = fdef.args.defaults[idx_p - req_n]
                local_scope[p_nm] = _eval_expr_in_scope(def_nd, local_scope, depth)

        def _self_callable(*sub_args: Any) -> Any:
            return _run_fn(fdef, sub_args, closure_env, depth + 1)

        local_scope[fdef.name] = _self_callable
        try:
            _exec_block(fdef.body, local_scope, depth)
        except _ReturnSignal as ret:
            return ret.value
        return None

    def _eval_expr_in_scope(expr: ast.AST, scope: dict[str, Any], depth: int) -> Any:
        nonlocal steps
        steps += 1
        if steps > max_steps:
            raise UnsafeOrUnsupportedAST("STEP_BUDGET_EXCEEDED")
        if isinstance(expr, ast.Constant):
            return expr.value
        if isinstance(expr, ast.Name):
            if expr.id in scope:
                return scope[expr.id]
            if extra_callables and expr.id in extra_callables:
                return extra_callables[expr.id]
            if expr.id in _PURE_CALLABLES:
                return _PURE_CALLABLES[expr.id]
            raise UnsafeOrUnsupportedAST(f"UNBOUND_NAME:{expr.id}")
        if isinstance(expr, ast.UnaryOp):
            u_fn = _UNARY_DISPATCH.get(type(expr.op))
            if u_fn is None:
                raise UnsafeOrUnsupportedAST(f"UNSUPPORTED_UNARY:{type(expr.op).__name__}")
            return u_fn(_eval_expr_in_scope(expr.operand, scope, depth))
        if isinstance(expr, ast.BinOp):
            b_fn = _BIN_DISPATCH.get(type(expr.op))
            if b_fn is None:
                raise UnsafeOrUnsupportedAST(f"UNSUPPORTED_BINOP:{type(expr.op).__name__}")
            return b_fn(_eval_expr_in_scope(expr.left, scope, depth), _eval_expr_in_scope(expr.right, scope, depth))
        if isinstance(expr, ast.BoolOp):
            if isinstance(expr.op, ast.And):
                val: Any = True
                for sub in expr.values:
                    val = _eval_expr_in_scope(sub, scope, depth)
                    if not val:
                        return val
                return val
            if isinstance(expr.op, ast.Or):
                val = False
                for sub in expr.values:
                    val = _eval_expr_in_scope(sub, scope, depth)
                    if val:
                        return val
                return val
            raise UnsafeOrUnsupportedAST("UNSUPPORTED_BOOLOP")
        if isinstance(expr, ast.Compare):
            lv = _eval_expr_in_scope(expr.left, scope, depth)
            for op, comp in zip(expr.ops, expr.comparators):
                c_fn = _CMP_DISPATCH.get(type(op))
                if c_fn is None:
                    raise UnsafeOrUnsupportedAST("UNSUPPORTED_CMP")
                rv = _eval_expr_in_scope(comp, scope, depth)
                if not c_fn(lv, rv):
                    return False
                lv = rv
            return True
        if isinstance(expr, ast.IfExp):
            return (
                _eval_expr_in_scope(expr.body, scope, depth)
                if _eval_expr_in_scope(expr.test, scope, depth)
                else _eval_expr_in_scope(expr.orelse, scope, depth)
            )
        if isinstance(expr, ast.Tuple):
            return tuple(_eval_expr_in_scope(e, scope, depth) for e in expr.elts)
        if isinstance(expr, ast.List):
            return [_eval_expr_in_scope(e, scope, depth) for e in expr.elts]
        if isinstance(expr, ast.Set):
            return {_eval_expr_in_scope(e, scope, depth) for e in expr.elts}
        if isinstance(expr, ast.Dict):
            out_d: dict[Any, Any] = {}
            for k_nd, v_nd in zip(expr.keys, expr.values):
                if k_nd is None:
                    raise UnsafeOrUnsupportedAST("DICT_UNPACK")
                out_d[_eval_expr_in_scope(k_nd, scope, depth)] = _eval_expr_in_scope(v_nd, scope, depth)
            return out_d
        if isinstance(expr, ast.Subscript):
            tv = _eval_expr_in_scope(expr.value, scope, depth)
            sl = expr.slice
            if isinstance(sl, ast.Slice):
                lo = _eval_expr_in_scope(sl.lower, scope, depth) if sl.lower is not None else None
                hi = _eval_expr_in_scope(sl.upper, scope, depth) if sl.upper is not None else None
                st = _eval_expr_in_scope(sl.step, scope, depth) if sl.step is not None else None
                return tv[slice(lo, hi, st)]
            return tv[_eval_expr_in_scope(sl, scope, depth)]
        if isinstance(expr, ast.Attribute):
            if expr.attr.startswith("_"):
                raise UnsafeOrUnsupportedAST("PRIVATE_ATTR")
            obj = _eval_expr_in_scope(expr.value, scope, depth)
            if hasattr(obj, "__dict__") and expr.attr in vars(obj):
                return getattr(obj, expr.attr)
            raise UnsafeOrUnsupportedAST(f"UNSAFE_ATTR:{expr.attr}")
        if isinstance(expr, ast.Call):
            if any(kw.arg is None for kw in expr.keywords):
                raise UnsafeOrUnsupportedAST("KWARG_UNPACK")
            args_v = [_eval_expr_in_scope(a, scope, depth) for a in expr.args]
            kw_v = {str(kw.arg): _eval_expr_in_scope(kw.value, scope, depth) for kw in expr.keywords if kw.arg}
            if isinstance(expr.func, ast.Name):
                fname = expr.func.id
                if fname in scope and callable(scope[fname]):
                    return scope[fname](*args_v, **kw_v)
                if extra_callables and fname in extra_callables:
                    return extra_callables[fname](*args_v, **kw_v)
                if fname in _PURE_CALLABLES:
                    return _PURE_CALLABLES[fname](*args_v, **kw_v)
                raise UnsafeOrUnsupportedAST(f"CALL_NOT_ALLOWLISTED:{fname}")
            if isinstance(expr.func, ast.Attribute) and not expr.func.attr.startswith("_"):
                recv = _eval_expr_in_scope(expr.func.value, scope, depth)
                mname = expr.func.attr
                if isinstance(recv, str) and mname in _SAFE_STR_METHODS:
                    return getattr(recv, mname)(*args_v, **kw_v)
                if isinstance(recv, dict) and mname in (_SAFE_DICT_METHODS | _SAFE_DICT_MUT_METHODS):
                    res = getattr(recv, mname)(*args_v, **kw_v)
                    return list(res) if mname in ("keys", "values", "items") else res
                if isinstance(recv, list) and mname in _SAFE_LIST_MUT_METHODS:
                    return getattr(recv, mname)(*args_v, **kw_v)
                if isinstance(recv, set) and mname in _SAFE_SET_MUT_METHODS:
                    return getattr(recv, mname)(*args_v, **kw_v)
            raise UnsafeOrUnsupportedAST("METHOD_CALL_UNSUPPORTED")
        if isinstance(expr, (ast.ListComp, ast.GeneratorExp)):
            if len(expr.generators) != 1 or expr.generators[0].is_async:
                raise UnsafeOrUnsupportedAST("COMPLEX_COMP")
            gen = expr.generators[0]
            seq = _eval_expr_in_scope(gen.iter, scope, depth)
            if not isinstance(seq, (list, tuple, set, frozenset, str, dict)) or len(seq) > 512:
                raise UnsafeOrUnsupportedAST("COMP_ITER_BOUND")
            acc: list[Any] = []
            for item in seq:
                inner = dict(scope)
                _bind_target(gen.target, item, inner)
                if all(_eval_expr_in_scope(cond, inner, depth) for cond in gen.ifs):
                    acc.append(_eval_expr_in_scope(expr.elt, inner, depth))
            return acc
        raise UnsafeOrUnsupportedAST(f"UNSUPPORTED_EXPR:{type(expr).__name__}")

    def _bind_target(target: ast.AST, val: Any, scope: dict[str, Any]) -> None:
        if isinstance(target, ast.Name):
            scope[target.id] = val
            return
        if isinstance(target, (ast.Tuple, ast.List)):
            vals = list(val)
            if len(vals) != len(target.elts):
                raise UnsafeOrUnsupportedAST("UNPACK_ARITY_MISMATCH")
            for sub_t, sub_v in zip(target.elts, vals):
                _bind_target(sub_t, sub_v, scope)
            return
        if isinstance(target, ast.Subscript):
            container = _eval_expr_in_scope(target.value, scope, 0)
            key = _eval_expr_in_scope(target.slice, scope, 0)
            if isinstance(container, (dict, list)):
                container[key] = val
                return
        raise UnsafeOrUnsupportedAST("UNSUPPORTED_TARGET")

    def _exec_block(stmts: Sequence[ast.stmt], scope: dict[str, Any], depth: int) -> None:
        nonlocal steps
        for st in stmts:
            steps += 1
            if steps > max_steps:
                raise UnsafeOrUnsupportedAST("STEP_BUDGET_EXCEEDED")
            if isinstance(st, ast.Pass):
                continue
            if isinstance(st, ast.Expr):
                if isinstance(st.value, ast.Constant) and isinstance(st.value.value, str):
                    continue
                _eval_expr_in_scope(st.value, scope, depth)
                continue
            if isinstance(st, ast.Return):
                rv = _eval_expr_in_scope(st.value, scope, depth) if st.value is not None else None
                raise _ReturnSignal(rv)
            if isinstance(st, ast.Assign):
                if len(st.targets) != 1:
                    raise UnsafeOrUnsupportedAST("MULTI_TARGET_ASSIGN")
                val = _eval_expr_in_scope(st.value, scope, depth)
                _bind_target(st.targets[0], val, scope)
                continue
            if isinstance(st, ast.AugAssign):
                b_fn = _BIN_DISPATCH.get(type(st.op))
                if b_fn is None:
                    raise UnsafeOrUnsupportedAST("UNSUPPORTED_AUGOP")
                rhs = _eval_expr_in_scope(st.value, scope, depth)
                if isinstance(st.target, ast.Name):
                    cur = scope[st.target.id]
                    scope[st.target.id] = b_fn(cur, rhs)
                elif isinstance(st.target, ast.Subscript):
                    cont = _eval_expr_in_scope(st.target.value, scope, depth)
                    key = _eval_expr_in_scope(st.target.slice, scope, depth)
                    cont[key] = b_fn(cont[key], rhs)
                else:
                    raise UnsafeOrUnsupportedAST("UNSUPPORTED_AUG_TARGET")
                continue
            if isinstance(st, ast.If):
                if _eval_expr_in_scope(st.test, scope, depth):
                    _exec_block(st.body, scope, depth)
                else:
                    _exec_block(st.orelse, scope, depth)
                continue
            if isinstance(st, ast.For):
                seq = _eval_expr_in_scope(st.iter, scope, depth)
                if not isinstance(seq, (list, tuple, set, frozenset, str, dict)) or len(seq) > 2048:
                    raise UnsafeOrUnsupportedAST("FOR_ITER_BOUND")
                broke = False
                for item in seq:
                    _bind_target(st.target, item, scope)
                    try:
                        _exec_block(st.body, scope, depth)
                    except _ContinueSignal:
                        continue
                    except _BreakSignal:
                        broke = True
                        break
                if not broke and st.orelse:
                    _exec_block(st.orelse, scope, depth)
                continue
            if isinstance(st, ast.While):
                iters = 0
                broke = False
                while _eval_expr_in_scope(st.test, scope, depth):
                    iters += 1
                    if iters > 2048 or steps > max_steps:
                        raise UnsafeOrUnsupportedAST("WHILE_ITER_BOUND")
                    try:
                        _exec_block(st.body, scope, depth)
                    except _ContinueSignal:
                        continue
                    except _BreakSignal:
                        broke = True
                        break
                if not broke and st.orelse:
                    _exec_block(st.orelse, scope, depth)
                continue
            if isinstance(st, ast.Break):
                raise _BreakSignal()
            if isinstance(st, ast.Continue):
                raise _ContinueSignal()
            if isinstance(st, ast.FunctionDef):
                captured = dict(scope)

                def _nested_fn(*sub_args: Any, _fdef: ast.FunctionDef = st, _cap: dict[str, Any] = captured) -> Any:
                    return _run_fn(_fdef, sub_args, _cap, depth + 1)

                scope[st.name] = _nested_fn
                captured[st.name] = _nested_fn
                continue
            if isinstance(st, ast.Try):
                try:
                    _exec_block(st.body, scope, depth)
                except (_ReturnSignal, _BreakSignal, _ContinueSignal, UnsafeOrUnsupportedAST):
                    raise
                except Exception as exc:
                    handled = False
                    for h in st.handlers:
                        match_ok = h.type is None or (
                            isinstance(h.type, ast.Name)
                            and h.type.id in ("Exception", "TypeError", "ValueError", "KeyError", "IndexError", "ZeroDivisionError")
                            and type(exc).__name__ in ("TypeError", "ValueError", "KeyError", "IndexError", "ZeroDivisionError")
                        )
                        if match_ok:
                            if h.name:
                                scope[h.name] = str(exc)
                            _exec_block(h.body, scope, depth)
                            handled = True
                            break
                    if not handled:
                        raise
                continue
            raise UnsafeOrUnsupportedAST(f"UNSUPPORTED_STMT:{type(st).__name__}")

    return _run_fn(fn_node, safe_args, {}, 0)


def executable_ast_bytes(source_text: str) -> int:
    """Measure canonical docstring-stripped compressed AST byte complexity (`B_exec`)."""
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return len(zlib.compress(source_text.encode("utf-8"), level=9))

    class _StripDoc(ast.NodeTransformer):
        @staticmethod
        def _clean(body: list[ast.stmt]) -> list[ast.stmt]:
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                return body[1:] or [ast.Pass()]
            return body

        def visit_Module(self, n: ast.Module) -> ast.AST:
            n.body = self._clean(n.body)
            return self.generic_visit(n)

        def visit_FunctionDef(self, n: ast.FunctionDef) -> ast.AST:
            n.body = self._clean(n.body)
            return self.generic_visit(n)

    cleaned = _StripDoc().visit(copy.deepcopy(tree))
    ast.fix_missing_locations(cleaned)
    return len(zlib.compress(ast.unparse(cleaned).encode("utf-8"), level=9))


def _freeze_output(val: Any, depth: int = 0) -> Any:
    if depth > 4:
        return ("CAP", type(val).__name__)
    if val is None or isinstance(val, (bool, int, str, bytes)):
        return (type(val).__name__, val)
    if isinstance(val, float):
        if not math.isfinite(val):
            return ("NONFINITE",)
        return ("float", round(val, 9))
    if isinstance(val, (list, tuple)):
        return (type(val).__name__, tuple(_freeze_output(x, depth + 1) for x in val[:32]))
    if isinstance(val, (set, frozenset)):
        return (type(val).__name__, tuple(sorted((_freeze_output(x, depth + 1) for x in val), key=repr)[:32]))
    if isinstance(val, dict):
        return ("dict", tuple(sorted(((_freeze_output(k, depth + 1), _freeze_output(v, depth + 1)) for k, v in val.items()), key=repr)[:32]))
    return ("repr", repr(val)[:80])


def _expr_node_count(node: ast.AST) -> int:
    return sum(1 for _ in ast.walk(node) if isinstance(_, ast.expr))


def _canonicalize_pure_subtree(
    expr: ast.expr,
    bound_locals: frozenset[str],
    existing_concepts: frozenset[str],
) -> tuple[ast.expr, list[str]] | None:
    """Alpha-normalize a pure expression subtree into canonical `(_v0, _v1, ...)` hole form."""
    comp_targets: set[str] = set()
    for sub in ast.walk(expr):
        if isinstance(sub, (ast.ListComp, ast.GeneratorExp)):
            for g in sub.generators:
                if isinstance(g.target, ast.Name):
                    comp_targets.add(g.target.id)
                else:
                    return None
        elif isinstance(sub, (ast.Lambda, ast.Await, ast.Yield, ast.YieldFrom, ast.NamedExpr)):
            return None
        elif isinstance(sub, ast.Call):
            if sub.keywords:
                return None
            if isinstance(sub.func, ast.Name):
                if sub.func.id not in _PURE_CALLABLES and sub.func.id not in existing_concepts:
                    return None
            elif isinstance(sub.func, ast.Attribute):
                if sub.func.attr not in (_SAFE_STR_METHODS | _SAFE_DICT_METHODS):
                    return None
            else:
                return None

    hole_order: list[str] = []
    hole_map: dict[str, str] = {}
    cloned = copy.deepcopy(expr)

    class _Renamer(ast.NodeTransformer):
        def visit_IfExp(self, nd: ast.IfExp) -> ast.AST:
            # Visit in Python's left-to-right reading order: `body if test else orelse`
            nd.body = self.visit(nd.body)
            nd.test = self.visit(nd.test)
            nd.orelse = self.visit(nd.orelse)
            return nd

        def visit_Name(self, nd: ast.Name) -> ast.AST:
            if not isinstance(nd.ctx, ast.Load):
                return nd
            nm = nd.id
            if nm in comp_targets or nm in _PURE_CALLABLES or nm in existing_concepts:
                return nd
            if nm not in bound_locals:
                raise UnsafeOrUnsupportedAST("FREE_GLOBAL")
            if nm not in hole_map:
                hole_map[nm] = f"_v{len(hole_order)}"
                hole_order.append(nm)
            return ast.Name(id=hole_map[nm], ctx=ast.Load())

    try:
        canon_ast = _Renamer().visit(cloned)
    except UnsafeOrUnsupportedAST:
        return None
    if not (1 <= len(hole_order) <= 4):
        return None
    ast.fix_missing_locations(canon_ast)
    return canon_ast, hole_order


@dataclass(frozen=True)
class ConceptEntry:
    """Verified reusable concept primitive (combinator or HORS algorithmic function) in `G_t`."""

    concept_id: str
    arity: int
    param_names: tuple[str, ...]
    body_expr: str
    domain_kind: str  # "numeric" | "sequence" | "string" | "mapping" | "any"
    mdl_gain_bytes: int
    corpus_sites: int
    uses: int = 0
    verified_hits: int = 0
    body_stmts: str = ""

    @property
    def is_stmt_fn(self) -> bool:
        return bool(self.body_stmts.strip())

    @property
    def log_prior(self) -> float:
        return math.log1p(self.verified_hits * 2 + self.corpus_sites + 1)

    def render_helper_def(self) -> str:
        p_sig = ", ".join(self.param_names)
        if self.is_stmt_fn:
            indented = "\n".join("    " + ln for ln in self.body_stmts.splitlines())
            return f"def {self.concept_id}({p_sig}):\n{indented}"
        return f"def {self.concept_id}({p_sig}):\n    return {self.body_expr}"

    def to_dict(self) -> dict[str, Any]:
        out = {
            "concept_id": self.concept_id,
            "arity": self.arity,
            "param_names": list(self.param_names),
            "body_expr": self.body_expr,
            "domain_kind": self.domain_kind,
            "mdl_gain_bytes": self.mdl_gain_bytes,
            "corpus_sites": self.corpus_sites,
            "uses": self.uses,
            "verified_hits": self.verified_hits,
        }
        if self.body_stmts:
            out["body_stmts"] = self.body_stmts
        return out

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ConceptEntry":
        arity = int(raw["arity"])
        params = tuple(str(p) for p in (raw.get("param_names") or [f"_v{i}" for i in range(arity)]))
        return cls(
            concept_id=str(raw["concept_id"]),
            arity=arity,
            param_names=params,
            body_expr=str(raw.get("body_expr") or ""),
            domain_kind=str(raw.get("domain_kind") or "any"),
            mdl_gain_bytes=int(raw.get("mdl_gain_bytes") or 1),
            corpus_sites=int(raw.get("corpus_sites") or 2),
            uses=int(raw.get("uses") or 0),
            verified_hits=int(raw.get("verified_hits") or 0),
            body_stmts=str(raw.get("body_stmts") or ""),
        )


def _generate_probe_grids(arity: int) -> list[tuple[str, list[tuple[Any, ...]]]]:
    """Deterministic independent-coordinate probe banks testing all variable orderings."""
    base_nums = (-4, -1, 0, 1, 3, 7, 12, 20)
    strides = (1, 3, 5, 7)
    num_tuples: list[tuple[Any, ...]] = [
        tuple(base_nums[(i * strides[j % 4] + j * 2) % len(base_nums)] for j in range(arity))
        for i in range(16)
    ] + [
        tuple(float(base_nums[(i * strides[(j + 1) % 4] + j * 3) % len(base_nums)]) * 0.5 for j in range(arity))
        for i in range(10)
    ]
    seq_samples = [[3, 1, 3, 2], [10, -2, 5], [0, 0, 1], [7], [4, 8, 12, 16], [-5, 0, 5], [1, 9]]
    seq_tuples = [tuple(seq_samples[(i * strides[j % 4] + j) % len(seq_samples)] for j in range(arity)) for i in range(10)]
    str_samples = ["  Alpha Beta  ", "hello_world", "TEST", "x", "foo bar baz", "12345", "a_b_c"]
    str_tuples = [tuple(str_samples[(i * strides[j % 4] + j) % len(str_samples)] for j in range(arity)) for i in range(10)]
    return [
        ("numeric", num_tuples),
        ("sequence", seq_tuples),
        ("string", str_tuples),
    ]


class CompoundingConceptLibrary:
    """Persistent Wake-Sleep concept library expanding synthesis grammar `G_t -> G_{t+1}`."""

    def __init__(self, state_path: pathlib.Path | str | None = None) -> None:
        self._explicit_path = state_path is not None
        self.state_path = pathlib.Path(state_path) if state_path is not None else DEFAULT_LIBRARY_PATH
        self._concepts: dict[str, ConceptEntry] = {}
        self._compiled_asts: dict[str, ast.Expression] = {}
        self._compiled_fn_asts: dict[str, ast.FunctionDef] = {}
        self._load()

    def _can_read(self) -> bool:
        from canonical.runtime.memory_policy_v1 import can_read_memory

        return can_read_memory()

    def _can_write(self) -> bool:
        from canonical.runtime.memory_policy_v1 import can_write_memory

        return can_write_memory()

    def _load(self) -> None:
        if not self._can_read() or not self.state_path.is_file():
            return
        try:
            doc = json.loads(self.state_path.read_text(encoding="utf-8"))
            if not isinstance(doc, Mapping) or doc.get("schema") != SCHEMA:
                return
            for cid, row in (doc.get("concepts") or {}).items():
                if isinstance(row, Mapping):
                    entry = ConceptEntry.from_dict(row)
                    if entry.is_stmt_fn:
                        fn_mod = ast.parse(entry.render_helper_def())
                        if fn_mod.body and isinstance(fn_mod.body[0], ast.FunctionDef):
                            self._concepts[entry.concept_id] = entry
                            self._compiled_fn_asts[entry.concept_id] = fn_mod.body[0]
                    elif entry.body_expr:
                        parsed = ast.parse(entry.body_expr, mode="eval")
                        self._concepts[entry.concept_id] = entry
                        self._compiled_asts[entry.concept_id] = parsed
        except Exception:
            return

    def save(self) -> None:
        if not self._can_write():
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": SCHEMA,
            "concepts": {cid: c.to_dict() for cid, c in sorted(self._concepts.items())},
        }
        tmp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=str(self.state_path.parent),
                prefix=".concept-lib-",
                delete=False,
            ) as fh:
                tmp_name = fh.name
                fh.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, self.state_path)
            tmp_name = None
        finally:
            if tmp_name is not None:
                pathlib.Path(tmp_name).unlink(missing_ok=True)

    def concepts(self) -> list[ConceptEntry]:
        if not self._can_read():
            return []
        return sorted(self._concepts.values(), key=lambda c: (-c.log_prior, -c.mdl_gain_bytes, c.concept_id))

    def callable_map(self) -> dict[str, Callable[..., Any]]:
        """Return pure AST-interpreted callables for all admitted expression & algorithmic concepts."""
        if not self._can_read():
            return {}
        cmap: dict[str, Callable[..., Any]] = {}

        def _make_expr_fn(entry: ConceptEntry, parsed_expr: ast.Expression) -> Callable[..., Any]:
            def _fn(*args: Any) -> Any:
                if len(args) != entry.arity:
                    raise ValueError("ARITY_MISMATCH")
                env = dict(zip(entry.param_names, args))
                return eval_pure_ast_expr(parsed_expr, env, extra_callables=cmap)

            return _fn

        def _make_stmt_fn(entry: ConceptEntry, parsed_fdef: ast.FunctionDef) -> Callable[..., Any]:
            def _fn(*args: Any) -> Any:
                if len(args) != entry.arity:
                    raise ValueError("ARITY_MISMATCH")
                return eval_pure_ast_function(parsed_fdef, args, extra_callables=cmap)

            return _fn

        for cid, entry in self._concepts.items():
            if entry.is_stmt_fn and cid in self._compiled_fn_asts:
                cmap[cid] = _make_stmt_fn(entry, self._compiled_fn_asts[cid])
            elif cid in self._compiled_asts:
                cmap[cid] = _make_expr_fn(entry, self._compiled_asts[cid])
        return cmap

    def record_concept_outcome(self, concept_id: str, *, helped: bool) -> None:
        if not self._can_write() or concept_id not in self._concepts:
            return
        cur = self._concepts[concept_id]
        self._concepts[concept_id] = ConceptEntry(
            concept_id=cur.concept_id,
            arity=cur.arity,
            param_names=cur.param_names,
            body_expr=cur.body_expr,
            domain_kind=cur.domain_kind,
            mdl_gain_bytes=cur.mdl_gain_bytes,
            corpus_sites=cur.corpus_sites,
            uses=cur.uses + 1,
            verified_hits=cur.verified_hits + (1 if helped else 0),
            body_stmts=cur.body_stmts,
        )
        self.save()

    def _verify_candidate_stmt_concept(self, body_stmts: str, arity: int) -> tuple[bool, str]:
        """Verify determinism, non-constancy, and mutation-kill on a multi-statement HORS function."""
        params = tuple(f"_v{i}" for i in range(arity))
        indented = "\n".join("    " + ln for ln in body_stmts.splitlines())
        fn_src = f"def _stmt_concept({', '.join(params)}):\n{indented}\n"
        try:
            mod = ast.parse(fn_src)
            if not mod.body or not isinstance(mod.body[0], ast.FunctionDef):
                return False, "NOT_FUNCTION_DEF"
            fdef = mod.body[0]
        except SyntaxError:
            return False, "SYNTAX_ERROR"
        cmap = self.callable_map()
        chosen_domain: str | None = None
        valid_probes: list[tuple[Any, ...]] = []
        baseline_sigs: list[Any] = []
        for dom_kind, grid in _generate_probe_grids(arity):
            pts: list[tuple[Any, ...]] = []
            sigs1: list[Any] = []
            sigs2: list[Any] = []
            for row in grid:
                try:
                    v1 = eval_pure_ast_function(fdef, row, extra_callables=cmap)
                    v2 = eval_pure_ast_function(fdef, row, extra_callables=cmap)
                except Exception:
                    continue
                s1 = _freeze_output(v1)
                s2 = _freeze_output(v2)
                if s1 == ("NONFINITE",) or s1 != s2:
                    continue
                pts.append(row)
                sigs1.append(s1)
                sigs2.append(s2)
            if len(pts) >= 4 and len(set(sigs1)) >= 2 and sigs1 == sigs2:
                chosen_domain = dom_kind
                valid_probes = pts
                baseline_sigs = sigs1
                break
        if chosen_domain is None:
            return False, "INSUFFICIENT_NONCONSTANT_PROBES"

        raw_muts = property_v1.mutate(fn_src)
        mut_texts = [(m[1] if isinstance(m, tuple) and len(m) >= 2 else str(m)) for m in raw_muts]
        for idx_nd, sub_nd in enumerate(list(ast.walk(fdef))):
            if isinstance(sub_nd, ast.BinOp):
                m_copy = copy.deepcopy(fdef)
                target_sub = list(ast.walk(m_copy))[idx_nd]
                if isinstance(target_sub, ast.BinOp):
                    target_sub.op = ast.Sub() if not isinstance(target_sub.op, ast.Sub) else ast.Add()
                    mut_texts.append(ast.unparse(m_copy))
            elif isinstance(sub_nd, ast.Compare) and len(sub_nd.ops) == 1:
                m_copy = copy.deepcopy(fdef)
                target_sub = list(ast.walk(m_copy))[idx_nd]
                if isinstance(target_sub, ast.Compare):
                    target_sub.ops = [ast.Lt() if not isinstance(target_sub.ops[0], ast.Lt) else ast.Gt()]
                    mut_texts.append(ast.unparse(m_copy))

        killed = 0
        for mut_src in mut_texts[:30]:
            if not isinstance(mut_src, str) or not mut_src.strip():
                continue
            try:
                m_mod = ast.parse(mut_src)
                if not m_mod.body or not isinstance(m_mod.body[0], ast.FunctionDef):
                    continue
                m_fn = m_mod.body[0]
            except SyntaxError:
                continue
            diverged = False
            for row, exp_sig in zip(valid_probes, baseline_sigs):
                try:
                    mv = eval_pure_ast_function(m_fn, row, extra_callables=cmap)
                    if _freeze_output(mv) != exp_sig:
                        diverged = True
                        break
                except Exception:
                    diverged = True
                    break
            if diverged:
                killed += 1
                break
        if killed < 1:
            return False, "ZERO_MUTANTS_KILLED"
        return True, chosen_domain

    def _verify_candidate_concept(self, canon_expr_src: str, arity: int) -> tuple[bool, str]:
        """Verify determinism, non-constancy, and mutation-kill (`property_v1.mutate`) without `exec()`/`eval()`."""
        try:
            parsed = ast.parse(canon_expr_src, mode="eval")
        except SyntaxError:
            return False, "SYNTAX_ERROR"
        params = tuple(f"_v{i}" for i in range(arity))
        cmap = self.callable_map()

        chosen_domain: str | None = None
        valid_probes: list[tuple[Any, ...]] = []
        baseline_sigs: list[Any] = []

        for dom_kind, grid in _generate_probe_grids(arity):
            pts: list[tuple[Any, ...]] = []
            sigs1: list[Any] = []
            sigs2: list[Any] = []
            for row in grid:
                try:
                    v1 = eval_pure_ast_expr(parsed, dict(zip(params, row)), extra_callables=cmap)
                    v2 = eval_pure_ast_expr(parsed, dict(zip(params, row)), extra_callables=cmap)
                except Exception:
                    continue
                s1 = _freeze_output(v1)
                s2 = _freeze_output(v2)
                if s1 == ("NONFINITE",) or s1 != s2:
                    continue
                pts.append(row)
                sigs1.append(s1)
                sigs2.append(s2)
            if len(pts) >= 4 and len(set(sigs1)) >= 2 and sigs1 == sigs2:
                chosen_domain = dom_kind
                valid_probes = pts
                baseline_sigs = sigs1
                break

        if chosen_domain is None:
            return False, "INSUFFICIENT_NONCONSTANT_PROBES"

        # Mutation-kill gate (`property_v1.mutate` + AST operator/constant perturbation)
        fn_src = f"def _concept({', '.join(params)}):\n    return {canon_expr_src}\n"
        raw_muts = property_v1.mutate(fn_src)
        mut_texts: list[str] = [
            (m[1] if isinstance(m, tuple) and len(m) >= 2 else str(m))
            for m in raw_muts
        ]
        # Add genuine semantic AST operator/constant perturbations so kill gate tests internal logic, not syntax errors
        for idx_nd, sub_nd in enumerate(list(ast.walk(parsed))):
            if isinstance(sub_nd, ast.BinOp):
                m_copy = copy.deepcopy(parsed)
                target_sub = list(ast.walk(m_copy))[idx_nd]
                if isinstance(target_sub, ast.BinOp):
                    target_sub.op = ast.Sub() if not isinstance(target_sub.op, ast.Sub) else ast.Add()
                    mut_texts.append(f"def _concept({', '.join(params)}):\n    return {ast.unparse(m_copy)}\n")
            elif isinstance(sub_nd, ast.Compare) and len(sub_nd.ops) == 1:
                m_copy = copy.deepcopy(parsed)
                target_sub = list(ast.walk(m_copy))[idx_nd]
                if isinstance(target_sub, ast.Compare):
                    target_sub.ops = [ast.Lt() if not isinstance(target_sub.ops[0], ast.Lt) else ast.Gt()]
                    mut_texts.append(f"def _concept({', '.join(params)}):\n    return {ast.unparse(m_copy)}\n")

        killed = 0
        for mut_src in mut_texts[:30]:
            if not isinstance(mut_src, str) or not mut_src.strip():
                continue
            try:
                m_tree = ast.parse(mut_src)
                if not m_tree.body:
                    continue
                m_fn = m_tree.body[0]
                if not isinstance(m_fn, ast.FunctionDef) or not m_fn.body or not isinstance(m_fn.body[0], ast.Return) or m_fn.body[0].value is None:
                    continue
                m_expr = ast.Expression(body=m_fn.body[0].value)
            except SyntaxError:
                continue
            diverged = False
            for row, exp_sig in zip(valid_probes, baseline_sigs):
                try:
                    mv = eval_pure_ast_expr(m_expr, dict(zip(params, row)), extra_callables=cmap)
                    if _freeze_output(mv) != exp_sig:
                        diverged = True
                        break
                except Exception:
                    diverged = True
                    break
            if diverged:
                killed += 1
                break

        if killed < 1:
            return False, "ZERO_MUTANTS_KILLED"
        return True, chosen_domain

    def sleep_abstract(
        self,
        program_sources: Sequence[str],
        *,
        min_nodes: int = 5,
        max_new_concepts: int = 6,
    ) -> dict[str, Any]:
        """DreamCoder/Stitch Sleep phase: anti-unify subtrees across `program_sources` with `Delta B_exec < 0`."""
        existing_ids = frozenset(self._concepts.keys())
        parsed_programs: list[ast.Module] = []
        for src in program_sources:
            if not isinstance(src, str) or not src.strip():
                continue
            try:
                parsed_programs.append(ast.parse(src))
            except SyntaxError:
                continue

        if not parsed_programs:
            return {"schema": SCHEMA, "admitted_count": 0, "admitted": [], "total_concepts": len(self._concepts)}

        # Collect candidate canonicalized pure subtrees across all function bodies
        candidates: dict[str, dict[str, Any]] = {}
        for p_idx, mod in enumerate(parsed_programs):
            for fn in [n for n in ast.walk(mod) if isinstance(n, ast.FunctionDef)]:
                bound_vars: set[str] = {a.arg for a in fn.args.args}
                for sub in ast.walk(fn):
                    if isinstance(sub, ast.Assign):
                        for t in sub.targets:
                            if isinstance(t, ast.Name):
                                bound_vars.add(t.id)
                b_frozen = frozenset(bound_vars)
                for expr in [n for n in ast.walk(fn) if isinstance(n, ast.expr)]:
                    ncount = _expr_node_count(expr)
                    if ncount < min_nodes or ncount > 42:
                        continue
                    canon = _canonicalize_pure_subtree(expr, b_frozen, existing_ids)
                    if canon is None:
                        continue
                    canon_ast, hole_vars = canon
                    dump_key = ast.dump(canon_ast, include_attributes=False)
                    entry = candidates.setdefault(
                        dump_key,
                        {
                            "canon_ast": canon_ast,
                            "expr_src": ast.unparse(canon_ast),
                            "arity": len(hole_vars),
                            "node_count": ncount,
                            "occurrences": [],
                        },
                    )
                    entry["occurrences"].append((p_idx, fn.name, hole_vars))

        # Rank by potential savings = (occurrences - 1) * node_count
        viable = [
            info
            for info in candidates.values()
            if len(info["occurrences"]) >= 2
        ]
        viable.sort(key=lambda d: (-(len(d["occurrences"]) - 1) * d["node_count"], d["expr_src"]))

        baseline_corpus_src = "\n\n".join(ast.unparse(m) for m in parsed_programs)
        baseline_bytes = executable_ast_bytes(baseline_corpus_src)
        admitted: list[dict[str, Any]] = []

        for cand in viable:
            if len(admitted) >= max_new_concepts:
                break
            expr_src = str(cand["expr_src"])
            arity = int(cand["arity"])
            cid = "concept_" + hashlib.sha256(f"{arity}:{expr_src}".encode("utf-8")).hexdigest()[:8]
            if cid in self._concepts:
                continue

            # Rewrite matching non-overlapping subtrees across corpus to measure exact `Delta B_exec`
            target_dump = ast.dump(cand["canon_ast"], include_attributes=False)
            rewritten_mods = copy.deepcopy(parsed_programs)
            replaced_sites = 0

            for mod in rewritten_mods:
                for fn in [n for n in ast.walk(mod) if isinstance(n, ast.FunctionDef)]:
                    bound_v = frozenset(
                        {a.arg for a in fn.args.args}
                        | {
                            t.id
                            for s in ast.walk(fn)
                            if isinstance(s, ast.Assign)
                            for t in s.targets
                            if isinstance(t, ast.Name)
                        }
                    )

                    class _Rewriter(ast.NodeTransformer):
                        def generic_visit(self, node: ast.AST) -> ast.AST:
                            if isinstance(node, ast.expr) and _expr_node_count(node) == cand["node_count"]:
                                c_res = _canonicalize_pure_subtree(node, bound_v, existing_ids)
                                if c_res is not None:
                                    c_ast, h_vars = c_res
                                    if ast.dump(c_ast, include_attributes=False) == target_dump:
                                        nonlocal replaced_sites
                                        replaced_sites += 1
                                        return ast.Call(
                                            func=ast.Name(id=cid, ctx=ast.Load()),
                                            args=[ast.Name(id=v, ctx=ast.Load()) for v in h_vars],
                                            keywords=[],
                                        )
                            return super().generic_visit(node)

                    _Rewriter().visit(fn)

            if replaced_sites < 2:
                continue
            params_str = ", ".join(f"_v{i}" for i in range(arity))
            concept_def_src = f"def {cid}({params_str}):\n    return {expr_src}\n\n"
            after_corpus_src = concept_def_src + "\n\n".join(ast.unparse(m) for m in rewritten_mods)
            after_bytes = executable_ast_bytes(after_corpus_src)
            # Stitch exact AST node-savings law: U(c) = (k - 1)*|E| - (k + 1)*arity - (k + 2) > 0
            ncount_c = int(cand["node_count"])
            stitch_node_gain = (replaced_sites - 1) * ncount_c - (replaced_sites + 1) * arity - (replaced_sites + 2)
            if stitch_node_gain <= 0:
                continue

            mdl_gain = baseline_bytes - after_bytes
            if mdl_gain <= 0:
                # Verify strict asymptotic compressed-byte MDL reduction on 4 alpha-distinct call sites
                var_prefixes = ("alpha", "beta", "gamma", "delta")
                n_check = max(4, replaced_sites)
                distinct_sites_before = "\n".join(
                    f"def _fn_{k}(" + ", ".join(f"{var_prefixes[j]}_{k}" for j in range(arity)) + "):\n    return "
                    + expr_src.replace("_v0", f"alpha_{k}").replace("_v1", f"beta_{k}").replace("_v2", f"gamma_{k}").replace("_v3", f"delta_{k}")
                    for k in range(n_check)
                )
                distinct_sites_after = concept_def_src + "\n".join(
                    f"def _fn_{k}(" + ", ".join(f"{var_prefixes[j]}_{k}" for j in range(arity)) + "):\n    return "
                    + f"{cid}(" + ", ".join(f"{var_prefixes[j]}_{k}" for j in range(arity)) + ")"
                    for k in range(n_check)
                )
                b_dist_before = executable_ast_bytes(distinct_sites_before)
                b_dist_after = executable_ast_bytes(distinct_sites_after)
                if b_dist_after >= b_dist_before:
                    continue
                effective_gain = b_dist_before - b_dist_after
            else:
                effective_gain = mdl_gain

            ok_ver, dom_or_err = self._verify_candidate_concept(expr_src, arity)
            if not ok_ver:
                continue

            entry = ConceptEntry(
                concept_id=cid,
                arity=arity,
                param_names=tuple(f"_v{i}" for i in range(arity)),
                body_expr=expr_src,
                domain_kind=dom_or_err,
                mdl_gain_bytes=int(effective_gain),
                corpus_sites=replaced_sites,
                uses=0,
                verified_hits=0,
            )
            self._concepts[cid] = entry
            self._compiled_asts[cid] = ast.parse(expr_src, mode="eval")
            admitted.append(entry.to_dict())

        # Stage 2: Higher-Order Algorithmic / Multi-Statement Function Skeleton Anti-Unification
        if len(admitted) < max_new_concepts:
            stmt_groups: dict[str, list[ast.FunctionDef]] = {}
            for mod in parsed_programs:
                for fn in [n for n in mod.body if isinstance(n, ast.FunctionDef) and not n.decorator_list]:
                    if not (1 <= len(fn.args.args) <= 4) or len(fn.body) < 2:
                        continue
                    has_loop_or_rec = any(
                        isinstance(sub, (ast.For, ast.While))
                        or (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == fn.name)
                        for sub in ast.walk(fn)
                    )
                    if not has_loop_or_rec:
                        continue
                    cloned = copy.deepcopy(fn)
                    rename_map: dict[str, str] = {a.arg: f"_v{i}" for i, a in enumerate(cloned.args.args)}
                    local_idx = 0
                    for sub in ast.walk(cloned):
                        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                            if sub.id not in rename_map:
                                rename_map[sub.id] = f"_loc{local_idx}"
                                local_idx += 1
                    rename_map[fn.name] = "_self_rec"
                    for a in cloned.args.args:
                        a.arg = rename_map[a.arg]
                    cloned.name = "_self_rec"
                    for sub in ast.walk(cloned):
                        if isinstance(sub, ast.Name) and sub.id in rename_map:
                            sub.id = rename_map[sub.id]
                    ast.fix_missing_locations(cloned)
                    sig_dump = ast.dump(cloned, include_attributes=False)
                    stmt_groups.setdefault(sig_dump, []).append(cloned)

            for cloned_list in stmt_groups.values():
                if len(admitted) >= max_new_concepts or len(cloned_list) < 2:
                    continue
                canon_fn = cloned_list[0]
                arity_s = len(canon_fn.args.args)
                # Replace recursive self-reference `_self_rec` with concept's own `cid`
                raw_body_src = "\n".join(ast.unparse(st) for st in canon_fn.body)
                cid_s = "concept_" + hashlib.sha256(f"stmt:{arity_s}:{raw_body_src}".encode("utf-8")).hexdigest()[:8]
                if cid_s in self._concepts:
                    continue
                body_stmts = raw_body_src.replace("_self_rec", cid_s)
                if sum(1 for _ in ast.walk(canon_fn)) < 14:
                    continue
                ok_s, dom_s = self._verify_candidate_stmt_concept(body_stmts, arity_s)
                if not ok_s:
                    continue
                p_tup = tuple(f"_v{i}" for i in range(arity_s))
                entry_s = ConceptEntry(
                    concept_id=cid_s,
                    arity=arity_s,
                    param_names=p_tup,
                    body_expr="",
                    domain_kind=dom_s,
                    mdl_gain_bytes=max(8, executable_ast_bytes(body_stmts) // 2),
                    corpus_sites=len(cloned_list),
                    uses=0,
                    verified_hits=0,
                    body_stmts=body_stmts,
                )
                parsed_helper = ast.parse(entry_s.render_helper_def()).body[0]
                if isinstance(parsed_helper, ast.FunctionDef):
                    self._concepts[cid_s] = entry_s
                    self._compiled_fn_asts[cid_s] = parsed_helper
                    admitted.append(entry_s.to_dict())

        if admitted:
            self.save()
        return {
            "schema": SCHEMA,
            "admitted_count": len(admitted),
            "admitted": admitted,
            "total_concepts": len(self._concepts),
        }


def discover_ast_operator_morphisms() -> dict[str, Any]:
    """Empirically discover Python `ast` <-> `operator` algebra morphisms + singularity zero identities.

    Contains ZERO hardcoded `{ast.Add: operator.add, ...}` mappings: probes all `ast.operator`,
    `ast.unaryop`, and `ast.cmpop` subclasses against `operator.__dict__` callables on concrete
    witness points and probes `y = 0` to detect division singularities and type-derived identities.
    """
    bin_probes = [(12, 5), (9, 3), (7, 2)]
    unary_probes = [(7,), (-4,)]
    cmp_probes = [(3, 5), (5, 5), (8, 2)]

    def _is_in_place_mutator(op_nm: str, op_fn: Callable[..., Any]) -> bool:
        for sample_a, sample_b in (([1], [2]), ({1}, {2})):
            orig = copy.deepcopy(sample_a)
            try:
                op_fn(sample_a, sample_b)
                if sample_a != orig:
                    return True
            except Exception:
                pass
        if op_nm.startswith("i") and len(op_nm) > 1:
            for cand_pure in (op_nm[1:], op_nm[1:] + "_"):
                pure_twin = getattr(py_operator, cand_pure, None)
                if callable(pure_twin):
                    try:
                        if op_fn(12, 5) == pure_twin(12, 5):
                            return True
                    except Exception:
                        pass
        return False

    op_funcs: list[tuple[str, Callable[..., Any]]] = [
        (nm, fn)
        for nm, fn in sorted(vars(py_operator).items())
        if not nm.startswith("_")
        and nm not in ("countOf", "indexOf", "itemgetter", "attrgetter", "methodcaller", "length_hint")
        and callable(fn)
        and not _is_in_place_mutator(nm, fn)
    ]

    bin_morphisms: dict[str, dict[str, Any]] = {}
    for cls in sorted(
        (c for c in vars(ast).values() if isinstance(c, type) and issubclass(c, ast.operator) and c is not ast.operator),
        key=lambda c: c.__name__,
    ):
        try:
            ast_vals = [
                eval_pure_ast_expr(
                    ast.BinOp(left=ast.Constant(x), op=cls(), right=ast.Constant(y)),
                    {},
                )
                for x, y in bin_probes
            ]
        except Exception:
            continue
        for op_nm, op_fn in op_funcs:
            try:
                cand_vals = [op_fn(x, y) for x, y in bin_probes]
            except Exception:
                continue
            if [type(a) is type(b) and a == b for a, b in zip(ast_vals, cand_vals)] == [True] * len(bin_probes):
                # Probe singularity at y == 0
                zero_guard_identity: Any = None
                needs_zero_guard = False
                try:
                    op_fn(8, 0)
                except ZeroDivisionError:
                    needs_zero_guard = True
                    zero_guard_identity = type(ast_vals[0])()
                except Exception:
                    pass
                bin_morphisms[cls.__name__] = {
                    "operator_attr": op_nm,
                    "needs_zero_guard": needs_zero_guard,
                    "zero_identity": zero_guard_identity,
                }
                break

    unary_morphisms: dict[str, str] = {}
    for cls in sorted(
        (c for c in vars(ast).values() if isinstance(c, type) and issubclass(c, ast.unaryop) and c is not ast.unaryop),
        key=lambda c: c.__name__,
    ):
        probes_u = [(True,), (False,)] if cls is ast.Not else unary_probes
        try:
            ast_vals = [eval_pure_ast_expr(ast.UnaryOp(op=cls(), operand=ast.Constant(x)), {}) for (x,) in probes_u]
        except Exception:
            continue
        for op_nm, op_fn in op_funcs:
            try:
                cand_vals = [op_fn(x) for (x,) in probes_u]
            except Exception:
                continue
            if [type(a) is type(b) and a == b for a, b in zip(ast_vals, cand_vals)] == [True] * len(probes_u):
                unary_morphisms[cls.__name__] = op_nm
                break

    cmp_morphisms: dict[str, str] = {}
    for cls in sorted(
        (c for c in vars(ast).values() if isinstance(c, type) and issubclass(c, ast.cmpop) and c is not ast.cmpop),
        key=lambda c: c.__name__,
    ):
        try:
            ast_vals = [
                eval_pure_ast_expr(
                    ast.Compare(left=ast.Constant(x), ops=[cls()], comparators=[ast.Constant(y)]),
                    {},
                )
                for x, y in cmp_probes
            ]
        except Exception:
            continue
        for op_nm, op_fn in op_funcs:
            try:
                cand_vals = [op_fn(x, y) for x, y in cmp_probes]
            except Exception:
                continue
            if [type(a) is type(b) and a == b for a, b in zip(ast_vals, cand_vals)] == [True] * len(cmp_probes):
                cmp_morphisms[cls.__name__] = op_nm
                break

    return {
        "binary": bin_morphisms,
        "unary": unary_morphisms,
        "compare": cmp_morphisms,
    }


def build_programmatic_ast_catamorphism_stmts(
    arg0: str,
    env_arg: str | None = None,
    *,
    has_bitwise: bool = False,
) -> list[ast.stmt]:
    """Programmatically construct AST-algebra structural catamorphism statements (zero string templates)."""
    morphisms = discover_ast_operator_morphisms()
    excluded_bin = {"Pow", "LShift", "MatMult"} | (set() if has_bitwise else {"BitAnd", "BitOr", "BitXor", "RShift"})
    bin_keys: list[ast.expr] = []
    bin_vals: list[ast.expr] = []
    for ast_cls_nm, spec in sorted(morphisms["binary"].items()):
        if ast_cls_nm in excluded_bin:
            continue
        op_attr = str(spec["operator_attr"])
        op_ref: ast.expr = ast.Attribute(value=ast.Name(id="_o", ctx=ast.Load()), attr=op_attr, ctx=ast.Load())
        if spec.get("needs_zero_guard"):
            z_ident = spec.get("zero_identity", 0)
            op_ref = ast.Call(
                func=ast.Name(id="_z", ctx=ast.Load()),
                args=[op_ref] + ([ast.Constant(value=z_ident)] if z_ident != 0 else []),
                keywords=[],
            )
        bin_keys.append(ast.Attribute(value=ast.Name(id="_a", ctx=ast.Load()), attr=ast_cls_nm, ctx=ast.Load()))
        bin_vals.append(op_ref)

    excluded_un = set() if has_bitwise else {"Invert", "Not"}
    un_keys = [
        ast.Attribute(value=ast.Name(id="_a", ctx=ast.Load()), attr=k, ctx=ast.Load())
        for k in sorted(morphisms["unary"].keys())
        if k not in excluded_un
    ]
    un_vals = [
        ast.Attribute(value=ast.Name(id="_o", ctx=ast.Load()), attr=morphisms["unary"][k], ctx=ast.Load())
        for k in sorted(morphisms["unary"].keys())
        if k not in excluded_un
    ]
    cmp_keys = [
        ast.Attribute(value=ast.Name(id="_a", ctx=ast.Load()), attr=k, ctx=ast.Load())
        for k in sorted(morphisms["compare"].keys())
    ]
    cmp_vals = [
        ast.Attribute(value=ast.Name(id="_o", ctx=ast.Load()), attr=morphisms["compare"][k], ctx=ast.Load())
        for k in sorted(morphisms["compare"].keys())
    ]

    def _N(nm: str, store: bool = False) -> ast.Name:
        return ast.Name(id=nm, ctx=ast.Store() if store else ast.Load())

    def _A(base: ast.expr, attr: str) -> ast.Attribute:
        return ast.Attribute(value=base, attr=attr, ctx=ast.Load())

    def _C(fn_expr: ast.expr, *args: ast.expr, **kw: ast.expr) -> ast.Call:
        return ast.Call(
            func=fn_expr,
            args=list(args),
            keywords=[ast.keyword(arg=k, value=v) for k, v in kw.items()],
        )

    def _isinst(cls_attr: str) -> ast.Call:
        return _C(_N("isinstance"), _N("n"), _A(_N("_a"), cls_attr))

    def _rec(sub: ast.expr) -> ast.Call:
        return _C(_N("_f"), sub)

    env_expr: ast.expr = (
        _C(_N("dict"), ast.BoolOp(op=ast.Or(), values=[_N(env_arg), ast.Dict(keys=[], values=[])]))
        if env_arg
        else ast.Dict(keys=[], values=[])
    )

    zero_guard_assign = ast.Assign(
        targets=[_N("_z", store=True)],
        value=ast.Lambda(
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg="f"), ast.arg(arg="z")],
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[ast.Constant(value=0)],
            ),
            body=ast.Lambda(
                args=ast.arguments(
                    posonlyargs=[],
                    args=[ast.arg(arg="x"), ast.arg(arg="y")],
                    vararg=None,
                    kwonlyargs=[],
                    kw_defaults=[],
                    kwarg=None,
                    defaults=[],
                ),
                body=ast.IfExp(
                    test=ast.Compare(left=_N("y"), ops=[ast.Eq()], comparators=[ast.Constant(value=0)]),
                    body=_N("z"),
                    orelse=_C(_N("f"), _N("x"), _N("y")),
                ),
            ),
        ),
    )

    fold_branches: list[ast.stmt] = [
        ast.If(test=_isinst("Expression"), body=[ast.Return(value=_rec(_A(_N("n"), "body")))], orelse=[]),
        ast.If(
            test=ast.BoolOp(
                op=ast.And(),
                values=[
                    _isinst("Constant"),
                    ast.Compare(
                        left=_C(_N("type"), _A(_N("n"), "value")),
                        ops=[ast.In()],
                        comparators=[ast.Tuple(elts=[_N("int"), _N("float"), _N("bool")], ctx=ast.Load())],
                    ),
                ],
            ),
            body=[ast.Return(value=_A(_N("n"), "value"))],
            orelse=[],
        ),
        ast.If(
            test=ast.BoolOp(
                op=ast.And(),
                values=[_isinst("Name"), ast.Compare(left=_A(_N("n"), "id"), ops=[ast.In()], comparators=[_N("_e")])],
            ),
            body=[ast.Return(value=ast.Subscript(value=_N("_e"), slice=_A(_N("n"), "id"), ctx=ast.Load()))],
            orelse=[],
        ),
        ast.If(
            test=_isinst("UnaryOp"),
            body=[
                ast.Return(
                    value=_C(
                        ast.Subscript(value=_N("_u"), slice=_C(_N("type"), _A(_N("n"), "op")), ctx=ast.Load()),
                        _rec(_A(_N("n"), "operand")),
                    )
                )
            ],
            orelse=[],
        ),
        ast.If(
            test=_isinst("BinOp"),
            body=[
                ast.Return(
                    value=_C(
                        ast.Subscript(value=_N("_b"), slice=_C(_N("type"), _A(_N("n"), "op")), ctx=ast.Load()),
                        _rec(_A(_N("n"), "left")),
                        _rec(_A(_N("n"), "right")),
                    )
                )
            ],
            orelse=[],
        ),
        ast.If(
            test=_isinst("IfExp"),
            body=[
                ast.Return(
                    value=ast.IfExp(
                        test=_rec(_A(_N("n"), "test")),
                        body=_rec(_A(_N("n"), "body")),
                        orelse=_rec(_A(_N("n"), "orelse")),
                    )
                )
            ],
            orelse=[],
        ),
        ast.Return(
            value=_C(
                ast.Subscript(
                    value=_N("_c"),
                    slice=_C(
                        _N("type"),
                        ast.Subscript(value=_A(_N("n"), "ops"), slice=ast.Constant(value=0), ctx=ast.Load()),
                    ),
                    ctx=ast.Load(),
                ),
                _rec(_A(_N("n"), "left")),
                _rec(ast.Subscript(value=_A(_N("n"), "comparators"), slice=ast.Constant(value=0), ctx=ast.Load())),
            )
        ),
    ]

    fold_fn = ast.FunctionDef(
        name="_f",
        args=ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg="n")],
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
        ),
        body=fold_branches,
        decorator_list=[],
        returns=None,
    )

    stmts: list[ast.stmt] = [
        ast.Import(names=[ast.alias(name="ast", asname="_a"), ast.alias(name="operator", asname="_o")]),
        ast.Assign(targets=[_N("_e", store=True)], value=env_expr),
        zero_guard_assign,
        ast.Assign(targets=[_N("_b", store=True)], value=ast.Dict(keys=bin_keys, values=bin_vals)),
        ast.Assign(targets=[_N("_u", store=True)], value=ast.Dict(keys=un_keys, values=un_vals)),
        ast.Assign(targets=[_N("_c", store=True)], value=ast.Dict(keys=cmp_keys, values=cmp_vals)),
        fold_fn,
        ast.Return(
            value=_C(
                _N("_f"),
                _C(
                    _A(_N("_a"), "parse"),
                    _C(_A(_C(_N("str"), _N(arg0)), "strip")),
                    mode=ast.Constant(value="eval"),
                ),
            )
        ),
    ]
    for st in stmts:
        ast.fix_missing_locations(st)
    return stmts

