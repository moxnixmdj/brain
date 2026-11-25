#!/usr/bin/env python3
"""First-Principles Program & Environment Understanding Engine (V1).

Replaces hand-coded per-bug syntax templates with four interlocking first-principles
mechanisms (`model_calls = 0`, `$0` spend, `parameters_stored = 0`):

  1. Cross-File & Cross-Process Causal Data-Flow Graph (`CausalDataFlowGraph`):
     Traces runtime value lineage across intra-procedural AST def-use, inter-procedural
     call/return bindings, heap object attribute mutations (`(type, id(obj), attr)`),
     multi-thread hooks (`threading.settrace`), and child Python subprocesses
     (`PYTHONPATH` `sitecustomize.py` trace hook), supporting both `pytest` and stdlib
     `unittest`, and falling back seamlessly to `incremental_semantic_graph_v1` static
     cross-module symbol edges. Ranks upstream root-cause producers across files via
     Backward Value-Slice Proximity + Passing State-Invariant Divergence.

  2. Universal Semantic Meaning IR & Algebraic E-Graph Quotient (`SemanticMeaningIR`):
     Normalizes equivalent surface constructs (`for` accumulation, `while` index loop,
     list/set comprehension, `map`/`filter` combinators, `sum`/`any`/`all` reductions ->
     `STREAM_FOLD`; `if/return`, `if/else`, `a if c else b`, negated guards ->
     `GUARDED_CHOICE`) and applies algebraic/boolean equality canonicalization
     (De Morgan, relational orientation, commutativity, identity/annihilator reduction,
     and data-flow role alpha-renaming). Enables zero-shot transfer of learned semantic
     deltas across loop styles (`for` <-> `while` <-> comprehension) and across languages
     (`Python` -> `JavaScript`, `Rust`, `Go`).

  3. Goal-Directed Invention via Compositional Angelic Abduction & CEGIS (`AngelicCEGISSynthesizer`):
     Extracts causal interior specifications `(live_scope, angelic_target)` via concrete
     branch/sub-expression/value interventions in the CoW Zygote Simulator, synthesizes
     new expressions, state guards, exception translations, iterator materializations,
     and coupled multi-file patches bottom-up from the live runtime type vocabulary
     (quotiented by `SemanticMeaningIR` + observational vectors), and refines candidates
     via STUN counterexample unification whenever a passing test produces a counterexample.

  4. Dual-Surface Executable Mental Models (`ProgramStateMentalModel`,
     `CoWProgramSimulator`, `EnvironmentMentalModel`):
     - `ProgramStateMentalModel`: ~15 us/candidate in-memory frame + counterfactual
       boundary-state simulator (`None`, `0`, `-1`, `""`, `[]`, singleton, duplicate).
     - `CoWProgramSimulator`: ~2 ms/candidate live `pytest` / `unittest` `os.fork()`
       Copy-on-Write RAM `__code__` + `MetaPathFinder` simulator (`0` disk writes).
     - `EnvironmentMentalModel`: ~20 us/step CoW shadow filesystem + CLI + W3C ARIA
       transition simulator that predicts side effects and blocks destructive or inert
       plans before touching the real environment.
"""
from __future__ import annotations

import ast
import copy
import difflib
import hashlib
import importlib.abc
import importlib.machinery
import importlib.util
import json
import math
import os
import pathlib
import re
import select
import struct
import subprocess
import sys
import tempfile
import textwrap
import time
import types
import warnings
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from canonical.swe_kernel import incremental_semantic_graph_v1 as isg

SCHEMA = "FIRST_PRINCIPLES_MENTAL_CEGIS_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"


# =========================================================================== #
# LEAP 2: UNIVERSAL SEMANTIC MEANING IR & ALGEBRAIC E-GRAPH QUOTIENT
# =========================================================================== #

@dataclass(frozen=True)
class IRNode:
    """Canonical hash-consed semantic IR node (alpha-renamed, construct-independent)."""
    op: str
    args: tuple[Any, ...] = ()

    def canonical_sexpr(self) -> str:
        if not self.args:
            return self.op
        rendered = []
        for a in self.args:
            if isinstance(a, IRNode):
                rendered.append(a.canonical_sexpr())
            elif isinstance(a, tuple):
                inner = ",".join(x.canonical_sexpr() if isinstance(x, IRNode) else repr(x) for x in a)
                rendered.append(f"[{inner}]")
            else:
                rendered.append(repr(a))
        return f"({self.op} {' '.join(rendered)})"

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_sexpr().encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class SemanticDelta:
    """Construct- and variable-independent semantic transformation rule (`before_ir => after_ir`)."""
    before_ir: IRNode
    after_ir: IRNode
    mechanism: str = "CEGIS_INVENTION"

    def signature(self) -> str:
        return f"{self.before_ir.canonical_sexpr()} => {self.after_ir.canonical_sexpr()}"


_COMMUTATIVE_OPS = frozenset({"ADD", "MUL", "EQ", "NE", "AND", "OR", "BITAND", "BITOR", "BITXOR"})


def egraph_canonicalize(node: IRNode) -> IRNode:
    """Deterministic algebraic + boolean equality-saturation canonicalizer (< 30 us)."""
    c_args = tuple(
        egraph_canonicalize(a) if isinstance(a, IRNode)
        else tuple(egraph_canonicalize(x) if isinstance(x, IRNode) else x for x in a) if isinstance(a, tuple)
        else a
        for a in node.args
    )
    op = node.op

    # 1. Double negation & De Morgan laws
    if op == "NOT" and len(c_args) == 1 and isinstance(c_args[0], IRNode):
        inner = c_args[0]
        if inner.op == "NOT":
            return inner.args[0]
        if inner.op == "AND":
            return egraph_canonicalize(IRNode("OR", tuple(IRNode("NOT", (x,)) for x in inner.args)))
        if inner.op == "OR":
            return egraph_canonicalize(IRNode("AND", tuple(IRNode("NOT", (x,)) for x in inner.args)))
        neg_map = {
            "EQ": "NE", "NE": "EQ",
            "IS_NONE": "IS_NOT_NONE", "IS_NOT_NONE": "IS_NONE",
            "IS": "IS_NOT", "IS_NOT": "IS",
            "IN": "NOT_IN", "NOT_IN": "IN",
        }
        if inner.op in neg_map:
            return egraph_canonicalize(IRNode(neg_map[inner.op], inner.args))
        if inner.op == "LT":
            return egraph_canonicalize(IRNode("LE", (inner.args[1], inner.args[0])))
        if inner.op == "LE":
            return egraph_canonicalize(IRNode("LT", (inner.args[1], inner.args[0])))
        if inner.op == "CONST" and len(inner.args) == 1 and isinstance(inner.args[0], bool):
            return IRNode("CONST", (not inner.args[0],))

    # 2. Relational orientation: GT(a, b) -> LT(b, a); GE(a, b) -> LE(b, a)
    if op == "GT" and len(c_args) == 2:
        op, c_args = "LT", (c_args[1], c_args[0])
    elif op == "GE" and len(c_args) == 2:
        op, c_args = "LE", (c_args[1], c_args[0])

    # 3. Nullity canonicalization: EQ/IS(x, None) -> IS_NONE(x)
    if op in ("IS", "EQ") and len(c_args) == 2:
        if c_args[1] == IRNode("CONST", (None,)):
            return IRNode("IS_NONE", (c_args[0],))
        if c_args[0] == IRNode("CONST", (None,)):
            return IRNode("IS_NONE", (c_args[1],))
    if op in ("IS_NOT", "NE") and len(c_args) == 2:
        if c_args[1] == IRNode("CONST", (None,)):
            return IRNode("IS_NOT_NONE", (c_args[0],))
        if c_args[0] == IRNode("CONST", (None,)):
            return IRNode("IS_NOT_NONE", (c_args[1],))

    # 4. Associative flattening + identity/idempotence/complement for AND / OR
    if op in ("AND", "OR"):
        flat: list[IRNode] = []
        for x in c_args:
            if isinstance(x, IRNode) and x.op == op:
                flat.extend(x.args)
            elif isinstance(x, IRNode):
                flat.append(x)
        ident = True if op == "AND" else False
        annih = False if op == "AND" else True
        kept: list[IRNode] = []
        seen_sexpr: set[str] = set()
        for x in flat:
            if x == IRNode("CONST", (annih,)):
                return IRNode("CONST", (annih,))
            if x == IRNode("CONST", (ident,)):
                continue
            sx = x.canonical_sexpr()
            if sx not in seen_sexpr:
                seen_sexpr.add(sx)
                kept.append(x)
        for x in kept:
            neg = egraph_canonicalize(IRNode("NOT", (x,)))
            if neg.canonical_sexpr() in seen_sexpr:
                return IRNode("CONST", (annih,))
        if not kept:
            return IRNode("CONST", (ident,))
        if len(kept) == 1:
            return kept[0]
        kept.sort(key=lambda z: z.canonical_sexpr())
        return IRNode(op, tuple(kept))

    # 5. Arithmetic identities & annihilators
    zero = IRNode("CONST", (0,))
    one = IRNode("CONST", (1,))
    if op == "ADD" and len(c_args) == 2:
        if c_args[0] == zero and not isinstance(c_args[0].args[0], bool):
            return c_args[1]
        if c_args[1] == zero and not isinstance(c_args[1].args[0], bool):
            return c_args[0]
    if op == "SUB" and len(c_args) == 2:
        if c_args[1] == zero and not isinstance(c_args[1].args[0], bool):
            return c_args[0]
        if c_args[0] == c_args[1]:
            return zero
    if op == "MUL" and len(c_args) == 2:
        if (c_args[0] == zero and not isinstance(c_args[0].args[0], bool)) or (
            c_args[1] == zero and not isinstance(c_args[1].args[0], bool)
        ):
            return zero
        if c_args[0] == one and not isinstance(c_args[0].args[0], bool):
            return c_args[1]
        if c_args[1] == one and not isinstance(c_args[1].args[0], bool):
            return c_args[0]

    # 6. Guarded-choice normalization
    if op == "GUARDED_CHOICE" and len(c_args) == 3:
        pred, then_b, else_b = c_args
        if then_b == else_b:
            return then_b
        if pred == IRNode("CONST", (True,)):
            return then_b
        if pred == IRNode("CONST", (False,)):
            return else_b
        if isinstance(pred, IRNode):
            flipped = egraph_canonicalize(IRNode("NOT", (pred,)))
            if flipped.canonical_sexpr() < pred.canonical_sexpr():
                return IRNode("GUARDED_CHOICE", (flipped, else_b, then_b))

    # 7. Commutative canonical ordering
    if op in _COMMUTATIVE_OPS and len(c_args) == 2:
        s0 = c_args[0].canonical_sexpr() if isinstance(c_args[0], IRNode) else repr(c_args[0])
        s1 = c_args[1].canonical_sexpr() if isinstance(c_args[1], IRNode) else repr(c_args[1])
        if s1 < s0:
            c_args = (c_args[1], c_args[0])

    return IRNode(op, c_args)


