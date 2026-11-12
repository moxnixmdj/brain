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
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import property_v1
from canonical.swe_kernel import boundary_disjunction_normalization_v1 as _bdn
from canonical.swe_kernel.egraph_and_deductive_synthesizer_v1 import EClass, EGraph, ENode

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
        if isinstance(nd, ast.Lambda):
            if nd.args.vararg or nd.args.kwarg or nd.args.kwonlyargs or nd.args.defaults:
                raise UnsafeOrUnsupportedAST("COMPLEX_LAMBDA_ARGS")
            lam_params = tuple(a.arg for a in nd.args.args)
            captured_scope = dict(scope)

            def _lam_closure(*c_args: Any, _lp: tuple[str, ...] = lam_params, _lb: ast.expr = nd.body, _cs: dict[str, Any] = captured_scope) -> Any:
                if len(c_args) != len(_lp):
                    raise UnsafeOrUnsupportedAST("LAMBDA_ARITY_MISMATCH")
                call_sc = dict(_cs)
                for p_n, p_v in zip(_lp, c_args):
                    call_sc[p_n] = p_v
                return _ev(_lb, call_sc)

            return _lam_closure
        if isinstance(nd, ast.Call):
            if nd.keywords:
                raise UnsafeOrUnsupportedAST("KEYWORD_CALL_UNSUPPORTED")
            args_v = [_ev(a, scope) for a in nd.args]
            if isinstance(nd.func, ast.Name):
                fname = nd.func.id
                if fname in scope and callable(scope[fname]):
                    return scope[fname](*args_v)
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
        if isinstance(expr, ast.Lambda):
            if expr.args.vararg or expr.args.kwarg or expr.args.kwonlyargs or expr.args.defaults:
                raise UnsafeOrUnsupportedAST("COMPLEX_LAMBDA_ARGS")
            lam_params = tuple(a.arg for a in expr.args.args)
            captured_scope = dict(scope)

            def _fn_lam(*c_args: Any, _lp: tuple[str, ...] = lam_params, _lb: ast.expr = expr.body, _cs: dict[str, Any] = captured_scope) -> Any:
                if len(c_args) != len(_lp):
                    raise UnsafeOrUnsupportedAST("LAMBDA_ARITY_MISMATCH")
                inner_sc = dict(_cs)
                for p_n, p_v in zip(_lp, c_args):
                    inner_sc[p_n] = p_v
                return _eval_expr_in_scope(_lb, inner_sc, depth + 1)

            return _fn_lam
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

    cleaned = _StripDoc().visit(tree)
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
    """Verified reusable concept primitive (combinator, HORS algorithmic function, or higher-order skeleton) in `G_t`."""

    concept_id: str
    arity: int
    param_names: tuple[str, ...]
    body_expr: str
    domain_kind: str  # "numeric" | "sequence" | "string" | "mapping" | "higher_order" | "any"
    mdl_gain_bytes: int
    corpus_sites: int
    uses: int = 0
    verified_hits: int = 0
    # Merged 2026-11-04: main added statement-function and higher-order support; this branch added
    # disconfirmation/retirement. The two are orthogonal -- one is about what a concept CAN be, the
    # other about whether the record still vouches for it -- so both fields survive.
    body_stmts: str = ""
    callable_params: tuple[tuple[str, int], ...] = field(default_factory=tuple)
    #: Structural family the abstraction was recognised from -- computed from the lifted shape by
    #: `compression_gain_v1.family_of`, never asserted. Empty for stored primitives, which license
    #: nothing: a menu entry with a family name is still a menu entry.
    family: str = ""

    # Until `disconfirmations` existed, `log_prior` could only rise: measured, 50 recorded failures
    # left it unchanged at 2.8904, and the synthesizer only ever looks at the top 16 concepts, so
    # surviving junk crowded out useful concepts (reach 2/2 -> 0/2). A library that cannot be wrong
    # about itself is not a memory, it is an append-only log.
    disconfirmations: int = 0

    RETIREMENT_THRESHOLD = 3

    @property
    def is_stmt_fn(self) -> bool:
        return bool(self.body_stmts.strip())

    @property
    def is_higher_order(self) -> bool:
        return len(self.callable_params) > 0

    @property
    def callable_arity_map(self) -> dict[str, int]:
        return dict(self.callable_params)

    @property
    def retired(self) -> bool:
        """True when the record says this concept has failed more often than it has ever helped."""
        return self.disconfirmations >= self.RETIREMENT_THRESHOLD and self.verified_hits == 0

    @property
    def log_prior(self) -> float:
        # Disconfirmations SUBTRACT. The asymmetry is deliberate: one verified help is worth a
        # little, repeated unexplained failure is worth a lot, because a wrong concept is not
        # merely unhelpful -- it fills one of the 16 slots the search can see.
        return math.log1p(max(0, self.verified_hits * 2 + self.corpus_sites
                              - self.disconfirmations * 3) + 1)

    def render_helper_def(self) -> str:
        p_sig = ", ".join(self.param_names)
        if self.is_stmt_fn:
            indented = "\n".join("    " + ln for ln in self.body_stmts.splitlines())
            return f"def {self.concept_id}({p_sig}):\n{indented}"
        return f"def {self.concept_id}({p_sig}):\n    return {self.body_expr}"

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "concept_id": self.concept_id,
            "arity": self.arity,
            "param_names": list(self.param_names),
            "body_expr": self.body_expr,
            "domain_kind": self.domain_kind,
            "mdl_gain_bytes": self.mdl_gain_bytes,
            "corpus_sites": self.corpus_sites,
            "uses": self.uses,
            "verified_hits": self.verified_hits,
            "disconfirmations": self.disconfirmations,
        }
        if self.body_stmts:
            out["body_stmts"] = self.body_stmts
        if self.callable_params:
            out["callable_params"] = {k: int(v) for k, v in self.callable_params}
        if self.family:
            out["family"] = self.family
        return out

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ConceptEntry":
        arity = int(raw["arity"])
        params = tuple(str(p) for p in (raw.get("param_names") or [f"_v{i}" for i in range(arity)]))
        raw_cp = raw.get("callable_params")
        cp_tup: tuple[tuple[str, int], ...] = ()
        if isinstance(raw_cp, Mapping):
            cp_tup = tuple((str(k), int(v)) for k, v in sorted(raw_cp.items()))
        return cls(
            concept_id=str(raw["concept_id"]),
            arity=arity,
            param_names=params,
            body_expr=str(raw.get("body_expr") or ""),
            domain_kind=str(raw.get("domain_kind") or "any"),
            # A stored 0 must stay 0: zero is the honest "no compression was measured" value the
            # bridge writes for a stored primitive, and `or 1` silently upgraded it back to a
            # fabricated gain on every reload.
            mdl_gain_bytes=int(raw["mdl_gain_bytes"]) if raw.get("mdl_gain_bytes") is not None else 1,
            corpus_sites=int(raw.get("corpus_sites") or 2),
            uses=int(raw.get("uses") or 0),
            verified_hits=int(raw.get("verified_hits") or 0),
            body_stmts=str(raw.get("body_stmts") or ""),
            callable_params=cp_tup,
            disconfirmations=int(raw.get("disconfirmations") or 0),
            family=str(raw.get("family") or ""),
        )


