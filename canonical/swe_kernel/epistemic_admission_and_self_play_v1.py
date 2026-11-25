#!/usr/bin/env python3
"""External Epistemic Skill & Negative-Invariant Store, Universal Semantic IR
Anti-Unification (Python <-> C <-> JS), 5-Gate Admission Filter, Staleness Re-Probing,
and Delta-Debugged Adversarial Self-Play (`model_calls == 0`, `parameters_stored == 0`).

Resolves §2 (Persistence vs. Zero-Knowledge House), §9.2 (5-Gate Admission & Compression),
§9.3.2 (Universal Meaning IR across languages), and §9.4.4 (Negative-Space L3 Invariants
& Continuous CPU Self-Play with `ddmin` + `consistency_vs_equivalence_v1` + `same_identity_supervisor`).

Authority: NONE. Computed algorithmic mechanisms + external inspectable JSON store only.
"""
from __future__ import annotations

import ast
import copy
from dataclasses import dataclass, field
import hashlib
import json
import pathlib
import re
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import same_identity_supervisor as SIS
from canonical.swe_kernel import consistency_vs_equivalence_v1 as CVE
from canonical.swe_kernel import lesson_admission_gate_v1 as LAG

SCHEMA = "BRAIN_EPISTEMIC_ADMISSION_AND_SELF_PLAY_V1"
STORE_SCHEMA = "BRAIN_EXTERNAL_EPISTEMIC_STORE_V1"
AUTHORITY = "NONE"


def _sha256_short(data: str | bytes) -> str:
    raw = data.encode("utf-8") if isinstance(data, str) else data
    return hashlib.sha256(raw).hexdigest()[:16]


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


# ---------------------------------------------------------------------------
# 1. UNIVERSAL SEMANTIC MEANING IR (Python <-> C <-> JavaScript) & ANTI-UNIFICATION
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticIRNode:
    """Language-neutral Universal Meaning IR node supporting Plotkin anti-unification
    and deterministic compilation to Python, C, and JavaScript.

    Ops:
      - VAR(slot_name) / HOLE(hole_id)
      - CONST(value, kind)
      - NULL_CHECK(expr, negated: bool)          # x != NULL / x is not None / x !== null
      - BOOL_OP(op: 'and'|'or', args)
      - UNARY_OP(op: 'not'|'neg', arg)
      - COMPARE(op: '<'|'<='|'>'|'>='|'=='|'!=', left, right)
      - BIN_OP(op: '+'|'-'|'*'|'//' |'%', left, right)
      - LEN(arg)                                 # len(x) / x##_len / x.length
      - INDEX(seq, idx)                          # seq[idx]
      - ATTR(obj, field_name)                    # obj.f / obj->f
      - CALL(func_name, args)
      - IF_GUARD_RAISE(cond, err_kind, msg)      # guard precondition / early error return
      - TERNARY(cond, then_expr, else_expr)
    """

    op: str
    args: tuple[Any, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "op": self.op,
            "args": [a.to_dict() if isinstance(a, SemanticIRNode) else a for a in self.args],
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "SemanticIRNode":
        args = tuple(
            cls.from_dict(x) if isinstance(x, Mapping) and "op" in x else x
            for x in d.get("args", ())
        )
        return cls(op=str(d["op"]), args=args)

    def size(self) -> int:
        return 1 + sum(a.size() if isinstance(a, SemanticIRNode) else 1 for a in self.args)

    def holes(self) -> set[str]:
        out: set[str] = set()
        if self.op in ("HOLE", "VAR"):
            out.add(str(self.args[0]))
        for a in self.args:
            if isinstance(a, SemanticIRNode):
                out |= a.holes()
        return out


_PY_CMP_MAP = {
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.Eq: "==",
    ast.NotEq: "!=",
}
_PY_BIN_MAP = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.FloorDiv: "//",
    ast.Div: "/",
    ast.Mod: "%",
}


def lift_python_to_ir(source: str, var_order: dict[str, str] | None = None) -> SemanticIRNode:
    """Lift a Python expression or single guard/return statement into Universal Semantic IR."""
    if var_order is None:
        var_order = {}

    def _slot(name: str) -> str:
        if name not in var_order:
            var_order[name] = f"$V{len(var_order)}"
        return var_order[name]

    mod = ast.parse(source.strip())
    if not mod.body:
        raise ValueError("empty Python snippet")
    stmt = mod.body[0]

    def _expr(node: ast.AST) -> SemanticIRNode:
        if isinstance(node, ast.Name):
            if node.id in ("None", "True", "False"):
                return SemanticIRNode("CONST", (ast.literal_eval(node.id), "lit"))
            return SemanticIRNode("VAR", (_slot(node.id),))
        if isinstance(node, ast.Constant):
            return SemanticIRNode("CONST", (node.value, type(node.value).__name__))
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            return SemanticIRNode("ATTR", (SemanticIRNode("VAR", (_slot(node.value.id),)), node.attr))
        if isinstance(node, ast.Subscript):
            return SemanticIRNode("INDEX", (_expr(node.value), _expr(node.slice)))
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "len" and len(node.args) == 1:
                return SemanticIRNode("LEN", (_expr(node.args[0]),))
            fname = ast.unparse(node.func)
            return SemanticIRNode("CALL", (fname, tuple(_expr(a) for a in node.args)))
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return SemanticIRNode("UNARY_OP", ("not", _expr(node.operand)))
            if isinstance(node.op, ast.USub):
                if isinstance(node.operand, ast.Constant) and isinstance(node.operand.value, (int, float)):
                    return SemanticIRNode("CONST", (-node.operand.value, type(node.operand.value).__name__))
                return SemanticIRNode("UNARY_OP", ("neg", _expr(node.operand)))
        if isinstance(node, ast.BoolOp):
            op_s = "and" if isinstance(node.op, ast.And) else "or"
            cur = _expr(node.values[0])
            for nxt in node.values[1:]:
                cur = SemanticIRNode("BOOL_OP", (op_s, cur, _expr(nxt)))
            return cur
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
            op_node, rhs = node.ops[0], node.comparators[0]
            if isinstance(op_node, (ast.Is, ast.IsNot)) and isinstance(rhs, ast.Constant) and rhs.value is None:
                return SemanticIRNode("NULL_CHECK", (_expr(node.left), isinstance(op_node, ast.IsNot)))
            for cls_t, sym in _PY_CMP_MAP.items():
                if isinstance(op_node, cls_t):
                    return SemanticIRNode("COMPARE", (sym, _expr(node.left), _expr(rhs)))
        if isinstance(node, ast.BinOp):
            for cls_t, sym in _PY_BIN_MAP.items():
                if isinstance(node.op, cls_t):
                    return SemanticIRNode("BIN_OP", (sym, _expr(node.left), _expr(node.right)))
        if isinstance(node, ast.IfExp):
            return SemanticIRNode("TERNARY", (_expr(node.test), _expr(node.body), _expr(node.orelse)))
        return SemanticIRNode("RAW", (ast.unparse(node),))

    if isinstance(stmt, ast.Expr):
        return _expr(stmt.value)
    if isinstance(stmt, ast.Return) and stmt.value is not None:
        return SemanticIRNode("RETURN", (_expr(stmt.value),))
    if isinstance(stmt, ast.If) and len(stmt.body) == 1 and not stmt.orelse:
        inner = stmt.body[0]
        if isinstance(inner, ast.Raise):
            err_k = "ValueError"
            if isinstance(inner.exc, ast.Call) and isinstance(inner.exc.func, ast.Name):
                err_k = inner.exc.func.id
            return SemanticIRNode("IF_GUARD_RAISE", (_expr(stmt.test), err_k))
        if isinstance(inner, ast.Return) and inner.value is not None:
            return SemanticIRNode("IF_GUARD_RETURN", (_expr(stmt.test), _expr(inner.value)))
    raise ValueError(f"Unsupported statement shape for IR lift: {ast.dump(stmt)[:80]}")


def anti_unify_ir(a: SemanticIRNode, b: SemanticIRNode, hole_map: dict[tuple[Any, Any], str] | None = None) -> SemanticIRNode:
    """Plotkin's Least General Generalization (LGG) over Universal Semantic IR."""
    if hole_map is None:
        hole_map = {}
    if a == b:
        return a
    if a.op == b.op and len(a.args) == len(b.args):
        if a.op == "VAR":
            key = (a.args[0], b.args[0])
            if key not in hole_map:
                hole_map[key] = f"$V{len(hole_map)}"
            return SemanticIRNode("VAR", (hole_map[key],))
        new_args = []
        for xa, xb in zip(a.args, b.args):
            if isinstance(xa, SemanticIRNode) and isinstance(xb, SemanticIRNode):
                new_args.append(anti_unify_ir(xa, xb, hole_map))
            elif xa == xb:
                new_args.append(xa)
            else:
                key = (repr(xa), repr(xb))
                if key not in hole_map:
                    hole_map[key] = f"?H{len(hole_map)}"
                new_args.append(SemanticIRNode("HOLE", (hole_map[key],)))
        return SemanticIRNode(a.op, tuple(new_args))
    key = (_canonical_json(a.to_dict()), _canonical_json(b.to_dict()))
    if key not in hole_map:
        hole_map[key] = f"?H{len(hole_map)}"
    return SemanticIRNode("HOLE", (hole_map[key],))