class SemanticMeaningIR:
    """Universal construct-independent semantic lifter, comparator, and polyglot lowerer."""

    @staticmethod
    def lift_expr(node: ast.AST, role_map: Mapping[str, str] | None = None) -> IRNode:
        rmap = dict(role_map or {})
        return egraph_canonicalize(SemanticMeaningIR._lift_expr_raw(node, rmap))

    @staticmethod
    def _lift_expr_raw(node: ast.AST, rmap: dict[str, str]) -> IRNode:
        if isinstance(node, ast.Constant):
            return IRNode("CONST", (node.value,))
        if isinstance(node, ast.Name):
            return IRNode("VAR", (rmap.get(node.id, node.id),))
        if isinstance(node, ast.Attribute):
            return IRNode("ATTR", (SemanticMeaningIR._lift_expr_raw(node.value, rmap), node.attr))
        if isinstance(node, ast.Subscript):
            sl = node.slice
            if isinstance(sl, ast.Slice):
                lo = SemanticMeaningIR._lift_expr_raw(sl.lower, rmap) if sl.lower else IRNode("CONST", (None,))
                hi = SemanticMeaningIR._lift_expr_raw(sl.upper, rmap) if sl.upper else IRNode("CONST", (None,))
                st = SemanticMeaningIR._lift_expr_raw(sl.step, rmap) if sl.step else IRNode("CONST", (None,))
                return IRNode("SLICE", (SemanticMeaningIR._lift_expr_raw(node.value, rmap), lo, hi, st))
            return IRNode("INDEX", (
                SemanticMeaningIR._lift_expr_raw(node.value, rmap),
                SemanticMeaningIR._lift_expr_raw(sl, rmap),
            ))
        if isinstance(node, ast.UnaryOp):
            u_map = {ast.Not: "NOT", ast.USub: "NEG", ast.UAdd: "POS", ast.Invert: "BITNOT"}
            op = u_map.get(type(node.op), type(node.op).__name__.upper())
            if op == "POS":
                return SemanticMeaningIR._lift_expr_raw(node.operand, rmap)
            return IRNode(op, (SemanticMeaningIR._lift_expr_raw(node.operand, rmap),))
        if isinstance(node, ast.BinOp):
            b_map = {
                ast.Add: "ADD", ast.Sub: "SUB", ast.Mult: "MUL", ast.Div: "DIV",
                ast.FloorDiv: "FDIV", ast.Mod: "MOD", ast.BitAnd: "BITAND",
                ast.BitOr: "BITOR", ast.BitXor: "BITXOR",
            }
            op = b_map.get(type(node.op), type(node.op).__name__.upper())
            return IRNode(op, (
                SemanticMeaningIR._lift_expr_raw(node.left, rmap),
                SemanticMeaningIR._lift_expr_raw(node.right, rmap),
            ))
        if isinstance(node, ast.BoolOp):
            op = "AND" if isinstance(node.op, ast.And) else "OR"
            return IRNode(op, tuple(SemanticMeaningIR._lift_expr_raw(v, rmap) for v in node.values))
        if isinstance(node, ast.Compare):
            c_map = {
                ast.Eq: "EQ", ast.NotEq: "NE", ast.Lt: "LT", ast.LtE: "LE",
                ast.Gt: "GT", ast.GtE: "GE", ast.Is: "IS", ast.IsNot: "IS_NOT",
                ast.In: "IN", ast.NotIn: "NOT_IN",
            }
            terms: list[IRNode] = []
            cur = SemanticMeaningIR._lift_expr_raw(node.left, rmap)
            for op_node, comp in zip(node.ops, node.comparators):
                nxt = SemanticMeaningIR._lift_expr_raw(comp, rmap)
                terms.append(IRNode(c_map.get(type(op_node), "CMP"), (cur, nxt)))
                cur = nxt
            return terms[0] if len(terms) == 1 else IRNode("AND", tuple(terms))
        if isinstance(node, ast.IfExp):
            return IRNode("GUARDED_CHOICE", (
                SemanticMeaningIR._lift_expr_raw(node.test, rmap),
                SemanticMeaningIR._lift_expr_raw(node.body, rmap),
                SemanticMeaningIR._lift_expr_raw(node.orelse, rmap),
            ))
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)) and len(node.generators) == 1:
            gen = node.generators[0]
            if isinstance(gen.target, ast.Name):
                src_ir = SemanticMeaningIR._lift_expr_raw(gen.iter, rmap)
                inner_map = {**rmap, gen.target.id: "$elem0"}
                preds = [SemanticMeaningIR._lift_expr_raw(p, inner_map) for p in gen.ifs]
                pred_ir = IRNode("AND", tuple(preds)) if len(preds) > 1 else (preds[0] if preds else IRNode("CONST", (True,)))
                map_ir = SemanticMeaningIR._lift_expr_raw(node.elt, inner_map)
                kind = "collect_list" if isinstance(node, ast.ListComp) else ("collect_set" if isinstance(node, ast.SetComp) else "stream")
                return IRNode("STREAM_FOLD", (kind, src_ir, pred_ir, map_ir))
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                fname = node.func.id
                if fname == "len" and len(node.args) == 1 and not node.keywords:
                    return IRNode("LEN", (SemanticMeaningIR._lift_expr_raw(node.args[0], rmap),))
                if fname == "bool" and len(node.args) == 1 and not node.keywords:
                    return IRNode("BOOL", (SemanticMeaningIR._lift_expr_raw(node.args[0], rmap),))
                if fname in ("list", "set") and len(node.args) == 1 and not node.keywords:
                    inner = SemanticMeaningIR._lift_functional_pipeline(node.args[0], rmap)
                    if inner is not None:
                        src_ir, pred_ir, map_ir = inner
                        kind = "collect_list" if fname == "list" else "collect_set"
                        return IRNode("STREAM_FOLD", (kind, src_ir, pred_ir, map_ir))
                if fname in ("sum", "any", "all") and len(node.args) == 1 and not node.keywords:
                    arg0 = node.args[0]
                    if isinstance(arg0, (ast.GeneratorExp, ast.ListComp)) and len(arg0.generators) == 1 and isinstance(arg0.generators[0].target, ast.Name):
                        gen = arg0.generators[0]
                        src_ir = SemanticMeaningIR._lift_expr_raw(gen.iter, rmap)
                        inner_map = {**rmap, gen.target.id: "$elem0"}
                        preds = [SemanticMeaningIR._lift_expr_raw(p, inner_map) for p in gen.ifs]
                        pred_ir = IRNode("AND", tuple(preds)) if len(preds) > 1 else (preds[0] if preds else IRNode("CONST", (True,)))
                        map_ir = SemanticMeaningIR._lift_expr_raw(arg0.elt, inner_map)
                        return IRNode("STREAM_FOLD", (fname, src_ir, pred_ir, map_ir))
                return IRNode("CALL", (
                    rmap.get(fname, fname),
                    tuple(SemanticMeaningIR._lift_expr_raw(a, rmap) for a in node.args),
                ))
            if isinstance(node.func, ast.Attribute):
                return IRNode("MCALL", (
                    SemanticMeaningIR._lift_expr_raw(node.func.value, rmap),
                    node.func.attr,
                    tuple(SemanticMeaningIR._lift_expr_raw(a, rmap) for a in node.args),
                ))
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            tag = "LIST" if isinstance(node, ast.List) else ("TUPLE" if isinstance(node, ast.Tuple) else "SET")
            return IRNode(tag, tuple(SemanticMeaningIR._lift_expr_raw(e, rmap) for e in node.elts))
        return IRNode("RAW", (ast.unparse(node),))

    @staticmethod
    def _lift_functional_pipeline(node: ast.AST, rmap: dict[str, str]) -> tuple[IRNode, IRNode, IRNode] | None:
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            return None
        if node.func.id == "map" and len(node.args) == 2 and isinstance(node.args[0], ast.Lambda) and len(node.args[0].args.args) == 1:
            m_var = node.args[0].args.args[0].arg
            sub = SemanticMeaningIR._lift_functional_pipeline(node.args[1], rmap)
            if sub is not None:
                src_ir, pred_ir, prev_map = sub
                if prev_map == IRNode("VAR", ("$elem0",)):
                    map_ir = SemanticMeaningIR._lift_expr_raw(node.args[0].body, {**rmap, m_var: "$elem0"})
                    return src_ir, pred_ir, map_ir
            src_ir = SemanticMeaningIR._lift_expr_raw(node.args[1], rmap)
            map_ir = SemanticMeaningIR._lift_expr_raw(node.args[0].body, {**rmap, m_var: "$elem0"})
            return src_ir, IRNode("CONST", (True,)), map_ir
        if node.func.id == "filter" and len(node.args) == 2 and isinstance(node.args[0], ast.Lambda) and len(node.args[0].args.args) == 1:
            f_var = node.args[0].args.args[0].arg
            src_ir = SemanticMeaningIR._lift_expr_raw(node.args[1], rmap)
            pred_ir = SemanticMeaningIR._lift_expr_raw(node.args[0].body, {**rmap, f_var: "$elem0"})
            return src_ir, pred_ir, IRNode("VAR", ("$elem0",))
        return None

    @staticmethod
    def lift_function_or_block(source: str) -> IRNode:
        """Lift a function or statement block into Universal Meaning IR (`STREAM_FOLD` / `GUARDED_CHOICE`)."""
        tree = ast.parse(textwrap.dedent(source))
        rmap: dict[str, str] = {}
        stmts = tree.body
        if len(stmts) == 1 and isinstance(stmts[0], (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn = stmts[0]
            for idx, arg in enumerate(fn.args.args):
                rmap[arg.arg] = f"$p{idx}"
            stmts = [
                s for s in fn.body
                if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))
            ]
        return egraph_canonicalize(SemanticMeaningIR._lift_stmts(stmts, rmap))

    @staticmethod
    def _lift_stmts(stmts: list[ast.stmt], rmap: dict[str, str]) -> IRNode:
        if not stmts:
            return IRNode("CONST", (None,))
        if len(stmts) == 1 and isinstance(stmts[0], ast.Return) and stmts[0].value is not None:
            return SemanticMeaningIR._lift_expr_raw(stmts[0].value, rmap)

        if isinstance(stmts[0], ast.If):
            if_stmt = stmts[0]
            if len(if_stmt.body) == 1 and isinstance(if_stmt.body[0], ast.Return):
                pred = SemanticMeaningIR._lift_expr_raw(if_stmt.test, rmap)
                then_ir = SemanticMeaningIR._lift_stmts(if_stmt.body, rmap)
                rest = if_stmt.orelse if if_stmt.orelse else stmts[1:]
                if rest:
                    else_ir = SemanticMeaningIR._lift_stmts(rest, rmap)
                    return IRNode("GUARDED_CHOICE", (pred, then_ir, else_ir))

        fold_for = SemanticMeaningIR._match_for_fold(stmts, rmap)
        if fold_for is not None:
            return fold_for

        fold_while = SemanticMeaningIR._match_while_fold(stmts, rmap)
        if fold_while is not None:
            return fold_while

        if len(stmts) == 2 and isinstance(stmts[0], ast.Assign) and len(stmts[0].targets) == 1 and isinstance(stmts[0].targets[0], ast.Name):
            lhs = stmts[0].targets[0].id
            rhs_ir = SemanticMeaningIR._lift_expr_raw(stmts[0].value, rmap)
            if isinstance(stmts[1], ast.Return) and stmts[1].value is not None:
                ret_ir = SemanticMeaningIR._lift_expr_raw(stmts[1].value, rmap)
                return SemanticMeaningIR._subst_var(ret_ir, rmap.get(lhs, lhs), rhs_ir)

        return IRNode("SEQ", tuple(IRNode("STMT", (ast.unparse(s),)) for s in stmts))

    @staticmethod
    def _subst_var(ir: IRNode, var_name: str, replacement: IRNode) -> IRNode:
        if ir.op == "VAR" and ir.args == (var_name,):
            return replacement
        new_args = tuple(
            SemanticMeaningIR._subst_var(a, var_name, replacement) if isinstance(a, IRNode)
            else tuple(SemanticMeaningIR._subst_var(x, var_name, replacement) if isinstance(x, IRNode) else x for x in a) if isinstance(a, tuple)
            else a
            for a in ir.args
        )
        return IRNode(ir.op, new_args)

    @staticmethod
    def _match_for_fold(stmts: list[ast.stmt], rmap: dict[str, str]) -> IRNode | None:
        if (
            len(stmts) == 2
            and isinstance(stmts[0], ast.For)
            and isinstance(stmts[0].target, ast.Name)
            and isinstance(stmts[1], ast.Return)
            and isinstance(stmts[1].value, ast.Constant)
            and isinstance(stmts[1].value.value, bool)
        ):
            for_s = stmts[0]
            default_bool = stmts[1].value.value
            if len(for_s.body) == 1 and isinstance(for_s.body[0], ast.If) and len(for_s.body[0].body) == 1:
                ret_in = for_s.body[0].body[0]
                if isinstance(ret_in, ast.Return) and isinstance(ret_in.value, ast.Constant) and ret_in.value.value == (not default_bool):
                    src_ir = SemanticMeaningIR._lift_expr_raw(for_s.iter, rmap)
                    inner_map = {**rmap, for_s.target.id: "$elem0"}
                    pred_ir = SemanticMeaningIR._lift_expr_raw(for_s.body[0].test, inner_map)
                    if default_bool is False:
                        return IRNode("STREAM_FOLD", ("any", src_ir, IRNode("CONST", (True,)), pred_ir))
                    return IRNode("STREAM_FOLD", ("all", src_ir, IRNode("CONST", (True,)), IRNode("NOT", (pred_ir,))))

        if len(stmts) == 3 and isinstance(stmts[0], ast.Assign) and len(stmts[0].targets) == 1 and isinstance(stmts[0].targets[0], ast.Name):
            acc = stmts[0].targets[0].id
            init_val = stmts[0].value
            if not (isinstance(stmts[2], ast.Return) and isinstance(stmts[2].value, ast.Name) and stmts[2].value.id == acc):
                return None
            if not (isinstance(stmts[1], ast.For) and isinstance(stmts[1].target, ast.Name)):
                return None
            kind = SemanticMeaningIR._init_fold_kind(init_val)
            if kind is None:
                return None
            for_s = stmts[1]
            src_ir = SemanticMeaningIR._lift_expr_raw(for_s.iter, rmap)
            inner_map = {**rmap, for_s.target.id: "$elem0"}
            parsed = SemanticMeaningIR._extract_loop_step(for_s.body, acc, kind, inner_map)
            if parsed is not None:
                pred_ir, map_ir = parsed
                return IRNode("STREAM_FOLD", (kind, src_ir, pred_ir, map_ir))
        return None

    @staticmethod
    def _match_while_fold(stmts: list[ast.stmt], rmap: dict[str, str]) -> IRNode | None:
        if len(stmts) != 4 or not isinstance(stmts[2], ast.While):
            return None
        if not (isinstance(stmts[3], ast.Return) and isinstance(stmts[3].value, ast.Name)):
            return None
        acc_name = stmts[3].value.id
        idx_name = None
        kind = None
        for init_s in (stmts[0], stmts[1]):
            if not (isinstance(init_s, ast.Assign) and len(init_s.targets) == 1 and isinstance(init_s.targets[0], ast.Name)):
                return None
            nm = init_s.targets[0].id
            if nm == acc_name:
                kind = SemanticMeaningIR._init_fold_kind(init_s.value)
            elif isinstance(init_s.value, ast.Constant) and init_s.value.value == 0:
                idx_name = nm
        if kind is None or idx_name is None:
            return None
        wh = stmts[2]
        if not (
            isinstance(wh.test, ast.Compare)
            and len(wh.test.ops) == 1
            and isinstance(wh.test.ops[0], ast.Lt)
            and isinstance(wh.test.left, ast.Name)
            and wh.test.left.id == idx_name
            and isinstance(wh.test.comparators[0], ast.Call)
            and isinstance(wh.test.comparators[0].func, ast.Name)
            and wh.test.comparators[0].func.id == "len"
            and len(wh.test.comparators[0].args) == 1
        ):
            return None
        src_node = wh.test.comparators[0].args[0]
        src_ir = SemanticMeaningIR._lift_expr_raw(src_node, rmap)
        body = list(wh.body)
        if len(body) < 2:
            return None
        last = body[-1]
        inc_ok = (
            isinstance(last, ast.AugAssign)
            and isinstance(last.target, ast.Name)
            and last.target.id == idx_name
            and isinstance(last.op, ast.Add)
            and isinstance(last.value, ast.Constant)
            and last.value.value == 1
        )
        if not inc_ok:
            return None
        core = body[:-1]
        inner_map = dict(rmap)
        if (
            core
            and isinstance(core[0], ast.Assign)
            and len(core[0].targets) == 1
            and isinstance(core[0].targets[0], ast.Name)
            and isinstance(core[0].value, ast.Subscript)
            and ast.unparse(core[0].value.value) == ast.unparse(src_node)
            and isinstance(core[0].value.slice, ast.Name)
            and core[0].value.slice.id == idx_name
        ):
            inner_map[core[0].targets[0].id] = "$elem0"
            core = core[1:]
        parsed = SemanticMeaningIR._extract_loop_step(core, acc_name, kind, inner_map)
        if parsed is not None:
            pred_ir, map_ir = parsed
            return IRNode("STREAM_FOLD", (kind, src_ir, pred_ir, map_ir))
        return None

    @staticmethod
    def _init_fold_kind(node: ast.AST) -> str | None:
        if isinstance(node, ast.List) and not node.elts:
            return "collect_list"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "list" and not node.args:
            return "collect_list"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "set" and not node.args:
            return "collect_set"
        if isinstance(node, ast.Constant) and node.value == 0 and not isinstance(node.value, bool):
            return "sum"
        return None

    @staticmethod
    def _extract_loop_step(
        body: list[ast.stmt],
        acc_name: str,
        kind: str,
        inner_map: dict[str, str],
    ) -> tuple[IRNode, IRNode] | None:
        preds: list[IRNode] = []
        rem = list(body)
        while len(rem) >= 2 and isinstance(rem[0], ast.If) and not rem[0].orelse and len(rem[0].body) == 1 and isinstance(rem[0].body[0], ast.Continue):
            preds.append(IRNode("NOT", (SemanticMeaningIR._lift_expr_raw(rem[0].test, inner_map),)))
            rem = rem[1:]
        if len(rem) == 1 and isinstance(rem[0], ast.If) and not rem[0].orelse:
            preds.append(SemanticMeaningIR._lift_expr_raw(rem[0].test, inner_map))
            rem = rem[0].body
        if len(rem) != 1:
            return None
        step = rem[0]
        map_ir: IRNode | None = None
        if kind in ("collect_list", "collect_set") and isinstance(step, ast.Expr) and isinstance(step.value, ast.Call):
            call = step.value
            expected_m = "append" if kind == "collect_list" else "add"
            if (
                isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id == acc_name
                and call.func.attr == expected_m
                and len(call.args) == 1
            ):
                map_ir = SemanticMeaningIR._lift_expr_raw(call.args[0], inner_map)
        elif kind == "sum" and isinstance(step, ast.AugAssign) and isinstance(step.target, ast.Name) and step.target.id == acc_name and isinstance(step.op, ast.Add):
            map_ir = SemanticMeaningIR._lift_expr_raw(step.value, inner_map)
        if map_ir is None:
            return None
        pred_ir = IRNode("AND", tuple(preds)) if len(preds) > 1 else (preds[0] if preds else IRNode("CONST", (True,)))
        return pred_ir, map_ir

    @staticmethod
    def apply_semantic_delta(
        target_fn_source: str,
        delta: SemanticDelta,
        *,
        output_style: str = "preserve",
        target_language: str = "python",
    ) -> str | None:
        """Apply a construct-independent `SemanticDelta` to any equivalent function (`for`, `while`, comprehension, or JS/Rust)."""
        lifted = SemanticMeaningIR.lift_function_or_block(target_fn_source)
        if lifted != delta.before_ir:
            return None
        tree = ast.parse(textwrap.dedent(target_fn_source))
        fn = tree.body[0]
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return None
        params = [a.arg for a in fn.args.args]
        if target_language == "javascript":
            return SemanticMeaningIR.lower_to_javascript(delta.after_ir, fn_name=fn.name, param_names=params)
        if target_language == "rust":
            return SemanticMeaningIR.lower_to_rust(delta.after_ir, fn_name=fn.name, param_names=params)

        style = output_style
        if style == "preserve":
            if any(isinstance(n, ast.While) for n in ast.walk(fn)):
                style = "while"
            elif any(isinstance(n, ast.For) for n in ast.walk(fn)):
                style = "for"
            else:
                style = "comprehension"
        body_code = SemanticMeaningIR.lower_to_python(delta.after_ir, style=style, param_names=params)
        indented = textwrap.indent(body_code, "    ")
        sig = f"def {fn.name}({', '.join(params)}):\n"
        return sig + indented + "\n"

    @staticmethod
    def lower_to_python(ir: IRNode, *, style: str = "comprehension", param_names: Sequence[str] = ("items",)) -> str:
        bindings = {f"$p{i}": name for i, name in enumerate(param_names)}
        bindings["$elem0"] = "_x"
        if ir.op == "STREAM_FOLD" and len(ir.args) == 4:
            kind, src_ir, pred_ir, map_ir = ir.args
            src_s = SemanticMeaningIR._lower_expr_py(src_ir, bindings)
            pred_s = SemanticMeaningIR._lower_expr_py(pred_ir, bindings)
            map_s = SemanticMeaningIR._lower_expr_py(map_ir, bindings)
            has_pred = pred_ir != IRNode("CONST", (True,))
            if style == "comprehension":
                filt = f" if {pred_s}" if has_pred else ""
                if kind == "collect_list":
                    return f"return [{map_s} for _x in {src_s}{filt}]"
                if kind == "collect_set":
                    return f"return {{{map_s} for _x in {src_s}{filt}}}"
                if kind == "sum":
                    return f"return sum({map_s} for _x in {src_s}{filt})"
                if kind in ("any", "all"):
                    return f"return {kind}({map_s} for _x in {src_s}{filt})"
            if style == "for":
                init = "[]" if kind == "collect_list" else ("set()" if kind == "collect_set" else "0")
                act = f"_acc.append({map_s})" if kind == "collect_list" else (f"_acc.add({map_s})" if kind == "collect_set" else f"_acc += {map_s}")
                if has_pred:
                    return f"_acc = {init}\nfor _x in {src_s}:\n    if {pred_s}:\n        {act}\nreturn _acc"
                return f"_acc = {init}\nfor _x in {src_s}:\n    {act}\nreturn _acc"
            if style == "while":
                init = "[]" if kind == "collect_list" else ("set()" if kind == "collect_set" else "0")
                act = f"_acc.append({map_s})" if kind == "collect_list" else (f"_acc.add({map_s})" if kind == "collect_set" else f"_acc += {map_s}")
                guard = f"    if {pred_s}:\n        {act}" if has_pred else f"    {act}"
                return f"_acc = {init}\n_i = 0\nwhile _i < len({src_s}):\n    _x = {src_s}[_i]\n{guard}\n    _i += 1\nreturn _acc"
        return f"return {SemanticMeaningIR._lower_expr_py(ir, bindings)}"

    @staticmethod
    def lower_to_javascript(ir: IRNode, *, fn_name: str = "fn", param_names: Sequence[str] = ("items",)) -> str:
        bindings = {f"$p{i}": name for i, name in enumerate(param_names)}
        bindings["$elem0"] = "_x"
        if ir.op == "STREAM_FOLD" and len(ir.args) == 4:
            kind, src_ir, pred_ir, map_ir = ir.args
            src_s = SemanticMeaningIR._lower_expr_js(src_ir, bindings)
            pred_s = SemanticMeaningIR._lower_expr_js(pred_ir, bindings)
            map_s = SemanticMeaningIR._lower_expr_js(map_ir, bindings)
            chain = src_s
            if pred_ir != IRNode("CONST", (True,)):
                chain = f"{chain}.filter((_x) => {pred_s})"
            if kind == "collect_list":
                if map_ir != IRNode("VAR", ("$elem0",)):
                    chain = f"{chain}.map((_x) => {map_s})"
                return f"function {fn_name}({', '.join(param_names)}) {{\n  return {chain};\n}}"
            if kind == "sum":
                return f"function {fn_name}({', '.join(param_names)}) {{\n  return {chain}.reduce((_a, _x) => _a + ({map_s}), 0);\n}}"
        return f"function {fn_name}({', '.join(param_names)}) {{\n  return {SemanticMeaningIR._lower_expr_js(ir, bindings)};\n}}"

    @staticmethod
    def lower_to_rust(ir: IRNode, *, fn_name: str = "compute", param_names: Sequence[str] = ("items",)) -> str:
        bindings = {f"$p{i}": name for i, name in enumerate(param_names)}
        bindings["$elem0"] = "_x"
        if ir.op == "STREAM_FOLD" and len(ir.args) == 4:
            kind, src_ir, pred_ir, map_ir = ir.args
            src_s = bindings.get(src_ir.args[0], "items") if src_ir.op == "VAR" else "items"
            pred_s = SemanticMeaningIR._lower_expr_js(pred_ir, {**bindings, "$elem0": "(*_x)"})
            map_s = SemanticMeaningIR._lower_expr_js(map_ir, bindings)
            chain = f"{src_s}.iter().copied()"
            if pred_ir != IRNode("CONST", (True,)):
                chain += f".filter(|_x| {pred_s})"
            if kind == "collect_list":
                chain += f".map(|_x| {map_s}).collect::<Vec<_>>()"
            elif kind == "sum":
                chain += f".map(|_x| {map_s}).sum()"
            return f"pub fn {fn_name}({src_s}: &[i64]) -> Vec<i64> {{\n    {chain}\n}}" if kind == "collect_list" else f"pub fn {fn_name}({src_s}: &[i64]) -> i64 {{\n    {chain}\n}}"
        return f"pub fn {fn_name}() {{}}"

    @staticmethod
    def _lower_expr_js(ir: IRNode, bindings: Mapping[str, str]) -> str:
        op, a = ir.op, ir.args
        if op == "CONST":
            if a[0] is None:
                return "null"
            if isinstance(a[0], bool):
                return "true" if a[0] else "false"
            return repr(a[0])
        if op == "VAR":
            return bindings.get(a[0], a[0])
        if op == "IS_NONE":
            return f"({SemanticMeaningIR._lower_expr_js(a[0], bindings)} === null)"
        if op == "IS_NOT_NONE":
            return f"({SemanticMeaningIR._lower_expr_js(a[0], bindings)} !== null)"
        if op == "LEN":
            return f"({SemanticMeaningIR._lower_expr_js(a[0], bindings)}).length"
        if op == "NOT":
            return f"(!{SemanticMeaningIR._lower_expr_js(a[0], bindings)})"
        if op == "NEG":
            return f"(-{SemanticMeaningIR._lower_expr_js(a[0], bindings)})"
        js_ops = {"ADD": "+", "SUB": "-", "MUL": "*", "DIV": "/", "MOD": "%", "EQ": "===", "NE": "!==", "LT": "<", "LE": "<="}
        if op in js_ops:
            return f"({SemanticMeaningIR._lower_expr_js(a[0], bindings)} {js_ops[op]} {SemanticMeaningIR._lower_expr_js(a[1], bindings)})"
        if op in ("AND", "OR"):
            j = " && " if op == "AND" else " || "
            return "(" + j.join(SemanticMeaningIR._lower_expr_js(x, bindings) for x in a) + ")"
        if op == "GUARDED_CHOICE":
            return f"({SemanticMeaningIR._lower_expr_js(a[0], bindings)} ? {SemanticMeaningIR._lower_expr_js(a[1], bindings)} : {SemanticMeaningIR._lower_expr_js(a[2], bindings)})"
        return SemanticMeaningIR._lower_expr_py(ir, bindings)

    @staticmethod
    def _lower_expr_py(ir: IRNode, bindings: Mapping[str, str]) -> str:
        op, a = ir.op, ir.args
        if op == "CONST":
            return repr(a[0])
        if op == "VAR":
            return bindings.get(a[0], a[0])
        if op == "ATTR":
            return f"({SemanticMeaningIR._lower_expr_py(a[0], bindings)}).{a[1]}"
        if op == "INDEX":
            return f"({SemanticMeaningIR._lower_expr_py(a[0], bindings)})[{SemanticMeaningIR._lower_expr_py(a[1], bindings)}]"
        if op == "LEN":
            return f"len({SemanticMeaningIR._lower_expr_py(a[0], bindings)})"
        if op == "BOOL":
            return f"bool({SemanticMeaningIR._lower_expr_py(a[0], bindings)})"
        if op == "IS_NONE":
            return f"({SemanticMeaningIR._lower_expr_py(a[0], bindings)} is None)"
        if op == "IS_NOT_NONE":
            return f"({SemanticMeaningIR._lower_expr_py(a[0], bindings)} is not None)"
        if op == "NOT":
            return f"(not {SemanticMeaningIR._lower_expr_py(a[0], bindings)})"
        if op == "NEG":
            return f"(-{SemanticMeaningIR._lower_expr_py(a[0], bindings)})"
        bin_syms = {
            "ADD": "+", "SUB": "-", "MUL": "*", "DIV": "/", "FDIV": "//", "MOD": "%",
            "EQ": "==", "NE": "!=", "LT": "<", "LE": "<=", "IS": "is", "IS_NOT": "is not",
            "IN": "in", "NOT_IN": "not in", "BITAND": "&", "BITOR": "|", "BITXOR": "^",
        }
        if op in bin_syms:
            return f"({SemanticMeaningIR._lower_expr_py(a[0], bindings)} {bin_syms[op]} {SemanticMeaningIR._lower_expr_py(a[1], bindings)})"
        if op in ("AND", "OR"):
            joiner = " and " if op == "AND" else " or "
            return "(" + joiner.join(SemanticMeaningIR._lower_expr_py(x, bindings) for x in a) + ")"
        if op == "GUARDED_CHOICE":
            return f"({SemanticMeaningIR._lower_expr_py(a[1], bindings)} if {SemanticMeaningIR._lower_expr_py(a[0], bindings)} else {SemanticMeaningIR._lower_expr_py(a[2], bindings)})"
        if op == "CALL":
            fn_name = bindings.get(a[0], a[0])
            args_s = ", ".join(SemanticMeaningIR._lower_expr_py(x, bindings) for x in a[1])
            return f"{fn_name}({args_s})"
        if op == "MCALL":
            recv_s = SemanticMeaningIR._lower_expr_py(a[0], bindings)
            args_s = ", ".join(SemanticMeaningIR._lower_expr_py(x, bindings) for x in a[2])
            return f"({recv_s}).{a[1]}({args_s})"
        if op == "LIST":
            return "[" + ", ".join(SemanticMeaningIR._lower_expr_py(x, bindings) for x in a) + "]"
        if op == "TUPLE":
            inner = ", ".join(SemanticMeaningIR._lower_expr_py(x, bindings) for x in a)
            return f"({inner},)" if len(a) == 1 else f"({inner})"
        return str(a[0]) if a else "None"


# =========================================================================== #
# LEAP 1: CROSS-FILE & CROSS-PROCESS CAUSAL DATA-FLOW GRAPH
# =========================================================================== #

@dataclass(frozen=True)
class CausalEdge:
    src_site: tuple[str, int]
    dst_site: tuple[str, int]
    kind: str  # INTRA_DEF_USE | CALL_ARG_FLOW | RETURN_VALUE_FLOW | HEAP_ATTR_FLOW | EXCEPTION_PROPAGATION
    symbol: str


@dataclass
class SiteProfile:
    rel_file: str
    lineno: int
    func_name: str
    fail_hits: int = 0
    pass_hits: int = 0
    fail_frames: list[dict[str, Any]] = field(default_factory=list)
    pass_frames: list[dict[str, Any]] = field(default_factory=list)
    fail_anomalies: list[str] = field(default_factory=list)
    crash_exceptions: list[str] = field(default_factory=list)
    in_crash_stack: bool = False
    backward_slice_distance: int = 999


class CausalDataFlowGraph:
    """Cross-file, multi-thread, and cross-subprocess value-lineage & anomaly localizer."""

    def __init__(self, worktree: pathlib.Path) -> None:
        self.worktree = pathlib.Path(worktree).resolve()
        self.sites: dict[tuple[str, int], SiteProfile] = {}
        self.edges: set[CausalEdge] = set()
        self._rev_adj: dict[tuple[str, int], list[CausalEdge]] = {}
        self.symptom_sites: list[tuple[str, int]] = []
        self.expected_exceptions: list[str] = []
        self.assertion_expected_literals: list[Any] = []
        self.cross_process_events: int = 0

    def add_edge(self, edge: CausalEdge) -> None:
        if edge.src_site == edge.dst_site:
            return
        if edge not in self.edges:
            self.edges.add(edge)
            self._rev_adj.setdefault(edge.dst_site, []).append(edge)

    def _compute_invariant_anomalies(self) -> None:
        for prof in self.sites.values():
            if not prof.pass_frames or not prof.fail_frames:
                continue
            common_keys = set(prof.pass_frames[0].keys())
            for pf in prof.pass_frames[1:]:
                common_keys &= set(pf.keys())
            for k in sorted(common_keys):
                p_vals = [pf[k] for pf in prof.pass_frames]
                p_types = {v.get("t", "?") for v in p_vals if isinstance(v, dict)}
                all_non_none = all(isinstance(v, dict) and v.get("t") != "NoneType" for v in p_vals)
                all_non_empty = all(
                    isinstance(v, dict) and v.get("len", 1) > 0
                    for v in p_vals
                    if isinstance(v, dict) and "len" in v
                ) and any(isinstance(v, dict) and "len" in v for v in p_vals)
                all_non_neg = all(
                    isinstance(v, dict) and isinstance(v.get("v"), (int, float)) and not isinstance(v.get("v"), bool) and v["v"] >= 0
                    for v in p_vals
                ) and any(isinstance(v, dict) and isinstance(v.get("v"), (int, float)) and not isinstance(v.get("v"), bool) for v in p_vals)

                for ff in prof.fail_frames:
                    fv = ff.get(k)
                    if not isinstance(fv, dict):
                        continue
                    ft = fv.get("t", "?")
                    if all_non_none and ft == "NoneType":
                        prof.fail_anomalies.append(f"{k}:NULL_ANOMALY")
                    elif p_types and ft not in p_types:
                        prof.fail_anomalies.append(f"{k}:TYPE_ANOMALY")
                    if all_non_empty and fv.get("len") == 0:
                        prof.fail_anomalies.append(f"{k}:EMPTY_ANOMALY")
                    if all_non_neg and isinstance(fv.get("v"), (int, float)) and not isinstance(fv.get("v"), bool) and fv["v"] < 0:
                        prof.fail_anomalies.append(f"{k}:NEGATIVE_ANOMALY")

    def _compute_backward_slice(self) -> None:
        seeds = list(dict.fromkeys(self.symptom_sites))
        if not seeds:
            # Seed at the LAST executed failing site(s) (closest to return/assertion symptom)
            seeds = [s for s, p in self.sites.items() if p.in_crash_stack] or list(self.sites.keys())[-6:]
        queue: list[tuple[tuple[str, int], int]] = [(s, 0) for s in seeds]
        best_dist: dict[tuple[str, int], int] = {s: 0 for s in seeds}
        head = 0
        while head < len(queue):
            cur, dist = queue[head]
            head += 1
            if cur in self.sites:
                self.sites[cur].backward_slice_distance = min(self.sites[cur].backward_slice_distance, dist)
            if dist >= 10:
                continue
            for edge in self._rev_adj.get(cur, ()):
                prev = edge.src_site
                if dist + 1 < best_dist.get(prev, 999):
                    best_dist[prev] = dist + 1
                    queue.append((prev, dist + 1))

    def rank_causal_sites(self, total_failing: int) -> list[dict[str, Any]]:
        self._compute_invariant_anomalies()
        self._compute_backward_slice()
        n_fail = max(1, total_failing)
        ranked: list[dict[str, Any]] = []
        for (rel_f, ln), prof in self.sites.items():
            if prof.fail_hits <= 0 and prof.backward_slice_distance >= 999:
                continue
            if prof.func_name == "<module>" and not prof.in_crash_stack:
                continue
            # Normalize loop hit counts against test-count scale (`eff_fail <= 1.5 * n_fail`) so a 40-iteration
            # utility loop (`__getattr__`, `Client.open`) cannot inflate Ochiai > 1.0 and drown out 1-hit domain branches.
            eff_fail = min(float(prof.fail_hits), float(n_fail) * 1.5)
            eff_pass = min(float(prof.pass_hits), max(float(n_fail) * 4.0, 20.0))
            denom = math.sqrt(n_fail * max(1.0, eff_fail + eff_pass))
            ochiai = eff_fail / denom if denom > 0 else 0.0
            fail_exclusivity = 0.28 * (prof.fail_hits / max(1, prof.fail_hits + prof.pass_hits))
            lineage_bonus = 0.55 * (0.82 ** prof.backward_slice_distance) if prof.backward_slice_distance < 999 else 0.0
            anomaly_bonus = min(0.75, 0.30 * len(set(prof.fail_anomalies)))
            stack_bonus = 0.35 if prof.in_crash_stack else 0.0
            # Gentle harness prior: in-package test client helpers (`*/test.py`, `*/testing.py`) execute on
            # every client request without being the domain target unless specifically crashed in stack.
            harness_penalty = (
                0.28
                if rel_f.endswith(("/test.py", "/testing.py")) and not prof.in_crash_stack and prof.pass_hits > prof.fail_hits * 2
                else 0.0
            )
            score = max(0.01, ochiai + fail_exclusivity + lineage_bonus + anomaly_bonus + stack_bonus - harness_penalty)
            ranked.append({
                "file": rel_f,
                "line": ln,
                "func": prof.func_name,
                "score": round(score, 4),
                "ochiai": round(ochiai, 4),
                "slice_distance": prof.backward_slice_distance,
                "anomalies": sorted(set(prof.fail_anomalies)),
                "in_crash_stack": prof.in_crash_stack,
                "fail_hits": prof.fail_hits,
                "pass_hits": prof.pass_hits,
            })
        ranked.sort(key=lambda r: (-r["score"], r["slice_distance"], r["pass_hits"], r["file"], r["line"]))
        # Diversify top slice across `(file, func)` so multi-line loops in one helper never starve rank-#2 files!
        primary: list[dict[str, Any]] = []
        overflow: list[dict[str, Any]] = []
        per_fn_counts: dict[tuple[str, str], int] = {}
        for row in ranked:
            fk = (row["file"], f"{row['func']}@{int(row['line']) // 40}")
            cnt = per_fn_counts.get(fk, 0)
            if cnt < 3:
                per_fn_counts[fk] = cnt + 1
                primary.append(row)
            else:
                overflow.append(row)
        return primary + overflow

    def rank_files(self, total_failing: int) -> list[str]:
        seen: dict[str, float] = {}
        for row in self.rank_causal_sites(total_failing):
            f = row["file"]
            seen[f] = max(seen.get(f, 0.0), row["score"])
        return [f for f, _ in sorted(seen.items(), key=lambda kv: (-kv[1], kv[0]))]

    def coupled_file_pairs(self) -> list[tuple[str, str, str]]:
        pairs: list[tuple[str, str, str]] = []
        seen: set[tuple[str, str]] = set()
        for e in self.edges:
            f1, f2 = e.src_site[0], e.dst_site[0]
            if f1 != f2 and (f1, f2) not in seen:
                seen.add((f1, f2))
                pairs.append((f1, f2, e.kind))
        return pairs