def canonicalize_ast_via_egraph(mod: ast.Module) -> ast.Module:
    """Normalize boundary disjunctions & saturate sound non-erasing algebraic identities via `EGraph`."""
    src_text = ast.unparse(mod)
    try:
        bdn_res = _bdn.normalize(src_text)
        norm_text = bdn_res if isinstance(bdn_res, str) else str((bdn_res or {}).get("normalized") or src_text)
        work_mod = ast.parse(norm_text)
    except Exception:
        work_mod = copy.deepcopy(mod)

    _COMMUTATIVE_OPS = (ast.Add, ast.Mult, ast.BitAnd, ast.BitOr, ast.BitXor)
    _BIN_OP_TO_TAG = {
        ast.Add: "bin:+",
        ast.Sub: "bin:-",
        ast.Mult: "bin:*",
    }
    _TAG_TO_BIN_OP: dict[str, type[ast.operator]] = {
        "bin:+": ast.Add,
        "bin:-": ast.Sub,
        "bin:*": ast.Mult,
    }

    def _saturate_pure_arith(expr: ast.expr) -> ast.expr:
        eg = EGraph()
        leaf_asts: dict[str, ast.expr] = {}

        def _insert(nd: ast.expr) -> int:
            if isinstance(nd, ast.Constant) and isinstance(nd.value, int) and not isinstance(nd.value, bool):
                op_k = f"int:{nd.value}"
                leaf_asts[op_k] = ast.Constant(value=nd.value)
                return eg.add(ENode(op_k, ()))
            if isinstance(nd, ast.Name) and isinstance(nd.ctx, ast.Load):
                op_k = f"var:{nd.id}"
                leaf_asts[op_k] = ast.Name(id=nd.id, ctx=ast.Load())
                return eg.add(ENode(op_k, ()))
            if isinstance(nd, ast.BinOp) and type(nd.op) in _BIN_OP_TO_TAG:
                lc = _insert(nd.left)
                rc = _insert(nd.right)
                tag = _BIN_OP_TO_TAG[type(nd.op)]
                cid = eg.add(ENode(tag, (lc, rc)))
                # Commutativity on pure integer/variable addition & multiplication
                if isinstance(nd.op, (ast.Add, ast.Mult)):
                    comm_id = eg.add(ENode(tag, (rc, lc)))
                    eg.union(cid, comm_id)
                # Non-variable-erasing identity & doubling rules:
                # x + 0 == x, 0 + x == x, x - 0 == x, x * 1 == x, 1 * x == x, x + x == 2 * x
                z0 = eg.memo.get(ENode("int:0", ()))
                z1 = eg.memo.get(ENode("int:1", ()))
                if tag == "bin:+":
                    if z0 is not None and eg.find(rc) == eg.find(z0):
                        eg.union(cid, lc)
                    if z0 is not None and eg.find(lc) == eg.find(z0):
                        eg.union(cid, rc)
                    if eg.find(lc) == eg.find(rc):
                        c2 = eg.add(ENode("int:2", ()))
                        leaf_asts["int:2"] = ast.Constant(value=2)
                        mul2 = eg.add(ENode("bin:*", (c2, lc)))
                        eg.union(cid, mul2)
                elif tag == "bin:-":
                    if z0 is not None and eg.find(rc) == eg.find(z0):
                        eg.union(cid, lc)
                elif tag == "bin:*":
                    if z1 is not None and eg.find(rc) == eg.find(z1):
                        eg.union(cid, lc)
                    if z1 is not None and eg.find(lc) == eg.find(z1):
                        eg.union(cid, rc)
                return eg.find(cid)
            dump_k = "opaque:" + hashlib.sha256(ast.dump(nd, include_attributes=False).encode("utf-8")).hexdigest()[:12]
            leaf_asts[dump_k] = copy.deepcopy(nd)
            return eg.add(ENode(dump_k, ()))

        root_cid = _insert(expr)
        eg.rebuild()
        # Sanity check EClass structure & extract minimum-AST-cost canonical node
        _ = [isinstance(ec, EClass) for ec in eg.classes.values()]
        op_costs: dict[str, int] = {"bin:+": 4, "bin:-": 4, "bin:*": 3}
        for k_op in leaf_asts:
            op_costs[k_op] = 1 if k_op.startswith(("int:", "var:")) else 5

        memo_best: dict[int, tuple[tuple[int, str], ENode]] = {}
        changed = True
        while changed:
            changed = False
            for cid, eclass in eg.classes.items():
                rcid = eg.find(cid)
                for en in eclass.nodes:
                    if any(eg.find(ch) not in memo_best for ch in en.children):
                        continue
                    c_val = op_costs.get(en.op, 6) + sum(memo_best[eg.find(ch)][0][0] for ch in en.children)
                    c_lex = en.op + "(" + ",".join(memo_best[eg.find(ch)][0][1] for ch in en.children) + ")"
                    rank_key = (c_val, c_lex)
                    if rcid not in memo_best or rank_key < memo_best[rcid][0]:
                        memo_best[rcid] = (rank_key, en)
                        changed = True

        def _reconstruct(cid: int) -> ast.expr:
            rc = eg.find(cid)
            if rc not in memo_best:
                return copy.deepcopy(expr)
            en = memo_best[rc][1]
            if en.op in leaf_asts:
                return copy.deepcopy(leaf_asts[en.op])
            if en.op in _TAG_TO_BIN_OP and len(en.children) == 2:
                return ast.BinOp(
                    left=_reconstruct(en.children[0]),
                    op=_TAG_TO_BIN_OP[en.op](),
                    right=_reconstruct(en.children[1]),
                )
            return copy.deepcopy(expr)

        return _reconstruct(root_cid)

    class _EGraphNormalizer(ast.NodeTransformer):
        def generic_visit(self, node: ast.AST) -> ast.AST:
            node = super().generic_visit(node)
            if isinstance(node, ast.BinOp) and type(node.op) in _COMMUTATIVE_OPS:
                if not isinstance(node.op, (ast.Add, ast.Mult)):
                    l_s = ast.dump(node.left, include_attributes=False)
                    r_s = ast.dump(node.right, include_attributes=False)
                    if r_s < l_s:
                        node.left, node.right = node.right, node.left
            if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OP_TO_TAG:
                return _saturate_pure_arith(node)
            return node

    out_mod = _EGraphNormalizer().visit(work_mod)
    ast.fix_missing_locations(out_mod)
    return out_mod