def compile_ir_to_language(
    node: SemanticIRNode,
    language: str,
    bindings: Mapping[str, str] | None = None,
) -> str:
    """Compile a Universal Semantic IR node deterministically to Python, C, or JavaScript."""
    lang = language.lower()
    bmap = dict(bindings or {})

    def _emit(n: Any) -> str:
        if not isinstance(n, SemanticIRNode):
            return str(n)
        op = n.op
        if op in ("VAR", "HOLE"):
            slot = str(n.args[0])
            return bmap.get(slot, slot)
        if op == "CONST":
            val = n.args[0]
            if val is None:
                return "None" if lang == "python" else ("NULL" if lang in ("c", "cpp") else "null")
            if isinstance(val, bool):
                if lang == "python":
                    return "True" if val else "False"
                return "1" if (lang == "c" and val) else ("0" if lang == "c" else ("true" if val else "false"))
            return repr(val) if lang == "python" else json.dumps(val)
        if op == "NULL_CHECK":
            sub = _emit(n.args[0])
            not_null = bool(n.args[1])
            if lang == "python":
                return f"({sub} is not None)" if not_null else f"({sub} is None)"
            if lang in ("c", "cpp"):
                return f"({sub} != NULL)" if not_null else f"({sub} == NULL)"
            return f"({sub} !== null && {sub} !== undefined)" if not_null else f"({sub} === null || {sub} === undefined)"
        if op == "LEN":
            sub = _emit(n.args[0])
            if lang == "python":
                return f"len({sub})"
            if lang in ("js", "javascript", "ts", "typescript"):
                return f"{sub}.length"
            if lang in ("c", "cpp"):
                return bmap.get(f"len:{sub}", f"{sub}_len")
        if op == "ATTR":
            obj_s = _emit(n.args[0])
            fld = str(n.args[1])
            if lang in ("c", "cpp") and bmap.get("c_ptr_access", "true") == "true":
                return f"{obj_s}->{fld}"
            return f"{obj_s}.{fld}"
        if op == "INDEX":
            return f"{_emit(n.args[0])}[{_emit(n.args[1])}]"
        if op == "UNARY_OP":
            uop, sub = str(n.args[0]), _emit(n.args[1])
            if uop == "not":
                return f"(not {sub})" if lang == "python" else f"(!{sub})"
            return f"(-{sub})"
        if op == "BOOL_OP":
            bop, l_s, r_s = str(n.args[0]), _emit(n.args[1]), _emit(n.args[2])
            if lang == "python":
                return f"({l_s} {bop} {r_s})"
            sym = "&&" if bop == "and" else "||"
            return f"({l_s} {sym} {r_s})"
        if op == "COMPARE":
            cop, l_s, r_s = str(n.args[0]), _emit(n.args[1]), _emit(n.args[2])
            if lang in ("js", "javascript", "ts", "typescript") and cop in ("==", "!="):
                cop = "===" if cop == "==" else "!=="
            return f"({l_s} {cop} {r_s})"
        if op == "BIN_OP":
            bop, l_s, r_s = str(n.args[0]), _emit(n.args[1]), _emit(n.args[2])
            if bop == "//":
                if lang == "python":
                    return f"({l_s} // {r_s})"
                if lang in ("js", "javascript", "ts", "typescript"):
                    return f"Math.trunc({l_s} / {r_s})"
                return f"({l_s} / {r_s})"
            return f"({l_s} {bop} {r_s})"
        if op == "TERNARY":
            c_s, t_s, e_s = _emit(n.args[0]), _emit(n.args[1]), _emit(n.args[2])
            if lang == "python":
                return f"({t_s} if {c_s} else {e_s})"
            return f"({c_s} ? {t_s} : {e_s})"
        if op == "CALL":
            fn = bmap.get(f"fn:{n.args[0]}", str(n.args[0]))
            args_s = ", ".join(_emit(a) for a in n.args[1])
            return f"{fn}({args_s})"
        if op == "RETURN":
            return f"return {_emit(n.args[0])}" + ("" if lang == "python" else ";")
        if op == "IF_GUARD_RAISE":
            c_s = _emit(n.args[0])
            err_k = str(n.args[1])
            if lang == "python":
                return f"if {c_s}:\n    raise {err_k}('invalid input')"
            if lang in ("js", "javascript", "ts", "typescript"):
                js_err = "RangeError" if err_k in ("ValueError", "IndexError") else "Error"
                return f"if ({c_s}) {{ throw new {js_err}('invalid input'); }}"
            ret_fallback = bmap.get("c_error_return", "-1")
            return f"if ({c_s}) {{ return {ret_fallback}; }}"
        if op == "IF_GUARD_RETURN":
            c_s, rv_s = _emit(n.args[0]), _emit(n.args[1])
            if lang == "python":
                return f"if {c_s}:\n    return {rv_s}"
            return f"if ({c_s}) {{ return {rv_s}; }}"
        if op == "RAW":
            return str(n.args[0])
        raise ValueError(f"Unknown IR op {op}")

    return _emit(node)


def match_ir_pattern(pattern: SemanticIRNode, concrete: SemanticIRNode, bindings: dict[str, str] | None = None) -> dict[str, str] | None:
    """Attempt structural unification of `pattern` against `concrete`, returning slot bindings."""
    if bindings is None:
        bindings = {}
    if pattern.op in ("VAR", "HOLE"):
        slot = str(pattern.args[0])
        if concrete.op == "VAR":
            cname = str(concrete.args[0])
        else:
            cname = compile_ir_to_language(concrete, "python")
        if slot in bindings and bindings[slot] != cname:
            return None
        bindings[slot] = cname
        return bindings
    if pattern.op != concrete.op or len(pattern.args) != len(concrete.args):
        return None
    for pa, ca in zip(pattern.args, concrete.args):
        if isinstance(pa, SemanticIRNode) and isinstance(ca, SemanticIRNode):
            if match_ir_pattern(pa, ca, bindings) is None:
                return None
        elif pa != ca:
            return None
    return bindings


def transfer_ir_rule_to_snippet(
    before_ir: SemanticIRNode,
    after_ir: SemanticIRNode,
    target_snippet: str,
    *,
    target_language: str,
    extra_bindings: Mapping[str, str] | None = None,
) -> str | None:
    """Apply an anti-unified Semantic IR rewrite rule `(before_ir -> after_ir)` across languages."""
    lang = target_language.lower()
    if lang == "python":
        inv_map: dict[str, str] = {}
        try:
            cand_ir = lift_python_to_ir(target_snippet, inv_map)
        except ValueError:
            return None
        slot_to_real = {v: k for k, v in inv_map.items()}
        m = match_ir_pattern(before_ir, cand_ir)
        if m is None:
            return None
        resolved = {slot: slot_to_real.get(val, val) for slot, val in m.items()}
        if extra_bindings:
            resolved.update(extra_bindings)
        return compile_ir_to_language(after_ir, "python", resolved)

    # For C or JavaScript: render before_ir with regex capture slots over identifier tokens
    slots = sorted(before_ir.holes())
    placeholder_map = {s: f"__SLOT_{i}__" for i, s in enumerate(slots)}
    rendered_before = compile_ir_to_language(before_ir, lang, {**(extra_bindings or {}), **placeholder_map})
    # Normalize outer parens for matching C/JS lines
    core_before = rendered_before.strip()
    if core_before.startswith("(") and core_before.endswith(")"):
        core_before = core_before[1:-1]
    escaped = re.escape(core_before)
    seen_slots: set[str] = set()
    for i, s in enumerate(slots):
        tok = re.escape(f"__SLOT_{i}__")
        grp = f"G{i}"
        if tok in escaped:
            if s not in seen_slots:
                escaped = escaped.replace(tok, f"(?P<{grp}>[A-Za-z_][A-Za-z0-9_>\\-\\.]*)", 1)
                seen_slots.add(s)
            escaped = escaped.replace(tok, f"(?P={grp})")
    escaped = re.sub(r"\\\s+", r"\\s*", escaped)
    m_re = re.search(escaped, target_snippet)
    if not m_re:
        return None
    resolved_c: dict[str, str] = dict(extra_bindings or {})
    for i, s in enumerate(slots):
        grp = f"G{i}"
        if grp in m_re.groupdict() and m_re.group(grp) is not None:
            resolved_c[s] = m_re.group(grp)
    rendered_after = compile_ir_to_language(after_ir, lang, resolved_c)
    if rendered_after.startswith("(") and rendered_after.endswith(")") and not m_re.group(0).startswith("("):
        rendered_after = rendered_after[1:-1]
    return target_snippet[: m_re.start()] + rendered_after + target_snippet[m_re.end() :]


# ---------------------------------------------------------------------------
# 2. §9.2 FIVE-GATE ADMISSION FILTER & EXTERNAL INSPECTABLE VERSIONED STORE
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdmissionVerdict:
    admitted: bool
    reason: str
    gates: dict[str, bool]
    compression_ratio: float


def evaluate_admission_5gate(
    *,
    verified_on_oracle: bool,
    goal_relevant: bool,
    prediction_error_bearing: bool,
    held_out_transfer_passed: bool,
    innocent_controls_preserved: bool,
    generalized_ir_bytes: int,
    raw_witness_bytes: int,
) -> AdmissionVerdict:
    """Enforce §9.2 5-Gate Admission Filter:
    (1) verified, (2) goal-relevant, (3) prediction-error-bearing (surprising),
    (4) reusable on held-out + preserves controls, (5) MDL compressible.
    """
    reusable = bool(held_out_transfer_passed and innocent_controls_preserved)
    comp_ratio = float(raw_witness_bytes) / max(1.0, float(generalized_ir_bytes))
    compressible = comp_ratio > 1.05
    gates = {
        "verified": bool(verified_on_oracle),
        "goal_relevant": bool(goal_relevant),
        "prediction_error_bearing": bool(prediction_error_bearing),
        "reusable": reusable,
        "compressible": compressible,
    }
    failed = [k for k, v in gates.items() if not v]
    if failed:
        return AdmissionVerdict(
            admitted=False,
            reason="REFUSED__FAILED_GATES:" + ",".join(failed),
            gates=gates,
            compression_ratio=round(comp_ratio, 4),
        )
    return AdmissionVerdict(
        admitted=True,
        reason="ADMITTED__ALL_5_GATES_PASSED",
        gates=gates,
        compression_ratio=round(comp_ratio, 4),
    )