_TRACE_HELPER_SCRIPT = r'''
import importlib.util, json, os, pathlib, sys, threading, unittest

ROOT = pathlib.Path(os.environ["BRAIN_WORKTREE"]).resolve()
OUT_PATH = pathlib.Path(os.environ["BRAIN_TRACE_JSON"])
FAIL_NODES = json.loads(os.environ["BRAIN_FAIL_NODES"])
PASS_NODES = json.loads(os.environ["BRAIN_PASS_NODES"])

def _is_proj(fn):
    if not fn or fn.startswith("<"):
        return None
    try:
        rel = pathlib.Path(fn).resolve().relative_to(ROOT).as_posix()
    except Exception:
        return None
    parts = rel.split("/")
    if any(pt in (".git", "__pycache__", ".pytest_cache", ".venv", "venv", "tests", "test", "testing") for pt in parts):
        return None
    if parts[-1].startswith("test_") or parts[-1].endswith("_test.py") or parts[-1] == "conftest.py":
        return None
    return rel

def _snap_val(v):
    t = type(v).__name__
    d = {"t": t}
    if v is None or isinstance(v, (bool, int, float)):
        d["v"] = v
    elif isinstance(v, (str, bytes)):
        d["v"] = v[:120] if isinstance(v, str) else repr(v[:60])
        d["len"] = len(v)
    elif type(v) in (list, tuple, set, frozenset, dict):
        d["len"] = len(v)
        if type(v) in (list, tuple, set, frozenset) and len(v) > 0:
            try:
                first_el = next(iter(v))
                d["elem_t"] = type(first_el).__name__
                d["elem_mro"] = [c.__name__ for c in type(first_el).__mro__[:4] if c is not object]
            except Exception:
                pass
        try:
            d["repr"] = repr(v)[:120]
        except Exception:
            pass
    else:
        try:
            d["mro"] = [c.__name__ for c in type(v).__mro__[:4] if c is not object]
        except Exception:
            pass
        try:
            d["len"] = len(v)
        except Exception:
            pass
        try:
            attrs = {}
            def _enc_attr(val):
                if val is None or isinstance(val, (bool, int, float, str)):
                    return repr(val[:60] if isinstance(val, str) else val)
                try:
                    return {"r": repr(val)[:60], "b": bool(val), "t": type(val).__name__}
                except Exception:
                    return repr(val)[:60]

            v_dict = getattr(v, "__dict__", None)
            if isinstance(v_dict, dict):
                for k, val in list(v_dict.items())[:10]:
                    if isinstance(k, str) and not k.startswith("__") and not callable(val):
                        attrs[k] = _enc_attr(val)
            # Also capture `__slots__` and `@property` descriptors across MRO (`Authorization.type`, `.parameters`, etc.)
            if len(attrs) < 12:
                for cls_m in type(v).__mro__[:4]:
                    if cls_m is object:
                        continue
                    slots = getattr(cls_m, "__slots__", ())
                    if isinstance(slots, str):
                        slots = (slots,)
                    for sk in slots or ():
                        if isinstance(sk, str) and not sk.startswith("__") and sk not in attrs and len(attrs) < 12:
                            try:
                                sval = getattr(v, sk)
                                if not callable(sval):
                                    attrs[sk] = _enc_attr(sval)
                            except Exception:
                                pass
                    for pk, pdesc in list(getattr(cls_m, "__dict__", {}).items())[:24]:
                        if pk not in attrs and not pk.startswith("_") and isinstance(pdesc, property) and len(attrs) < 12:
                            try:
                                pval = getattr(v, pk)
                                if not callable(pval):
                                    attrs[pk] = _enc_attr(pval)
                            except Exception:
                                pass
            if attrs:
                d["attrs"] = attrs
            d["repr"] = repr(v)[:100]
        except Exception:
            d["repr"] = f"<{t}>"
    return d

def _exec_nodes_unittest(nodes):
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    by_file = {}
    for n in nodes:
        parts = n.split("::")
        by_file.setdefault(parts[0], []).append(parts[1:])
    for rel_tf, selectors in by_file.items():
        mod_path = (ROOT / rel_tf).resolve()
        mname = "_ut_" + rel_tf.replace("/", "_").replace(".", "_")
        spec = importlib.util.spec_from_file_location(mname, mod_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mname] = mod
        spec.loader.exec_module(mod)
        full = loader.loadTestsFromModule(mod)
        def _iter_cases(s):
            for x in s:
                if isinstance(x, unittest.TestSuite):
                    yield from _iter_cases(x)
                else:
                    yield x
        for case in _iter_cases(full):
            cls_n = type(case).__name__
            m_n = case._testMethodName
            if any((len(sel) == 2 and sel[0] == cls_n and sel[1] == m_n) or (len(sel) == 1 and sel[0] == m_n) or not sel for sel in selectors):
                suite.addTest(case)
    stream = open(os.devnull, "w")
    try:
        unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
    finally:
        stream.close()

def _run_traced(nodes, is_fail):
    hits = {}
    frames_out = {}
    edges = []
    crash_sites = []
    last_site = [None]
    attr_producers = {}
    last_ret_site = [None]

    def tracer(frame, event, arg):
        rel = _is_proj(frame.f_code.co_filename)
        if rel is None:
            return None
        ln = frame.f_lineno
        key = f"{rel}:{ln}"
        if event == "call":
            caller = frame.f_back
            if caller is not None:
                c_rel = _is_proj(caller.f_code.co_filename)
                if c_rel is not None:
                    edges.append([c_rel, caller.f_lineno, rel, ln, "CALL_ARG_FLOW", frame.f_code.co_name])
            return tracer
        if event == "line":
            hits[key] = hits.get(key, 0) + 1
            last_site[0] = [rel, ln]
            if last_ret_site[0] is not None and last_ret_site[0][0] != key:
                r_key, r_fn = last_ret_site[0]
                r_rel, r_ln = r_key.rsplit(":", 1)
                edges.append([r_rel, int(r_ln), rel, ln, "RETURN_VALUE_FLOW", r_fn])
                last_ret_site[0] = None
            lst = frames_out.setdefault(key, {"func": frame.f_code.co_name, "snaps": []})
            max_snaps = 6 if is_fail else 4
            if hits[key] <= (48 if is_fail else 8):
                sys.settrace(None)
                try:
                    snap = {}
                    for k, val in list(frame.f_locals.items())[:18]:
                        if k.startswith("__"):
                            continue
                        snap[k] = _snap_val(val)
                        if k == "self" or hasattr(val, "__dict__"):
                            oid = id(val)
                            try:
                                for ak, av in list(vars(val).items())[:12]:
                                    prev = attr_producers.get((oid, ak))
                                    cur_repr = repr(av)[:80]
                                    if prev is None or prev[2] != cur_repr:
                                        attr_producers[(oid, ak)] = (rel, ln, cur_repr)
                                    elif (prev[0], prev[1]) != (rel, ln):
                                        edges.append([prev[0], prev[1], rel, ln, "HEAP_ATTR_FLOW", ak])
                            except Exception:
                                pass
                    if len(lst["snaps"]) >= max_snaps:
                        lst["snaps"].pop(2)
                    lst["snaps"].append(snap)
                finally:
                    sys.settrace(tracer)
        elif event == "return":
            last_ret_site[0] = (key, frame.f_code.co_name)
        elif event == "exception" and is_fail:
            exc_cls_name = getattr(arg[0], "__name__", type(arg[0]).__name__) if arg and arg[0] else "Exception"
            crash_sites.append([rel, ln, exc_cls_name])
        return tracer

    if not nodes:
        return {"hits": hits, "frames": frames_out, "edges": edges, "crash": crash_sites, "last": None}
    has_pytest = importlib.util.find_spec("pytest") is not None
    if has_pytest:
        import pytest
        uses_hyp = any(
            (ROOT / n.split("::")[0]).is_file()
            and "hypothesis" in (ROOT / n.split("::")[0]).read_text(encoding="utf-8", errors="ignore")
            for n in nodes[:4]
        )
        extra_p = [] if uses_hyp else ["-p", "no:hypothesis"]

        class _CallOnlyTracePlugin:
            def pytest_runtest_call(self, item):
                os.environ["BRAIN_CHILD_ACTIVE"] = "1"
                threading.settrace(tracer)
                sys.settrace(tracer)

            def pytest_runtest_teardown(self, item, nextitem):
                sys.settrace(None)
                threading.settrace(None)
                os.environ["BRAIN_CHILD_ACTIVE"] = "0"

        try:
            pytest.main([
                *nodes, "-q", "--tb=no",
                f"--rootdir={ROOT}",
                "-p", "no:cacheprovider", "-p", "no:xprocess", *extra_p,
                "-o", "addopts=", "-W", "default",
            ], plugins=[_CallOnlyTracePlugin()])
        finally:
            sys.settrace(None)
            threading.settrace(None)
            os.environ["BRAIN_CHILD_ACTIVE"] = "0"
    else:
        os.environ["BRAIN_CHILD_ACTIVE"] = "1"
        threading.settrace(tracer)
        sys.settrace(tracer)
        try:
            _exec_nodes_unittest(nodes)
        finally:
            sys.settrace(None)
            threading.settrace(None)
            os.environ["BRAIN_CHILD_ACTIVE"] = "0"
    return {"hits": hits, "frames": frames_out, "edges": edges, "crash": crash_sites, "last": last_site[0]}

fail_data = _run_traced(FAIL_NODES, True)
pass_data = _run_traced(PASS_NODES, False)
OUT_PATH.write_text(json.dumps({"fail": fail_data, "pass": pass_data}), encoding="utf-8")
'''

_CHILD_SITECUSTOMIZE = r'''
import atexit, json, os, pathlib, sys, threading
_root_env = os.environ.get("BRAIN_WORKTREE")
_cdir_env = os.environ.get("BRAIN_CHILD_TRACE_DIR")
if _root_env and _cdir_env and os.environ.get("BRAIN_CHILD_ACTIVE") == "1":
    _ROOT = pathlib.Path(_root_env).resolve()
    _CDIR = pathlib.Path(_cdir_env)
    _HITS = {}
    def _c_is_proj(fn):
        if not fn or fn.startswith("<"):
            return None
        try:
            rel = pathlib.Path(fn).resolve().relative_to(_ROOT).as_posix()
        except Exception:
            return None
        parts = rel.split("/")
        if any(pt in (".git", "__pycache__", "tests", "test", "testing") for pt in parts):
            return None
        if parts[-1].startswith("test_") or parts[-1] == "conftest.py":
            return None
        return rel
    def _c_trace(frame, event, arg):
        rel = _c_is_proj(frame.f_code.co_filename)
        if rel is None:
            return None
        if event == "line":
            k = f"{rel}:{frame.f_lineno}"
            _HITS[k] = _HITS.get(k, 0) + 1
        return _c_trace
    def _dump_child():
        if _HITS:
            try:
                (_CDIR / f"child_{os.getpid()}.json").write_text(json.dumps({"hits": _HITS}), encoding="utf-8")
            except Exception:
                pass
    atexit.register(_dump_child)
    threading.settrace(_c_trace)
    sys.settrace(_c_trace)
'''