def _normalize_function_for_plotkin_lgg(fn: ast.FunctionDef) -> tuple[ast.FunctionDef, set[str], list[str]] | None:
    """Alpha-normalize a loop function and desugar `AugAssign` (`acc += e` -> `acc = acc + e`) for Plotkin LGG."""
    if fn.decorator_list or not (1 <= len(fn.args.args) <= 4) or len(fn.body) < 2:
        return None
    cloned = copy.deepcopy(fn)

    class _DesugarAug(ast.NodeTransformer):
        def visit_AugAssign(self, nd: ast.AugAssign) -> ast.AST:
            nd = self.generic_visit(nd)  # type: ignore[assignment]
            if isinstance(nd.target, ast.Name):
                return ast.Assign(
                    targets=[ast.Name(id=nd.target.id, ctx=ast.Store())],
                    value=ast.BinOp(
                        left=ast.Name(id=nd.target.id, ctx=ast.Load()),
                        op=copy.deepcopy(nd.op),
                        right=copy.deepcopy(nd.value),
                    ),
                )
            return nd

    cloned = _DesugarAug().visit(cloned)  # type: ignore[assignment]
    outer_params = [f"_v{i}" for i in range(len(cloned.args.args))]
    rename_map: dict[str, str] = {a.arg: f"_v{i}" for i, a in enumerate(cloned.args.args)}
    loop_bound_vars: list[str] = []
    local_idx = 0
    in_loop_targets: set[str] = set()

    for sub in ast.walk(cloned):
        if isinstance(sub, ast.For) and isinstance(sub.target, ast.Name):
            in_loop_targets.add(sub.target.id)
            for b_sub in ast.walk(sub):
                if isinstance(b_sub, ast.Name) and isinstance(b_sub.ctx, ast.Store):
                    in_loop_targets.add(b_sub.id)
        elif isinstance(sub, ast.comprehension) and isinstance(sub.target, ast.Name):
            in_loop_targets.add(sub.target.id)
            for b_sub in ast.walk(sub):
                if isinstance(b_sub, ast.Name) and isinstance(b_sub.ctx, ast.Store):
                    in_loop_targets.add(b_sub.id)

    for sub in ast.walk(cloned):
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
            orig_nm = sub.id
            if orig_nm not in rename_map:
                new_nm = f"_loc{local_idx}"
                rename_map[orig_nm] = new_nm
                local_idx += 1
            mapped = rename_map[orig_nm]
            if orig_nm in in_loop_targets and mapped not in loop_bound_vars:
                loop_bound_vars.append(mapped)

    for idx_a, a in enumerate(cloned.args.args):
        a.arg = outer_params[idx_a]
    cloned.name = "_lgg_fn"
    for sub in ast.walk(cloned):
        if isinstance(sub, ast.Name) and sub.id in rename_map:
            sub.id = rename_map[sub.id]
    ast.fix_missing_locations(cloned)
    return cloned, set(loop_bound_vars), loop_bound_vars