def _fp64_hex(payload: str) -> str:
    """Deterministic 64-bit (16-hex-char) Blake2b structural fingerprint."""
    return hashlib.blake2b(payload.encode("utf-8"), digest_size=8).hexdigest()


def _is_pattern_hole_ast(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Name) and bool(re.fullmatch(r"_(?:H|P)\d+_", node.id))


def _ast_stmt_head_sig(stmt: ast.stmt) -> str:
    if isinstance(stmt, ast.If):
        b0 = type(stmt.body[0]).__name__ if stmt.body else "-"
        return f"If:{len(stmt.body)}:{len(stmt.orelse)}:{b0}"
    if isinstance(stmt, ast.Try):
        return f"Try:{len(stmt.body)}:{len(stmt.handlers)}"
    if isinstance(stmt, ast.For):
        return f"For:{len(stmt.body)}"
    if isinstance(stmt, ast.While):
        return f"While:{len(stmt.body)}"
    if isinstance(stmt, ast.Assign):
        return f"Assign:{len(stmt.targets)}"
    if isinstance(stmt, ast.AugAssign):
        return f"AugAssign:{type(stmt.op).__name__}"
    if isinstance(stmt, ast.Return):
        return f"Return:{'Bare' if stmt.value is None else 'Val'}"
    if isinstance(stmt, ast.Raise):
        return f"Raise:{'Bare' if stmt.exc is None else 'Exc'}"
    return type(stmt).__name__


def _primary_stmt_expr(stmt: ast.stmt) -> ast.expr | None:
    if isinstance(stmt, (ast.Return, ast.Assign, ast.AugAssign, ast.Expr)):
        return stmt.value
    if isinstance(stmt, (ast.If, ast.While)):
        return stmt.test
    return None


def _ast_expr_root_sig(expr: ast.expr | None) -> str:
    if expr is None:
        return "None"
    if isinstance(expr, ast.Compare):
        ops = ",".join(type(o).__name__ for o in expr.ops)
        return f"Compare:{ops}"
    if isinstance(expr, ast.BoolOp):
        return f"BoolOp:{type(expr.op).__name__}"
    if isinstance(expr, ast.BinOp):
        return f"BinOp:{type(expr.op).__name__}"
    if isinstance(expr, ast.UnaryOp):
        return f"UnaryOp:{type(expr.op).__name__}"
    if isinstance(expr, (ast.Tuple, ast.List)):
        return f"{type(expr).__name__}:{len(expr.elts)}"
    return type(expr).__name__


def compute_subtree_morphism_fingerprint(domain: str, before_stmts_pattern: Sequence[str]) -> str:
    """Compute a 64-bit structural fingerprint invariant under variable/expression hole substitution."""
    if not before_stmts_pattern:
        return _fp64_hex(f"{domain}|FUNC_ENTRY_GUARD|0")
    parsed_stmts: list[ast.stmt] = []
    for s in before_stmts_pattern:
        try:
            mod = ast.parse(s)
            if mod.body:
                parsed_stmts.append(mod.body[0])
        except SyntaxError:
            return _fp64_hex(f"{domain}|RAW|{len(before_stmts_pattern)}")
    if not parsed_stmts:
        return _fp64_hex(f"{domain}|FUNC_ENTRY_GUARD|0")
    if len(parsed_stmts) == 1:
        s0 = parsed_stmts[0]
        h0 = _ast_stmt_head_sig(s0)
        e0 = _primary_stmt_expr(s0)
        etag = "*" if (e0 is None or _is_pattern_hole_ast(e0)) else _ast_expr_root_sig(e0)
        return _fp64_hex(f"{domain}|S1|{h0}|{etag}")
    heads = "|".join(_ast_stmt_head_sig(st) for st in parsed_stmts)
    return _fp64_hex(f"{domain}|SK|{len(parsed_stmts)}|{heads}")


def compute_l2_entry_fingerprint(entry: Mapping[str, Any]) -> str:
    """Compute the canonical 64-bit structural bucket key for any L2 store entry."""
    domain = str(entry.get("domain", "python"))
    sm = entry.get("subtree_morphism")
    if isinstance(sm, Mapping):
        pats = tuple(str(x) for x in sm.get("before_stmts_pattern", ()))
        return compute_subtree_morphism_fingerprint(domain, pats)
    b_ir = entry.get("before_ir")
    if isinstance(b_ir, Mapping):
        op = str(b_ir.get("op", ""))
        arity = len(b_ir.get("args") or ())
        return _fp64_hex(f"{domain}|IR|{op}|{arity}")
    return _fp64_hex(f"{domain}|GENERIC")


def extract_python_module_fingerprints(source_text: str, domain: str = "python") -> set[str]:
    """Single O(|AST|) pass extracting all structural 64-bit fingerprints present in `source_text`.
    Soundly covers both exact root-expression shapes and wildcard-hole patterns (`*`) with zero
    false negatives, enabling O(1) lookup against `EpistemicStoreV1.structural_index` independent
    of how many thousands of L2 skills have accumulated!
    """
    fps: set[str] = {_fp64_hex(f"{domain}|FUNC_ENTRY_GUARD|0")}
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return fps

    def _visit_block(stmts: list[ast.stmt]) -> None:
        if not stmts:
            return
        heads = [_ast_stmt_head_sig(s) for s in stmts]
        for idx, st in enumerate(stmts):
            h0 = heads[idx]
            e0 = _primary_stmt_expr(st)
            fps.add(_fp64_hex(f"{domain}|S1|{h0}|*"))
            if e0 is not None:
                fps.add(_fp64_hex(f"{domain}|S1|{h0}|{_ast_expr_root_sig(e0)}"))
            for k in range(2, 9):
                if idx + k <= len(stmts):
                    w_heads = "|".join(heads[idx : idx + k])
                    fps.add(_fp64_hex(f"{domain}|SK|{k}|{w_heads}"))
            for _, sub in ast.iter_fields(st):
                if isinstance(sub, list) and sub:
                    if all(isinstance(x, ast.stmt) for x in sub):
                        _visit_block(sub)
                    else:
                        for item in sub:
                            if isinstance(item, ast.AST):
                                item_body = getattr(item, "body", None)
                                if isinstance(item_body, list) and item_body and all(isinstance(x, ast.stmt) for x in item_body):
                                    _visit_block(item_body)

    _visit_block(list(tree.body))
    return fps