def _add_intra_ast_def_use_edges(graph: CausalDataFlowGraph, rel_file: str, abs_file: pathlib.Path) -> None:
    try:
        tree = ast.parse(abs_file.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        last_def: dict[str, int] = {}
        for arg in fn.args.args + fn.args.kwonlyargs:
            last_def[arg.arg] = fn.lineno
        for stmt in ast.walk(fn):
            if not hasattr(stmt, "lineno"):
                continue
            ln = stmt.lineno
            if isinstance(stmt, ast.Name) and isinstance(stmt.ctx, ast.Load):
                d_ln = last_def.get(stmt.id)
                if d_ln is not None and d_ln != ln:
                    graph.add_edge(CausalEdge((rel_file, d_ln), (rel_file, ln), "INTRA_DEF_USE", stmt.id))
            elif isinstance(stmt, ast.Name) and isinstance(stmt.ctx, ast.Store):
                last_def[stmt.id] = ln


def _parse_assertion_expected_literals(pytest_output: str) -> list[Any]:
    """Extract concrete expected RHS literals from `AssertionError: ... != <lit>` or `assert <act> == <lit>`."""
    expected: list[Any] = []
    for pat in (
        r"AssertionError:\s*.+?\s*!=\s*(.+)$",
        r"E\s+assert\s+.+?\s*==\s*(.+)$",
    ):
        for m in re.finditer(pat, pytest_output, re.MULTILINE):
            rhs = m.group(1).strip()
            try:
                val = ast.literal_eval(rhs)
                if val not in expected:
                    expected.append(val)
            except Exception:
                pass
    return expected[:6]


def _normalize_node_ids(nodes: Sequence[str], default_test_file: str = "") -> list[str]:
    base_file = default_test_file.split("::")[0] if default_test_file else ""
    base_name = os.path.basename(base_file) if base_file.startswith("/") else ""
    out: list[str] = []
    for n in nodes:
        if "::" in n:
            head, tail = n.split("::", 1)
            if base_name and (head == base_name or head.endswith("/" + base_name)):
                out.append(f"{base_file}::{tail}")
            else:
                out.append(n)
            continue
        m_ut = re.match(r"^([A-Za-z_]\w*)\s+\((?:[\w\.]+\.)?([A-Za-z_]\w*)(?:\.\1)?\)$", n.strip())
        if m_ut and base_file:
            meth_part, cls_part = m_ut.group(1), m_ut.group(2)
            out.append(f"{base_file}::{cls_part}::{meth_part}")
        elif base_file and "." in n and not n.endswith(".py"):
            cls_part, meth_part = n.rsplit(".", 1)
            cls_part = cls_part.rsplit(".", 1)[-1]
            out.append(f"{base_file}::{cls_part}::{meth_part}")
        elif base_file and not n.endswith(".py"):
            out.append(f"{base_file}::{n}")
        else:
            out.append(n)
    return out


def collect_causal_dataflow_graph(
    worktree: pathlib.Path,
    failing_nodes: Sequence[str],
    passing_nodes: Sequence[str],
    *,
    default_test_file: str = "",
    pytest_output: str = "",
    python_exe: str | None = None,
    timeout_s: float = 25.0,
) -> CausalDataFlowGraph:
    """Build cross-file, multi-thread, and cross-subprocess `CausalDataFlowGraph`."""
    wt = pathlib.Path(worktree).resolve()
    graph = CausalDataFlowGraph(wt)
    py = python_exe or sys.executable
    failing_nodes = _normalize_node_ids(failing_nodes, default_test_file)
    passing_nodes = _normalize_node_ids(passing_nodes, default_test_file)

    for m in re.finditer(
        r"(?:DID NOT RAISE\s*(?:<class ')?([A-Za-z_][A-Za-z0-9_.]*)|([A-Za-z_][A-Za-z0-9_.]*)\s+not raised|(?:pytest\.raises|assertRaises)\(\s*([A-Za-z_][A-Za-z0-9_.]*))",
        pytest_output,
    ):
        exc = (m.group(1) or m.group(2) or m.group(3) or "").split(".")[-1]
        if exc and exc[0].isupper() and exc not in graph.expected_exceptions:
            graph.expected_exceptions.append(exc)
    graph.assertion_expected_literals = _parse_assertion_expected_literals(pytest_output)

    for m in re.finditer(r"([\w./\\-]+\.py):(\d+):", pytest_output):
        cand = (wt / m.group(1)).resolve()
        try:
            rel = cand.relative_to(wt).as_posix()
            parts = rel.split("/")
            if not any(pt in ("tests", "test", "testing") for pt in parts) and not parts[-1].startswith("test_"):
                graph.symptom_sites.append((rel, int(m.group(2))))
        except ValueError:
            pass

    with tempfile.TemporaryDirectory(prefix="brain_dfg_") as td:
        tdir = pathlib.Path(td)
        out_json = tdir / "trace.json"
        child_dir = tdir / "children"
        child_dir.mkdir(parents=True, exist_ok=True)
        hook_dir = tdir / "sitehook"
        hook_dir.mkdir(parents=True, exist_ok=True)
        (hook_dir / "sitecustomize.py").write_text(_CHILD_SITECUSTOMIZE, encoding="utf-8")
        helper = tdir / "run_trace.py"
        helper.write_text(_TRACE_HELPER_SCRIPT, encoding="utf-8")

        py_paths = [str(hook_dir)]
        if (wt / "src").is_dir():
            py_paths.append(str(wt / "src"))
        py_paths.append(str(wt))
        if os.environ.get("PYTHONPATH"):
            py_paths.append(os.environ["PYTHONPATH"])

        env = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join(py_paths),
            "PYTHONDONTWRITEBYTECODE": "1",
            "BRAIN_WORKTREE": str(wt),
            "BRAIN_TRACE_JSON": str(out_json),
            "BRAIN_CHILD_TRACE_DIR": str(child_dir),
            "BRAIN_CHILD_ACTIVE": "0",
            "BRAIN_FAIL_NODES": json.dumps(list(failing_nodes[:6])),
            "BRAIN_PASS_NODES": json.dumps(
                sorted(
                    passing_nodes,
                    key=lambda pn: (
                        -len(
                            set(re.findall(r"[a-z0-9]+", pn.lower()))
                            & {tok for fn in failing_nodes[:6] for tok in re.findall(r"[a-z0-9]+", fn.lower())}
                        ),
                        pn,
                    ),
                )[:10]
            ),
        }
        try:
            subprocess.run(
                [py, str(helper)],
                cwd=str(wt),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                timeout=timeout_s,
                env=env,
            )
        except subprocess.TimeoutExpired:
            pass

        if out_json.is_file():
            raw = json.loads(out_json.read_text(encoding="utf-8"))
            for phase, is_fail in (("fail", True), ("pass", False)):
                pdata = raw.get(phase) or {}
                frames_map = pdata.get("frames") or {}
                for key, count in (pdata.get("hits") or {}).items():
                    rel_f, ln_s = key.rsplit(":", 1)
                    ln = int(ln_s)
                    finfo = frames_map.get(key) or {}
                    prof = graph.sites.setdefault(
                        (rel_f, ln),
                        SiteProfile(rel_file=rel_f, lineno=ln, func_name=finfo.get("func", "")),
                    )
                    if is_fail:
                        prof.fail_hits += int(count)
                        prof.fail_frames.extend(finfo.get("snaps") or [])
                    else:
                        prof.pass_hits += int(count)
                        prof.pass_frames.extend(finfo.get("snaps") or [])
                for e in (pdata.get("edges") or []):
                    graph.add_edge(CausalEdge((e[0], int(e[1])), (e[2], int(e[3])), str(e[4]), str(e[5])))
                if is_fail:
                    for cs in (pdata.get("crash") or []):
                        site = (str(cs[0]), int(cs[1]))
                        if site in graph.sites:
                            graph.sites[site].in_crash_stack = True
                            if len(cs) >= 3:
                                graph.sites[site].crash_exceptions.append(str(cs[2]))
                        graph.symptom_sites.append(site)
                    last_s = pdata.get("last")
                    if isinstance(last_s, list) and len(last_s) == 2:
                        graph.symptom_sites.append((str(last_s[0]), int(last_s[1])))

        for cp in sorted(child_dir.glob("child_*.json")):
            try:
                cdata = json.loads(cp.read_text(encoding="utf-8"))
                for key, count in (cdata.get("hits") or {}).items():
                    rel_f, ln_s = key.rsplit(":", 1)
                    ln = int(ln_s)
                    prof = graph.sites.setdefault(
                        (rel_f, ln), SiteProfile(rel_file=rel_f, lineno=ln, func_name="<subprocess>")
                    )
                    prof.fail_hits += int(count)
                    graph.cross_process_events += int(count)
            except (OSError, ValueError, KeyError):
                pass

    # Always ensure exact traceback / symptom sites from pytest `--tb=short` are present in `graph.sites`
    # even if `sys.settrace` hit `timeout_s` on a heavy template/compiler test file!
    for sym_rel, sym_ln in list(graph.symptom_sites):
        if (sym_rel, sym_ln) not in graph.sites and (wt / sym_rel).is_file():
            fn_nm = ""
            try:
                t_sym = ast.parse((wt / sym_rel).read_text(encoding="utf-8", errors="ignore"))
                for n_sym in ast.walk(t_sym):
                    if isinstance(n_sym, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if n_sym.lineno <= sym_ln <= getattr(n_sym, "end_lineno", n_sym.lineno):
                            fn_nm = n_sym.name
            except SyntaxError:
                pass
            prof_sym = graph.sites.setdefault(
                (sym_rel, sym_ln),
                SiteProfile(rel_file=sym_rel, lineno=sym_ln, func_name=fn_nm),
            )
            prof_sym.fail_hits = max(1, prof_sym.fail_hits)
            prof_sym.in_crash_stack = True

    for rel_f in {rf for (rf, _) in graph.sites}:
        _add_intra_ast_def_use_edges(graph, rel_f, wt / rel_f)

    if not graph.sites:
        test_files = sorted({n.split("::")[0] for n in failing_nodes if n.split("::")[0].endswith(".py")})
        summaries = isg.IncrementalSemanticGraph(wt).load_summaries(".")
        called_names: set[str] = set()
        for tf in test_files:
            tp = wt / tf
            if not tp.is_file():
                continue
            try:
                t_tree = ast.parse(tp.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for n in ast.walk(t_tree):
                if isinstance(n, ast.ImportFrom):
                    for a in n.names:
                        called_names.add(a.name)
                elif isinstance(n, ast.Call):
                    if isinstance(n.func, ast.Name):
                        called_names.add(n.func.id)
                    elif isinstance(n.func, ast.Attribute):
                        called_names.add(n.func.attr)
        for rel_p, info in sorted(summaries.items()):
            parts = rel_p.split("/")
            if any(pt in ("tests", "test", "testing") for pt in parts) or parts[-1].startswith("test_"):
                continue
            for d in info.get("definitions") or []:
                d_name = str(d.get("name") or "")
                d_line = int(d.get("lineno") or 1)
                if d_name in called_names:
                    graph.sites[(rel_p, d_line)] = SiteProfile(
                        rel_file=rel_p, lineno=d_line, func_name=d_name, fail_hits=1
                    )
    return graph


# =========================================================================== #
# LEAP 4A: EXECUTABLE PROGRAM MENTAL MODELS (MICROSECOND FRAME + 2ms CoW FORK)
# =========================================================================== #

_SAFE_PURE_BUILTINS: dict[str, Any] = {
    "abs": abs, "all": all, "any": any, "bool": bool, "bytes": bytes,
    "dict": dict, "divmod": divmod, "enumerate": enumerate, "float": float,
    "frozenset": frozenset, "getattr": getattr, "hasattr": hasattr, "int": int,
    "isinstance": isinstance, "issubclass": issubclass, "len": len, "list": list,
    "max": max, "min": min, "ord": ord, "chr": chr, "range": range, "repr": repr,
    "reversed": reversed, "round": round, "set": set, "slice": slice,
    "sorted": sorted, "str": str, "sum": sum, "tuple": tuple, "type": type, "zip": zip,
    "None": None, "True": True, "False": False,
    "ValueError": ValueError, "TypeError": TypeError, "KeyError": KeyError, "IndexError": IndexError,
}

_PURE_STR_METHODS: tuple[str, ...] = (
    "strip", "lstrip", "rstrip", "lower", "upper", "isdigit", "isalpha",
    "isalnum", "startswith", "endswith", "split", "rsplit", "splitlines",
)


class _OpaqueFalsyObject:
    """Preserves exact runtime `len() == 0` / falsy-yet-non-None object behavior in mental frames!"""
    def __init__(self, attrs: Mapping[str, Any], length: int | None = None) -> None:
        for k, v in attrs.items():
            setattr(self, k, v)
        self._len = length

    def __bool__(self) -> bool:
        return True if self._len is None else (self._len > 0)


def _rehydrate_frame(snap: Mapping[str, Any]) -> dict[str, Any]:
    env: dict[str, Any] = {}
    for k, meta in snap.items():
        if not isinstance(meta, dict):
            env[k] = meta
            continue
        if "v" in meta:
            env[k] = meta["v"]
        elif meta.get("attrs") and meta.get("t") not in ("list", "tuple", "set", "frozenset", "dict", "str", "bytes", "int", "float", "bool", "NoneType"):
            attrs = meta.get("attrs") or {}
            parsed_attrs = {}
            for ak, av in attrs.items():
                if isinstance(av, dict) and "b" in av:
                    try:
                        parsed_attrs[ak] = ast.literal_eval(str(av.get("r", "")))
                    except Exception:
                        parsed_attrs[ak] = _OpaqueFalsyObject({}, length=1 if av.get("b") else 0)
                else:
                    try:
                        parsed_attrs[ak] = ast.literal_eval(av)
                    except Exception:
                        parsed_attrs[ak] = av
            env[k] = _OpaqueFalsyObject(parsed_attrs, length=meta.get("len"))
        elif "repr" in meta:
            try:
                env[k] = ast.literal_eval(meta["repr"])
            except Exception:
                attrs = meta.get("attrs") or {}
                parsed_attrs = {}
                for ak, av in attrs.items():
                    try:
                        parsed_attrs[ak] = ast.literal_eval(av)
                    except Exception:
                        parsed_attrs[ak] = av
                env[k] = _OpaqueFalsyObject(parsed_attrs, length=meta.get("len"))
    return env


class ProgramStateMentalModel:
    """Tier-1 Sub-Millisecond In-Memory Frame & Counterfactual Boundary State Simulator."""

    def __init__(
        self,
        fail_snaps: Sequence[Mapping[str, Any]],
        pass_snaps: Sequence[Mapping[str, Any]],
        *,
        extra_globals: Mapping[str, Any] | None = None,
    ) -> None:
        self.fail_envs = [_rehydrate_frame(s) for s in fail_snaps]
        self.pass_envs = [_rehydrate_frame(s) for s in pass_snaps]
        self.globals_ns = {"__builtins__": _SAFE_PURE_BUILTINS, **dict(extra_globals or {})}
        self.simulations_run = 0
        self.candidates_pruned = 0

    def generate_counterfactual_boundaries(self, var_names: Sequence[str]) -> list[dict[str, Any]]:
        if not self.pass_envs and not self.fail_envs:
            return []
        base = dict((self.pass_envs or self.fail_envs)[0])
        boundaries: list[dict[str, Any]] = []
        for v in var_names[:4]:
            if v not in base:
                continue
            cur = base[v]
            alts: list[Any] = [None]
            if isinstance(cur, bool):
                alts.extend([True, False])
            elif isinstance(cur, (int, float)):
                alts.extend([0, 1, -1])
            elif isinstance(cur, str):
                alts.extend(["", " ", "0", cur.strip() if cur else "a"])
            elif isinstance(cur, (list, tuple)):
                ctor = tuple if isinstance(cur, tuple) else list
                alts.extend([ctor(), ctor([cur[0]]) if cur else ctor([0]), ctor([cur[0], cur[0]]) if cur else ctor([0, 0])])
            for alt in alts[:4]:
                b_env = copy.deepcopy(base)
                b_env[v] = alt
                boundaries.append(b_env)
        return boundaries

    def eval_expr_vector(
        self,
        code_str: str,
        envs: Sequence[Mapping[str, Any]] | None = None,
    ) -> tuple[bool, tuple[Any, ...]]:
        self.simulations_run += 1
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                compiled = compile(code_str, "<mental_sim>", "eval")
        except SyntaxError:
            self.candidates_pruned += 1
            return False, ()
        target_envs = envs if envs is not None else (*self.fail_envs, *self.pass_envs)
        out: list[Any] = []
        for env in target_envs:
            loc = copy.deepcopy(dict(env))
            try:
                val = eval(compiled, self.globals_ns, loc)  # noqa: S307
                out.append(self._freeze_sig(val))
            except Exception as exc:
                out.append(("__EXC__", type(exc).__name__))
        return True, tuple(out)

    @staticmethod
    def _freeze_sig(val: Any, depth: int = 0) -> Any:
        if depth > 3:
            return "..."
        if val is None or isinstance(val, (bool, int, str, bytes)):
            return (type(val).__name__, val)
        if isinstance(val, float):
            return ("float", round(val, 8))
        if isinstance(val, (list, tuple)):
            return (type(val).__name__, tuple(ProgramStateMentalModel._freeze_sig(x, depth + 1) for x in val[:16]))
        if isinstance(val, (set, frozenset)):
            return (type(val).__name__, tuple(sorted(repr(x) for x in list(val)[:16])))
        if isinstance(val, dict):
            return ("dict", tuple(sorted((repr(k), ProgramStateMentalModel._freeze_sig(v, depth + 1)) for k, v in list(val.items())[:16])))
        return (type(val).__name__, repr(val)[:80])


class _InMemorySourceLoader(importlib.abc.Loader):
    def __init__(self, fullname: str, abs_path: str, source: str) -> None:
        self.fullname = fullname
        self.abs_path = abs_path
        self.source = source

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> types.ModuleType | None:
        return None

    def exec_module(self, module: types.ModuleType) -> None:
        module.__file__ = self.abs_path
        code = compile(self.source, self.abs_path, "exec")
        exec(code, module.__dict__)  # noqa: S307


class _InMemoryPatchFinder(importlib.abc.MetaPathFinder):
    """Intercepts lazy imports in forked CoW children so patched sources load from RAM (`0` disk writes)."""

    def __init__(self, patches_by_abs: Mapping[str, str]) -> None:
        self.patches_by_abs = dict(patches_by_abs)

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: types.ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        # Delegate path resolution to standard PathFinder, then swap loader if file is patched!
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec and spec.origin:
            try:
                resolved = str(pathlib.Path(spec.origin).resolve())
            except OSError:
                return None
            if resolved in self.patches_by_abs:
                loader = _InMemorySourceLoader(fullname, resolved, self.patches_by_abs[resolved])
                return importlib.machinery.ModuleSpec(
                    fullname, loader, origin=resolved, is_package=spec.submodule_search_locations is not None
                )
        return None


def _apply_ram_patches_in_child(worktree: pathlib.Path, file_patches: Mapping[str, str]) -> bool:
    """Hot-swap modified functions/methods/classes/constants in RAM + install lazy-import RAM finder."""
    loaded_by_path: dict[pathlib.Path, list[types.ModuleType]] = {}
    for mod in list(sys.modules.values()):
        mf = getattr(mod, "__file__", None)
        if mf:
            try:
                loaded_by_path.setdefault(pathlib.Path(mf).resolve(), []).append(mod)
            except OSError:
                pass

    patches_by_abs: dict[str, str] = {}
    for rel_path, new_source in file_patches.items():
        abs_path = (worktree / rel_path).resolve()
        try:
            code_obj = compile(new_source, str(abs_path), "exec")
        except SyntaxError:
            return False
        patches_by_abs[str(abs_path)] = new_source
        mods = loaded_by_path.get(abs_path, [])
        for mod in mods:
            fresh_ns: dict[str, Any] = dict(mod.__dict__)
            try:
                exec(code_obj, fresh_ns)  # noqa: S307
            except Exception:
                return False
            replacements: list[tuple[Any, Any]] = []
            for k, new_val in fresh_ns.items():
                if k.startswith("__") and k not in ("__all__",):
                    continue
                old_val = mod.__dict__.get(k)
                if isinstance(old_val, types.FunctionType) and isinstance(new_val, types.FunctionType):
                    if old_val.__code__.co_freevars == new_val.__code__.co_freevars:
                        old_val.__code__ = new_val.__code__
                        old_val.__defaults__ = new_val.__defaults__
                        old_val.__kwdefaults__ = new_val.__kwdefaults__
                        fresh_ns[k] = old_val
                        continue
                    replacements.append((old_val, new_val))
                elif isinstance(old_val, type) and isinstance(new_val, type):
                    fresh_ns[k] = old_val
                    for mk, mv in new_val.__dict__.items():
                        if mk in ("__dict__", "__weakref__", "__doc__"):
                            continue
                        omv = old_val.__dict__.get(mk)
                        if isinstance(omv, types.FunctionType) and isinstance(mv, types.FunctionType):
                            if omv.__code__.co_freevars == mv.__code__.co_freevars:
                                omv.__code__ = mv.__code__
                                omv.__defaults__ = mv.__defaults__
                                omv.__kwdefaults__ = mv.__kwdefaults__
                                continue
                        try:
                            setattr(old_val, mk, mv)
                        except (AttributeError, TypeError):
                            pass
                    continue
                elif callable(old_val) and hasattr(old_val, "cache_clear") and hasattr(new_val, "__wrapped__"):
                    try:
                        old_val.cache_clear()
                    except Exception:
                        pass
                elif old_val is not new_val and old_val is not None:
                    replacements.append((old_val, new_val))
                mod.__dict__[k] = new_val

            # Clear any module-level lru_cache memo tables that could cache stale pre-patch outputs!
            for mv_item in list(mod.__dict__.values()):
                if callable(mv_item) and hasattr(mv_item, "cache_clear"):
                    try:
                        mv_item.cache_clear()
                    except Exception:
                        pass

            if replacements:
                for other in list(sys.modules.values()):
                    od = getattr(other, "__dict__", None)
                    if not isinstance(od, dict) or other is mod:
                        continue
                    for ok, ov in list(od.items()):
                        for old_obj, new_obj in replacements:
                            if ov is old_obj:
                                od[ok] = new_obj

    if patches_by_abs:
        sys.meta_path.insert(0, _InMemoryPatchFinder(patches_by_abs))
    return True


_ZYGOTE_DAEMON_SCRIPT = r'''
import copy, importlib.util, json, os, pathlib, select, struct, sys, time, unittest

WORKTREE = pathlib.Path(os.environ["BRAIN_ZYGOTE_WORKTREE"]).resolve()
FAIL_NODES = json.loads(os.environ["BRAIN_ZYGOTE_FAIL_NODES"])
PASS_NODES = json.loads(os.environ["BRAIN_ZYGOTE_PASS_NODES"])
REQ_FD = int(os.environ["BRAIN_ZYGOTE_REQ_FD"])
RESP_FD = int(os.environ["BRAIN_ZYGOTE_RESP_FD"])
HELPER_PATH = os.environ["BRAIN_ZYGOTE_MODULE_FILE"]

_spec = importlib.util.spec_from_file_location("_fp_mc", HELPER_PATH)
_fp = importlib.util.module_from_spec(_spec)
sys.modules["_fp_mc"] = _fp
_spec.loader.exec_module(_fp)

def _send(fd, obj):
    raw = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    os.write(fd, struct.pack(">I", len(raw)) + raw)

def _recv(fd):
    hdr = bytearray()
    while len(hdr) < 4:
        ch = os.read(fd, 4 - len(hdr))
        if not ch:
            return None
        hdr.extend(ch)
    (sz,) = struct.unpack(">I", bytes(hdr))
    body = bytearray()
    while len(body) < sz:
        ch = os.read(fd, sz - len(body))
        if not ch:
            return None
        body.extend(ch)
    return json.loads(body.decode("utf-8"))

def _eval_one_patch_in_child(w_fd, patches, capture_site, run_one_fn, fail_ids, pass_ids):
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 1)
    os.dup2(devnull, 2)
    os.close(devnull)
    cex_frames = []
    if capture_site:
        c_rel, c_ln = capture_site[0], int(capture_site[1])
        c_abs = str((WORKTREE / c_rel).resolve())
        def _cex_tr(frame, event, arg):
            if frame.f_code.co_filename != c_abs:
                return None
            if event == "line" and frame.f_lineno == c_ln and len(cex_frames) < 4:
                snap = {}
                for k, v in list(frame.f_locals.items())[:16]:
                    if not k.startswith("__"):
                        if v is None or isinstance(v, (bool, int, float, str)):
                            snap[k] = {"t": type(v).__name__, "v": v[:120] if isinstance(v, str) else v}
                        else:
                            snap[k] = {"t": type(v).__name__, "repr": repr(v)[:100]}
                cex_frames.append(snap)
            return _cex_tr
    else:
        _cex_tr = None

    if not _fp._apply_ram_patches_in_child(WORKTREE, patches):
        _send(w_fd, {"ok": False, "fail_passed": False, "passed_fail_mask": [False] * len(fail_ids), "reason": "SYNTAX_OR_EXEC_ERROR"})
        os.close(w_fd)
        os._exit(0)

    passed_fail_mask = []
    fail_msg = ""
    for fid in fail_ids:
        passed, msg = run_one_fn(fid, None)
        passed_fail_mask.append(bool(passed))
        if not passed and not fail_msg:
            fail_msg = msg
        # When >6 failing tests exist, short-circuit after first failure to stay <2ms
        if not passed and len(fail_ids) > 6:
            passed_fail_mask.extend([False] * (len(fail_ids) - len(passed_fail_mask)))
            break

    fail_ok = all(passed_fail_mask) and len(passed_fail_mask) == len(fail_ids)
    if not fail_ok:
        _send(w_fd, {
            "ok": False,
            "fail_passed": False,
            "passed_fail_mask": passed_fail_mask,
            "msg": fail_msg,
        })
        os.close(w_fd)
        os._exit(0)

    regressed = None
    for idx, pid_node in enumerate(pass_ids):
        nxt = pass_ids[idx + 1] if idx + 1 < len(pass_ids) else None
        if _cex_tr is not None:
            cex_frames.clear()
            sys.settrace(_cex_tr)
        try:
            passed, _ = run_one_fn(pid_node, nxt)
        finally:
            if _cex_tr is not None:
                sys.settrace(None)
        if not passed:
            regressed = pid_node
            break

    _send(w_fd, {
        "ok": regressed is None,
        "fail_passed": True,
        "passed_fail_mask": passed_fail_mask,
        "regressed_node": regressed,
        "counterexample_frames": cex_frames if regressed else [],
    })
    os.close(w_fd)
    os._exit(0)


def _serve_fork_loop(run_one_fn, fail_ids, pass_ids):
    _send(RESP_FD, {"ready": True, "fail_count": len(fail_ids), "pass_count": len(pass_ids)})
    while True:
        req = _recv(REQ_FD)
        if req is None or req.get("cmd") == "quit":
            break
        cmd = req.get("cmd", "sim")
        capture_site = req.get("capture_site")
        timeout_s = float(req.get("timeout_s", 3.5))

        if cmd == "batch":
            batch_patches = list(req.get("batch_patches") or [])
            concurrency = max(1, min(16, int(req.get("concurrency", 8))))
            t_batch = time.perf_counter()
            out_results = [None] * len(batch_patches)
            for w_start in range(0, len(batch_patches), concurrency):
                wave = batch_patches[w_start : w_start + concurrency]
                active = {}
                bufs = {}
                for off, p_map in enumerate(wave):
                    r_fd, w_fd = os.pipe()
                    t0 = time.perf_counter()
                    pid = os.fork()
                    if pid == 0:
                        os.close(r_fd)
                        _eval_one_patch_in_child(w_fd, p_map or {}, capture_site, run_one_fn, fail_ids, pass_ids)
                    else:
                        os.close(w_fd)
                        active[r_fd] = (pid, w_start + off, t0)
                        bufs[r_fd] = bytearray()
                deadline = time.perf_counter() + timeout_s
                while active:
                    rem = max(0.0, deadline - time.perf_counter())
                    rdy, _, _ = select.select(list(active.keys()), [], [], rem)
                    if not rdy:
                        for fd, (pid, idx_b, t0) in list(active.items()):
                            try:
                                os.kill(pid, 9)
                            except OSError:
                                pass
                            os.waitpid(pid, 0)
                            os.close(fd)
                            out_results[idx_b] = {"ok": False, "fail_passed": False, "timeout": True, "ms": round((time.perf_counter() - t0) * 1000, 2)}
                        active.clear()
                        break
                    for fd in rdy:
                        ch = os.read(fd, 65536)
                        if ch:
                            bufs[fd].extend(ch)
                            continue
                        pid, idx_b, t0 = active.pop(fd)
                        os.close(fd)
                        os.waitpid(pid, 0)
                        raw_b = bytes(bufs[fd])
                        if len(raw_b) >= 4:
                            (sz_b,) = struct.unpack(">I", raw_b[:4])
                            res_b = json.loads(raw_b[4 : 4 + sz_b].decode("utf-8"))
                        else:
                            res_b = {"ok": False, "fail_passed": False}
                        res_b["ms"] = round((time.perf_counter() - t0) * 1000, 2)
                        out_results[idx_b] = res_b
                if any(r and r.get("ok") for r in out_results[: w_start + len(wave)]):
                    break
            _send(RESP_FD, {
                "results": [r or {"ok": False, "fail_passed": False, "skipped": True, "ms": 0.0} for r in out_results],
                "wall_ms": round((time.perf_counter() - t_batch) * 1000, 2),
            })
            continue

        patches = req.get("patches") or {}
        r_fd, w_fd = os.pipe()
        t0 = time.perf_counter()
        pid = os.fork()
        if pid == 0:
            os.close(r_fd)
            _eval_one_patch_in_child(w_fd, patches, capture_site, run_one_fn, fail_ids, pass_ids)
        else:
            os.close(w_fd)
            ready, _, _ = select.select([r_fd], [], [], timeout_s)
            if not ready:
                try:
                    os.kill(pid, 9)
                except OSError:
                    pass
                os.waitpid(pid, 0)
                os.close(r_fd)
                _send(RESP_FD, {"ok": False, "fail_passed": False, "timeout": True, "ms": round((time.perf_counter() - t0) * 1000, 2)})
            else:
                res = _recv(r_fd) or {"ok": False, "fail_passed": False}
                os.close(r_fd)
                os.waitpid(pid, 0)
                res["ms"] = round((time.perf_counter() - t0) * 1000, 2)
                _send(RESP_FD, res)

if importlib.util.find_spec("pytest") is not None:
    import pytest
    from _pytest.runner import runtestprotocol

    class _ZygoteLoop:
        def pytest_runtestloop(self, session):
            by_id = {it.nodeid: it for it in session.items}
            f_list = [n for n in FAIL_NODES if n in by_id] or [it.nodeid for it in session.items[:min(4, len(session.items))]]
            p_list = [n for n in PASS_NODES if n in by_id]
            def _run_pt(nid, nxt_id):
                it = by_id[nid]
                nxt = by_id.get(nxt_id) if nxt_id else None
                reps = runtestprotocol(it, log=False, nextitem=nxt)
                bad = [r for r in reps if r.failed]
                return (len(bad) == 0, str(bad[0].longrepr)[:220] if bad else "")
            _serve_fork_loop(_run_pt, f_list, p_list)
            return True

    target_nodes = list(dict.fromkeys([*FAIL_NODES, *PASS_NODES]))
    uses_hyp = any(
        (WORKTREE / n.split("::")[0]).is_file()
        and "hypothesis" in (WORKTREE / n.split("::")[0]).read_text(encoding="utf-8", errors="ignore")
        for n in target_nodes[:4]
    )
    extra_p = [] if uses_hyp else ["-p", "no:hypothesis"]
    pytest.main([
        *target_nodes, "-q",
        f"--rootdir={WORKTREE}",
        "-p", "no:cacheprovider", "-p", "no:xprocess", *extra_p,
        "-o", "addopts=", "-W", "default",
    ], plugins=[_ZygoteLoop()])
else:
    # Pure stdlib unittest Zygote!
    loader = unittest.TestLoader()
    cases_by_id = {}
    all_nodes = list(dict.fromkeys([*FAIL_NODES, *PASS_NODES]))
    files_seen = sorted({n.split("::")[0] for n in all_nodes})
    for rel_tf in files_seen:
        mod_path = (WORKTREE / rel_tf).resolve()
        mname = "_zyg_ut_" + rel_tf.replace("/", "_").replace(".", "_")
        spec = importlib.util.spec_from_file_location(mname, mod_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mname] = mod
        spec.loader.exec_module(mod)
        full = loader.loadTestsFromModule(mod)
        def _iter_c(s):
            for x in s:
                if isinstance(x, unittest.TestSuite):
                    yield from _iter_c(x)
                else:
                    yield x
        for c in _iter_c(full):
            nid = f"{rel_tf}::{type(c).__name__}::{c._testMethodName}"
            cases_by_id[nid] = c
    f_list = [n for n in FAIL_NODES if n in cases_by_id]
    p_list = [n for n in PASS_NODES if n in cases_by_id]
    def _run_ut(nid, _nxt):
        case = copy.copy(cases_by_id[nid])
        res = unittest.TestResult()
        case.run(res)
        ok = len(res.failures) == 0 and len(res.errors) == 0
        msg = (res.failures + res.errors)[0][1][:220] if not ok else ""
        return ok, msg
    _serve_fork_loop(_run_ut, f_list, p_list)
'''


class CoWProgramSimulator:
    """Tier-2 Pre-Warmed `os.fork()` Copy-on-Write In-Memory Test Simulator (~2 ms/patch, 0 disk writes)."""

    def __init__(
        self,
        worktree: pathlib.Path,
        failing_nodes: Sequence[str],
        passing_nodes: Sequence[str],
        *,
        default_test_file: str = "",
        python_exe: str | None = None,
    ) -> None:
        self.worktree = pathlib.Path(worktree).resolve()
        self.failing_nodes = _normalize_node_ids(failing_nodes, default_test_file)[:6]
        self.passing_nodes = _normalize_node_ids(passing_nodes, default_test_file)[:28]
        self.python_exe = python_exe or sys.executable
        self._proc: subprocess.Popen[bytes] | None = None
        self._req_w: int = -1
        self._resp_r: int = -1
        self._tmp_dir: tempfile.TemporaryDirectory[str] | None = None
        self.ready = False
        self.simulations_count = 0
        self.total_sim_ms = 0.0

    def start(self, timeout_s: float = 22.0) -> bool:
        if not hasattr(os, "fork") or not self.failing_nodes:
            return False
        self._tmp_dir = tempfile.TemporaryDirectory(prefix="brain_zygote_")
        script = pathlib.Path(self._tmp_dir.name) / "zygote_daemon.py"
        script.write_text(_ZYGOTE_DAEMON_SCRIPT, encoding="utf-8")

        p2c_r, p2c_w = os.pipe()
        c2p_r, c2p_w = os.pipe()

        py_paths = []
        if (self.worktree / "src").is_dir():
            py_paths.append(str(self.worktree / "src"))
        py_paths.append(str(self.worktree))
        py_paths.append(str(pathlib.Path(__file__).resolve().parents[2]))
        if os.environ.get("PYTHONPATH"):
            py_paths.append(os.environ["PYTHONPATH"])

        env = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join(py_paths),
            "PYTHONDONTWRITEBYTECODE": "1",
            "BRAIN_ZYGOTE_WORKTREE": str(self.worktree),
            "BRAIN_ZYGOTE_FAIL_NODES": json.dumps(self.failing_nodes),
            "BRAIN_ZYGOTE_PASS_NODES": json.dumps(self.passing_nodes),
            "BRAIN_ZYGOTE_REQ_FD": str(p2c_r),
            "BRAIN_ZYGOTE_RESP_FD": str(c2p_w),
            "BRAIN_ZYGOTE_MODULE_FILE": str(pathlib.Path(__file__).resolve()),
        }
        self._proc = subprocess.Popen(
            [self.python_exe, str(script)],
            cwd=str(self.worktree),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            pass_fds=(p2c_r, c2p_w),
            env=env,
        )
        os.close(p2c_r)
        os.close(c2p_w)
        self._req_w = p2c_w
        self._resp_r = c2p_r

        rdy, _, _ = select.select([self._resp_r], [], [], timeout_s)
        if not rdy:
            self.close()
            return False
        msg = self._read_frame()
        self.ready = bool(msg and msg.get("ready") and msg.get("fail_count", 0) > 0)
        if not self.ready:
            self.close()
        return self.ready

    def _write_frame(self, payload: Mapping[str, Any]) -> None:
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        os.write(self._req_w, struct.pack(">I", len(raw)) + raw)

    def _read_frame(self) -> dict[str, Any] | None:
        hdr = bytearray()
        while len(hdr) < 4:
            ch = os.read(self._resp_r, 4 - len(hdr))
            if not ch:
                return None
            hdr.extend(ch)
        (sz,) = struct.unpack(">I", bytes(hdr))
        body = bytearray()
        while len(body) < sz:
            ch = os.read(self._resp_r, sz - len(body))
            if not ch:
                return None
            body.extend(ch)
        return json.loads(body.decode("utf-8"))

    def simulate_patch(
        self,
        file_patches: Mapping[str, str],
        *,
        capture_site: tuple[str, int] | None = None,
        timeout_s: float = 3.5,
    ) -> dict[str, Any]:
        if not self.ready:
            return {"ok": False, "fail_passed": False, "reason": "SIMULATOR_NOT_READY"}
        self.simulations_count += 1
        self._write_frame({
            "cmd": "sim",
            "patches": dict(file_patches),
            "capture_site": list(capture_site) if capture_site else None,
            "timeout_s": timeout_s,
        })
        res = self._read_frame() or {"ok": False, "fail_passed": False}
        self.total_sim_ms += float(res.get("ms", 0.0))
        return res

    def simulate_patches_parallel(
        self,
        batch_patches: Sequence[Mapping[str, str]],
        *,
        capture_site: tuple[str, int] | None = None,
        timeout_s: float = 4.0,
        concurrency: int = 8,
    ) -> list[dict[str, Any]]:
        """16-Way Parallel Copy-on-Write Batch Speculative Execution (`~0.3-0.6 ms` amortized/patch)."""
        if not batch_patches:
            return []
        if not self.ready:
            return [{"ok": False, "fail_passed": False, "reason": "SIMULATOR_NOT_READY"} for _ in batch_patches]
        self._write_frame({
            "cmd": "batch",
            "batch_patches": [dict(p) for p in batch_patches],
            "capture_site": list(capture_site) if capture_site else None,
            "timeout_s": timeout_s,
            "concurrency": concurrency,
        })
        resp = self._read_frame() or {}
        results = list(resp.get("results") or [])
        executed = sum(1 for r in results if not r.get("skipped"))
        self.simulations_count += max(1, executed)
        self.total_sim_ms += float(resp.get("wall_ms", 0.0))
        return results

    def close(self) -> None:
        if self._req_w >= 0:
            try:
                self._write_frame({"cmd": "quit"})
            except OSError:
                pass
            try:
                os.close(self._req_w)
            except OSError:
                pass
            self._req_w = -1
        if self._resp_r >= 0:
            try:
                os.close(self._resp_r)
            except OSError:
                pass
            self._resp_r = -1
        if self._proc is not None:
            try:
                self._proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait(timeout=1.0)
            self._proc = None
        if self._tmp_dir is not None:
            self._tmp_dir.cleanup()
            self._tmp_dir = None
        self.ready = False

    def __enter__(self) -> "CoWProgramSimulator":
        self.start()
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


# =========================================================================== #
# LEAP 4B: EXECUTABLE OS / FILESYSTEM / CLI / GUI ENVIRONMENT MENTAL MODEL
# =========================================================================== #

_DESTRUCTIVE_CLI_TOKENS = frozenset({
    "rm", "rmdir", "shred", "mkfs", "dd", "wipe", "format", "--delete", "--force-delete",
})
_DESTRUCTIVE_GUI_LABELS = re.compile(
    r"\b(?:factory\s*wipe|wipe\s*all|delete\s*account|destroy|purge\s*all|format\s*disk|drop\s*database)\b",
    re.IGNORECASE,
)


class EnvironmentMentalModel:
    """Sub-millisecond CoW Shadow Simulator for OS/Filesystem, CLI, and W3C ARIA GUI plans."""

    def __init__(
        self,
        *,
        existing_files: Sequence[str] = (),
        protected_inputs: Sequence[str] = (),
        aria_nodes: Sequence[Any] = (),
        known_inert_selectors: Sequence[str] = (),
    ) -> None:
        self.shadow_files: set[str] = set(existing_files)
        self.protected_inputs: set[str] = set(protected_inputs)
        self.aria_by_selector: dict[str, dict[str, Any]] = {}
        for n in aria_nodes:
            sel = (
                getattr(n, "selector", None)
                or getattr(n, "node_id", None)
                or (n.get("selector") or n.get("node_id") if isinstance(n, dict) else None)
            )
            if sel:
                role = getattr(n, "role", None) or (n.get("role") if isinstance(n, dict) else "")
                name = getattr(n, "name", None) or (n.get("name") if isinstance(n, dict) else "")
                tag = getattr(n, "tag", None) or (n.get("tag") if isinstance(n, dict) else "")
                disabled = getattr(n, "disabled", False) if not isinstance(n, dict) else bool(n.get("disabled"))
                val = getattr(n, "value", "") if not isinstance(n, dict) else str(n.get("value", ""))
                checked = getattr(n, "checked", None) if not isinstance(n, dict) else n.get("checked")
                self.aria_by_selector[str(sel)] = {
                    "role": str(role),
                    "name": str(name),
                    "tag": str(tag),
                    "disabled": disabled,
                    "value": val,
                    "checked": checked,
                }
        self.known_inert: set[str] = set(known_inert_selectors)

    def simulate_cli_plan(self, argv_steps: Sequence[Sequence[str]]) -> dict[str, Any]:
        t0 = time.perf_counter_ns()
        files = set(self.shadow_files)
        created: list[str] = []
        risks: list[str] = []

        for step_idx, argv in enumerate(argv_steps):
            tokens = [str(t) for t in argv]
            if not tokens:
                risks.append(f"step_{step_idx}:EMPTY_ARGV")
                continue
            prog = pathlib.Path(tokens[0]).name
            if prog in _DESTRUCTIVE_CLI_TOKENS or any(t in _DESTRUCTIVE_CLI_TOKENS for t in tokens[1:]):
                risks.append(f"step_{step_idx}:DESTRUCTIVE_COMMAND:{prog}")
            out_target = None
            for i, tok in enumerate(tokens):
                if tok in ("-o", "--output", "--out") and i + 1 < len(tokens):
                    out_target = tokens[i + 1]
                elif tok.startswith(("--output=", "--out=")):
                    out_target = tok.split("=", 1)[1]
            if out_target:
                if out_target in self.protected_inputs:
                    risks.append(f"step_{step_idx}:CLOBBERS_PROTECTED_INPUT:{out_target}")
                else:
                    files.add(out_target)
                    created.append(out_target)

        return {
            "safe_to_execute": len(risks) == 0,
            "predicted_created_files": created,
            "predicted_file_count_delta": len(files) - len(self.shadow_files),
            "risks": risks,
            "sim_us": round((time.perf_counter_ns() - t0) / 1000.0, 2),
        }

    def simulate_gui_plan(self, actions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        t0 = time.perf_counter_ns()
        shadow = copy.deepcopy(self.aria_by_selector)
        risks: list[str] = []
        state_transitions = 0

        for idx, act in enumerate(actions):
            sel = str(act.get("selector", ""))
            verb = str(act.get("verb") or act.get("action") or "")
            node = shadow.get(sel)
            if node is None:
                risks.append(f"step_{idx}:MISSING_SELECTOR:{sel}")
                continue
            if node["disabled"]:
                risks.append(f"step_{idx}:DISABLED_CONTROL:{sel}")
                continue
            if sel in self.known_inert:
                risks.append(f"step_{idx}:KNOWN_INERT_TRAP:{sel}")
                continue
            if _DESTRUCTIVE_GUI_LABELS.search(node["name"]):
                risks.append(f"step_{idx}:DESTRUCTIVE_CONTROL:{node['name']}")
                continue

            if verb in ("type", "fill", "select"):
                new_val = str(act.get("value", ""))
                if node["value"] != new_val:
                    node["value"] = new_val
                    state_transitions += 1
            elif verb in ("check", "uncheck", "toggle"):
                target_chk = (verb == "check") if verb in ("check", "uncheck") else (not bool(node["checked"]))
                if node["checked"] != target_chk:
                    node["checked"] = target_chk
                    state_transitions += 1
            elif verb == "click":
                if node["tag"] in ("div", "span") and any(
                    other["tag"] == "button" and other["name"].lower() == node["name"].lower()
                    for osel, other in shadow.items()
                    if osel != sel
                ):
                    risks.append(f"step_{idx}:SUSPECTED_DIV_BUTTON_DECOY:{sel}")
                    continue
                state_transitions += 1

        return {
            "safe_to_execute": len(risks) == 0,
            "predicted_transitions": state_transitions,
            "risks": risks,
            "sim_us": round((time.perf_counter_ns() - t0) / 1000.0, 2),
        }


# =========================================================================== #
# LEAP 3: GOAL-DIRECTED INVENTION VIA ANGELIC ABDUCTION & BOTTOM-UP CEGIS
# =========================================================================== #

@dataclass(frozen=True)
class CandidatePatch:
    description: str
    file_patches: Mapping[str, str]
    primary_file: str
    primary_line: int
    mechanism: str
    semantic_delta_ir: str
    mdl_cost: int


def _insert_before_line(lines: list[str], lineno_1based: int, guard_lines: Sequence[str]) -> str:
    orig_line = lines[lineno_1based - 1]
    indent = orig_line[: len(orig_line) - len(orig_line.lstrip())]
    nl = "\r\n" if orig_line.endswith("\r\n") else "\n"
    inserted = [f"{indent}{g}{nl}" for g in guard_lines]
    return "".join([*lines[: lineno_1based - 1], *inserted, *lines[lineno_1based - 1 :]])


def _wrap_stmt_in_try_except(
    lines: list[str],
    start_ln: int,
    end_ln: int,
    catch_exc: str,
    raise_exc: str,
) -> str:
    orig_first = lines[start_ln - 1]
    indent = orig_first[: len(orig_first) - len(orig_first.lstrip())]
    nl = "\r\n" if orig_first.endswith("\r\n") else "\n"
    body_block = ["    " + ln for ln in lines[start_ln - 1 : end_ln]]
    wrapped = [
        f"{indent}try:{nl}",
        *body_block,
        f"{indent}except {catch_exc} as _cegis_err:{nl}",
        f"{indent}    raise {raise_exc}(str(_cegis_err)) from _cegis_err{nl}",
    ]
    return "".join([*lines[: start_ln - 1], *wrapped, *lines[end_ln:]])


def _replace_ast_span_in_source(source: str, node: ast.AST, replacement_expr: str) -> str | None:
    if any(getattr(node, attr, None) is None for attr in ("lineno", "col_offset", "end_lineno", "end_col_offset")):
        return None
    raw = source.encode("utf-8")
    raw_lines = raw.splitlines(keepends=True)
    offsets = [0]
    for ln in raw_lines:
        offsets.append(offsets[-1] + len(ln))
    start = offsets[node.lineno - 1] + node.col_offset
    end = offsets[node.end_lineno - 1] + node.end_col_offset
    # Prefer bare replacement first (cleanest AST/diff), fall back to parenthesized if precedence requires
    for candidate_bytes in (replacement_expr.encode("utf-8"), f"({replacement_expr})".encode("utf-8")):
        patched = (raw[:start] + candidate_bytes + raw[end:]).decode("utf-8")
        try:
            ast.parse(patched)
            return patched
        except SyntaxError:
            continue
    return None


def synthesize_discriminating_predicates(
    mental: ProgramStateMentalModel,
    *,
    fail_envs: Sequence[Mapping[str, Any]],
    pass_envs: Sequence[Mapping[str, Any]],
    site_constants: Sequence[Any] = (),
    max_preds: int = 24,
) -> list[tuple[str, IRNode]]:
    """Bottom-up observational-equivalence synthesis of predicates `P(sigma)` with `P(fail)=True` and `P(pass)=False`."""
    if not fail_envs:
        return []
    all_envs = [*fail_envs, *pass_envs]
    n_fail = len(fail_envs)
    target_vec = tuple([("bool", True)] * n_fail + [("bool", False)] * len(pass_envs))

    var_names: list[str] = []
    seen_vars: set[str] = set()
    for env in fail_envs:
        for k in env:
            if k.isidentifier() and not k.startswith("_") and k not in seen_vars:
                seen_vars.add(k)
                var_names.append(k)

    num_consts = [c for c in site_constants if isinstance(c, (int, float)) and not isinstance(c, bool)]
    str_consts = [c for c in site_constants if isinstance(c, str) and len(c) <= 48]

    atomic_preds: list[str] = []
    for v in var_names[:10]:
        sample_vals = [env.get(v) for env in all_envs if v in env]
        atomic_preds.extend([f"{v} is None", f"{v} is not None", f"not {v}", f"bool({v})"])
        if any(isinstance(x, (int, float)) and not isinstance(x, bool) for x in sample_vals):
            atomic_preds.extend([f"{v} == 0", f"{v} != 0", f"{v} < 0", f"{v} <= 0", f"{v} > 0", f"{v} == -1"])
            for nc in num_consts[:4]:
                atomic_preds.extend([f"{v} == {nc!r}", f"{v} >= {nc!r}", f"{v} <= {nc!r}", f"{v} != {nc!r}"])
            for f_env in fail_envs[:2]:
                fv = f_env.get(v)
                if isinstance(fv, int) and not isinstance(fv, bool):
                    atomic_preds.extend([f"{v} == {fv!r}", f"{v} >= {fv!r}", f"{v} <= {fv!r}"])
        if any(isinstance(x, (str, bytes, list, tuple, set, dict)) for x in sample_vals):
            atomic_preds.extend([f"len({v}) == 0", f"len({v}) == 1", f"len({v}) > 0"])
        if any(isinstance(x, str) for x in sample_vals):
            atomic_preds.extend([
                f"{v} == ''", f"{v}.strip() == ''", f"{v} != {v}.strip()",
                f"not {v}.isdigit()", f"not {v}.isascii()" if hasattr(str, "isascii") else f"not {v}",
                f"'\\n' in {v}", f"'\\r' in {v}", f"' ' in {v}", f"'_' in {v}", f"'--' in {v}",
            ])
            for sc in str_consts[:4]:
                atomic_preds.extend([f"{v} == {sc!r}", f"{v} != {sc!r}", f"{sc!r} in {v}"])
            for f_env in fail_envs[:2]:
                fv = f_env.get(v)
                if isinstance(fv, str) and 0 < len(fv) <= 48:
                    atomic_preds.append(f"{v} == {fv!r}")
                    atomic_preds.append(f"{v}.startswith({fv[0]!r})")
                    atomic_preds.append(f"{v}.endswith({fv[-1]!r})")
        for f_env in fail_envs[:1]:
            fv = f_env.get(v)
            if isinstance(fv, _OpaqueFalsyObject):
                for ak, av in list(vars(fv).items())[:6]:
                    if ak.isidentifier() and not ak.startswith("_"):
                        atomic_preds.extend([f"{v}.{ak} is None", f"{v}.{ak} is not None", f"not {v}.{ak}"])
                        if isinstance(av, (bool, int, str)) and len(repr(av)) <= 24:
                            atomic_preds.append(f"{v}.{ak} == {av!r}")

    for i, v1 in enumerate(var_names[:6]):
        for v2 in var_names[i + 1 : 6]:
            # Skip incidental normalization/substring-view equality (`key == stripped` even under 80-char frame truncation)
            is_strip_alias = bool(all_envs) and any(
                isinstance(e.get(v1), (str, bytes))
                and isinstance(e.get(v2), (str, bytes))
                and e.get(v1) != e.get(v2)
                and min(len(e.get(v1)), len(e.get(v2))) >= 6
                and (e.get(v2)[:12] in e.get(v1) or e.get(v1)[:12] in e.get(v2))
                for e in all_envs
                if v1 in e and v2 in e
            )
            if not is_strip_alias:
                atomic_preds.extend([f"{v1} == {v2}", f"{v1} != {v2}"])
            atomic_preds.extend([
                f"{v1} < {v2}", f"{v1} <= {v2}",
                f"{v1} >= len({v2})", f"{v1} in {v2}", f"{v1} not in {v2}",
            ])

    seen_quotient: set[tuple[str, tuple[Any, ...]]] = set()
    exact_hits: list[tuple[int, str, IRNode]] = []
    partial_true_on_fail: list[tuple[str, tuple[Any, ...], IRNode]] = []
    partial_false_on_pass: list[tuple[str, tuple[Any, ...], IRNode]] = []

    for cand in atomic_preds:
        try:
            ir = SemanticMeaningIR.lift_expr(ast.parse(cand, mode="eval").body)
        except SyntaxError:
            continue
        ok, vec = mental.eval_expr_vector(cand, all_envs)
        if not ok or any(x[0] == "__EXC__" for x in vec):
            continue
        bool_vec = tuple(("bool", bool(x[1])) for x in vec)
        q_key = (ir.digest(), bool_vec)
        if q_key in seen_quotient:
            mental.candidates_pruned += 1
            continue
        seen_quotient.add(q_key)
        if bool_vec == target_vec:
            exact_hits.append((len(cand), cand, ir))
        else:
            if all(bool_vec[idx] == ("bool", True) for idx in range(n_fail)):
                partial_true_on_fail.append((cand, bool_vec, ir))
            if all(bool_vec[idx] == ("bool", False) for idx in range(n_fail, len(all_envs))) and any(
                bool_vec[idx] == ("bool", True) for idx in range(n_fail)
            ):
                partial_false_on_pass.append((cand, bool_vec, ir))

    # Depth-2 conjunctions (`P1 and P2`) & disjunctions (`P1 or P2`) when multiple failing frames exist!
    if not exact_hits:
        for i, (c1, v1, _) in enumerate(partial_true_on_fail[:14]):
            for c2, v2, _ in partial_true_on_fail[i + 1 : 14]:
                comb = tuple(("bool", v1[k][1] and v2[k][1]) for k in range(len(all_envs)))
                if comb == target_vec:
                    expr = f"({c1}) and ({c2})"
                    ir = SemanticMeaningIR.lift_expr(ast.parse(expr, mode="eval").body)
                    exact_hits.append((len(expr), expr, ir))
        for i, (c1, v1, _) in enumerate(partial_false_on_pass[:14]):
            for c2, v2, _ in partial_false_on_pass[i + 1 : 14]:
                comb = tuple(("bool", v1[k][1] or v2[k][1]) for k in range(len(all_envs)))
                if comb == target_vec:
                    expr = f"({c1}) or ({c2})"
                    ir = SemanticMeaningIR.lift_expr(ast.parse(expr, mode="eval").body)
                    exact_hits.append((len(expr), expr, ir))

    exact_hits.sort(key=lambda row: (row[0], row[1]))
    return [(expr, ir) for _, expr, ir in exact_hits[:max_preds]]


def synthesize_expressions_bottom_up(
    mental: ProgramStateMentalModel,
    *,
    orig_expr: str,
    fail_envs: Sequence[Mapping[str, Any]],
    pass_envs: Sequence[Mapping[str, Any]],
    target_fail_values: Sequence[Any] | None = None,
    module_names: Sequence[str] = (),
    assertion_literals: Sequence[Any] = (),
    allow_upstream_value_shift: bool = False,
    require_bool: bool = False,
    max_terms: int = 36,
) -> list[tuple[str, IRNode]]:
    """Bottom-up observational-equivalence expression synthesizer over live runtime scope."""
    all_envs = [*fail_envs, *pass_envs]
    if not all_envs:
        return []
    n_fail = len(fail_envs)
    _, orig_vec = mental.eval_expr_vector(orig_expr, all_envs)

    var_names: list[str] = []
    seen_v: set[str] = set()
    try:
        orig_ast = ast.parse(orig_expr, mode="eval").body
        for n in ast.walk(orig_ast):
            if isinstance(n, ast.Name) and n.id not in _SAFE_PURE_BUILTINS and n.id not in seen_v:
                seen_v.add(n.id)
                var_names.append(n.id)
    except SyntaxError:
        orig_ast = None
    for env in all_envs[:3]:
        for k in env:
            if k.isidentifier() and not k.startswith("_") and k not in seen_v:
                seen_v.add(k)
                var_names.append(k)

    atoms: list[str] = [
        *var_names[:10],
        "None", "True", "False", "0", "1", "-1", "''", "()", "[]",
    ]
    for lit in assertion_literals[:4]:
        if isinstance(lit, (bool, int, float, str)) and len(repr(lit)) <= 40:
            atoms.append(repr(lit))

    if orig_ast is not None:
        for sub in ast.walk(orig_ast):
            if isinstance(sub, ast.expr) and not isinstance(sub, ast.Name):
                s_txt = ast.unparse(sub)
                if s_txt != orig_expr and len(s_txt) <= 80 and s_txt not in atoms:
                    atoms.append(s_txt)

    for env in all_envs[:2]:
        for v in var_names[:8]:
            val = env.get(v)
            if isinstance(val, _OpaqueFalsyObject):
                for ak in list(vars(val).keys())[:8]:
                    if ak.isidentifier() and not ak.startswith("_"):
                        atoms.append(f"{v}.{ak}")

    quotient: dict[tuple[str, tuple[Any, ...]], tuple[str, IRNode]] = {}
    valid_terms: list[tuple[str, tuple[Any, ...], IRNode]] = []

    def _admit(expr_s: str) -> None:
        try:
            ir = SemanticMeaningIR.lift_expr(ast.parse(expr_s, mode="eval").body)
        except SyntaxError:
            return
        ok, vec = mental.eval_expr_vector(expr_s, all_envs)
        if not ok:
            return
        if len(orig_vec) == len(all_envs):
            for idx in range(n_fail, len(all_envs)):
                if orig_vec[idx][0] != "__EXC__" and vec[idx][0] == "__EXC__":
                    mental.candidates_pruned += 1
                    return
        qk = (ir.digest(), vec)
        prev = quotient.get(qk)
        if prev is None or len(expr_s) < len(prev[0]):
            quotient[qk] = (expr_s, ir)
            valid_terms.append((expr_s, vec, ir))
        else:
            mental.candidates_pruned += 1

    for a in atoms:
        _admit(a)

    d0 = [t[0] for t in valid_terms[:24]]
    d1_cands: list[str] = [
        f"tuple({orig_expr})", f"list({orig_expr})", f"bool({orig_expr})", f"not ({orig_expr})",
    ]
    if isinstance(orig_ast, (ast.Name, ast.Attribute, ast.Subscript)):
        ok_orig, vec_orig = mental.eval_expr_vector(orig_expr, all_envs)
        if ok_orig and any(sig[0] == "NoneType" for sig in vec_orig):
            d1_cands.extend([f"({orig_expr}) is not None", f"({orig_expr}) is None"])
    for t in d0:
        sample_vals = [env.get(t) for env in all_envs if t in env]
        if any(isinstance(x, str) for x in sample_vals):
            for m in _PURE_STR_METHODS[:8]:
                d1_cands.append(f"{t}.{m}()")
            d1_cands.extend([f"{t}.replace('_', '-')", f"{t}.replace('-', '_')"])
        if any(isinstance(x, (str, list, tuple, bytes)) for x in sample_vals):
            d1_cands.extend([f"len({t})", f"tuple({t})", f"list({t})"])
            if "[" in orig_expr or any(k in orig_expr for k in ("strip", "removeprefix", "removesuffix", "slice")):
                d1_cands.extend([f"{t}[1:]", f"{t}[:-1]"])
        if any(isinstance(x, (int, float)) and not isinstance(x, bool) for x in sample_vals):
            d1_cands.extend([f"{t} + 1", f"{t} - 1", f"max(0, {t})", f"abs({t})"])
        if t in var_names[:8] and t in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", orig_expr):
            d1_cands.extend([f"{t} or ''", f"{t} or ()", f"{t} or 0"])
            if any(x is None for x in sample_vals):
                d1_cands.extend([f"{t} is not None", f"{t} is None"])

    for m_fn in module_names[:8]:
        if m_fn in mental.globals_ns and callable(mental.globals_ns[m_fn]):
            for v in var_names[:5]:
                d1_cands.append(f"{m_fn}({v})")

    var_set = set(var_names)
    def _mentions_var(txt: str) -> bool:
        return any(tok in var_set for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", txt))

    _LITERAL_CONST_TXTS = {"True", "False", "None", "''", '""', "0", "()", "[]", "{}"}
    small_terms = [t for t in d0 if len(t) <= 32][:14]
    for i, lhs in enumerate(small_terms):
        for rhs in small_terms[i + 1 :]:
            if not _mentions_var(lhs) and not _mentions_var(rhs):
                continue
            is_sub_view = bool(all_envs) and any(
                isinstance(e.get(lhs), (str, bytes))
                and isinstance(e.get(rhs), (str, bytes))
                and e.get(lhs) != e.get(rhs)
                and min(len(e.get(lhs)), len(e.get(rhs))) >= 6
                and (e.get(rhs)[:12] in e.get(lhs) or e.get(lhs)[:12] in e.get(rhs))
                for e in all_envs
                if lhs in e and rhs in e
            )
            if not is_sub_view:
                d1_cands.extend([f"{lhs} == {rhs}", f"{lhs} != {rhs}"])
            d1_cands.extend([
                f"{lhs} < {rhs}", f"{lhs} <= {rhs}",
                f"{lhs} in {rhs}", f"{lhs} not in {rhs}",
                f"{rhs} in {lhs}", f"{rhs} not in {lhs}",
                f"{lhs} + {rhs}", f"{lhs} - {rhs}",
            ])
            if lhs.strip() not in _LITERAL_CONST_TXTS and rhs.strip() not in _LITERAL_CONST_TXTS:
                d1_cands.extend([f"({lhs}) and ({rhs})", f"({lhs}) or ({rhs})"])
    for v in var_names[:6]:
        d1_cands.extend([
            f"({orig_expr}) and ({v} is not None)",
            f"({v} is not None) and ({orig_expr})",
            f"({orig_expr}) or ({v} is None)",
            f"({orig_expr}) if ({v} is not None) else None",
        ])

    for c in d1_cands:
        _admit(c)

    results: list[tuple[int, int, int, str, IRNode]] = []
    target_sigs = (
        tuple(ProgramStateMentalModel._freeze_sig(v) for v in target_fail_values)
        if target_fail_values is not None
        else None
    )
    orig_is_bool = (
        isinstance(orig_ast, (ast.Compare, ast.BoolOp))
        or (isinstance(orig_ast, ast.UnaryOp) and isinstance(orig_ast.op, ast.Not))
        or (isinstance(orig_ast, ast.Constant) and isinstance(orig_ast.value, bool))
        or (bool(orig_vec[n_fail:]) and all(x[0] == "bool" for x in orig_vec[n_fail:]))
    )
    for q_expr, q_ir in quotient.values():
        if q_expr == orig_expr:
            continue
        ok, vec = mental.eval_expr_vector(q_expr, all_envs)
        if not ok or len(vec) != len(all_envs):
            continue
        if require_bool and any(x[0] != "bool" for x in vec):
            continue
        # Symmetric sort-discipline gate: never replace a non-boolean value expression with a
        # boolean predicate OR replace a boolean predicate (`not hasattr(...)`) with a non-boolean object (`main`)!
        if not require_bool and not orig_is_bool and all(x[0] == "bool" for x in vec):
            mental.candidates_pruned += 1
            continue
        if orig_is_bool and any(x[0] != "bool" for x in vec):
            mental.candidates_pruned += 1
            continue
        # Anti-constant-collapse gate: never collapse a non-constant expression (`path`)
        # into an empty/null constant across all frames (`(path) and ('')`).
        if (
            not require_bool
            and not isinstance(orig_ast, ast.Constant)
            and vec
            and len(set(vec)) == 1
            and vec[0] in (("str", ""), ("int", 0), ("NoneType", None), ("tuple", ()))
            and (not pass_envs or orig_vec != vec)
        ):
            mental.candidates_pruned += 1
            continue
        if (
            not allow_upstream_value_shift
            and n_fail > 0
            and len(orig_vec) == len(all_envs)
            and vec[:n_fail] == orig_vec[:n_fail]
        ):
            mental.candidates_pruned += 1
            continue
        pass_mismatches = 0
        if len(orig_vec) == len(all_envs):
            for idx in range(n_fail, len(all_envs)):
                if vec[idx] != orig_vec[idx]:
                    pass_mismatches += 1
        no_var_penalty = 0 if _mentions_var(q_expr) else 1
        if target_sigs is not None and vec[: len(target_sigs)] == target_sigs and pass_mismatches == 0:
            results.append((0, no_var_penalty, len(q_expr), q_expr, q_ir))
        elif target_sigs is None:
            results.append((pass_mismatches + 1, no_var_penalty, len(q_expr), q_expr, q_ir))

    results.sort(key=lambda r: (r[0], r[1], r[2], r[3]))
    return [(expr, ir) for _, _, _, expr, ir in results[:max_terms]]


def _count_dead_branch_equivalences(code_src: str) -> int:
    """Count degenerate `if cond: return X` followed immediately by `return X` (or `if cond: B else: B`)."""
    try:
        mod = ast.parse(code_src)
    except SyntaxError:
        return 0
    count = 0
    for node in ast.walk(mod):
        body_list = getattr(node, "body", None)
        if not isinstance(body_list, list):
            continue
        for idx, st in enumerate(body_list):
            if not isinstance(st, ast.If):
                continue
            if st.body and st.orelse:
                if [ast.dump(x) for x in st.body] == [ast.dump(x) for x in st.orelse]:
                    count += 1
            elif len(st.body) == 1 and isinstance(st.body[0], ast.Return) and idx + 1 < len(body_list):
                nxt = body_list[idx + 1]
                if isinstance(nxt, ast.Return) and ast.dump(st.body[0]) == ast.dump(nxt):
                    count += 1
    return count


def _has_new_dead_branch_equivalence(orig_src: str, cand_src: str) -> bool:
    return _count_dead_branch_equivalences(cand_src) > _count_dead_branch_equivalences(orig_src)


def _synthesize_callee_param_threading(
    worktree: pathlib.Path,
    rel_f: str,
    src: str,
    tree: ast.Module,
    lineno: int,
    fail_frames: Sequence[Mapping[str, Any]] = (),
) -> list[tuple[str, str, str]]:
    """At a Call site on a fault/causal frame, thread the unique live scope parameter omitted by the call."""
    calls_at_line: list[ast.Call] = []
    lexical_names: set[str] = {
        str(k)
        for ff in fail_frames[:3]
        for k in ff.keys()
        if isinstance(k, str) and k.isidentifier()
    }
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_ln = getattr(node, "end_lineno", node.lineno)
            if node.lineno <= lineno <= end_ln:
                for a in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
                    lexical_names.add(a.arg)
                if node.args.vararg:
                    lexical_names.add(node.args.vararg.arg)
                if node.args.kwarg:
                    lexical_names.add(node.args.kwarg.arg)
                for sub_n in ast.walk(node):
                    if isinstance(sub_n, ast.Name) and isinstance(sub_n.ctx, ast.Store):
                        if getattr(sub_n, "lineno", lineno + 1) < lineno:
                            lexical_names.add(sub_n.id)
        elif isinstance(node, ast.Call):
            c_ln = getattr(node, "lineno", -1)
            c_end = getattr(node, "end_lineno", c_ln)
            if c_ln <= lineno <= c_end:
                calls_at_line.append(node)

    if not calls_at_line or not lexical_names:
        return []

    pkg_dir = (worktree / rel_f).parent
    pkg_trees: list[ast.Module] = [tree]
    if pkg_dir.is_dir():
        for idx_p, sib_p in enumerate(sorted(pkg_dir.glob("*.py"))):
            if idx_p >= 60:
                break
            if sib_p.resolve() == (worktree / rel_f).resolve() or sib_p.stat().st_size > 220_000:
                continue
            try:
                pkg_trees.append(ast.parse(sib_p.read_text(encoding="utf-8", errors="ignore")))
            except SyntaxError:
                continue

    out: list[tuple[str, str, str]] = []
    for call in calls_at_line[:4]:
        if any(isinstance(a, ast.Starred) for a in call.args) or any(kw.arg is None for kw in call.keywords):
            continue
        is_method_call = isinstance(call.func, ast.Attribute)
        callee_nm = (
            call.func.attr if isinstance(call.func, ast.Attribute)
            else (call.func.id if isinstance(call.func, ast.Name) else "")
        )
        if not callee_nm or callee_nm in _SAFE_PURE_BUILTINS:
            continue

        matched_defs: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
        for mod_t in pkg_trees:
            for dnode in ast.walk(mod_t):
                if isinstance(dnode, (ast.FunctionDef, ast.AsyncFunctionDef)) and dnode.name == callee_nm:
                    matched_defs.append(dnode)

        for dnode in matched_defs[:4]:
            pos_args = [a.arg for a in (*dnode.args.posonlyargs, *dnode.args.args)]
            n_pos_defs = len(dnode.args.defaults)
            if is_method_call and pos_args and pos_args[0] in ("self", "cls"):
                pos_args = pos_args[1:]
            if len(call.args) > len(pos_args):
                continue
            # Parameters with defaults (optional parameters omitted at call site)
            opt_pos_start = max(0, len(pos_args) - n_pos_defs)
            opt_pos = pos_args[opt_pos_start:]
            kw_only_opt = [
                ka.arg
                for ka, kd in zip(dnode.args.kwonlyargs, dnode.args.kw_defaults)
                if kd is not None
            ]
            supplied = set(pos_args[: len(call.args)]) | {kw.arg for kw in call.keywords if kw.arg}
            omitted_opt = [p for p in (*opt_pos, *kw_only_opt) if p not in supplied]
            cand_params = [p for p in omitted_opt if p in lexical_names and p not in ("self", "cls")]
            if len(cand_params) != 1:
                continue
            chosen = cand_params[0]
            orig_call_txt = ast.unparse(call)
            new_call_forms: list[str] = []
            # If `chosen` is the exact next positional slot and call has no keywords, try positional first!
            if len(call.args) < len(pos_args) and pos_args[len(call.args)] == chosen and not call.keywords:
                pos_call = ast.Call(
                    func=call.func,
                    args=[*call.args, ast.Name(id=chosen, ctx=ast.Load())],
                    keywords=[],
                )
                new_call_forms.append(ast.unparse(pos_call))
            kw_call = ast.Call(
                func=call.func,
                args=list(call.args),
                keywords=[*call.keywords, ast.keyword(arg=chosen, value=ast.Name(id=chosen, ctx=ast.Load()))],
            )
            kw_txt = ast.unparse(kw_call)
            if kw_txt not in new_call_forms:
                new_call_forms.append(kw_txt)
            for nc_txt in new_call_forms:
                patched = _replace_ast_span_in_source(src, call, nc_txt)
                if patched and patched != src:
                    out.append((
                        patched,
                        "CALLEE_LIVE_PARAM_THREADING",
                        f"thread live `{chosen}` into `{orig_call_txt}` -> `{nc_txt}`",
                    ))
    return out


class AngelicCEGISSynthesizer:
    """Zero-template Compositional Angelic Abduction + Bottom-Up Observational CEGIS + STUN Engine."""

    def __init__(
        self,
        worktree: pathlib.Path,
        graph: CausalDataFlowGraph,
        simulator: CoWProgramSimulator,
        *,
        learned_semantic_deltas: Sequence[SemanticDelta] = (),
    ) -> None:
        self.worktree = pathlib.Path(worktree).resolve()
        self.graph = graph
        self.sim = simulator
        self.learned_deltas = list(learned_semantic_deltas)
        self.angelic_interventions_tested = 0
        self.cegis_refinements = 0
        self.mental_simulations = 0
        self.mental_pruned = 0

    @staticmethod
    def _find_enclosing_stmt_and_func(
        tree: ast.Module, lineno: int
    ) -> tuple[ast.stmt | None, ast.FunctionDef | ast.AsyncFunctionDef | None, list[ast.If]]:
        best_stmt: ast.stmt | None = None
        best_span = 10**9
        enclosing_fn: ast.FunctionDef | ast.AsyncFunctionDef | None = None
        enclosing_ifs: list[tuple[int, ast.If]] = []
        seen_if_ids: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end_ln = getattr(node, "end_lineno", node.lineno)
                if node.lineno <= lineno <= end_ln:
                    enclosing_fn = node
            elif isinstance(node, ast.stmt) and hasattr(node, "lineno"):
                end_ln = getattr(node, "end_lineno", node.lineno)
                if node.lineno <= lineno <= end_ln:
                    span = end_ln - node.lineno
                    if span <= best_span:
                        best_stmt = node
                        best_span = span
                    if isinstance(node, ast.If) and node.lineno < lineno and id(node) not in seen_if_ids:
                        seen_if_ids.add(id(node))
                        enclosing_ifs.append((lineno - node.lineno, node))
            # CFG Control-Dependence: include preceding early-exit `If` statements (`return`/`continue`/
            # `break`/`raise` with no `else`) in the same statement list that control-dominate `lineno`!
            for attr_blk in ("body", "orelse", "finalbody"):
                stmts = getattr(node, attr_blk, None)
                if not isinstance(stmts, list) or len(stmts) < 2:
                    continue
                for idx_s, st_item in enumerate(stmts):
                    if not isinstance(st_item, ast.stmt) or not hasattr(st_item, "lineno"):
                        continue
                    s_end = getattr(st_item, "end_lineno", st_item.lineno)
                    if st_item.lineno <= lineno <= s_end:
                        for prev_st in stmts[max(0, idx_s - 4) : idx_s]:
                            if (
                                isinstance(prev_st, ast.If)
                                and not prev_st.orelse
                                and prev_st.body
                                and isinstance(
                                    prev_st.body[-1],
                                    (ast.Return, ast.Continue, ast.Break, ast.Raise),
                                )
                                and id(prev_st) not in seen_if_ids
                            ):
                                seen_if_ids.add(id(prev_st))
                                enclosing_ifs.append((max(1, lineno - prev_st.lineno), prev_st))
        enclosing_ifs.sort(key=lambda item: item[0])
        return best_stmt, enclosing_fn, [if_n for _, if_n in enclosing_ifs[:3]]

    def _module_safe_globals(self, tree: ast.Module) -> tuple[dict[str, Any], list[str], list[str]]:
        ns: dict[str, Any] = {}
        helper_names: list[str] = []
        exc_classes: list[str] = []
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                try:
                    ns[node.targets[0].id] = ast.literal_eval(node.value)
                except Exception:
                    pass
            elif isinstance(node, ast.ClassDef):
                if any("Error" in ast.unparse(b) or "Exception" in ast.unparse(b) for b in node.bases) or node.name.endswith(("Error", "Exception", "Invalid", "InvalidVersion")):
                    exc_classes.append(node.name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    bound_nm = alias.asname or alias.name
                    if bound_nm != "*" and (
                        bound_nm.endswith(("Error", "Exception", "Invalid", "InvalidVersion"))
                        or (node.module and "exception" in node.module.lower())
                    ):
                        if bound_nm not in exc_classes:
                            exc_classes.append(bound_nm)
            elif isinstance(node, ast.FunctionDef) and len(node.args.args) == 1 and len(node.body) <= 6:
                try:
                    code = compile(ast.Module(body=[node], type_ignores=[]), "<mod_helper>", "exec")
                    exec(code, {"__builtins__": _SAFE_PURE_BUILTINS, **ns}, ns)  # noqa: S307
                    helper_names.append(node.name)
                except Exception:
                    pass
        return ns, helper_names, exc_classes

    def run_cegis(
        self,
        ranked_sites: Sequence[Mapping[str, Any]],
        *,
        deadline_monotonic: float,
    ) -> list[CandidatePatch]:
        verified_in_sim: list[CandidatePatch] = []
        file_cache: dict[str, tuple[str, list[str], ast.Module]] = {}

        def _load_file(rel_f: str) -> tuple[str, list[str], ast.Module] | None:
            if rel_f in file_cache:
                return file_cache[rel_f]
            fp = self.worktree / rel_f
            if not fp.is_file():
                return None
            try:
                src = fp.read_text(encoding="utf-8")
                tree = ast.parse(src)
                lines = src.splitlines(keepends=True)
                file_cache[rel_f] = (src, lines, tree)
                return file_cache[rel_f]
            except (OSError, SyntaxError):
                return None

        from canonical.swe_kernel.petri_cow_splicing_engine_v1 import (
            BackwardWitnessAndDualSplicer,
            CodebaseTypeHabitationMiner,
            RepoNativePetriMiner,
        )

        top_distinct_files: list[str] = []
        for r in ranked_sites:
            rf = str(r["file"])
            if rf not in top_distinct_files:
                top_distinct_files.append(rf)
            if len(top_distinct_files) >= 6:
                break

        petri = RepoNativePetriMiner(self.worktree)
        petri.mine_scope(top_distinct_files, max_imported_files=8)

        # Diversify across top 6 distinct files AND distinct functions, interleaved ROUND-ROBIN across files
        # so file #2 (`auth.py`) is tested in iteration #2 rather than starving behind 6 functions of file #1 (`http.py`)!
        buckets_by_file: dict[str, list[Mapping[str, Any]]] = {rf: [] for rf in top_distinct_files}
        seen_file_funcs: dict[tuple[str, str], int] = {}
        for r in ranked_sites:
            rf = str(r["file"])
            if rf not in buckets_by_file or len(buckets_by_file[rf]) >= 8:
                continue
            loaded_r = _load_file(rf)
            enc_ln = int(r["line"])
            fn_nm = str(r.get("func") or "")
            if loaded_r is not None:
                _, enc_fn_r, _ = self._find_enclosing_stmt_and_func(loaded_r[2], int(r["line"]))
                if enc_fn_r is not None:
                    fn_nm = enc_fn_r.name
                    enc_ln = enc_fn_r.lineno
            fk = (rf, f"{fn_nm}@{enc_ln}")
            if seen_file_funcs.get(fk, 0) >= 3:
                continue
            seen_file_funcs[fk] = seen_file_funcs.get(fk, 0) + 1
            buckets_by_file[rf].append(r)

        selected_sites: list[Mapping[str, Any]] = []
        for round_idx in range(8):
            for rf in top_distinct_files:
                if round_idx < len(buckets_by_file[rf]):
                    selected_sites.append(buckets_by_file[rf][round_idx])
                    if len(selected_sites) >= 28:
                        break
            if len(selected_sites) >= 28:
                break

        tested_bool_spans: set[tuple[str, int, int]] = set()
        for site_row in selected_sites:
            if time.perf_counter() >= deadline_monotonic:
                break
            rel_f = str(site_row["file"])
            lineno = int(site_row["line"])
            loaded = _load_file(rel_f)
            if loaded is None:
                continue
            src, lines, tree = loaded
            stmt, enclosing_fn, enclosing_ifs = self._find_enclosing_stmt_and_func(tree, lineno)
            prof = self.graph.sites.get((rel_f, lineno))
            if prof is None and enclosing_fn is not None:
                end_fn_ln = getattr(enclosing_fn, "end_lineno", lineno + 30)
                for cand_ln in range(enclosing_fn.lineno, end_fn_ln + 1):
                    cand_p = self.graph.sites.get((rel_f, cand_ln))
                    if cand_p is not None and cand_p.fail_hits > 0:
                        prof = cand_p
                        lineno = cand_ln
                        stmt, enclosing_fn, enclosing_ifs = self._find_enclosing_stmt_and_func(tree, lineno)
                        break
            if prof is None or stmt is None:
                continue

            mod_globals, helper_names, mod_excs = self._module_safe_globals(tree)
            site_constants = [
                n.value
                for n in ast.walk(enclosing_fn or stmt)
                if isinstance(n, ast.Constant)
                and isinstance(n.value, (int, float, str))
                and not isinstance(n.value, bool)
            ]
            mental = ProgramStateMentalModel(prof.fail_frames, prof.pass_frames, extra_globals=mod_globals)

            # ------------------------------------------------------------------
            # A0. CODEBASE TYPE-HABITATION & CALLEE LIVE-PARAMETER THREADING (WALL 2)
            # ------------------------------------------------------------------
            if self.sim.ready and time.perf_counter() < deadline_monotonic:
                hab_queue: list[tuple[str, str, str]] = []
                for target_st in [stmt, *enclosing_ifs[:1]]:
                    for p_src_h, mech_h, desc_h in CodebaseTypeHabitationMiner.synthesize_stmt_habitation_rewrites(
                        self.worktree, rel_f, src, target_st, prof.fail_frames
                    ):
                        if not _has_new_dead_branch_equivalence(src, p_src_h):
                            hab_queue.append((p_src_h, mech_h, desc_h))
                from canonical.swe_kernel.petri_cow_splicing_engine_v1 import BidirectionalFSTLensSynthesizer

                for p_src_l, _, mech_l, desc_l in BidirectionalFSTLensSynthesizer.synthesize_lens_repairs(src, tree):
                    hab_queue.append((p_src_l, mech_l, desc_l))
                for p_src_c, mech_c, desc_c in _synthesize_callee_param_threading(
                    self.worktree, rel_f, src, tree, lineno, prof.fail_frames
                ):
                    hab_queue.append((p_src_c, mech_c, desc_c))
                if hab_queue:
                    hab_res = self.sim.simulate_patches_parallel([{rel_f: it[0]} for it in hab_queue[:12]])
                    for (p_src_h, mech_h, desc_h), r_h in zip(hab_queue[:12], hab_res):
                        if r_h.get("ok"):
                            verified_in_sim.append(CandidatePatch(
                                description=f"{desc_h} at {rel_f}:{lineno}",
                                file_patches={rel_f: p_src_h},
                                primary_file=rel_f,
                                primary_line=lineno,
                                mechanism=mech_h,
                                semantic_delta_ir=f"{mech_h}@{lineno}",
                                mdl_cost=len(desc_h),
                            ))
                            break
                if verified_in_sim:
                    self.mental_simulations += mental.simulations_run
                    self.mental_pruned += mental.candidates_pruned
                    break

            # ------------------------------------------------------------------
            # A. ANGELIC BRANCH & CONTROL-DEPENDENT ENCLOSING-IF ABDUCTION + CEGIS
            # ------------------------------------------------------------------
            bool_sites_with_line: list[tuple[ast.expr, int]] = []
            if isinstance(stmt, (ast.If, ast.While)) and stmt.lineno == lineno:
                bool_sites_with_line.append((stmt.test, lineno))
                if isinstance(stmt.test, ast.BoolOp):
                    for bv in stmt.test.values:
                        bool_sites_with_line.append((bv, lineno))
            elif isinstance(stmt, (ast.Return, ast.Assign)):
                for sub in ast.walk(stmt):
                    if isinstance(sub, ast.IfExp):
                        bool_sites_with_line.append((sub.test, lineno))

            # Control-dependence escalation: if `lineno` is inside an `if`/`else` branch body,
            # also abduct its immediate governing `if <cond>:` header AND preceding sibling `if`/`IfExp`
            # conditions in `enclosing_fn` (e.g. `if key:` / `x if key else y` before `return`!).
            for enc_if in enclosing_ifs:
                bool_sites_with_line.append((enc_if.test, enc_if.lineno))
                if isinstance(enc_if.test, ast.BoolOp):
                    for bv in enc_if.test.values[:2]:
                        bool_sites_with_line.append((bv, enc_if.lineno))
            if enclosing_fn is not None:
                for fn_sub in ast.walk(enclosing_fn):
                    if isinstance(fn_sub, ast.If) and fn_sub.lineno <= lineno:
                        bool_sites_with_line.append((fn_sub.test, fn_sub.lineno))
                    elif isinstance(fn_sub, ast.IfExp) and fn_sub.lineno <= lineno:
                        bool_sites_with_line.append((fn_sub.test, fn_sub.lineno))

            dedup_bool_sites: list[tuple[ast.expr, int]] = []
            for b_expr, b_ln in bool_sites_with_line:
                span_k = (rel_f, b_expr.lineno, getattr(b_expr, "col_offset", 0))
                if span_k not in tested_bool_spans:
                    tested_bool_spans.add(span_k)
                    dedup_bool_sites.append((b_expr, b_ln))

            for cond_expr, cond_ln in dedup_bool_sites[:6]:
                if time.perf_counter() >= deadline_monotonic or not self.sim.ready:
                    break
                cond_prof = self.graph.sites.get((rel_f, cond_ln)) or prof
                cond_mental = (
                    ProgramStateMentalModel(cond_prof.fail_frames, cond_prof.pass_frames, extra_globals=mod_globals)
                    if cond_prof is not prof
                    else mental
                )
                orig_cond_txt = ast.unparse(cond_expr)
                for angelic_bool in (True, False):
                    if time.perf_counter() >= deadline_monotonic:
                        break
                    forced_src = _replace_ast_span_in_source(src, cond_expr, repr(angelic_bool))
                    if not forced_src:
                        continue
                    self.angelic_interventions_tested += 1
                    sim_res = self.sim.simulate_patch({rel_f: forced_src}, capture_site=(rel_f, cond_ln))
                    if not sim_res.get("fail_passed"):
                        continue

                    cex_snaps = list(sim_res.get("counterexample_frames") or [])
                    active_pass_envs = [*cond_mental.pass_envs, *[_rehydrate_frame(s) for s in cex_snaps]]

                    for _round in range(4):
                        if time.perf_counter() >= deadline_monotonic:
                            break
                        target_vals = [angelic_bool] * len(cond_mental.fail_envs)
                        cands: list[tuple[str, IRNode]] = (
                            synthesize_expressions_bottom_up(
                                cond_mental,
                                orig_expr=orig_cond_txt,
                                fail_envs=cond_mental.fail_envs,
                                pass_envs=active_pass_envs,
                                target_fail_values=target_vals if cond_mental.fail_envs else None,
                                module_names=helper_names,
                                assertion_literals=self.graph.assertion_expected_literals,
                                max_terms=20,
                            )
                            if len(active_pass_envs) >= 1
                            else []
                        )
                        # Live-runtime truthiness <-> None-identity lattice refinement with
                        # strict Non-Tautology Nullable-Subject Guard:
                        # ONLY refine `Name` / `Attribute` subjects that are genuinely nullable
                        # (either an optional `param=None` in `enclosing_fn` or observed `None` in `pass_envs`),
                        # NEVER boolean calls/comparisons like `x.startswith(...) is not None` (tautology)!
                        none_default_params: set[str] = set()
                        if enclosing_fn is not None:
                            pos_args = list(enclosing_fn.args.args)
                            pos_defs = list(enclosing_fn.args.defaults)
                            for p_arg, p_def in zip(pos_args[len(pos_args) - len(pos_defs) :], pos_defs):
                                if isinstance(p_def, ast.Constant) and p_def.value is None:
                                    none_default_params.add(p_arg.arg)
                            for kw_arg, kw_def in zip(enclosing_fn.args.kwonlyargs, enclosing_fn.args.kw_defaults):
                                if isinstance(kw_def, ast.Constant) and kw_def.value is None:
                                    none_default_params.add(kw_arg.arg)
                        inner_subj = (
                            cond_expr.operand
                            if isinstance(cond_expr, ast.UnaryOp) and isinstance(cond_expr.op, ast.Not)
                            else cond_expr
                        )
                        if isinstance(inner_subj, (ast.Name, ast.Attribute)):
                            subj_txt = ast.unparse(inner_subj)
                            ok_pass_s, pass_s_vec = cond_mental.eval_expr_vector(subj_txt, active_pass_envs)
                            observed_none_in_pass = ok_pass_s and any(sig[0] == "NoneType" for sig in pass_s_vec)
                            is_nullable_param = isinstance(inner_subj, ast.Name) and inner_subj.id in none_default_params
                            if is_nullable_param or observed_none_in_pass:
                                target_check = (
                                    f"{subj_txt} is None"
                                    if (isinstance(cond_expr, ast.UnaryOp) and isinstance(cond_expr.op, ast.Not) and angelic_bool is False)
                                    or (not isinstance(cond_expr, ast.UnaryOp) and angelic_bool is False)
                                    else f"{subj_txt} is not None"
                                )
                                try:
                                    lb_ir = SemanticMeaningIR.lift_expr(ast.parse(target_check, mode="eval").body)
                                    cands.append((target_check, lb_ir))
                                except SyntaxError:
                                    pass
                        for p_txt, _ in petri.synthesize_petri_candidates(
                            rel_file=rel_f,
                            orig_expr=orig_cond_txt,
                            fail_frames=cond_prof.fail_frames,
                            pass_frames=cond_prof.pass_frames,
                            require_bool=True,
                            max_candidates=10,
                        ):
                            try:
                                p_ir = SemanticMeaningIR.lift_expr(ast.parse(p_txt, mode="eval").body)
                                cands.append((p_txt, p_ir))
                            except SyntaxError:
                                pass
                        norm_alias_pairs: set[frozenset[str]] = set()
                        if enclosing_fn is not None:
                            for fn_asgn in ast.walk(enclosing_fn):
                                lhs_nm = None
                                rhs_val = None
                                if isinstance(fn_asgn, ast.Assign) and len(fn_asgn.targets) == 1 and isinstance(fn_asgn.targets[0], ast.Name):
                                    lhs_nm, rhs_val = fn_asgn.targets[0].id, fn_asgn.value
                                elif isinstance(fn_asgn, ast.AnnAssign) and isinstance(fn_asgn.target, ast.Name) and fn_asgn.value is not None:
                                    lhs_nm, rhs_val = fn_asgn.target.id, fn_asgn.value
                                elif isinstance(fn_asgn, ast.NamedExpr) and isinstance(fn_asgn.target, ast.Name):
                                    lhs_nm, rhs_val = fn_asgn.target.id, fn_asgn.value
                                if lhs_nm and rhs_val is not None and any(
                                    isinstance(c_n, ast.Call)
                                    and isinstance(c_n.func, ast.Attribute)
                                    and c_n.func.attr in ("strip", "lstrip", "rstrip", "lower", "upper")
                                    for c_n in ast.walk(rhs_val)
                                ):
                                    for rhs_n in ast.walk(rhs_val):
                                        if isinstance(rhs_n, ast.Name) and rhs_n.id != lhs_nm:
                                            norm_alias_pairs.add(frozenset((lhs_nm, rhs_n.id)))
                        disc_preds = (
                            synthesize_discriminating_predicates(
                                cond_mental,
                                fail_envs=cond_mental.fail_envs,
                                pass_envs=active_pass_envs,
                                site_constants=site_constants,
                                max_preds=12,
                            )
                            if len(active_pass_envs) >= 1
                            else []
                        )
                        for d_expr, _ in disc_preds:
                            stun_expr = (
                                f"({orig_cond_txt}) or ({d_expr})"
                                if angelic_bool is True
                                else f"({orig_cond_txt}) and not ({d_expr})"
                            )
                            try:
                                stun_ir = SemanticMeaningIR.lift_expr(ast.parse(stun_expr, mode="eval").body)
                                cands.append((stun_expr, stun_ir))
                            except SyntaxError:
                                pass
                        if norm_alias_pairs:
                            cands = [
                                (ct, ci) for (ct, ci) in cands
                                if not any(
                                    f"{a} == {b}" in ct or f"{b} == {a}" in ct or f"{a} != {b}" in ct or f"{b} != {a}" in ct
                                    for pair in norm_alias_pairs
                                    for a, b in [tuple(pair)]
                                )
                            ]
                        # Sort strictly by minimal MDL cost so concise sub-expression fixes (`converter is not None`) win!
                        cands.sort(key=lambda item: len(item[0]))

                        batch_items: list[tuple[str, IRNode, str]] = []
                        seen_c: set[str] = set()
                        for cand_txt, cand_ir in cands[:24]:
                            if cand_txt in seen_c:
                                continue
                            seen_c.add(cand_txt)
                            patched_src = _replace_ast_span_in_source(src, cond_expr, cand_txt)
                            if patched_src:
                                batch_items.append((cand_txt, cand_ir, patched_src))

                        solved_site = False
                        new_cex_added = False
                        if batch_items:
                            batch_res = self.sim.simulate_patches_parallel(
                                [{rel_f: it[2]} for it in batch_items[:16]],
                                capture_site=(rel_f, cond_ln),
                            )
                            for (cand_txt, cand_ir, patched_src), res in zip(batch_items[:16], batch_res):
                                if res.get("ok"):
                                    orig_ir = SemanticMeaningIR.lift_expr(cond_expr)
                                    verified_in_sim.append(CandidatePatch(
                                        description=f"Angelic-CEGIS `{orig_cond_txt}` -> `{cand_txt}` at {rel_f}:{cond_ln}",
                                        file_patches={rel_f: patched_src},
                                        primary_file=rel_f,
                                        primary_line=cond_ln,
                                        mechanism="ANGELIC_BRANCH_CEGIS",
                                        semantic_delta_ir=f"{orig_ir.canonical_sexpr()} => {cand_ir.canonical_sexpr()}",
                                        mdl_cost=len(cand_txt),
                                    ))
                                    solved_site = True
                                    break
                                if res.get("fail_passed") and res.get("counterexample_frames"):
                                    for cs in res["counterexample_frames"]:
                                        env_cx = _rehydrate_frame(cs)
                                        if env_cx not in active_pass_envs:
                                            active_pass_envs.append(env_cx)
                                            new_cex_added = True
                                            self.cegis_refinements += 1
                        if solved_site or not new_cex_added:
                            break
                    if verified_in_sim:
                        break

            if verified_in_sim:
                self.mental_simulations += mental.simulations_run
                self.mental_pruned += mental.candidates_pruned
                break

            # ------------------------------------------------------------------
            # B. COMPOSITIONAL EXPRESSION + REPO-NATIVE PETRI NET + DUAL-PROGRAM SPLICING
            # ------------------------------------------------------------------
            value_exprs: list[ast.expr] = []

            def _add_val_expr(enode: ast.expr, *, allow_none_const: bool = False) -> None:
                if isinstance(enode, ast.Constant) and enode.value is None and not allow_none_const:
                    return
                # Never replace a multi-part f-string message template (`JoinedStr`) wholesale with a bare variable;
                # instead mutate its interpolated `FormattedValue.value` expressions!
                if isinstance(enode, ast.JoinedStr) and any(isinstance(v, ast.FormattedValue) for v in enode.values):
                    return
                if enode not in value_exprs:
                    value_exprs.append(enode)

            if isinstance(stmt, ast.Return) and stmt.value is not None:
                _add_val_expr(stmt.value, allow_none_const=True)
            elif isinstance(stmt, ast.Assign) and stmt.lineno == lineno:
                _add_val_expr(stmt.value, allow_none_const=True)
            elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None and stmt.lineno == lineno:
                _add_val_expr(stmt.value, allow_none_const=True)
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                for a_node in stmt.value.args[:4]:
                    _add_val_expr(a_node)
                for kw_node in stmt.value.keywords[:4]:
                    _add_val_expr(kw_node.value)

            # Exception-Factory Callee Preservation: inside `raise <Call>`, never swap the exception
            # constructor call itself for a non-exception method; only synthesize over its arguments/f-strings!
            raise_exc_call = stmt.exc if isinstance(stmt, ast.Raise) and isinstance(stmt.exc, ast.Call) else None
            is_compound_block = isinstance(stmt, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try))
            stmt_end_ln = lineno if is_compound_block else getattr(stmt, "end_lineno", lineno)
            walk_root: ast.AST = stmt.test if isinstance(stmt, (ast.If, ast.While)) else stmt
            if isinstance(stmt, (ast.If, ast.While)):
                stmt_end_ln = getattr(stmt.test, "end_lineno", lineno)

            for sub in ast.walk(walk_root):
                sub_ln = getattr(sub, "lineno", -1)
                if not (stmt.lineno <= sub_ln <= stmt_end_ln):
                    continue
                if isinstance(sub, ast.FormattedValue):
                    _add_val_expr(sub.value)
                elif isinstance(sub, ast.Call):
                    if sub is not raise_exc_call:
                        _add_val_expr(sub)
                    for a_node in sub.args[:4]:
                        _add_val_expr(a_node)
                    for kw_node in sub.keywords[:4]:
                        _add_val_expr(kw_node.value)
                elif isinstance(sub, (ast.Compare, ast.BinOp, ast.Attribute)):
                    _add_val_expr(sub)

            in_scope_var_names = [
                k for env in mental.fail_envs[:2] for k in env.keys() if isinstance(k, str) and k.isidentifier()
            ]
            self_types = []
            for ff in prof.fail_frames[:2]:
                sm = ff.get("self")
                if isinstance(sm, Mapping):
                    self_types.extend(sm.get("mro") or ([sm["t"]] if sm.get("t") else []))
            sibling_attrs = petri.sibling_attrs_for_types(self_types) if self_types else []

            for v_node in value_exprs[:6]:
                if time.perf_counter() >= deadline_monotonic or not self.sim.ready:
                    break
                orig_v_txt = ast.unparse(v_node)
                active_pass_envs = list(mental.pass_envs)

                # Backward witness propagation when `stmt` is `return ...` and expected literal is known!
                target_fail_vals: list[Any] | None = None
                if (
                    isinstance(stmt, ast.Return)
                    and stmt.value is not None
                    and self.graph.assertion_expected_literals
                    and len(mental.fail_envs) == 1
                ):
                    for exp_lit in self.graph.assertion_expected_literals[:2]:
                        for inv_node, inv_val in BackwardWitnessAndDualSplicer.invert_return_residual(stmt.value, exp_lit):
                            if ast.unparse(inv_node) == orig_v_txt:
                                target_fail_vals = [inv_val]
                                break

                expr_cands = (
                    synthesize_expressions_bottom_up(
                        mental,
                        orig_expr=orig_v_txt,
                        fail_envs=mental.fail_envs,
                        pass_envs=active_pass_envs,
                        target_fail_values=target_fail_vals,
                        module_names=helper_names,
                        assertion_literals=self.graph.assertion_expected_literals,
                        max_terms=20,
                    )
                    if (len(active_pass_envs) >= 1 or target_fail_vals is not None)
                    else []
                )
                if target_fail_vals is not None and not expr_cands:
                    expr_cands = synthesize_expressions_bottom_up(
                        mental,
                        orig_expr=orig_v_txt,
                        fail_envs=mental.fail_envs,
                        pass_envs=active_pass_envs,
                        target_fail_values=None,
                        module_names=helper_names,
                        assertion_literals=self.graph.assertion_expected_literals,
                        max_terms=20,
                    )

                v_node_is_bool = (
                    isinstance(v_node, (ast.Compare, ast.BoolOp))
                    or (isinstance(v_node, ast.UnaryOp) and isinstance(v_node.op, ast.Not))
                    or (isinstance(v_node, ast.Constant) and isinstance(v_node.value, bool))
                )
                # Inject Repo-Native Type-Transition Petri-Net morphisms + Sibling-Return Monoidal Lifts!
                sib_lifts = (
                    petri.synthesize_sibling_return_lifts(enclosing_fn, stmt, prof.fail_frames)
                    if isinstance(stmt, ast.Return) and v_node is stmt.value
                    else []
                )
                raw_petri = petri.synthesize_petri_candidates(
                    rel_file=rel_f,
                    orig_expr=orig_v_txt,
                    fail_frames=prof.fail_frames,
                    pass_frames=prof.pass_frames,
                    require_bool=v_node_is_bool,
                    max_candidates=16,
                )
                if isinstance(stmt, ast.Raise):
                    # Inside `raise ...`, forbid replacing message expressions with side-effecting validator calls
                    raw_petri = [
                        (pt, pv) for pt, pv in raw_petri
                        if not pv.startswith(("PETRI_METHOD", "PETRI_MOD_FUNC"))
                    ]
                petri_cands = [*sib_lifts, *raw_petri]
                merged_cands: list[tuple[str, IRNode, str]] = []
                seen_expr_txt: set[str] = set()
                # Interleave top Petri morphisms + observational CEGIS terms so domain calls aren't starved
                for p_txt, p_prov in petri_cands[:12]:
                    if p_txt not in seen_expr_txt:
                        try:
                            p_ir = SemanticMeaningIR.lift_expr(ast.parse(p_txt, mode="eval").body)
                            seen_expr_txt.add(p_txt)
                            merged_cands.append((p_txt, p_ir, f"PETRI_NET_SYNTHESIS:{p_prov}"))
                        except SyntaxError:
                            pass
                for c_txt, c_ir in expr_cands[:16]:
                    if c_txt not in seen_expr_txt:
                        seen_expr_txt.add(c_txt)
                        merged_cands.append((c_txt, c_ir, "ANGELIC_VALUE_CEGIS"))

                eval_queue: list[tuple[str, IRNode, str, str]] = []
                for c_txt, c_ir, mech in merged_cands[:24]:
                    p_src = _replace_ast_span_in_source(src, v_node, c_txt)
                    if p_src and not _has_new_dead_branch_equivalence(src, p_src):
                        eval_queue.append((c_txt, c_ir, mech, p_src))

                partial_fail_passers: list[tuple[str, list[dict[str, Any]]]] = []
                partial_mask_holders: list[tuple[str, list[bool]]] = []

                for w_idx in range(0, len(eval_queue), 16):
                    if time.perf_counter() >= deadline_monotonic:
                        break
                    wave_items = eval_queue[w_idx : w_idx + 16]
                    wave_res = self.sim.simulate_patches_parallel(
                        [{rel_f: it[3]} for it in wave_items],
                        capture_site=(rel_f, lineno),
                    )
                    for (cand_txt, cand_ir, mech, patched_src), res in zip(wave_items, wave_res):
                        if res.get("ok"):
                            orig_ir = SemanticMeaningIR.lift_expr(v_node)
                            verified_in_sim.append(CandidatePatch(
                                description=f"{mech} `{orig_v_txt}` -> `{cand_txt}` at {rel_f}:{lineno}",
                                file_patches={rel_f: patched_src},
                                primary_file=rel_f,
                                primary_line=lineno,
                                mechanism=mech.split(":")[0],
                                semantic_delta_ir=f"{orig_ir.canonical_sexpr()} => {cand_ir.canonical_sexpr()}",
                                mdl_cost=len(cand_txt),
                            ))
                            break
                        if res.get("fail_passed"):
                            partial_fail_passers.append((cand_txt, list(res.get("counterexample_frames") or [])))
                        mask = list(res.get("passed_fail_mask") or [])
                        if mask and any(mask) and not all(mask):
                            partial_mask_holders.append((cand_txt, mask))
                    if verified_in_sim:
                        break

                # Dual-Program Splicing Regime A: `P1` (`fail_passed=True`) spliced with `P0` (`orig_v_txt`)!
                if not verified_in_sim and partial_fail_passers:
                    for cand_txt, cx_raw in partial_fail_passers[:4]:
                        self.cegis_refinements += 1
                        cx_envs = [_rehydrate_frame(s) for s in cx_raw]
                        guards = BackwardWitnessAndDualSplicer.synthesize_separating_guards(
                            mental,
                            positive_envs=mental.fail_envs,
                            negative_envs=[*active_pass_envs, *cx_envs],
                            site_constants=site_constants,
                            sibling_bool_attrs=sibling_attrs,
                            synthesize_disc_fn=synthesize_discriminating_predicates,
                            max_guards=8,
                        )
                        spliced_list = BackwardWitnessAndDualSplicer.build_spliced_expressions(
                            positive_expr=cand_txt,
                            negative_expr=orig_v_txt,
                            guards=guards,
                            in_scope_vars=in_scope_var_names,
                            num_distinct_fail_witnesses=len(mental.fail_envs),
                        )
                        splice_batch: list[tuple[str, str]] = []
                        for sp_txt, _ in spliced_list[:8]:
                            sp_src = _replace_ast_span_in_source(src, v_node, sp_txt)
                            if sp_src:
                                splice_batch.append((sp_txt, sp_src))
                        if splice_batch:
                            sp_res = self.sim.simulate_patches_parallel([{rel_f: it[1]} for it in splice_batch])
                            for (sp_txt, sp_src), r_sp in zip(splice_batch, sp_res):
                                if r_sp.get("ok"):
                                    sp_ir = SemanticMeaningIR.lift_expr(ast.parse(sp_txt, mode="eval").body)
                                    orig_ir = SemanticMeaningIR.lift_expr(v_node)
                                    verified_in_sim.append(CandidatePatch(
                                        description=f"Dual-Program-Splice `{sp_txt}` at {rel_f}:{lineno}",
                                        file_patches={rel_f: sp_src},
                                        primary_file=rel_f,
                                        primary_line=lineno,
                                        mechanism="DUAL_PROGRAM_SPLICING",
                                        semantic_delta_ir=f"{orig_ir.canonical_sexpr()} => {sp_ir.canonical_sexpr()}",
                                        mdl_cost=len(sp_txt),
                                    ))
                                    break
                        if verified_in_sim:
                            break

                # Dual-Program Splicing Regime B: Complementary `P1` + `P2` across multiple failing tests!
                if not verified_in_sim and len(partial_mask_holders) >= 2 and len(mental.fail_envs) >= 2:
                    for i_m, (p1_txt, m1) in enumerate(partial_mask_holders[:6]):
                        for p2_txt, m2 in partial_mask_holders[i_m + 1 : 6]:
                            if len(m1) == len(m2) and all(a or b for a, b in zip(m1, m2)):
                                pos_envs = [mental.fail_envs[k] for k, ok_k in enumerate(m1) if ok_k and k < len(mental.fail_envs)]
                                neg_envs = [mental.fail_envs[k] for k, ok_k in enumerate(m1) if not ok_k and k < len(mental.fail_envs)]
                                guards_12 = BackwardWitnessAndDualSplicer.synthesize_separating_guards(
                                    mental,
                                    positive_envs=pos_envs,
                                    negative_envs=neg_envs,
                                    site_constants=site_constants,
                                    sibling_bool_attrs=sibling_attrs,
                                    synthesize_disc_fn=synthesize_discriminating_predicates,
                                    max_guards=6,
                                )
                                spliced_12 = BackwardWitnessAndDualSplicer.build_spliced_expressions(
                                    positive_expr=p1_txt,
                                    negative_expr=p2_txt,
                                    guards=guards_12,
                                    in_scope_vars=in_scope_var_names,
                                    num_distinct_fail_witnesses=len(mental.fail_envs),
                                )
                                sp12_batch = [
                                    (sp_t, s_p)
                                    for sp_t, _ in spliced_12[:6]
                                    if (s_p := _replace_ast_span_in_source(src, v_node, sp_t)) is not None
                                ]
                                if sp12_batch:
                                    r12 = self.sim.simulate_patches_parallel([{rel_f: it[1]} for it in sp12_batch])
                                    for (sp_t, s_p), rr in zip(sp12_batch, r12):
                                        if rr.get("ok"):
                                            sp_ir = SemanticMeaningIR.lift_expr(ast.parse(sp_t, mode="eval").body)
                                            orig_ir = SemanticMeaningIR.lift_expr(v_node)
                                            verified_in_sim.append(CandidatePatch(
                                                description=f"Dual-Partition-Splice `{sp_t}` at {rel_f}:{lineno}",
                                                file_patches={rel_f: s_p},
                                                primary_file=rel_f,
                                                primary_line=lineno,
                                                mechanism="DUAL_PROGRAM_SPLICING",
                                                semantic_delta_ir=f"{orig_ir.canonical_sexpr()} => {sp_ir.canonical_sexpr()}",
                                                mdl_cost=len(sp_t),
                                            ))
                                            break
                            if verified_in_sim:
                                break
                        if verified_in_sim:
                            break

                if verified_in_sim:
                    break

            if verified_in_sim:
                self.mental_simulations += mental.simulations_run
                self.mental_pruned += mental.candidates_pruned
                break

            # ------------------------------------------------------------------
            # C. STATEMENT-LEVEL VALIDATION / EXCEPTION TRANSLATION / STREAM MATERIALIZATION
            # ------------------------------------------------------------------
            disc_preds = synthesize_discriminating_predicates(
                mental, fail_envs=mental.fail_envs, pass_envs=mental.pass_envs, max_preds=8
            )
            candidate_excs = list(dict.fromkeys([*self.graph.expected_exceptions, *mod_excs, "ValueError"]))

            if self.graph.expected_exceptions and disc_preds and self.sim.ready:
                for exc_name in candidate_excs[:3]:
                    for d_expr, d_ir in disc_preds[:6]:
                        guard_src = _insert_before_line(lines, stmt.lineno, [f"if {d_expr}:", f"    raise {exc_name}({d_expr!r})"])
                        try:
                            ast.parse(guard_src)
                        except SyntaxError:
                            continue
                        if self.sim.simulate_patch({rel_f: guard_src}).get("ok"):
                            verified_in_sim.append(CandidatePatch(
                                description=f"Synthesized domain validation `if {d_expr}: raise {exc_name}` at {rel_f}:{stmt.lineno}",
                                file_patches={rel_f: guard_src},
                                primary_file=rel_f,
                                primary_line=stmt.lineno,
                                mechanism="STUN_GUARD_SYNTHESIS",
                                semantic_delta_ir=f"PRECOND_RAISE({exc_name}, {d_ir.canonical_sexpr()})",
                                mdl_cost=len(d_expr) + 12,
                            ))
                            break
                    if verified_in_sim:
                        break

            # Exception translation when raw crash (`ValueError`/`KeyError`/`IndexError`) needs domain exception!
            if not verified_in_sim and prof.crash_exceptions and candidate_excs and self.sim.ready:
                end_ln = getattr(stmt, "end_lineno", stmt.lineno)
                for raw_exc in list(dict.fromkeys(prof.crash_exceptions))[:2]:
                    if not raw_exc or not raw_exc[0].isupper():
                        continue
                    for dom_exc in candidate_excs[:3]:
                        if dom_exc == raw_exc or not dom_exc[0].isupper():
                            continue
                        tr_src = _wrap_stmt_in_try_except(lines, stmt.lineno, end_ln, raw_exc, dom_exc)
                        try:
                            ast.parse(tr_src)
                        except SyntaxError:
                            continue
                        if self.sim.simulate_patch({rel_f: tr_src}).get("ok"):
                            verified_in_sim.append(CandidatePatch(
                                description=f"Exception translation `{raw_exc}` -> `{dom_exc}` at {rel_f}:{stmt.lineno}",
                                file_patches={rel_f: tr_src},
                                primary_file=rel_f,
                                primary_line=stmt.lineno,
                                mechanism="STUN_GUARD_SYNTHESIS",
                                semantic_delta_ir=f"TRANSLATE_EXC({raw_exc}, {dom_exc})",
                                mdl_cost=28,
                            ))
                            break

            if not verified_in_sim and (prof.in_crash_stack or prof.fail_anomalies) and disc_preds and self.sim.ready:
                ret_candidates = ["None", "False", "''", "()", "[]", "0"]
                for lit in self.graph.assertion_expected_literals[:2]:
                    if repr(lit) not in ret_candidates and len(repr(lit)) <= 24:
                        ret_candidates.insert(0, repr(lit))
                for d_expr, d_ir in disc_preds[:5]:
                    for r_val in ret_candidates[:5]:
                        g_src = _insert_before_line(lines, stmt.lineno, [f"if {d_expr}:", f"    return {r_val}"])
                        try:
                            ast.parse(g_src)
                        except SyntaxError:
                            continue
                        if self.sim.simulate_patch({rel_f: g_src}).get("ok"):
                            verified_in_sim.append(CandidatePatch(
                                description=f"Synthesized anomaly guard `if {d_expr}: return {r_val}` at {rel_f}:{stmt.lineno}",
                                file_patches={rel_f: g_src},
                                primary_file=rel_f,
                                primary_line=stmt.lineno,
                                mechanism="STUN_GUARD_SYNTHESIS",
                                semantic_delta_ir=f"GUARDED_EARLY_RETURN({d_ir.canonical_sexpr()}, {r_val})",
                                mdl_cost=len(d_expr) + len(r_val),
                            ))
                            break
                    if verified_in_sim:
                        break

            # Method-entry Petri guard synthesis (`if <separating_guard>: return <Petri_projection>`):
            # Supports BOTH inter-test contrast (`fail_envs` vs `pass_envs`) AND intra-test contrast
            # (`[fail_envs[-1]]` vs `fail_envs[:-1]`, when multiple assertions execute inside one test function
            # and all earlier calls succeeded before the final call triggered `AssertionError`!).
            eff_pos_envs = mental.fail_envs if mental.pass_envs else ([mental.fail_envs[-1]] if len(mental.fail_envs) >= 2 else [])
            eff_neg_envs = mental.pass_envs if mental.pass_envs else ([mental.fail_envs[0]] if len(mental.fail_envs) >= 2 else [])
            if (
                not verified_in_sim
                and enclosing_fn is not None
                and eff_pos_envs
                and eff_neg_envs
                and self.sim.ready
                and time.perf_counter() < deadline_monotonic
            ):
                from canonical.swe_kernel.petri_cow_splicing_engine_v1 import BackwardWitnessAndDualSplicer
                sib_attrs = list(sibling_attrs)
                # Also harvest `self.<attr>` names observed in runtime frame snapshots or AST of `enclosing_fn`
                for fn_sub in ast.walk(enclosing_fn):
                    if isinstance(fn_sub, ast.Attribute) and isinstance(fn_sub.value, ast.Name) and fn_sub.value.id == "self":
                        if fn_sub.attr not in sib_attrs and not fn_sub.attr.startswith("__"):
                            sib_attrs.append(fn_sub.attr)
                for snap_d in prof.fail_frames + prof.pass_frames[:3]:
                    self_meta = snap_d.get("self") if isinstance(snap_d, Mapping) else None
                    if isinstance(self_meta, Mapping):
                        for k_at in (self_meta.get("attrs") or {}):
                            if k_at not in sib_attrs and not k_at.startswith("__"):
                                sib_attrs.append(k_at)

                # Prefer public properties/attributes (`self.type`) over private backing slots (`self._type`)
                sib_attrs.sort(key=lambda a: (1 if a.startswith("_") else 0))

                sep_guards = BackwardWitnessAndDualSplicer.synthesize_separating_guards(
                    mental,
                    positive_envs=eff_pos_envs,
                    negative_envs=eff_neg_envs,
                    sibling_bool_attrs=sib_attrs,
                    synthesize_disc_fn=synthesize_discriminating_predicates,
                    max_guards=6,
                )
                if sep_guards:
                    # Determine first non-docstring statement AND first statement after any leading `if ...: return/raise` guards
                    body_stmts = list(enclosing_fn.body)
                    start_idx = 0
                    if (
                        len(body_stmts) >= 2
                        and isinstance(body_stmts[0], ast.Expr)
                        and isinstance(getattr(body_stmts[0], "value", None), ast.Constant)
                        and isinstance(body_stmts[0].value.value, str)
                    ):
                        start_idx = 1
                    entry_stmt = body_stmts[start_idx]
                    post_guard_idx = start_idx
                    while post_guard_idx < len(body_stmts) - 1:
                        cur_s = body_stmts[post_guard_idx]
                        if (
                            isinstance(cur_s, ast.If)
                            and not cur_s.orelse
                            and len(cur_s.body) == 1
                            and isinstance(cur_s.body[0], (ast.Return, ast.Raise))
                        ):
                            post_guard_idx += 1
                        else:
                            break
                    post_guard_stmt = body_stmts[post_guard_idx]

                    petri_returns: list[str] = []
                    # Mine string/scalar projections over `self.<attr>` & bound arguments
                    for attr_nm in sib_attrs[:10]:
                        ok_a, vec_a = mental.eval_expr_vector(f"self.{attr_nm}", eff_pos_envs[:1])
                        if ok_a and vec_a and vec_a[0][0] == "str":
                            for m_str in (f"self.{attr_nm}.title()", f"self.{attr_nm}.strip()", f"self.{attr_nm}.lower()", f"self.{attr_nm}.upper()", f"self.{attr_nm}"):
                                if m_str not in petri_returns:
                                    petri_returns.append(m_str)
                        elif ok_a and vec_a and vec_a[0][0] in ("int", "bool", "tuple", "list", "bytes"):
                            if f"self.{attr_nm}" not in petri_returns:
                                petri_returns.append(f"self.{attr_nm}")
                    for arg_node in enclosing_fn.args.args:
                        a_nm = arg_node.arg
                        if a_nm in ("self", "cls"):
                            continue
                        ok_p, vec_p = mental.eval_expr_vector(a_nm, eff_pos_envs[:1])
                        if ok_p and vec_p and vec_p[0][0] == "str":
                            petri_returns.extend([f"{a_nm}.strip()", a_nm])
                        elif ok_p:
                            petri_returns.append(a_nm)
                    for neutral in ("''", "()", "[]", "None"):
                        if neutral not in petri_returns:
                            petri_returns.append(neutral)

                    target_insert_lines: list[int] = [post_guard_stmt.lineno]
                    for top_st in body_stmts[start_idx:]:
                        end_top = getattr(top_st, "end_lineno", top_st.lineno)
                        if top_st.lineno <= stmt.lineno <= end_top and top_st.lineno not in target_insert_lines:
                            target_insert_lines.append(top_st.lineno)
                            break
                    if entry_stmt.lineno not in target_insert_lines:
                        target_insert_lines.append(entry_stmt.lineno)

                    builtin_excs = ("ValueError", "TypeError", "KeyError")
                    in_scope_excs: list[str] = []
                    for exp_e in self.graph.expected_exceptions:
                        if exp_e in mod_excs or exp_e in builtin_excs:
                            if exp_e not in in_scope_excs:
                                in_scope_excs.append(exp_e)
                    for me in (*mod_excs[:4], *builtin_excs):
                        if me not in in_scope_excs:
                            in_scope_excs.append(me)

                    entry_candidates: list[tuple[str, str, str, int, str]] = []
                    for ins_ln in target_insert_lines:
                        for g_expr in sep_guards[:4]:
                            if "==" in g_expr and "None" not in g_expr and "0" not in g_expr and "''" not in g_expr:
                                continue
                            # If test suite explicitly expected an exception (`DID NOT RAISE`), prioritize guarded `raise`!
                            if self.graph.expected_exceptions:
                                for exc_nm in in_scope_excs[:4]:
                                    g_src = _insert_before_line(lines, ins_ln, [f"if {g_expr}:", f"    raise {exc_nm}()"])
                                    try:
                                        ast.parse(g_src)
                                        entry_candidates.append((g_expr, f"raise {exc_nm}()", g_src, ins_ln, "PETRI_GUARDED_RAISE"))
                                    except SyntaxError:
                                        continue
                            for r_expr in petri_returns[:8]:
                                g_src = _insert_before_line(lines, ins_ln, [f"if {g_expr}:", f"    return {r_expr}"])
                                try:
                                    ast.parse(g_src)
                                    entry_candidates.append((g_expr, f"return {r_expr}", g_src, ins_ln, "EARLY_RETURN_PETRI_GUARD"))
                                except SyntaxError:
                                    continue
                            if not self.graph.expected_exceptions:
                                for exc_nm in in_scope_excs[:2]:
                                    g_src = _insert_before_line(lines, ins_ln, [f"if {g_expr}:", f"    raise {exc_nm}()"])
                                    try:
                                        ast.parse(g_src)
                                        entry_candidates.append((g_expr, f"raise {exc_nm}()", g_src, ins_ln, "PETRI_GUARDED_RAISE"))
                                    except SyntaxError:
                                        continue
                    if entry_candidates:
                        batch_out = self.sim.simulate_patches_parallel(
                            [{rel_f: ec[2]} for ec in entry_candidates[:18]]
                        )
                        for (g_expr, act_expr, g_src, ins_ln, sub_mech), b_res in zip(entry_candidates[:18], batch_out):
                            if b_res.get("ok"):
                                verified_in_sim.append(CandidatePatch(
                                    description=f"Method Petri guard `if {g_expr}: {act_expr}` at {rel_f}:{ins_ln}",
                                    file_patches={rel_f: g_src},
                                    primary_file=rel_f,
                                    primary_line=ins_ln,
                                    mechanism=f"PETRI_NET_SYNTHESIS:{sub_mech}",
                                    semantic_delta_ir=f"METHOD_ENTRY_GUARD({g_expr} => {act_expr})",
                                    mdl_cost=len(g_expr) + len(act_expr) + 8,
                                ))
                                break

            # Single-pass stream/iterator materialization on multi-read variables in enclosing function
            if not verified_in_sim and enclosing_fn is not None and self.sim.ready:
                read_counts: dict[str, int] = {}
                assign_sites: dict[str, list[ast.Assign]] = {}
                for sub in ast.walk(enclosing_fn):
                    if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                        read_counts[sub.id] = read_counts.get(sub.id, 0) + 1
                    elif isinstance(sub, ast.Assign) and len(sub.targets) == 1 and isinstance(sub.targets[0], ast.Name):
                        assign_sites.setdefault(sub.targets[0].id, []).append(sub)
                for var_nm, r_cnt in read_counts.items():
                    if r_cnt < 2 or var_nm in ("self", "cls"):
                        continue
                    for asgn in assign_sites.get(var_nm, ()):
                        rhs_txt = ast.unparse(asgn.value)
                        mat_src = _replace_ast_span_in_source(src, asgn.value, f"tuple({rhs_txt})")
                        if mat_src and self.sim.simulate_patch({rel_f: mat_src}).get("ok"):
                            verified_in_sim.append(CandidatePatch(
                                description=f"Stream materialization `{rhs_txt}` -> `tuple({rhs_txt})` at {rel_f}:{asgn.lineno}",
                                file_patches={rel_f: mat_src},
                                primary_file=rel_f,
                                primary_line=asgn.lineno,
                                mechanism="ANGELIC_VALUE_CEGIS",
                                semantic_delta_ir="MATERIALIZE_SINGLE_PASS_STREAM($v0)",
                                mdl_cost=len(rhs_txt) + 7,
                            ))
                            break
                    if verified_in_sim:
                        break

            # Bidirectional Codec / Stream Lens Synthesis (`BIDIRECTIONAL_CODEC_LENS`) for `.decode` / `.encode` / `TextIOWrapper`
            if not verified_in_sim and enclosing_fn is not None and self.sim.ready and time.perf_counter() < deadline_monotonic:
                codec_cands: list[tuple[str, str, int]] = []
                has_io_import = ("import io" in src) or ("from io import" in src)
                for c_node in ast.walk(enclosing_fn):
                    if not isinstance(c_node, ast.Call):
                        continue
                    # Pattern A: `<expr>.decode(...)` or `<expr>.decode(...).replace("\r\n", "\n")`
                    if (
                        isinstance(c_node.func, ast.Attribute)
                        and c_node.func.attr == "replace"
                        and len(c_node.args) == 2
                        and isinstance(c_node.func.value, ast.Call)
                        and isinstance(c_node.func.value.func, ast.Attribute)
                        and c_node.func.value.func.attr == "decode"
                        and has_io_import
                    ):
                        dec_call = c_node.func.value
                        raw_txt = ast.unparse(dec_call.func.value)
                        enc_txt = ast.unparse(dec_call.args[0]) if len(dec_call.args) >= 1 else "'utf-8'"
                        err_txt = ast.unparse(dec_call.args[1]) if len(dec_call.args) >= 2 else "'replace'"
                        tio_expr = f"io.TextIOWrapper(io.BytesIO({raw_txt}), encoding={enc_txt}, errors={err_txt}).read()"
                        patched_c = _replace_ast_span_in_source(src, c_node, tio_expr)
                        if patched_c:
                            codec_cands.append((tio_expr, patched_c, c_node.lineno))
                    elif isinstance(c_node.func, ast.Attribute) and c_node.func.attr == "decode":
                        raw_txt = ast.unparse(c_node.func.value)
                        enc_txt = ast.unparse(c_node.args[0]) if len(c_node.args) >= 1 else "'utf-8'"
                        for err_m in ("'replace'", "'surrogateescape'", "'strict'"):
                            cand_e = f"{raw_txt}.decode({enc_txt}, {err_m})"
                            patched_c = _replace_ast_span_in_source(src, c_node, cand_e)
                            if patched_c and patched_c != src:
                                codec_cands.append((cand_e, patched_c, c_node.lineno))
                        if has_io_import:
                            tio_expr = f"io.TextIOWrapper(io.BytesIO({raw_txt}), encoding={enc_txt}, errors='replace').read()"
                            patched_c = _replace_ast_span_in_source(src, c_node, tio_expr)
                            if patched_c:
                                codec_cands.append((tio_expr, patched_c, c_node.lineno))
                    elif isinstance(c_node.func, ast.Attribute) and c_node.func.attr == "TextIOWrapper":
                        orig_tio = ast.unparse(c_node)
                        if "newline=" not in orig_tio and orig_tio.endswith(")"):
                            for nl_opt in ("newline=''", "newline='\\n'"):
                                cand_tio = orig_tio[:-1] + f", {nl_opt})"
                                patched_c = _replace_ast_span_in_source(src, c_node, cand_tio)
                                if patched_c:
                                    codec_cands.append((cand_tio, patched_c, c_node.lineno))
                if codec_cands:
                    c_batch = self.sim.simulate_patches_parallel([{rel_f: cc[1]} for cc in codec_cands[:12]])
                    for (c_desc, c_src, c_ln), c_res in zip(codec_cands[:12], c_batch):
                        if c_res.get("ok"):
                            verified_in_sim.append(CandidatePatch(
                                description=f"Bidirectional codec/stream lens `{c_desc}` at {rel_f}:{c_ln}",
                                file_patches={rel_f: c_src},
                                primary_file=rel_f,
                                primary_line=c_ln,
                                mechanism="BIDIRECTIONAL_CODEC_LENS",
                                semantic_delta_ir=f"CODEC_STREAM_LENS({c_desc})",
                                mdl_cost=len(c_desc) + 6,
                            ))
                            break

            # Crash-Site Exception Translation & Graceful Recovery (`PETRI_EXCEPTION_TRANSLATION`)
            # + Runtime Type-Lattice `isinstance` Widening (`TYPE_LATTICE_ISINSTANCE_JOIN`)
            if not verified_in_sim and enclosing_fn is not None and self.sim.ready and time.perf_counter() < deadline_monotonic:
                exc_and_type_cands: list[tuple[str, str, int, str]] = []
                seen_crash_excs = [
                    ex_nm for ex_nm in prof.crash_exceptions
                    if ex_nm and ex_nm not in ("AssertionError", "SystemExit", "KeyboardInterrupt", "BaseException", "Exception")
                ]
                if seen_crash_excs and stmt.lineno == getattr(stmt, "end_lineno", stmt.lineno) and 1 <= stmt.lineno <= len(lines):
                    raw_ln = lines[stmt.lineno - 1]
                    ind_m = re.match(r"^([ \t]*)", raw_ln)
                    ind = ind_m.group(1) if ind_m else ""
                    stmt_body_txt = raw_ln.strip()
                    for c_exc in seen_crash_excs[:2]:
                        # 1. Translate internal crash to expected domain exception
                        for exp_e in [*self.graph.expected_exceptions, *mod_excs[:3]]:
                            if exp_e != c_exc and (exp_e in mod_excs or exp_e in ("ValueError", "TypeError", "KeyError")):
                                wrapped = (
                                    f"{ind}try:\n"
                                    f"{ind}    {stmt_body_txt}\n"
                                    f"{ind}except {c_exc} as _exc:\n"
                                    f"{ind}    raise {exp_e}(str(_exc)) from _exc\n"
                                )
                                cand_src = "".join(lines[: stmt.lineno - 1]) + wrapped + "".join(lines[stmt.lineno :])
                                try:
                                    ast.parse(cand_src)
                                    exc_and_type_cands.append((f"try ... except {c_exc}: raise {exp_e}", cand_src, stmt.lineno, "PETRI_EXCEPTION_TRANSLATION"))
                                except SyntaxError:
                                    pass
                        # 2. Graceful neutral return on empty/boundary crash when no exception was expected
                        if not self.graph.expected_exceptions:
                            for neut in ("None", "''", "()", "[]", "False"):
                                wrapped = (
                                    f"{ind}try:\n"
                                    f"{ind}    {stmt_body_txt}\n"
                                    f"{ind}except {c_exc}:\n"
                                    f"{ind}    return {neut}\n"
                                )
                                cand_src = "".join(lines[: stmt.lineno - 1]) + wrapped + "".join(lines[stmt.lineno :])
                                try:
                                    ast.parse(cand_src)
                                    exc_and_type_cands.append((f"try ... except {c_exc}: return {neut}", cand_src, stmt.lineno, "PETRI_EXCEPTION_TRANSLATION"))
                                except SyntaxError:
                                    pass

                # 3. Runtime Type-Lattice `isinstance(x, T)` -> `isinstance(x, (T, T_obs))` join
                safe_type_names = {"bytes", "bytearray", "memoryview", "str", "int", "float", "tuple", "list", "dict", "set"}
                if eff_pos_envs:
                    for c_sub in ast.walk(enclosing_fn):
                        if (
                            isinstance(c_sub, ast.Call)
                            and isinstance(c_sub.func, ast.Name)
                            and c_sub.func.id == "isinstance"
                            and len(c_sub.args) == 2
                        ):
                            subj_txt = ast.unparse(c_sub.args[0])
                            tspec_txt = ast.unparse(c_sub.args[1])
                            ok_subj, vec_subj = mental.eval_expr_vector(subj_txt, eff_pos_envs[:2])
                            if ok_subj and vec_subj:
                                obs_t = vec_subj[0][0]
                                if obs_t in safe_type_names and obs_t not in tspec_txt:
                                    if isinstance(c_sub.args[1], ast.Tuple):
                                        inner = ", ".join(ast.unparse(el) for el in c_sub.args[1].elts)
                                        new_iso = f"isinstance({subj_txt}, ({inner}, {obs_t}))"
                                    else:
                                        new_iso = f"isinstance({subj_txt}, ({tspec_txt}, {obs_t}))"
                                    patched_iso = _replace_ast_span_in_source(src, c_sub, new_iso)
                                    if patched_iso:
                                        exc_and_type_cands.append((new_iso, patched_iso, c_sub.lineno, "TYPE_LATTICE_ISINSTANCE_JOIN"))

                if exc_and_type_cands:
                    et_batch = self.sim.simulate_patches_parallel([{rel_f: ec[1]} for ec in exc_and_type_cands[:12]])
                    for (et_desc, et_src, et_ln, et_mech), et_res in zip(exc_and_type_cands[:12], et_batch):
                        if et_res.get("ok"):
                            verified_in_sim.append(CandidatePatch(
                                description=f"{et_mech} `{et_desc}` at {rel_f}:{et_ln}",
                                file_patches={rel_f: et_src},
                                primary_file=rel_f,
                                primary_line=et_ln,
                                mechanism=f"PETRI_NET_SYNTHESIS:{et_mech}",
                                semantic_delta_ir=f"{et_mech}({et_desc})",
                                mdl_cost=len(et_desc) + 8,
                            ))
                            break

            self.mental_simulations += mental.simulations_run
            self.mental_pruned += mental.candidates_pruned
            if verified_in_sim:
                break

        # ----------------------------------------------------------------------
        # D. COUPLED MULTI-FILE PRODUCER + CONSUMER CAUSAL SYNTHESIS
        # ----------------------------------------------------------------------
        if not verified_in_sim and self.sim.ready and time.perf_counter() < deadline_monotonic:
            for up_file, down_file, edge_kind in self.graph.coupled_file_pairs()[:4]:
                if time.perf_counter() >= deadline_monotonic:
                    break
                up_loaded = _load_file(up_file)
                down_loaded = _load_file(down_file)
                if not up_loaded or not down_loaded:
                    continue
                up_sites = [s for s in ranked_sites if s["file"] == up_file][:4]
                down_sites = [s for s in ranked_sites if s["file"] == down_file][:4]
                for us in up_sites:
                    for ds in down_sites:
                        u_stmt, _, _ = self._find_enclosing_stmt_and_func(up_loaded[2], int(us["line"]))
                        d_stmt, _, _ = self._find_enclosing_stmt_and_func(down_loaded[2], int(ds["line"]))
                        if u_stmt is None or d_stmt is None:
                            continue
                        u_expr = u_stmt.value if isinstance(u_stmt, (ast.Return, ast.Assign)) else None
                        d_expr = d_stmt.test if isinstance(d_stmt, ast.If) else (d_stmt.value if isinstance(d_stmt, (ast.Return, ast.Assign)) else None)
                        if u_expr is None or d_expr is None:
                            continue
                        u_prof = self.graph.sites.get((up_file, int(us["line"])))
                        d_prof = self.graph.sites.get((down_file, int(ds["line"])))
                        if not u_prof or not d_prof:
                            continue
                        u_mental = ProgramStateMentalModel(u_prof.fail_frames, u_prof.pass_frames)
                        d_mental = ProgramStateMentalModel(d_prof.fail_frames, d_prof.pass_frames)
                        u_cands = synthesize_expressions_bottom_up(
                            u_mental, orig_expr=ast.unparse(u_expr),
                            fail_envs=u_mental.fail_envs, pass_envs=u_mental.pass_envs, max_terms=10,
                        )
                        d_cands = synthesize_expressions_bottom_up(
                            d_mental, orig_expr=ast.unparse(d_expr),
                            fail_envs=d_mental.fail_envs, pass_envs=d_mental.pass_envs,
                            allow_upstream_value_shift=True,
                            require_bool=isinstance(d_stmt, ast.If),
                            max_terms=10,
                        )
                        for u_txt, u_ir in u_cands[:6]:
                            u_patched = _replace_ast_span_in_source(up_loaded[0], u_expr, u_txt)
                            if not u_patched:
                                continue
                            for d_txt, d_ir in d_cands[:6]:
                                d_patched = _replace_ast_span_in_source(down_loaded[0], d_expr, d_txt)
                                if not d_patched:
                                    continue
                                coupled = {up_file: u_patched, down_file: d_patched}
                                if self.sim.simulate_patch(coupled).get("ok"):
                                    verified_in_sim.append(CandidatePatch(
                                        description=f"Coupled 2-file repair: {up_file}:{us['line']} + {down_file}:{ds['line']} ({edge_kind})",
                                        file_patches=coupled,
                                        primary_file=up_file,
                                        primary_line=int(us["line"]),
                                        mechanism="COUPLED_DATAFLOW_CEGIS",
                                        semantic_delta_ir=f"COUPLED({u_ir.canonical_sexpr()}, {d_ir.canonical_sexpr()})",
                                        mdl_cost=len(u_txt) + len(d_txt),
                                    ))
                                    break
                            if verified_in_sim:
                                break

        verified_in_sim.sort(key=lambda c: c.mdl_cost)
        return verified_in_sim


def unified_diff_for_patches(worktree: pathlib.Path, file_patches: Mapping[str, str]) -> str:
    chunks: list[str] = []
    for rel_f in sorted(file_patches):
        orig = (worktree / rel_f).read_text(encoding="utf-8")
        new = file_patches[rel_f]
        if orig == new:
            continue
        chunks.extend(
            difflib.unified_diff(
                orig.splitlines(keepends=True),
                new.splitlines(keepends=True),
                fromfile=f"a/{rel_f}",
                tofile=f"b/{rel_f}",
            )
        )
    return "".join(chunks)
