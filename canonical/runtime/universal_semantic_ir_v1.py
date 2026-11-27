"""Universal Semantic Meaning IR, E-Graph Normalizer, Cross-Language Transfer & Inter-Procedural Data-Flow Graph v1.

Zero-LLM (`model_calls=0`), zero-weight (`parameters_stored=0`), pure-stdlib deep program
understanding engine delivering Architectural Leaps 1 & 2:

  1. Universal Semantic Meaning IR (`lift_to_ir` + `canonicalize_ir`):
     Translates Python (stdlib `ast`), JavaScript/TypeScript, and C/C++ (O(N) Pratt
     recursive-descent parser atop `polyglot_cst_skill_inducer_v1.tokenize_code`) into
     ONE language-agnostic semantic representation (`IRNode`):
       - Semantic Equivalence across syntax & languages:
           * `strlen(s)` (C) == `s.length` (JS/TS) == `len(s)` (Python) -> `Len(s)`
           * `s[-1]` (Python) == `s[len(s)-1]` (Py) == `s[s.length-1]` (JS) == `s[strlen(s)-1]` (C)
             -> `Index(s, BinOp('-', Len(s), Lit(1)))`
           * `for (i = 0; i < n; i++)` == `while (i < n) { ...; i++; }` == `for i in range(n):`
             -> `Loop(var=i, init=0, cond=BinOp('<', i, n), step=BinOp('+', i, 1))`
           * Commutative / relational / boolean E-Graph normalization:
             `NULL != p` == `p != NULL` -> `NotNull(p)`;
             `!(a < b)` -> `BinOp('>=', a, b)`;
             `a > b` -> `BinOp('<', b, a)`;
             `Len(s) > 0` == `Len(s) >= 1` == `Len(s) != 0` -> `NotEmpty(s)`;
             `INT_MAX` / `Number.MAX_SAFE_INTEGER` / `sys.maxsize` -> `Lit('MAX_INT', 'max_int')`.
  2. True Cross-Language Single-Experience Skill Induction & Native Lowering
     (`induce_semantic_skill` -> external JSON store `BRAIN_UNIVERSAL_SEMANTIC_SKILL_STORE_V1`
      -> `recall_semantic_candidates` + `lower_ir_to_lang`):
     Learn ONE verified fix in C (or Python or JS), lift & canonicalize to semantic IR,
     alpha-abstract all identifiers (`$V0`, `$V1`, ...) with zero concrete names or language
     tokens leaked, and transfer + natively lower into ANY target language (C <-> Python <-> JS/TS)
     even when written in a completely different syntactic style (`for` vs `while`, `s[-1]` vs
     `s[strlen(s)-1]`, `NULL != x` vs `x is not None`).
  3. Inter-Procedural Cross-File Data-Flow & Causal Graph (`build_cross_file_dataflow_graph`
     + `backward_causal_slice`):
     Statement-level intra-procedural def-use + inter-procedural call-argument/return-value
     edges across repository files (`ARISE` May 2026 / `CausalRepair` Aug 2026 principle),
     tracing failing sinks backward across call boundaries to upstream root-cause files.
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from canonical.runtime import polyglot_cst_skill_inducer_v1 as CST

SCHEMA = "BRAIN_UNIVERSAL_SEMANTIC_SKILL_STORE_V1"
AUTHORITY = "NONE"

_MAX_INT_SYMS = frozenset({
    "INT_MAX", "UINT_MAX", "LONG_MAX", "LLONG_MAX", "SIZE_MAX", "INT64_MAX", "INT32_MAX",
    "MAX_SAFE_INTEGER", "MAX_VALUE", "maxsize",
})
_NULL_SYMS = frozenset({"None", "null", "NULL", "nullptr", "undefined"})
_BOOL_TRUE = frozenset({"True", "true"})
_BOOL_FALSE = frozenset({"False", "false"})

_COMMUTATIVE_OPS = frozenset({"+", "*", "==", "!=", "&&", "||", "&", "|", "^"})
_FLIP_REL = {">": "<", ">=": "<="}
_NEG_REL = {"==": "!=", "!=": "==", "<": ">=", "<=": ">", ">": "<=", ">=": "<"}


# ---------------------------------------------------------------------------
# 1. Universal Semantic IR Representation (JSON-serializable nested dicts!)
# ---------------------------------------------------------------------------
# Every IR node is a plain dict: {"op": "...", ...} so it serializes directly to
# inspectable, editable, deletable external JSON with ZERO opaque objects & ZERO weights.

def _ir_var(name: str) -> dict[str, Any]:
    return {"op": "Var", "name": name}


def _ir_lit(value: Any, kind: str) -> dict[str, Any]:
    return {"op": "Lit", "value": value, "kind": kind}


def _ir_len(target: dict[str, Any]) -> dict[str, Any]:
    return {"op": "Len", "target": target}


def _ir_index(seq: dict[str, Any], idx: dict[str, Any]) -> dict[str, Any]:
    return {"op": "Index", "seq": seq, "idx": idx}


def _ir_unop(uop: str, arg: dict[str, Any]) -> dict[str, Any]:
    return {"op": "UnOp", "uop": uop, "arg": arg}


def _ir_binop(bop: str, left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return {"op": "BinOp", "bop": bop, "left": left, "right": right}


def _ir_call(callee: str, args: list[dict[str, Any]]) -> dict[str, Any]:
    return {"op": "Call", "callee": callee, "args": args}


def _ir_prop(obj: dict[str, Any], attr: str) -> dict[str, Any]:
    return {"op": "Prop", "obj": obj, "attr": attr}


def _ir_has_key(obj: dict[str, Any], key: dict[str, Any]) -> dict[str, Any]:
    return {"op": "HasKey", "obj": obj, "key": key}


def _ir_key(node: Any) -> str:
    return json.dumps(node, sort_keys=True, separators=(",", ":"))


def _is_int_lit(node: Mapping[str, Any], val: int) -> bool:
    return node.get("op") == "Lit" and node.get("kind") == "int" and node.get("value") == val


def _is_null_lit(node: Mapping[str, Any]) -> bool:
    return node.get("op") == "Lit" and node.get("kind") == "null"


def _is_bool_lit(node: Mapping[str, Any], val: bool) -> bool:
    return node.get("op") == "Lit" and node.get("kind") == "bool" and node.get("value") is val


# ---------------------------------------------------------------------------
# 2. E-Graph Algebraic & Semantic Equivalence Normalizer
# ---------------------------------------------------------------------------

def canonicalize_ir(node: dict[str, Any]) -> dict[str, Any]:
    """Rewrite an IR expression or statement to its canonical semantic normal form.

    Equivalence laws applied bottom-up until fixed point:
      - `!(a rel b)` -> `a neg(rel) b`
      - `!!x` -> `x`
      - `a > b` -> `b < a`; `a >= b` -> `b <= a`
      - Commutative ops sorted by canonical key: `NULL != x` == `x != NULL`, `a + b` == `b + a`
      - `x == null` -> `UnOp('is_null', x)`; `x != null` -> `UnOp('not_null', x)`
      - `x == false` -> `UnOp('!', x)`; `x == true` -> `x`
      - `Len(s) == 0` / `Len(s) <= 0` -> `UnOp('is_empty', s)`
      - `Len(s) > 0` / `Len(s) >= 1` / `Len(s) != 0` -> `UnOp('not_empty', s)`
      - `Index(s, -k)` (Python negative index) -> `Index(s, BinOp('-', Len(s), Lit(k)))`
      - `Call('strlen', [s])` / `Call('len', [s])` / `Prop(s, 'length')` -> `Len(s)`
      - `Prop(Number, 'MAX_SAFE_INTEGER')` / `Prop(sys, 'maxsize')` -> `Lit('MAX_INT', 'max_int')`
    """
    if not isinstance(node, dict):
        return node
    op = node.get("op")

    if op == "Var":
        nm = str(node.get("name") or "")
        if nm in _NULL_SYMS:
            return _ir_lit(None, "null")
        if nm in _BOOL_TRUE:
            return _ir_lit(True, "bool")
        if nm in _BOOL_FALSE:
            return _ir_lit(False, "bool")
        if nm in _MAX_INT_SYMS:
            return _ir_lit("MAX_INT", "max_int")
        return node

    if op == "Lit":
        return node

    if op == "Len":
        return _ir_len(canonicalize_ir(node["target"]))

    if op == "Prop":
        obj = canonicalize_ir(node["obj"])
        attr = str(node.get("attr") or "")
        if attr == "length":
            return _ir_len(obj)
        if attr in _MAX_INT_SYMS and obj.get("op") == "Var" and obj.get("name") in ("Number", "sys", "math", "limits"):
            return _ir_lit("MAX_INT", "max_int")
        return _ir_prop(obj, attr)

    if op == "Call":
        callee = str(node.get("callee") or "")
        args = [canonicalize_ir(a) for a in (node.get("args") or [])]
        if callee in ("len", "strlen") and len(args) == 1:
            return _ir_len(args[0])
        if callee in ("isfinite", "Number.isFinite", "math.isfinite") and len(args) == 1:
            return _ir_unop("isfinite", args[0])
        if callee in ("isnan", "Number.isNaN", "math.isnan") and len(args) == 1:
            return _ir_unop("isnan", args[0])
        if callee in ("Object.hasOwn", "Object.prototype.hasOwnProperty.call") and len(args) == 2:
            return _ir_has_key(args[0], args[1])
        if callee.endswith(".hasOwnProperty") and len(args) == 1:
            recv = callee[: -len(".hasOwnProperty")]
            return _ir_call("unsafe_has_own", [_ir_var(recv), args[0]])
        return _ir_call(callee, args)

    if op == "HasKey":
        return _ir_has_key(canonicalize_ir(node["obj"]), canonicalize_ir(node["key"]))

    if op == "Index":
        seq = canonicalize_ir(node["seq"])
        idx = canonicalize_ir(node["idx"])
        # Canonicalize negative literal index `s[-1]` -> `s[Len(s) - 1]` (Python <-> C/JS equivalence!)
        if idx.get("op") == "UnOp" and idx.get("uop") == "-" and idx["arg"].get("op") == "Lit" and idx["arg"].get("kind") == "int":
            idx = _ir_binop("-", _ir_len(seq), idx["arg"])
        elif idx.get("op") == "Lit" and idx.get("kind") == "int" and int(idx["value"]) < 0:
            idx = _ir_binop("-", _ir_len(seq), _ir_lit(abs(int(idx["value"])), "int"))
        return _ir_index(seq, idx)

    if op == "UnOp":
        uop = str(node.get("uop") or "")
        arg = canonicalize_ir(node["arg"])
        if uop == "!":
            if arg.get("op") == "UnOp" and arg.get("uop") == "!":
                return arg["arg"]
            if arg.get("op") == "UnOp" and arg.get("uop") == "is_null":
                return _ir_unop("not_null", arg["arg"])
            if arg.get("op") == "UnOp" and arg.get("uop") == "not_null":
                return _ir_unop("is_null", arg["arg"])
            if arg.get("op") == "UnOp" and arg.get("uop") == "is_empty":
                return _ir_unop("not_empty", arg["arg"])
            if arg.get("op") == "UnOp" and arg.get("uop") == "not_empty":
                return _ir_unop("is_empty", arg["arg"])
            if arg.get("op") == "BinOp" and arg.get("bop") in _NEG_REL:
                return canonicalize_ir(_ir_binop(_NEG_REL[arg["bop"]], arg["left"], arg["right"]))
            # De Morgan's Laws: `!(A || B) => (!A) && (!B)` and `!(A && B) => (!A) || (!B)`
            if arg.get("op") == "BinOp" and arg.get("bop") == "||":
                return canonicalize_ir(_ir_binop("&&", _ir_unop("!", arg["left"]), _ir_unop("!", arg["right"])))
            if arg.get("op") == "BinOp" and arg.get("bop") == "&&":
                return canonicalize_ir(_ir_binop("||", _ir_unop("!", arg["left"]), _ir_unop("!", arg["right"])))
        if uop == "-" and arg.get("op") == "Lit" and arg.get("kind") == "int":
            return _ir_lit(-int(arg["value"]), "int")
        return _ir_unop(uop, arg)

    if op == "BinOp":
        bop = str(node.get("bop") or "")
        left = canonicalize_ir(node["left"])
        right = canonicalize_ir(node["right"])

        # Normalize `>` and `>=` to `<` and `<=`
        if bop in _FLIP_REL:
            bop = _FLIP_REL[bop]
            left, right = right, left

        # Sort commutative operands deterministically (`NULL != x` == `x != NULL`, `a && b` == `b && a`)
        if bop in _COMMUTATIVE_OPS and _ir_key(left) > _ir_key(right):
            left, right = right, left

        # Null checks
        if bop == "==" and _is_null_lit(left):
            return _ir_unop("is_null", right)
        if bop == "==" and _is_null_lit(right):
            return _ir_unop("is_null", left)
        if bop == "!=" and _is_null_lit(left):
            return _ir_unop("not_null", right)
        if bop == "!=" and _is_null_lit(right):
            return _ir_unop("not_null", left)

        # Boolean literal simplifications
        if bop == "==" and _is_bool_lit(left, True):
            return right
        if bop == "==" and _is_bool_lit(right, True):
            return left
        if bop == "==" and _is_bool_lit(left, False):
            return canonicalize_ir(_ir_unop("!", right))
        if bop == "==" and _is_bool_lit(right, False):
            return canonicalize_ir(_ir_unop("!", left))

        # Length-emptiness equivalence (`Len(s) > 0` == `0 < Len(s)` == `1 <= Len(s)` == `Len(s) != 0`)
        if bop == "<" and _is_int_lit(left, 0) and right.get("op") == "Len":
            return _ir_unop("not_empty", right["target"])
        if bop == "<=" and _is_int_lit(left, 1) and right.get("op") == "Len":
            return _ir_unop("not_empty", right["target"])
        if bop == "!=" and ((_is_int_lit(left, 0) and right.get("op") == "Len") or (_is_int_lit(right, 0) and left.get("op") == "Len")):
            t = right["target"] if right.get("op") == "Len" else left["target"]
            return _ir_unop("not_empty", t)
        if bop in ("==", "<=") and ((_is_int_lit(left, 0) and right.get("op") == "Len") or (_is_int_lit(right, 0) and left.get("op") == "Len")):
            if bop == "==" or (left.get("op") == "Len" and _is_int_lit(right, 0)):
                t = right["target"] if right.get("op") == "Len" else left["target"]
                return _ir_unop("is_empty", t)

        return _ir_binop(bop, left, right)

    # Statement nodes
    if op == "IfGuard":
        return {
            "op": "IfGuard",
            "cond": canonicalize_ir(node["cond"]),
            "body": [canonicalize_ir(s) for s in (node.get("body") or [])],
            "orelse": [canonicalize_ir(s) for s in (node.get("orelse") or [])],
        }
    if op == "Loop":
        return {
            "op": "Loop",
            "var": node.get("var"),
            "init": canonicalize_ir(node["init"]) if node.get("init") is not None else None,
            "cond": canonicalize_ir(node["cond"]) if node.get("cond") is not None else None,
            "step": canonicalize_ir(node["step"]) if node.get("step") is not None else None,
            "body": [canonicalize_ir(s) for s in (node.get("body") or [])],
        }
    if op == "Assign":
        return {"op": "Assign", "target": canonicalize_ir(node["target"]), "value": canonicalize_ir(node["value"])}
    if op == "Return":
        return {"op": "Return", "value": canonicalize_ir(node["value"]) if node.get("value") is not None else None}
    if op == "ExprStmt":
        return {"op": "ExprStmt", "expr": canonicalize_ir(node["expr"])}
    return node


# ---------------------------------------------------------------------------
# 3. Multi-Language Frontends -> Universal Semantic IR (`python`, `js`/`ts`, `c`)
# ---------------------------------------------------------------------------

@dataclass
class LiftedSpan:
    """One semantic statement (or loop/guard header) anchored to source lines."""
    ir: dict[str, Any]
    start_line: int  # 1-based inclusive
    end_line: int    # 1-based inclusive
    indent: str
    kind: str        # 'if', 'loop_for', 'loop_while', 'return', 'assign', 'expr'
    raw_lines: str
    lang: str


def _lift_py_expr(node: ast.AST) -> dict[str, Any]:
    if isinstance(node, ast.Name):
        return _ir_var(node.id)
    if isinstance(node, ast.Constant):
        v = node.value
        if v is None:
            return _ir_lit(None, "null")
        if isinstance(v, bool):
            return _ir_lit(v, "bool")
        if isinstance(v, int):
            return _ir_lit(v, "int")
        if isinstance(v, float):
            return _ir_lit(v, "float")
        if isinstance(v, str):
            return _ir_lit(v, "str")
        return _ir_lit(repr(v), "other")
    if isinstance(node, ast.Attribute):
        return _ir_prop(_lift_py_expr(node.value), node.attr)
    if isinstance(node, ast.Subscript):
        return _ir_index(_lift_py_expr(node.value), _lift_py_expr(node.slice))
    if isinstance(node, ast.UnaryOp):
        m = {ast.Not: "!", ast.USub: "-", ast.UAdd: "+", ast.Invert: "~"}
        return _ir_unop(m.get(type(node.op), "!"), _lift_py_expr(node.operand))
    if isinstance(node, ast.BinOp):
        m = {
            ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "//",
            ast.Mod: "%", ast.BitAnd: "&", ast.BitOr: "|", ast.BitXor: "^",
            ast.LShift: "<<", ast.RShift: ">>",
        }
        return _ir_binop(m.get(type(node.op), "+"), _lift_py_expr(node.left), _lift_py_expr(node.right))
    if isinstance(node, ast.BoolOp):
        bop = "&&" if isinstance(node.op, ast.And) else "||"
        acc = _lift_py_expr(node.values[0])
        for v in node.values[1:]:
            acc = _ir_binop(bop, acc, _lift_py_expr(v))
        return acc
    if isinstance(node, ast.Compare):
        op_map = {
            ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=",
            ast.Is: "==", ast.IsNot: "!=", ast.In: "in", ast.NotIn: "not_in",
        }
        parts: list[dict[str, Any]] = []
        lhs = _lift_py_expr(node.left)
        for op_n, comp in zip(node.ops, node.comparators):
            rhs = _lift_py_expr(comp)
            sym = op_map.get(type(op_n), "==")
            if sym == "in":
                parts.append(_ir_has_key(rhs, lhs))
            elif sym == "not_in":
                parts.append(_ir_unop("!", _ir_has_key(rhs, lhs)))
            else:
                parts.append(_ir_binop(sym, lhs, rhs))
            lhs = rhs
        acc = parts[0]
        for p in parts[1:]:
            acc = _ir_binop("&&", acc, p)
        return acc
    if isinstance(node, ast.Call):
        callee = ast.unparse(node.func)
        return _ir_call(callee, [_lift_py_expr(a) for a in node.args])
    return _ir_lit(ast.unparse(node), "raw")


def _lift_python(source: str) -> list[LiftedSpan]:
    lines = source.splitlines(keepends=True)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    spans: list[LiftedSpan] = []

    def _indent_of(ln: int) -> str:
        if 1 <= ln <= len(lines):
            m = re.match(r"^([ \t]*)", lines[ln - 1])
            return m.group(1) if m else ""
        return ""

    def _walk_body(stmts: Sequence[ast.stmt]) -> None:
        for idx_s, st in enumerate(stmts):
            ln = int(getattr(st, "lineno", 1))
            eln = int(getattr(st, "end_lineno", ln) or ln)
            ind = _indent_of(ln)
            raw = "".join(lines[ln - 1 : eln])
            if isinstance(st, ast.If):
                spans.append(LiftedSpan(
                    ir=canonicalize_ir({"op": "IfGuard", "cond": _lift_py_expr(st.test), "body": [], "orelse": []}),
                    start_line=ln, end_line=ln, indent=ind, kind="if",
                    raw_lines=lines[ln - 1] if 1 <= ln <= len(lines) else raw, lang="python",
                ))
                _walk_body(st.body)
                _walk_body(st.orelse)
            elif isinstance(st, ast.While):
                # Check if previous stmt initialized loop var (`i = 0`) and body increments it (`i += 1`)
                cond_ir = canonicalize_ir(_lift_py_expr(st.test))
                loop_var = None
                init_ir = None
                step_ir = None
                if cond_ir.get("op") == "BinOp" and cond_ir["left"].get("op") == "Var":
                    loop_var = cond_ir["left"]["name"]
                elif cond_ir.get("op") == "BinOp" and cond_ir["right"].get("op") == "Var":
                    loop_var = cond_ir["right"]["name"]
                if loop_var and idx_s > 0 and isinstance(stmts[idx_s - 1], ast.Assign):
                    prev_a = stmts[idx_s - 1]
                    if len(prev_a.targets) == 1 and isinstance(prev_a.targets[0], ast.Name) and prev_a.targets[0].id == loop_var:
                        init_ir = _lift_py_expr(prev_a.value)
                if loop_var:
                    for bs in st.body:
                        if isinstance(bs, ast.AugAssign) and isinstance(bs.target, ast.Name) and bs.target.id == loop_var:
                            op_s = "+" if isinstance(bs.op, ast.Add) else "-"
                            step_ir = _ir_binop(op_s, _ir_var(loop_var), _lift_py_expr(bs.value))
                spans.append(LiftedSpan(
                    ir=canonicalize_ir({"op": "Loop", "var": loop_var, "init": init_ir, "cond": cond_ir, "step": step_ir, "body": []}),
                    start_line=ln, end_line=ln, indent=ind, kind="loop_while",
                    raw_lines=lines[ln - 1] if 1 <= ln <= len(lines) else raw, lang="python",
                ))
                _walk_body(st.body)
            elif isinstance(st, ast.For):
                if isinstance(st.target, ast.Name) and isinstance(st.iter, ast.Call) and isinstance(st.iter.func, ast.Name) and st.iter.func.id == "range":
                    rargs = st.iter.args
                    if len(rargs) == 1:
                        init_ir = _ir_lit(0, "int")
                        lim_ir = _lift_py_expr(rargs[0])
                        step_ir = _ir_binop("+", _ir_var(st.target.id), _ir_lit(1, "int"))
                    elif len(rargs) >= 2:
                        init_ir = _lift_py_expr(rargs[0])
                        lim_ir = _lift_py_expr(rargs[1])
                        step_ir = _ir_binop("+", _ir_var(st.target.id), _lift_py_expr(rargs[2]) if len(rargs) >= 3 else _ir_lit(1, "int"))
                    else:
                        init_ir, lim_ir, step_ir = None, None, None
                    if lim_ir is not None:
                        cond_ir = _ir_binop("<", _ir_var(st.target.id), lim_ir)
                        spans.append(LiftedSpan(
                            ir=canonicalize_ir({"op": "Loop", "var": st.target.id, "init": init_ir, "cond": cond_ir, "step": step_ir, "body": []}),
                            start_line=ln, end_line=ln, indent=ind, kind="loop_for",
                            raw_lines=lines[ln - 1] if 1 <= ln <= len(lines) else raw, lang="python",
                        ))
                _walk_body(st.body)
            elif isinstance(st, ast.Return):
                spans.append(LiftedSpan(
                    ir=canonicalize_ir({"op": "Return", "value": _lift_py_expr(st.value) if st.value is not None else None}),
                    start_line=ln, end_line=eln, indent=ind, kind="return", raw_lines=raw, lang="python",
                ))
            elif isinstance(st, ast.Assign) and len(st.targets) == 1:
                spans.append(LiftedSpan(
                    ir=canonicalize_ir({"op": "Assign", "target": _lift_py_expr(st.targets[0]), "value": _lift_py_expr(st.value)}),
                    start_line=ln, end_line=eln, indent=ind, kind="assign", raw_lines=raw, lang="python",
                ))
            elif isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.With, ast.Try)):
                for sub_attr in ("body", "orelse", "finalbody"):
                    sub = getattr(st, sub_attr, None)
                    if isinstance(sub, list):
                        _walk_body(sub)
                if isinstance(st, ast.Try):
                    for h in st.handlers:
                        _walk_body(h.body)

    _walk_body(tree.body)
    return spans


# --- O(N) Pratt Expression Parser for C/C++/JS/TS ---

_PREC: dict[str, int] = {
    "||": 1, "&&": 2, "|": 3, "^": 4, "&": 5,
    "==": 6, "===": 6, "!=": 6, "!==": 6,
    "<": 7, "<=": 7, ">": 7, ">=": 7, "in": 7,
    "<<": 8, ">>": 8, "+": 9, "-": 9, "*": 10, "/": 10, "%": 10,
}


class _PrattParser:
    def __init__(self, toks: Sequence[CST.Tok]) -> None:
        self.toks = list(toks)
        self.pos = 0

    def peek(self, off: int = 0) -> CST.Tok | None:
        i = self.pos + off
        return self.toks[i] if 0 <= i < len(self.toks) else None

    def eat(self, val: str | None = None) -> CST.Tok | None:
        t = self.peek()
        if t is None:
            return None
        if val is not None and t.text != val:
            return None
        self.pos += 1
        return t

    def parse_expr(self, min_prec: int = 1) -> dict[str, Any] | None:
        lhs = self._parse_unary()
        if lhs is None:
            return None
        while True:
            t = self.peek()
            if t is None or t.text not in _PREC:
                break
            prec = _PREC[t.text]
            if prec < min_prec:
                break
            op_tok = self.eat()
            assert op_tok is not None
            rhs = self.parse_expr(prec + 1)
            if rhs is None:
                return lhs
            op_s = op_tok.text
            if op_s == "===":
                op_s = "=="
            elif op_s == "!==":
                op_s = "!="
            if op_s == "in":
                lhs = _ir_has_key(rhs, lhs)
            else:
                lhs = _ir_binop(op_s, lhs, rhs)
        return lhs

    def _parse_unary(self) -> dict[str, Any] | None:
        t = self.peek()
        if t is None:
            return None
        if t.text in ("!", "-", "~", "+", "*"):
            self.eat()
            sub = self._parse_unary()
            if sub is None:
                return None
            return _ir_unop(t.text, sub)
        return self._parse_postfix()

    def _parse_postfix(self) -> dict[str, Any] | None:
        base = self._parse_primary()
        if base is None:
            return None
        while True:
            t = self.peek()
            if t is None:
                break
            if t.text == "[":
                self.eat("[")
                idx = self.parse_expr(1)
                self.eat("]")
                if idx is None:
                    break
                base = _ir_index(base, idx)
            elif t.text in (".", "->"):
                self.eat()
                attr = self.eat()
                if attr is None:
                    break
                base = _ir_prop(base, attr.text)
            elif t.text == "(":
                self.eat("(")
                args: list[dict[str, Any]] = []
                while self.peek() is not None and self.peek().text != ")":  # type: ignore[union-attr]
                    a = self.parse_expr(1)
                    if a is not None:
                        args.append(a)
                    if self.peek() is not None and self.peek().text == ",":  # type: ignore[union-attr]
                        self.eat(",")
                    else:
                        break
                self.eat(")")
                callee_str = _flatten_callee(base)
                base = _ir_call(callee_str, args)
            elif t.text in ("++", "--"):
                self.eat()
                base = _ir_binop("+" if t.text == "++" else "-", base, _ir_lit(1, "int"))
            else:
                break
        return base

    def _parse_primary(self) -> dict[str, Any] | None:
        t = self.peek()
        if t is None:
            return None
        if t.text == "(":
            save = self.pos
            self.eat("(")
            if self._looks_like_c_cast():
                while self.peek() is not None and self.peek().text != ")":  # type: ignore[union-attr]
                    self.eat()
                self.eat(")")
                return self._parse_unary()
            self.pos = save
            self.eat("(")
            inner = self.parse_expr(1)
            self.eat(")")
            return inner
        if t.kind == "NUM":
            self.eat()
            v = t.text.rstrip("uUlLfF")
            try:
                if v.startswith(("0x", "0X")):
                    return _ir_lit(int(v, 16), "int")
                if "." in v or "e" in v or "E" in v:
                    return _ir_lit(float(v), "float")
                return _ir_lit(int(v), "int")
            except ValueError:
                return _ir_lit(t.text, "raw")
        if t.kind == "STR":
            self.eat()
            raw = t.text
            try:
                decoded = ast.literal_eval(raw)
                return _ir_lit(decoded, "str")
            except Exception:
                return _ir_lit(raw.strip("'\""), "str")
        if t.kind in ("IDENT", "KW"):
            self.eat()
            if t.text in ("NULL", "null", "undefined", "nullptr", "None"):
                return _ir_lit(None, "null")
            if t.text in ("true", "True"):
                return _ir_lit(True, "bool")
            if t.text in ("false", "False"):
                return _ir_lit(False, "bool")
            return _ir_var(t.text)
        return None

    def _looks_like_c_cast(self) -> bool:
        c_types = {"int", "char", "unsigned", "signed", "long", "short", "size_t", "ssize_t", "uint8_t", "int32_t", "int64_t", "uint64_t", "double", "float", "void", "const"}
        i = 0
        seen_t = False
        while True:
            tk = self.peek(i)
            if tk is None:
                return False
            if tk.text == ")":
                nxt = self.peek(i + 1)
                return seen_t and nxt is not None and (nxt.kind in ("IDENT", "KW", "NUM", "STR") or nxt.text in ("(", "-", "!"))
            if tk.text in c_types or tk.text == "*":
                if tk.text in c_types:
                    seen_t = True
                i += 1
                continue
            return False


def _flatten_callee(node: dict[str, Any]) -> str:
    if node.get("op") == "Var":
        return str(node["name"])
    if node.get("op") == "Prop":
        return f"{_flatten_callee(node['obj'])}.{node['attr']}"
    return "call"


def _parse_c_js_expr_tokens(toks: Sequence[CST.Tok]) -> dict[str, Any] | None:
    if not toks:
        return None
    p = _PrattParser(toks)
    ex = p.parse_expr(1)
    return canonicalize_ir(ex) if ex is not None else None


def _split_top_level(toks: Sequence[CST.Tok], sep: str) -> list[list[CST.Tok]]:
    parts: list[list[CST.Tok]] = []
    cur: list[CST.Tok] = []
    depth = 0
    for t in toks:
        if t.text in ("(", "[", "{"):
            depth += 1
        elif t.text in (")", "]", "}"):
            depth = max(0, depth - 1)
        if depth == 0 and t.text == sep:
            parts.append(cur)
            cur = []
        else:
            cur.append(t)
    parts.append(cur)
    return parts


def _lift_c_or_js(source: str, lang: str) -> list[LiftedSpan]:
    lines = source.splitlines(keepends=True)
    spans: list[LiftedSpan] = []

    def _extract_paren_group(toks: list[CST.Tok], start_idx: int) -> tuple[list[CST.Tok], int]:
        if start_idx >= len(toks) or toks[start_idx].text != "(":
            return [], start_idx
        depth = 0
        inner: list[CST.Tok] = []
        i = start_idx
        while i < len(toks):
            v = toks[i].text
            if v == "(":
                depth += 1
                if depth > 1:
                    inner.append(toks[i])
            elif v == ")":
                depth -= 1
                if depth == 0:
                    return inner, i + 1
                inner.append(toks[i])
            else:
                inner.append(toks[i])
            i += 1
        return inner, i

    for ln_idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith(("//", "/*", "*", "#")):
            continue
        ind = re.match(r"^([ \t]*)", raw_line).group(1)  # type: ignore[union-attr]
        toks = CST.tokenize_code(raw_line, language=lang)
        if not toks:
            continue

        # 1. `if (<cond>)`
        if toks[0].text == "if" and len(toks) > 2 and toks[1].text == "(":
            cond_toks, _ = _extract_paren_group(toks, 1)
            cond_ir = _parse_c_js_expr_tokens(cond_toks)
            if cond_ir is not None:
                spans.append(LiftedSpan(
                    ir=canonicalize_ir({"op": "IfGuard", "cond": cond_ir, "body": [], "orelse": []}),
                    start_line=ln_idx, end_line=ln_idx, indent=ind, kind="if", raw_lines=raw_line, lang=lang,
                ))
            continue

        # 2. `for (<init>; <cond>; <step>)`
        if toks[0].text == "for" and len(toks) > 2 and toks[1].text == "(":
            hdr_toks, _ = _extract_paren_group(toks, 1)
            parts = _split_top_level(hdr_toks, ";")
            if len(parts) == 3:
                init_p, cond_p, step_p = parts
                loop_var = None
                init_ir = None
                clean_init = [t for t in init_p if t.text not in ("int", "size_t", "long", "unsigned", "let", "var", "const")]
                if len(clean_init) >= 3 and clean_init[0].kind in ("IDENT", "KW") and clean_init[1].text == "=":
                    loop_var = clean_init[0].text
                    init_ir = _parse_c_js_expr_tokens(clean_init[2:])
                cond_ir = _parse_c_js_expr_tokens(cond_p)
                step_ir = _parse_c_js_expr_tokens(step_p)
                if cond_ir is not None:
                    spans.append(LiftedSpan(
                        ir=canonicalize_ir({"op": "Loop", "var": loop_var, "init": init_ir, "cond": cond_ir, "step": step_ir, "body": []}),
                        start_line=ln_idx, end_line=ln_idx, indent=ind, kind="loop_for", raw_lines=raw_line, lang=lang,
                    ))
            continue

        # 3. `while (<cond>)`
        if toks[0].text == "while" and len(toks) > 2 and toks[1].text == "(":
            cond_toks, _ = _extract_paren_group(toks, 1)
            cond_ir = _parse_c_js_expr_tokens(cond_toks)
            if cond_ir is not None:
                loop_var = None
                if cond_ir.get("op") == "BinOp" and cond_ir["left"].get("op") == "Var":
                    loop_var = cond_ir["left"]["name"]
                elif cond_ir.get("op") == "BinOp" and cond_ir["right"].get("op") == "Var":
                    loop_var = cond_ir["right"]["name"]
                spans.append(LiftedSpan(
                    ir=canonicalize_ir({"op": "Loop", "var": loop_var, "init": None, "cond": cond_ir, "step": None, "body": []}),
                    start_line=ln_idx, end_line=ln_idx, indent=ind, kind="loop_while", raw_lines=raw_line, lang=lang,
                ))
            continue

        # 4. `return <expr>;`
        if toks[0].text == "return":
            expr_toks = [t for t in toks[1:] if t.text != ";"]
            val_ir = _parse_c_js_expr_tokens(expr_toks) if expr_toks else None
            spans.append(LiftedSpan(
                ir=canonicalize_ir({"op": "Return", "value": val_ir}),
                start_line=ln_idx, end_line=ln_idx, indent=ind, kind="return", raw_lines=raw_line, lang=lang,
            ))
            continue

    return spans


def lift_to_ir(source: str, lang: str) -> list[LiftedSpan]:
    lg = lang.lower()
    if lg in ("py", "python"):
        return _lift_python(source)
    return _lift_c_or_js(source, "js" if lg in ("js", "ts", "javascript", "typescript") else "c")


# ---------------------------------------------------------------------------
# 4. Native 3-Language Lowering (`lower_ir_to_lang`: IR -> Python / JS / C)
# ---------------------------------------------------------------------------

def lower_ir_expr(node: dict[str, Any], lang: str) -> str:
    """Lower a canonical semantic IR expression natively into `python`, `js`, or `c`."""
    lg = "python" if lang.lower() in ("py", "python") else ("js" if lang.lower() in ("js", "ts", "javascript", "typescript") else "c")
    op = node.get("op")

    if op == "Var":
        return str(node["name"])
    if op == "Lit":
        kind = node.get("kind")
        val = node.get("value")
        if kind == "null":
            return {"python": "None", "js": "null", "c": "NULL"}[lg]
        if kind == "bool":
            if lg == "python":
                return "True" if val else "False"
            return "true" if val else "false"
        if kind == "max_int":
            return {"python": "sys.maxsize", "js": "Number.MAX_SAFE_INTEGER", "c": "INT_MAX"}[lg]
        if kind in ("int", "float"):
            return str(val)
        if kind == "char":
            s = str(val)
            esc = s.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t").replace("'", "\\'")
            return f"'{esc}'"
        if kind == "str":
            return repr(str(val)) if lg == "python" else json.dumps(str(val))
        return str(val)

    if op == "Len":
        t = lower_ir_expr(node["target"], lg)
        if lg == "python":
            return f"len({t})"
        if lg == "js":
            return f"{t}.length"
        return f"strlen({t})"

    if op == "Index":
        s = lower_ir_expr(node["seq"], lg)
        ix = lower_ir_expr(node["idx"], lg)
        return f"{s}[{ix}]"

    if op == "Prop":
        o = lower_ir_expr(node["obj"], lg)
        return f"{o}.{node['attr']}"

    if op == "HasKey":
        o = lower_ir_expr(node["obj"], lg)
        k = lower_ir_expr(node["key"], lg)
        if lg == "python":
            return f"({k} in {o})"
        if lg == "js":
            return f"Object.prototype.hasOwnProperty.call({o}, {k})"
        return f"({o} != NULL)"

    if op == "Call":
        c = str(node["callee"])
        args = ", ".join(lower_ir_expr(a, lg) for a in (node.get("args") or []))
        return f"{c}({args})"

    if op == "UnOp":
        uop = str(node["uop"])
        a = lower_ir_expr(node["arg"], lg)
        if uop == "!":
            return f"(not ({a}))" if lg == "python" else f"!({a})"
        if uop == "is_null":
            return {"python": f"({a} is None)", "js": f"({a} == null)", "c": f"({a} == NULL)"}[lg]
        if uop == "not_null":
            return {"python": f"({a} is not None)", "js": f"({a} != null)", "c": f"({a} != NULL)"}[lg]
        if uop == "is_empty":
            return {"python": f"(len({a}) == 0)", "js": f"({a}.length === 0)", "c": f"(strlen({a}) == 0)"}[lg]
        if uop == "not_empty":
            return {"python": f"(len({a}) > 0)", "js": f"({a}.length > 0)", "c": f"(strlen({a}) > 0)"}[lg]
        if uop == "isfinite":
            return {"python": f"math.isfinite({a})", "js": f"Number.isFinite({a})", "c": f"isfinite({a})"}[lg]
        if uop == "isnan":
            return {"python": f"math.isnan({a})", "js": f"Number.isNaN({a})", "c": f"isnan({a})"}[lg]
        return f"({uop}{a})"

    if op == "BinOp":
        bop = str(node["bop"])
        l = lower_ir_expr(node["left"], lg)
        r = lower_ir_expr(node["right"], lg)
        if bop == "&&":
            return f"({l} and {r})" if lg == "python" else f"({l} && {r})"
        if bop == "||":
            return f"({l} or {r})" if lg == "python" else f"({l} || {r})"
        if bop == "==":
            eq = "===" if lg == "js" else "=="
            return f"({l} {eq} {r})"
        if bop == "!=":
            neq = "!==" if lg == "js" else "!="
            return f"({l} {neq} {r})"
        return f"({l} {bop} {r})"

    return ""


# ---------------------------------------------------------------------------
# 5. Cross-Language Single-Experience Semantic Skill Induction & Transfer
# ---------------------------------------------------------------------------

def _abstract_ir_vars(node: Any, vmap: dict[str, str]) -> Any:
    """Alpha-canonicalize all variable names inside an IR node to `$V0`, `$V1`, ..."""
    if isinstance(node, list):
        return [_abstract_ir_vars(x, vmap) for x in node]
    if not isinstance(node, dict):
        return node
    out = dict(node)
    if out.get("op") == "Var":
        nm = str(out["name"])
        if nm not in vmap:
            vmap[nm] = f"$V{len(vmap)}"
        out["name"] = vmap[nm]
        return out
    if out.get("op") == "Loop" and out.get("var"):
        nm = str(out["var"])
        if nm not in vmap:
            vmap[nm] = f"$V{len(vmap)}"
        out["var"] = vmap[nm]
    for k, v in list(out.items()):
        if isinstance(v, (dict, list)):
            out[k] = _abstract_ir_vars(v, vmap)
    return out


def _collect_ir_holes(node: Any, acc: set[str]) -> None:
    if isinstance(node, list):
        for x in node:
            _collect_ir_holes(x, acc)
    elif isinstance(node, dict):
        if node.get("op") == "Var" and str(node.get("name", "")).startswith("$V"):
            acc.add(str(node["name"]))
        for v in node.values():
            if isinstance(v, (dict, list)):
                _collect_ir_holes(v, acc)


def _unify_ir(pattern: Any, target: Any, bindings: dict[str, dict[str, Any]]) -> bool:
    """Unify an alpha-abstracted semantic IR pattern against a concrete target IR node.

    Because BOTH pattern and target are E-Graph canonicalized, commutative operands and
    cross-language equivalents (`strlen(s)` == `s.length` == `len(s)`, `s[-1]` == `s[len(s)-1]`,
    `for` == `while`) unify directly!
    """
    if isinstance(pattern, list):
        if not isinstance(target, list) or len(pattern) != len(target):
            return False
        return all(_unify_ir(p, t, bindings) for p, t in zip(pattern, target))
    if not isinstance(pattern, dict):
        return pattern == target
    if not isinstance(target, dict):
        return False

    pop = pattern.get("op")
    if pop == "Var" and str(pattern.get("name", "")).startswith("$V"):
        h = str(pattern["name"])
        if h in bindings:
            return _ir_key(bindings[h]) == _ir_key(target)
        # Bind semantic hole to any variable or pure expression
        if target.get("op") in ("Var", "Prop", "Index"):
            bindings[h] = target
            return True
        return False

    if pop != target.get("op"):
        return False

    if pop == "Lit":
        return pattern.get("kind") == target.get("kind") and pattern.get("value") == target.get("value")
    if pop == "Var":
        return pattern.get("name") == target.get("name")
    if pop == "Len":
        return _unify_ir(pattern["target"], target["target"], bindings)
    if pop == "Index":
        return _unify_ir(pattern["seq"], target["seq"], bindings) and _unify_ir(pattern["idx"], target["idx"], bindings)
    if pop == "Prop":
        return pattern.get("attr") == target.get("attr") and _unify_ir(pattern["obj"], target["obj"], bindings)
    if pop == "HasKey":
        return _unify_ir(pattern["obj"], target["obj"], bindings) and _unify_ir(pattern["key"], target["key"], bindings)
    if pop == "Call":
        return pattern.get("callee") == target.get("callee") and _unify_ir(pattern.get("args", []), target.get("args", []), bindings)
    if pop == "UnOp":
        return pattern.get("uop") == target.get("uop") and _unify_ir(pattern["arg"], target["arg"], bindings)
    if pop == "BinOp":
        if pattern.get("bop") != target.get("bop"):
            return False
        # Try direct order; for commutative ops also try swapped order in case hole sorting differed!
        snap = dict(bindings)
        if _unify_ir(pattern["left"], target["left"], bindings) and _unify_ir(pattern["right"], target["right"], bindings):
            return True
        if pattern.get("bop") in _COMMUTATIVE_OPS:
            bindings.clear()
            bindings.update(snap)
            if _unify_ir(pattern["left"], target["right"], bindings) and _unify_ir(pattern["right"], target["left"], bindings):
                return True
        bindings.clear()
        bindings.update(snap)
        return False
    if pop == "IfGuard":
        return _unify_ir(pattern["cond"], target["cond"], bindings)
    if pop == "Loop":
        # Match semantically equivalent loops regardless of `for` vs `while` spelling!
        return _unify_ir(pattern.get("cond"), target.get("cond"), bindings)
    if pop == "Return":
        return _unify_ir(pattern.get("value"), target.get("value"), bindings)
    return False


def _instantiate_ir(template: Any, bindings: Mapping[str, dict[str, Any]]) -> Any:
    if isinstance(template, list):
        return [_instantiate_ir(x, bindings) for x in template]
    if not isinstance(template, dict):
        return template
    if template.get("op") == "Var" and str(template.get("name", "")).startswith("$V"):
        h = str(template["name"])
        return bindings.get(h, template)
    out = dict(template)
    for k, v in list(out.items()):
        if isinstance(v, (dict, list)):
            out[k] = _instantiate_ir(v, bindings)
    return out


def new_semantic_skill_store() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "parameters_stored": 0,
        "external_model_dependency": False,
        "skills": {},
    }


def save_semantic_skill_store(store: Mapping[str, Any], path: str | pathlib.Path) -> None:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(store, indent=2, sort_keys=True), encoding="utf-8")


def load_semantic_skill_store(path: str | pathlib.Path) -> dict[str, Any]:
    p = pathlib.Path(path)
    if not p.is_file():
        return new_semantic_skill_store()
    data = json.loads(p.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else new_semantic_skill_store()


def delete_semantic_skill(store: dict[str, Any], skill_id: str) -> bool:
    skills = store.get("skills")
    if isinstance(skills, dict) and skill_id in skills:
        del skills[skill_id]
        return True
    return False


def induce_semantic_skill(
    before_source: str,
    after_source: str,
    *,
    source_lang: str,
    description: str = "",
) -> dict[str, Any]:
    """Induce a language-agnostic semantic IR rewrite skill from ONE verified before/after fix.

    Zero concrete variable names, zero workspace paths, zero language syntax tokens stored.
    """
    b_spans = lift_to_ir(before_source, source_lang)
    a_spans = lift_to_ir(after_source, source_lang)
    if not b_spans or not a_spans:
        return {"admitted": False, "reason": "NO_LIFTABLE_IR_SPANS"}

    b_keys = {_ir_key(s.ir) for s in b_spans}
    a_keys = {_ir_key(s.ir) for s in a_spans}
    removed = [s for s in b_spans if _ir_key(s.ir) not in a_keys]
    added = [s for s in a_spans if _ir_key(s.ir) not in b_keys]
    if not added:
        return {"admitted": False, "reason": "NO_SEMANTIC_IR_DIFF"}

    # Pair the primary changed statement (same IR op: IfGuard->IfGuard, Loop->Loop, Return->Return,
    # OR guard-prefix insertion before Return: Return -> PreGuard + Return)
    pair_before: LiftedSpan | None = None
    pair_after: LiftedSpan | None = None
    rule_mode = "replace_stmt"
    pre_guard_ir: dict[str, Any] | None = None

    for rs in removed:
        for as_ in added:
            if rs.ir.get("op") == as_.ir.get("op"):
                pair_before, pair_after = rs, as_
                break
        if pair_before is not None:
            break

    # Also detect `return expr` -> `if guard: return fallback; return expr` (e.g. CWE-190 / div-by-zero!)
    if pair_before is None:
        added_ifs = [s for s in added if s.ir.get("op") == "IfGuard"]
        added_rets = [s for s in added if s.ir.get("op") == "Return"]
        b_rets = [s for s in b_spans if s.ir.get("op") == "Return"]
        if added_ifs and b_rets:
            rule_mode = "prepend_guard_before_return"
            pair_before = b_rets[0]
            pre_guard_ir = added_ifs[0].ir["cond"]
            pair_after = added_rets[0] if added_rets else LiftedSpan(
                ir={"op": "Return", "value": _ir_lit(0, "int")},
                start_line=1, end_line=1, indent="", kind="return", raw_lines="", lang=source_lang,
            )

    if pair_before is None or pair_after is None:
        return {"admitted": False, "reason": "NO_MATCHING_IR_PAIR"}

    vmap: dict[str, str] = {}
    pat_before = _abstract_ir_vars(pair_before.ir, vmap)
    if rule_mode == "replace_stmt":
        pat_after = _abstract_ir_vars(pair_after.ir, vmap)
        before_holes: set[str] = set()
        after_holes: set[str] = set()
        _collect_ir_holes(pat_before, before_holes)
        _collect_ir_holes(pat_after, after_holes)
        unbound = after_holes - before_holes
        if unbound:
            return {"admitted": False, "reason": f"UNBOUND_SEMANTIC_HOLES:{sorted(unbound)}"}
        tpl_payload = {"mode": rule_mode, "before": pat_before, "after": pat_after}
    else:
        assert pre_guard_ir is not None
        g_abs = _abstract_ir_vars(pre_guard_ir, vmap)
        r_abs = _abstract_ir_vars(pair_after.ir, vmap)
        before_holes = set()
        after_holes = set()
        _collect_ir_holes(pat_before, before_holes)
        _collect_ir_holes(g_abs, after_holes)
        _collect_ir_holes(r_abs, after_holes)
        unbound = after_holes - before_holes
        if unbound:
            return {"admitted": False, "reason": f"UNBOUND_SEMANTIC_HOLES:{sorted(unbound)}"}
        tpl_payload = {"mode": rule_mode, "before": pat_before, "guard": g_abs, "fallback_return": r_abs}

    sig = json.dumps(tpl_payload, sort_keys=True, separators=(",", ":"))
    skill_id = "sem_" + hashlib.sha256(sig.encode("utf-8")).hexdigest()[:12]
    skill = {
        "skill_id": skill_id,
        "source_lang": source_lang,
        "description": description or f"semantic_{rule_mode}_{pair_before.ir.get('op')}",
        "status": "ACTIVE",
        "parameters_stored": 0,
        "verified_count": 1,
        **tpl_payload,
    }
    return {"admitted": True, "skill_id": skill_id, "skill": skill}


def admit_semantic_skill(
    store: dict[str, Any],
    before_source: str,
    after_source: str,
    *,
    source_lang: str,
    description: str = "",
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    res = induce_semantic_skill(before_source, after_source, source_lang=source_lang, description=description)
    if not res.get("admitted"):
        return res
    if provenance:
        res["skill"]["provenance"] = dict(provenance)
    skills = store.setdefault("skills", {})
    sid = res["skill_id"]
    if sid in skills:
        skills[sid]["verified_count"] = int(skills[sid].get("verified_count", 1)) + 1
    else:
        skills[sid] = res["skill"]
    return res


def _lower_patched_span(span: LiftedSpan, skill: Mapping[str, Any], bindings: Mapping[str, dict[str, Any]]) -> str | None:
    """Lower an instantiated semantic IR transformation back into `span.lang` preserving syntax & indentation."""
    lg = "python" if span.lang.lower() in ("py", "python") else ("js" if span.lang.lower() in ("js", "ts") else "c")
    mode = str(skill.get("mode") or "replace_stmt")
    ind = span.indent
    raw = span.raw_lines

    if mode == "replace_stmt":
        inst = _instantiate_ir(skill["after"], bindings)
        op = inst.get("op")
        if op == "IfGuard":
            new_cond = lower_ir_expr(inst["cond"], lg)
            if lg == "python":
                return f"{ind}if {new_cond}:\n"
            # Preserve trailing `{` or inline body after `if (...)`
            m_tail = re.match(r"^[ \t]*if\s*\(.*\)(.*)$", raw.rstrip("\r\n"))
            tail = m_tail.group(1) if m_tail else ""
            # Safer balanced paren skip on raw
            p0 = raw.find("(")
            if p0 != -1:
                depth = 0
                end_p = p0
                for ci in range(p0, len(raw)):
                    if raw[ci] == "(":
                        depth += 1
                    elif raw[ci] == ")":
                        depth -= 1
                        if depth == 0:
                            end_p = ci
                            break
                tail = raw[end_p + 1 :].rstrip("\r\n")
            return f"{ind}if ({new_cond}){tail}\n"

        if op == "Loop":
            new_cond = lower_ir_expr(inst["cond"], lg)
            if span.kind == "loop_while":
                if lg == "python":
                    return f"{ind}while {new_cond}:\n"
                p0 = raw.find("(")
                tail = ""
                if p0 != -1:
                    depth = 0
                    for ci in range(p0, len(raw)):
                        if raw[ci] == "(":
                            depth += 1
                        elif raw[ci] == ")":
                            depth -= 1
                            if depth == 0:
                                tail = raw[ci + 1 :].rstrip("\r\n")
                                break
                return f"{ind}while ({new_cond}){tail}\n"
            if span.kind == "loop_for":
                if lg == "python":
                    # `for i in range(n)` -> adjust range bound if cond changed `<` vs `<=`
                    if inst["cond"].get("op") == "BinOp" and inst["cond"].get("bop") == "<":
                        lim = lower_ir_expr(inst["cond"]["right"], lg)
                        vnm = str(inst.get("var") or lower_ir_expr(inst["cond"]["left"], lg))
                        return f"{ind}for {vnm} in range({lim}):\n"
                    return None
                # C/JS `for (init; OLD_COND; step)` -> replace ONLY middle semicolon segment!
                p0 = raw.find("(")
                if p0 != -1:
                    depth = 0
                    end_p = len(raw) - 1
                    for ci in range(p0, len(raw)):
                        if raw[ci] == "(":
                            depth += 1
                        elif raw[ci] == ")":
                            depth -= 1
                            if depth == 0:
                                end_p = ci
                                break
                    inner = raw[p0 + 1 : end_p]
                    segs = inner.split(";")
                    if len(segs) == 3:
                        tail = raw[end_p + 1 :].rstrip("\r\n")
                        return f"{ind}for ({segs[0]}; {new_cond};{segs[2]}){tail}\n"

        if op == "Return":
            new_val = lower_ir_expr(inst["value"], lg) if inst.get("value") is not None else ""
            if lg == "python":
                return f"{ind}return {new_val}\n" if new_val else f"{ind}return\n"
            return f"{ind}return {new_val};\n" if new_val else f"{ind}return;\n"

    elif mode == "prepend_guard_before_return":
        g_ir = _instantiate_ir(skill["guard"], bindings)
        r_ir = _instantiate_ir(skill["fallback_return"], bindings)
        g_code = lower_ir_expr(g_ir, lg)
        r_val = lower_ir_expr(r_ir["value"], lg) if r_ir.get("value") is not None else ""
        if lg == "python":
            return f"{ind}if {g_code}:\n{ind}    return {r_val}\n{raw}"
        return f"{ind}if ({g_code}) return {r_val};\n{raw}"

    return None


def recall_semantic_candidates(
    store: Mapping[str, Any],
    target_source: str,
    *,
    target_lang: str,
    target_lines: Sequence[int] | None = None,
    max_candidates: int = 8,
) -> list[dict[str, Any]]:
    """Recall cross-language semantic IR skills and lower them natively into `target_lang`."""
    skills = store.get("skills")
    if not isinstance(skills, Mapping) or not skills:
        return []
    spans = lift_to_ir(target_source, target_lang)
    if not spans:
        return []
    lines = target_source.splitlines(keepends=True)
    target_set = set(target_lines or ())
    out: list[dict[str, Any]] = []
    seen_patched: set[str] = set()

    for sid, sk in skills.items():
        if not isinstance(sk, Mapping) or sk.get("status") != "ACTIVE":
            continue
        pat_before = sk.get("before")
        if not isinstance(pat_before, Mapping):
            continue
        matched_spans: list[tuple[int, LiftedSpan, dict[str, dict[str, Any]]]] = []
        for sp in spans:
            binds: dict[str, dict[str, Any]] = {}
            if _unify_ir(pat_before, sp.ir, binds):
                prio = 0 if (not target_set or sp.start_line in target_set) else 1
                matched_spans.append((prio, sp, binds))
        matched_spans.sort(key=lambda x: (x[0], x[1].start_line))
        for _prio, sp, binds in matched_spans:
            repl = _lower_patched_span(sp, sk, binds)
            if not repl:
                continue
            nl = list(lines)
            nl[sp.start_line - 1 : sp.end_line] = [repl]
            patched = "".join(nl)
            if patched == target_source or patched in seen_patched:
                continue
            # Fail-closed syntax validation for Python
            if target_lang.lower() in ("py", "python"):
                try:
                    ast.parse(patched)
                except SyntaxError:
                    continue
            seen_patched.add(patched)
            out.append({
                "skill_id": str(sid),
                "source_lang": str(sk.get("source_lang") or ""),
                "target_lang": target_lang,
                "lineno": sp.start_line,
                "patched_source": patched,
                "description": str(sk.get("description") or sid),
            })
            if len(out) >= max_candidates:
                return out
    return out


# ---------------------------------------------------------------------------
# 6. Leap 1: Inter-Procedural Cross-File Data-Flow & Causal Slicing Graph
# ---------------------------------------------------------------------------

@dataclass
class DataFlowNode:
    file: str
    func: str
    lineno: int
    defs: frozenset[str]
    uses: frozenset[str]
    calls: tuple[tuple[str, tuple[str, ...]], ...]  # (callee_name, arg_var_names)
    is_return: bool = False


@dataclass
class CrossFileDataFlowGraph:
    nodes: dict[tuple[str, int], DataFlowNode] = field(default_factory=dict)
    funcs: dict[str, list[tuple[str, int, tuple[str, ...], list[int]]]] = field(default_factory=dict)
    # funcs[func_name] = [(rel_file, def_line, param_names, return_lines)]
    intra_rev: dict[tuple[str, int], set[tuple[str, int]]] = field(default_factory=dict)
    inter_rev: dict[tuple[str, int], set[tuple[str, int]]] = field(default_factory=dict)


def build_cross_file_dataflow_graph(repo_root: pathlib.Path, rel_files: Sequence[str] | None = None) -> CrossFileDataFlowGraph:
    """Build a statement-level intra- + inter-procedural data-flow graph across Python repo files.

    Captures:
      - Statement-level `defs` and `uses` within every function (def-use backward edges)
      - Cross-file call edges: `call(callee, arg_vars)` -> `callee`'s `return` statements AND
        `callee`'s parameter uses -> caller's call-site argument definitions!
    """
    graph = CrossFileDataFlowGraph()
    root = pathlib.Path(repo_root)
    if rel_files is None:
        files = [
            str(p.relative_to(root)).replace("\\", "/")
            for p in sorted(root.rglob("*.py"))
            if not any(part.startswith(".") or part in ("__pycache__", "tests", "test", "venv", ".venv") for part in p.parts)
        ][:80]
    else:
        files = list(rel_files)[:80]

    for rel in files:
        p = root / rel
        if not p.is_file():
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue

        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            params = tuple(
                a.arg for a in (
                    list(getattr(fn.args, "posonlyargs", []))
                    + list(fn.args.args)
                    + list(fn.args.kwonlyargs)
                )
            )
            ret_lines: list[int] = []
            # Last definition line per variable within `fn`
            last_def: dict[str, list[int]] = {pm: [int(fn.lineno)] for pm in params}
            graph.nodes[(rel, int(fn.lineno))] = DataFlowNode(
                file=rel, func=fn.name, lineno=int(fn.lineno),
                defs=frozenset(params), uses=frozenset(), calls=(), is_return=False,
            )

            for st in ast.walk(fn):
                if not isinstance(st, ast.stmt) or st is fn:
                    continue
                ln = int(getattr(st, "lineno", fn.lineno))
                defs: set[str] = set()
                uses: set[str] = set()
                calls: list[tuple[str, tuple[str, ...]]] = []
                for sub in ast.walk(st):
                    if isinstance(sub, ast.Name):
                        if isinstance(sub.ctx, ast.Store):
                            defs.add(sub.id)
                        elif isinstance(sub.ctx, ast.Load):
                            uses.add(sub.id)
                    elif isinstance(sub, ast.Call):
                        cname = None
                        if isinstance(sub.func, ast.Name):
                            cname = sub.func.id
                        elif isinstance(sub.func, ast.Attribute):
                            cname = sub.func.attr
                        if cname:
                            avars = tuple(
                                sorted({n.id for a in sub.args for n in ast.walk(a) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)})
                            )
                            calls.append((cname, avars))
                is_ret = isinstance(st, ast.Return)
                if is_ret:
                    ret_lines.append(ln)
                key = (rel, ln)
                if key not in graph.nodes:
                    graph.nodes[key] = DataFlowNode(
                        file=rel, func=fn.name, lineno=ln,
                        defs=frozenset(defs), uses=frozenset(uses), calls=tuple(calls), is_return=is_ret,
                    )
                else:
                    old = graph.nodes[key]
                    graph.nodes[key] = DataFlowNode(
                        file=rel, func=fn.name, lineno=ln,
                        defs=old.defs | frozenset(defs),
                        uses=old.uses | frozenset(uses),
                        calls=old.calls + tuple(calls),
                        is_return=old.is_return or is_ret,
                    )
                for u in uses:
                    for dl in last_def.get(u, ()):
                        if dl != ln:
                            graph.intra_rev.setdefault(key, set()).add((rel, dl))
                for d in defs:
                    last_def.setdefault(d, []).append(ln)

            graph.funcs.setdefault(fn.name, []).append((rel, int(fn.lineno), params, ret_lines))

    # Wire Inter-Procedural Edges: call-site `(caller_file, call_ln)` <- callee `return` lines (and callee entry!)
    for key, node in graph.nodes.items():
        for cname, _avars in node.calls:
            for c_rel, c_def_ln, _c_params, c_rets in graph.funcs.get(cname, ()):
                if c_rel == node.file and c_def_ln == node.lineno:
                    continue
                for rln in c_rets[:4]:
                    graph.inter_rev.setdefault(key, set()).add((c_rel, rln))
                graph.inter_rev.setdefault(key, set()).add((c_rel, c_def_ln))

    return graph


def backward_causal_slice(
    graph: CrossFileDataFlowGraph,
    seeds: Sequence[tuple[str, int]],
    *,
    max_hops: int = 4,
    max_nodes: int = 40,
) -> list[dict[str, Any]]:
    """Compute minimal backward inter-procedural causal data-flow slice from failing seed lines.

    Follows BOTH intra-procedural def-use edges AND inter-procedural caller<-callee return edges
    across multiple files, returning upstream producer statements ranked by causal hop distance.
    """
    visited: dict[tuple[str, int], int] = {}
    frontier: list[tuple[tuple[str, int], int]] = []
    for s in seeds:
        if s in graph.nodes and s not in visited:
            visited[s] = 0
            frontier.append((s, 0))

    idx = 0
    while idx < len(frontier) and len(visited) < max_nodes:
        cur, hop = frontier[idx]
        idx += 1
        if hop >= max_hops:
            continue
        # Walk intra-procedural def-use backwards (same hop cost) and inter-procedural callee returns (+1 hop)
        for nxt in sorted(graph.intra_rev.get(cur, ())):
            if nxt not in visited:
                visited[nxt] = hop + 1
                frontier.append((nxt, hop + 1))
        for nxt in sorted(graph.inter_rev.get(cur, ())):
            if nxt not in visited:
                visited[nxt] = hop + 1
                frontier.append((nxt, hop + 1))

    out: list[dict[str, Any]] = []
    for (rel, ln), hop in sorted(visited.items(), key=lambda kv: (kv[1], kv[0][0], kv[0][1])):
        nd = graph.nodes.get((rel, ln))
        if nd is None:
            continue
        out.append({
            "file": rel,
            "func": nd.func,
            "lineno": ln,
            "hop": hop,
            "defs": sorted(nd.defs),
            "uses": sorted(nd.uses),
            "is_return": nd.is_return,
        })
    return out