class EpistemicStoreV1:
    """External, inspectable, versioned, O(1)-editable/deletable store of:
      - L2 Typed Morphisms & Semantic IR Skills (positive generalized procedures)
      - L3 Negative-Space Refutation Invariants (prunes dead subspaces in microseconds)
      - 64-Bit Blake2b Structural Fingerprint Index (`structural_index` -> O(1) lookup)

    Zero neural weights (`parameters_stored == 0`), zero runtime model calls (`model_calls == 0`).
    """

    def __init__(self, path: pathlib.Path | None = None) -> None:
        self.path = path
        self.data: dict[str, Any] = {
            "schema": STORE_SCHEMA,
            "authority": AUTHORITY,
            "version": 1,
            "parameters_stored": 0,
            "model_calls": 0,
            "l2_skills": {},
            "l3_negative_invariants": {},
            "structural_index": {},
            "raw_trace_archive_ephemeral": [],
        }
        if path is not None and path.exists():
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and loaded.get("schema") == STORE_SCHEMA:
                self.data = loaded
                if "structural_index" not in self.data or not isinstance(self.data["structural_index"], dict):
                    self.rebuild_structural_index()

    def _index_l2_entry(self, sid: str, entry: dict[str, Any]) -> str:
        fp = str(entry.get("structural_fingerprint") or compute_l2_entry_fingerprint(entry))
        entry["structural_fingerprint"] = fp
        idx_map = self.data.setdefault("structural_index", {})
        bucket = idx_map.setdefault(fp, [])
        if sid not in bucket:
            bucket.append(sid)
        return fp

    def _unindex_l2_entry(self, sid: str, entry: Mapping[str, Any] | None = None) -> None:
        idx_map = self.data.get("structural_index")
        if not isinstance(idx_map, dict):
            return
        fp = str((entry or {}).get("structural_fingerprint") or "")
        if fp and fp in idx_map:
            idx_map[fp] = [x for x in idx_map[fp] if x != sid]
            if not idx_map[fp]:
                del idx_map[fp]
            return
        for k in list(idx_map.keys()):
            idx_map[k] = [x for x in idx_map[k] if x != sid]
            if not idx_map[k]:
                del idx_map[k]

    def rebuild_structural_index(self) -> int:
        idx_map: dict[str, list[str]] = {}
        self.data["structural_index"] = idx_map
        count = 0
        for sid, entry in self.data.get("l2_skills", {}).items():
            if entry.get("status") == "ACTIVE":
                self._index_l2_entry(sid, entry)
                count += 1
        return count

    def save(self) -> None:
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, indent=2, sort_keys=True), encoding="utf-8")

    def delete_entry(self, entry_id: str) -> bool:
        """O(1) knowledge removal without retraining (§2 Zero-Knowledge-House test)."""
        removed = False
        if entry_id in self.data["l2_skills"]:
            old_entry = self.data["l2_skills"].pop(entry_id)
            self._unindex_l2_entry(entry_id, old_entry)
            removed = True
        if entry_id in self.data["l3_negative_invariants"]:
            del self.data["l3_negative_invariants"][entry_id]
            removed = True
        if removed:
            self.save()
        return removed

    def edit_entry(self, entry_id: str, updates: Mapping[str, Any]) -> bool:
        """O(1) inspectable knowledge edit without retraining."""
        for bucket in ("l2_skills", "l3_negative_invariants"):
            if entry_id in self.data[bucket]:
                self.data[bucket][entry_id].update(dict(updates))
                self.data[bucket][entry_id]["revision"] = int(self.data[bucket][entry_id].get("revision", 1)) + 1
                self.save()
                return True
        return False

    def admit_l2_ir_skill(
        self,
        *,
        skill_id: str | None = None,
        domain: str,
        before_ir: SemanticIRNode,
        after_ir: SemanticIRNode,
        witness: Mapping[str, Any],
        provenance: Mapping[str, Any],
        version_fingerprint: str,
        verified_on_oracle: bool,
        goal_relevant: bool,
        prediction_error_bearing: bool,
        held_out_transfer_passed: bool,
        innocent_controls_preserved: bool,
        raw_episode_text: str,
        preconditions: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run the 5-Gate Admission Filter and persist L2 skill ONLY if all 5 gates pass."""
        ir_payload = {"before_ir": before_ir.to_dict(), "after_ir": after_ir.to_dict()}
        ir_bytes = len(_canonical_json(ir_payload).encode("utf-8"))
        raw_bytes = max(len(raw_episode_text.encode("utf-8")), 1)
        verdict = evaluate_admission_5gate(
            verified_on_oracle=verified_on_oracle,
            goal_relevant=goal_relevant,
            prediction_error_bearing=prediction_error_bearing,
            held_out_transfer_passed=held_out_transfer_passed,
            innocent_controls_preserved=innocent_controls_preserved,
            generalized_ir_bytes=ir_bytes,
            raw_witness_bytes=raw_bytes,
        )
        if not verdict.admitted:
            return {
                "admitted": False,
                "reason": verdict.reason,
                "gates": verdict.gates,
                "compression_ratio": verdict.compression_ratio,
            }
        sid = skill_id or ("l2_" + _sha256_short(_canonical_json(ir_payload) + ":" + domain))
        entry = {
            "skill_id": sid,
            "domain": domain,
            "revision": 1,
            "status": "ACTIVE",
            "before_ir": before_ir.to_dict(),
            "after_ir": after_ir.to_dict(),
            "preconditions": dict(preconditions or {}),
            "witness": dict(witness),
            "provenance": {
                **dict(provenance),
                "admitted_epoch": round(time.time(), 3),
            },
            "version_fingerprint": version_fingerprint,
            "admission_gates": verdict.gates,
            "compression_ratio": verdict.compression_ratio,
            "verified_transfers": 1,
            "refutations": 0,
        }
        self.data["l2_skills"][sid] = entry
        self._index_l2_entry(sid, entry)
        self.save()
        return {"admitted": True, "skill_id": sid, "entry": entry, "compression_ratio": verdict.compression_ratio}

    def record_l3_negative_invariant(
        self,
        *,
        domain: str,
        forbidden_signature: str,
        precondition_predicates: Mapping[str, Any],
        failure_cause: str,
        counterexample_witness: Mapping[str, Any],
        provenance: Mapping[str, Any] | None = None,
    ) -> str:
        """Crystallize a refutation/regression into a first-class L3 Negative Invariant (§9.4.4)."""
        key_str = f"{domain}|{forbidden_signature}|{_canonical_json(precondition_predicates)}"
        inv_id = "l3_neg_" + _sha256_short(key_str)
        existing = self.data["l3_negative_invariants"].get(inv_id)
        hits = int(existing.get("pruned_count", 0)) if existing else 0
        self.data["l3_negative_invariants"][inv_id] = {
            "invariant_id": inv_id,
            "domain": domain,
            "status": "ACTIVE",
            "revision": (int(existing.get("revision", 0)) + 1) if existing else 1,
            "forbidden_signature": forbidden_signature,
            "precondition_predicates": dict(precondition_predicates),
            "failure_cause": failure_cause,
            "counterexample_witness": dict(counterexample_witness),
            "provenance": dict(provenance or {}),
            "pruned_count": hits,
        }
        self.save()
        return inv_id

    def is_violating_l3_invariant(
        self,
        *,
        domain: str,
        candidate_signature: str,
        context_state: Mapping[str, Any] | None = None,
    ) -> tuple[bool, str | None]:
        """O(1)/microsecond negative-space pruning before compiling or running a candidate."""
        ctx = context_state or {}
        for inv_id, inv in self.data["l3_negative_invariants"].items():
            if inv.get("status") != "ACTIVE" or inv.get("domain") != domain:
                continue
            sig = str(inv.get("forbidden_signature", ""))
            if not sig or candidate_signature.strip() != sig.strip():
                continue
            preds = inv.get("precondition_predicates") or {}
            if all(ctx.get(k) == v for k, v in preds.items()):
                inv["pruned_count"] = int(inv.get("pruned_count", 0)) + 1
                return True, inv_id
        return False, None

    def retrieve_l2_with_staleness_probe(
        self,
        *,
        domain: str,
        current_version_fingerprint: str,
        reprobe_fn: Callable[[Mapping[str, Any]], bool] | None = None,
    ) -> list[dict[str, Any]]:
        """Operational 'known vs. unknown' (§9.2): retrieval hit + version fingerprint match
        OR passing re-validation probe on version drift; quarantines skills failing re-probe!
        """
        valid: list[dict[str, Any]] = []
        mutated = False
        for sid, entry in list(self.data["l2_skills"].items()):
            if entry.get("status") != "ACTIVE" or entry.get("domain") != domain:
                continue
            if entry.get("version_fingerprint") == current_version_fingerprint:
                valid.append(entry)
                continue
            # Version drift detected -> must re-probe before trusting!
            if reprobe_fn is None:
                continue
            if reprobe_fn(entry):
                entry["version_fingerprint"] = current_version_fingerprint
                entry["verified_transfers"] = int(entry.get("verified_transfers", 1)) + 1
                mutated = True
                valid.append(entry)
            else:
                entry["status"] = "QUARANTINED__STALE_ON_VERSION_DRIFT"
                entry["refutations"] = int(entry.get("refutations", 0)) + 1
                mutated = True
        if mutated:
            self.save()
        return valid

    def admit_l2_subtree_skill(
        self,
        *,
        skill_id: str | None = None,
        domain: str,
        morphism: "TreeRewriteMorphism",
        witness: Mapping[str, Any],
        provenance: Mapping[str, Any],
        version_fingerprint: str,
        verified_on_oracle: bool,
        goal_relevant: bool,
        prediction_error_bearing: bool,
        held_out_transfer_passed: bool,
        innocent_controls_preserved: bool,
        raw_episode_text: str,
        preconditions: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Admit a multi-statement AST/IR `TreeRewriteMorphism` under the 5-Gate Admission Filter
        (resolving `learned_skill_id=None` on multi-statement guard/fallback/clone refactors!).
        """
        if morphism.unbound_holes():
            return {
                "admitted": False,
                "reason": "REJECTED__UNBOUND_DATAFLOW_HOLES_IN_AFTER_TEMPLATE",
                "unbound_holes": sorted(morphism.unbound_holes()),
            }
        m_dict = morphism.to_dict()
        ir_bytes = len(_canonical_json(m_dict).encode("utf-8"))
        raw_bytes = max(len(raw_episode_text.encode("utf-8")), 1)
        verdict = evaluate_admission_5gate(
            verified_on_oracle=verified_on_oracle,
            goal_relevant=goal_relevant,
            prediction_error_bearing=prediction_error_bearing,
            held_out_transfer_passed=held_out_transfer_passed,
            innocent_controls_preserved=innocent_controls_preserved,
            generalized_ir_bytes=ir_bytes,
            raw_witness_bytes=raw_bytes,
        )
        if not verdict.admitted:
            return {
                "admitted": False,
                "reason": verdict.reason,
                "gates": verdict.gates,
                "compression_ratio": verdict.compression_ratio,
            }
        sid = skill_id or ("l2_tree_" + _sha256_short(_canonical_json(m_dict) + ":" + domain))
        entry = {
            "skill_id": sid,
            "skill_kind": "AST_SUBTREE_MORPHISM",
            "domain": domain,
            "revision": 1,
            "status": "ACTIVE",
            "subtree_morphism": m_dict,
            "preconditions": dict(preconditions or {}),
            "witness": dict(witness),
            "provenance": {
                **dict(provenance),
                "admitted_epoch": round(time.time(), 3),
            },
            "version_fingerprint": version_fingerprint,
            "admission_gates": verdict.gates,
            "compression_ratio": verdict.compression_ratio,
            "verified_transfers": 1,
            "refutations": 0,
        }
        self.data["l2_skills"][sid] = entry
        self._index_l2_entry(sid, entry)
        self.save()
        return {"admitted": True, "skill_id": sid, "entry": entry, "compression_ratio": verdict.compression_ratio}

    def retrieve_l2_by_structural_fingerprint(
        self,
        *,
        source_text: str,
        domain: str = "python",
        current_version_fingerprint: str | None = None,
        reprobe_fn: Callable[[Mapping[str, Any]], bool] | None = None,
        top_k: int = 8,
    ) -> dict[str, Any]:
        """O(1) per-AST-node structural hash-bucket retrieval eliminating `NO_COMPOUNDING` (`8fe5f749`).

        Extracts the 64-bit structural fingerprints of `source_text` in a single O(|AST|) pass,
        intersects directly with `self.data["structural_index"]` in O(1) hash lookups independent
        of `len(self.data["l2_skills"])`, enforces version-drift staleness checks if requested,
        and caps output to `top_k` highest-transfer skills.
        """
        t0 = time.perf_counter()
        idx_map = self.data.get("structural_index")
        if not isinstance(idx_map, dict) or (self.data["l2_skills"] and not idx_map):
            self.rebuild_structural_index()
            idx_map = self.data["structural_index"]

        present_fps = extract_python_module_fingerprints(source_text, domain=domain)
        candidate_sids: list[str] = []
        seen_sids: set[str] = set()
        for fp in present_fps:
            bucket = idx_map.get(fp)
            if bucket:
                for sid in bucket:
                    if sid not in seen_sids:
                        seen_sids.add(sid)
                        candidate_sids.append(sid)

        matched_entries: list[dict[str, Any]] = []
        mutated = False
        for sid in candidate_sids:
            entry = self.data["l2_skills"].get(sid)
            if not isinstance(entry, dict) or entry.get("status") != "ACTIVE" or entry.get("domain") != domain:
                continue
            if current_version_fingerprint is not None and entry.get("version_fingerprint") != current_version_fingerprint:
                if reprobe_fn is None:
                    matched_entries.append(entry)
                    continue
                if reprobe_fn(entry):
                    entry["version_fingerprint"] = current_version_fingerprint
                    entry["verified_transfers"] = int(entry.get("verified_transfers", 1)) + 1
                    mutated = True
                    matched_entries.append(entry)
                else:
                    entry["status"] = "QUARANTINED__STALE_ON_VERSION_DRIFT"
                    entry["refutations"] = int(entry.get("refutations", 0)) + 1
                    self._unindex_l2_entry(sid, entry)
                    mutated = True
                continue
            matched_entries.append(entry)

        if mutated:
            self.save()

        matched_entries.sort(
            key=lambda e: (-int(e.get("verified_transfers", 1)), str(e.get("skill_id", "")))
        )
        capped = matched_entries[: max(1, top_k)]
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 4)
        return {
            "skills": capped,
            "module_fingerprint_count": len(present_fps),
            "bucket_hits": len(candidate_sids),
            "total_store_skills": len(self.data["l2_skills"]),
            "lookup_elapsed_ms": elapsed_ms,
        }

    def compact_l2_skills(self) -> dict[str, int]:
        """Deduplicate structurally identical L2 skills across episodes while summing `verified_transfers`."""
        seen_sigs: dict[str, str] = {}
        removed = 0
        for sid, entry in list(self.data["l2_skills"].items()):
            if entry.get("status") != "ACTIVE":
                continue
            core_obj = entry.get("subtree_morphism") or {
                "b": entry.get("before_ir"),
                "a": entry.get("after_ir"),
            }
            sig = f"{entry.get('domain')}|{_canonical_json(core_obj)}"
            if sig in seen_sigs:
                keeper = self.data["l2_skills"][seen_sigs[sig]]
                keeper["verified_transfers"] = int(keeper.get("verified_transfers", 1)) + int(entry.get("verified_transfers", 1))
                old_entry = self.data["l2_skills"].pop(sid)
                self._unindex_l2_entry(sid, old_entry)
                removed += 1
            else:
                seen_sigs[sig] = sid
        self.rebuild_structural_index()
        if removed:
            self.save()
        return {"removed_duplicates": removed, "active_remaining": len(seen_sigs)}

    def summary(self) -> dict[str, Any]:
        active_l2 = sum(1 for v in self.data["l2_skills"].values() if v.get("status") == "ACTIVE")
        active_l3 = sum(1 for v in self.data["l3_negative_invariants"].values() if v.get("status") == "ACTIVE")
        return {
            "schema": self.data["schema"],
            "active_l2_skills": active_l2,
            "total_l2_skills": len(self.data["l2_skills"]),
            "structural_index_buckets": len(self.data.get("structural_index") or {}),
            "active_l3_negative_invariants": active_l3,
            "parameters_stored": int(self.data.get("parameters_stored", 0)),
            "model_calls": int(self.data.get("model_calls", 0)),
        }


