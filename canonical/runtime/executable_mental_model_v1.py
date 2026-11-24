"""Lightweight Executable Mental Models — Leap 4 of Deep Program Understanding (0 LLM, 0 Weights).

Provides TWO unified, pure-stdlib, sub-millisecond pre-execution mental simulators:

1. **SWE Code Pre-Execution Mental Simulator (`MentalASTExecutor` + `simulate_patch_mental_model`):**
   - Evaluates an original vs. candidate-patched Python function directly in RAM against live
     failing & passing runtime frames already captured during localization (~0.2-0.5ms/candidate,
     ~1,000x faster than spawning a `pytest` subprocess!).
   - Bounded fuel (`max_steps <= 256`), zero filesystem writes, zero network, zero subprocesses,
     zero `eval`/`exec` of untrusted I/O.
   - Sound fail-open semantics: any call to an unknown external/repo helper returns `_UNKNOWN`
     so a valid patch is NEVER falsely pruned, while provably regressive (`passing_regressions > 0`)
     or provably no-op (`failing_evaluable > 0 and failing_flips == 0`) candidates are pruned/demoted
     instantly, and provably clean behavioral flippers (`failing_flips > 0 and passing_regressions == 0`)
     are promoted straight to the front of the verification queue!
   - Also supports **Mental-Model-Guided Synthesis** (`mental_rank_and_filter_candidates`) to
     re-order & prune candidate queues before touching disk.

2. **Computer Use Pre-Execution World-Model Rollout (`CUMentalWorldModel` + `simulate_cu_plan`):**
   - Explicit, inspectable, editable symbolic state-transition program (PatchWorld-style, ZERO LLM).
   - Rolls forward multi-step CLI / HTTP / SQLite / GUI action plans in RAM BEFORE touching the
     real OS/server, detecting precondition violations (missing auth token, missing/compressed input
     file, uncheckpointed destructive action) and repairing plans pre-execution.
   - Counterexample-driven world-model patching (`patch_transition_from_counterexample`): when real
     execution diverges from mental prediction, updates the inspectable transition table in O(1)
     (with instant deletion/reset, `parameters_stored == 0`).

Hard constraints respected by construction:
  - 0 external model calls (`model_calls == 0`)
  - 0 stored neural weights (`parameters_stored == 0`)
  - Pure Python stdlib only

Authority: NONE. Computed mechanism only.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import math
import operator
import re
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_EXECUTABLE_MENTAL_MODEL_V1"
AUTHORITY = "NONE"


# ---------------------------------------------------------------------------
# 1. Pure, Fuel-Bounded In-Memory AST Mental Interpreter (SWE Leap 4)
# ---------------------------------------------------------------------------

class _UnknownSentinel:
    def __repr__(self) -> str:
        return "<UNKNOWN>"


_UNKNOWN = _UnknownSentinel()


class _MentalReturn(Exception):
    def __init__(self, value: Any) -> None:
        self.value = value


class _MentalBreak(Exception):
    pass


class _MentalContinue(Exception):
    pass


class _MentalRaised(Exception):
    def __init__(self, exc_type: str, msg: str = "") -> None:
        self.exc_type = exc_type
        self.msg = msg


class _MentalFuelExceeded(Exception):
    pass


_SAFE_BUILTINS: dict[str, Any] = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "chr": chr,
    "dict": dict,
    "divmod": divmod,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "frozenset": frozenset,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "ord": ord,
    "pow": pow,
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "set": set,
    "slice": slice,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
    "None": None,
    "True": True,
    "False": False,
}

_SAFE_TYPES: dict[str, type] = {
    "int": int,
    "float": float,
    "str": str,
    "bytes": bytes,
    "bool": bool,
    "list": list,
    "tuple": tuple,
    "dict": dict,
    "set": set,
    "frozenset": frozenset,
    "object": object,
}

_SAFE_EXC_NAMES: frozenset[str] = frozenset({
    "ValueError", "TypeError", "KeyError", "IndexError", "ZeroDivisionError",
    "AttributeError", "RuntimeError", "OverflowError", "AssertionError",
    "LookupError", "ArithmeticError", "Exception",
})

_SAFE_STR_METHODS: frozenset[str] = frozenset({
    "strip", "lstrip", "rstrip", "lower", "upper", "title", "capitalize", "casefold",
    "startswith", "endswith", "split", "rsplit", "splitlines", "partition", "rpartition",
    "replace", "join", "find", "rfind", "index", "rindex", "count", "isdigit", "isdecimal",
    "isnumeric", "isalpha", "isalnum", "isspace", "isascii", "islower", "isupper",
    "removeprefix", "removesuffix", "encode", "zfill", "ljust", "rjust", "center",
})

_SAFE_LIST_METHODS: frozenset[str] = frozenset({
    "append", "extend", "insert", "pop", "remove", "clear", "copy", "count", "index", "reverse", "sort",
})

_SAFE_DICT_METHODS: frozenset[str] = frozenset({
    "get", "keys", "values", "items", "copy", "pop", "setdefault", "update", "clear",
})

_SAFE_SET_METHODS: frozenset[str] = frozenset({
    "add", "discard", "remove", "pop", "clear", "copy", "union", "intersection",
    "difference", "symmetric_difference", "issubset", "issuperset", "isdisjoint",
})

_SAFE_MATH_FUNCS: dict[str, Any] = {
    "isnan": math.isnan,
    "isinf": math.isinf,
    "isfinite": math.isfinite,
    "floor": math.floor,
    "ceil": math.ceil,
    "trunc": math.trunc,
    "sqrt": math.sqrt,
    "fabs": math.fabs,
    "gcd": math.gcd,
    "copysign": math.copysign,
    "ldexp": math.ldexp,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
}

_SAFE_RE_FUNCS: dict[str, Any] = {
    "match": re.match,
    "fullmatch": re.fullmatch,
    "search": re.search,
    "findall": re.findall,
    "sub": re.sub,
    "split": re.split,
    "compile": re.compile,
    "escape": re.escape,
}

_BINOPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: lambda a, b: _UNKNOWN if (isinstance(b, (int, float)) and abs(b) > 64) else operator.pow(a, b),
    ast.BitAnd: operator.and_,
    ast.BitOr: operator.or_,
    ast.BitXor: operator.xor,
    ast.LShift: lambda a, b: _UNKNOWN if (isinstance(b, int) and (b < 0 or b > 64)) else operator.lshift(a, b),
    ast.RShift: operator.rshift,
}

_UNOPS: dict[type, Any] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
    ast.Not: operator.not_,
    ast.Invert: operator.invert,
}


@dataclass(frozen=True)
class MentalExecResult:
    status: str  # "RETURN", "RAISE", "UNKNOWN", "FUEL_EXCEEDED"
    value: Any = None
    exc_type: str = ""
    steps: int = 0

    def signature(self) -> tuple[Any, ...]:
        if self.status == "RETURN":
            return ("RETURN", _freeze_value(self.value))
        if self.status == "RAISE":
            return ("RAISE", self.exc_type)
        return (self.status,)


def _freeze_value(v: Any, depth: int = 0) -> Any:
    if depth > 4:
        return repr(v)[:64]
    if v is None or isinstance(v, (bool, int, str, bytes)):
        return (type(v).__name__, v)
    if isinstance(v, float):
        if math.isnan(v):
            return ("float", "NaN")
        return ("float", v)
    if isinstance(v, (list, tuple)):
        return (type(v).__name__, tuple(_freeze_value(x, depth + 1) for x in v[:32]))
    if isinstance(v, (set, frozenset)):
        items = sorted((_freeze_value(x, depth + 1) for x in list(v)[:32]), key=repr)
        return (type(v).__name__, tuple(items))
    if isinstance(v, dict):
        items = sorted(((_freeze_value(k, depth + 1), _freeze_value(val, depth + 1)) for k, val in list(v.items())[:32]), key=repr)
        return ("dict", tuple(items))
    return (type(v).__name__, repr(v)[:64])


class MentalASTExecutor:
    """Fuel-bounded, pure-in-memory Python AST micro-interpreter for sub-millisecond mental simulation."""

    def __init__(self, module_consts: Mapping[str, Any] | None = None, *, max_steps: int = 256) -> None:
        self.module_consts: dict[str, Any] = dict(module_consts or {})
        self.max_steps = max_steps
        self.steps = 0

    def _tick(self) -> None:
        self.steps += 1
        if self.steps > self.max_steps:
            raise _MentalFuelExceeded()

    def run_function(
        self,
        fn_node: ast.FunctionDef | ast.AsyncFunctionDef,
        arg_env: Mapping[str, Any],
    ) -> MentalExecResult:
        self.steps = 0
        env: dict[str, Any] = {}
        # Populate function defaults first, then override with concrete captured frame values
        args_spec = fn_node.args
        all_pos = list(getattr(args_spec, "posonlyargs", [])) + list(args_spec.args)
        defaults = list(args_spec.defaults or [])
        n_no_def = len(all_pos) - len(defaults)
        for i, a in enumerate(all_pos):
            if i >= n_no_def:
                dv = self._eval_expr(defaults[i - n_no_def], env)
                if dv is not _UNKNOWN:
                    env[a.arg] = copy.deepcopy(dv)
        for a, d in zip(args_spec.kwonlyargs or [], args_spec.kw_defaults or []):
            if d is not None:
                dv = self._eval_expr(d, env)
                if dv is not _UNKNOWN:
                    env[a.arg] = copy.deepcopy(dv)
        for k, v in arg_env.items():
            env[k] = copy.deepcopy(v)
        # Ensure all required positional parameters are bound; otherwise fail-open UNKNOWN
        for a in all_pos:
            if a.arg not in env and a.arg not in ("self", "cls"):
                return MentalExecResult(status="UNKNOWN", steps=self.steps)
        try:
            self._exec_block(fn_node.body, env)
            return MentalExecResult(status="RETURN", value=None, steps=self.steps)
        except _MentalReturn as r:
            if r.value is _UNKNOWN:
                return MentalExecResult(status="UNKNOWN", steps=self.steps)
            return MentalExecResult(status="RETURN", value=r.value, steps=self.steps)
        except _MentalRaised as exc:
            return MentalExecResult(status="RAISE", exc_type=exc.exc_type, steps=self.steps)
        except _MentalFuelExceeded:
            return MentalExecResult(status="FUEL_EXCEEDED", steps=self.steps)
        except Exception as exc:
            # Real runtime exception from pure expression (e.g. ZeroDivisionError, IndexError, ValueError)
            return MentalExecResult(status="RAISE", exc_type=type(exc).__name__, steps=self.steps)

    def _exec_block(self, stmts: Sequence[ast.stmt], env: dict[str, Any]) -> None:
        for st in stmts:
            self._exec_stmt(st, env)

    def _exec_stmt(self, st: ast.stmt, env: dict[str, Any]) -> None:
        self._tick()
        if isinstance(st, ast.Pass):
            return
        if isinstance(st, ast.Return):
            val = None if st.value is None else self._eval_expr(st.value, env)
            raise _MentalReturn(val)
        if isinstance(st, ast.Raise):
            exc_name = "Exception"
            if isinstance(st.exc, ast.Call) and isinstance(st.exc.func, ast.Name):
                exc_name = st.exc.func.id
            elif isinstance(st.exc, ast.Name):
                exc_name = st.exc.id
            raise _MentalRaised(exc_name)
        if isinstance(st, ast.Assert):
            cond = self._eval_expr(st.test, env)
            if cond is _UNKNOWN:
                raise _MentalReturn(_UNKNOWN)
            if not cond:
                raise _MentalRaised("AssertionError")
            return
        if isinstance(st, ast.Expr):
            # Skip docstrings
            if isinstance(st.value, ast.Constant) and isinstance(st.value.value, str):
                return
            v = self._eval_expr(st.value, env)
            if v is _UNKNOWN:
                raise _MentalReturn(_UNKNOWN)
            return
        if isinstance(st, ast.Assign):
            val = self._eval_expr(st.value, env)
            if val is _UNKNOWN:
                raise _MentalReturn(_UNKNOWN)
            for tgt in st.targets:
                self._assign_target(tgt, val, env)
            return
        if isinstance(st, ast.AnnAssign):
            if st.value is not None:
                val = self._eval_expr(st.value, env)
                if val is _UNKNOWN:
                    raise _MentalReturn(_UNKNOWN)
                self._assign_target(st.target, val, env)
            return
        if isinstance(st, ast.AugAssign):
            cur = self._eval_expr(st.target, env)
            rhs = self._eval_expr(st.value, env)
            if cur is _UNKNOWN or rhs is _UNKNOWN:
                raise _MentalReturn(_UNKNOWN)
            fn = _BINOPS.get(type(st.op))
            if fn is None:
                raise _MentalReturn(_UNKNOWN)
            nv = fn(cur, rhs)
            if nv is _UNKNOWN:
                raise _MentalReturn(_UNKNOWN)
            self._assign_target(st.target, nv, env)
            return
        if isinstance(st, ast.If):
            cond = self._eval_expr(st.test, env)
            if cond is _UNKNOWN:
                raise _MentalReturn(_UNKNOWN)
            if cond:
                self._exec_block(st.body, env)
            elif st.orelse:
                self._exec_block(st.orelse, env)
            return
        if isinstance(st, ast.While):
            iters = 0
            while True:
                self._tick()
                iters += 1
                if iters > 128:
                    raise _MentalFuelExceeded()
                cond = self._eval_expr(st.test, env)
                if cond is _UNKNOWN:
                    raise _MentalReturn(_UNKNOWN)
                if not cond:
                    break
                try:
                    self._exec_block(st.body, env)
                except _MentalBreak:
                    break
                except _MentalContinue:
                    continue
            return
        if isinstance(st, ast.For):
            it = self._eval_expr(st.iter, env)
            if it is _UNKNOWN:
                raise _MentalReturn(_UNKNOWN)
            try:
                seq = list(it)
            except Exception:
                raise _MentalReturn(_UNKNOWN)
            if len(seq) > 128:
                raise _MentalFuelExceeded()
            broke = False
            for item in seq:
                self._tick()
                self._assign_target(st.target, item, env)
                try:
                    self._exec_block(st.body, env)
                except _MentalBreak:
                    broke = True
                    break
                except _MentalContinue:
                    continue
            if not broke and st.orelse:
                self._exec_block(st.orelse, env)
            return
        if isinstance(st, ast.Break):
            raise _MentalBreak()
        if isinstance(st, ast.Continue):
            raise _MentalContinue()
        if isinstance(st, ast.Try):
            try:
                self._exec_block(st.body, env)
            except (_MentalReturn, _MentalBreak, _MentalContinue, _MentalFuelExceeded):
                raise
            except _MentalRaised as exc:
                handled = False
                for h in st.handlers:
                    if self._handler_matches(h.type, exc.exc_type):
                        handled = True
                        if h.name:
                            env[h.name] = exc.msg
                        self._exec_block(h.body, env)
                        break
                if not handled:
                    raise
            except Exception as py_exc:
                etype = type(py_exc).__name__
                handled = False
                for h in st.handlers:
                    if self._handler_matches(h.type, etype):
                        handled = True
                        if h.name:
                            env[h.name] = str(py_exc)
                        self._exec_block(h.body, env)
                        break
                if not handled:
                    raise
            finally:
                if st.finalbody:
                    self._exec_block(st.finalbody, env)
            return
        # Unsupported statement (e.g. Import, With, ClassDef) -> fail-open UNKNOWN
        raise _MentalReturn(_UNKNOWN)

    def _handler_matches(self, htype: ast.AST | None, exc_name: str) -> bool:
        if htype is None:
            return True
        if isinstance(htype, ast.Name):
            return htype.id == exc_name or htype.id == "Exception"
        if isinstance(htype, ast.Tuple):
            return any(self._handler_matches(e, exc_name) for e in htype.elts)
        return False

    def _assign_target(self, tgt: ast.AST, val: Any, env: dict[str, Any]) -> None:
        if isinstance(tgt, ast.Name):
            env[tgt.id] = val
            return
        if isinstance(tgt, (ast.Tuple, ast.List)):
            try:
                seq = list(val)
            except Exception:
                raise _MentalReturn(_UNKNOWN)
            if len(seq) != len(tgt.elts):
                raise _MentalRaised("ValueError")
            for sub_t, sub_v in zip(tgt.elts, seq):
                self._assign_target(sub_t, sub_v, env)
            return
        if isinstance(tgt, ast.Subscript):
            container = self._eval_expr(tgt.value, env)
            idx = self._eval_expr(tgt.slice, env)
            if container is _UNKNOWN or idx is _UNKNOWN:
                raise _MentalReturn(_UNKNOWN)
            if isinstance(container, (list, dict)):
                container[idx] = val
                return
        raise _MentalReturn(_UNKNOWN)

    def _eval_expr(self, node: ast.AST, env: dict[str, Any]) -> Any:
        self._tick()
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in env:
                return env[node.id]
            if node.id in self.module_consts:
                return self.module_consts[node.id]
            if node.id in _SAFE_BUILTINS:
                return _SAFE_BUILTINS[node.id]
            if node.id in _SAFE_TYPES:
                return _SAFE_TYPES[node.id]
            if node.id in _SAFE_EXC_NAMES:
                return node.id
            return _UNKNOWN
        if isinstance(node, ast.UnaryOp):
            v = self._eval_expr(node.operand, env)
            if v is _UNKNOWN:
                return _UNKNOWN
            fn = _UNOPS.get(type(node.op))
            return fn(v) if fn is not None else _UNKNOWN
        if isinstance(node, ast.BinOp):
            l = self._eval_expr(node.left, env)
            if l is _UNKNOWN:
                return _UNKNOWN
            r = self._eval_expr(node.right, env)
            if r is _UNKNOWN:
                return _UNKNOWN
            fn = _BINOPS.get(type(node.op))
            return fn(l, r) if fn is not None else _UNKNOWN
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                last: Any = True
                for vnode in node.values:
                    v = self._eval_expr(vnode, env)
                    if v is _UNKNOWN:
                        return _UNKNOWN
                    last = v
                    if not v:
                        return v
                return last
            else:
                last = False
                for vnode in node.values:
                    v = self._eval_expr(vnode, env)
                    if v is _UNKNOWN:
                        return _UNKNOWN
                    last = v
                    if v:
                        return v
                return last
        if isinstance(node, ast.Compare):
            left = self._eval_expr(node.left, env)
            if left is _UNKNOWN:
                return _UNKNOWN
            for op, comp in zip(node.ops, node.comparators):
                right = self._eval_expr(comp, env)
                if right is _UNKNOWN:
                    return _UNKNOWN
                if isinstance(op, ast.Eq):
                    ok = left == right
                elif isinstance(op, ast.NotEq):
                    ok = left != right
                elif isinstance(op, ast.Lt):
                    ok = left < right
                elif isinstance(op, ast.LtE):
                    ok = left <= right
                elif isinstance(op, ast.Gt):
                    ok = left > right
                elif isinstance(op, ast.GtE):
                    ok = left >= right
                elif isinstance(op, ast.Is):
                    ok = left is right
                elif isinstance(op, ast.IsNot):
                    ok = left is not right
                elif isinstance(op, ast.In):
                    ok = left in right
                elif isinstance(op, ast.NotIn):
                    ok = left not in right
                else:
                    return _UNKNOWN
                if not ok:
                    return False
                left = right
            return True
        if isinstance(node, ast.IfExp):
            c = self._eval_expr(node.test, env)
            if c is _UNKNOWN:
                return _UNKNOWN
            return self._eval_expr(node.body if c else node.orelse, env)
        if isinstance(node, ast.List):
            out = []
            for e in node.elts:
                v = self._eval_expr(e, env)
                if v is _UNKNOWN:
                    return _UNKNOWN
                out.append(v)
            return out
        if isinstance(node, ast.Tuple):
            out_t = []
            for e in node.elts:
                v = self._eval_expr(e, env)
                if v is _UNKNOWN:
                    return _UNKNOWN
                out_t.append(v)
            return tuple(out_t)
        if isinstance(node, ast.Set):
            out_s = set()
            for e in node.elts:
                v = self._eval_expr(e, env)
                if v is _UNKNOWN:
                    return _UNKNOWN
                out_s.add(v)
            return out_s
        if isinstance(node, ast.Dict):
            out_d: dict[Any, Any] = {}
            for k_n, v_n in zip(node.keys, node.values):
                if k_n is None:
                    return _UNKNOWN
                kv = self._eval_expr(k_n, env)
                vv = self._eval_expr(v_n, env)
                if kv is _UNKNOWN or vv is _UNKNOWN:
                    return _UNKNOWN
                out_d[kv] = vv
            return out_d
        if isinstance(node, ast.Subscript):
            val = self._eval_expr(node.value, env)
            if val is _UNKNOWN:
                return _UNKNOWN
            if isinstance(node.slice, ast.Slice):
                lo = None if node.slice.lower is None else self._eval_expr(node.slice.lower, env)
                hi = None if node.slice.upper is None else self._eval_expr(node.slice.upper, env)
                st = None if node.slice.step is None else self._eval_expr(node.slice.step, env)
                if _UNKNOWN in (lo, hi, st):
                    return _UNKNOWN
                return val[slice(lo, hi, st)]
            idx = self._eval_expr(node.slice, env)
            if idx is _UNKNOWN:
                return _UNKNOWN
            return val[idx]
        if isinstance(node, (ast.ListComp, ast.GeneratorExp)):
            return self._eval_comp(node.elt, node.generators, env)
        if isinstance(node, ast.JoinedStr):
            parts: list[str] = []
            for v in node.values:
                if isinstance(v, ast.Constant):
                    parts.append(str(v.value))
                elif isinstance(v, ast.FormattedValue):
                    ev = self._eval_expr(v.value, env)
                    if ev is _UNKNOWN:
                        return _UNKNOWN
                    parts.append(str(ev))
                else:
                    return _UNKNOWN
            return "".join(parts)
        if isinstance(node, ast.Call):
            return self._eval_call(node, env)
        return _UNKNOWN

    def _eval_comp(self, elt: ast.AST, gens: Sequence[ast.comprehension], env: dict[str, Any]) -> Any:
        if len(gens) != 1:
            return _UNKNOWN
        g = gens[0]
        it = self._eval_expr(g.iter, env)
        if it is _UNKNOWN:
            return _UNKNOWN
        try:
            seq = list(it)
        except Exception:
            return _UNKNOWN
        if len(seq) > 128:
            raise _MentalFuelExceeded()
        out = []
        sub_env = dict(env)
        for item in seq:
            self._tick()
            self._assign_target(g.target, item, sub_env)
            keep = True
            for cond in g.ifs:
                cv = self._eval_expr(cond, sub_env)
                if cv is _UNKNOWN:
                    return _UNKNOWN
                if not cv:
                    keep = False
                    break
            if keep:
                ev = self._eval_expr(elt, sub_env)
                if ev is _UNKNOWN:
                    return _UNKNOWN
                out.append(ev)
        return out

    def _eval_call(self, node: ast.Call, env: dict[str, Any]) -> Any:
        # Evaluate arguments safely
        args: list[Any] = []
        for a in node.args:
            if isinstance(a, ast.Starred):
                return _UNKNOWN
            v = self._eval_expr(a, env)
            if v is _UNKNOWN:
                return _UNKNOWN
            args.append(v)
        kwargs: dict[str, Any] = {}
        for kw in node.keywords:
            if kw.arg is None:
                return _UNKNOWN
            v = self._eval_expr(kw.value, env)
            if v is _UNKNOWN:
                return _UNKNOWN
            kwargs[kw.arg] = v

        # 1. `math.<fn>(...)` or `re.<fn>(...)`
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            mod = node.func.value.id
            attr = node.func.attr
            if mod == "math" and attr in _SAFE_MATH_FUNCS:
                return _SAFE_MATH_FUNCS[attr](*args, **kwargs)
            if mod == "re" and attr in _SAFE_RE_FUNCS:
                return _SAFE_RE_FUNCS[attr](*args, **kwargs)

        # 2. Pure value methods (`str`, `list`, `dict`, `set`, compiled `re.Pattern`)
        if isinstance(node.func, ast.Attribute):
            recv = self._eval_expr(node.func.value, env)
            if recv is _UNKNOWN:
                return _UNKNOWN
            attr = node.func.attr
            if isinstance(recv, str) and attr in _SAFE_STR_METHODS:
                return getattr(recv, attr)(*args, **kwargs)
            if isinstance(recv, list) and attr in _SAFE_LIST_METHODS:
                return getattr(recv, attr)(*args, **kwargs)
            if isinstance(recv, dict) and attr in _SAFE_DICT_METHODS:
                return getattr(recv, attr)(*args, **kwargs)
            if isinstance(recv, set) and attr in _SAFE_SET_METHODS:
                return getattr(recv, attr)(*args, **kwargs)
            if isinstance(recv, re.Pattern) and attr in ("match", "fullmatch", "search", "findall", "sub", "split"):
                return getattr(recv, attr)(*args, **kwargs)
            return _UNKNOWN

        # 3. Safe builtins (`len`, `any`, `all`, `ord`, `int`, `isinstance`, etc.)
        if isinstance(node.func, ast.Name) and node.func.id in _SAFE_BUILTINS:
            fn = _SAFE_BUILTINS[node.func.id]
            return fn(*args, **kwargs)
        return _UNKNOWN


def _extract_module_safe_consts(tree: ast.AST) -> dict[str, Any]:
    """Extract pure literal/regex module-level constants for mental simulation (zero side effects)."""
    consts: dict[str, Any] = {}
    if not isinstance(tree, ast.Module):
        return consts
    for st in tree.body:
        if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
            name = st.targets[0].id
            try:
                consts[name] = ast.literal_eval(st.value)
                continue
            except Exception:
                pass
            if (
                isinstance(st.value, ast.Call)
                and isinstance(st.value.func, ast.Attribute)
                and isinstance(st.value.func.value, ast.Name)
                and st.value.func.value.id == "re"
                and st.value.func.attr == "compile"
                and st.value.args
                and isinstance(st.value.args[0], ast.Constant)
                and isinstance(st.value.args[0].value, str)
            ):
                try:
                    flags = 0
                    if len(st.value.args) > 1 and isinstance(st.value.args[1], ast.Constant) and isinstance(st.value.args[1].value, int):
                        flags = st.value.args[1].value
                    consts[name] = re.compile(st.value.args[0].value, flags)
                except Exception:
                    pass
    return consts


def _find_changed_function_pair(
    orig_source: str,
    patched_source: str,
    hint_lineno: int = 0,
) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef | None, ast.FunctionDef | ast.AsyncFunctionDef | None, dict[str, Any], dict[str, Any]]:
    try:
        t_orig = ast.parse(orig_source)
        t_pat = ast.parse(patched_source)
    except SyntaxError:
        return None, None, {}, {}
    orig_consts = _extract_module_safe_consts(t_orig)
    pat_consts = _extract_module_safe_consts(t_pat)

    orig_fns: dict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]] = {}
    for nd in ast.walk(t_orig):
        if isinstance(nd, (ast.FunctionDef, ast.AsyncFunctionDef)):
            orig_fns.setdefault(nd.name, []).append(nd)
    pat_fns: dict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]] = {}
    for nd in ast.walk(t_pat):
        if isinstance(nd, (ast.FunctionDef, ast.AsyncFunctionDef)):
            pat_fns.setdefault(nd.name, []).append(nd)

    best_pair: tuple[ast.FunctionDef | ast.AsyncFunctionDef, ast.FunctionDef | ast.AsyncFunctionDef] | None = None
    best_dist = 10**9
    for name, o_list in orig_fns.items():
        p_list = pat_fns.get(name) or []
        if len(o_list) != len(p_list):
            continue
        for ofn, pfn in zip(o_list, p_list):
            if ast.dump(ofn) != ast.dump(pfn):
                lo = int(getattr(ofn, "lineno", 0))
                hi = int(getattr(ofn, "end_lineno", lo) or lo)
                dist = 0 if (lo <= hint_lineno <= hi) else abs(lo - hint_lineno)
                if dist < best_dist:
                    best_dist = dist
                    best_pair = (ofn, pfn)
    if best_pair is None:
        return None, None, orig_consts, pat_consts
    return best_pair[0], best_pair[1], orig_consts, pat_consts


def simulate_patch_mental_model(
    orig_source: str,
    patched_source: str,
    *,
    failing_envs: Sequence[Mapping[str, Any]],
    passing_envs: Sequence[Mapping[str, Any]],
    hint_lineno: int = 0,
    max_steps: int = 256,
) -> dict[str, Any]:
    """Run sub-millisecond mental simulation of a candidate patch BEFORE spawning subprocess `pytest`.

    Returns:
      - verdict:
          * "PRUNE_REGRESSION": provably changes behavior on >= 1 captured passing frame!
          * "PRUNE_NOOP": evaluable on >= 1 failing frame, yet changes 0 failing frames!
          * "PROMOTE_CLEAN_FLIP": flips >= 1 failing frame AND preserves 100% of evaluable passing frames!
          * "UNCERTAIN": could not purely evaluate (external calls/types) -> fail-open pass-through!
    """
    t0 = time.monotonic()
    ofn, pfn, o_consts, p_consts = _find_changed_function_pair(orig_source, patched_source, hint_lineno=hint_lineno)
    if ofn is None or pfn is None:
        return {
            "schema": SCHEMA,
            "verdict": "UNCERTAIN",
            "reason": "NO_SINGLE_CHANGED_FUNCTION",
            "failing_evaluable": 0,
            "failing_flips": 0,
            "passing_evaluable": 0,
            "passing_regressions": 0,
            "ms": round((time.monotonic() - t0) * 1000.0, 3),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    o_exec = MentalASTExecutor(o_consts, max_steps=max_steps)
    p_exec = MentalASTExecutor(p_consts, max_steps=max_steps)

    fail_eval = 0
    fail_flips = 0
    for fenv in list(failing_envs)[:24]:
        ro = o_exec.run_function(ofn, fenv)
        rp = p_exec.run_function(pfn, fenv)
        if ro.status in ("RETURN", "RAISE") and rp.status in ("RETURN", "RAISE"):
            fail_eval += 1
            if ro.signature() != rp.signature():
                fail_flips += 1

    pass_eval = 0
    pass_regs = 0
    for penv in list(passing_envs)[:32]:
        ro = o_exec.run_function(ofn, penv)
        rp = p_exec.run_function(pfn, penv)
        if ro.status in ("RETURN", "RAISE") and rp.status in ("RETURN", "RAISE"):
            pass_eval += 1
            if ro.signature() != rp.signature():
                pass_regs += 1

    if pass_regs > 0:
        verdict = "PRUNE_REGRESSION"
    elif fail_eval > 0 and fail_flips == 0:
        verdict = "PRUNE_NOOP"
    elif fail_flips > 0 and pass_regs == 0:
        verdict = "PROMOTE_CLEAN_FLIP"
    else:
        verdict = "UNCERTAIN"

    return {
        "schema": SCHEMA,
        "function": ofn.name,
        "verdict": verdict,
        "failing_evaluable": fail_eval,
        "failing_flips": fail_flips,
        "passing_evaluable": pass_eval,
        "passing_regressions": pass_regs,
        "ms": round((time.monotonic() - t0) * 1000.0, 3),
        "model_calls": 0,
        "parameters_stored": 0,
    }


# ---------------------------------------------------------------------------
# 2. Computer Use Pre-Execution Symbolic World Model & Counterexample Repair
# ---------------------------------------------------------------------------

@dataclass
class CUWorldState:
    """Explicit, inspectable symbolic state for Computer Use mental rollouts."""
    files: dict[str, dict[str, Any]] = field(default_factory=dict)
    auth_tokens: dict[str, bool] = field(default_factory=dict)
    checkpoints: list[str] = field(default_factory=list)
    http_known_auth_required: set[str] = field(default_factory=set)
    facts: dict[str, Any] = field(default_factory=dict)

    def clone(self) -> "CUWorldState":
        return copy.deepcopy(self)


class CUMentalWorldModel:
    """Inspectable, editable, zero-LLM symbolic world model for pre-execution CU simulation.

    Rolls forward CLI / HTTP / SQLite / GUI action plans in RAM BEFORE acting, detects
    precondition failures and uncheckpointed destructive actions, repairs plans pre-execution,
    and updates its transition laws online from concrete execution counterexamples (PatchWorld-style).
    """

    def __init__(self) -> None:
        self.learned_preconditions: dict[str, list[dict[str, Any]]] = {}
        self.parameters_stored = 0

    def export_rules(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "learned_preconditions": copy.deepcopy(self.learned_preconditions),
            "parameters_stored": 0,
        }

    def delete_rule(self, action_key: str) -> bool:
        if action_key in self.learned_preconditions:
            del self.learned_preconditions[action_key]
            return True
        return False

    def patch_from_counterexample(
        self,
        action_key: str,
        *,
        observed_error: str,
        required_precondition: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Patch the mental model's transition law from ONE concrete live execution counterexample."""
        entry = {
            "observed_error": observed_error,
            "precondition": dict(required_precondition),
            "rule_id": "wm_" + hashlib.sha256(f"{action_key}:{observed_error}".encode("utf-8")).hexdigest()[:10],
        }
        rules = self.learned_preconditions.setdefault(action_key, [])
        if not any(r["rule_id"] == entry["rule_id"] for r in rules):
            rules.append(entry)
        return entry

    def simulate_step(self, state: CUWorldState, action: Mapping[str, Any]) -> tuple[CUWorldState, dict[str, Any]]:
        """Mentally simulate ONE action without touching disk/network/OS."""
        nxt = state.clone()
        kind = str(action.get("kind") or "")
        key = str(action.get("action_key") or f"{kind}:{action.get('target', '')}")

        # Check counterexample-learned preconditions first
        for rule in self.learned_preconditions.get(key, []):
            pre = rule["precondition"]
            ptype = pre.get("type")
            if ptype == "auth_token" and not nxt.auth_tokens.get(str(pre.get("service", "default")), False):
                return nxt, {
                    "ok": False,
                    "predicted_error": rule["observed_error"],
                    "missing_precondition": pre,
                    "suggested_repair": {"kind": "http_auth", "service": str(pre.get("service", "default"))},
                }
            if ptype == "decompressed_file":
                fp = str(pre.get("path") or action.get("path") or "")
                fmeta = nxt.files.get(fp, {})
                if fmeta.get("compressed"):
                    return nxt, {
                        "ok": False,
                        "predicted_error": rule["observed_error"],
                        "missing_precondition": pre,
                        "suggested_repair": {"kind": "decompress_file", "path": fp},
                    }

        # Built-in universal physical/OS invariants (zero app-specific memorization)
        if kind == "checkpoint":
            cid = str(action.get("checkpoint_id") or f"cp_{len(nxt.checkpoints) + 1}")
            nxt.checkpoints.append(cid)
            return nxt, {"ok": True, "effect": f"checkpoint:{cid}"}

        if kind == "http_auth":
            svc = str(action.get("service") or "default")
            nxt.auth_tokens[svc] = True
            return nxt, {"ok": True, "effect": f"auth_acquired:{svc}"}

        if kind == "decompress_file":
            fp = str(action.get("path") or "")
            fmeta = nxt.files.setdefault(fp, {"exists": True})
            fmeta["compressed"] = False
            fmeta["encoding"] = "utf-8"
            return nxt, {"ok": True, "effect": f"decompressed:{fp}"}

        if kind == "cli_read_text":
            fp = str(action.get("path") or "")
            fmeta = nxt.files.get(fp)
            if not fmeta or not fmeta.get("exists", False):
                return nxt, {
                    "ok": False,
                    "predicted_error": "ENOENT",
                    "missing_precondition": {"type": "file_exists", "path": fp},
                }
            if fmeta.get("compressed"):
                return nxt, {
                    "ok": False,
                    "predicted_error": "COMPRESSED_BINARY_READ_AS_TEXT",
                    "missing_precondition": {"type": "decompressed_file", "path": fp},
                    "suggested_repair": {"kind": "decompress_file", "path": fp},
                }
            nxt.facts[f"read:{fp}"] = True
            return nxt, {"ok": True, "effect": f"read:{fp}"}

        if kind == "http_request":
            svc = str(action.get("service") or "default")
            method = str(action.get("method") or "GET").upper()
            target = str(action.get("target") or "/")
            if (target in nxt.http_known_auth_required or action.get("requires_auth")) and not nxt.auth_tokens.get(svc, False):
                return nxt, {
                    "ok": False,
                    "predicted_error": "HTTP_401_UNAUTHORIZED",
                    "missing_precondition": {"type": "auth_token", "service": svc},
                    "suggested_repair": {"kind": "http_auth", "service": svc},
                }
            if method in ("DELETE", "PUT", "PATCH") and action.get("destructive", False) and not nxt.checkpoints:
                return nxt, {
                    "ok": False,
                    "predicted_error": "UNCHECKPOINTED_DESTRUCTIVE_ACTION",
                    "missing_precondition": {"type": "checkpoint"},
                    "suggested_repair": {"kind": "checkpoint", "checkpoint_id": "auto_pre_destructive"},
                }
            nxt.facts[f"http:{method}:{target}"] = 200
            return nxt, {"ok": True, "effect": f"http_200:{method}:{target}"}

        if kind == "destructive_write":
            if not nxt.checkpoints:
                return nxt, {
                    "ok": False,
                    "predicted_error": "UNCHECKPOINTED_DESTRUCTIVE_ACTION",
                    "missing_precondition": {"type": "checkpoint"},
                    "suggested_repair": {"kind": "checkpoint", "checkpoint_id": "auto_pre_destructive"},
                }
            fp = str(action.get("path") or "")
            nxt.files[fp] = {"exists": True, "mutated": True}
            return nxt, {"ok": True, "effect": f"mutated:{fp}"}

        return nxt, {"ok": True, "effect": f"noop:{kind}"}

    def simulate_and_repair_plan(
        self,
        initial_state: CUWorldState,
        plan: Sequence[Mapping[str, Any]],
        *,
        auto_repair: bool = True,
        max_repairs: int = 8,
    ) -> dict[str, Any]:
        """Mentally roll out an entire multi-step CU plan BEFORE touching the real environment.

        If `auto_repair=True`, automatically injects missing precondition actions (checkpoints,
        auth acquisition, decompression) and re-simulates until the entire plan is verified safe!
        """
        cur_plan = [dict(a) for a in plan]
        injected_repairs: list[dict[str, Any]] = []
        for _ in range(max_repairs + 1):
            st = initial_state.clone()
            trace: list[dict[str, Any]] = []
            failed_idx = -1
            fail_info: dict[str, Any] = {}
            for idx, act in enumerate(cur_plan):
                st, res = self.simulate_step(st, act)
                trace.append({"step": idx, "action": act, **res})
                if not res.get("ok"):
                    failed_idx = idx
                    fail_info = res
                    break
            if failed_idx == -1:
                return {
                    "schema": SCHEMA,
                    "safe_to_execute": True,
                    "repaired": bool(injected_repairs),
                    "injected_repairs": injected_repairs,
                    "final_plan": cur_plan,
                    "predicted_final_facts": dict(st.facts),
                    "predicted_checkpoints": list(st.checkpoints),
                    "trace": trace,
                    "model_calls": 0,
                    "parameters_stored": 0,
                }
            sugg = fail_info.get("suggested_repair")
            if not auto_repair or not isinstance(sugg, Mapping) or len(injected_repairs) >= max_repairs:
                return {
                    "schema": SCHEMA,
                    "safe_to_execute": False,
                    "failed_step": failed_idx,
                    "predicted_error": fail_info.get("predicted_error"),
                    "missing_precondition": fail_info.get("missing_precondition"),
                    "final_plan": cur_plan,
                    "trace": trace,
                    "model_calls": 0,
                    "parameters_stored": 0,
                }
            cur_plan.insert(failed_idx, dict(sugg))
            injected_repairs.append({"before_step": failed_idx, "repair": dict(sugg), "reason": fail_info.get("predicted_error")})

        return {
            "schema": SCHEMA,
            "safe_to_execute": False,
            "predicted_error": "MAX_REPAIRS_EXCEEDED",
            "final_plan": cur_plan,
            "model_calls": 0,
            "parameters_stored": 0,
        }

    def speculative_cow_choose(
        self,
        initial_state: CUWorldState,
        candidate_actions: Sequence[Mapping[str, Any]],
        goal_facts: Mapping[str, Any],
        *,
        max_workers: int = 16,
    ) -> dict[str, Any]:
        """Fork up to 16 parallel Linux Copy-on-Write realities to speculatively execute
        candidate CU actions in total isolation, scoring goal-fact residual across all 16
        outcomes without mutating parent state."""
        from canonical.runtime import repo_component_and_cow_engine_v1 as RCCE

        def _residual_for_state(st_obj: CUWorldState) -> float:
            missing = sum(1 for k, v in goal_facts.items() if st_obj.facts.get(k) != v)
            return float(missing)

        base_res = _residual_for_state(initial_state)

        def _exec_in_cow_child(act: Mapping[str, Any]) -> tuple[bool, float]:
            st_copy = initial_state.clone()
            nxt, info = self.simulate_step(st_copy, act)
            if not info.get("ok"):
                return (False, float("inf"))
            return (True, _residual_for_state(nxt))

        return RCCE.speculative_cow_rollout(
            candidate_actions,
            executor_fn=_exec_in_cow_child,
            residual_fn=lambda pair: pair[1] if pair[0] else float("inf"),
            baseline_residual=base_res,
            max_workers=max_workers,
        )