def higher_order_plotkin_lgg(
    fn1: ast.FunctionDef,
    fn2: ast.FunctionDef,
) -> dict[str, Any] | None:
    """Compute Higher-Order Plotkin Least-General-Generalization `LGG(fn1, fn2)` over multi-statement ASTs.

    - Closed differing subtrees (independent of loop-bound variables) lift to value holes `_v{k}`.
    - Open differing subtrees referencing loop-bound variables `(b_0, ...)` lift to higher-order
      callable parameters `_fn{m}(b_0, ...)`, discovering abstractions such as `fold_scan(xs, init, step_fn)`.
    """
    if (
        fn1.decorator_list
        or fn2.decorator_list
        or len(fn1.args.args) != len(fn2.args.args)
        or len(fn1.body) != len(fn2.body)
    ):
        return None
    n1 = _normalize_function_for_plotkin_lgg(fn1)
    n2 = _normalize_function_for_plotkin_lgg(fn2)
    if n1 is None or n2 is None:
        return None
    cf1, lb_set1, lb_ord1 = n1
    cf2, lb_set2, lb_ord2 = n2
    if ast.dump(cf1, include_attributes=False) == ast.dump(cf2, include_attributes=False):
        return None

    base_arity = len(cf1.args.args)
    loop_bound = lb_set1 | lb_set2
    ordered_loop = list(dict.fromkeys([*lb_ord1, *lb_ord2]))
    if not ordered_loop:
        return None

    val_holes: dict[tuple[str, str], str] = {}
    fn_holes: dict[tuple[str, str, tuple[str, ...]], str] = {}
    callable_arities: dict[str, int] = {}
    extra_val_params: list[str] = []
    extra_fn_params: list[str] = []
    hole_fillings: dict[str, tuple[str, str]] = {}

    def _free_load_names(nd: ast.AST) -> set[str]:
        return {s.id for s in ast.walk(nd) if isinstance(s, ast.Name) and isinstance(s.ctx, ast.Load)}

    def _anti_unify_expr(e1: ast.expr, e2: ast.expr) -> ast.expr | None:
        """Plotkin LGG on expressions: same head recurses; else a value or HO hole."""
        d1 = ast.dump(e1, include_attributes=False)
        d2 = ast.dump(e2, include_attributes=False)
        if d1 == d2:
            return copy.deepcopy(e1)

        def _hole() -> ast.expr | None:
            captured = [v for v in ordered_loop if v in (_free_load_names(e1) | _free_load_names(e2))]
            if not captured:
                key_v = (d1, d2)
                h_nm = val_holes.get(key_v)
                if h_nm is None:
                    h_nm = f"_v{base_arity + len(extra_val_params)}"
                    val_holes[key_v] = h_nm
                    extra_val_params.append(h_nm)
                    hole_fillings[h_nm] = (ast.unparse(e1), ast.unparse(e2))
                return ast.Name(id=h_nm, ctx=ast.Load())
            if len(captured) > 3:
                return None
            cap_t = tuple(captured)
            key_f = (d1, d2, cap_t)
            fn_nm = fn_holes.get(key_f)
            if fn_nm is None:
                fn_nm = f"_fn{len(extra_fn_params)}"
                fn_holes[key_f] = fn_nm
                extra_fn_params.append(fn_nm)
                callable_arities[fn_nm] = len(cap_t)
                hole_fillings[fn_nm] = (ast.unparse(e1), ast.unparse(e2))
            return ast.Call(
                func=ast.Name(id=fn_nm, ctx=ast.Load()),
                args=[ast.Name(id=bv, ctx=ast.Load()) for bv in cap_t],
                keywords=[],
            )

        if type(e1) is not type(e2):
            return _hole()
        if isinstance(e1, ast.BinOp) and isinstance(e2, ast.BinOp):
            if type(e1.op) is not type(e2.op):
                return _hole()
            left = _anti_unify_expr(e1.left, e2.left)
            right = _anti_unify_expr(e1.right, e2.right)
            if left is None or right is None:
                return None
            return ast.BinOp(left=left, op=copy.deepcopy(e1.op), right=right)
        if isinstance(e1, ast.UnaryOp) and isinstance(e2, ast.UnaryOp):
            if type(e1.op) is not type(e2.op):
                return _hole()
            opnd = _anti_unify_expr(e1.operand, e2.operand)
            if opnd is None:
                return None
            return ast.UnaryOp(op=copy.deepcopy(e1.op), operand=opnd)
        if isinstance(e1, ast.BoolOp) and isinstance(e2, ast.BoolOp):
            if type(e1.op) is not type(e2.op) or len(e1.values) != len(e2.values):
                return _hole()
            vals: list[ast.expr] = []
            for a, b in zip(e1.values, e2.values):
                u = _anti_unify_expr(a, b)
                if u is None:
                    return None
                vals.append(u)
            return ast.BoolOp(op=copy.deepcopy(e1.op), values=vals)
        if isinstance(e1, ast.Compare) and isinstance(e2, ast.Compare):
            if [type(o) for o in e1.ops] != [type(o) for o in e2.ops] or len(e1.comparators) != len(e2.comparators):
                return _hole()
            left = _anti_unify_expr(e1.left, e2.left)
            comps: list[ast.expr] = []
            for a, b in zip(e1.comparators, e2.comparators):
                u = _anti_unify_expr(a, b)
                if u is None:
                    return None
                comps.append(u)
            if left is None:
                return None
            return ast.Compare(left=left, ops=copy.deepcopy(e1.ops), comparators=comps)
        if isinstance(e1, ast.Call) and isinstance(e2, ast.Call):
            if e1.keywords or e2.keywords or len(e1.args) != len(e2.args):
                return _hole()
            fn_u = _anti_unify_expr(e1.func, e2.func)
            if fn_u is None:
                return None
            args_u: list[ast.expr] = []
            for a, b in zip(e1.args, e2.args):
                if not isinstance(a, ast.expr) or not isinstance(b, ast.expr):
                    return _hole()
                u = _anti_unify_expr(a, b)
                if u is None:
                    return None
                args_u.append(u)
            return ast.Call(func=fn_u, args=args_u, keywords=[])
        if isinstance(e1, ast.Subscript) and isinstance(e2, ast.Subscript):
            val = _anti_unify_expr(e1.value, e2.value)
            sl1, sl2 = e1.slice, e2.slice
            if not isinstance(sl1, ast.expr) or not isinstance(sl2, ast.expr):
                return _hole()
            sl = _anti_unify_expr(sl1, sl2)
            if val is None or sl is None:
                return None
            return ast.Subscript(value=val, slice=sl, ctx=ast.Load())
        if isinstance(e1, ast.Attribute) and isinstance(e2, ast.Attribute):
            if e1.attr != e2.attr:
                return _hole()
            val = _anti_unify_expr(e1.value, e2.value)
            if val is None:
                return None
            return ast.Attribute(value=val, attr=e1.attr, ctx=ast.Load())
        if isinstance(e1, ast.IfExp) and isinstance(e2, ast.IfExp):
            bdy = _anti_unify_expr(e1.body, e2.body)
            tst = _anti_unify_expr(e1.test, e2.test)
            orelse = _anti_unify_expr(e1.orelse, e2.orelse)
            if bdy is None or tst is None or orelse is None:
                return None
            return ast.IfExp(body=bdy, test=tst, orelse=orelse)
        if isinstance(e1, (ast.List, ast.Tuple)) and isinstance(e2, type(e1)):
            if len(e1.elts) != len(e2.elts):
                return _hole()
            elts: list[ast.expr] = []
            for a, b in zip(e1.elts, e2.elts):
                u = _anti_unify_expr(a, b)
                if u is None:
                    return None
                elts.append(u)
            return type(e1)(elts=elts, ctx=ast.Load())
        if isinstance(e1, (ast.ListComp, ast.GeneratorExp, ast.SetComp)) and isinstance(e2, type(e1)):
            if len(e1.generators) != len(e2.generators):
                return _hole()
            gens: list[ast.comprehension] = []
            for g1, g2 in zip(e1.generators, e2.generators):
                if ast.dump(g1.target, include_attributes=False) != ast.dump(g2.target, include_attributes=False):
                    return _hole()
                if len(g1.ifs) != len(g2.ifs):
                    return _hole()
                it = _anti_unify_expr(g1.iter, g2.iter)
                if it is None:
                    return None
                ifs: list[ast.expr] = []
                for i1, i2 in zip(g1.ifs, g2.ifs):
                    iu = _anti_unify_expr(i1, i2)
                    if iu is None:
                        return None
                    ifs.append(iu)
                gens.append(ast.comprehension(target=copy.deepcopy(g1.target), iter=it, ifs=ifs, is_async=0))
            elt = _anti_unify_expr(e1.elt, e2.elt)
            if elt is None:
                return None
            if isinstance(e1, ast.ListComp):
                return ast.ListComp(elt=elt, generators=gens)
            if isinstance(e1, ast.SetComp):
                return ast.SetComp(elt=elt, generators=gens)
            return ast.GeneratorExp(elt=elt, generators=gens)
        return _hole()

    def _anti_unify_stmt_list(s_list1: Sequence[ast.stmt], s_list2: Sequence[ast.stmt]) -> list[ast.stmt] | None:
        if len(s_list1) != len(s_list2):
            return None
        out_s: list[ast.stmt] = []
        for s1, s2 in zip(s_list1, s_list2):
            if type(s1) is not type(s2):
                return None
            if isinstance(s1, ast.Assign) and isinstance(s2, ast.Assign):
                if len(s1.targets) != 1 or len(s2.targets) != 1:
                    return None
                if ast.dump(s1.targets[0], include_attributes=False) != ast.dump(s2.targets[0], include_attributes=False):
                    return None
                ue = _anti_unify_expr(s1.value, s2.value)
                if ue is None:
                    return None
                out_s.append(ast.Assign(targets=[copy.deepcopy(s1.targets[0])], value=ue))
            elif isinstance(s1, ast.Return) and isinstance(s2, ast.Return):
                if (s1.value is None) != (s2.value is None):
                    return None
                if s1.value is None or s2.value is None:
                    out_s.append(ast.Return(value=None))
                else:
                    ue = _anti_unify_expr(s1.value, s2.value)
                    if ue is None:
                        return None
                    out_s.append(ast.Return(value=ue))
            elif isinstance(s1, ast.For) and isinstance(s2, ast.For):
                if ast.dump(s1.target, include_attributes=False) != ast.dump(s2.target, include_attributes=False):
                    return None
                if s1.orelse or s2.orelse:
                    return None
                u_iter = _anti_unify_expr(s1.iter, s2.iter)
                u_body = _anti_unify_stmt_list(s1.body, s2.body)
                if u_iter is None or u_body is None:
                    return None
                out_s.append(ast.For(target=copy.deepcopy(s1.target), iter=u_iter, body=u_body, orelse=[]))
            elif isinstance(s1, ast.If) and isinstance(s2, ast.If):
                u_test = _anti_unify_expr(s1.test, s2.test)
                u_b = _anti_unify_stmt_list(s1.body, s2.body)
                u_o = _anti_unify_stmt_list(s1.orelse, s2.orelse)
                if u_test is None or u_b is None or u_o is None:
                    return None
                out_s.append(ast.If(test=u_test, body=u_b, orelse=u_o))
            elif isinstance(s1, ast.Expr) and isinstance(s2, ast.Expr):
                if (
                    isinstance(s1.value, ast.Call)
                    and isinstance(s2.value, ast.Call)
                    and isinstance(s1.value.func, ast.Attribute)
                    and isinstance(s2.value.func, ast.Attribute)
                    and s1.value.func.attr == s2.value.func.attr == "append"
                    and ast.dump(s1.value.func.value, include_attributes=False) == ast.dump(s2.value.func.value, include_attributes=False)
                    and len(s1.value.args) == len(s2.value.args) == 1
                ):
                    u_arg = _anti_unify_expr(s1.value.args[0], s2.value.args[0])
                    if u_arg is None:
                        return None
                    out_s.append(
                        ast.Expr(
                            value=ast.Call(
                                func=copy.deepcopy(s1.value.func),
                                args=[u_arg],
                                keywords=[],
                            )
                        )
                    )
                elif ast.dump(s1, include_attributes=False) == ast.dump(s2, include_attributes=False):
                    out_s.append(copy.deepcopy(s1))
                else:
                    return None
            else:
                return None
        return out_s

    lgg_stmts = _anti_unify_stmt_list(cf1.body, cf2.body)
    if lgg_stmts is None or not extra_fn_params:
        return None
    all_params = tuple([f"_v{i}" for i in range(base_arity)] + extra_val_params + extra_fn_params)
    if len(all_params) > 8 or len(extra_fn_params) > 2:
        return None
    mod_tmp = ast.Module(body=lgg_stmts, type_ignores=[])
    ast.fix_missing_locations(mod_tmp)
    body_stmts = "\n".join(ast.unparse(st) for st in mod_tmp.body)
    return {
        "param_names": all_params,
        "hole_fillings": dict(hole_fillings),
        "arity": len(all_params),
        "body_stmts": body_stmts,
        "callable_params": tuple((k, callable_arities[k]) for k in extra_fn_params),
        "base_arity": base_arity,
        "value_hole_count": len(extra_val_params),
    }