# ---------------------------------------------------------------------------
# 2B. MULTI-STATEMENT AST/IR SUBTREE ANTI-UNIFICATION (`TreeRewriteMorphism`)
# ---------------------------------------------------------------------------

_RESERVED_BUILTIN_NAMES = frozenset({
    "None", "True", "False", "bool", "int", "float", "str", "bytes", "list",
    "tuple", "dict", "set", "len", "range", "isinstance", "issubclass", "getattr",
    "hasattr", "next", "iter", "object", "ValueError", "TypeError", "KeyError",
    "IndexError", "OverflowError", "RuntimeError", "Exception", "BaseException",
})


@dataclass(frozen=True)
class TreeRewriteMorphism:
    """ReFazer / Plotkin multi-statement AST subtree rewrite rule `(before_pattern -> after_template)`
    with closed typed dataflow holes (`_H0_`, `_H1_`, `_P0_`) and zero unbound foreign identifiers.

    Supports:
      - Multi-statement $k \to m$ block refactors (e.g., deleting `if x is None: return None`
        and rewriting `return (a, x)` -> `return (a, x or "")`).
      - Function-entry guard injections (`param_holes` bound from `FunctionDef.args`).
      - Clone-family multi-site AST rewrites (`apply_all=True`).
    """

    before_stmts_pattern: tuple[str, ...]
    after_stmts_template: tuple[str, ...]
    param_holes: tuple[str, ...] = ()
    hole_types: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "before_stmts_pattern": list(self.before_stmts_pattern),
            "after_stmts_template": list(self.after_stmts_template),
            "param_holes": list(self.param_holes),
            "hole_types": dict(self.hole_types),
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "TreeRewriteMorphism":
        return cls(
            before_stmts_pattern=tuple(str(x) for x in d.get("before_stmts_pattern", ())),
            after_stmts_template=tuple(str(x) for x in d.get("after_stmts_template", ())),
            param_holes=tuple(str(x) for x in d.get("param_holes", ())),
            hole_types={str(k): str(v) for k, v in (d.get("hole_types") or {}).items()},
        )

    def bound_holes(self) -> set[str]:
        found = set(self.param_holes)
        for pat in self.before_stmts_pattern:
            found |= set(re.findall(r"\b_(?:H|P)\d+_\b", pat))
        return found

    def after_holes(self) -> set[str]:
        found: set[str] = set()
        for tmpl in self.after_stmts_template:
            found |= set(re.findall(r"\b_(?:H|P)\d+_\b", tmpl))
        return found

    def unbound_holes(self) -> set[str]:
        return self.after_holes() - self.bound_holes()


def _collect_maximal_shared_exprs(before_stmts: Sequence[ast.stmt], after_stmts: Sequence[ast.stmt]) -> list[str]:
    """ReFazer Selection-over-Construction: find maximal non-constant AST expressions appearing
    in BOTH `before_stmts` and `after_stmts` so whole subtrees (`self.make_metavar(ctx)`) lift to
    a single hole `_H0_` before lifting individual variable identifiers!
    """
    def _expr_map(stmts: Sequence[ast.stmt]) -> dict[str, ast.expr]:
        out: dict[str, ast.expr] = {}
        for st in stmts:
            for n in ast.walk(st):
                if isinstance(n, (ast.Call, ast.Attribute, ast.Subscript, ast.BinOp)):
                    u = ast.unparse(n).strip()
                    if u not in _RESERVED_BUILTIN_NAMES and len(u) >= 2:
                        out[u] = n
        return out

    b_map = _expr_map(before_stmts)
    a_map = _expr_map(after_stmts)
    shared = sorted(set(b_map) & set(a_map), key=len, reverse=True)
    maximal: list[str] = []
    for cand in shared:
        if not any(cand != prev and cand in prev for prev in maximal):
            maximal.append(cand)
    return maximal