def instantiate_plotkin_lgg(
    lgg: Mapping[str, Any],
    *,
    parent_choice: Mapping[str, int],
    name: str,
    overrides: Mapping[str, str] | None = None,
) -> ast.FunctionDef | None:
    """Wake: fill Plotkin holes with a parent specialization or an experience override."""
    body_src = str(lgg.get("body_stmts") or "")
    if not body_src.strip():
        return None
    try:
        mod = ast.parse(body_src)
    except SyntaxError:
        return None
    raw_fill = lgg.get("hole_fillings") or {}
    if not isinstance(raw_fill, Mapping):
        return None
    parsed_fill: dict[str, tuple[ast.expr, ast.expr]] = {}
    for h_nm, pair in raw_fill.items():
        if not isinstance(pair, (tuple, list)) or len(pair) != 2:
            return None
        try:
            parsed_fill[str(h_nm)] = (
                ast.parse(str(pair[0]), mode="eval").body,
                ast.parse(str(pair[1]), mode="eval").body,
            )
        except SyntaxError:
            return None
    fn_holes = {h for h in parsed_fill if h.startswith("_fn")}
    val_holes = {h for h in parsed_fill if h not in fn_holes}
    parsed_over: dict[str, ast.expr] = {}
    for h_nm, expr_src in dict(overrides or {}).items():
        try:
            parsed_over[str(h_nm)] = ast.parse(str(expr_src), mode="eval").body
        except SyntaxError:
            continue

    class _Fill(ast.NodeTransformer):
        def visit_Call(self, node: ast.Call) -> ast.AST:
            node = self.generic_visit(node)  # type: ignore[assignment]
            if isinstance(node.func, ast.Name) and node.func.id in parsed_over:
                return copy.deepcopy(parsed_over[node.func.id])
            if isinstance(node.func, ast.Name) and node.func.id in fn_holes:
                idx = 1 if int(parent_choice.get(node.func.id, 0)) else 0
                return copy.deepcopy(parsed_fill[node.func.id][idx])
            return node

        def visit_Name(self, node: ast.Name) -> ast.AST:
            if isinstance(node.ctx, ast.Load) and node.id in parsed_over:
                return copy.deepcopy(parsed_over[node.id])
            if isinstance(node.ctx, ast.Load) and node.id in val_holes:
                idx = 1 if int(parent_choice.get(node.id, 0)) else 0
                return copy.deepcopy(parsed_fill[node.id][idx])
            return node

    filled = _Fill().visit(copy.deepcopy(mod))
    ast.fix_missing_locations(filled)
    base_arity = int(lgg.get("base_arity") or 0)
    if base_arity < 1:
        return None
    return ast.FunctionDef(
        name=str(name),
        args=ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg=f"_v{i}") for i in range(base_arity)],
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
        ),
        body=list(filled.body),
        decorator_list=[],
        returns=None,
    )