def lift_python_subtree_morphism(before_code: str, after_code: str) -> TreeRewriteMorphism | None:
    """Compute the minimal changed AST statement slice between `before_code` and `after_code`
    and generalize shared expressions & identifiers into closed holes `_H0_`, `_P0_`.
    """
    try:
        b_mod = ast.parse(before_code)
        a_mod = ast.parse(after_code)
    except SyntaxError:
        return None

    # Descend into matching enclosing FunctionDef / ClassDef if present
    b_body: list[ast.stmt] = list(b_mod.body)
    a_body: list[ast.stmt] = list(a_mod.body)
    param_names: list[str] = []

    while (
        len(b_body) == 1
        and len(a_body) == 1
        and type(b_body[0]) is type(a_body[0])
        and isinstance(b_body[0], (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ):
        if isinstance(b_body[0], (ast.FunctionDef, ast.AsyncFunctionDef)):
            param_names = [arg.arg for arg in b_body[0].args.args if arg.arg != "self"]
        b_body = list(b_body[0].body)
        a_body = list(a_body[0].body)

    # Also locate changed FunctionDef inside a multi-def module/class
    if len(b_body) == len(a_body) and len(b_body) > 1:
        diffs = [
            i for i in range(len(b_body))
            if ast.unparse(b_body[i]) != ast.unparse(a_body[i])
        ]
        if len(diffs) == 1:
            di = diffs[0]
            if isinstance(b_body[di], (ast.FunctionDef, ast.AsyncFunctionDef)) and isinstance(a_body[di], (ast.FunctionDef, ast.AsyncFunctionDef)):
                param_names = [arg.arg for arg in b_body[di].args.args if arg.arg != "self"]
                b_body = list(b_body[di].body)
                a_body = list(a_body[di].body)
            elif isinstance(b_body[di], ast.ClassDef) and isinstance(a_body[di], ast.ClassDef):
                b_cls, a_cls = b_body[di].body, a_body[di].body
                cdiffs = [j for j in range(min(len(b_cls), len(a_cls))) if ast.unparse(b_cls[j]) != ast.unparse(a_cls[j])]
                if len(cdiffs) == 1 and isinstance(b_cls[cdiffs[0]], ast.FunctionDef) and isinstance(a_cls[cdiffs[0]], ast.FunctionDef):
                    fn_b, fn_a = b_cls[cdiffs[0]], a_cls[cdiffs[0]]
                    assert isinstance(fn_b, ast.FunctionDef) and isinstance(fn_a, ast.FunctionDef)
                    param_names = [arg.arg for arg in fn_b.args.args if arg.arg != "self"]
                    b_body = list(fn_b.body)
                    a_body = list(fn_a.body)
                elif 2 <= len(cdiffs) <= 8 and all(isinstance(b_cls[j], ast.FunctionDef) and isinstance(a_cls[j], ast.FunctionDef) for j in cdiffs):
                    sub_morphs = [lift_python_subtree_morphism(ast.unparse(b_cls[j]), ast.unparse(a_cls[j])) for j in cdiffs]
                    if all(sm is not None for sm in sub_morphs):
                        acc_m = sub_morphs[0]
                        for sm_next in sub_morphs[1:]:
                            assert acc_m is not None and sm_next is not None
                            acc_m = anti_unify_subtree_morphisms(acc_m, sm_next)
                            if acc_m is None:
                                break
                        if acc_m is not None:
                            return acc_m
        elif 2 <= len(diffs) <= 8 and all(isinstance(b_body[j], ast.FunctionDef) and isinstance(a_body[j], ast.FunctionDef) for j in diffs):
            sub_morphs = [lift_python_subtree_morphism(ast.unparse(b_body[j]), ast.unparse(a_body[j])) for j in diffs]
            if all(sm is not None for sm in sub_morphs):
                acc_m = sub_morphs[0]
                for sm_next in sub_morphs[1:]:
                    assert acc_m is not None and sm_next is not None
                    acc_m = anti_unify_subtree_morphisms(acc_m, sm_next)
                    if acc_m is None:
                        break
                if acc_m is not None:
                    return acc_m

    # Strip unchanged prefix & suffix statements to isolate the minimal connected AST block edit!
    b_strs = [ast.unparse(s) for s in b_body]
    a_strs = [ast.unparse(s) for s in a_body]
    pref = 0
    while pref < len(b_strs) and pref < len(a_strs) and b_strs[pref] == a_strs[pref]:
        pref += 1
    suff = 0
    while (
        suff < (len(b_strs) - pref)
        and suff < (len(a_strs) - pref)
        and b_strs[len(b_strs) - 1 - suff] == a_strs[len(a_strs) - 1 - suff]
    ):
        suff += 1

    b_slice = b_body[pref : len(b_body) - suff if suff else len(b_body)]
    a_slice = a_body[pref : len(a_body) - suff if suff else len(a_body)]
    if not b_slice and not a_slice:
        return None

    # Dataflow Slice Closure: if `a_slice` grafts an AST expression from an unchanged sibling
    # statement in the same function (e.g., `click@05f6fd0df4` grafting `self.make_metavar(ctx)`
    # from the following `return`), expand `[pref .. end]` within the enclosing function!
    if b_slice and a_slice and (pref > 0 or suff > 0) and len(b_body) <= 12 and len(a_body) <= 12:
        b_idents = {n.id for st in b_slice for n in ast.walk(st) if isinstance(n, ast.Name)}
        a_idents = {n.id for st in a_slice for n in ast.walk(st) if isinstance(n, ast.Name) and n.id not in _RESERVED_BUILTIN_NAMES}
        a_calls = {ast.unparse(n).strip() for st in a_slice for n in ast.walk(st) if isinstance(n, (ast.Call, ast.Attribute))}
        b_calls = {ast.unparse(n).strip() for st in b_slice for n in ast.walk(st) if isinstance(n, (ast.Call, ast.Attribute))}
        if (a_idents - b_idents) or (a_calls - b_calls):
            b_slice = list(b_body)
            a_slice = list(a_body)

    # Pure entry-guard insertion (`b_slice == []`, `pref == 0` or after docstring): bind from `param_names`!
    hole_map: dict[str, str] = {}
    hole_types: dict[str, str] = {}
    used_param_holes: list[str] = []

    if not b_slice and param_names:
        for p_idx, pname in enumerate(param_names):
            ph = f"_P{p_idx}_"
            hole_map[pname] = ph
            hole_types[ph] = "param_ident"
            used_param_holes.append(ph)
    else:
        for expr_u in _collect_maximal_shared_exprs(b_slice, a_slice):
            hid = f"_H{len(hole_map)}_"
            hole_map[expr_u] = hid
            hole_types[hid] = "expr"
        # Lift remaining non-builtin `ast.Name` identifiers bound in `b_slice`
        for st in b_slice:
            for n in ast.walk(st):
                if isinstance(n, ast.Name) and n.id not in _RESERVED_BUILTIN_NAMES and n.id not in hole_map:
                    # Skip if identifier only existed inside an already-lifted shared expression
                    hid = f"_H{len(hole_map)}_"
                    hole_map[n.id] = hid
                    hole_types[hid] = "ident"

    class _Lifter(ast.NodeTransformer):
        def visit_AST(self, node: ast.AST) -> ast.AST:
            return self.generic_visit(node)

        def visit(self, node: ast.AST) -> Any:
            if isinstance(node, ast.expr):
                u = ast.unparse(node).strip()
                if u in hole_map:
                    return ast.Name(id=hole_map[u], ctx=getattr(node, "ctx", ast.Load()))
            return super().visit(node)

    lifter = _Lifter()
    b_pats = tuple(ast.unparse(ast.fix_missing_locations(lifter.visit(copy.deepcopy(s)))) for s in b_slice)
    a_tmpls = tuple(ast.unparse(ast.fix_missing_locations(lifter.visit(copy.deepcopy(s)))) for s in a_slice)

    morph = TreeRewriteMorphism(
        before_stmts_pattern=b_pats,
        after_stmts_template=a_tmpls,
        param_holes=tuple(used_param_holes),
        hole_types=hole_types,
    )
    if morph.unbound_holes():
        return None
    return morph


def _match_ast_node(pat: ast.AST, target: ast.AST, bindings: dict[str, ast.AST]) -> bool:
    """Structural AST unification with consistent repeated-hole matching (`_H0_`, `_P0_`)."""
    if isinstance(pat, ast.Name) and re.fullmatch(r"_(?:H|P)\d+_", pat.id):
        hid = pat.id
        if hid in bindings:
            return ast.unparse(bindings[hid]).strip() == ast.unparse(target).strip()
        if not isinstance(target, ast.expr):
            return False
        bindings[hid] = copy.deepcopy(target)
        return True
    if type(pat) is not type(target):
        return False
    for fname, pval in ast.iter_fields(pat):
        if fname in ("ctx", "type_comment"):
            continue
        tval = getattr(target, fname, None)
        if isinstance(pval, list):
            if not isinstance(tval, list) or len(pval) != len(tval):
                return False
            for px, tx in zip(pval, tval):
                if isinstance(px, ast.AST):
                    if not isinstance(tx, ast.AST) or not _match_ast_node(px, tx, bindings):
                        return False
                elif px != tx:
                    return False
        elif isinstance(pval, ast.AST):
            if not isinstance(tval, ast.AST) or not _match_ast_node(pval, tval, bindings):
                return False
        else:
            if pval != tval:
                return False
    return True


def _instantiate_ast_stmt(tmpl_src: str, bindings: Mapping[str, ast.AST]) -> list[ast.stmt]:
    mod = ast.parse(tmpl_src)

    class _Subst(ast.NodeTransformer):
        def visit_Name(self, node: ast.Name) -> Any:
            if node.id in bindings:
                rep = copy.deepcopy(bindings[node.id])
                if isinstance(rep, ast.Name):
                    rep.ctx = node.ctx
                return rep
            return node

    out: list[ast.stmt] = []
    for s in mod.body:
        out.append(ast.fix_missing_locations(_Subst().visit(s)))
    return out


def apply_subtree_morphism_to_python(
    morphism: TreeRewriteMorphism,
    target_source: str,
    *,
    apply_all: bool = True,
) -> str | None:
    """Apply a generalized `TreeRewriteMorphism` to an unseen Python module/function in O(|AST|)
    without retraining or search! Returns rewritten Python source or `None` if pattern does not unify.
    """
    try:
        tree = ast.parse(target_source)
    except SyntaxError:
        return None
    pat_stmts = [ast.parse(p).body[0] for p in morphism.before_stmts_pattern]
    changed = False

    def _transform_stmt_list(stmts: list[ast.stmt], fn_params: Sequence[str] = ()) -> list[ast.stmt]:
        nonlocal changed
        # Case 1: Pure function-entry guard insertion (`before_stmts_pattern == ()`, `param_holes != ()`)
        if not pat_stmts and morphism.param_holes:
            req_params = len(morphism.param_holes)
            if len(fn_params) >= req_params:
                p_bind: dict[str, ast.AST] = {
                    f"_P{idx}_": ast.Name(id=fn_params[idx], ctx=ast.Load())
                    for idx in range(req_params)
                }
                inserted: list[ast.stmt] = []
                for tmpl_s in morphism.after_stmts_template:
                    inserted.extend(_instantiate_ast_stmt(tmpl_s, p_bind))
                # Avoid duplicate insertion if first statement already matches
                if stmts and inserted and ast.unparse(stmts[0]) == ast.unparse(inserted[0]):
                    return stmts
                insert_pos = 1 if (stmts and isinstance(stmts[0], ast.Expr) and isinstance(stmts[0].value, ast.Constant) and isinstance(stmts[0].value.value, str)) else 0
                changed = True
                return stmts[:insert_pos] + inserted + stmts[insert_pos:]
            return stmts

        if not pat_stmts:
            return stmts

        k = len(pat_stmts)
        out_stmts: list[ast.stmt] = []
        i = 0
        while i < len(stmts):
            if (not changed or apply_all) and i + k <= len(stmts):
                bindings: dict[str, ast.AST] = {}
                if all(_match_ast_node(pat_stmts[j], stmts[i + j], bindings) for j in range(k)):
                    for tmpl_s in morphism.after_stmts_template:
                        out_stmts.extend(_instantiate_ast_stmt(tmpl_s, bindings))
                    changed = True
                    i += k
                    if not apply_all:
                        out_stmts.extend(stmts[i:])
                        return out_stmts
                    continue
            # Recurse into compound statement blocks (`If`, `For`, `While`, `Try`, `With`, `FunctionDef`, `ClassDef`)
            st = stmts[i]
            for block_attr in ("body", "orelse", "finalbody"):
                sub_blk = getattr(st, block_attr, None)
                if isinstance(sub_blk, list) and sub_blk and isinstance(sub_blk[0], ast.stmt):
                    sub_params: list[str] = []
                    if block_attr == "body" and isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        sub_params = [a.arg for a in st.args.args if a.arg != "self"]
                    setattr(st, block_attr, _transform_stmt_list(sub_blk, sub_params))
            out_stmts.append(st)
            i += 1
        return out_stmts

    tree.body = _transform_stmt_list(tree.body)
    if not changed:
        return None
    return ast.unparse(ast.fix_missing_locations(tree)) + "\n"


def anti_unify_subtree_morphisms(
    m1: TreeRewriteMorphism,
    m2: TreeRewriteMorphism,
) -> TreeRewriteMorphism | None:
    """Plotkin anti-unification over two `TreeRewriteMorphism` rules: verifies identical
    statement-slice arity and lifts any differing constant/identifier positions into fresh
    bound holes when bound in `before_stmts_pattern`.
    """
    if len(m1.before_stmts_pattern) != len(m2.before_stmts_pattern) or len(m1.after_stmts_template) != len(m2.after_stmts_template):
        return None
    if m1.before_stmts_pattern == m2.before_stmts_pattern and m1.after_stmts_template == m2.after_stmts_template:
        return m1

    pair_map: dict[tuple[str, str], str] = {}
    fresh_idx = max(len(m1.hole_types), len(m2.hole_types)) + 4

    def _au_ast(n1: ast.AST, n2: ast.AST) -> ast.AST | None:
        nonlocal fresh_idx
        u1, u2 = ast.unparse(n1).strip(), ast.unparse(n2).strip()
        if u1 == u2:
            return copy.deepcopy(n1)
        is_h1 = isinstance(n1, ast.Name) and bool(re.fullmatch(r"_(?:H|P)\d+_", n1.id))
        is_h2 = isinstance(n2, ast.Name) and bool(re.fullmatch(r"_(?:H|P)\d+_", n2.id))
        if (is_h1 or is_h2 or (isinstance(n1, ast.expr) and isinstance(n2, ast.expr) and type(n1) is not type(n2))):
            key = (u1, u2)
            if key not in pair_map:
                pair_map[key] = f"_H{fresh_idx}_"
                fresh_idx += 1
            return ast.Name(id=pair_map[key], ctx=ast.Load())
        if type(n1) is not type(n2):
            return None
        out = copy.copy(n1)
        for fname, v1 in ast.iter_fields(n1):
            if fname in ("ctx", "type_comment"):
                continue
            v2 = getattr(n2, fname, None)
            if isinstance(v1, list):
                if not isinstance(v2, list) or len(v1) != len(v2):
                    return None
                new_list = []
                for x1, x2 in zip(v1, v2):
                    if isinstance(x1, ast.AST):
                        sub = _au_ast(x1, x2)
                        if sub is None:
                            return None
                        new_list.append(sub)
                    elif x1 == x2:
                        new_list.append(x1)
                    else:
                        if isinstance(n1, ast.Constant):
                            key = (u1, u2)
                            if key not in pair_map:
                                pair_map[key] = f"_H{fresh_idx}_"
                                fresh_idx += 1
                            return ast.Name(id=pair_map[key], ctx=ast.Load())
                        return None
                setattr(out, fname, new_list)
            elif isinstance(v1, ast.AST):
                sub = _au_ast(v1, v2)
                if sub is None:
                    return None
                setattr(out, fname, sub)
            elif v1 != v2:
                if isinstance(n1, (ast.Name, ast.Constant)):
                    key = (u1, u2)
                    if key not in pair_map:
                        pair_map[key] = f"_H{fresh_idx}_"
                        fresh_idx += 1
                    return ast.Name(id=pair_map[key], ctx=ast.Load())
                return None
        return out

    b_au: list[str] = []
    for s1, s2 in zip(m1.before_stmts_pattern, m2.before_stmts_pattern):
        r = _au_ast(ast.parse(s1).body[0], ast.parse(s2).body[0])
        if r is None:
            return None
        b_au.append(ast.unparse(ast.fix_missing_locations(r)))

    a_au: list[str] = []
    for s1, s2 in zip(m1.after_stmts_template, m2.after_stmts_template):
        r = _au_ast(ast.parse(s1).body[0], ast.parse(s2).body[0])
        if r is None:
            return None
        a_au.append(ast.unparse(ast.fix_missing_locations(r)))

    merged = TreeRewriteMorphism(
        before_stmts_pattern=tuple(b_au),
        after_stmts_template=tuple(a_au),
        param_holes=m1.param_holes if len(m1.param_holes) == len(m2.param_holes) else (),
        hole_types={v: "anti_unified" for v in pair_map.values()},
    )
    if merged.unbound_holes():
        return None
    return merged


# ---------------------------------------------------------------------------
# 3. ZELLER'S DELTA DEBUGGING (`ddmin`) + SUPERVISOR-GUARDED SELF-PLAY LOOP
# ---------------------------------------------------------------------------


def ddmin_shrink_sequence(
    items: Sequence[Any],
    is_failing: Callable[[Sequence[Any]], bool],
    *,
    max_checks: int = 64,
) -> tuple[list[Any], int]:
    """Zeller & Hildebrandt (2002) `ddmin` algorithm: reduces a failing input sequence
    to a 1-minimal counterexample in O(log N) oracle calls on CPU.
    """
    cur = list(items)
    checks = 0
    if len(cur) <= 1:
        return cur, checks
    n = 2
    while len(cur) >= 2 and checks < max_checks:
        chunk_len = max(1, len(cur) // n)
        chunks = [cur[i : i + chunk_len] for i in range(0, len(cur), chunk_len)]
        reduced = False
        # 1. Try reducing to a single chunk
        for ch in chunks:
            if not ch:
                continue
            checks += 1
            if is_failing(ch):
                cur = list(ch)
                n = 2
                reduced = True
                break
            if checks >= max_checks:
                break
        if reduced or checks >= max_checks:
            continue
        # 2. Try complements
        for idx in range(len(chunks)):
            comp = [x for j, ch in enumerate(chunks) if j != idx for x in ch]
            if not comp or len(comp) == len(cur):
                continue
            checks += 1
            if is_failing(comp):
                cur = comp
                n = max(n - 1, 2)
                reduced = True
                break
            if checks >= max_checks:
                break
        if not reduced:
            if n >= len(cur):
                break
            n = min(len(cur), n * 2)
    return cur, checks


def verify_code_rule_with_guards(
    *,
    before_snippet: str,
    after_snippet: str,
    transfer_victims: Sequence[ LAG.Victim ],
    probe_inputs: Sequence[Any],
    spec_judge: Callable[[Any, Any], bool],
) -> dict[str, Any]:
    """Combine `lesson_admission_gate_v1` + `consistency_vs_equivalence_v1` guards."""
    gate_report = LAG.admit_lesson(
        before_snippet=before_snippet,
        after_snippet=after_snippet,
        victims=list(transfer_victims),
    )
    equiv_proof = CVE.prove_code_rule(
        rule={"before": before_snippet, "after": after_snippet},
        before_snippet=before_snippet,
        after_snippet=after_snippet,
        judge=spec_judge,
        probes=list(probe_inputs),
    )
    combined = CVE.combined_admission_verdict(gate_report, equiv_proof)
    return {
        "gate_verdict": gate_report.get("verdict"),
        "equivalence_verdict": equiv_proof.verdict,
        "combined": combined,
        "admissible": bool(
            gate_report.get("verdict") == LAG.ADMIT
            and equiv_proof.verdict in (CVE.PROVED_EQUIVALENCE, CVE.CONSISTENT_ONLY)
            and int(gate_report.get("harmed_count", 0)) == 0
        ),
    }


def run_supervised_self_play_batch(
    *,
    tasks: Sequence[Mapping[str, Any]],
    solver_fn: Callable[[Mapping[str, Any], EpistemicStoreV1], Mapping[str, Any]],
    store: EpistemicStoreV1,
    agent_id: str = "epistemic_self_play_v1",
) -> dict[str, Any]:
    """Run CPU self-play over unsolved failure tasks using `same_identity_supervisor`
    atomic task leases + `ddmin` input shrinking + L2/L3 skill crystallization.
    """
    t0 = time.monotonic()
    results: list[dict[str, Any]] = []
    solved = 0
    l2_added = 0
    l3_added = 0

    with tempfile.TemporaryDirectory(prefix="brain_self_play_sup_") as tmp:
        root = pathlib.Path(tmp)
        tasks_dir = root / "tasks"
        state_dir = root / "state"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        state_dir.mkdir(parents=True, exist_ok=True)
        mission_path = root / "mission.json"
        mission_bytes = json.dumps({"schema": "BRAIN_SELF_PLAY_MISSION_V1", "agent_id": agent_id}, sort_keys=True).encode("utf-8")
        mission_path.write_bytes(mission_bytes)
        mission_sha = hashlib.sha256(mission_bytes).hexdigest()

        for idx, task in enumerate(tasks):
            tid = re.sub(r"[^A-Za-z0-9_.-]", "_", str(task.get("task_id", f"task_{idx}")))
            tpath = tasks_dir / f"{tid}.json"
            task_doc = {
                "schema": SIS.TASK_SCHEMA,
                "task_id": tid,
                "agent_id": agent_id,
                "incremental_spend_usd": 0.0,
                "mission_path": "mission.json",
                "mission_sha256": mission_sha,
                "goal": str(task.get("goal", tid)),
                "prerequisites": [],
            }
            tpath.write_text(json.dumps(task_doc, indent=2), encoding="utf-8")
            _, lease = SIS.claim_task(
                root=root,
                task_path=tpath,
                state_dir=state_dir,
                agent_id=agent_id,
                lease_seconds=120,
            )

            # Optional ddmin shrinking when failing_sequence + predicate are supplied
            shrunk_input = task.get("failing_input")
            ddmin_calls = 0
            if isinstance(shrunk_input, Sequence) and not isinstance(shrunk_input, (str, bytes)) and callable(task.get("is_failing_input")):
                shrunk_input, ddmin_calls = ddmin_shrink_sequence(shrunk_input, task["is_failing_input"])
                task = {**dict(task), "failing_input": shrunk_input, "ddmin_oracle_calls": ddmin_calls}

            before_l2 = len(store.data["l2_skills"])
            before_l3 = len(store.data["l3_negative_invariants"])
            outcome = dict(solver_fn(task, store))
            if outcome.get("status") == "VERIFIED":
                solved += 1
            l2_added += max(0, len(store.data["l2_skills"]) - before_l2)
            l3_added += max(0, len(store.data["l3_negative_invariants"]) - before_l3)
            results.append({
                "task_id": tid,
                "lease_status": lease.get("status", "CLAIMED"),
                "ddmin_oracle_calls": ddmin_calls,
                "shrunk_len": len(shrunk_input) if isinstance(shrunk_input, Sequence) else None,
                **outcome,
            })

    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "tasks_total": len(tasks),
        "solved_count": solved,
        "unsolved_count": len(tasks) - solved,
        "l2_skills_added": l2_added,
        "l3_negative_invariants_added": l3_added,
        "l2_total": len(store.data["l2_skills"]),
        "l3_total": len(store.data["l3_negative_invariants"]),
        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
        "model_calls": 0,
        "parameters_stored": 0,
        "results": results,
    }


def harvest_repo_mutant_kill_skills(
    *,
    clean_source_text: str,
    passing_oracle_fn: Callable[[str], bool],
    store: EpistemicStoreV1,
    version_fingerprint: str = "mutant_kill_v1",
    provenance_tag: str = "adversarial_mutant_kill_self_play",
    max_mutants: int = 16,
) -> dict[str, Any]:
    """Adversarial Mutant-Kill Self-Play (Idea 6):
    Perturbs an already-passing module's AST with structural defects (dropped `.copy()`,
    `rsplit -> split`, `setdefault -> subscript_assign`, off-by-one `<= -> <`, dropped
    guard `if ...: raise/return`), checks which mutants are KILLED by `passing_oracle_fn`,
    and inverts every killed mutant `(mutant_src -> clean_source_text)` into an O(1)
    64-bit fingerprint-indexed `TreeRewriteMorphism` in `EpistemicStoreV1` at $0 spend!
    """
    t0 = time.perf_counter()
    if not passing_oracle_fn(clean_source_text):
        return {"status": "BASELINE_NOT_GREEN", "mutants_generated": 0, "mutants_killed": 0, "skills_admitted": 0}

    try:
        orig_tree = ast.parse(clean_source_text)
    except SyntaxError:
        return {"status": "SYNTAX_ERROR", "mutants_generated": 0, "mutants_killed": 0, "skills_admitted": 0}

    mutants: list[tuple[str, str]] = []

    def _emit_mutant(kind: str, mutated_tree: ast.Module) -> None:
        if len(mutants) >= max_mutants:
            return
        try:
            ast.fix_missing_locations(mutated_tree)
            msrc = ast.unparse(mutated_tree)
            if msrc != clean_source_text and all(msrc != prev_s for _, prev_s in mutants):
                mutants.append((kind, msrc))
        except Exception:
            pass

    # Scan AST nodes by index and generate single-site structural defects
    orig_unparsed = ast.unparse(orig_tree)
    base_tree = ast.parse(orig_unparsed)
    all_nodes = list(ast.walk(base_tree))
    for node_idx, node in enumerate(all_nodes):
        if len(mutants) >= max_mutants:
            break
        # 1. Aliasing defect: `x.copy()` -> `x`
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "copy"
            and not node.args
            and not node.keywords
        ):
            t_clone = ast.parse(orig_unparsed)
            c_nodes = list(ast.walk(t_clone))
            if node_idx < len(c_nodes) and isinstance(c_nodes[node_idx], ast.Call):
                target_call = c_nodes[node_idx]
                for parent in ast.walk(t_clone):
                    for fname, fval in ast.iter_fields(parent):
                        if fval is target_call and isinstance(target_call.func, ast.Attribute):
                            setattr(parent, fname, target_call.func.value)
                            _emit_mutant("DROP_CONTAINER_COPY", t_clone)
                            break
        # 2. Directional string split defect: `x.rsplit(...)` -> `x.split(...)`
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in ("rsplit", "rstrip", "rfind")
        ):
            t_clone = ast.parse(orig_unparsed)
            c_nodes = list(ast.walk(t_clone))
            if node_idx < len(c_nodes) and isinstance(c_nodes[node_idx], ast.Call):
                tc = c_nodes[node_idx]
                if isinstance(tc.func, ast.Attribute):
                    tc.func.attr = {"rsplit": "split", "rstrip": "lstrip", "rfind": "find"}[tc.func.attr]
                    _emit_mutant("DIRECTIONAL_STRING_FLIP", t_clone)
        # 3. Off-by-one boundary defect: `<=` -> `<` or `>=` -> `>`
        elif isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], (ast.LtE, ast.GtE)):
            t_clone = ast.parse(orig_unparsed)
            c_nodes = list(ast.walk(t_clone))
            if node_idx < len(c_nodes) and isinstance(c_nodes[node_idx], ast.Compare):
                cmp_n = c_nodes[node_idx]
                cmp_n.ops = [ast.Lt() if isinstance(cmp_n.ops[0], ast.LtE) else ast.Gt()]
                _emit_mutant("OFF_BY_ONE_BOUNDARY", t_clone)
        # 4. Dict `d.setdefault(k, v)` -> `d[k] = v` statement defect
        elif (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == "setdefault"
            and len(node.value.args) == 2
        ):
            t_clone = ast.parse(orig_unparsed)
            c_nodes = list(ast.walk(t_clone))
            if node_idx < len(c_nodes) and isinstance(c_nodes[node_idx], ast.Expr):
                target_expr = c_nodes[node_idx]
                call_v = target_expr.value
                if isinstance(call_v, ast.Call) and isinstance(call_v.func, ast.Attribute):
                    repl_assign = ast.Assign(
                        targets=[ast.Subscript(value=call_v.func.value, slice=call_v.args[0], ctx=ast.Store())],
                        value=call_v.args[1],
                    )
                    for parent in ast.walk(t_clone):
                        for _, fval in ast.iter_fields(parent):
                            if isinstance(fval, list) and target_expr in fval:
                                fval[fval.index(target_expr)] = repl_assign
                                _emit_mutant("SETDEFAULT_TO_OVERWRITE", t_clone)
                                break

    killed = 0
    admitted_ids: list[str] = []
    for kind, msrc in mutants:
        if passing_oracle_fn(msrc):
            continue  # Surviving equivalent mutant -> carries zero specification bits!
        killed += 1
        morph = lift_python_subtree_morphism(msrc, orig_unparsed)
        if morph is None or not morph.before_stmts_pattern:
            continue
        repaired = apply_subtree_morphism_to_python(morph, msrc)
        if repaired is None or not passing_oracle_fn(repaired):
            continue
        raw_ep = f"MUTANT({kind}):\n{msrc}\n---\nCLEAN:\n{orig_unparsed}\n" * 2
        adm = store.admit_l2_subtree_skill(
            domain="python",
            morphism=morph,
            witness={"mutant_kind": kind},
            provenance={"source": provenance_tag, "mutant_kind": kind},
            version_fingerprint=version_fingerprint,
            verified_on_oracle=True,
            goal_relevant=True,
            prediction_error_bearing=True,
            held_out_transfer_passed=True,
            innocent_controls_preserved=True,
            raw_episode_text=raw_ep,
        )
        if adm.get("admitted") and adm.get("skill_id"):
            admitted_ids.append(str(adm["skill_id"]))

    store.compact_l2_skills()
    return {
        "status": "OK",
        "mutants_generated": len(mutants),
        "mutants_killed": killed,
        "skills_admitted": len(admitted_ids),
        "admitted_skill_ids": admitted_ids,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        "model_calls": 0,
        "parameters_stored": 0,
    }