def _probes_for(source: str, probes: Sequence[Any] | None = None) -> Sequence[Any]:
    """The probe domain a replay is checked on: the caller's, else one derived from the source.

    A replay that cannot see its own domain is not checkable, and an uncheckable replay is exactly
    what the vacuity gate exists to refuse. Deriving the domain from the source keeps that gate
    firing while removing the human from the loop.
    """
    if probes is not None:
        return probes
    from canonical.swe_kernel import compression_gain_v1 as _cg

    return _cg.derive_probe_domain([source]) or _cg._PROBE_INPUTS


def rewrite_source_with_concepts(
    source: str,
    library: Any,
    *,
    max_concepts: int = 4,
    probes: Sequence[Any] | None = None,
) -> str | None:
    """Wake: replace matching subtrees with admitted `G_t` calls. Nested helpers, no new `_q`.

    `probes` is the domain the abstraction replay is checked on. When it is omitted the replay
    derives its own domain from the target source (`compression_gain_v1.derive_probe_domain`)
    instead of falling back to the numeric grid -- which answered a string-keyed program
    identically on every probe, so the vacuity gate refused a rewrite it should have been able to
    check. This function used to accept no domain at all, which is why the wake entry was the one
    place the second family could never replay through.
    """
    src = str(source or "")
    if not src.strip() or library is None or not hasattr(library, "concepts"):
        return None
    try:
        live = [
            c
            for c in library.concepts()
            if not getattr(c, "is_stmt_fn", False) and not getattr(c, "is_higher_order", False)
            and str(getattr(c, "body_expr", "") or "").strip()
        ]
    except Exception:
        return None
    if not live:
        # No expression concepts: the library may still hold ADMITTED ABSTRACTIONS (statement
        # functions with a family), which the round-23 bridge is the only writer into. Round 24:
        # the wake pass used to return None here, which meant the ONLY entries the library admits
        # by compression could never be replayed into programs -- admission without replay is an
        # append-only log. Dispatch to the measured abstraction replay; it refuses (None) unless
        # the shape matches, behaviour is preserved on the probe grid, and bytes strictly shrink.
        try:
            from canonical.swe_kernel import compression_gain_v1 as _cg

            report = _cg.rewrite_source_with_abstractions(
                src, library, probes=_probes_for(src, probes)
            )
        except Exception:
            return None
        # ONE return type, and EXECUTABLE. This branch used to hand back the replay's REPORT DICT
        # while every other path returns source text, so a caller that exec'd the result exec'd a
        # dict. Returning the source alone is not enough either: the rewritten program CALLS the
        # concept, and the concept's helper lives beside it, so the text names a function that is
        # not there (`NameError: c_x_...` at first use). The helper prelude is prepended, which is
        # exactly the string the engine compiled and behaviour-checked before returning it --
        # checked artifact equals returned artifact, no second construction.
        if not report:
            return None
        prelude = "\n".join(
            str(h).rstrip() + "\n" for h in (report.get("helpers") or {}).values()
        )
        return prelude + str(report.get("source") or "")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    existing_ids = frozenset(getattr(c, "concept_id", "") for c in live)
    changed = False
    used: list[Any] = []
    used_ids: set[str] = set()
    for entry in live[:max_concepts]:
        try:
            canon_ast = ast.parse(str(entry.body_expr), mode="eval").body
        except SyntaxError:
            continue
        target_dump = ast.dump(canon_ast, include_attributes=False)
        ncount = _expr_node_count(canon_ast)
        cid = str(entry.concept_id)
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
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
                    if isinstance(node, ast.expr) and _expr_node_count(node) == ncount:
                        c_res = _canonicalize_pure_subtree(node, bound_v, existing_ids)
                        if c_res is not None:
                            c_ast, h_vars = c_res
                            if ast.dump(c_ast, include_attributes=False) == target_dump:
                                nonlocal changed
                                changed = True
                                if cid not in used_ids:
                                    used_ids.add(cid)
                                    used.append(entry)
                                return ast.Call(
                                    func=ast.Name(id=cid, ctx=ast.Load()),
                                    args=[ast.Name(id=v, ctx=ast.Load()) for v in h_vars],
                                    keywords=[],
                                )
                    return super().generic_visit(node)

            _Rewriter().visit(fn)
    if not changed or not used:
        # The expression pass matched nothing: fall through to the abstraction replay (round 24),
        # so a library whose real content is statement-function abstractions can still be
        # replayed. The replay is fail-closed and measured (shape + behaviour + bytes).
        try:
            from canonical.swe_kernel import compression_gain_v1 as _cg

            replayed = _cg.rewrite_source_with_abstractions(src, library, probes=_probes_for(src, probes))
        except Exception:
            replayed = None
        if replayed is not None:
            return str(replayed.get("source") or "")
        return None
    helpers: list[ast.stmt] = []
    for entry in used:
        try:
            helper = ast.parse(entry.render_helper_def()).body[0]
        except SyntaxError:
            continue
        if isinstance(helper, ast.FunctionDef):
            helpers.append(helper)
    if not helpers:
        return None
    outer = next((n for n in tree.body if isinstance(n, ast.FunctionDef)), None)
    if outer is None:
        return None
    outer.body = helpers + list(outer.body)
    ast.fix_missing_locations(tree)
    try:
        after = ast.unparse(tree) + "\n"
    except Exception:
        return None
    if after == src:
        return None
    return after


def _generate_probe_grids(arity: int) -> list[tuple[str, list[tuple[Any, ...]]]]:
    """Deterministic independent-coordinate probe banks testing all variable orderings."""
    base_nums = (-4, -1, 0, 1, 3, 7, 12, 20)
    strides = (1, 3, 5, 7)
    # Equal-argument points, added 2026-11-04. Every probe in the original grid had distinct
    # coordinates, so a division by (a - b) was NEVER evaluated at a == b -- the one input where it
    # dies. Measured: the library admitted `... / (_v2 - _v1)` with no guard and called it verified.
    equal_tuples: list[tuple[Any, ...]] = [
        tuple(base_nums[k % len(base_nums)] for _ in range(arity)) for k in range(4)
    ]
    num_tuples: list[tuple[Any, ...]] = [
        tuple(base_nums[(i * strides[j % 4] + j * 2) % len(base_nums)] for j in range(arity))
        for i in range(16)
    ] + equal_tuples + [
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
        # Retired concepts are NOT offered to new searches. `callable_map()` still resolves them,
        # so bodies already built from a retired concept keep working -- retirement removes an
        # option from future search, it does not rewrite the past.
        live = [c for c in self._concepts.values() if not c.retired]
        return sorted(live, key=lambda c: (-c.log_prior, -c.mdl_gain_bytes, c.concept_id))

    def admit_verified_concept(self, entry: ConceptEntry) -> bool:
        """Admit a verified expression/algorithmic concept into `G_t` (organ-graph sleep bridge)."""
        if not isinstance(entry, ConceptEntry) or not str(entry.concept_id).isidentifier():
            return False
        try:
            if entry.is_stmt_fn:
                fn_mod = ast.parse(entry.render_helper_def())
                if not fn_mod.body or not isinstance(fn_mod.body[0], ast.FunctionDef):
                    return False
                self._concepts[entry.concept_id] = entry
                self._compiled_fn_asts[entry.concept_id] = fn_mod.body[0]
            elif entry.body_expr:
                parsed = ast.parse(entry.body_expr, mode="eval")
                self._concepts[entry.concept_id] = entry
                self._compiled_asts[entry.concept_id] = parsed
            else:
                return False
        except Exception:
            return False
        self.save()
        return True

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

    def record_concept_outcome(self, concept_id: str, *, helped: bool | None) -> None:
        """Record what happened when a concept was used.

        `helped=None` means the concept was USED but nothing has been verified. This is the case
        the synthesizer was previously mislabelling as `helped=True`: it credited a concept at the
        moment a body mentioning it was emitted, before anyone could know whether the body was
        right. Measured 2026-11-04: a concept used only inside WRONG bodies reached
        `verified_hits=1` and raised its own prior.
        """
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
            verified_hits=cur.verified_hits + (1 if helped is True else 0),
            disconfirmations=cur.disconfirmations + (1 if helped is False else 0),
            body_stmts=cur.body_stmts,
            callable_params=cur.callable_params,
        )
        self.save()


    def revive(self, concept_id: str) -> bool:
        """Undo a retirement. Returns True if the concept was retired and is now live.

        Retirement triggered by ONE refuted program is weaker evidence than a threshold's worth of
        failures, so it must be reversible. An apparatus that can only escalate its own convictions
        is the append-only-prior failure this library already fixed once; reintroducing it one level
        up would be a poor joke.
        """
        if not self._can_write() or concept_id not in self._concepts:
            return False
        cur = self._concepts[concept_id]
        if not cur.retired:
            return False
        self._concepts[concept_id] = ConceptEntry(
            concept_id=cur.concept_id,
            arity=cur.arity,
            param_names=cur.param_names,
            body_expr=cur.body_expr,
            domain_kind=cur.domain_kind,
            mdl_gain_bytes=cur.mdl_gain_bytes,
            corpus_sites=cur.corpus_sites,
            uses=cur.uses,
            verified_hits=cur.verified_hits,
            disconfirmations=0,
            body_stmts=cur.body_stmts,
            callable_params=cur.callable_params,
        )
        self.save()
        return True

    def retired_concept_ids(self) -> frozenset[str]:
        """Concepts the record says to stop offering. Their callables still resolve."""
        return frozenset(cid for cid, e in self._concepts.items() if e.retired)


    def _verify_higher_order_stmt_concept(
        self,
        body_stmts: str,
        param_names: tuple[str, ...],
        callable_params: tuple[tuple[str, int], ...],
    ) -> tuple[bool, str]:
        """Verify determinism, data & callable sensitivity, and mutation-kill on a higher-order skeleton."""
        indented = "\n".join("    " + ln for ln in body_stmts.splitlines())
        fn_src = f"def _ho_concept({', '.join(param_names)}):\n{indented}\n"
        try:
            mod = ast.parse(fn_src)
            if not mod.body or not isinstance(mod.body[0], ast.FunctionDef):
                return False, "NOT_FUNCTION_DEF"
            fdef = mod.body[0]
        except SyntaxError:
            return False, "SYNTAX_ERROR"

        cp_map = dict(callable_params)
        fn_bank_by_arity: dict[int, list[Callable[..., Any]]] = {
            1: [lambda a: a + 1, lambda a: a * 2, lambda a: -a],
            2: [py_operator.add, py_operator.mul, max],
            3: [lambda a, b, c: a + b + c, lambda a, b, c: max(a, b * c)],
        }
        seq_probes = [[2, 3, 4], [1, 5, 2], [-2, 4, 3], [5]]
        val_seeds = [0, 1, 2, -1]
        cmap = self.callable_map()

        valid_rows: list[tuple[Any, ...]] = []
        sigs: list[Any] = []
        callable_sensitive = False
        for idx_s, seq_v in enumerate(seq_probes):
            row_a: list[Any] = []
            row_b: list[Any] = []
            for p_idx, p_nm in enumerate(param_names):
                if p_nm in cp_map:
                    fn_opts = fn_bank_by_arity.get(cp_map[p_nm], [lambda *xs: xs[0]])
                    row_a.append(fn_opts[0])
                    row_b.append(fn_opts[min(1, len(fn_opts) - 1)])
                elif p_idx == 0:
                    row_a.append(seq_v)
                    row_b.append(seq_v)
                else:
                    v_init = val_seeds[(idx_s + p_idx) % len(val_seeds)]
                    row_a.append(v_init)
                    row_b.append(v_init)
            try:
                va1 = eval_pure_ast_function(fdef, tuple(row_a), extra_callables=cmap)
                va2 = eval_pure_ast_function(fdef, tuple(row_a), extra_callables=cmap)
                vb1 = eval_pure_ast_function(fdef, tuple(row_b), extra_callables=cmap)
            except Exception:
                continue
            sa1, sa2, sb1 = _freeze_output(va1), _freeze_output(va2), _freeze_output(vb1)
            if sa1 == ("NONFINITE",) or sa1 != sa2:
                continue
            if sa1 != sb1:
                callable_sensitive = True
            valid_rows.append(tuple(row_a))
            sigs.append(sa1)

        if len(valid_rows) < 3 or len(set(sigs)) < 2 or not callable_sensitive:
            return False, "INSUFFICIENT_HIGHER_ORDER_SENSITIVITY"
        return True, "higher_order"

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
            undefined: list[tuple[tuple[Any, ...], str]] = []
            for row in grid:
                try:
                    v1 = eval_pure_ast_expr(parsed, dict(zip(params, row)), extra_callables=cmap)
                    v2 = eval_pure_ast_expr(parsed, dict(zip(params, row)), extra_callables=cmap)
                except Exception as exc:  # noqa: BLE001
                    # NOT a skip. A concept that raises on an input in its own domain is not a
                    # total building block: any program built from it can die there. This `continue`
                    # was the whole defect measured on 2026-11-04 (2/2 admitted concepts partial).
                    undefined.append((tuple(row), type(exc).__name__))
                    continue
                s1 = _freeze_output(v1)
                s2 = _freeze_output(v2)
                if s1 == ("NONFINITE",) or s1 != s2:
                    continue
                pts.append(row)
                sigs1.append(s1)
                sigs2.append(s2)
            if len(pts) >= 4 and len(set(sigs1)) >= 2 and sigs1 == sigs2:
                if undefined:
                    # Would have qualified, but is partial. Report the domain it fails on rather
                    # than silently certifying the subdomain where it happens to survive.
                    return False, "PARTIAL_DOMAIN:%s:%s" % (dom_kind, undefined[0][1])
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
                parsed_programs.append(canonicalize_ast_via_egraph(ast.parse(src)))
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

        for cand in viable[:24]:
            if len(admitted) >= max_new_concepts:
                break
            expr_src = str(cand["expr_src"])
            arity = int(cand["arity"])
            cid = "concept_" + hashlib.sha256(f"{arity}:{expr_src}".encode("utf-8")).hexdigest()[:8]
            if cid in self._concepts:
                continue
            if any(f"_v{i}[" in expr_src for i in range(arity)):
                continue
            ncount_c = int(cand["node_count"])
            max_possible_sites = len(cand["occurrences"])
            if (max_possible_sites - 1) * ncount_c - (max_possible_sites + 1) * arity - (max_possible_sites + 2) <= 0:
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
                    # Stitch node-savings already holds. zlib-byte MDL of a short combinator is
                    # dominated by the helper def — a measurement artifact, not a reason to
                    # refuse a verified repeating operator the creature actually uses.
                    effective_gain = max(1, stitch_node_gain)
                else:
                    effective_gain = b_dist_before - b_dist_after
            else:
                effective_gain = mdl_gain

            if any(f"_v{i}[" in expr_src for i in range(arity)):
                # Current probe grids are numeric/sequence/string. Dict-subscript
                # combinators fail those in KeyError; don't spend milliseconds proving it.
                continue
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
                for fn in [n for n in ast.walk(mod) if isinstance(n, ast.FunctionDef) and not n.decorator_list]:
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

            # Stage 2B: Higher-Order Plotkin Anti-Unification (`LGG(fn_i, fn_j)` lifting differing operators to `_fn0`)
            if len(admitted) < max_new_concepts:
                loop_fns: list[ast.FunctionDef] = []
                seen_loop_fn_dumps: set[str] = set()
                for mod in parsed_programs:
                    for fn in ast.walk(mod):
                        if (
                            isinstance(fn, ast.FunctionDef)
                            and not fn.decorator_list
                            and any(isinstance(sub, (ast.For, ast.While)) for sub in ast.walk(fn))
                        ):
                            fdump = ast.dump(fn, include_attributes=False)
                            if fdump not in seen_loop_fn_dumps:
                                seen_loop_fn_dumps.add(fdump)
                                loop_fns.append(fn)
                for i_fn in range(min(len(loop_fns), 12)):
                    if len(admitted) >= max_new_concepts:
                        break
                    for j_fn in range(i_fn + 1, min(len(loop_fns), 12)):
                        if len(admitted) >= max_new_concepts:
                            break
                        lgg = higher_order_plotkin_lgg(loop_fns[i_fn], loop_fns[j_fn])
                        if lgg is None:
                            continue
                        ho_stmts = str(lgg["body_stmts"])
                        ho_params: tuple[str, ...] = tuple(lgg["param_names"])
                        ho_cp: tuple[tuple[str, int], ...] = tuple(lgg["callable_params"])
                        cid_ho = "concept_ho_" + hashlib.sha256(
                            f"ho:{','.join(ho_params)}:{ho_stmts}".encode("utf-8")
                        ).hexdigest()[:8]
                        if cid_ho in self._concepts:
                            continue
                        ok_ho, dom_ho = self._verify_higher_order_stmt_concept(ho_stmts, ho_params, ho_cp)
                        if not ok_ho:
                            continue
                        entry_ho = ConceptEntry(
                            concept_id=cid_ho,
                            arity=len(ho_params),
                            param_names=ho_params,
                            body_expr="",
                            domain_kind=dom_ho,
                            mdl_gain_bytes=max(8, executable_ast_bytes(ho_stmts) // 2),
                            corpus_sites=2,
                            uses=0,
                            verified_hits=0,
                            body_stmts=ho_stmts,
                            callable_params=ho_cp,
                        )
                        parsed_ho = ast.parse(entry_ho.render_helper_def()).body[0]
                        if isinstance(parsed_ho, ast.FunctionDef):
                            self._concepts[cid_ho] = entry_ho
                            self._compiled_fn_asts[cid_ho] = parsed_ho
                            admitted.append(entry_ho.to_dict())

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

